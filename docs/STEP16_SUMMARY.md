# Step 16 Summary: Run DOMASS Neural Network

**Status:** Complete
**Implementation:** `steps/step16_run_domass.py`
**Lines of Code:** ~310
**Complexity:** Medium

---

## Purpose

Run the trained DOMASS TensorFlow neural network to predict the probability that each domain-ECOD pair represents a correct ECOD classification. Outputs probabilities for filtering in step 17.

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step RUN_DOMASS \
  --working-dir ./work --data-dir ./data
```

### Input
- `{prefix}.step15_features` - Features for ML model (from step 15)
- `domass_epo29.*` - Trained TensorFlow model checkpoint

### Output
- `{prefix}.step16_predictions` - ML predictions with probabilities

### Performance
- **Time:** 2-15 seconds (depends on feature count)
- **Memory:** 500MB - 2GB (TensorFlow overhead)

---

## Model Architecture

```
Input Layer:    13 features (float32)
                    |
Hidden Layer:   64 neurons, ReLU activation
                    |
Output Layer:   2-class softmax (incorrect=0, correct=1)
```

### TensorFlow Layer Names
- `dense` - Hidden layer (64 units)
- `dense_1` - Output layer (2 units)

---

## Algorithm

```
1. Load feature file from step 15
2. Extract 13 numerical features per row (columns 4-16)
3. Preserve metadata (domain, range, tgroup, ecod, hit names)
4. Initialize TensorFlow 1.x compatibility mode
5. Build model graph (dense -> dense_1 -> softmax)
6. Load trained weights from checkpoint
7. Process in batches of 100:
   a. Full batches: Direct inference
   b. Partial batch: Pad with copies, extract valid predictions
   c. Small datasets (<100): Tile to reach batch size
8. Extract probability of class 1 (correct assignment)
9. Write results with all features + DPAM probability
```

---

## Features Used (13 of 17)

The model uses columns 4-16 from step 15 output:

| Index | Feature | Description |
|-------|---------|-------------|
| 0 | domain_length | Domain size in residues |
| 1 | helix_count | Number of helices |
| 2 | strand_count | Number of strands |
| 3 | hh_prob | HHsearch probability |
| 4 | hh_cov | HHsearch coverage |
| 5 | hh_rank | HHsearch rank (normalized) |
| 6 | dali_zscore | DALI z-score (normalized) |
| 7 | dali_qscore | DALI q-score |
| 8 | dali_ztile | DALI z-score percentile |
| 9 | dali_qtile | DALI q-score percentile |
| 10 | dali_rank | DALI rank (normalized) |
| 11 | consensus_diff | Template position difference |
| 12 | consensus_cov | Consensus coverage |

---

## Batch Processing

### Standard Processing (>=100 samples)
```python
n_batches = n_samples // batch_size
for i in range(n_batches):
    batch = features[i*100 : (i+1)*100]
    predictions = model.predict(batch)
