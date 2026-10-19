# Plan: DPAM reference set at ECOD v295

**Drafted:** 2026-07-21
**Builds on:** `docs/ECOD_UPDATE_REQUIREMENTS.md` (component formats, dependency graph,
phase checklist, DOMASS reparameterization criteria). This document does **not** restate
those — it scopes them to v295 with measured numbers and flags the decisions that must be
made before any compute is spent.

---

## 1. Why now

The installed reference (`~/data/dpam_reference/ecod_data`) is **develop285**. Current ECOD
is **v295**. Measured drift:

| | develop285 | v295 |
|---|---|---|
| domains (all) | 898,380 | **2,945,500** (3.3x) |
| T-groups | 3,948 | **3,956 (+8, +0.2%)** |
| F-group id churn | — | **78.3%** of ids differ |

Fold space is essentially static; the growth is denser sampling (largely AFDB-derived), and
the F-group id churn looks like systematic renumbering rather than reclassification. Practical
consequence: develop285 F-group labels are unusable against v295 resources, but T-level
conclusions carry over.

---

## 2. What already exists (do NOT rebuild)

Verified present 2026-07-21:

| Asset | State | Location |
|---|---|---|
| `ecod.v295.domains.txt` + F40/F70/F99 + names/hierarchy | ready | `v295/bulk_files/` |
| `ecod.v295.fa` (+ per-level FASTA) | ready | `v295/bulk_files/` |
| **ECOD v295 HHM database, 32,084 profiles** | **built 2026-07-04** | `v295/hhsuite_db/db/ecod_v295_Fgroup_{hhm,a3m,cs219}.ff*` |
| `ecod.v295.f_id_pfam_acc.txt` (32,075 F-groups → Pfam 38.2) | ready | `v295/bulk_files/` |
| hh-suite binaries | present | `/sw/apps/hh-suite/bin/` |
| DALI (`wolf`, `dalicon`) + Rust port | present | `~/dev/dali_cl/` |
| TensorFlow 2.15 + `domass_epo29.*` checkpoint | present | `dpam`/base envs, `dpam_reference/ecod_data` |
| foldseek 10 | present | `dpam` env, PATH |

**This kills the stated Phase-2 bottleneck.** `ECOD_UPDATE_REQUIREMENTS.md` calls the pdb70
HHsearch build "~1-2h per domain, ~63K domains" — the single largest line item. It is
**already done** for v295, with its own SLURM build scripts (`hhsuite_db/scripts/`).

---

## 3. THE decision that dominates everything: representative set

All-vs-all DALI is O(N²) and every remaining cost scales off N.

| Candidate rep set | N | pairwise (N²/2) | @50ms, 1000 cores |
|---|---|---|---|
| **F-group reps** (matches existing HHM DB) | **32,084** | 5.1e8 | **~7 hours** |
| develop285-equivalent ECOD70 | ~63,064 | 2.0e9 | ~28 hours |
| v295 F40 | 457,565 | 1.0e11 | ~60 days |
| v295 F70 | 886,539 | 3.9e11 | **~227 days — infeasible** |

Note the develop285 reference is **63,064 domains** (`ECOD_pdbs` = 63,065 `.pdb` + 62,892
`.dssp`; the foldseek DB has 63,064 entries). It is *not* v295's F70 (886,539) — the label
"ECOD70" is misleading. Naively adopting v295 F70 makes the build impossible.

**Recommendation: build at F-group representative granularity (32,084).**

- It is the granularity the v295 HHM DB is already built at, so sequence and structure
  evidence share one key. In develop285 the HH DB was **per-domain** while DALI was
  per-domain too; adopting F-group HH + domain DALI would introduce a join mismatch in
  step 5/6 that does not exist today.
- It is ~4x *cheaper* than the develop285 build, not more expensive.
- One structural exemplar per F-group is the natural unit for homology assignment.

**Cost of that choice — it triggers the DOMASS retraining condition.** See §5.

---

## 4. Build plan

Phases follow `ECOD_UPDATE_REQUIREMENTS.md`; only v295-specific scope is given here.

### Phase 0 — decide and freeze (blocking, no compute)
- [ ] Choose rep set (§3). Everything downstream keys off this.
- [ ] Decide whether AFDB-derived domains are eligible as reps. They are the bulk of the
      3.3x growth and likely improve bacterial fold coverage for ATB — but they inflate N
      and have no experimental structure.
