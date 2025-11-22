# Step 19 ECOD_length Column Bug Fix

**Date**: 2025-11-22
**Issue**: Step 19 parsing ECOD_length with wrong column index
**Status**: ✅ **FIXED**

## Problem Statement

Step 19 failed to identify **ANY** merge candidates due to parsing the ECOD_length file with the wrong column index. This completely broke discontinuous domain formation, affecting ~30-40% of all protein domains.

### Impact

**Severity**: 🔴 **CRITICAL** - Prevents all discontinuous domain formation

- **Affected Domains**: Rossmann folds, jelly-roll folds, split β-barrels (~30-40% of ECOD)
- **Symptom**: Step 19 reports "No ECOD hits found" even with valid Step 18 mappings
- **Result**: Discontinuous domains never merged, remain as separate compact domains
- **Validation Impact**: Cannot compare dpam_c2 against BFVD reference data

### Example Bug Behavior

**Validation Protein**: A0A1D6Y707 (Rossmann fold dehydrogenase)

**Original DPAM (BFVD reference):**
```
nD5: 16-95,501-680    T-group: 2004.1.1 (Rossmann)    prob: 0.980
```
Correctly identified discontinuous domain spanning 485 residues.

**dpam_c2 (BEFORE FIX):**
```
D1:  1-90        T-group: 2004.1.1 (Rossmann)    prob: 0.674
D8:  546-675     T-group: 2004.1.1 (Rossmann)    prob: 0.986
```
Both segments hit same Rossmann fold but remained separate (no merging).

**Step 19 log output:**
```
[INFO] dpam.steps.step19_get_merge_candidates: No ECOD hits found for A0A1D6Y707
```

Despite Step 18 producing valid mappings with ECOD hits, Step 19 found ZERO hits.

## Root Cause

### ECOD_length File Format

```bash
$ head -5 /home/rschaeff/data/dpam_reference/ecod_data/ECOD_length
000000003	e2rspA1	124
000000017	e2pmaA1	141
000000020	e1eu1A1	155
```

**Column Layout:**
- **Column 0**: Numeric UID (internal database ID) - e.g., `000000003`
- **Column 1**: ECOD domain ID (what Step 18 outputs) - e.g., `e2rspA1`
- **Column 2**: Domain length - e.g., `124`

### Bug in Step 19

**File**: `dpam/steps/step19_get_merge_candidates.py`

**Lines 117-126 (BUGGY CODE):**
```python
# Load ECOD lengths
ecod_lengths = {}

with open(ecod_length_file, 'r') as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) >= 3:
            ecod_id = parts[0]  # ← BUG: Reads numeric UID (000000003)
            length = int(parts[2])
            ecod_lengths[ecod_id] = length
```

**Result**: `ecod_lengths` dict has keys like `"000000003"`, `"000000017"` (numeric UIDs).

**Lines 148-172 (Mappings processing):**
```python
ecod_id = parts[2]  # Step 18 outputs domain IDs like "e3qf7A1"

# ...

# Calculate weighted coverage
if ecod_id in ecod_lengths:  # ← ALWAYS FALSE
    ecod_length = ecod_lengths[ecod_id]
    # ... coverage calculation
```

**Result**: Lookup `"e3qf7A1" in ecod_lengths` fails because dict has numeric UIDs, not domain IDs.

**Lines 214-216 (Early exit):**
```python
if not ecod_to_hits:
    logger.info(f"No ECOD hits found for {prefix}")
    return True
```

Since `ecod_lengths` lookup always fails, no hits pass validation, `ecod_to_hits` remains empty, causing early exit with "No ECOD hits found".

## Solution

### One-Line Fix

**File**: `dpam/steps/step19_get_merge_candidates.py`

**Line 124 - Changed:**
```python
ecod_id = parts[0]  # WRONG - numeric UID
```

**To:**
```python
ecod_id = parts[1]  # CORRECT - ECOD domain ID (matches Step 18 output)
```

### Complete Fixed Section (Lines 117-127):

```python
# Load ECOD lengths
ecod_lengths = {}

with open(ecod_length_file, 'r') as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) >= 3:
            ecod_id = parts[1]  # Fixed: ECOD ID is in column 1, not 0
            length = int(parts[2])
            ecod_lengths[ecod_id] = length
```

## Validation

### Regression Tests

**File**: `tests/integration/test_step19_get_merge_candidates.py`

Added two critical regression tests:

#### 1. Column Mapping Verification

```python
def test_step19_ecod_length_column_mapping(self, tmp_path):
    """
    Regression test: Verify ECOD_length uses correct column for ECOD ID.

    Bug: Step 19 was reading column 0 (numeric UID) instead of column 1 (ECOD ID),
    causing 100% failure in finding ECOD hits.
    """
    # Create ECOD_length file with realistic format
    ecod_length_file.write_text(
        "000000003\te2rspA1\t124\n"
        "001288642\te4cxfA2\t191\n"
    )

    # Verify correct parsing
    assert "e4cxfA2" in ecod_lengths  # ECOD ID from column 1
    assert "001288642" not in ecod_lengths  # NOT numeric UID from column 0
```

#### 2. Discontinuous Domain Detection

