# Step 15 Summary: Prepare DOMASS Features

**Status:** Complete
**Implementation:** `steps/step15_prepare_domass.py`
**Lines of Code:** ~500
**Complexity:** Medium

---

## Purpose

Extract 17 machine learning features for each domain-ECOD pair by combining domain properties (length, SSE counts) with HHsearch and DALI evidence scores. Features are used by the DOMASS neural network in step 16.

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step PREPARE_DOMASS \
  --working-dir ./work --data-dir ./data
```

### Input
- `{prefix}.step13_domains` - Parsed domains (from step 13)
- `{prefix}.sse` - Secondary structure elements (from step 11)
- `{prefix}.goodDomains` - Filtered HHsearch hits (from step 10)
- `{prefix}_good_hits` - DALI hits with scores (from step 9)
- `ECOD_maps/{ecod_id}.map` - PDB to ECOD residue numbering
- `ecod.latest.domains` - ECOD hierarchy (T-groups, H-groups)

### Output
- `{prefix}.step15_features` - Features for ML model (17 columns + metadata)

### Performance
- **Time:** 1-5 seconds
- **Memory:** <200 MB

---

## Algorithm

```
1. Load ECOD hierarchy (T-groups, H-groups) from ecod.latest.domains
2. Load SSE data from .sse file
3. For each domain:
   a. Count helices (>=6 residues) and strands (>=3 residues)
4. Load HHsearch hits from goodDomains:
   a. Filter for 'sequence' type entries only
   b. Calculate H-group redundancy rank per query residue
5. Load DALI hits from _good_hits:
   a. Map template residues to ECOD canonical numbering
6. For each domain:
   a. Find overlapping HHsearch hits (50% threshold)
   b. Find overlapping DALI hits (50% threshold)
   c. For ECODs found by BOTH methods:
      - Calculate consensus coverage and position diff
   d. For single-method ECODs:
      - Assign default values (0.0 or max_rank)
7. Write feature rows with 17 features + metadata
```

---

## Feature Definitions (17 total)

### Domain Properties (3 features)
| Feature | Column | Description |
|---------|--------|-------------|
| domLen | 5 | Domain length (residue count) |
| Helix_num | 6 | Number of helices (>=6 residues) |
| Strand_num | 7 | Number of strands (>=3 residues) |

### HHsearch Scores (3 features)
| Feature | Column | Description |
|---------|--------|-------------|
| HHprob | 8 | HHsearch probability (0-1) |
| HHcov | 9 | Query coverage (0-1) |
| HHrank | 10 | H-group redundancy rank / 10 |

### DALI Scores (5 features)
| Feature | Column | Description |
|---------|--------|-------------|
| Dzscore | 11 | Z-score / 10 |
| Dqscore | 12 | Q-score (0-1) |
| Dztile | 13 | Z-score percentile (0-10) |
| Dqtile | 14 | Q-score percentile (0-10) |
| Drank | 15 | Template rank / 10 |

### Consensus Metrics (2 features)
| Feature | Column | Description |
|---------|--------|-------------|
| Cdiff | 16 | Mean template position diff (-1 if no consensus) |
| Ccov | 17 | Consensus coverage (0-1) |

### Metadata (4 columns)
| Field | Column | Description |
|-------|--------|-------------|
| HHname | 18 | HHsearch hit ECOD UID |
| Dname | 19 | DALI hit name |
| Drot1-3 | 20-22 | DALI rotation (placeholder 'na') |
| Dtrans | 23 | DALI translation (placeholder 'na') |

---

## Overlap Check

Uses 50% threshold (more permissive than step 18):

```python
overlap = resids_a & resids_b
return (len(overlap) >= len(resids_a) * 0.5 or
        len(overlap) >= len(resids_b) * 0.5)
```

---

## Output Format

**File:** `{prefix}.step15_features`

**Header:**
```
domID  domRange  tgroup  ecodid  domLen  Helix_num  Strand_num  HHprob  HHcov  HHrank  Dzscore  Dqscore  Dztile  Dqtile  Drank  Cdiff  Ccov  HHname  Dname  Drot1  Drot2  Drot3  Dtrans
```

**Example:**
```
D1	10-150	2.30.30	e1abc1	141	3	5	0.950	0.850	0.30	2.530	0.850	0.120	0.050	0.12	1.50	0.720	000000003_1	Q1_e1abc1_1	na	na	na	na
```

---

## Default Values

### HHsearch-only hits (no DALI match)
- Dzscore: 0.000
- Dqscore: 0.000
- Dztile: 10.000
- Dqtile: 10.000
- Drank: max_dali_rank
- Cdiff: -1.00
- Ccov: 0.000

### DALI-only hits (no HHsearch match)
- HHprob: 0.000
- HHcov: 0.000
- HHrank: max_hh_rank
- Cdiff: -1.00
- Ccov: 0.000

---

## Typical Statistics

### 500-Residue Protein (3 domains)
- **Domains:** 3
- **Feature rows:** 200-500
- **ECODs per domain:** 50-150
- **Both methods:** 60-80%
- **HHsearch-only:** 15-25%
- **DALI-only:** 5-15%

---

## Common Issues

### No features generated
**Cause:** No domains in .step13_domains or no hits overlap
**Check:** Verify step 13 completed successfully

### Missing ECOD maps
**Cause:** ECOD_maps directory not found
**Fix:** Ensure data_dir contains ECOD_maps/

### Low consensus coverage
**Cause:** HHsearch and DALI alignments don't overlap well
**Note:** Normal for divergent sequences

---

## Backward Compatibility

**100% v1.0 compatible**
- Feature normalization (z-score/10, rank/10) exact
- SSE counting thresholds (6 helix, 3 strand) exact
- Overlap calculation exact
- Output format exact

---

## Summary

Step 15 extracts 17 ML features combining domain properties with sequence/structure evidence.

**Key metrics:**
- 500 lines of code
- 1-5s execution time
- 17 features per domain-ECOD pair
- Handles single-method hits with defaults
- Ready for DOMASS model input (step 16)
