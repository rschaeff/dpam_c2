# Step 23 Multiple Assignments Bug Fix

**Date**: 2025-01-22
**Issue**: Step 23 outputting multiple ECOD assignments per domain
**Status**: ✅ **FIXED**

## Problem Statement

Step 23 was outputting **all possible ECOD family assignments** for each parsed domain instead of selecting the **single best assignment**. This resulted in domains receiving 10-30 different ECOD assignments, breaking the expected 1:1 mapping between domains and ECOD classifications.

### Impact

**Severity**: 🔴 **CRITICAL** - Breaks downstream analysis

- **Validation Example**: Domain D8 (546-675) in protein A0A1D6Y707 received **23 different ECOD assignments**
- **Expected Behavior**: 1 assignment per domain (1:1 mapping)
- **Actual Behavior**: All ECODs that passed classification thresholds were output
- **Downstream Effect**: Step 24 integrates all assignments, producing nonsensical multi-family domain annotations

### Example Bug Output

```
# From A0A1D6Y707.step23_predictions (WRONG)
full    D8  546-675    e4cxfA2    101.1.1    0.950    ...
full    D8  546-675    e6dxoA2    101.1.1    0.945    ...
full    D8  546-675    e2rspA1    101.1.1    0.940    ...
full    D8  546-675    e3fxgA1    101.1.1    0.935    ...
... (19 more lines for D8) ...
```

**Expected**: Only ONE line for D8 (the best match: e4cxfA2)

## Root Cause

### Code Location

`dpam/steps/step23_get_predictions.py`:
- **Merged domains**: Lines 249-304 (OLD)
- **Single domains**: Lines 328-381 (OLD)

### Bug Pattern

Both sections used a loop that output **all ECODs** that passed validation:

```python
# BUG: Outputs ALL ECODs
for ecod, pred in ecod_to_best.items():
    if ecod not in ecod_lengths:
        continue

    # Calculate coverage, classify...

    # Output this ECOD (WRONG: outputs all, not just best)
    results.append(f"{classification}\t{domain}\t...")
```

This loop iterates through **all ECODs** and outputs **every one** that has valid length data and mappings. No selection logic was present.

## Solution

### Selection Algorithm

Implemented the original DPAM v1.0 selection logic:

1. **Sort ECODs** by probability (descending) to prioritize best matches
2. **Find best candidates** of each type while iterating:
   - `best_full`: First ECOD with classification "full"
   - `best_part`: First ECOD with classification "part"
   - `best_miss`: First ECOD with classification "miss"
3. **Select single best**: `best_full OR best_part OR best_miss`
4. **Output exactly ONE** line per domain

### Fixed Code Pattern

```python
# Sort by probability to prioritize best matches
sorted_ecods = sorted(
    ecod_to_best.items(),
    key=lambda x: x[1]['dpam_prob'],
    reverse=True
)

# Find best candidate of each type
best_full = None
best_part = None
best_miss = None

for ecod, pred in sorted_ecods:
    # Calculate coverage, classify...

    # Keep best candidate of each type
    if classification == 'full' and best_full is None:
        best_full = candidate
    elif classification == 'part' and best_part is None:
        best_part = candidate
    elif best_miss is None:
        best_miss = candidate

# Output single best match (prefer full > part > miss)
best_candidate = best_full or best_part or best_miss
if best_candidate:
    results.append(f"{classification}\t{domain}\t...")
```

### Changes Made

**File**: `dpam/steps/step23_get_predictions.py`

1. **Merged domains section** (lines 228-334):
   - Added ECOD sorting by probability
   - Added best_full/best_part/best_miss tracking
   - Output only single best candidate

2. **Single domains section** (lines 336-441):
   - Added ECOD sorting by probability
   - Added best_full/best_part/best_miss tracking
   - Output only single best candidate

## Validation

### Regression Test

**File**: `tests/integration/test_step23_get_predictions.py`

Added `test_step23_single_assignment_per_domain()`:

