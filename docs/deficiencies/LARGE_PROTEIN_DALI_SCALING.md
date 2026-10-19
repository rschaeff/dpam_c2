# Iterative-DALI scaling deficiency for ≥2.5 kAA queries

**Severity**: medium (correctness OK; throughput unbounded)
**First observed**: 2026-05-08, v294.2 large-protein revalidation cohort
**Affected step**: `dpam.steps.iterative_dali` (Step 7)
**Affected pipeline modes**: `--resume` and fresh runs equally

## Problem

When the query protein is at the upper tail of AlphaFold's length distribution
(≈2.4 kAA and above), Step 7 (iterative DALI against the ECOD reference set)
becomes the dominant wall-time consumer and can run indefinitely with no
log progress between reference-domain comparisons. Concrete observation from
the v294.2 revalidation set (783 proteins ≥1000 AA, cross-fold composite
F-groups, recovery batch with `--time=12:00:00`):

| query | length | Step 7 wall | other steps | outcome |
|---|---:|---|---|---|
| Q13813 (SPTBN1, human) | 2472 AA | >9 h, no progress lines | unreached | ran out of budget |
| Q68FG2 (Spectrin/PH9, mouse) | 2388 AA | ~5 h on Step 7 | unreached at 5 h elapsed | tracking |
| Q9VE34 (Drosophila pair) | 2455 AA | ~3 h | reached Step 13 by 5 h | likely OK |
| (most other ≥2 kAA cases) | 2000-2400 AA | 30-60 min | normal | OK |

The transition happens somewhere around 2.4 kAA. Proteins of this size are
near the upper limit of what AFDB predicts (vanishingly few human proteins
fall above 2.5 kAA), so the population is small but real and includes
biologically important scaffolds — Spectrin, FASN (P12276 / 2512 AA),
PIEZO1 (Q92508 / 2521 AA), TANC2 (Q9P273 / 2699 AA), NBEAL1 (2694 AA).

## Why it scales badly

`iterative_dali` performs a pairwise DALI alignment between the query and
~2000 ECOD reference domains. The DALI runtime is roughly proportional to
`|Q| × |R|` for query Q and reference R; for a 2.5 kAA query each reference
alignment is ~5-10× more work than for a 500 AA query, and the reference
set size is fixed. With 32 DALI workers oversubscribed on 16 CPUs, the
extra CPU contention slows things further.

There is no progress-logging between references inside the iterative-DALI
loop, so a hung worker is indistinguishable from a slow one until the SLURM
wall limit fires.

## Proposed fix — Step 7 wall-time watchdog

Wrap the iterative-DALI loop in a wall-time guard with these properties:

1. **Per-step budget**, configurable via CLI flag (suggested default
   `--iterative-dali-max-seconds=10800` = 3 h).
2. **Per-reference progress logging** every N references (e.g. N=100) with
   elapsed time, so a hung worker is visible.
3. **Graceful early stop**: when the budget elapses, mark Step 7 as
   completed with the partial hit set, stamp a `step7_partial=True` flag
   in the checkpoint state, and let downstream steps (8-24) proceed. The
   classifier is robust to a smaller reference set; the partial result is
   useful, the empty/failed result is not.
4. **Audit field** in the final domain output indicating that Step 7 was
   truncated, so curators can flag those domains for re-review with a
   length-adapted strategy.

Estimated effort: ~1 day. Touches `dpam/steps/iterative_dali.py` and the
checkpoint serialisation; downstream steps need minor tolerance for fewer
references.

## Why not the alternatives (for now)

- **Length-stratified reference subset** (use 1 rep per ECOD F-group instead
  of full ~2000) is the better long-term fix but requires recalibrating
  Step 8+ scoring against a different reference distribution and re-running
  the v1-vs-v2 validation. Scope >> watchdog.

- **Sliding-window decomposition** for ≥2 kAA queries (run on overlapping
  windows, stitch boundaries) is the structurally correct approach but is
  a major refactor of the DPAM data flow.

- **Foldseek pre-filter** before DALI is appealing (~1000× faster) but the
  Step 8+ score model is DALI-calibrated, so substituting would require
  retraining; would also lose some sensitivity for unusual fold compositions
  in cross-fold composite hosts (the entire population this work is about).

## Population scope

In the v294.2 revalidation batch, **3 of 33 recovery tasks are blocked by
this scaling issue**. Counting downstream domain-level impact:

| straggler F-group | ≥1000 AA cohort behind it |
|---|---:|
| 604.1.1.157 | 2 |
| 604.1.1.137 | 6 |
| 109.4.1.3504 | 1 |
| **total** | **9** |

Population is small enough that the proximate v294.2 / next-release
delivery is *not* blocked on this fix — the 9 affected domains can be
hand-curated or processed by a one-off length-adapted re-run. The fix is a
follow-up to make subsequent ECOD updates self-driving without this manual
escape hatch.

## Cross-references

- Trigger investigation: `INSR_KINASE_DEFICIENCY.md` (the parser bug that
  led us to revalidate the large-protein cohort in the first place).
- v294.2 evidence: `/data/ecod/database_versions/v294.2/audit/DPAM_V2_LARGE_PROTEIN_REVALIDATION.md`
- Job artifacts: SLURM job 526511 (main, 4 h limit, 33 timeouts) and
  527440 (recovery, 12 h limit, 3 stragglers).
