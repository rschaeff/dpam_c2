# Rust DALI Backend Validation Report

**Date:** 2025-02-15
**Status:** Promising but not production-ready
**dali_cl commit:** `0ad98aa`
**dpam_c2 branch:** unstaged changes on `main`

## Summary

The Rust DALI backend (`dali_cl`) is a drop-in replacement for Fortran
DaliLite.v5 in DPAM's step 07 (iterative DALI alignment). Four deficiencies
were identified during initial integration testing and subsequently fixed.
This report documents the verification of those fixes and characterizes
remaining divergence between backends.

**Key result:** The indexing fix dramatically improved alignment accuracy
(qscore agreement 49% -> 88%), and .dat bypass improves z-score agreement
among high-confidence hits to 94%. However, inherent algorithmic divergence
(DSSP + WOLF/PARSI) causes 18-51% of Fortran hits to be missed entirely,
including occasional high-scoring hits. The backend is not yet suitable for
production use.

## Deficiencies and Fixes

### Deficiency 1: Off-by-one in alignment indices (FIXED)

`align_pdb()` returned raw PDB residue numbers instead of 1-based sequential
indices. For templates with non-standard PDB numbering (e.g., residues 2-87),
this caused alignment pairs to be shifted, corrupting downstream qscore and
domain range calculations.

**Fix:** `align_pdb()` now returns 1-based sequential indices consistent with
the Fortran `.dat` convention. Verified via self-alignment of template
000005249 (PDB residues 2-87, 86 residues): indices correctly in [1, 86].

**Impact:** Qscore agreement improved from 49% to 88% on AF-Q97ZL0-F1.

### Deficiency 2: DSSP divergence (MITIGATED)

Rust's built-in DSSP (based on BioJava) assigns different secondary structure
than Fortran's `dsspcmbi`. Since DALI uses secondary structure for scoring and
segment definition, this causes z-score differences and missed hits.

**Mitigation:** Added `.dat` bypass — when a pre-computed Fortran `.dat` file
is available for a template, the Rust backend loads it directly, skipping Rust
DSSP for the template side. This eliminates template-side DSSP divergence.

Query-side DSSP divergence remains (AlphaFold query structures have no
pre-existing `.dat` files).

**Impact:** Z-score agreement among high-confidence hits (z >= 5) improved
from 77% to 94% on AF-Q97ZL0-F1.

### Deficiency 3: 5-character ECOD codes (FIXED)

Rust's `import_pdb()` truncated 5-character codes. Fixed with proper handling
of 4- and 5-character identifiers.

### Deficiency 4: `ResidNumbering` enum (FIXED)

Added `numbering` field and `resid_map` accessor to the Python bindings,
enabling DPAM to map between sequential indices and PDB residue numbers.

## Test Results

### dali_cl Unit Tests

All 17 tests pass:
- 10 binding tests (import, alignment, .dat roundtrip, residue mapping)
- 7 coverage tests (sequential indices, .dat bypass, numbering consistency,
  small domain self-alignment, rotation matrices)

### DPAM Integration: Head-to-Head Comparison

Two test proteins run through step 07 with both backends, with and without
`.dat` bypass. Step 08 (analyze_dali) run on outputs to compute qscores.

#### AF-Q97ZL0-F1 (161 DALI candidates, Fortran: 151 hits)

**High-confidence hits (z >= 5.0):**

| Condition       | Common | Fortran-only | Rust-only | Z-agree (±0.5) |
|-----------------|--------|--------------|-----------|----------------|
| Pre-fix         | —      | —            | —         | ~63%           |
| Post-fix no .dat| 70     | 32           | 0         | 77%            |
| Post-fix + .dat | 77     | 25           | 1         | **94%**        |

**All hits (z >= 2.0), post-fix:**

| Condition       | Common | Fortran-only | Rust-only | Z-agree | Q-agree |
|-----------------|--------|--------------|-----------|---------|---------|
| No .dat         | 124    | 27           | 0         | 63%     | 88%     |
| With .dat       | 119    | 32           | 0         | 75%     | 86%     |

#### AF-P06596-F1 (213 DALI candidates, Fortran: 57 hits)

**z >= 4.0:**

