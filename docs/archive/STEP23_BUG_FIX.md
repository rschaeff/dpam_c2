# Step 23 Bug Fix: Empty Predictions Output

**Date:** 2025-11-19
**Issue:** Steps 23 and 24 produced empty output (header only, 0 predictions)
**Impact:** Critical - broke final domain quality classification pipeline
**Status:** ✅ Fixed with regression tests

## Problem Summary

The user reported that Step 23 was producing only header lines with no data, even when Step 17 successfully generated confident ECOD predictions. This caused Step 24 to fail with "No results to integrate" messages.

Example:
```bash
# Step 17: 83 confident predictions ✓
$ wc -l UHGV-0067376_2.step17_confident_predictions
84 UHGV-0067376_2.step17_confident_predictions

# Step 23: Only header, 0 predictions ✗
$ wc -l UHGV-0067376_2.step23_predictions
1 UHGV-0067376_2.step23_predictions
```

## Root Causes

Three distinct bugs in the Step 17 → Step 18 → Step 23 pipeline:

### Bug 1: Step 18 HHsearch Parser (CRITICAL)

**File:** `dpam/steps/step18_get_mapping.py` lines 147-166
**Problem:** Step 18 tried to parse raw HHsearch output (`.hhsearch`) as tab-delimited data instead of using the proper parser.

```python
# WRONG: Trying to read native HHsearch format as TSV
with open(hhsearch_file, 'r') as f:
    for line in f:
        parts = line.strip().split('\t')  # ❌ HHsearch uses spaces, not tabs
        if len(parts) < 14:
            continue
```

**Impact:** 0 HHsearch hits loaded (expected ~1800+)

**Fix:** Use `parse_hhsearch_output()` from `dpam/io/parsers.py`:

```python
from dpam.io.parsers import parse_hhsearch_output

# CORRECT: Use proper parser
hhsearch_alignments = parse_hhsearch_output(hhsearch_file)
for aln in hhsearch_alignments:
    query_resids = set(range(aln.query_start, aln.query_end + 1))
    template_resids = list(range(aln.template_start, aln.template_end + 1))
    hhsearch_hits.append({
        'ecod': aln.hit_id,
        'prob': aln.probability / 100.0,
        'query_resids': query_resids,
        'template_resids': template_resids,
    })
```

**Result:** Now loads 1824 HHsearch alignments correctly

### Bug 2: Step 18 DALI Column Mapping

**File:** `dpam/steps/step18_get_mapping.py` line 181
**Problem:** ECOD ID read from wrong column (column 1 instead of column 2)

DALI good_hits format:
```
hitname       ecodnum    ecodkey    hgroup  zscore ...
001288642_1   001288642  e4cxfA2    101.1   9.0    ...
              ↑ col 1    ↑ col 2
              (number)   (ECOD ID) ← Need this!
```

**Wrong code:**
```python
ecod_id = parts[1]  # ❌ Gets ecodnum (001288642) instead of ecodkey
```

**Fixed code:**
```python
ecod_id = parts[2]  # ✓ Gets ecodkey (e4cxfA2)
```

**Result:** Now correctly matches 382 DALI hits by ECOD ID

### Bug 3: Step 23 ECOD_length Column Mapping (CRITICAL)

**File:** `dpam/steps/step23_get_predictions.py` line 132
**Problem:** ECOD ID read from wrong column (column 0 instead of column 1)

ECOD_length format:
```
000000003  e2rspA1  124
↑ col 0    ↑ col 1  ↑ col 2
(number)   (ID)     (length)
           ← Need this!
```

**Wrong code:**
```python
ecod_id = parts[0]  # ❌ Gets ECOD number (000000003)
length = int(parts[2])
ecod_lengths[ecod_id] = length
```

This caused **all 422 ECOD predictions to be filtered out** because none matched the numeric keys.

**Fixed code:**
```python
ecod_id = parts[1]  # ✓ Gets ECOD ID (e2rspA1)
length = int(parts[2])
ecod_lengths[ecod_id] = length
```

**Result:** Now finds all 422 ECOD IDs in reference data (was 0/422)

## Data Flow Analysis

### Before Fix
```
Step 17: 83 confident predictions
    ↓
Step 18: Load HHsearch hits → 0 loaded (parser bug)
         Load DALI hits → 382 loaded but wrong IDs (column bug)
         Result: All mappings have 'na\tna' template ranges
    ↓
Step 23: Load ECOD lengths → 0 matches (column bug)
         Filter predictions → All filtered out (no ECOD matches)
         Write output → Header only (0 predictions)
    ↓
Step 24: No results to integrate
```

