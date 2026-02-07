# Step 23 Summary: Get Predictions (Classify Domains)

**Status:** Complete
**Implementation:** `steps/step23_get_predictions.py`
**Lines of Code:** ~490
**Complexity:** High

---

## Purpose

Classify merged and single domains as "full", "part", or "miss" based on ML probability
and template coverage. Uses position-specific weights for coverage calculation.

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step GET_PREDICTIONS \
  --working-dir ./work --data-dir ./data
```

### Input
- `{prefix}.step22_merged_domains` - Merged domain groups
- `{prefix}.step13_domains` - Original parsed domains
- `{prefix}.step16_predictions` - ML predictions
- `{prefix}.step18_mappings` - Template alignments
- `tgroup_length` - Average T-group lengths (reference)
- `ECOD_length` - Template lengths (reference)
- `posi_weights/*.weight` - Position-specific weights (reference)

### Output
- `{prefix}.step23_predictions` - Domain classifications

### Performance
- **Time:** 1-5 seconds
- **Memory:** <100 MB

---

## Classification Logic (V1-compatible)

### Decision Tree
```
If dpam_prob >= 0.85:
    If (weighted_ratio >= 0.66 OR length_ratio >= 0.66):
        If (weighted_ratio >= 0.33 AND length_ratio >= 0.33):
            classification = "full"
        Else:
            classification = "part"
    Elif (weighted_ratio >= 0.33 OR length_ratio >= 0.33):
        classification = "part"
    Else:
        classification = "miss"
Else:
    classification = "miss"
```

### Thresholds Summary

| Classification | dpam_prob | weighted_ratio | length_ratio |
|---------------|-----------|----------------|--------------|
| **full** | >= 0.85 | (>=0.66 OR other>=0.66) AND both>=0.33 |
| **part** | >= 0.85 | >=0.33 OR other>=0.33 |
| **miss** | < 0.85 | OR both < 0.33 |

---

## Algorithm

```
1. Load merged domain groups from step 22
2. Identify single (non-merged) domains from step 13
3. For each final domain (merged or single):
   a. Collect all ECOD predictions for member domains
   b. Keep best prediction per ECOD ID (by dpam_prob)
   c. For each ECOD candidate:
      - Calculate weighted coverage from position weights
      - Calculate length ratio from T-group average
      - Classify based on probability and ratios
   d. Select best classification (prefer full > part > miss)
4. Write single best match per domain
```

---

## Coverage Calculation

### Weighted Coverage Ratio
```python
# Load position-specific weights
pos_weights, total_weight = load_position_weights(ecod_id, weights_dir)

# Calculate covered weight
covered_weight = sum(pos_weights[res] for res in template_resids)

# Ratio
weighted_ratio = covered_weight / total_weight
```

### Length Ratio
```python
# From T-group average length
if tgroup in tgroup_lengths:
    length_ratio = domain_length / tgroup_lengths[tgroup]
else:
    length_ratio = len(template_resids) / ecod_length
```

### Template Residue Selection (V1 Logic)
```python
# Use DALI only if it covers >50% of HH residues
if len(dali_resids) > len(hh_resids) * 0.5:
    template_resids = dali_resids
else:
    template_resids = hh_resids
```

---

## Output Format

**File:** `{prefix}.step23_predictions`

**Header:**
```
# classification	domain	range	ecod	tgroup	dpam_prob	hh_prob	dali_zscore	weighted_ratio	length_ratio	quality
```

**Format:** Tab-delimited, 11 columns
```
{class}<TAB>{domain}<TAB>{range}<TAB>{ecod}<TAB>{tgroup}<TAB>{dpam_prob}<TAB>{hh_prob}<TAB>{dali_zscore}<TAB>{weighted_ratio}<TAB>{length_ratio}<TAB>{quality}
```

**Example:**
```
full	D1,D2	10-150	e2rspA1	1.1.1	0.950	9.52	25.3	0.850	0.920	good
part	D3	200-280	e3dkrA1	2.3.1	0.870	8.85	18.5	0.450	0.380	ok
miss	D4	300-350	na	na	na	na	na	na	na	na
```

---

## Quality Values

From Step 18 mappings:
- **good**: High-quality alignment
- **ok**: Moderate-quality alignment
- **bad**: Low-quality alignment
- **na**: No mapping available

For merged domains, best quality is selected (good > ok > bad).

---

## Key Functions

### `load_position_weights(ecod_id, weights_dir, ecod_length)`
Load position-specific weights for ECOD template.
Returns dict of residue -> weight and total weight.

### `run_step23(prefix, working_dir, data_dir, path_resolver=None, **kwargs) -> bool`
Main classification function. `path_resolver`: Optional PathResolver for sharded output layout.
Processes merged and single domains.

---

## Typical Statistics

### 500-Residue Protein
- **Domains classified:** 3-8
- **Full:** 40-60%
- **Part:** 20-40%
- **Miss:** 10-30%

---

## Common Issues

### Missing reference data
**Cause:** tgroup_length or ECOD_length not in data_dir
**Fix:** Verify data directory contents

### All "miss" classifications
**Cause:** Low ML probabilities or poor coverage
**Check:** Review step16_predictions and step18_mappings

### No predictions for domain
**Cause:** Domain not in step16_predictions
**Result:** Written as "miss" with "na" values

---

## Backward Compatibility

100% V1-compatible
- Probability threshold: 0.85 (exact)
- Coverage thresholds: 0.66/0.33 (exact)
- Template selection logic (DALI >50% of HH)
- Quality precedence (good > ok > bad)
- Output format matches

---

## Quick Commands

```bash
# Run step 23
dpam run-step AF-P12345 --step GET_PREDICTIONS \
  --working-dir ./work --data-dir ./data

# Check output
cat work/AF-P12345.step23_predictions

# Count by classification
cut -f1 work/AF-P12345.step23_predictions | grep -v "^#" | sort | uniq -c

# Show full predictions
grep "^full" work/AF-P12345.step23_predictions
```

---

## Summary

Step 23 is **complete** and classifies domains.

**Key metrics:**
- 490 lines of code
- 1-5s execution time
- V1-compatible classification logic
- Position-weighted coverage calculation
- Three-tier classification: full/part/miss
- Outputs classifications for Step 24 refinement
