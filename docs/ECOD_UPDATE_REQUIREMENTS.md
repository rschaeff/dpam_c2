# ECOD Update Requirements for DPAM v2

**Date:** 2026-02-27
**Status:** Reference document for ECOD version updates

## Overview

DPAM v2 depends on ~12 distinct reference data files derived from ECOD. This
document specifies each file's exact format, which pipeline steps consume it,
how it was historically generated, and what changes during an ECOD version
update.

**Current data**: ECOD develop285, ~63,000 ECOD70 representative domains.

---

## Quick Reference: Files and Consumers

| File | Format | Entries | Consumer Steps | Update Sensitivity |
|------|--------|---------|----------------|-------------------|
| `ecod.latest.domains` | TSV, 16 cols | ~800K+ | 08, 15, 23 | **Source of truth** — drives everything |
| `ECOD_length` | WSV, 3 cols | 63,065 | 08, 23 | Low: simple extraction |
| `ECOD_norms` | WSV, 2 cols | 62,653 | 08 | **High: requires all-vs-all DALI** |
| `ECOD_pdbmap` | WSV, 3 cols | 63,065 | 05, 06 | Low: simple extraction |
| `ECOD70/` (= `ECOD_pdbs/`) | PDB + DSSP | 63,065 + 62,892 | 07, 08 | Medium: structure extraction |
| `posi_weights/{shard}/` | WSV, 4 cols | ~63K files | 08, 23 | **High: requires all-vs-all DALI** |
| `ecod_internal/{shard}/` | Alignment+scores | ~63K files | 08 | **High: requires all-vs-all DALI** |
| `ECOD_maps/` | WSV, 2 cols | 63,066 | 15, 18 | Low: PDB→sequential mapping |
| `tgroup_length` | WSV, 2 cols | 3,914 | 23 | Low: aggregate from ECOD_length |
| `pdb70*` (HHsearch DB) | FFdata/FFindex | — | 02 | Medium: HHsuite `ffindex_build` |
| `ECOD_foldseek_DB*` | Foldseek DB | — | 03 | Medium: `foldseek createdb` |
| `domass_epo29.*` | TF1 checkpoint | 3 files | 16 | **Low unless reclassification** |

**WSV** = whitespace-separated values.

---

## File Format Specifications

### 1. `ecod.latest.domains`

**Source**: ECOD database export. The canonical ECOD domains file.

**Format**: Tab-separated, 16 columns. First 3 lines are comments (`#`).

```
#/data/ecod/database_versions/v285/ecod.develop285.domains.txt
#ECOD version develop285
#Domain list version 1.6
000000003  e2rspA1  AUTO_NONREP  1.1.1.1  2rsp  A  A:1-124  ...  (16 cols total)
```

**Columns**:
| # | Name | Example | Used By |
|---|------|---------|---------|
| 0 | uid (ecod_num) | `000000003` | Key everywhere |
| 1 | ecod_domain_id | `e2rspA1` | ECOD_length col 2, step 15 |
| 2 | manual_rep | `AUTO_NONREP` | Not used |
| 3 | f_id (full hierarchy) | `1.1.1.1` (X.H.T.F) | T-group, H-group, family extraction |
| 4 | pdb | `2rsp` | Not used directly |
| 5 | chain | `A` | Not used directly |
| 6-15 | pdb_range, seqid_range, etc. | ... | Not used by DPAM |

**DPAM extractions from col 3 (f_id)**:
- **Family** (H-group): first 2 levels → `1.1` (used in step 08)
- **T-group**: first 3 levels → `1.1.1` (used in steps 15, 23)
- **H-group**: first 2 levels → `1.1` (used in step 15 for HHrank)

**Loaded by**: `reference_data.load_ecod_domains_file()` → `Dict[ecod_num → (ecod_id, family)]`

**Generation**: Direct export from ECOD database. No transformation needed.

---

### 2. `ECOD_length`

**Source**: Derived from ECOD70 domain coordinates.

**Format**: Whitespace-separated, 3 columns.
```
000000003  e2rspA1  124
000000017  e2pmaA1  141
```

| Col | Content | Type |
|-----|---------|------|
| 0 | ecod_num | string (9-digit zero-padded) |
| 1 | ecod_key (domain id) | string |
| 2 | domain length (residues) | int |

**Loaded by**: `reference_data.load_ecod_lengths()` → `Dict[ecod_num → (ecod_key, length)]`

