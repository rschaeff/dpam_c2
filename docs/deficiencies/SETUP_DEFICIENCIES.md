# DPAM v2.0 Setup Deficiencies Report

> **See `docs/QUICKSTART_SETUP.md` for the comprehensive setup guide.**

## Issue Summary

DPAM jobs running via SLURM fail at the HHsearch step (Step 2) because `addss.pl` cannot find legacy BLAST tools (`blastpgp`, `makemat`) required for PSIPRED secondary structure prediction.

## Root Cause

The custom `HHPaths.pm` at `dpam/tools/scripts/HHPaths.pm` relies on `CONDA_PREFIX` environment variable to locate PSIPRED and legacy BLAST binaries:

```perl
my $conda_prefix = $ENV{"CONDA_PREFIX"} || "";
our $execdir = $conda_prefix ? "$conda_prefix/bin" : "/usr/bin";
our $ncbidir = $conda_prefix ? "$conda_prefix/bin" : "/usr/bin";
```

When `CONDA_PREFIX` is not set, paths fall back to `/usr/bin` where these tools don't exist.

## Required Dependencies Location

The `dpam` conda environment contains the required binaries:
- `/home/rschaeff/.conda/envs/dpam/bin/blastpgp`
- `/home/rschaeff/.conda/envs/dpam/bin/psipred`
- `/home/rschaeff/.conda/envs/dpam/bin/makemat`

## Job Script Deficiency

Current job scripts (e.g., `dpam_job.sh`) only add Anaconda to PATH but don't activate the conda environment:

```bash
export PATH="/sw/apps/Anaconda3-2023.09-0/bin:$PATH"
```

This does NOT set `CONDA_PREFIX`, which the custom HHPaths.pm requires.

## Recommended Fix

Job scripts should either:

### Option 1: Activate conda environment (Preferred)
```bash
source /sw/apps/Anaconda3-2023.09-0/etc/profile.d/conda.sh
conda activate dpam
```

### Option 2: Explicitly set CONDA_PREFIX
```bash
export CONDA_PREFIX="/home/rschaeff/.conda/envs/dpam"
export PATH="$CONDA_PREFIX/bin:$PATH"
```

### Option 3: Update HHPaths.pm with hardcoded paths
Modify `dpam/tools/scripts/HHPaths.pm`:
```perl
our $execdir = "/home/rschaeff/.conda/envs/dpam/bin";
our $ncbidir = "/home/rschaeff/.conda/envs/dpam/bin";
our $datadir = "/home/rschaeff/.conda/envs/dpam/share/psipred/data";
```

## Additional Configuration Pain Points

1. **UniRef30 database location**: Jobs copy UniRef30 to local scratch but the path `/home/rschaeff_1/data/dpam_reference/ecod_data/UniRef30_2022_02` is hardcoded in job scripts. Should be configurable.

2. **HH-suite scripts path**: The custom HHPaths.pm hardcodes `/sw/apps/hh-suite` which may not exist on all systems.

3. **HHLIB environment variable**: The `hhsuite.py` code sets `HHLIB` to the dpam tools directory for custom HHPaths.pm loading, but this is fragile and depends on correct directory structure.

4. **Pipeline doesn't fail fast**: ~~When HHsearch fails, the pipeline continues with Foldseek-only mode (graceful degradation). This hides the configuration error.~~ **FIXED**: Critical steps (HHSEARCH, FOLDSEEK, ITERATIVE_DALI) now halt the pipeline on failure. See `dpam/pipeline/runner.py:CRITICAL_STEPS`.

## Error Cascade

When blastpgp is not found:
1. `addss.pl` fails (exit code 127: command not found)
2. Step 2 (HHSEARCH) fails - no `.hhsearch` file produced
3. Step 5 (MAP_ECOD) fails - missing `.hhsearch` input
4. Step 9 (GET_SUPPORT) fails - missing HHsearch support data
5. Step 15 (PREPARE_DOMASS) fails - missing `.goodDomains`
6. Step 23 (GET_PREDICTIONS) fails - missing prediction features

The pipeline completes but produces incomplete results (Foldseek-only).

## Validation Environment Difference

The `validation_10k` runs succeeded because:
1. They used `run_downstream_rerun.sh` which runs steps 6-24 (skipping HHsearch)
2. The original HHsearch runs may have used a properly configured environment

## Date: 2026-01-11
