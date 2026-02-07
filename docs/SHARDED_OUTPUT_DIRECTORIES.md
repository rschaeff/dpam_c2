# Sharded Output Directories

## Overview

DPAM now organizes intermediate pipeline outputs into per-step subdirectories
instead of dumping all files flat into a single working directory. For a
1000-protein batch this reduces per-directory file counts from ~25,000 to
manageable sizes, making `ls`/tab-completion usable and debugging easier.

## Directory Layout

New runs produce this structure by default:

```
working_dir/
  {prefix}.cif, {prefix}.json          # User inputs (unchanged location)
  .{prefix}.dpam_state.json            # State files (unchanged location)
  _batch_state.json                    # Batch state (unchanged location)
  step01_prepare/                      # .fa, .pdb
  step02_hhsearch/                     # .hmm, .hhsearch
  step03_foldseek/                     # .foldseek
  step04_filter/                       # .foldseek.flt.result
  step05_map_ecod/                     # .map2ecod.result
  step06_candidates/                   # _hits4Dali
  step07_dali/                         # _iterativdDali_hits, .iterativeDali.done
  step08_analyze/                      # _good_hits
  step09_support/                      # _sequence.result, _structure.result
  step10_filter_domains/               # .goodDomains
  step11_sse/                          # .sse
  step12_disorder/                     # .diso
  step13_parse/                        # .step13_domains, .finalDPAM.domains
  step15_domass_features/              # .step15_features
  step16_domass_predict/               # .step16_predictions
  step17_confident/                    # .step17_confident_predictions
  step18_mapping/                      # .step18_mappings
  step19_merge_candidates/             # .step19_merge_candidates
  step20_extract/                      # {prefix}_{domain}.pdb
  step21_compare/                      # .step21_comparisons
  step22_merge/                        # .step22_merged_domains
  step23_predictions/                  # .step23_predictions
  step24_integrate/                    # {prefix}_domains/
  results/                             # .finalDPAM.domains (final output)
  _batch/                              # foldseek DB, template cache (batch mode)
```

## Usage

### Default (sharded layout)

```bash
dpam run AF-P12345 --working-dir ./work --data-dir ./data --cpus 4
```

### Force flat layout (legacy)

```bash
dpam run AF-P12345 --working-dir ./work --data-dir ./data --cpus 4 --flat
```

### Resuming existing runs

Layout is auto-detected on `--resume`:
- If `step01_prepare/` directory exists → sharded mode
- Otherwise → flat mode

No flags needed when resuming.

### Batch mode

```bash
dpam batch-run prefixes.txt --working-dir ./work --data-dir ./data --cpus 8 --resume
dpam batch-run prefixes.txt --working-dir ./work --data-dir ./data --cpus 8 --flat
```

### Migrating existing flat directories

Existing working directories with flat layout can be migrated to sharded:

```bash
# Preview what will happen (no files modified)
dpam migrate-layout --working-dir ./work --dry-run

# Execute migration
dpam migrate-layout --working-dir ./work
```

The migration tool:
- Discovers proteins from state files and `.fa` files
- Moves intermediate files into per-step subdirectories
- Copies `.pdb` files (keeps originals in root as potential user inputs)
- Copies `.finalDPAM.domains` to both `step13_parse/` and `results/`
- Renames existing `step20/` → `step20_extract/`, `step24/` → `step24_integrate/`
- Moves batch directories (`_foldseek_batch/`, `_dali_template_cache/`) to `_batch/`
- Never touches `.cif`, `.json`, or state files
- Is idempotent: safe to run multiple times, aborts if already sharded

## Implementation

### PathResolver

`dpam/core/path_resolver.py` contains the `PathResolver` class that centralizes
all directory layout logic:

```python
from dpam.core.path_resolver import PathResolver

resolver = PathResolver(working_dir, sharded=True)
resolver.step_dir(3)    # -> working_dir/step03_foldseek/
resolver.results_dir()  # -> working_dir/results/
resolver.batch_dir()    # -> working_dir/_batch/
resolver.state_file(p)  # -> working_dir/.{p}.dpam_state.json (always root)

resolver = PathResolver(working_dir, sharded=False)
resolver.step_dir(3)    # -> working_dir/  (flat mode)
```

### Step integration

Every `run_stepN()` function accepts an optional `path_resolver=None` parameter.
When `None`, a flat-mode resolver is created as fallback, so direct calls from
scripts or tests work unchanged:

```python
def run_step12(prefix, working_dir, path_resolver=None):
    from dpam.core.path_resolver import PathResolver
    resolver = path_resolver or PathResolver(working_dir, sharded=False)

    sse_file = resolver.step_dir(11) / f'{prefix}.sse'      # input
    output_file = resolver.step_dir(12) / f'{prefix}.diso'   # output
```

### Auto-detection

`DPAMPipeline.__init__()` auto-detects layout when `sharded=None`:

- **Resuming + sharded layout detected** → sharded mode
- **Resuming + no sharded layout** → flat mode
- **New run** → sharded mode (default)

### Backward compatibility

- `path_resolver=None` default means all existing callers work unchanged
- `--flat` flag explicitly forces flat layout
- State files (`.dpam_state.json`, `_batch_state.json`) always stay in root
- User inputs (`.cif`, `.json`) always read from root
- Cross-mode resume works: batch and single-protein modes share state files

## Cross-step I/O Map

| Step | Reads from | Writes to |
|------|-----------|-----------|
| 1 | root (.cif, .json) | step_dir(1) |
| 2 | step_dir(1): .fa | step_dir(2) |
| 3 | step_dir(1): .pdb | step_dir(3) |
| 4 | step_dir(1): .fa; step_dir(3): .foldseek | step_dir(4) |
| 5 | step_dir(2): .hhsearch | step_dir(5) |
| 6 | step_dir(5): .map2ecod.result; step_dir(4): .foldseek.flt.result | step_dir(6) |
| 7 | step_dir(6): _hits4Dali; step_dir(1): .pdb | step_dir(7) |
| 8 | step_dir(7): _iterativdDali_hits | step_dir(8) |
| 9 | step_dir(5): .map2ecod.result; step_dir(8): _good_hits | step_dir(9) |
| 10 | step_dir(9): _sequence.result, _structure.result | step_dir(10) |
| 11 | step_dir(1): .pdb, .fa | step_dir(11) |
| 12 | step_dir(11): .sse; root: .json; step_dir(10): .goodDomains | step_dir(12) |
| 13 | step_dir(1): .fa, .pdb; root: .json; step_dir(12): .diso; step_dir(10): .goodDomains | step_dir(13) + results_dir() |
| 15 | step_dir(13), step_dir(11), step_dir(10), step_dir(8) | step_dir(15) |
| 16 | step_dir(15) | step_dir(16) |
| 17 | step_dir(16) | step_dir(17) |
| 18 | step_dir(17), step_dir(5), step_dir(8) | step_dir(18) |
| 19 | step_dir(18) | step_dir(19) |
| 20 | step_dir(19), step_dir(1) | step_dir(20) |
| 21 | step_dir(19), step_dir(13), step_dir(20) | step_dir(21) |
| 22 | step_dir(21) | step_dir(22) |
| 23 | step_dir(22), step_dir(13), step_dir(16), step_dir(18) | step_dir(23) |
| 24 | step_dir(23), step_dir(11) | step_dir(24) + results_dir() + root |