**Consumers**: Step 08 (normalize qscore), Step 23 (fallback weights when posi_weights missing)

**Generation**: Count residues in each ECOD70 PDB file, or extract from `ecod.latest.domains` column 7 (pdb_range). Pseudocode:
```python
for domain in ecod70_domains:
    length = count_residues(f"ECOD70/{domain.ecod_num}.pdb")
    print(f"{domain.ecod_num}\t{domain.ecod_id}\t{length}")
```

---

### 3. `ECOD_norms`

**Source**: All-vs-all DALI alignment of ECOD70 representatives. Each entry is the self-alignment Z-score (or a comparable normalization value).

**Format**: Whitespace-separated, 2 columns.
```
000423727  27.3
001821129  27.4
```

| Col | Content | Type |
|-----|---------|------|
| 0 | ecod_num | string |
| 1 | normalization value | float |

**Loaded by**: `reference_data.load_ecod_norms()` → `Dict[ecod_num → float]`

**Consumers**: Step 08 (not directly used in current v2 code path — present for v1 compatibility)

**Generation**: **Requires all-vs-all DALI.** Run self-alignment for each ECOD70 domain and record the Z-score. The normalization value appears to be max Z-score from internal comparisons.

**Note**: 62,653 entries vs 63,065 in ECOD_length — some domains too small for DALI self-alignment.

---

### 4. `ECOD_pdbmap`

**Source**: Derived from ECOD domain definitions.

**Format**: Whitespace-separated, 3 columns.
```
000000003  2rsp  A:1-124
000000017  2pma  A:4-144
000000020  1eu1  A:626-780
```

| Col | Content | Type |
|-----|---------|------|
| 0 | ecod_num | string |
| 1 | pdb_id (lowercase 4-char) | string |
| 2 | chain:ranges | string (e.g., `A:1-124` or `A:10-50,A:60-100`) |

**Loaded by**: `reference_data.load_ecod_pdbmap()` → `Dict[PDB_CHAIN → (ecod_num, chain, residues)]`

Key is `{PDB_ID_UPPER}_{chain}` (e.g., `2RSP_A`). Only single-chain domains are loaded.

**Consumers**: Step 05 (MAP_ECOD — maps foldseek PDB hits to ECOD domains), Step 06 (DALI_CANDIDATES)

**Generation**: Extract from `ecod.latest.domains` columns 0, 4, 6 (uid, pdb, pdb_range).

---

### 5. `ECOD70/` (symlink to `ECOD_pdbs/`)

**Source**: Domain PDB files extracted from parent PDB structures.

**Format**: Flat directory containing `{ecod_num}.pdb` and `{ecod_num}.dssp` files.
- **63,065** `.pdb` files
- **62,892** `.dssp` files (173 fewer — some fail DSSP)
- **11 subdirectories** for multi-chain domains (contain chain-specific files)

PDB files use chain A, renumbered to sequential 1-based residue numbers:
```
ATOM      1  N   LEU A   1       0.921  29.839  56.196  1.00  0.00           N
ATOM      2  CA  LEU A   1       2.437  29.879  56.145  1.00  0.00           C
```

**Consumers**: Step 07 (ITERATIVE_DALI — template structures for alignment)

**Generation**: For each ECOD70 representative domain:
1. Extract domain residues from parent PDB using ECOD range
2. Renumber to sequential 1-based
3. Write as single-chain PDB (chain A)
4. Run DSSP (`dsspcmbi` or `mkdssp`) to generate `.dssp` file

This is the most I/O-intensive generation step (~63K PDB extractions). Likely
done via ECOD's own domain extraction pipeline.

---

### 6. `posi_weights/{shard}/{ecod_num}.weight`

**Source**: **All-vs-all DALI alignment.** Position conservation weights derived from structural alignment of each ECOD70 domain against all other ECOD70 domains.

**Format**: Whitespace-separated, 4 columns. Sharded by last 2 digits of ecod_num (100 subdirectories: `00/` through `99/`).

```
1   137  408  0.34
2   140  408  0.34
3   141  408  0.35
```

| Col | Content | Type | Interpretation |
|-----|---------|------|----------------|
| 0 | position (1-based) | int | Residue position in domain |
| 1 | aligned_count | int | Number of ECOD70 hits aligning this position |
| 2 | total_hits | int | Total number of ECOD70 hits (same for all positions) |
| 3 | weight | float | `aligned_count / total_hits` |

Number of rows = domain length (matches ECOD_length).

