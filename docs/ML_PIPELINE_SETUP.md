# ML Pipeline Setup Guide

## Overview

DPAM v2.0 ML pipeline (steps 15-23) uses a trained TensorFlow neural network (DOMASS model) to assign ECOD classifications to parsed domains. This guide explains how to set up and use the ML pipeline.

## Status

**All ML steps are fully implemented** ✅

- ✅ Step 15: PREPARE_DOMASS - Extract 17 ML features
- ✅ Step 16: RUN_DOMASS - Run TensorFlow model
- ✅ Step 17: GET_CONFIDENT - Filter high-confidence predictions
- ✅ Step 18: GET_MAPPING - Map domains to ECOD templates (already implemented)
- ✅ Step 19: GET_MERGE_CANDIDATES - Identify domains to merge
- ⚠️  Step 20-22: Domain merging (already implemented)
- ✅ Step 23: GET_PREDICTIONS - Classify domains as full/part/miss
- ✅ Step 24: INTEGRATE_RESULTS - Final integration (already implemented)

## Prerequisites

### 1. Python Dependencies

```bash
# Install TensorFlow (required for step 16)
pip install tensorflow

# Or with all dev dependencies
pip install -e ".[dev]"
```

### 2. DOMASS Model Files

**CRITICAL**: The ML pipeline requires trained TensorFlow model checkpoint files:

```
data/
└── domass_epo29.meta        # TensorFlow meta graph
└── domass_epo29.index       # TensorFlow checkpoint index
└── domass_epo29.data-*      # TensorFlow checkpoint data
```

**How to obtain the model:**

1. **From DPAM v1.0**: Copy model files from your v1.0 installation
2. **From the original authors**: Contact the DPAM team for trained model
3. **Train your own**: Use the training script with labeled domain data (advanced)

**Model Architecture:**
- Input: 13 features (domain properties, HHsearch scores, DALI scores, consensus metrics)
- Hidden layer: 64 neurons with ReLU activation
- Output: 2-class softmax (incorrect=0, correct=1)
- Framework: TensorFlow 1.x compatibility mode

### 3. Reference Data Files

The ML pipeline requires additional reference files in your `--data-dir`:

```
data/
├── ecod.latest.domains      # ECOD hierarchy (T-groups, H-groups)
├── ECOD_length              # Template lengths
├── ECOD_maps/               # PDB→ECOD residue numbering
│   └── *.map                # One file per ECOD domain
├── posi_weights/            # Position-specific weights (optional)
│   └── *.weight             # One file per ECOD domain
└── tgroup_length            # Average T-group lengths
```

## Running the ML Pipeline

### Full Pipeline (Steps 1-24)

```bash
dpam run AF-P12345 \
  --working-dir ./work \
  --data-dir /path/to/data \
  --cpus 4 \
  --resume
```

The pipeline will automatically run all ML steps (15-24) after completing steps 1-13.

### Run Only ML Steps

```bash
# Run specific ML step
dpam run-step AF-P12345 \
  --step PREPARE_DOMASS \
  --working-dir ./work \
  --data-dir /path/to/data

# Or use step numbers
dpam run-step AF-P12345 \
  --step 15 \
  --working-dir ./work \
  --data-dir /path/to/data
```

### Run ML Steps 15-24

```bash
# Run steps 15 through 24 sequentially
for step in {15..24}; do
  dpam run-step AF-P12345 \
    --step $step \
    --working-dir ./work \
    --data-dir /path/to/data
done
```

## ML Pipeline Data Flow

### Input Requirements

**Step 15** requires outputs from:
- Step 13: `{prefix}.step13_domains` - Parsed domains
- Step 11: `{prefix}.sse` - Secondary structure
- Step 2: `{prefix}.hhsearch_hits` - HHsearch hits
- Step 9: `{prefix}.dali_good_hits` - DALI hits
- Reference: `ECOD_maps/`, `ecod.latest.domains`

**Step 16** requires:
- Step 15: `{prefix}.step15_features`
- Model: `domass_epo29.*` files in data directory

**Step 17** requires:
- Step 16: `{prefix}.step16_predictions`

**Step 18** requires:
- Step 17: `{prefix}.step17_confident_predictions`

**Step 19** requires:
- Step 18: `{prefix}.step18_mappings`
- Reference: `ECOD_length`, `posi_weights/`

**Steps 20-22**: Domain merging pipeline (see existing docs)

**Step 23** requires:
- Step 22: `{prefix}.step22_merged_domains`
- Step 13: `{prefix}.step13_domains`
- Step 16: `{prefix}.step16_predictions`
- Step 18: `{prefix}.step18_mappings`
- Reference: `tgroup_length`, `ECOD_length`, `posi_weights/`

**Step 24** requires:
- Step 23: `{prefix}.step23_predictions`
- Step 11: `{prefix}.sse`

### Output Files

| Step | Output File | Description |
|------|-------------|-------------|
| 15 | `{prefix}.step15_features` | 17 ML features per domain-ECOD pair |
| 16 | `{prefix}.step16_predictions` | ML probabilities for each pair |
| 17 | `{prefix}.step17_confident_predictions` | High-confidence predictions (prob≥0.6) with quality labels |
| 18 | `{prefix}.step18_mappings` | Domain→ECOD template mappings |
| 19 | `{prefix}.step19_merge_candidates` | Domain pairs to merge |
| 23 | `{prefix}.step23_predictions` | Domain classifications (full/part/miss) |
| 24 | `{prefix}.finalDPAM.domains` | Final integrated domain definitions |

