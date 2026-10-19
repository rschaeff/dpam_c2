# DPAM v2 deficiency — INSR kinase domain dropped between step 13 and step 24

**Status**: ✅ FIXED in dpam_c2 (2026-05-02, post-discovery same day).
This document is preserved as the diagnostic record. The follow-up
validation list is at
`/data/ecod/database_versions/v294.2/audit/dpam_v2_revalidation_targets.tsv`
(see also `DPAM_V2_LARGE_PROTEIN_REVALIDATION.md` in the v294.2 audit dir).
The remaining suspicion is that DPAM v2 outputs on **>1000-residue, multi-fold
proteins** may have other latent issues; that's what the revalidation set
exercises.

---

**Discovered**: 2026-05-02
**Test target**: `AF-P06213-F1` (INSR_HUMAN, 1382 residues, model_v6)
**Pipeline**: full 24-step run, all steps reported as completed by the harness.
**Failure**: an unambiguous protein kinase domain (canonical INSR tyrosine
kinase, Pfam PF07714, ECOD T-group 206.1.1) is identified at the parsing
step but eliminated before final assignment. The final output covers only
residues 36-955; residues 956-1382 (including the entire intracellular
region with the kinase) are unrepresented.

This is a separate (and qualitatively different) failure from the DPAM v1/v5
INSR bug, where the kinase was *included* but merged with the C-terminal
ectodomain into one over-large domain. Both pipelines need fixing for INSR;
this writeup is for the v2-specific path.

---

## Reproduction

```bash
unset OMP_PROC_BIND
source ~/.bashrc && conda activate dpam

# Working dir already populated. The two inputs are:
#   AF-P06213-F1.cif   (v6 model, 1382 residues; 1.32 MB)
#   AF-P06213-F1.json  (v6 PAE matrix from EBI; 5.49 MB)
# both at /home/rschaeff/work_dpam_insr/work/

dpam run AF-P06213-F1 \
  --working-dir /home/rschaeff/work_dpam_insr/work \
  --data-dir /home/rschaeff_1/data/dpam_reference/ecod_data \
  --cpus 16 --resume --skip-addss --flat \
  --scratch-dir /tmp --dali-workers 32
```

SLURM record: job 524728 on `leda00` (192GB partition, 16 cpus, 64 GB mem,
6h walltime), wall ~1h24m. HHsearch took 27 min, iterative DALI 42 min;
everything else <2 min each. Pipeline completed: `24 succeeded, 0 failed`.

Full SLURM stdout/stderr:
`/home/rschaeff/work_dpam_insr/dpam_insr_524728.log`

---

## Final output (the bug)

`work/AF-P06213-F1.finalDPAM.domains`:

```
nD1   36-335
nD2   336-495
nD3   511-620
nD4   681-715
nD5   716-740
nD6   621-675,796-845
nD7   846-955
```

Coverage = 920 / 1382 residues = **66.6%**.

`work/AF-P06213-F1.diso` (disorder calls) only flags residues **1310-1381**
as disordered (the C-tail). Residues **956-1309** are NOT flagged disordered
and are NOT covered by any final domain — they are simply missing from the
output.

For comparison, DPAM v5 (in production via ECOD v294.1) covers 1225 / 1382
= 88.6% on the same protein, but does so by extending its `nD6` to 846-1305,
swallowing the kinase together with fn3-3 and the TM/JM region into one
domain (also wrong, but at least classifiable).

---

## Step-13 ground truth — the kinase WAS detected

`work/AF-P06213-F1.step13_domains` (initial domain parse, 10 candidates):

```
D1   36-180
D2   181-215
D3   216-335
D4   336-495
D5   511-620
D6   681-715
D7   716-740
D8   621-675,796-845
D9   846-955
D10  1026-1309   ← the kinase domain, correct boundaries
```

The intracellular kinase region is identified as **`D10 = 1026-1309`** — a
clean range covering the canonical INSR tyrosine kinase fold with the C-tail
(1310-1381) trimmed off as disordered. By this point the pipeline has done
exactly what we want.

---

## Step 14-19 — D10 is dropped

The 10 step-13 candidates feed step 14 onward. By step 24 (integrate
results), only 7 domains remain. D10 does not appear in
`work/AF-P06213-F1.step23_predictions`:

```
# classification  domain      range                    ecod      tgroup    dpam_prob  hh_prob  dali_zscore
full              D1,D2,D3    36-335                   e2hr7A1   389.6.1   1.000      1.000    1.820
full              D4          336-495                  e4zxbE7   207.1.1   0.997      1.000    3.120
full              D5          511-620                  e6hn5F2   11.1.1    0.987      1.000    1.910
miss              D6          681-715                  e5xnqA1   207.1.1   0.724      0.000    0.600
miss              D7          716-740                  e5yjzA1   206.1.1   0.927      0.000    0.920
full              D8          621-675,796-845          e1fnhA3   11.1.1    0.963      0.989    1.170
full              D9          846-955                  e6pxvA2   11.1.1    0.979      1.000    1.800
```