**Loaded by**: `reference_data.load_ecod_weights()` → `Dict[position → weight]`

**Consumers**:
- **Step 08**: Computes qscore = `Σ weight[template_res] / total_weight` for aligned positions
- **Step 23**: Computes weighted coverage ratio for full/part classification

**Generation**: **This is the most expensive reference data to generate.** Requires running DALI for every ECOD70 domain against every other ECOD70 domain, then counting how often each residue position participates in a structural alignment.

Pseudocode:
```python
for domain in ecod70:
    hit_count = 0
    position_counts = {pos: 0 for pos in range(1, domain.length + 1)}
    for other_domain in ecod70:
        alignment = dali_align(domain, other_domain)
        if alignment.zscore >= threshold:
            hit_count += 1
            for (qres, tres) in alignment.pairs:
                position_counts[tres] += 1
    for pos in sorted(position_counts):
        weight = position_counts[pos] / hit_count
        print(f"{pos}\t{position_counts[pos]}\t{hit_count}\t{weight:.2f}")
```

**Database alternative**: `ecod_commons.dpam_position_weights(ecod_num, position, weight)`

**Critical note**: The v1 code in `step23_get_predictions.py` loads weights by **ecod_num** (e.g., `posi_weights/000000003.weight`), using flat layout. The v2 code supports both sharded and flat layout.

---

### 7. `ecod_internal/{shard}/{ecod_num}.info`

**Source**: **All-vs-all DALI alignment.** Each file contains the alignment results of one ECOD70 domain against all other ECOD70 domains.

**Format**: Whitespace-separated, 3+ columns. Sharded by last 2 digits of ecod_num.

```
000423727  10.0  67.08  lamtmehkDRPLVR...
001821129   8.5  68.14  ------lamtmeHK...
```

| Col | Content | Type |
|-----|---------|------|
| 0 | hit ecod_num | string |
| 1 | zscore | float |
| 2 | qscore (raw, not normalized) | float |
| 3+ | alignment string | string (optional, not parsed by DPAM) |

Number of rows = number of ECOD70 domains that aligned with z >= threshold.

**Loaded by**: `reference_data.load_ecod_domain_info()` → `(zscores_list, qscores_list)`

**Consumers**: Step 08 — used to compute **percentiles**:
- `ztile = fraction of reference zscores > query zscore` (0.0 = best)
- `qtile = fraction of reference qscores > query qscore` (0.0 = best)

These percentiles are ML features for DOMASS (step 15/16).

**Generation**: Same all-vs-all DALI run that produces `posi_weights`. For each domain, record all hits with their z-scores and q-scores.

**Database alternative**: `ecod_commons.dpam_domain_scores(ecod_num, hit_ecod_num, zscore, qscore)`

---

### 8. `ECOD_maps/{ecod_num}.map`

**Source**: Mapping from PDB residue numbers to sequential ECOD domain positions.

**Format**: Whitespace-separated, 2 columns. Flat directory (not sharded). **63,066 files**, named by ecod_num.

```
1  1
2  2
3  3
```

For domains with standard numbering (chain starts at 1), this is an identity mapping. For domains extracted from multi-domain chains, PDB numbers differ from sequential positions.

| Col | Content | Type |
|-----|---------|------|
| 0 | PDB residue number (from ECOD70 PDB file) | int |
| 1 | ECOD sequential position | int |

**Consumers**:
- **Step 15** (PREPARE_DOMASS): Maps DALI template residues through ECOD map to get sequential positions for consensus features
- **Step 18** (GET_MAPPING): Maps aligned residues for merge candidate identification

**Note**: V1 `step15_prepare_domass.py` opens maps as `ECOD_maps/{ecodid}.map` using the **ecod_num** from `_good_hits` column 1, which despite the variable name `ecodid` is actually `ecod_num`. The naming is confusing but consistent.

**Generation**: For each ECOD70 domain PDB, create mapping from ATOM record residue numbers to sequential 1-based positions:
```python
for domain_pdb in ecod70_pdbs:
    resids = sorted(set(atom.resid for atom in domain_pdb.atoms))
    for seq_pos, pdb_resid in enumerate(resids, 1):
        print(f"{pdb_resid}\t{seq_pos}")
```

---

### 9. `tgroup_length`

**Source**: Average domain length per ECOD T-group.

**Format**: Whitespace-separated, 2 columns.
```
1.1.1  178.0
1.1.2  135.0
1.1.3   68.0
```