```python
def test_step23_single_assignment_per_domain(self, ...):
    """
    Regression test: Verify Step 23 outputs exactly ONE ECOD assignment per domain.

    Bug: Step 23 was outputting ALL ECOD predictions that passed thresholds
    instead of selecting the SINGLE BEST assignment per domain.
    """
    # Setup: D1 with 5 ECODs, D2 with 3 ECODs, D3 with 1 ECOD

    # Run step 23
    success = run_step23(...)

    # CRITICAL: Each domain should have exactly ONE assignment
    assert len(domain_assignments['D1']) == 1  # Not 5!
    assert len(domain_assignments['D2']) == 1  # Not 3!
    assert len(domain_assignments['D3']) == 1

    # Verify correct ECOD selected (best "full" > best "part" > best "miss")
    assert d1_ecod == 'e1_best_full'  # Highest prob full match
    assert d2_ecod == 'e2_best_part'   # No full match, highest prob part
```

**Test Results**: ✅ All tests pass

```bash
$ pytest tests/integration/test_step23_get_predictions.py -v
============================== 8 passed ==============================
```

### Before/After Comparison

**Test Case**: Domain D1 with 5 ECOD predictions

| Metric | Before (BUG) | After (FIXED) |
|--------|--------------|---------------|
| Output lines for D1 | 5 | 1 |
| Selected ECOD | ALL | e1_best_full |
| Classification | 2 full, 2 part, 1 miss | 1 full |
| Domain-to-ECOD mapping | 1:5 (WRONG) | 1:1 (CORRECT) |

## Expected Impact

### Assignment Quality

- **Before fix**: Domains get 10-30 ECOD assignments (nonsensical)
- **After fix**: Each domain gets **exactly 1** ECOD assignment (correct)

### Validation Improvement

Assuming validation protein A0A1D6Y707:
- **Before**: Domain D8 → 23 ECOD assignments (unusable)
- **After**: Domain D8 → 1 ECOD assignment (e4cxfA2, highest probability)

### Downstream Steps

Step 24 (INTEGRATE_RESULTS) will now receive clean 1:1 mappings instead of multi-assignment noise.

## Related Issues

This is the **third critical bug** fixed in the ML pipeline (Steps 15-24):

1. ✅ **Step 18/23 Parser Bugs** (commit 61da271)
   - Fixed HHsearch parser to use proper parser function
   - Fixed DALI column mapping (column 2 instead of 1)
   - Fixed ECOD_length column mapping (column 1 instead of 0)

2. ✅ **Step 9/15 Filtering Bugs** (commit 762059f)
   - Removed aggressive HHsearch filter causing 65-90% assignment failure
   - Fixed .pop() mutation bug in consensus mapping

3. ✅ **Step 23 Multiple Assignments Bug** (this fix)
   - Select single best ECOD per domain
   - Prefer full > part > miss
   - Maintain 1:1 domain-to-ECOD mapping

## Testing Checklist

- [x] Unit tests pass for helper functions
- [x] Integration test verifies single assignment per domain
- [x] Test verifies correct ECOD selection (best full > part > miss)
- [x] Test verifies sorting by probability
- [x] All existing Step 23 tests still pass
- [x] Code matches original DPAM v1.0 selection logic

## Migration Notes

**No migration required** - This is a pure bug fix. Existing Step 23 outputs should be regenerated to get correct 1:1 assignments.

**To regenerate**:
```bash
# Delete old buggy output
rm work/*.step23_predictions

# Re-run from step 23
dpam run-step PROTEIN_ID --step GET_PREDICTIONS --working-dir work --data-dir data
```

## References

- Original bug report: `/home/rschaeff/work/gvd/validation/DPAM_C2_STEP23_BUG_REPORT.md`
- Validation protein: A0A1D6Y707 (domain D8 had 23 assignments)
- Original DPAM v1.0: `dpam_ml/step23_get_predictions.py` (selection logic reference)