```

### Partial Batch Handling
```python
# Pad with copies from beginning of dataset
remaining = n_samples % batch_size
last_batch = features[n_batches*100:]
padding = features[:batch_size - remaining]
padded = np.vstack([last_batch, padding])
```

### Small Dataset Handling (<100 samples)
```python
# Tile features to reach batch size
fold = batch_size // n_samples + 1
pseudo = np.tile(features, (fold, 1))[:batch_size]
```

---

## Output Format

**File:** `{prefix}.step16_predictions`

**Header:**
```
Domain  Range  Tgroup  ECOD_ref  DPAM_prob  HH_prob  HH_cov  HH_rank  DALI_zscore  DALI_qscore  DALI_ztile  DALI_qtile  DALI_rank  Consensus_diff  Consensus_cov  HH_hit  DALI_hit  DALI_rot1  DALI_rot2  DALI_rot3  DALI_trans
```

**Example:**
```
D1	10-150	2.30.30	e1abc1	0.9234	0.950	0.850	0.30	2.530	0.850	0.120	0.050	0.12	1.50	0.720	000000003_1	Q1_e1abc1_1	na	na	na	na
```

---

## Probability Interpretation

| DPAM_prob | Interpretation |
|-----------|---------------|
| >= 0.9 | Very high confidence |
| 0.7 - 0.9 | High confidence |
| 0.6 - 0.7 | Moderate confidence |
| 0.4 - 0.6 | Uncertain |
| < 0.4 | Low confidence |

---

## Model Checkpoint Files

Required in `data_dir`:
- `domass_epo29.meta` - Graph definition
- `domass_epo29.index` - Variable index
- `domass_epo29.data-00000-of-00001` - Variable values

---

## Typical Statistics

### 500-Residue Protein
- **Features input:** 200-500 rows
- **Processing time:** 3-8 seconds
- **High confidence (>=0.6):** 50-70%
- **Mean probability:** 0.5-0.7

### Summary Statistics Logged
```
Probability range: 0.012 - 0.987
Mean probability: 0.623
Median probability: 0.654
High confidence (>=0.6): 312/500 (62.4%)
```

---

## Common Issues

### TensorFlow not installed
**Error:** `ImportError: TensorFlow not installed`
**Fix:** `pip install tensorflow`

### Model checkpoint not found
**Error:** `Model checkpoint not found: domass_epo29`
**Fix:** Ensure `domass_epo29.*` files exist in data_dir

### Graph construction errors
**Cause:** Layer names don't match checkpoint
**Note:** Must use `dense` and `dense_1` layer names

### Memory issues
**Cause:** Large feature sets with TensorFlow overhead
**Fix:** Process on machine with >= 4GB RAM

---

## TensorFlow Compatibility

Uses TensorFlow 1.x compatibility mode:
```python
tf.compat.v1.reset_default_graph()
tf.compat.v1.Session()
tf.compat.v1.placeholder()
tf.compat.v1.layers.dense()
tf.compat.v1.train.Saver()
```

Tested with TensorFlow 2.x (uses v1 API).

---

## Key Functions

```python
def run_step16(prefix, working_dir, data_dir, model=None, path_resolver=None, **kwargs) -> bool
    # model: Optional pre-loaded DomassModel for batch reuse.
    # path_resolver: Optional PathResolver for sharded output layout.
```

### DomassModel Class

Reusable TensorFlow model session for batch processing. Loads the model graph and checkpoint once; call `predict()` for each protein's features.

```python
class DomassModel:
    def __init__(self, model_path: Path)
    def predict(self, features: np.ndarray) -> np.ndarray
    def close(self)
    # Context manager support (__enter__, __exit__)
```

**Usage:**
```python
with DomassModel(data_dir / "domass_epo29") as model:
    for prefix in proteins:
        run_step16(prefix, working_dir, data_dir, model=model)
```

---

## Batch Mode

For multi-protein runs, the `DomassModel` class eliminates repeated TF model loading:

- **TF model load:** ~22s on cold start (SLURM nodes)
- **Per-protein inference:** <10ms
- **Speedup:** ~628x per-protein (22s vs 0.035s when model pre-loaded)

Must call `tf.compat.v1.disable_eager_execution()` before building TF1 graph in TF2 environment. The `DomassModel` constructor handles this automatically.

Used automatically by `dpam batch-run` (step-first mode) via `BatchRunner._run_domass_batch()`.

---

## Backward Compatibility

**100% v1.0 compatible**
- Same model architecture
- Same batch size (100)
- Same layer names (dense, dense_1)
- Same feature indexing
- Same probability output
- Predictions are bit-identical between batch and single-protein mode

---

## Summary

Step 16 runs the DOMASS neural network to score domain-ECOD pairs.

**Key metrics:**
- 310 lines of code
- 2-15s execution time
- 13 input features
- 64-unit hidden layer
- Binary classification (softmax)
- Batch size 100
- Ready for confidence filtering (step 17)