| Col | Content | Type |
|-----|---------|------|
| 0 | T-group ID (X.H.T format) | string |
| 1 | average length | float |

**3,914 entries** (one per T-group).

**Loaded by**: Step 23 directly (not via reference_data.py)

**Consumers**: Step 23 — computes `length_ratio = domain_length / tgroup_avg_length` for full/part classification threshold.

**Generation**: Group ECOD_length entries by T-group (from ecod.latest.domains col 3), compute mean length per group:
```python
from collections import defaultdict
tgroup_lengths = defaultdict(list)
for ecod_num, (ecod_id, length) in ecod_lengths.items():
    tgroup = '.'.join(ecod_metadata[ecod_num].f_id.split('.')[:3])
    tgroup_lengths[tgroup].append(length)
for tgroup in sorted(tgroup_lengths):
    avg = sum(tgroup_lengths[tgroup]) / len(tgroup_lengths[tgroup])
    print(f"{tgroup}\t{avg:.1f}")
```

---

### 10. `pdb70*` (HHsearch Database)

**Source**: HHsuite-format profile database of ECOD70 representatives.

**Files** (symlinked to `/home/rschaeff/search_libs/`):
- `pdb70_a3m.ffdata` / `pdb70_a3m.ffindex` — MSA profiles
- `pdb70_hhm.ffdata` / `pdb70_hhm.ffindex` — HMM profiles
- `pdb70_cs219.ffdata` / `pdb70_cs219.ffindex` — context state profiles

**Consumers**: Step 02 (HHSEARCH — `hhsearch -i query.hmm -d pdb70`)

**Generation**: Requires HHsuite tools:
1. For each ECOD70 domain, generate MSA via `hhblits` against UniRef30
2. Add secondary structure via `addss.pl`
3. Build HMM via `hhmake`
4. Build database via `ffindex_build` from individual profiles

This is computationally expensive (~1-2h per domain for hhblits, parallelizable).

**ECOD key format**: Database entries are keyed by ecod_num (visible in hhsearch output as hit identifiers).

---

### 11. `ECOD_foldseek_DB*` (Foldseek Database)

**Source**: Foldseek structure database of ECOD70 representatives.

**Files**:
- `ECOD_foldseek_DB` (main data, 10.8MB)
- `ECOD_foldseek_DB.index` (1.1MB)
- `ECOD_foldseek_DB.lookup` (1.6MB) — maps index → `{ecod_num}.pdb`
- `ECOD_foldseek_DB.source` (1.2MB)
- `ECOD_foldseek_DB.dbtype`
- `ECOD_foldseek_DB_ca*` (C-alpha coordinates, 128MB)
- `ECOD_foldseek_DB_h*` (header)
- `ECOD_foldseek_DB_ss*` (secondary structure)

**Consumers**: Step 03 (FOLDSEEK — `foldseek easy-search` or `createdb`+`search`)

**Generation**:
```bash
foldseek createdb ECOD_pdbs/ ECOD_foldseek_DB --chain-name-mode 0
```

Lookup entries confirm ecod_num-based naming:
```
0  000000003.pdb  1
1  000000017.pdb  33
2  000000020.pdb  53
```

Fast to generate (~minutes for 63K structures).

---

### 12. `domass_epo29.*` (DOMASS ML Model)

**Source**: Trained TensorFlow 1.x model checkpoint.

**Files**:
- `domass_epo29.data-00000-of-00001` (12KB — weights)
- `domass_epo29.index` (492B — variable index)
- `domass_epo29.meta` (42KB — graph definition)

**Consumers**: Step 16 (RUN_DOMASS — loads graph, runs inference)

**Architecture**: 13 input features → 64-neuron hidden layer → 2-class softmax

**13 input features** (from step 15):
1. `domLen` — domain length (ECOD-independent)
2. `Helix_num` — helix count (ECOD-independent)
3. `Strand_num` — strand count (ECOD-independent)
4. `HHprob` — HHsearch probability (ECOD-independent per query)
5. `HHcov` — HHsearch coverage (ECOD-independent per query)
6. `HHrank` — avg H-group diversity per residue / 10 (ECOD-dependent via H-group definitions)
7. `Dzscore` — DALI z-score / 10 (ECOD-independent per alignment)
8. `Dqscore` — weighted qscore (ECOD-dependent via posi_weights)
9. `Dztile` — z-score percentile (ECOD-dependent via ecod_internal)
10. `Dqtile` — q-score percentile (ECOD-dependent via ecod_internal)
11. `Drank` — DALI family diversity rank / 10 (ECOD-dependent via family definitions)
12. `Cdiff` — mean HH-DALI template position difference (weakly ECOD-dependent)
13. `Ccov` — fraction of domain covered by both methods (weakly ECOD-dependent)