D10 is gone. Note D6 and D7 show the "miss" classification (kept anyway), but
D10 isn't even on the page.

---

## Why D10 was filtered — DALI scores all collapse

`work/AF-P06213-F1.step15_features` and `step16_predictions` show the
per-template scoring inputs that the ML classifier sees. For D10:

| domain | range | t_group | template | dpam_prob | hh_prob | dali_zscore |
|---|---|---|---|---:|---:|---:|
| D10 | 1026-1309 | **206.1.1** | `e7ng7A1` | 0.0000 | **0.998** | **10.000** |
| D10 | 1026-1309 | **206.1.1** | `e3zosB1` | 0.0000 | **0.998** | 10.000 |
| D10 | 1026-1309 | **206.1.1** | `e2vwbA2` | 0.0000 | **0.993** | 10.000 |
| D10 | 1026-1309 | **206.1.1** | `e6kzdA1` | 0.0000 | **0.998** | 10.000 |
| D10 | 1026-1309 | **206.1.1** | `e3a99A1` | 0.0000 | **0.997** | 10.000 |

Five well-established Pkinase ECOD templates, all with HHsearch probability
0.99+, all with `dali_zscore = 10.000`. The 10.000 value is the no-hit
sentinel used by step 15 when no DALI alignment is available — that drives
`dpam_prob` to 0.0000 and the ML filter then removes the domain.

Compare to D9 (`846-955`, fn3-3) on the same row: `hh_prob = 1.000`,
`dali_zscore = 1.800` (clean alignment), `dpam_prob = 0.979`, kept.

---

## Why DALI scores collapsed — the iterative_dali output DOES have kinase hits

This is where it gets interesting.

`work/AF-P06213-F1_iterativdDali_hits` contains 1,439 DALI-aligned templates
in total. Several of them clearly hit the kinase region of the query:

```
> uid_ordinal     z_score   ali_len  template_len  ?
>000001475_2      10.5      85       1288          0   ← residue 1288 = inside kinase
>000001482_2      10.9      85       1288          0
>000001484_2       9.6      91       1289          0
>000001485_2       9.2      96       1284          0
>000001475_3       8.4      88       1192          0
>000001482_3      10.3      89       1198          0
```

Z-scores of 8-11 are unambiguous fold matches. So **DALI did successfully
align kinase templates to the kinase region of INSR**. The data exists.

But `work/AF-P06213-F1.map2ecod.result` shows the canonical kinase ECOD
templates that step 15 looked up:

```
uid       ecod_domain_id  hh_prob  query_range
002782594 e7ng7A1         99.75    1013-1295
000259768 e3zosB1         99.82    1015-1293
002542775 e6kzdA1         99.82    1018-1294
000141175 e3a99A1         99.66    1018-1288
001516135 e2vwbA2         99.29    1019-1234
```

These uids are `00278…`, `00025…`, `00254…`, `00014…`, `00151…` — none match
the iterative_dali template uids `000001475`, `000001482`, `000001484`,
`000001485` that did get DALI hits.

In other words: **iterative_dali aligned a DIFFERENT set of kinase templates
to the same query region than HHsearch did**, and the per-domain scoring in
step 15 only looks for the HHsearch-matched templates' DALI scores. Those
HHsearch-matched templates were either not in the iterative_dali candidate
list, or DALI failed on those specific ones, while DALI succeeded on a
different (overlapping but distinct) set of kinase templates.

The candidate list size is reported in the log:
> `dali_candidates: Merged candidates: 511 from HHsearch + 1789 from Foldseek = 2047 unique domains`

So step 6 fed 2,047 templates into iterative_dali. Whether all 5 of D10's
HHsearch-top templates made it through is the key question.

---

## Hypothesis space for the actual root cause

Ranked by likelihood after looking at the artifacts:

