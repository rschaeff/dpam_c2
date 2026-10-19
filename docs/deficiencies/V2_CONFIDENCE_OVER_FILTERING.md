# DPAM v2 confidence-model over-filtering on large multi-domain hosts

**Severity**: medium (correctness OK; recall drops dramatically vs v1 on a known protein class)
**First observed**: 2026-05-09, v294.2 large-protein revalidation cohort
**Affected steps**: Step 17 (`get_confident`), Step 23 (`get_predictions`)
**Symptom**: DPAM v2 finds candidate domains in Step 13 but discards most as
"low_confidence" or below the confidence threshold by Step 24.

## Problem

For a subset of large multi-domain proteins, DPAM v2 produces dramatically
fewer final domains than DPAM v1 even though the candidate-finding stage
(Step 13) sees the structure. The drop happens in the confidence filter
(Steps 17 / 23 / 24).

## Concrete cases (from v294.2 revalidation)

All five completed Step 24 successfully (no runtime error); the issue is
recall, not robustness:

| protein | length | Step 13 domains | Step 17 confident | finalDPAM | v294.2 production (DPAM v1) |
|---|---:|---:|---:|---:|---:|
| Q969F9 (HPS3, human) | 1004 | 4 | 8 → 1 | **1** | **4** |
| Q9JIL5 (DCAF1-like, mouse) | 1547 | 3 | 1 | **1** | 2 |
| A0A175W5B5 (TRAPPC9, fungal) | 1462 | — | — | **4** | **5** |
| P0CD64 (Dicty DDB_G0287209) | 1650 | — | — | **5** | **10** |
| Q54N60 (Dicty DDB homolog) | 1520 | — | — | **3** | **4** |

DPAM v1 (production v294.2) classifications for these proteins are good —
mostly `f_group_specific`, well-distributed across the protein length,
consistent with Pfam envelope structure. **Adopting DPAM v2 boundaries
would be a regression.**

## Why this happens (hypothesis)

The confidence model in Steps 16-17 is calibrated against single-fold
small-to-medium proteins (the validation set used during v2 development).
On long multi-domain hosts with sparse / unusual Pfam content, the
per-domain confidence scores fall below the cut-off even though Step 13
correctly identified the structural boundaries.

Q969F9 specifically:
- Step 13: 4 domains parsed (correctly)
- Step 17: 8 confident predictions (likely picking up alternative segmentations)
- Step 23: collapses to 1 prediction → only 1 domain in finalDPAM
- The dropped 3 candidate domains correspond to genuine HPS3_N + HPS3_C
  Pfam envelopes (PF14761 envelope 3-480, PF14763 envelope 498-1001).

Q9JIL5:
- Step 13: 3 domains parsed
- Step 17: 1 confident prediction
- The WDR35 propeller (PF24797 19-371) and Tub C-term (PF01167 1360-1544)
  are dropped despite very strong Pfam support.

## Proposed fix (sketch)

Two paths, complementary:

1. **Length-conditional confidence threshold**: lower the Step 17 / 23
   discard threshold for queries above ~1.5 kAA, where the per-domain
   confidence scores are systematically lower due to feature-vector
   characteristics on long proteins. Calibrate against v1 outcomes for
   the v294.2 large-protein revalidation cohort (782 proteins, with
   v1 reference classifications already in `ecod_commons.f_group_assignments`).

2. **Pfam-anchored rescue**: if a Step 13 domain candidate overlaps a
   Pfam envelope at high bitscore (≥ Pfam-A `--cut_ga`) but gets dropped
   by Step 17, retain it with `partial_domain` tier and a `pfam_rescued`
   audit flag. This is a safety net that uses external evidence to
   prevent the confidence model from over-filtering well-supported domains.

Either fix should be validated by re-running the same large-protein
cohort and comparing: (a) the v2 output now matches v1 in domain count;
(b) the v1 boundaries and v2 boundaries agree to within ±15 residues.

## Population scope

In the v294.2 revalidation set (782 successful runs), 5 proteins clearly
fit this regression pattern. The broader scope is harder to estimate
without a v1-vs-v2 boundary diff across the full 782, but the
"low_confidence" tier coverage stat we computed (49.4% of proteins have
≥1 low_confidence domain) suggests the confidence model is biased
conservative across the cohort, not just on these 5.

## Disposition for v294.2 / next release

**Hold v1 boundaries** for the 5 affected proteins (and any others
identified by a future v1-vs-v2 diff). Don't ingest DPAM v2 outputs
where the v2 domain count is materially lower than v1 unless the v2
boundaries are independently better-supported (e.g. by Pfam evidence
or by curator review).

## Related

- **Iterative-DALI scaling deficiency** (`LARGE_PROTEIN_DALI_SCALING.md`):
  affects Step 7. Different failure mode but same protein class
  (large + cross-fold composite). The scaling-watchdog fix and the
  confidence-recalibration fix should land together to make DPAM v2
  reliable for the 1.5 kAA+ class.
- **v294.2 audit data**: `dpam_v2_no_good_pfam_check.tsv` has the
  per-protein Pfam-vs-DPAM side-by-side for the five proteins listed
  here. `dpam_v2_no_good_domain.tsv` has them tagged `v2_regression_keep_v1`.