**Update sensitivity**: See [DOMASS Reparameterization](#domass-reparameterization) section below.

---

## Dependency Graph

```
ecod.latest.domains (source of truth)
  ├── ECOD_length          (extract: uid, domain_id, count residues)
  ├── ECOD_pdbmap          (extract: uid, pdb, pdb_range)
  ├── tgroup_length        (aggregate: ECOD_length grouped by T-group)
  ├── ECOD70/ PDB files    (extract domains from parent PDBs)
  │     ├── ECOD70/ DSSP   (run dsspcmbi on each PDB)
  │     ├── ECOD_foldseek_DB  (foldseek createdb on ECOD70/)
  │     ├── pdb70*          (hhblits + hhmake + ffindex_build)
  │     └── ECOD_maps/      (PDB resid → sequential position mapping)
  │
  └── All-vs-all DALI      (DALI each ECOD70 domain vs all others)
        ├── ECOD_norms      (self-alignment z-scores)
        ├── ecod_internal/  (per-domain hit lists with z/q-scores)
        └── posi_weights/   (per-position alignment frequency)
```

---

## Update Procedure Checklist

### Phase 0: Prerequisites

- [ ] New `ecod.latest.domains` file from ECOD database
- [ ] New ECOD70 representative set defined (F70 clustering)
- [ ] Access to parent PDB files for domain extraction

### Phase 1: Simple Extractions (minutes)

These can be generated directly from `ecod.latest.domains` and the ECOD70 PDBs:

- [ ] **ECOD_length**: Extract ecod_num, ecod_id, residue count from ECOD70 PDBs
- [ ] **ECOD_pdbmap**: Extract ecod_num, pdb_id, chain:ranges from domains file
- [ ] **tgroup_length**: Aggregate ECOD_length by T-group (from domains file col 3)
- [ ] **ECOD_maps/**: Generate PDB→sequential maps for each ECOD70 PDB

### Phase 2: Structure Processing (hours)

- [ ] **ECOD70/ PDB files**: Extract domain PDBs from parent structures, renumber
- [ ] **ECOD70/ DSSP files**: Run `dsspcmbi` on each ECOD70 PDB
- [ ] **ECOD_foldseek_DB**: `foldseek createdb ECOD70/ ECOD_foldseek_DB`
- [ ] **pdb70 HHsearch DB**: For each domain, run `hhblits` → `addss.pl` → `hhmake`, then `ffindex_build`. (**Bottleneck**: ~1-2h per domain with hhblits; ~63K domains. Highly parallelizable on SLURM.)

### Phase 3: All-vs-All DALI (days-weeks)

This is the most expensive step. Generates three interdependent reference files.

- [ ] **Run all-vs-all DALI**: Each of ~63K ECOD70 domains aligned against all others. With N domains, this is O(N²) = ~4 billion pairwise alignments, though symmetry and Z-score thresholds reduce this significantly.
- [ ] **ECOD_norms**: Extract self-alignment (or max) Z-scores
- [ ] **ecod_internal/**: For each domain, collect all hit z-scores and q-scores
- [ ] **posi_weights/**: For each domain, count per-position alignment frequency across all hits

**Estimated compute**: With Fortran DaliLite at ~50ms per alignment on average, 63K × 63K / 2 ≈ 2 billion alignments ≈ 100M seconds ≈ 3.2 years of single-core time. With 1000 cores: ~1.2 days. Pre-filtering (same X-group, similar length) would reduce this dramatically.

**Alternative**: If the ECOD update process already runs all-vs-all DALI for clustering, the alignment results can be repurposed directly.

### Phase 4: DOMASS Model (optional)

- [ ] Evaluate whether DOMASS retraining is needed (see below)
- [ ] If retraining: generate training data from new ECOD, retrain, validate
- [ ] If not: copy existing `domass_epo29.*` files unchanged

### Phase 5: Validation

- [ ] Run DPAM on validation protein set with new reference data
- [ ] Compare domain predictions against previous ECOD version
- [ ] Check T-group agreement rate (target: >90%)
- [ ] Verify percentile distributions are reasonable (not all 0 or all 1)

---

## DOMASS Reparameterization

### When retraining is NOT needed

For incremental ECOD updates (new PDB structures added, minor reclassification):

1. **6 of 13 features are ECOD-independent** (domLen, Helix_num, Strand_num, HHprob, HHcov, Dzscore)
2. **The model is a simple 13→64→2 network** with a broad decision boundary — it's learning "is this a good match?" not "which exact T-group?"
3. **V1 DOMASS was used across multiple ECOD releases** without retraining
4. **Percentile features (ztile, qtile) are self-normalizing** — they're relative rankings within each domain's hit distribution, so absolute score shifts don't matter
5. **HHrank and Drank are diversity measures** — robust to moderate changes in family membership

**Recommendation**: For standard ECOD updates, keep the existing model and run the validation suite. If T-group agreement drops below 90%, investigate before retraining.

### When retraining IS needed

1. **Major ECOD reclassification** — H-group or T-group hierarchy changes significantly
2. **Dramatic changes to ECOD70 representative set** — >30% of domains replaced
3. **Score distribution shift** — if percentile features become bimodal or degenerate due to very different hit counts
4. **Validation failure** — T-group agreement drops below acceptable thresholds

### Retraining procedure (undocumented in v1)

The original DOMASS training workflow was not included in the DPAM v1 source.
Retraining would require:

1. Generate training data: run DPAM steps 1-15 on a curated set of proteins with known domain assignments
2. Label examples: `positive` = correct ECOD assignment (domain maps to correct T-group), `negative` = incorrect
3. Train: TF1 `tf.train.AdamOptimizer`, 29 epochs, batch training on 13 features
4. Validate: holdout set T-group agreement

---

## Cross-Step Key Conventions

### ecod_num vs ecod_id

These are frequently confused in variable names:

| Identifier | Format | Example | Used As |
|------------|--------|---------|---------|
| ecod_num (uid) | 9-digit zero-padded | `000000003` | File naming, DB keys, all reference files |
| ecod_id (ecod_domain_id) | `e{pdb}{chain}{domain}` | `e2rspA1` | ECOD_length col 1, human-readable |

**All file-based lookups use ecod_num.** The v1 code sometimes uses variable name `ecodid` when it actually contains `ecod_num` (e.g., `step9_analyze_dali.py` line 57: `ecodid = ecod2id[ecodnum]` where `ecod2id` maps num→id, but later `ecodid` in `step15` column 1 of `_good_hits` is actually ecod_num).

### Sharding convention

`posi_weights/` and `ecod_internal/` use last 2 digits of ecod_num as subdirectory:
- `000000003` → shard `03/`
- `000423727` → shard `27/`

V2 code falls back to flat layout if sharded path doesn't exist.

### ECOD70 PDB numbering

ECOD70 PDB files use **sequential 1-based numbering** (residues always start at 1). The `ECOD_maps/` files provide the reverse mapping to original PDB numbering when needed.

---

## Database-Backed Alternative

DPAM v2 supports loading `posi_weights` and `ecod_internal` from PostgreSQL
instead of files, which is faster for batch processing:

- **Table**: `ecod_commons.dpam_position_weights(ecod_num, position, weight)`
- **Table**: `ecod_commons.dpam_domain_scores(ecod_num, hit_ecod_num, zscore, qscore)`
- **Connection**: `dione:45000/ecod_protein` (user: ecod)

See `dpam/io/reference_data.py` for `batch_load_weights_db()` and
`batch_load_domain_info_db()` functions. These provide ~76x speedup for batch
step 08 processing.

When updating ECOD, both file-based and database representations need to be
updated in sync.

---

## Known Issues

1. **ecod_internal format is richer than parsed**: Files contain alignment strings
   (col 3+) that DPAM ignores. Only cols 0-2 (ecod_num, zscore, qscore) are used.

2. **ECOD_norms may be vestigial**: The v2 code loads it in `load_ecod_data()` but
   the current step 08 implementation doesn't use it for score normalization.
   Retained for backward compatibility.

3. **Missing DSSP files**: 173 of 63,065 ECOD70 domains lack `.dssp` files (too
   small for DSSP). These domains can still be used for DALI alignment but may
   produce different results with Fortran vs Rust backends.

4. **UniRef30 not ECOD-dependent**: The UniRef30 database used by hhblits (step 02)
   is independent of ECOD and does not need updating with ECOD versions. Current
   version: UniRef30_2023_02.