| Condition       | Common | Fortran-only | Rust-only | Z-agree |
|-----------------|--------|--------------|-----------|---------|
| No .dat         | 26     | 1            | 0         | 100%    |
| With .dat       | 26     | 1            | 0         | 100%    |

At z >= 4.0 for this protein, agreement is perfect except for one outlier.

## Remaining Issues

### 1. Hit coverage gap (49-82%)

Rust consistently misses a significant fraction of Fortran hits. Most are
borderline (z < 3-4) and unlikely to affect domain assignments, but some
high-scoring hits are also missed:

- **AF-P06596-F1, domain 001145648:** Fortran z=16.6, Rust returns `None`.
  Root cause: Rust DSSP assigns only 3 secondary structure segments to this
  118-residue template (vs ~7-8 from Fortran dsspcmbi). Fewer segments give
  WOLF fewer anchor points, causing complete alignment failure. Self-alignment
  succeeds (z=26.8), confirming the issue is DSSP-dependent, not structural.

- **AF-Q97ZL0-F1, domain 000150428:** Fortran z=9.2, Rust misses with .dat
  bypass. Query-side DSSP divergence.

### 2. Query-side DSSP divergence is not addressable via .dat bypass

The `.dat` bypass only helps the template side. For production use, one would
need to also pre-compute query `.dat` files using Fortran DaliLite, which
changes the pipeline workflow.

### 3. Speed advantage is marginal to negative in practice

Raw per-alignment microbenchmarks show ~2x Rust advantage, but in the full
step 07 pipeline the picture is different:

| Protein | Fortran | Rust (no .dat) | Rust (.dat) |
|---------|---------|----------------|-------------|
| Q97ZL0 (161 cands) | 9.7s | 5.5s (1.8x) | 9.1s (1.1x) |
| P06596 (213 cands) | 11.2s | 8.6s (1.3x) | 21.8s (**0.5x**) |

The no-.dat speedup is inflated because Rust finds fewer hits (less work).
With .dat bypass, loading .dat files from disk adds I/O overhead that can
make Rust **slower** than Fortran. Multiprocessing pool overhead, PDB
parsing, and hit file writing dominate wall-clock time; the alignment kernel
is a small fraction per worker.

A proper benchmark (not yet done) would need to control for equal hit counts,
measure per-alignment time in isolation, and test across worker counts and
I/O configurations (NFS vs local scratch). Until then, speed is not a
compelling argument for the Rust backend.

## Generating .dat Files

For the `.dat` bypass to work, Fortran `.dat` files must be pre-generated for
ECOD70 templates. The procedure:

```bash
# For each template PDB:
~/src/Dali_v5/DaliLite.v5/bin/import.pl \
    --pdbfile /path/to/ECOD70/{edomain}.pdb \
    --pdbid test \
    --dat /tmp/workdir

# Rename output (import.pl produces testA.dat)
mv /tmp/workdir/testA.dat /path/to/dat_cache/{edomain}.dat
```

A parallel generation script produced 373/374 `.dat` files for the test set
in ~2 minutes (8 workers). One template (000296559) failed due to too few
residues for DaliLite's DSSP.

For full ECOD70 (~63,000 templates), expect ~30-60 minutes with 8 workers.

## Conclusion

The deficiency fixes are verified and effective:

1. **Indexing fix** is the most impactful change (qscore agreement 49% -> 88%)
2. **.dat bypass** significantly improves z-score agreement for high-confidence
   hits (77% -> 94% at z >= 5)
3. Remaining divergence is inherent to WOLF/PARSI algorithm and DSSP
   differences, not fixable without upstream changes to dali_cl

The Rust backend shows promise as a faster, dependency-free alternative to
Fortran DaliLite, but the hit coverage gap (especially occasional misses of
high-scoring hits like z=16.6) means it is **not yet suitable for production
DPAM runs** where completeness matters. It may be appropriate for:

- Screening / fast pre-filtering where some hit loss is acceptable
- Environments where Fortran DaliLite is unavailable
- Development and testing workflows

Further work needed:
- Investigate and reduce DSSP divergence in dali_cl (nseg=3 vs ~7 cases)
- Consider pre-computing query .dat files for full Fortran DSSP parity
- Larger-scale validation (100+ proteins) to characterize hit loss rate
  and downstream impact on domain predictions
