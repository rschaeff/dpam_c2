# DPAM v2.0 Validation Criteria and Results

## Exact Match Definition

A **strict exact match** between DPAM v2.0 and v1.0 reference requires ALL three criteria:

### 1. Same Domain Count
- V2 must predict the same number of domains as V1 reference
- Example: If V1 has 2 domains, V2 must also have exactly 2 domains

### 2. High Domain Overlap (≥50% Jaccard)
- Each V2 domain must have ≥50% Jaccard similarity with a corresponding V1 domain
- Jaccard similarity = |intersection| / |union| of residue sets
- This ensures domains cover similar regions, not just same count

### 3. Matching T-groups
- Overlapping domain pairs must have the same ECOD T-group assignment
- T-group is the topology-level classification in ECOD hierarchy
- This validates that domain identity, not just boundaries, is correct

## Validation Results

### Round 1 (Dec 12, 2025)
- **Configuration**: 1000 SwissProt proteins, ran on leda16-45
- **Issue**: ML pipeline (steps 15-16) had widespread failures

| Category | Count | Percentage |
|----------|-------|------------|
| **Exact matches** (all 3 criteria) | 4 | 0.4% |
| Count match, fails overlap/T-group | 9 | 0.9% |
| Count match, no V2 T-group | 726 | 72.7% |
| Domain count mismatch | 260 | 26.0% |

**Root cause**: Step 10 (FILTER_DOMAINS) ran before input files existed, creating empty goodDomains. This cascaded to ML pipeline failures.

### Round 2 (Dec 13-18, 2025)
- **Configuration**: Same 1000 proteins, step 10+ re-run after fix
- **Fix applied**: Cleared step 10 state, re-ran with proper input data

| Category | Count | Percentage |
|----------|-------|------------|
| **Exact matches** (all 3 criteria) | 383 | 38.6% |
| Count match, fails overlap/T-group | 79 | 8.0% |
| Count match, no V2 T-group | 233 | 23.5% |
| Domain count mismatch | 297 | 29.9% |

## Example Exact Matches

### Single Domain: Q6NH02
```
V2 D1: 1-395    T-group: 875.1.1    Overlap: 100%
V1 nD1: 1-395   T-group: 875.1.1    ✓ Match
```

### Two Domains: Q58079
```
V2 D1: 6-170,326-340   T-group: 7512.1.1   Overlap: 97.2%
V1 nD1: 6-165,326-340  T-group: 7512.1.1   ✓ Match

V2 D2: 171-325         T-group: 7512.1.1   Overlap: 96.9%
V1 nD2: 166-325        T-group: 7512.1.1   ✓ Match
```

### Single Domain with Boundary Difference: A8GQV6
```
V2 D1: 11-155   T-group: 167.1.1   Overlap: 93.5%
V1 nD1: 1-155   T-group: 167.1.1   ✓ Match
```

## Failure Categories

### Domain Count Mismatch (29.9%)
V2 predicts different number of domains than V1. Common causes:
- Under-segmentation: V2 merges domains V1 kept separate
- Over-segmentation: V2 splits domains V1 kept together
- Different disorder handling

### No V2 T-group (23.5% in Round 2, 72.7% in Round 1)
V2 domain parsing succeeded but T-group assignment failed.

**Pipeline cascade**:
```
Step 16 (DOMASS ML) → produces predictions with prob < 0.6
    ↓
Step 17 (GET_CONFIDENT) → filters out low-confidence → no output
    ↓
Step 18 (GET_MAPPING) → "No confident predictions" → no output
    ↓
Step 23 (GET_PREDICTIONS) → missing input file → FAIL
```

**Confidence threshold**: Step 17 requires `probability ≥ 0.6` to include a prediction.

**Round 2 breakdown** (after step 10 fix):
- 315 proteins (31.5%): High-confidence T-groups (≥0.6 prob)
- 684 proteins (68.5%): Only low-confidence predictions (<0.6 prob)

