# Step 17 Summary: Filter Confident Predictions

**Status:** Complete
**Implementation:** `steps/step17_get_confident.py`
**Lines of Code:** ~190
**Complexity:** Low

---

## Purpose

Filter ML predictions by probability threshold (>=0.6) and assign quality labels based on T-group and H-group consistency. Identifies unambiguous vs ambiguous ECOD classifications for downstream processing.

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step GET_CONFIDENT \
  --working-dir ./work --data-dir ./data
```

### Input
- `{prefix}.step16_predictions` - ML predictions with probabilities (from step 16)

### Output
- `{prefix}.step17_confident_predictions` - High-confidence predictions with quality labels

### Performance
- **Time:** <1 second
- **Memory:** <50 MB

---

## Algorithm

```
1. Load predictions from step 16
2. Group predictions by domain
3. For each domain:
   a. Find best probability per T-group
   b. Find max probability across all T-groups
   c. Identify similar T-groups (within 0.05 of max)
   d. Extract H-groups from similar T-groups
   e. Assign quality label:
      - 'good': Single T-group (unambiguous)
      - 'ok': Multiple T-groups, same H-group (family consensus)
      - 'bad': Multiple conflicting H-groups (ambiguous)
4. Filter predictions by probability >= 0.6
5. Write confident predictions with quality labels
```

---

## Filtering Rules

### Minimum Probability
- **Threshold:** 0.6
- Predictions below 0.6 are excluded

### T-group Similarity Window
- **Window:** 0.05
- T-groups with prob >= (max_prob - 0.05) are considered similar
- Example: If best T-group has prob=0.95, include all with prob>=0.90

---

## Quality Labels

| Label | Condition | Interpretation |
|-------|-----------|----------------|
| `good` | 1 similar T-group | Unambiguous classification |
| `ok` | Multiple T-groups, 1 H-group | Family-level consensus |
| `bad` | Multiple H-groups | Ambiguous classification |

### H-group Extraction
H-group is first two parts of T-group:
```
T-group: 2.30.42 -> H-group: 2.30
T-group: 2.30.18 -> H-group: 2.30 (same)
T-group: 1.10.5  -> H-group: 1.10 (different)
```

---

## Output Format

**File:** `{prefix}.step17_confident_predictions`

**Header:**
```
# domain  domain_range  tgroup  ecod_ref  prob  quality
```

**Example:**
```
# domain	domain_range	tgroup	ecod_ref	prob	quality
D1	10-150	2.30.30	e1abc1	0.9234	good
D1	10-150	2.30.42	e2xyz1	0.8856	ok
D2	160-280	1.10.5	e3def1	0.7512	good
D3	290-400	3.40.50	e4ghi1	0.6234	bad
```

---

## Example Scenarios

### Scenario 1: Good (Unambiguous)
```
D1 predictions:
  T-group 2.30.30: prob=0.95  <- Best
  T-group 1.10.5:  prob=0.45  <- Below threshold (0.90)

Similar T-groups: {2.30.30}
Quality: good
```

### Scenario 2: OK (Same H-group)
```
D2 predictions:
  T-group 2.30.30: prob=0.92  <- Best
  T-group 2.30.42: prob=0.88  <- Within 0.05

Similar T-groups: {2.30.30, 2.30.42}
H-groups: {2.30}  <- Single H-group
Quality: ok
```

### Scenario 3: Bad (Conflicting)
```
D3 predictions:
  T-group 2.30.30: prob=0.85  <- Best
  T-group 1.10.5:  prob=0.82  <- Within 0.05

Similar T-groups: {2.30.30, 1.10.5}
H-groups: {2.30, 1.10}  <- Multiple H-groups
Quality: bad
```

---

## Typical Statistics

### 500-Residue Protein (3 domains)
- **Input predictions:** 200-500 rows
- **Confident (>=0.6):** 100-300 rows
- **Quality distribution:**
  - good: 40-60%
  - ok: 20-30%
  - bad: 10-20%

---

## Quality Implications

| Quality | Downstream Use |
|---------|---------------|
| `good` | Direct ECOD assignment |
| `ok` | Use with family-level confidence |
| `bad` | May need manual review |

---

## Common Issues

### No confident predictions
**Cause:** All predictions below 0.6 threshold
**Check:** Review step 16 output for probability distribution

### All predictions marked 'bad'
**Cause:** Many competing H-groups with similar probabilities
**Note:** May indicate multi-domain or novel fold

### Few 'good' predictions
**Cause:** Multiple strong T-group hits per domain
**Note:** Normal for well-conserved folds

---

## Key Functions

```python
def run_step17(prefix, working_dir, path_resolver=None, **kwargs) -> bool
    # path_resolver: Optional PathResolver for sharded output layout.
```

---

## Backward Compatibility

**100% v1.0 compatible**
- Probability threshold: 0.6 (exact)
- Similarity window: 0.05 (exact)
- Quality label logic (exact)
- Output format (exact)

---

## Quick Commands

```bash
# Run step 17
dpam run-step AF-P12345 --step GET_CONFIDENT \
  --working-dir ./work --data-dir ./data

# Check output
head work/AF-P12345.step17_confident_predictions | column -t

# Count by quality
grep -v "^#" work/AF-P12345.step17_confident_predictions | \
  cut -f6 | sort | uniq -c

# High confidence only
awk -F'\t' '$5 >= 0.8' work/AF-P12345.step17_confident_predictions
```

---

## Summary

Step 17 filters predictions by probability threshold and assigns quality labels.

**Key metrics:**
- 190 lines of code
- <1s execution time
- Probability threshold: 0.6
- Similarity window: 0.05
- 3 quality labels: good/ok/bad
- Ready for alignment mapping (step 18)
