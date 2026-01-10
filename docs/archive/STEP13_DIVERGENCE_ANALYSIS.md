# Step 13 Divergence Analysis

## Overview

This document compares three implementations of domain parsing:
1. **v1.0 13-step** (`~/dev/DPAM/old_v1.0/v1.0/step13_parse_domains.py`)
2. **dpam_automatic step 14** (`~/dev/dpam_automatic/step14_parse_domains.py`)
3. **dpam_c2 step 13** (current implementation)

## Key Finding: v1.0 and dpam_automatic are NEARLY IDENTICAL

The v1.0 13-step and dpam_automatic implementations differ only in minor details.
**dpam_c2 is significantly divergent from both.**

---

## 1. Probability Lookup Tables

### PDB Distance Probability

| Distance (Å) | v1.0 / dpam_auto | dpam_c2 | Match? |
|--------------|------------------|---------|--------|
| ≤ 3  | 0.95 | 0.95 | ✅ |
| ≤ 6  | 0.94 | 0.94 | ✅ |
| ≤ 9  | 0.93 | **0.88** (at ≤8) | ❌ |
| ≤ 12 | 0.91 | **0.79** | ❌ |
| ≤ 15 | 0.89 | **0.69** (at ≤16) | ❌ |
| ≤ 18 | 0.85 | **0.64** | ❌ |
| ≤ 30 | 0.66 | **0.43** | ❌ |
| ≤ 60 | 0.24 | **0.23** | ~✅ |
| ≤ 200 | 0.1 | **0.08** | ~✅ |

**Divergence**: dpam_c2 has **completely different bin boundaries** and values for mid-range distances (8-40Å).

### PAE Error Probability

| PAE (Å) | v1.0 / dpam_auto | dpam_c2 | Match? |
|---------|------------------|---------|--------|
| ≤ 1  | 0.97 | 0.97 | ✅ |
| ≤ 2  | 0.89 | 0.89 | ✅ |
| ≤ 3  | 0.77 | **0.83** | ❌ |
| ≤ 4  | 0.67 | **0.78** | ❌ |
| ≤ 5  | 0.61 | **0.74** | ❌ |
| ≤ 8  | 0.52 | **0.62** | ❌ |
| ≤ 10 | 0.48 | **0.56** | ❌ |
| ≤ 20 | 0.39 | **0.35** | ~✅ |
| ≤ 28 | 0.16 | **0.19** | ~✅ |

**Divergence**: dpam_c2 is **more optimistic** for mid-range PAE values (3-10Å), giving higher probabilities.

### HHsearch Probability

| HHpro Score | v1.0 / dpam_auto | dpam_c2 | Match? |
|-------------|------------------|---------|--------|
| ≥ 180 | 0.98 | 0.98 | ✅ |
| ≥ 160 | 0.94 | **0.96** | ❌ |
| ≥ 140 | 0.92 | **0.93** | ~✅ |
| ≥ 120 | 0.88 | **0.89** | ~✅ |
| ≥ 110 | 0.87 | *(missing)* | ❌ |
| ≥ 100 | 0.81 | **0.85** | ❌ |
| ≥ 90  | *(missing)* | **0.81** | ❌ |
| ≥ 80  | *(missing)* | **0.77** | ❌ |
| ≥ 70  | *(missing)* | **0.72** | ❌ |
| ≥ 60  | *(missing)* | **0.66** | ❌ |
| ≥ 50  | 0.76 | **0.58** | ❌ |
| < 50  | 0.5  | 0.5 | ✅ |

**Divergence**: dpam_c2 has **finer granularity** (more bins) and slightly different values.

### DALI Z-score Probability

| Z-score | v1.0 13-step | dpam_auto | dpam_c2 | Match? |
|---------|--------------|-----------|---------|--------|
| ≥ 35 | 0.98 | **0.95** | 0.98 | v1.0 ≠ auto |
| ≥ 30 | *(missing)* | *(missing)* | 0.96 | dpam_c2 only |
| ≥ 25 | 0.96 | **0.94** | 0.93 | ALL DIFFER |
| ≥ 20 | 0.93 | **0.93** | 0.89 | v1.0 = auto |
| ≥ 18 | 0.89 | **0.9** | 0.85 | ALL DIFFER |
| ≥ 16 | 0.83 | **0.87** | 0.81 | ALL DIFFER |
| ≥ 14 | 0.79 | **0.85** | 0.77 | ALL DIFFER |
| ≥ 12 | 0.74 | **0.8** | 0.72 | ALL DIFFER |
| ≥ 11 | 0.69 | **0.77** | *(missing)* | - |
| ≥ 10 | 0.66 | *(missing)* | 0.66 | v1.0 = dpam_c2 |
| ≥ 6  | 0.51 | **0.60** | 0.55 | ALL DIFFER |
| < 6  | 0.5  | 0.5 (< 2) | 0.5 | ✅ |

**CRITICAL**: DALI tables differ **across all three versions**! This is unexpected - v1.0 and dpam_auto should match but don't.

---

## 2. Probability Combination Formula

