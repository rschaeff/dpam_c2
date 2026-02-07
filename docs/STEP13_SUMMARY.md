# Step 13 Summary: Parse Domains

**Status:** ✅ Complete
**Implementation:** `steps/step13_parse_domains.py`
**Lines of Code:** ~900
**Complexity:** High (most complex step)

---

## Purpose

Final domain parsing using all previous outputs:
1. **Probability matrices** - Combine PDB distance, PAE, HHsearch, DALI scores
2. **Segmentation** - Create 5-residue chunks excluding disorder
3. **Clustering** - Merge segments by probability thresholds
4. **Refinement** - Fill gaps, remove overlaps, filter by length

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step PARSE_DOMAINS --working-dir ./work
```

### Input
- `{prefix}.fa` - Sequence from step 1
- `{prefix}.diso` - Disorder predictions from step 12
- `{prefix}.pdb` - Structure from step 1
- `{prefix}.json` - AlphaFold PAE matrix
- `{prefix}.goodDomains` - Filtered domains from step 10

### Output
- `{prefix}.finalDPAM.domains` - Final parsed domains
- `{prefix}.step13_domains` - Same output (for ML pipeline compatibility)

### Performance
- **Time:** 1-5 minutes (depends on protein size)
- **Memory:** 500 MB - 2 GB (for probability matrix)
- **Scaling:** O(N²) for N residues

---

## Algorithm Overview

```
1. Load inputs
   - Sequence (length)
   - Disorder residues
   - PDB coordinates
   - PAE matrix
   - Good domains (HHsearch, DALI scores)

2. Calculate probability matrix
   - PDB distance probabilities
   - PAE error probabilities
   - HHsearch score aggregation
   - DALI score aggregation
   - Combined: (dist * pae * hhs * dali) ^ 0.25 (geometric mean)

3. Initial segmentation
   - 5-residue chunks
   - Exclude disordered residues
   - Keep segments >= 3 non-disordered residues

4. Merge by probability
   - Mean probability > 0.64 threshold
   - Merge all qualifying segment pairs

5. Iterative clustering (v1.0 algorithm)
   - Calculate intra-segment probabilities
   - Merge if: inter_prob * 1.1 >= min(intra1, intra2)
   - Repeat until convergence

6. Domain refinement v0
   - Filter domains >= 25 residues

7. Domain refinement v1
   - Fill gaps <= 10 residues
   - Fill gaps <= 20 if <= 10 in other domains

8. Domain refinement v2
   - Remove overlaps (keep segments >= 10 unique residues)

9. Final filter
   - Keep domains >= 25 residues

