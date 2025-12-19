# Step 13 v1.0 Compatibility Fixes

## Summary

Updated `dpam/steps/step13_parse_domains.py` to match v1.0 13-step reference implementation exactly.

**Date**: 2025-10-18
**Reference**: `~/dev/DPAM/old_v1.0/v1.0/step13_parse_domains.py`

---

## Critical Bugs Fixed

### 1. ⚠️ Missing Sequence Separation Filter (+5 bug)

**Impact**: MASSIVE - caused incorrect merging by including nearby residues

**Fix**: Added filter in `calculate_segment_pair_prob()` (line 628)

```python
# BEFORE (BUG):
for res1 in seg1:
    for res2 in seg2:
        total += get_prob(prob_matrix, res1, res2)  # Includes ALL pairs!

# AFTER (CORRECT):
for res1 in seg1:
    for res2 in seg2:
        if res1 + 5 < res2 or res2 + 5 < res1:  # Only pairs ≥5 apart
            total += get_prob(prob_matrix, res1, res2)
```

This was preventing proper domain separation by inflating similarity scores with
probabilities from residues close in sequence (which are naturally close in structure).

---

## Probability Table Updates

Replaced all four probability lookup tables with exact v1.0 values:

### PDB Distance (lines 35-84)
- Fixed bin boundaries (e.g., ≤9 instead of ≤8, ≤10)
- Fixed probability values (e.g., 0.93 instead of 0.88 at ≤9Å)
- Added missing bins (≤21, ≤27, ≤45, ≤55, ≤70, ≤120, ≤160)

### PAE Error (lines 87-134)
- Fixed to be more conservative (e.g., 0.61 instead of 0.74 at ≤5Å)
- Added missing bin (≤11)
- Matches v1.0 exactly

### HHsearch Score (lines 137-158)
- Simplified from 11 bins to 7 bins
- Added ≥110 bin (0.87)
- Removed granular bins (≥90, ≥80, ≥70, ≥60)
- Matches v1.0 exactly

### DALI Z-score (lines 161-194)
- Added finer granularity (≥11, ≥9, ≥7)
- Fixed probability values (e.g., 0.83 instead of 0.81 at ≥16)
- Matches v1.0 exactly

---

## Algorithm Changes

### 2. Removed T-group Constraints (NOT IN v1.0)

**Impact**: MAJOR - T-group logic was preventing merges that v1.0 would allow

**Changes**:
- Removed `apply_consensus_filter()` function
- Removed `get_dominant_tgroup()` function
- Removed `segments_share_tgroup()` function
- Simplified `load_good_domains()` to not track T-groups (lines 290-339)
- Updated `merge_segments_by_probability()` to remove T-group check (lines 505-542)
- Updated `iterative_clustering()` to remove T-group check (lines 561-600)

**Rationale**: T-group constraints were a v2.0 enhancement not present in v1.0.
While conceptually sound (prevent cross-domain merging), they caused validation
failures when comparing against v1.0 outputs.

### 3. Fixed Gap Filling Logic (lines 603-652)

**BEFORE**: Simple distance-based filling
```python
if res - new_domain[-1] <= gap_tolerance + 1:
    fill_gap()
```

**AFTER**: v1.0 segment-based filling
```python
# Split into consecutive segments
# For each gap between segments:
if len(interseg) <= 10:
    fill_gap()
```

Matches v1.0 lines 614-643 exactly.

### 4. Fixed Overlap Removal Logic (lines 655-701)

**BEFORE**: Remove overlapping residues, keep if ≥15 unique
```python
unique_resids = [res for res in domain if res not in overlap_resids]
if len(unique_resids) >= 15:
    keep_domain()
```

**AFTER**: v1.0 segment-based removal
```python
# For each domain:
#   Find residues in other domains
#   Split into segments
#   Keep segments with ≥15 non-overlapping residues
#   Keep domain if total ≥20 residues
```

Matches v1.0 lines 645-672 exactly.

---

## Formula Verification

### Probability Combination (ALREADY CORRECT)

Current formula matches v1.0 line 432:
```python
total_prob = dist_prob ** 0.1 * error_prob ** 0.1 * hhpro_prob ** 0.4 * daliz_prob ** 0.4
```

**Weights**: 10% PDB distance, 10% PAE, 40% HHsearch, 40% DALI

Note: dpam_automatic uses different formula (equal 25% weights) - we match 13-step v1.0.

### Merging Thresholds (ALREADY CORRECT)

- Initial merge: `prob > 0.54` (v1.0 line 497)
- Iterative merge: `inter_prob * 1.07 >= min_intra` (v1.0 line 546)

---

## Files Modified

1. `dpam/steps/step13_parse_domains.py` - All fixes applied
2. `docs/STEP13_DIVERGENCE_ANALYSIS.md` - Analysis of all three versions
3. `docs/STEP13_V1_FIXES.md` - This document

---

## Testing Recommendations

1. **Unit tests**: Test probability tables with known inputs
2. **Integration tests**: Compare outputs against v1.0 reference on validation set
3. **Regression tests**: Verify known good cases (O33946, O66611, etc.)

### Test Cases

Run on validation proteins:
```bash
# Known v1.0 outputs exist for these
dpam run-step Q99344 --step PARSE_DOMAINS --working-dir test_v1_match/
dpam run-step O33946 --step PARSE_DOMAINS --working-dir test_v1_match/
dpam run-step O66611 --step PARSE_DOMAINS --working-dir test_v1_match/
```

Compare `.finalDPAM.domains` files:
```bash
diff test_v1_match/Q99344.finalDPAM.domains v1_reference/Q99344.finalDPAM.domains
```

---

## Expected Impact

### Should Now Match v1.0 On:
- ✅ Probability calculations (exact tables)
- ✅ Segment pair filtering (+5 separation)
- ✅ Merging logic (no T-group constraints)
- ✅ Gap filling (segment-based)
- ✅ Overlap removal (segment-based)

### Known Remaining Differences:
- None expected - implementation should be byte-for-byte equivalent to v1.0

### Possible Edge Cases:
- Floating point precision differences (unlikely)
- Order of iteration in dictionaries (Python 3.7+ guarantees insertion order)
- Numerical rounding in probability calculations

---

## Future Enhancements (v2.0+)

The T-group constraint logic could be valuable as a future enhancement:

**Benefits**:
- Prevents inappropriate merging across domain boundaries
- Uses biological knowledge (ECOD T-group assignments)
- Adds consensus filtering to reduce noise

**Drawbacks**:
- More conservative - may under-merge in overlap regions
- Requires careful tuning of consensus thresholds

If re-implementing T-group constraints:
1. Make it optional (`--use-tgroup-constraints` flag)
2. Benchmark against known multi-domain proteins
3. Validate against ECOD domain assignments
4. Document as v2.0 feature, not v1.0 compatible

---

## Validation Checklist

- [x] Probability tables match v1.0 exactly
- [x] +5 sequence separation filter added
- [x] T-group constraints removed
- [x] Gap filling matches v1.0 logic
- [x] Overlap removal matches v1.0 logic
- [ ] Unit tests pass (TODO: create tests)
- [ ] Integration tests pass (TODO: run validation set)
- [ ] Known good cases reproduce v1.0 outputs

---

## References

- v1.0 reference: `~/dev/DPAM/old_v1.0/v1.0/step13_parse_domains.py`
- dpam_automatic: `~/dev/dpam_automatic/step14_parse_domains.py`
- Divergence analysis: `docs/STEP13_DIVERGENCE_ANALYSIS.md`
