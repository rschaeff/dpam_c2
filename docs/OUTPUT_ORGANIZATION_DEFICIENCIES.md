# dpam_c2 Output Organization Deficiencies

## Status: PROPOSED CLEANUP

## Problem Summary

dpam_c2 dumps all intermediate and final output files flat into a single working directory. For a 1000-protein batch, this produces **~26,000 files** in one directory, making it extremely difficult to:

1. Find specific outputs (e.g., final domain predictions)
2. Clean up intermediate files after a run
3. Debug failures for specific proteins
4. Track what pipeline stage produced each file

By contrast, native DPAM shards outputs by step (`step2/`, `step9/`, etc.), keeping each stage's outputs isolated and navigable.

## Current File Layout (per protein, ~25 files)

All of these live flat in the working directory:

```
working_dir/
  # Input (symlinks)
  {prefix}.cif                          # Input structure (symlink)
  {prefix}.json                         # PAE confidence (symlink)

  # Step 1: PREPARE
  {prefix}.fa                           # Extracted sequence
  {prefix}.pdb                          # Standardized PDB

  # Step 2: HHSEARCH
  {prefix}.hmm                          # HMM profile
  {prefix}.hhsearch                     # HHsearch raw output (LARGE, often >1MB)

  # Step 3: FOLDSEEK
  {prefix}.foldseek                     # Raw foldseek output (VERY LARGE, often >1MB)
  {prefix}.foldseek.log                 # Foldseek log

  # Step 4: FILTER_FOLDSEEK
  {prefix}.foldseek.flt.result          # Filtered foldseek hits

  # Step 5: MAP_ECOD
  {prefix}.map2ecod.result              # ECOD mapping from HHsearch

  # Step 6: DALI_CANDIDATES
  {prefix}_hits4Dali                    # DALI candidate list

  # Step 7: ITERATIVE_DALI
  {prefix}_iterativdDali_hits           # DALI alignment results
  {prefix}.iterativeDali.done           # Completion marker

  # Step 8: ANALYZE_DALI
  {prefix}_good_hits                    # Filtered DALI hits

  # Step 9: GET_SUPPORT
  {prefix}_sequence.result              # Sequence-based support
  {prefix}_structure.result             # Structure-based support

  # Step 10: FILTER_DOMAINS
  {prefix}.goodDomains                  # Filtered domain list

  # Step 11-12: SSE/DISORDER
  {prefix}.sse                          # Secondary structure
  {prefix}.diso                         # Disorder prediction

  # Step 13: PARSE_DOMAINS
  {prefix}.step13_domains               # Parsed domain boundaries

  # Step 15: PREPARE_DOMASS
  {prefix}.step15_features              # ML feature vectors

  # Step 16: RUN_DOMASS
  {prefix}.step16_predictions           # Raw ML predictions

  # Step 17: GET_CONFIDENT
  {prefix}.step17_confident_predictions # Confident predictions

  # Step 18: GET_MAPPING
  {prefix}.step18_mappings              # Domain-ECOD mappings

  # Step 23: GET_PREDICTIONS
  {prefix}.step23_predictions           # Final predictions

  # Step 24: INTEGRATE_RESULTS (in subdirectory)
  step24/{prefix}_domains               # Integrated domains

  # Final output
  {prefix}.finalDPAM.domains            # FINAL domain assignments

  # Pipeline state
  .{prefix}.dpam_state.json             # Checkpoint state (hidden)
```

### Additional Batch-Mode Artifacts

```
  _batch_state.json                     # Batch state checkpoint
  _foldseek_batch/                      # Batch foldseek DB (can be >1GB)
    queryDB, queryDB.dbtype, queryDB.index, queryDB.lookup, queryDB.source
    resultDB, resultDB.dbtype, resultDB.index
    all_results.tsv
  _dali_template_cache/                 # 36,000+ template PDB files (~4.5GB)
  prefixes_batch.txt                    # Protein list
  dpam_batch.sh                         # SLURM script
  slurm_logs/                           # SLURM output
```

## Specific Deficiencies

### 1. Flat Directory Structure

**Problem**: 25 files per protein × 1000 proteins = 25,000+ files in one directory. `ls` takes seconds, tab-completion is unusable, `find` is slow.

