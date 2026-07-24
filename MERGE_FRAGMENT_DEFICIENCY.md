# Merge-step deficiency: orphan fragments survive to final domains

**Found:** 2026-07-13, during the dpam_v5 reference-validation resplit campaign
(`~/work/afdb_200M/analysis/tier_a_run/`, 1,595 dpam_v5 domains re-parsed with dpam_c2).

## Symptom

DPAM emits sub-domain **fragments** as final domains — pieces far too small to be domains,
carrying a T-group assignment and a `simple_topology` judge.

Measured over 3,663 finalDPAM sub-domains from 1,553 resplit proteins
(fold-aware QC gate: fragment = smaller than *any* curated ECOD domain of its own T-group
AND < 0.5x that fold's median; see `analysis/tier_a_run/qc_gate.py`):

| | |
|---|--:|
| sub-domains judged FRAGMENT | **437 (11.9%)** |
| resplits containing >=1 fragment | **341 / 1,553 (22.0%)** |

Concentrated in repeat/solenoid folds — they are single repeat units and single propeller blades:

| T-group | fragments | fragment median len | ECOD curated median |
|---|--:|--:|--:|
| 109.4.1 ARM repeat | 171 | **25** | 282 |
| 5.1.4 7-bladed propeller | 42 | **30** | 348 |
| 207.1.1 LRR | 17 | 35 | 247 |
| 2004.1.1 P-loop | 11 | 30 | 224 |

## Root cause (traced end-to-end on AF-K7MVJ7-F1)

step13 domains:
```
D7   1196-1510,1536-1560     <-- D7 BRACKETS D8; the gap in D7 IS D8
D8   1511-1535               <-- 25aa fragment, physically embedded inside D7
D9   1561-1670
```
D8 is an insertion sitting *inside* D7 — maximally adjacent.

step19 proposed D8 against: **D1, D2, D4, D5, D6, D13** — all distant ARM domains that merely
share an ECOD template. It **never proposed D8 against D7 or D9** (its actual neighbours).
step21 then correctly judged every proposed pair `0` (not connected — they are ~1000 residues away).
D8 survives to finalDPAM as `nD2  1511-1535  109.4.1  simple_topology`.

**`D7` appears nowhere in the step19 candidate list at all.** Same for D12 and D14, which likewise
survive as 25aa fragments.

### The defect is in candidate GENERATION, not judgment

`dpam/steps/step19_get_merge_candidates.py` builds candidates **exclusively** from shared ECOD templates:

```python
for ecod_id, hits in ecod_to_hits.items():
    if len(hits) < 2:
        continue          # only domains WITH ECOD hits, paired with each other
```

Consequences:

1. **A domain with no ECOD hit is invisible to the merge step.** Any fragment whose only sensible
   merge partner lacks a template hit (D7, D12, D14) is permanently stranded.
2. **There is no adjacency-driven candidate rule.** Physical contiguity — the actual reason two
   pieces should merge — never generates a candidate. For repeat proteins this is perverse: the
   template-sharing rule proposes *every* ARM-vs-ARM pair (including distant ones), while never
   proposing the physically embedded neighbour.
3. **No minimum domain size is enforced anywhere** before final domains are emitted.

`step21_compare_domains.py` is behaving correctly — it rightly rejects merging a fragment with a
domain 1,000 residues away. It is simply being fed the wrong candidate set.

## Proposed fix

1. **step19: add adjacency-based candidates.** Propose any pair that is sequence-contiguous or
   structurally embedded, regardless of shared ECOD template. Fixes D8->D7 directly. Include
   ECOD-hitless domains as candidate partners.
2. **Orphan absorption pass (post-step22).** Any final domain below its T-group's curated size
   floor that is embedded in / adjacent to another domain is absorbed into it.
3. **Minimum domain size** before emitting final domains. DPAM already self-flags these as
   `simple_topology` — that signal plus a size floor is a cheap interim mitigation.

## Acceptance test

Re-run the 1,553 resplit proteins and re-apply `analysis/tier_a_run/qc_gate.py`.
Target: **FRAGMENT rate 11.9% -> ~0**, with no loss of the 420 genuine multi-T-group chimeras
or the 217 repeat-origin domain rescues (small-but-real domains such as Zn-fingers must survive —
the gate is fold-aware precisely so they do).

## Why this matters

We deliberately chose NOT to build a downstream fragment-merge, because these fragments already
survive DPAM's own merge (step19->21->22); a second merge would stack a competing heuristic on top
of DPAM's. The repair belongs here, at source.

---

## Why the adjacency rule was originally forgone — and how the fix preserves that safeguard

**Design intent (RS):** the adjacency rule was deliberately omitted to prevent domains of dissimilar
H/T groups being merged. The shared-ECOD-template requirement was doing real safety work: it ensured
two pieces only merge if they map to the SAME template, i.e. they are parts of ONE domain.

A naive "merge adjacent domains" rule would re-create under-splitting (fusing a kinase into its
neighbouring SH2, etc.). **So the adjacency rule must be GATED, not open.** Three conditions, ALL required:

1. **Fold-aware size floor (the discriminator).** Only a domain BELOW its own T-group's curated floor
   is eligible to be absorbed (floor = smaller than any curated ECOD domain of that fold AND < 0.5x its
   median; plus a 30-res absolute floor). A full-size domain is NEVER absorbable by adjacency.
   This is what protects small-but-real domains: a 30aa Zn-finger sits AT its T-group's curated min
   (~29) -> not eligible. A 25aa ARM piece is far below ARM's floor (median 282) -> eligible.
2. **H/T compatibility.** Absorb only if the fragment's T-group MATCHES the acceptor's (same H-group),
   OR one of them has no confident assignment. If BOTH carry confident but DIFFERENT H/T -> FORBIDDEN.
3. **Connectivity retained.** Keep step21's sequence/structure connectivity test unchanged.

Critically, this **preserves the domain-rescue cases**: a Zn-binding (or other) domain "eaten" by a
neighbouring ARM has a confident T-group different from ARM AND is at/above its own fold's floor ->
fails both (1) and (2) -> stays separate. That is the resplit we want.

### Empirical validation of the safeguard (over all 1,553 resplit proteins, 3,663 sub-domains)

| | |
|---|--:|
| fragments eligible (below fold floor) | 437 |
| -> absorbed (H/T-compatible acceptor) | **315** |
| -> **BLOCKED by the H/T gate** | **122** |
| small domains AT/ABOVE their fold floor (protected) | **361** |
| full-size domains (never eligible) | 2,865 |

The 122 blocked cases are exactly the ones a naive rule would have wrongly fused — e.g. a 95aa
TIM-barrel piece (2002.1.1), a 65aa RNase-H piece (2484.1.1), a 30aa 4.1.1 — each adjacent to a
domain of a DIFFERENT H-group.

**Net: FRAGMENT rate 11.9% -> 3.3% (437 -> 122).** It does NOT go to zero, deliberately: the residual
122 carry confident-but-dissimilar H/T assignments, so auto-merging them would commit precisely the
error the adjacency rule was forgone to avoid. Several are substantial (65-95aa) and are likely
genuinely truncated domains. **Route those to curation, not to a merge heuristic.**

=> Revised acceptance test: FRAGMENT 11.9% -> ~3% (auto-mergeable ones absorbed), 0 legitimate domains
absorbed, 420 multi-T-group chimeras and 217 repeat-origin rescues all preserved.

---

## STATUS: FIX IMPLEMENTED (2026-07-13)

`dpam/steps/step19_get_merge_candidates.py` — added a **gated adjacency pass** after the existing
template pass. It now also loads ALL step13 domains (previously step19 only saw domains present in
step18_mappings, which is exactly why the ECOD-hitless host D7 was invisible).

New reference data: **`ECOD_tgroup_sizes`** (t_id, n, min_len, p05, median over curated/experimental
ECOD domains; 3,950 T-groups) installed at `/home/rschaeff_1/data/dpam_reference/ecod_data/`.
Repo copy: `ECOD_tgroup_sizes.reference`. If absent, step19 degrades gracefully to the absolute floor.

Gates (all three required; constants `ABS_MIN_DOMAIN=30`, `ADJ_GAP_MAX=50`, `MIN_CURATED_N=3`):
  1. `is_fragment()`   — fold-aware size floor (protects small-but-real domains)
  2. `ht_compatible()` — same H-group, or one side unassigned (THE SAFEGUARD)
  3. `is_adjacent()`   — embedded in the acceptor's span, or within ADJ_GAP_MAX
step21's connectivity test still validates every proposed pair; step22 unchanged.

### Verified on the original failing case (AF-K7MVJ7-F1)
step19 now proposes the previously-invisible pair:
```
D8  1511-1535   D7  1196-1510,1536-1560
merge_info: D8,D7  ADJACENCY(frag=25aa, tg=109.4.1 -> NA)
```
5 adjacency candidates added (43 total, was 38). All are same-T-group or unassigned —
**zero cross-H/T proposals.**

### Regression test: `tests/test_step19_adjacency_merge.py` (13 tests, all passing)
Encodes the fix AND both safeguards, using the same fold-aware criterion as the campaign QC gate:
  - THE FIX: embedded fragment proposed against its ECOD-hitless host
  - SAFEGUARD 1: ARM fragment NOT proposed against an adjacent TIM barrel (different H-group)
  - SAFEGUARD 2: a 40aa domain in a fold whose curated min is 29 (Zn-finger class) is NOT absorbed
Existing `tests/integration/test_step19_get_merge_candidates.py` (8 tests) still passes -> the
template-based path is unchanged.
(Note: `tests/integration/test_step13_parse_domains.py` fails to collect — PRE-EXISTING, stale import
of `merge_segments_by_probability`, unrelated to this change.)

### Remaining
Full-scale acceptance still pending: re-run the 1,553 resplit proteins and re-apply
`analysis/tier_a_run/qc_gate.py`. Expected FRAGMENT 11.9% -> ~3% (the residual 122 carry
confident-but-dissimilar H/T and are correctly left for curation, not auto-merged).

---

## OUTCOME: fix REVERTED 2026-07-24 — the guard approach has a hard ceiling

The step19 adjacency merge (PR #2) and a follow-on step22 H-group / size-anchor guard were tested on
419 chimera proteins (whole-protein acceptance, `analysis/v295_1_rerun/`). Result:
- fragment rate 14.8% -> 7.8% (never near 0), AND
- **it INTRODUCED real over-merges** the original pipeline did not make: a genuine domain absorbed into
  an adjacent domain of a DIFFERENT fold. Best case (full size-anchor guard) still left **5/419 cross-X
  over-merges**.

**Root cause — a circular dependency (proven on AF-Q6FJL1):**
`is_fragment(len, T-group)` depends on the T-group assignment, which is itself unreliable for exactly
the ambiguous pieces the merge must decide on. Q6FJL1 D1 (45aa) hits BOTH 145.1.1 (prob 0.90, where 45aa
is a real domain) AND 207.1.1 (prob 0.96, where 45aa is a fragment). The fragment verdict — and thus
whether D1 is absorbed into the neighbouring LRR — flips depending on which ambiguous hit you believe.
No guard built on the T-group signal can resolve this; that is why the guards kept accumulating without
closing (bridge -> H-group guard -> size anchor -> ...).

**Decision (RS):** revert step19 + step22 to the original merge (the fragment tail is cosmetic — 25aa
slivers a curator ignores; the over-merges are real classification errors). `addss-modern-blastfree`
(PR #1) is KEPT. This doc + `ECOD_tgroup_sizes.reference` are kept as the record.

**The real fix (separate project): decide domain-hood from STRUCTURE, not from the circular ECOD
assignment.** A piece is a domain iff it folds as an independent unit (PAE/contact-based cohesion),
independent of what T-group it maps to. That breaks the circularity the guard approach cannot.

### v295.1 consequence
Do NOT use fixed-dpam_c2 boundaries. Adopt the ORIGINAL finalDPAM boundaries with the fold-aware
`qc_gate.py` as an ADOPTION-TIME filter (don't promote sub-floor slivers to F-group reps; merge nothing),
which never over-merges a real domain. See `analysis/dpam_v5_strategy/V295_1_PLAN.md`.