| Version | Formula | Equal Weights? |
|---------|---------|----------------|
| v1.0 | `dist^0.1 * pae^0.1 * hhs^0.4 * dali^0.4` | ❌ (20%/20%/40%/40%) |
| dpam_auto | `(dist * pae * hhs * dali)^0.25` | ✅ (25%/25%/25%/25%) |
| dpam_c2 | `dist^0.1 * pae^0.1 * hhs^0.4 * dali^0.4` | ❌ (20%/20%/40%/40%) |

**KEY FINDING**:
- **v1.0 matches dpam_c2** on formula (weighted toward HHS/DALI)
- **dpam_auto is different** (equal weights)
- This is the **OPPOSITE** of what we expected!

---

## 3. Merging Thresholds

| Parameter | v1.0 | dpam_auto | dpam_c2 | Match? |
|-----------|------|-----------|---------|--------|
| Initial merge threshold | 0.54 | 0.64 | 0.54 | v1.0 = dpam_c2 |
| Inter/intra ratio | 1.07 | 1.1 | 1.07 | v1.0 = dpam_c2 |

**v1.0 matches dpam_c2 exactly. dpam_auto is MORE CONSERVATIVE** (higher thresholds).

---

## 4. Gap Filling Logic (domains_v0 → domains_v1)

### v1.0 / dpam_c2
```python
# Simple: fill gaps ≤ 10 residues
if len(interseg) <= 10:
    for residue in interseg:
        newdomain.append(residue)
```

### dpam_automatic
```python
# Complex: check for overlap with other domains
count_other = 0  # residues in other domains
count_good = 0   # residues not in other domains
if count_all <= 10:
    getit = 1
elif count_all <= 20 and count_other <= 10:
    getit = 1
```

**Divergence**: dpam_automatic **considers overlap** when filling gaps. v1.0 and dpam_c2 do NOT.

---

## 5. Overlap Removal Logic (domains_v1 → domains_v2)

| Version | Min unique residues | Match? |
|---------|---------------------|--------|
| v1.0 | 15 | ✅ |
| dpam_auto | 10 (check ≥ 10 good, keep if ≥ 25 total) | ❌ |
| dpam_c2 | 15 | ✅ |

**v1.0 matches dpam_c2**. dpam_auto uses **different logic** (min 10 unique, min 25 total).

---

## 6. T-group Constraints

| Version | Uses T-groups? | Description |
|---------|----------------|-------------|
| v1.0 | ❌ NO | No T-group logic at all |
| dpam_auto | ❌ NO | No T-group logic at all |
| dpam_c2 | ✅ **YES** | Extensive consensus filtering and merge constraints |

**CRITICAL ADDITION**: dpam_c2 adds sophisticated T-group compatibility checking:
- Consensus filtering (3:1 ratio or 75% majority)
- Requires shared dominant T-group for merging
- Strict constraint: both segments must have assignments

**This is a major algorithmic change not present in either reference.**

---

## 7. Segment Pair Distance Filtering

### v1.0 / dpam_automatic
```python
# Only count pairs with sequence separation ≥ 5
if resi + 5 < resj:
    probs.append(rpair2prob[resi][resj])
```

### dpam_c2
```python
# Count ALL pairs regardless of separation
for res1 in seg1:
    for res2 in seg2:
        total += get_prob(prob_matrix, res1, res2)
        count += 1
```

**CRITICAL BUG**: dpam_c2 is **missing the `+5` filter** that excludes nearby residues!

This means dpam_c2 includes probabilities for residue pairs that are close in sequence,
which inflates similarity scores and causes inappropriate merging.

---

## Summary of Divergences

### dpam_c2 matches v1.0 on:
1. ✅ Probability combination formula (weighted)
2. ✅ Merging thresholds (0.54, 1.07)
3. ✅ Gap filling logic (simple ≤10)
4. ✅ Overlap removal threshold (15)

### dpam_c2 diverges from v1.0 on:
1. ❌ **PDB distance probability table** (different bins/values)
2. ❌ **PAE probability table** (more optimistic mid-range)
3. ❌ **HHS probability table** (finer granularity)
4. ❌ **DALI probability table** (minor differences)
5. ❌ **T-group constraints** (major addition, not in v1.0)
6. ❌ **Sequence separation filter** (MISSING - critical bug!)

### v1.0 vs dpam_automatic differences:
1. Probability combination formula (weighted vs equal)
2. Merging thresholds (0.54/1.07 vs 0.64/1.1)
3. Gap filling (simple vs overlap-aware)
4. Some DALI probability values differ

---

## Recommended Fix Priority

To match v1.0 behavior exactly:

### HIGH PRIORITY (algorithmic correctness)
1. **Add sequence separation filter** (`if resi + 5 < resj`) - CRITICAL BUG
2. **Remove all T-group constraints** - not in v1.0
3. **Fix probability tables** - use exact v1.0 values

### MEDIUM PRIORITY (validation)
4. Test against known v1.0 outputs
5. Document which version is "canonical"

### LOW PRIORITY (future enhancement)
6. Consider T-group constraints as v2.0 feature (if they improve results)
7. Document why probability tables differ from v1.0

---

## Next Steps

1. **Decide on canonical reference**: Is v1.0 13-step the gold standard?
2. **Fix critical bugs**: Add +5 filter, align probability tables
3. **Document T-group enhancement**: If keeping it, treat as v2.0 feature
4. **Validate**: Run both versions on test cases, compare outputs