**Proposed fix**: Shard by step, matching native DPAM convention:
```
working_dir/
  input/                    # .cif, .json symlinks
  step01_prepare/           # .fa, .pdb
  step02_hhsearch/          # .hmm, .hhsearch
  step03_foldseek/          # .foldseek, .foldseek.log
  step04_filter/            # .foldseek.flt.result
  step05_map_ecod/          # .map2ecod.result
  step06_candidates/        # _hits4Dali
  step07_dali/              # _iterativdDali_hits, .done
  step08_analyze/           # _good_hits
  step09_support/           # _sequence.result, _structure.result
  step10_filter_domains/    # .goodDomains
  step11_sse/               # .sse
  step12_disorder/          # .diso
  step13_parse/             # .step13_domains
  step15_domass_features/   # .step15_features
  step16_domass_predict/    # .step16_predictions
  step17_confident/         # .step17_confident_predictions
  step18_mapping/           # .step18_mappings
  step23_predictions/       # .step23_predictions
  step24_integrate/         # _domains
  results/                  # .finalDPAM.domains (final output)
  state/                    # .dpam_state.json
  _batch/                   # batch state, foldseek DB, template cache
```

### 2. Large Intermediate Files Not Cleaned Up

**Problem**: Raw foldseek output (`.foldseek`, often 1-3MB per protein) and raw hhsearch output (`.hhsearch`, often 1-5MB per protein) are kept permanently. For 1000 proteins, that's 2-8GB of intermediate data that is never used after filtering.

**Files safe to delete after pipeline completion**:
- `{prefix}.foldseek` - raw foldseek (superseded by `.foldseek.flt.result`)
- `{prefix}.foldseek.log` - foldseek log
- `{prefix}.hhsearch` - raw hhsearch (superseded by `.map2ecod.result`)
- `{prefix}.hmm` - HMM profile (not used after hhsearch)
- `{prefix}.iterativeDali.done` - completion marker (state file tracks this)
- `_foldseek_batch/` - batch foldseek DB (>1GB, only needed during run)
- `_dali_template_cache/` - template PDBs (~4.5GB, only needed during run)

**Estimated savings**: ~5-10GB per 1000-protein batch

### 3. Inconsistent Naming Conventions

**Problem**: Output files use a mix of naming conventions:
- Dot-separated: `{prefix}.foldseek`, `{prefix}.goodDomains`, `{prefix}.sse`
- Underscore-separated: `{prefix}_hits4Dali`, `{prefix}_iterativdDali_hits`, `{prefix}_good_hits`
- Step-prefixed: `{prefix}.step13_domains`, `{prefix}.step15_features`
- Typo in DALI filename: `_iterativ**d**Dali_hits` (should be `_iterativeDali_hits`)

### 4. No Summary/Index File

**Problem**: After a batch run, there is no single file summarizing all proteins' results. To find how many proteins succeeded, you must count `.finalDPAM.domains` files. To find failures, you must parse individual state files.

**Proposed fix**: Generate a batch summary TSV after completion:
```
prefix    n_domains    status    tgroups    notes
ENA_...   3            complete  1.1,2.40
ENA_...   0            no_hits   -          No foldseek/DALI matches
ENA_...   -            failed    -          DALI timeout
```

### 5. step20 and step24 Subdirectories Break the Pattern

**Problem**: Steps 20 (EXTRACT_DOMAINS) and 24 (INTEGRATE_RESULTS) create their own subdirectories (`step20/`, `step24/`) while all other steps dump to root. This is inconsistent - either all steps should shard or none should.

### 6. Batch Artifacts Left Behind

**Problem**: `_foldseek_batch/` (~1GB) and `_dali_template_cache/` (~4.5GB) are not cleaned up after a successful batch run. These are only needed during processing.

**Proposed fix**: Add a cleanup phase at the end of `BatchRunner.run()` that removes these directories when all proteins complete successfully. Add `--keep-intermediates` flag to preserve them for debugging.

## Implementation Priority

1. **Cleanup script** (immediate): Write a post-processing script that moves completed results into step directories and removes intermediates. Can be run on existing batch_01-20 results.
2. **Batch summary** (immediate): Generate summary TSV from existing results.
3. **Step-sharded output** (next release): Refactor step functions to write to step-specific subdirectories.
4. **Auto-cleanup** (next release): Add cleanup phase to BatchRunner.

## Impact

With 39 batches × 1000 proteins, the current flat layout will produce ~1M files in 39 directories, consuming ~200-400GB of intermediate data that could be reduced to ~50GB of final results + essential intermediates.