- [ ] Freeze an `ecod.latest.domains` equivalent for v295 and pin the rep list to a file.

### Phase 1 — simple extractions (minutes)
Derived mechanically from the v295 domains file + rep list:
- [ ] `ECOD_length`, `ECOD_pdbmap`, `tgroup_length`, `ECOD_tgroup_sizes`
- [ ] `ECOD_maps/` (PDB resid → sequential position, one per rep)

### Phase 2 — structures (hours)
- [ ] Extract rep domain PDBs from parent structures, renumber → `ECOD_pdbs/`
- [ ] `dsspcmbi` per rep. *(QC: develop285 has 63,065 pdb but only 62,892 dssp — 173
      missing. Do not inherit that gap; make DSSP coverage an explicit gate.)*
- [ ] `foldseek createdb` → `ECOD_foldseek_DB*`
- [ ] **HHsearch DB: SKIP — already built.** Wire DPAM to
      `v295/hhsuite_db/db/ecod_v295_Fgroup` instead of the (stub) `pdb70*` in the bundle.

### Phase 3 — all-vs-all DALI (the real cost)

> **BUILD TOOLING DOES NOT EXIST — AND NEVER HAS.** Confirmed with RS 2026-07-21: the
> reference files were **inherited from the original DPAM implementation and tooled against,
> but never updated**. No script in `dpam_c2` produces `ecod_internal`, `posi_weights` or
> `ECOD_norms`; `ECOD_UPDATE_REQUIREMENTS.md` documents formats reverse-engineered from the
> inherited artifacts, not a build process. A v295 rebuild would be the **first reference
> regeneration in DPAM's history**.
>
> Phase 3 is therefore *write the tooling* **and then** run it — the compute estimate below
> covers only the second half. Budget three generators (norms, per-domain z/q histograms,
> per-position weights) plus a DALI driver, **and do Phase 3.5 first**.

Produces three interdependent files, all derived from the same alignment sweep:
- [ ] `ECOD_norms` — self/max alignment z-scores (one per rep)
- [ ] `ecod_internal/{shard}/{num}.info` — per-domain z/q-score hit distributions
      (**these are what make ztile/qtile self-normalizing — see §5**)
- [ ] `posi_weights/{shard}/{num}.weight` — per-position alignment frequency
- [ ] Pre-filter aggressively (same X-group, length ratio) as the requirements doc suggests
- [ ] ~~Check whether the v295 release process already ran all-vs-all DALI~~
      **ANSWERED 2026-07-21: NO. There is nothing to reuse.**
      `v295/clustering/` contains only `all_fgroups.json` (a list of F-group id strings).
      No `*dali*` / `*.dat` / `*zscore*` / `*align*` artifacts exist anywhere under v295.
      `V295_SEQUENCE_BUILD_SCOPE.md` confirms F40/F70/F99 clustering is **sequence-identity
      based**, not structural — the ECOD release process never runs all-vs-all DALI.
      Phase 3 must be built and run from scratch, in full.

### Phase 3.5 — reproduce develop285 first (DE-RISKING; do this before any v295 sweep)

The develop285 bundle was **inherited from the original DPAM implementation and tooled
against, never regenerated**. v295 would be the first rebuild ever attempted. Consequently
the format specs in `ECOD_UPDATE_REQUIREMENTS.md` were reverse-engineered from the artifacts
— they pin down *layout*, but not necessarily *semantics*:

- does a `.info` histogram contain **all** DALI hits, or z-thresholded ones?
- is `ECOD_norms` the **self**-alignment z-score, or the max over hits?
- what exactly does `posi_weights` count — aligned residues, or weighted by hit quality?
- which DaliLite parameters/cutoffs produced the inherited scores?

Get any of these subtly wrong and DOMASS's features shift on a scale the model never saw.
The failure mode is silent: no crash, just quietly worse assignments.

**The inherited bundle is the oracle.** Validate the new generators by making them
reproduce develop285 before pointing them at v295:

- [ ] **Pairwise spot-check (cheap, do first).** Pick ~200 (query, hit) pairs that appear in
      inherited `ecod_internal/*.info`. Re-run DALI on those exact pairs with the candidate
      parameters. Do we reproduce the recorded z/q-scores? This pins the alignment semantics
      *without* any all-vs-all sweep.
- [ ] **Aggregation check.** For a handful of domains, rebuild the `.info` histogram and
      `posi_weights` from re-derived hits and diff against the inherited files.