```python
def test_step19_finds_merge_candidates_with_correct_column(self, ...):
    """
    Regression test: Verify Step 19 finds merge candidates when ECOD_length is parsed correctly.

    Bug: With column 0 parsing, reports "No ECOD hits found" even with valid mappings.
    Fix: With column 1 parsing, correctly identifies discontinuous domain pairs.
    """
    # Setup: Two domains hitting same ECOD template (e4cxfA2)
    (working_dir / f"{test_prefix}.step18_mappings").write_text(
        "D1\t10-90\te4cxfA2\t2004.1.1\t0.950\tgood\tna\t1-80\n"
        "D8\t546-675\te4cxfA2\t2004.1.1\t0.986\tgood\tna\t100-191\n"
    )

    success = run_step19(...)

    # CRITICAL: Should find merge candidates
    assert output_file.exists(), "Should create output (not 'No ECOD hits found')"
    assert len(lines) >= 2, "Should find D1 + D8 merge candidate"

    # Verify D1 and D8 are identified as merge candidates
    assert "D1" in domains_in_merge and "D8" in domains_in_merge
```

**Test Results**: ✅ All 8 Step 19 tests pass

```bash
$ pytest tests/integration/test_step19_get_merge_candidates.py -v
============================== 8 passed ==============================
```

### Also Fixed: Test Fixture

The test fixture was also creating incorrect ECOD_length format:

**Before (WRONG):**
```python
ecod_length_file.write_text("e001 domain1 100\ne002 domain2 150\n")
```

**After (CORRECT):**
```python
ecod_length_file.write_text("000001\te001\t100\n000002\te002\t150\n")
```

## Expected Impact

### Before Fix

- **Merge Candidates**: 0 (always "No ECOD hits found")
- **Discontinuous Domains**: 0% success rate
- **Rossmann Folds**: Incorrectly split into separate N/C-terminal domains
- **Validation**: Cannot compare to BFVD reference data

### After Fix

- **Merge Candidates**: Correctly identified based on shared ECOD templates
- **Discontinuous Domains**: Should match original DPAM architecture
- **Example (A0A1D6Y707)**:
  - Step 19: Identifies D1 + D8 sharing e3qf7A1 template
  - Step 22: Merges → "1-90,546-675" (discontinuous Rossmann)
  - Step 23: Single assignment to 2004.1.1 (prob ~0.98)
- **Validation**: Can now directly compare to BFVD reference data

### Affected Protein Families

Now correctly handles:
- **Rossmann folds** (NAD/FAD binding domains)
- **Jelly-roll folds** (viral capsid proteins)
- **Immunoglobulin-like domains**
- **Split β-barrel domains**

These represent **~30-40% of all protein domains** in ECOD.

## Related Bugs

This is **Bug #4** discovered during BFVD validation:

1. ✅ **Step 18/23 Parser Bugs** (commit 61da271)
   - Fixed HHsearch parser and DALI column mapping
   - Fixed ECOD_length column in Step 23

2. ✅ **Step 9/15 Filtering Bugs** (commit 762059f)
   - Removed aggressive HHsearch filter causing 65-90% assignment failure
   - Fixed .pop() mutation bug in consensus mapping

3. ✅ **Step 23 Multiple Assignments Bug** (commit ed8b983)
   - Select single best ECOD per domain
   - Maintain 1:1 domain-to-ECOD mapping

4. ✅ **Step 19 ECOD_length Column Bug** (this fix)
   - Parse column 1 (ECOD ID) instead of column 0 (numeric UID)
   - **Enables discontinuous domain formation for first time in dpam_c2**

## Comparison with Step 23

**Step 23 already had this bug FIXED** (commit 61da271):

**File**: `dpam/steps/step23_get_predictions.py`

**Lines 126-134:**
```python
# Load ECOD lengths
ecod_lengths = {}

with open(ecod_length_file, 'r') as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) >= 3:
            ecod_id = parts[1]  # Fixed: ECOD ID is in column 1, not 0
            length = int(parts[2])
            ecod_lengths[ecod_id] = length
```

Comment explicitly documents the fix, but **Step 19 still had the old broken code** until now.

## Testing Checklist

- [x] Unit test verifies correct column parsing
- [x] Integration test verifies merge candidate detection
- [x] Test verifies discontinuous domain pairs identified (D1 + D8)
- [x] All existing Step 19 tests still pass
- [x] Test fixture corrected to use proper ECOD_length format
- [x] Code matches Step 23 corrected implementation

## Migration Notes

**No migration required** - This is a pure bug fix. Existing Step 19 outputs (if any) should be regenerated.

**To regenerate from Step 19:**
```bash
# Delete old buggy outputs
rm work/*.step19_merge_candidates
rm work/*.step19_merge_info
rm work/*.step22_merged_domains
rm work/*.step23_predictions

# Re-run from step 19
dpam run-step PROTEIN_ID --step GET_MERGE_CANDIDATES --working-dir work --data-dir data
```

## Priority

**CRITICAL** - This bug was blocking all discontinuous domain formation, making dpam_c2 validation impossible for ~40% of proteins. Fix enables:

- First-time discontinuous domain support in dpam_c2
- BFVD validation comparison on full protein set
- Rossmann fold and split domain detection
- Complete ML pipeline validation (Steps 15-24)

## Next Steps

1. ✅ Apply Step 19 fix (complete)
2. ✅ Add regression tests (complete)
3. ⏭️ Re-run BFVD validation (20 proteins)
4. ⏭️ Verify discontinuous domains are correctly merged
5. ⏭️ Compare final assignments to BFVD reference data

## Discovery Notes

This bug was discovered through systematic comparison of dpam_c2 output with original DPAM/BFVD database for protein A0A1D6Y707. The iterative validation approach (run → observe → compare → fix → repeat) successfully identified the root cause after noticing:

1. Step 18 generates valid ECOD mappings
2. Step 19 reports "No ECOD hits found"
3. Step 23 uses correct column parsing (already fixed)
4. Step 19 still uses wrong column parsing (← this bug)

The fix is trivial (one line change), but the impact is massive - **enables discontinuous domain formation for the first time in dpam_c2**.