### After Fix
```
Step 17: 83 confident predictions
    ↓
Step 18: Load HHsearch hits → 1824 loaded ✓
         Load DALI hits → 382 loaded with correct IDs ✓
         Result: Mappings have actual template ranges
    ↓
Step 23: Load ECOD lengths → 422/422 matches ✓
         Filter predictions → 83 predictions kept ✓
         Classify → full/part/miss based on coverage ✓
         Write output → 83 predictions written ✓
    ↓
Step 24: Integrates 83 results successfully ✓
```

## Validation

### Test Case: UHGV-0067376_2 (gut virome protein)

**Before:**
- Step 18 mappings: 83 lines, all with `na\tna` template ranges
- Step 23 predictions: 1 line (header only)
- Step 24: "No results to integrate"

**After:**
- Step 18 mappings: 83 lines with DALI template ranges (e.g., `4-64`, `3-24,29-67`)
- Step 23 predictions: 84 lines (header + 83 classified predictions)
- Classifications: 83 "miss" (correct - none have dpam_prob ≥ 0.85)

## Regression Tests Added

### test_step18_get_mapping.py

1. **test_step18_parses_hhsearch_correctly**
   - Verifies HHsearch native format is parsed using proper parser
   - Catches bug where raw file was read as tab-delimited

2. **test_step18_dali_column_mapping**
   - Verifies DALI good_hits uses column 2 (ecodkey) not column 1 (ecodnum)
   - Catches bug where wrong column was used for ECOD ID matching

3. **test_step18_produces_non_empty_mappings**
   - End-to-end test that template ranges are populated
   - Catches bug where all mappings had 'na\tna'

### test_step23_get_predictions.py (NEW FILE)

1. **test_step23_ecod_length_column_mapping**
   - Verifies ECOD_length uses column 1 (ECOD ID) not column 0 (number)
   - Catches bug that caused 0 ECOD matches

2. **test_step23_produces_non_empty_output**
   - End-to-end test that predictions are generated
   - Catches bug where only headers were written

3. **test_step23_classification_logic**
   - Verifies full/part/miss classification works correctly
   - Tests coverage and probability thresholds

4. **test_load_position_weights_** (3 tests)
   - Unit tests for position weight loading
   - Handles missing files, malformed data

## Files Modified

**Core Fixes:**
- `dpam/steps/step18_get_mapping.py` - HHsearch parser fix (lines 147-166)
- `dpam/steps/step18_get_mapping.py` - DALI column fix (line 181)
- `dpam/steps/step23_get_predictions.py` - ECOD_length column fix (line 132)

**Test Suite:**
- `tests/integration/test_step18_get_mapping.py` - Added 3 regression tests
- `tests/integration/test_step23_get_predictions.py` - Created new file with 7 tests

## Running Regression Tests

```bash
# Test Step 18 fixes
pytest tests/integration/test_step18_get_mapping.py::TestStep18GetMapping::test_step18_parses_hhsearch_correctly -v
pytest tests/integration/test_step18_get_mapping.py::TestStep18GetMapping::test_step18_dali_column_mapping -v
pytest tests/integration/test_step18_get_mapping.py::TestStep18GetMapping::test_step18_produces_non_empty_mappings -v

# Test Step 23 fixes
pytest tests/integration/test_step23_get_predictions.py::TestStep23GetPredictions::test_step23_ecod_length_column_mapping -v
pytest tests/integration/test_step23_get_predictions.py::TestStep23GetPredictions::test_step23_produces_non_empty_output -v

# Run all new regression tests
pytest tests/integration/test_step18_get_mapping.py tests/integration/test_step23_get_predictions.py -v
```

## Lessons Learned

1. **Column indexing errors are subtle** - Easy to use wrong column when file formats are inconsistent
2. **Parser abstraction is critical** - Don't manually parse complex formats that have parsers
3. **End-to-end tests catch integration bugs** - Unit tests alone wouldn't have caught these
4. **Empty output is a red flag** - When a step produces only headers, check for filtering bugs

## Related Documentation

- Original bug report: `/home/rschaeff/work/gvd/DPAM_C2_STEP23_BUG_REPORT.md`
- Step 18 implementation: `docs/STEP18_IMPLEMENTATION.md`
- Step 23 implementation: `docs/STEP23_IMPLEMENTATION.md`
- ML pipeline overview: `docs/ML_PIPELINE_SETUP.md`