## The 17 ML Features

Step 15 extracts these features for each domain-ECOD pair:

### Domain Properties (3 features)
1. **domain_length**: Number of residues in domain
2. **helix_count**: Helices with ≥6 residues
3. **strand_count**: Strands with ≥3 residues

### HHsearch Scores (3 features)
4. **hh_prob**: Probability (0-1, stored as 0-100)
5. **hh_coverage**: Fraction of domain covered by hit
6. **hh_rank**: Average H-groups per residue / 10

### DALI Scores (5 features)
7. **dali_zscore**: Z-score / 10
8. **dali_qscore**: Weighted alignment score
9. **dali_ztile**: Z-score percentile (0-10)
10. **dali_qtile**: Q-score percentile (0-10)
11. **dali_rank**: Family rank / 10

### Consensus Metrics (2 features)
12. **consensus_diff**: Mean template position difference between HH/DALI alignments
13. **consensus_cov**: Fraction of residues with both HH and DALI support

### Metadata (4 fields, not used by ML)
14. **hh_hit_name**: HHsearch hit identifier
15. **dali_hit_name**: DALI hit identifier
16-18. **DALI rotation/translation matrices**

**Note**: The TensorFlow model uses only features 1-13 (columns 5-17 of step 15 output).

## Classification Logic

### Step 17: Quality Labels

Predictions are labeled based on T-group and H-group consistency:

- **good**: Single T-group above threshold (unambiguous)
- **ok**: Multiple T-groups but same H-group (family consensus)
- **bad**: Multiple conflicting H-groups (ambiguous)

**Thresholds:**
- Minimum probability: 0.6
- T-group similarity: within 0.05 of best probability

### Step 23: Full/Part/Miss

Domains are classified based on ML probability and template coverage:

```python
if dpam_prob >= 0.85:
    if weighted_ratio >= 0.66 and length_ratio >= 0.33:
        classification = 'full'    # Full domain match
    elif weighted_ratio >= 0.33 or length_ratio >= 0.33:
        classification = 'part'    # Partial domain
    else:
        classification = 'miss'    # Insufficient coverage
else:
    classification = 'miss'        # Low confidence
```

Where:
- `dpam_prob`: ML model probability
- `weighted_ratio`: Position-weighted template coverage
- `length_ratio`: Domain length / T-group average length

## Troubleshooting

### Missing TensorFlow Model

**Error:** `Model checkpoint not found: {data_dir}/domass_epo29`

**Solution:**
1. Verify model files exist in data directory
2. Check file permissions
3. Obtain model from v1.0 or DPAM authors

**Temporary workaround** (testing only):
```bash
# Skip step 16 and downstream ML steps
dpam run AF-P12345 \
  --working-dir ./work \
  --data-dir /path/to/data \
  --steps PREPARE HHSEARCH FOLDSEEK ... PARSE_DOMAINS
```

### Import Error: tensorflow not found

**Error:** `ImportError: TensorFlow not installed`

**Solution:**
```bash
pip install tensorflow
```

For CPU-only installation:
```bash
pip install tensorflow-cpu
```

### Missing Reference Files

**Error:** `Required file not found: {data_dir}/ECOD_length`

**Solution:**
1. Verify all reference files are present in data directory
2. Check file paths match expected names
3. Ensure files are not empty

### Low Feature Counts

**Warning:** `Step 15 complete: 0 feature rows generated`

**Possible causes:**
- No domains found in step 13
- No overlapping HHsearch and DALI hits
- Missing ECOD maps for template domains

**Check:**
```bash
# Verify step 13 output
cat work/{prefix}.step13_domains

# Verify HHsearch hits
wc -l work/{prefix}.hhsearch_hits

# Verify DALI hits
wc -l work/{prefix}.dali_good_hits
```

### No Merge Candidates

**Info:** `Step 19: No validated merge candidates found`

This is normal when:
- Domains have low overlap on templates
- Support doesn't exceed opposition
- Only single-domain proteins

Not an error - pipeline continues normally.

## Performance Notes

### Resource Requirements

- **Step 15** (Feature extraction): Fast, <1 min, minimal memory
- **Step 16** (TensorFlow inference):
  - Time: ~1-5 seconds per 100 predictions
  - Memory: 500MB-1GB for model
  - CPU: Single-threaded (no GPU needed)
- **Steps 17-24**: Fast, <30 seconds total

### Batch Processing

For large datasets, use batch mode:

```bash
dpam batch prefixes.txt \
  --working-dir ./work \
  --data-dir /path/to/data \
  --cpus 4 \
  --parallel 10 \
  --resume
```

The TensorFlow model loads once per structure, so parallel processing gives near-linear speedup.

## Development Notes

### Adding New Features

To add features to the ML model:

1. Modify `step15_prepare_domass.py` to extract new features
2. Retrain TensorFlow model with updated feature set
3. Update model architecture in `step16_run_domass.py`
4. Update this documentation

### Alternative ML Frameworks

To use PyTorch, scikit-learn, or other frameworks:

1. Create new step16 implementation
2. Keep feature extraction (step 15) unchanged
3. Maintain same output format for step 17 compatibility

## References

- Original DPAM paper: [Add citation]
- ECOD database: http://prodata.swmed.edu/ecod/
- TensorFlow documentation: https://www.tensorflow.org/

## Support

For questions about the ML pipeline:
1. Check this documentation
2. Review `docs/STEP*_IMPLEMENTATION.md` for technical details
3. Open issue at: https://github.com/your-repo/dpam_v2/issues