10. Write output
```

---

## Key Functions

### `run_step13(prefix, working_dir, path_resolver=None)`
Main entry point. Runs complete domain parsing algorithm.
`path_resolver`: Optional `PathResolver` for sharded output layout.

---

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Segment size | 5 | Initial chunk size |
| Min segment residues | 3 | Non-disordered residues required |
| Merge threshold | 0.64 | Mean probability for initial merge |
| Iterative ratio | 1.1 | Inter/intra probability ratio |
| Min unique residues | 10 | For overlap removal |
| Min domain length | 25 | Final domain filter |
| Gap fill (always) | ≤ 10 | Always fill gaps this size |
| Gap fill (conditional) | ≤ 20 | Fill if ≤ 10 in other domains |
| Sequence separation | ≥ 5 | For probability calculation |

---

## Probability Functions

### PDB Distance Probability

| Distance (Å) | Probability |
|--------------|-------------|
| ≤ 3 | 0.95 |
| ≤ 6 | 0.94 |
| ≤ 9 | 0.93 |
| ≤ 12 | 0.91 |
| ≤ 15 | 0.89 |
| ≤ 18 | 0.85 |
| ≤ 21 | 0.81 |
| ≤ 24 | 0.77 |
| ≤ 27 | 0.71 |
| ≤ 30 | 0.66 |
| ≤ 35 | 0.58 |
| ≤ 40 | 0.48 |
| ≤ 45 | 0.40 |
| ≤ 50 | 0.33 |
| ≤ 55 | 0.28 |
| ≤ 60 | 0.24 |
| ≤ 70 | 0.22 |
| ≤ 80 | 0.20 |
| ≤ 120 | 0.19 |
| ≤ 160 | 0.15 |
| ≤ 200 | 0.10 |
| > 200 | 0.06 |

---

### PAE Error Probability

| PAE (Å) | Probability |
|---------|-------------|
| ≤ 1 | 0.97 |
| ≤ 2 | 0.89 |
| ≤ 3 | 0.77 |
| ≤ 4 | 0.67 |
| ≤ 5 | 0.61 |
| ≤ 6 | 0.57 |
| ≤ 7 | 0.54 |
| ≤ 8 | 0.52 |
| ≤ 9 | 0.50 |
| ≤ 10 | 0.48 |
| ≤ 11 | 0.47 |
| ≤ 12 | 0.45 |
| ≤ 14 | 0.44 |
| ≤ 16 | 0.42 |
| ≤ 18 | 0.41 |
| > 18 | 0.25 |

---

### HHsearch Score Probability

| HHsearch Score | Probability |
|----------------|-------------|
| ≥ 180 | 0.98 |
| ≥ 160 | 0.94 |
| ≥ 140 | 0.92 |
| ≥ 120 | 0.88 |
| ≥ 110 | 0.87 |
| ≥ 100 | 0.81 |
| ≥ 50 | 0.76 |
| < 50 | 0.50 |

**Default score:** 20 (for missing pairs)

**Aggregation rules:**
- If count > 10: `score = max + 100`
- Else: `score = max + count * 10 - 10`

---

### DALI Z-score Probability

| DALI Z-score | Probability |
|--------------|-------------|
| ≥ 35 | 0.95 |
| ≥ 25 | 0.94 |
| ≥ 20 | 0.93 |
| ≥ 18 | 0.90 |
| ≥ 16 | 0.87 |
| ≥ 14 | 0.85 |
| ≥ 12 | 0.80 |
| ≥ 11 | 0.77 |
| ≥ 10 | 0.74 |
| ≥ 9 | 0.71 |
| ≥ 8 | 0.68 |
| ≥ 7 | 0.63 |
| ≥ 6 | 0.58 |
| < 6 | 0.50 |

**Default score:** 1 (for missing pairs)

**Aggregation rules:**
- If count > 5: `score = max + 5`
- Else: `score = max + count - 1`

---

## Combined Probability Formula

```
combined_prob = (dist_prob * pae_prob * hhs_prob * dali_prob) ^ 0.25
```

**Formula:** Geometric mean (equal weights of 0.25 each)

**Note:** Default HHS=20 and DALI=1 scores are applied to ALL residue pairs before aggregation, ensuring every pair has a baseline score.

---

## Clustering Algorithm (v1.0)

### Initial Merge (Probability-based)

**Threshold:** Mean probability > 0.64

For each segment pair:
1. Calculate mean probability between all residue pairs (separation ≥ 5)
2. If mean > 0.64, merge segments
3. Repeat until no more merges

### Iterative Merge (Intra/Inter comparison)

**Threshold:** `inter_prob * 1.1 >= min(intra1, intra2)`

For each cluster pair:
1. Calculate intra-cluster probabilities
2. Calculate inter-cluster probability
3. Special case: If intra_count ≤ 20, force merge
4. Otherwise: merge if `inter_prob * 1.1 >= min(intra1, intra2)`
5. Repeat until convergence

---

## Domain Refinement

### Version 0 (Initial)
- **Filter:** Keep domains ≥ 25 residues

### Version 1 (Gap Filling)
- Fill gaps ≤ 10 residues (always)
- Fill gaps ≤ 20 residues if ≤ 10 residues in other domains

### Version 2 (Overlap Removal)
- Remove residues that appear in multiple domains
- Keep segments with ≥ 10 unique (non-overlapping) residues
- Keep domains with ≥ 25 total residues

---

## Output Format

**Files:**
- `{prefix}.finalDPAM.domains`
- `{prefix}.step13_domains` (identical, for ML pipeline)

**Format:** `D{n}\t{range_string}`

**Example:**
```
D1	10-120
D2	130-250,260-280
D3	300-450
```

---

## Common Issues

### No domains found
**Cause:** All clusters < 25 residues or all removed due to overlaps
**Check:** Review disorder predictions, may indicate highly disordered protein

### Too many small domains
**Cause:** Low inter-segment probabilities prevent merging
**Fix:** Usually correct for fragmented proteins

### Single large domain
**Cause:** High probabilities throughout, entire protein merged
**Fix:** Normal for compact single-domain proteins

### Memory error
**Cause:** Large protein (> 2000 residues) creates huge probability matrix
**Fix:** Run on machine with more memory

---

## Integration with Pipeline

### Upstream Dependencies
- **Step 1 (Prepare):** Provides sequence, PDB, PAE
- **Step 10 (Filter Domains):** Provides good domains with scores
- **Step 12 (Disorder):** Provides disorder predictions

### Downstream Usage
- **Step 15+ (ML Pipeline):** Uses `.step13_domains` for ECOD classification

---

## Summary

Step 13 is the core domain parsing algorithm, using probability matrices from multiple sources (distance, PAE, HHsearch, DALI) to identify structural domains.

**Key algorithm parameters:**
- Combined probability: geometric mean (power 0.25)
- Merge threshold: 0.64
- Iterative ratio: 1.1
- Min domain size: 25 residues
- Min unique residues: 10

**Next:** Step 15 (Prepare DOMASS) - ML feature extraction
