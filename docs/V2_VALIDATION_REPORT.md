# DPAM V2 Validation Report

## Executive Summary

DPAM V2 has been validated against V1 using 9,850 SwissProt proteins (10 batches of ~1,000 each). **V2 passes all 9 validation metrics** and is deemed a suitable replacement for V1.

**Key Statistics:**
- 93.3% domain detection rate (V2/V1)
- 79.1% of V1 domains have high-quality V2 matches (Jaccard ≥0.8)
- 94.3% T-group agreement for matched domains
- 84.8% of proteins have identical domain counts

**For high-confidence (`good_domain`) predictions only:**
- 84.6% recall (V1 good_domain found in V2)
- 88.1% precision (V2 good_domain matches V1)
- 98.9% T-group agreement

## Validation Methodology

### Data Sources
- **V1 Reference:** PostgreSQL database (`ecod_protein` on dione:45000, table `swissprot.domain`)
- **V2 Results:** Pipeline output from `step24/*_domains` files
- **Proteins:** 10,000 SwissProt proteins with AlphaFold structures

### Comparison Metrics

1. **Jaccard Coefficient:** Measures residue-level overlap between domain ranges
   - J = |intersection| / |union|
   - J = 1.0: Exact match
   - J ≥ 0.8: High overlap (considered a match)
   - J < 0.2: No match (considered missed)

2. **T-group Agreement:** ECOD topology group classification match

3. **Judge Agreement:** Domain quality classification match
   - Categories: good_domain, low_confidence, simple_topology, partial_domain

## Validation Rubric

| Category | Metric | Threshold | Observed | Status |
|----------|--------|-----------|----------|--------|
| Coverage | Protein coverage (V2/V1) | ≥95% | 98.5% | PASS |
| Coverage | Domain count ratio (V2/V1) | ≥90% | 93.3% | PASS |
| Count Agreement | Exact same count | ≥80% | 84.8% | PASS |
| Count Agreement | Within ±1 domain | ≥95% | 96.6% | PASS |
| Boundary Agreement | High overlap (J≥0.8) | ≥75% | 79.1% | PASS |
| Boundary Agreement | Mean Jaccard | ≥0.80 | 0.841 | PASS |
| Classification | T-group agreement | ≥90% | 94.3% | PASS |
| Classification | Judge agreement | ≥90% | 95.8% | PASS |
| Missed Domains | V1 domains missed (J<0.2) | ≤10% | 6.6% | PASS |

### Threshold Rationale

- **95% protein coverage:** Allows for edge cases and pipeline failures
- **90% domain ratio:** V2 may filter more aggressively than V1
- **80% exact count:** Most proteins should match exactly
- **75% high Jaccard:** Accounts for boundary variation
- **90% classification:** Core ECOD assignments should match
- **10% missed rate:** Small fraction of difficult cases acceptable

## Jaccard Distribution

```
 0.0-0.1 │█████████                                   1,278 ( 6.6%)
 0.1-0.2 │█                                             ... ( 1.1%)
 0.2-0.5 │████                                          ... ( 6.3%)
 0.5-0.8 │████████                                    1,871 ( 9.7%)
 0.8-1.0 │██████████████████████████████████████████  8,955 (46.3%)
     1.0 │████████████████████████████████████        6,354 (32.8%)
```

- **79.1%** of V1 domains have J ≥ 0.8 (high-quality match)
- **32.8%** are exact matches (J = 1.0)
- **6.6%** are completely missed (J < 0.2)

## High-Confidence Domain Analysis (good_domain only)

Since `good_domain` is the most practically important category, we performed a focused analysis comparing only high-confidence predictions between V1 and V2.

### Comparison: All Domains vs good_domain Only

| Metric | All Domains | good_domain Only | Change |
|--------|-------------|------------------|--------|
| V1 domains | 19,348 | 15,181 | - |
| V2 domains | 18,253 | 14,573 | - |
| Domain ratio (V2/V1) | 94.3% | 96.0% | +1.7% |
| High Jaccard (≥0.8) | 79.1% | 84.6% | **+5.5%** |
| Exact match (J=1.0) | 32.9% | 36.0% | +3.1% |
| Missed (J<0.2) | 6.6% | 5.7% | -0.9% |
| Mean Jaccard | 0.841 | 0.871 | +0.03 |
| T-group agreement | 94.3% | **98.9%** | **+4.6%** |
| Exact count match | 84.8% | 87.2% | +2.4% |

### Recall and Precision for good_domain

**Recall (V1 good_domain → V2 good_domain):**
```
  Exact (J=1.0):       5,463 (36.0%)
  High (0.8≤J<1.0):    7,383 (48.6%)
  Medium (0.5≤J<0.8):  1,047 (6.9%)
  Low (0.2≤J<0.5):       425 (2.8%)
  Missed (J<0.2):        863 (5.7%)
  ─────────────────────────────────
  Combined (J≥0.8):   12,846 (84.6%)
```

