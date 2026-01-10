# Step 9 Bug Fix: Overly Aggressive HHsearch Filtering

**Date:** 2025-11-20
**Issue:** Step 9 applies probability/coverage filter that doesn't exist in original DPAM
**Severity:** CRITICAL - Causes 65-90% assignment failure rate
**Status:** ✅ Fixed with regression tests

## Problem Summary

Step 9 was applying an aggressive filter (`coverage >= 0.4 AND probability >= 50`) to HHsearch hits before passing them to DOMASS. **This filter does not exist in the original DPAM pipeline**. The original only requires ≥10 aligned residues.

This caused low-probability sequence hits to be filtered out before reaching the DOMASS ML model, resulting in:
- DOMASS receiving `HHprob=0, HHcov=0` as features
- ML model predicting low probabilities
- Dramatically reduced ECOD assignment success rates

**Impact:**
- **BFVD validation**: 35% success rate (7/20 proteins) vs expected ~90%
- **GVD proteins**: 10% success rate (5/50 proteins)
- **Root cause**: 65-90% of proteins had HHsearch hits filtered out at Step 9

---

## Root Cause Analysis

### Original DPAM Behavior (Correct)

**Step 5** (`step5_process_hhsearch.py` lines 179-183):
```python
# Only filter: requires ≥10 aligned residues
if len(qresids) >= 10 and len(eresids) >= 10:
    qrange = get_range(qresids,'')
    hrange = get_range(hresids, chainid)
    erange = get_range(eresids,'')
    coverage = round(len(eresids) / ecodlen, 3)
    # Write ALL hits - NO probability/coverage filter
```

**Step 15** (`step15_prepare_domass.py` lines 23-35):
```python
# Read ALL hits from step5 result
if os.exists('step5/' + spname + '/' + prot + '.result'):
    fp = open('step5/' + spname + '/' + prot + '.result','r')
    for countl, line in enumerate(fp):
        if countl:
            # Process ALL hits - no filtering
            hhprob = float(words[3]) / 100
            coverage = float(words[10])
```

**Design principle**: ALL HHsearch hits (including low-probability hits like prob=17.66) are passed to DOMASS. The ML model decides if evidence is strong enough.

### dpam_c2 Bug (Incorrect)

**Step 9** (`step09_get_support.py` lines 204-226 - OLD CODE):
```python
for hit in domain_hits:
    # Calculate coverage
    template_resids_set = set(hit.template_resids)
    coverage = len(template_resids_set) / hit.ecod_len

    # ❌ BUG: This filter doesn't exist in original!
    if coverage >= 0.4 and hit.probability >= 50:
        # Check for new residues (at least 50% new)
        new_resids = template_resids_set.difference(covered_resids)

        if len(new_resids) >= len(template_resids_set) * 0.5:
            # Write to _sequence.result
```

**Result**: Low-probability hits filtered out → never reach goodDomains → Step 15 sees NO sequence hits → DOMASS gets HHprob=0 → predicts low probability.

---

## Evidence: Case Study A0A0B5J9J9

### Original DPAM Results
```
Domain  Range      ECOD      DPAM_prob  Judge
D1      36-125     101.1.1   0.979      good_domain
D2      131-225    145.1.1   0.941      good_domain
```

### dpam_c2 Results (BEFORE FIX)

**HHsearch hits in map2ecod.result:**
```
uid        ecod_id    hh_prob  coverage
002407647  e5yekB1    17.66    0.905   ← Low probability but HIGH coverage
002704181  e7jrqA1    17.25    0.346   ← Low probability AND low coverage
```

**Step 9 filtering:**
- Both hits have prob < 50 → **FILTERED OUT**
- `_sequence.result` file: **0 bytes (empty)**

**Step 10 goodDomains:**
- Contains only "structure" (Foldseek) hits
- Contains ZERO "sequence" (HHsearch) hits

**Step 15 features:**
```
domID  domRange   tgroup    HHprob  HHcov   HHrank  Dzscore  ...
D1     41-125     3684.1.1  0.000   0.000   10.00   2.800    ...
                            ↑↑↑↑↑   ↑↑↑↑↑
                            NO sequence evidence!
```

**Step 16 DOMASS predictions:**
- Max DPAM probability: **0.4315** (vs 0.979 in original)
- Below 0.6 threshold → filtered out at Step 17
- **No confident predictions**

**Pipeline outcome:**
- ❌ Failed to assign domains D1 and D2
- Original DPAM prob: 0.979, dpam_c2 prob: 0.43 (**2.3x reduction**)

---

## Fix Applied

### Step 9: Remove Probability/Coverage Filter

**File:** `dpam/steps/step09_get_support.py`
**Lines:** 199-226

**OLD CODE:**
```python
for hit in domain_hits:
    # Calculate coverage
    template_resids_set = set(hit.template_resids)
    coverage = len(template_resids_set) / hit.ecod_len

    # ❌ BUG: Aggressive filter
    if coverage >= 0.4 and hit.probability >= 50:
        new_resids = template_resids_set.difference(covered_resids)
        if len(new_resids) >= len(template_resids_set) * 0.5:
            # Process hit
```

**NEW CODE:**
```python
for hit in domain_hits:
    # Calculate coverage
    template_resids_set = set(hit.template_resids)
    coverage = len(template_resids_set) / hit.ecod_len

    # ✓ FIXED: Keep ALL hits (no probability/coverage filter)
    # Only check for redundancy (50% new residues)
    # DOMASS ML model will decide if evidence is strong enough
    new_resids = template_resids_set.difference(covered_resids)

    if len(new_resids) >= len(template_resids_set) * 0.5:
        # Process hit
```