**Root causes for low confidence**:
1. **Domain-ECOD mismatch**: Step 13 domain boundaries may not align with ECOD templates
2. **Novel domains**: Query domains lack close ECOD homologs
3. **Weak HHsearch/DALI scores**: Features don't strongly support classification
4. **Training data gap**: ML model may not generalize to these domain types

### Overlap/T-group Mismatch (8.0%)
Same domain count but domains don't match. Causes:
- Different boundary positions (low Jaccard)
- Same boundaries but different T-group assignment
- Domain swapping (D1↔D2 correspondence issues)

## Technical Notes

### Jaccard Similarity Calculation
```python
def jaccard(v2_residues, v1_residues):
    intersection = len(v2_residues & v1_residues)
    union = len(v2_residues | v1_residues)
    return intersection / union
```

### Range Parsing
Ranges are parsed to residue sets:
- "1-100" → {1, 2, 3, ..., 100}
- "1-50,60-100" → {1, ..., 50, 60, ..., 100}

### T-group Selection
When multiple T-group predictions exist for a domain, the one with highest HH_prob is used.

## Bug Fix: DALI Feature Normalization (Dec 19, 2025)

### Root Cause Identified

The DOMASS model was producing near-zero probabilities because of a **feature normalization bug** in step 15:

**V1.0 step15** (correct):
```python
zscore = float(words[4]) / 10   # DALI z-score divided by 10
drank = drank / 10              # DALI rank divided by 10
```

**V2.0 step15** (bug):
```python
zscore = float(parts[4])        # NO DIVISION - 10x too large
rank = float(parts[8])          # NO DIVISION - 10x too large
```

### Impact

The DOMASS model was trained on V1.0 features where:
- DALI z-score range: 0.5-5.0 (after /10 normalization)
- DALI rank range: 0.1-10.0 (after /10 normalization)

V2.0 was feeding unnormalized features:
- DALI z-score: 5-50 (10x too large)
- DALI rank: 1-100 (10x too large)

This caused out-of-distribution inputs, producing near-zero probabilities.

### Fix Applied

In `dpam/steps/step15_prepare_domass.py`:
```python
# V1.0 normalizes z-score and rank by dividing by 10
# This matches the training data used for the DOMASS model
zscore = float(parts[4]) / 10.0
rank = float(parts[8]) / 10.0
```

### Before/After Comparison

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| HH+DALI mean prob | 0.21 | 0.58 |
| DALI-only mean prob | 0.005 | 0.31 |
| Predictions ≥0.6 | 7% | ~50% |

### Validation Impact

This fix should significantly improve:
- Step 17 pass rate (threshold 0.6)
- T-group assignment success rate
- Overall exact match rate (from 38.6% to potentially >50%)

**Round 3 revalidation required** with the fix applied to all 1000 proteins.

## Recommendations

1. **Target**: ≥50% strict exact match rate for production readiness
2. **Current status**: 38.6% achieved (Round 2), requires Round 3 with fix

### Priority Fixes

1. **DALI feature normalization** ✅ FIXED (Dec 19, 2025)
   - Root cause: V2.0 missing /10 division for z-score and rank
   - Fix applied to step15_prepare_domass.py

2. **Address domain count mismatches (29.9%)**
   - Compare step 13 segmentation algorithm with v1.0
   - Review PAE/PDB distance thresholds
   - Check gap tolerance and merge logic

3. **Improve domain boundary alignment (8.0%)**
   - Review step 13 clustering parameters
   - Consider using step 22 merge logic more aggressively

### Diagnostic Queries

Check confidence distribution:
```bash
# Count predictions by probability bucket
for f in *.step16_predictions; do
    tail -n +2 "$f" | awk -F'\t' '{print int($5*10)/10}'
done | sort | uniq -c | sort -k2 -n
```

Check which domains lack support:
```bash
# Find domains with no goodDomains overlap
python3 -c "... see validation scripts ..."
```