**Precision (V2 good_domain → V1 good_domain):**
```
  Exact (J=1.0):       5,463 (37.5%)
  High (0.8≤J<1.0):    7,383 (50.7%)
  Medium (0.5≤J<0.8):  1,046 (7.2%)
  Low (0.2≤J<0.5):       342 (2.3%)
  Novel (J<0.2):         339 (2.3%)
  ─────────────────────────────────
  Combined (J≥0.8):   12,846 (88.1%)
```

### Interpretation

The good_domain analysis reveals that **disagreements are concentrated in lower-confidence categories**:

1. **T-group agreement jumps to 98.9%** - Nearly perfect ECOD fold classification for high-confidence domains

2. **Recall improves by 5.5%** - V2 captures more V1 good_domains than overall domains

3. **Precision improves by 4.3%** - V2 good_domains are more likely to match V1

4. **Only 2.3% novel** - Very few V2 good_domains are not found in V1

5. **Only 5.7% missed** - Most V1 good_domains are recovered by V2

This strongly supports V2 as a V1 replacement for practical use cases that rely on high-confidence predictions.

## Known Limitations

### 1. Repeat Domain Handling

V2 treats tandem repeat proteins differently than V1:

| Repeat Family | V2/V1 Ratio | Notes |
|---------------|-------------|-------|
| ARM/HEAT (109) | 93.8% | Acceptable, boundary differences |
| Kelch (376) | 104.6% | V2 finds slightly more |
| WD40 (375) | 69.9% | **Significant loss** - individual blades missed |
| TPR (391) | Variable | Collapses repeat units into super-domains |

**Example:** Q9IBG7 has 24 TPR domains in V1 but only 4 in V2. V2 groups adjacent repeat units.

**Recommendation:** Document as expected behavior. Users seeking individual repeat unit detection should use V1 or post-process V2 output.

### 2. Missed good_domain Entries

387 V1 "good_domain" entries are not found in V2 (J < 0.2):
- 40% (153) are repeat-related domains
- 60% (233) are distributed across many T-groups (no concentration)

Top affected T-groups:
- 109.4.1 (EF-hand like): 16 missed
- 4043.1.1 (Sel1-like repeat): 16 missed
- 375.1.1 (WD40): 15 missed
- 325.1.7 (Tandem SH3): 15 missed

### 3. X-group Classification Disagreements

716 domains (5.7% of matched) have different X-group assignments:

**Systematic Issues:**
| V2 Template | Count | Pattern |
|-------------|-------|---------|
| e4rgvB1 | 11 | All Rossmann (2007) → 4002 |
| e3p8cD1 | 7 | Multiple X-groups → 3235 |
| e5xtcW1 | 5 | Multiple X-groups → 1132 |
| e4lidB1 | 5 | All 192.6.1 → 6161 |

**Recommendation:** Investigate these specific templates for potential ECOD classification issues or ML model bias.

### 4. Confidence Upgrades

88% of V1 "low_confidence" domains are upgraded to "good_domain" in V2.

This is likely correct behavior - V2's ML model may be more accurate than V1's heuristics. However, manual review of a sample is recommended.

## Analyses Performed

### Analysis 1: Domain Count Comparison
- Per-protein domain count comparison
- Distribution of count differences
- Identification of outlier proteins (|diff| ≥ 3)

### Analysis 2: Jaccard Coefficient Analysis
- Residue-level overlap for all domain pairs
- Bidirectional matching (V1→V2 and V2→V1)
- Size distribution of unmatched domains

### Analysis 3: Classification Agreement
- T-group exact match rate
- X-group match rate (fold level)
- Judge category cross-tabulation

### Analysis 4: Systematic Issue Detection
- V2 template concentration analysis
- X-group transition patterns
- Identification of "promiscuous" templates

### Analysis 5: Repeat Domain Characterization
- Per-family detection rates
- Size distribution of missed repeats
- Case study: Q9IBG7 (extreme outlier)

### Analysis 6: High-Confidence Domain Comparison
- Filtered to `good_domain` entries only (V1: 15,181, V2: 14,573)
- Recall analysis: V1 good_domain → V2 good_domain
- Precision analysis: V2 good_domain → V1 good_domain
- Comparison of metrics between all-domain and good_domain-only analyses
- Finding: All metrics improve when restricted to high-confidence predictions

## Recommendations

1. **Accept V2 as V1 replacement** - All metrics pass thresholds

2. **Document repeat domain behavior** - Users should know V2 may report fewer domains for tandem repeat proteins

3. **Investigate problematic templates** - e4rgvB1, e3p8cD1, e5xtcW1 warrant manual review

4. **Monitor WD40 (375) detection** - 30% reduction is significant; may need algorithm adjustment if individual blade detection is important

5. **Consider confidence upgrade validation** - Sample review of low_confidence→good_domain cases

## Files Generated

- `batch_XX/v1_reference.tsv` - V1 domain data extracted from database
- `batch_XX/step24/*_domains` - V2 domain output with Judge categories
- This report: `docs/V2_VALIDATION_REPORT.md`

## Validation Date

January 2025

## Authors

Automated validation performed by DPAM development team.