1. **Per-template DALI failure mode is opaque.** The 5 HHsearch-matched
   kinase templates probably *were* in the iterative_dali candidate list
   (they're high-prob HHsearch hits, which dominate that list), but DALI
   failed to produce alignments for them — perhaps a worker error, timeout,
   or template-PDB-file issue. Step 15 then treats "no DALI alignment row
   for this template" as `dali_zscore = 10.000` rather than going back to
   `iterativDali_hits` and looking for *any* high-scoring template that
   covers D10's range. The downstream effect is: an entire well-supported
   domain is dropped because of incidental DALI-runtime failures on a
   handful of templates.

2. **Iterative DALI uses different template identifiers than step 15.**
   `iterativDali_hits` uses `uid_ordinal` (e.g. `000001475_2`) while step 15
   keys on canonical ECOD domain ids (`e7ng7A1`). If the mapping table is
   incomplete or out of sync, alignments to a kinase template via one path
   might never reach the other. Need to read the iterative_dali → step15
   feature merge code to confirm.

3. **DALI-worker oversubscription.** We ran with `--dali-workers 32` on 16
   cpus per the README's recommendation ("DALI is I/O-bound; try 4x CPUs
   with local scratch"). It's plausible that under contention, individual
   worker processes silently truncate or fail. A targeted re-run with
   `--dali-workers 8` would test this.

4. **Sub-structure extraction issue.** Iterative_dali has to extract the
   query region for D10 (residues 1026-1309) and the template structure for
   each candidate. If the per-domain query extraction failed for D10 (e.g.
   the residue numbering was offset), every template DALI-vs-D10 would
   return no hit. Inspecting the `.dali` job logs / per-D10 work files would
   confirm. The DALI scratch dir we used (`/tmp/dpam_dali_AF-P06213-F1`)
   was in `--scratch-dir` and was probably cleaned up at job end; a re-run
   without scratch or with the cleanup disabled would let us inspect.

5. **Template fold dissimilarity.** Effectively zero probability — INSR
   kinase has the canonical bilobal Pkinase fold and standard DALI Z-scores
   against e.g. `e1ir3A1` (INSR's own fragment crystal) are 12-15.

---

## Suggested debugging path

1. **Cheap, high-information** — re-run only iterative_dali on this
   working dir with `--dali-workers 8` (no oversubscription) and **disable
   scratch cleanup** so the per-D10 inputs survive:

   ```bash
   conda activate dpam
   dpam run-step AF-P06213-F1 \
     --step ITERATIVE_DALI \
     --working-dir /home/rschaeff/work_dpam_insr/work \
     --data-dir /home/rschaeff_1/data/dpam_reference/ecod_data \
     --cpus 16 --flat
     # NB: omit --scratch-dir, omit --dali-workers
   ```

   Then re-run `step15` → `step24` from the result and compare.

2. **Diagnostic** — verify the 5 HHsearch-matched kinase templates were in
   the iterative_dali candidate list:

   ```bash
   grep -E "002782594|000259768|002542775|000141175|001516135" \
     /home/rschaeff/work_dpam_insr/work/AF-P06213-F1_hits4Dali
   ```

   If absent, the bug is in step 6 (DALI_CANDIDATES) merging logic, not in
   DALI itself.

3. **Code inspection** — open `dpam/steps/step15_features.py` (or whichever
   module handles the per-domain feature merge) and check how it reconciles
   `dali_zscore` for templates that are in `map2ecod.result` (HHsearch-side)
   but lack a row in `_iterativdDali_hits`. If it sets 10.000 instead of
   pulling the best Z-score for any template covering the query range,
   that's the algorithmic deficiency to fix.

4. **Validation re-test** — pick 5 other RTKs from the
   `dunbrack_2026-05-02_human_pk_slice` list (e.g. PDGFRA P09619, KIT P10721,
   VEGFR3 P35916, EphR Q91694, MELK Q14680) and run them through DPAM v2
   the same way. If the kinase-region drop reproduces, the bug is generic
   to large multi-domain RTKs and needs a methodology fix; if it's
   INSR-specific, it's likely a single-protein DALI artifact.

---

## Why this matters

The v294.2 ECOD release plan
(`/data/ecod/database_versions/v294.2/V294.2_RELEASE_PLAN.md`) replaces
domain-level Pfam scanning with protein-level. That correctly identifies
PF07714 in INSR at residues 1023-1298. But the Pfam reconciliation step then
needs a DPAM domain to attach the assignment to:

- Under DPAM v5 (current production), the wrong-boundary `nD6 = 846-1305`
  exists — Phase 2 can re-segment it.
- Under DPAM v2, **there is no domain** in the kinase region. Phase 2 would
  have to *create* a new domain on the basis of Pfam evidence alone, which
  loses the structural backing that DPAM is supposed to provide.

So this v2 deficiency directly limits how clean the v294.2 corrective
release can be. The 16 mis-parked human kinases enumerated in
`/data/ecod/database_versions/v294.2/audit/dunbrack_2026-05-02_human_pk_slice.md`
(plus the wider non-human population) are the proteins whose v294.2
correction depends on getting DPAM to keep the kinase domain. If v2's
output is the basis going forward, this iterative_dali → step15 linkage
needs to be solid.

---

## Artifacts preserved

Working dir (1.6 GB, do not delete):
`/home/rschaeff/work_dpam_insr/work/`

Snapshots in v294.2 audit:
- `/data/ecod/database_versions/v294.2/audit/dpam_v2_INSR_test.md` (release-side write-up)
- `/data/ecod/database_versions/v294.2/audit/dpam_v2_INSR_finalDPAM.domains`
- `/data/ecod/database_versions/v294.2/audit/dpam_v2_INSR_step13_domains.tsv`
- `/data/ecod/database_versions/v294.2/audit/dpam_v2_INSR_D10_step15_features.tsv`
- `/data/ecod/database_versions/v294.2/audit/dpam_v2_INSR_D10_step16_predictions.tsv`

Original investigation triggered by an email from Roland Dunbrack
(2026-05-02) — see
`/data/ecod/database_versions/v294.2/audit/dunbrack_2026-05-02_human_pk_slice.md`.