**Rationale:**
1. Matches original DPAM behavior exactly
2. Lets DOMASS ML model evaluate evidence strength
3. Filtering decisions should be data-driven by the trained model, not arbitrary thresholds
4. Low-probability hits can still provide valuable signal to ML model

---

## Secondary Fix: Step 15 Consensus Mapping

### Bug: `.pop()` During Dict Comprehension

**File:** `dpam/steps/step15_prepare_domass.py`
**Lines:** 432-437

**OLD CODE:**
```python
# ❌ BUG: Using .pop() mutates set during iteration
hh_map = {hh['query_resids'].pop(): hh['template_resids'][i]
         for i in range(len(hh['template_resids']))}
hh['query_resids'] = set(hh_map.keys())  # Try to restore (doesn't work)
```

**Issue**: `.pop()` removes elements from the set during iteration, producing incorrect mappings and breaking subsequent calculations using `query_resids`.

**NEW CODE:**
```python
# ✓ FIXED: Don't mutate set during iteration
hh_query_list = list(hh['query_resids'])
hh_map = {hh_query_list[i]: hh['template_resids'][i]
         for i in range(min(len(hh_query_list), len(hh['template_resids'])))}

dali_query_list = list(dali['query_resids'])
dali_map = {dali_query_list[i]: dali['template_resids'][i]
           for i in range(min(len(dali_query_list), len(dali['template_resids'])))}
```

---

## Regression Tests Added

### test_step09_get_support.py

**1. test_sequence_keeps_low_coverage_hits**
   - Creates HHsearch hit with coverage=0.30 (below old 0.4 threshold)
   - Verifies hit is KEPT, not filtered out
   - Catches bug where coverage < 0.4 was filtered

**2. test_sequence_keeps_low_probability_hits**
   - Creates HHsearch hit with prob=17.66 (like A0A0B5J9J9)
   - Verifies hit is KEPT, not filtered out
   - Catches bug where prob < 50 was filtered

### test_step15_prepare_domass.py

**3. test_consensus_mapping_does_not_mutate_sets**
   - Simulates consensus calculation with query_resids sets
   - Verifies sets are NOT mutated during mapping
   - Catches bug where `.pop()` consumed elements

---

## Validation Plan

After applying fixes:

**1. Re-run BFVD validation (20 proteins):**
```bash
dpam batch validation/bfvd_test_proteins.txt \
    --working-dir validation/dpam_c2_fixed \
    --data-dir ~/data/dpam_reference/ecod_data \
    --cpus 8 --parallel 1
```

**Expected outcomes:**
- A0A0B5J9J9 should get DPAM prob ≥0.9 (not 0.43)
- ≥18/20 proteins should produce Step 24 assignments (not 7/20)
- Assignment success rate should match original DPAM (≥90%)

**2. Re-run GVD proteins (50 proteins):**
- Expected: ≥40/50 proteins with assignments (not 5/50)
- Pass 2 success rate: ≥80% (not 10%)

**3. Verify sequence features in Step 15:**
```bash
# Check that HHprob > 0 for proteins with HHsearch hits
awk -F'\t' '$8 > 0 {print}' validation/dpam_c2_fixed/*.step15_features | wc -l
# Should be >> 0 (was 0 before fix)
```

---

## Impact Summary

**Before fix:**
- BFVD: 35% success rate (7/20 proteins)
- GVD: 10% success rate (5/50 proteins)
- ~70% of proteins lose valid HHsearch evidence

**After fix:**
- Expected BFVD: ≥90% success rate (≥18/20 proteins)
- Expected GVD: ≥80% success rate (≥40/50 proteins)
- DOMASS receives full feature set as designed

**Priority:** CRITICAL - This bug invalidates current dpam_c2 results and explains the low assignment rates observed in validation.

---

## Files Modified

**Core Fixes:**
- `dpam/steps/step09_get_support.py` - Remove prob/coverage filter (lines 199-226)
- `dpam/steps/step09_get_support.py` - Update docstrings (lines 1-20, 140-158)
- `dpam/steps/step15_prepare_domass.py` - Fix `.pop()` bug (lines 431-438)

**Test Suite:**
- `tests/integration/test_step09_get_support.py` - Updated 2 tests (lines 181-247)
- `tests/integration/test_step15_prepare_domass.py` - Added 1 test (lines 231-288)

---

## References

- **Original bug report:** `/home/rschaeff/work/gvd/validation/DPAM_C2_BUG_REPORT.md`
- **Original DPAM code:** `/data/data1/conglab/qcong/for/domain_parser/dpam_automatic/`
- **BFVD validation plan:** `validation/DPAM_VALIDATION_PLAN.md`
- **Reference protein:** A0A0B5J9J9 (35% → should be 100% success)

---

## Running Regression Tests

```bash
# Test Step 9 fixes
pytest tests/integration/test_step09_get_support.py::TestStep09GetSupport::test_sequence_keeps_low_coverage_hits -v
pytest tests/integration/test_step09_get_support.py::TestStep09GetSupport::test_sequence_keeps_low_probability_hits -v

# Test Step 15 fix
pytest tests/integration/test_step15_prepare_domass.py::TestStep15HelperFunctions::test_consensus_mapping_does_not_mutate_sets -v

# Run all Step 9/15 tests
pytest tests/integration/test_step09_get_support.py tests/integration/test_step15_prepare_domass.py -v
```