- [ ] **`ECOD_norms` semantics.** Test both hypotheses (self-alignment vs max-over-hits)
      against the inherited values — 62,653 rows is ample to disambiguate.
- [ ] Only once develop285 is reproducible, run the v295 sweep.

This converts an unbounded "did we get the semantics right?" risk into a bounded, cheap
experiment, and it is the single highest-value de-risking step in the plan.

### Phase 4 — DOMASS (§5)

### Phase 5 — validation (§6)

---

## 5. DOMASS: keep or retrain?

`ECOD_UPDATE_REQUIREMENTS.md` §DOMASS Reparameterization gives the criteria. Applying them
to v295:

**Arguments the model survives:**
- 6 of 13 features are ECOD-independent (domLen, Helix_num, Strand_num, HHprob, HHcov, Dzscore)
- `ztile`/`qtile` are percentiles **within each ECOD domain's own hit distribution**
  (`ecod_internal/*.info`), not against a global snapshot. Rebuild those distributions by the
  same procedure and the feature semantics are preserved — this is the strongest argument.
- `HHrank`/`Drank` are diversity measures, robust to moderate membership change
- The network is 13→64→2 learning "is this a good match?", not "which T-group?"
- v1 DOMASS was used across multiple ECOD releases without retraining
- T-groups moved only +0.2%, so the label space is effectively unchanged

**Arguments it does not:**
- The doc's explicit retraining trigger is *">30% of ECOD70 domains replaced"*. Moving
  63,064 domain-level reps → 32,084 F-group reps **far exceeds that**, whatever the merits.
- Candidate-set density changes: 3.3x more domains means more high-scoring wrong hits
  competing, which shifts rank-feature distributions in a direction the model never saw.

**Recommendation: keep `domass_epo29` initially, and treat this as an empirical question,
not an assumption.** Retraining is a genuine project — the v1 training workflow was never
released (requirements doc §"Retraining procedure (undocumented in v1)"), so it would have
to be reconstructed. Do not start there.

**Decision gate:** run the validation suite (§6) with the existing weights. If T-group
agreement holds ≥90% and the probability calibration is not degenerate, ship as-is. Only if
it fails do we reconstruct training.

**If retraining proves necessary**, the training data is self-generating from ECOD: run
steps 1–15 over domains with known assignments; positives = correct F-group, negatives =
high-scoring wrong pairs. The obstacle is the missing training harness, not the labels.

---

## 6. Validation

- [ ] Re-run the existing validation sets in `dpam_c2/` (`validation_1000`, `validation_10k`,
      `validation_swissprot*`) against the new reference
- [ ] Primary metric: **T-group agreement vs develop285 results, target ≥90%** (T-groups moved
      only +0.2%, so genuine disagreement indicates a pipeline problem, not ECOD drift)
- [ ] Check `ztile`/`qtile` distributions are not degenerate (all 0 / all 1 / bimodal) — the
      doc's named failure mode and the main risk from rebuilding `ecod_internal/`
- [ ] Compare DOMASS probability calibration old vs new; degradation here is the retraining trigger
- [ ] Confirm F-group ids resolve against `ecod.v295.f_id_pfam_acc.txt`

---

## 7. Open decisions (need RS)

1. **Rep set granularity** — F-group (32,084, recommended) vs domain-level (~63K)?
2. **AFDB-derived domains eligible as reps?** Better ATB coverage vs larger N and no
   experimental structure.
3. ~~Reusable DALI output in `v295/clustering/`?~~ **CLOSED — no.** See Phase 3. Nothing to
   reuse; the full sweep and its tooling must be built. This makes the rep-set choice (§3)
   and the develop285 oracle validation (Phase 3.5) the two decisions that matter most,
   since they set the cost and the correctness of the only expensive phase.
4. **Step 5/6 key handling** if HH evidence is F-group-keyed while DALI/foldseek are
   domain-keyed — needs a code change or a domain→F-group mapping layer.

---

## 8. Relationship to the ATB work

ATB domain assignment (`~/work/atbc`) is blocked on this only for *assignment*, not parsing.
Merizo segmentation is already done and PAE-free; DPAM's assignment stack (HHsearch + DALI →
DOMASS) needs no PAE. A v295-consistent reference is what makes those assignments trustworthy —
today's `atbc.domain_ecod_hits` are foldseek **neighbours only**, explicitly not assignments.
