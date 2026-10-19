# Quickstart: DPAM on TACC Lonestar6 with Pre-computed HHblits Profiles

This guide covers running DPAM v2.0 on Lonestar6 when you already have
HHblits `.a3m` profiles (e.g., computed on a system with UniRef30). The
container does **not** include UniRef30, so HHblits cannot run inside it.
It does include everything else: addss.pl, hhmake, hhsearch, foldseek,
DALI, DOMASS/TensorFlow, and all downstream steps.

## Overview

```
leda (has UniRef30)                      Lonestar6 (container)
──────────────────                       ──────────────────────
1. Run HHblits → .a3m files              3. Finish step 2: addss→hhmake→hhsearch
2. Transfer .a3m + .cif + .json ──────>  4. Run steps 3-24 (full pipeline)
```

## Step 1: Prepare Inputs on Leda

For each protein, you need three files. Use the AlphaFold prefix as the name
(e.g., `AF-P12345-F1-model_v4`).

```bash
# On leda: run HHblits to produce profiles
# (skip if you already have .a3m files)
hhblits -i AF-P12345-F1-model_v4.fa \
  -d /path/to/UniRef30_2022_02/UniRef30_2022_02 \
  -oa3m AF-P12345-F1-model_v4.a3m \
  -cpu 8 -n 2
```

Collect the three required files per protein:

| File | Source | Description |
|------|--------|-------------|
| `PREFIX.cif` | AlphaFold DB | Structure file (mmCIF format) |
| `PREFIX.json` | AlphaFold DB | PAE matrix (confidence data) |
| `PREFIX.a3m` | HHblits output | Sequence profile |

## Step 2: Stage Data on Lonestar6

```bash
# Create working directory on $SCRATCH
mkdir -p $SCRATCH/dpam_work

# Transfer input files
scp *.cif *.json *.a3m ls6.tacc.utexas.edu:$SCRATCH/dpam_work/

# Create protein list
ssh ls6.tacc.utexas.edu
cd $SCRATCH/dpam_work
ls *.cif | sed 's/\.cif$//' > proteins.txt
cat proteins.txt   # verify
```

Ensure reference data is on `$WORK`:
```
$WORK/dpam/
├── dpam.sif              # Container image
└── ecod_data/            # ECOD reference databases
    ├── pdb70/            # HHsearch template DB
    ├── ECOD_foldseek_DB/ # Foldseek DB
    ├── ECOD70/           # DALI templates
    ├── domass_epo29.*    # TF model checkpoint
    └── ...               # Other ECOD reference files
```

## Step 3: Prep Script — Finish HHsearch from .a3m

The prep script runs inside the container. It takes each protein's `.a3m`
file and completes the HHsearch pipeline (addss.pl + hhmake + hhsearch),
then seeds the checkpoint marking step 2 (HHSEARCH) as complete.
When you run `dpam run --resume`, it will:
1. Run step 1 (PREPARE) — creates `.pdb` and `.fa` from your `.cif`
2. Skip step 2 (HHSEARCH) — already done by the prep script
3. Continue with steps 3-24

Save this as `$SCRATCH/dpam_work/prep_from_a3m.py`:

```python
#!/usr/bin/env python3
"""
Prep script: complete HHsearch pipeline from pre-existing .a3m files.

Runs addss.pl → hhmake → hhsearch for each protein, then writes a
checkpoint file so 'dpam run --resume' skips steps 1-2.

Usage (inside container):
    python3 prep_from_a3m.py proteins.txt /work /data [--cpus 8] [--skip-addss]
"""
import sys
import json
import shutil
import argparse
from pathlib import Path


def prep_protein(prefix, working_dir, data_dir, cpus, skip_addss):
    """Run addss → hhmake → hhsearch for one protein, seed state file."""
    from dpam.tools.hhsuite import AddSS, HHMake, HHSearch

    a3m_src = working_dir / f"{prefix}.a3m"
    if not a3m_src.exists():
        print(f"  SKIP {prefix}: no .a3m file")
        return False

    # Define output paths (flat layout, all in working_dir)
    a3m_file = working_dir / f"{prefix}.a3m"
    hmm_file = working_dir / f"{prefix}.hmm"
    hhsearch_file = working_dir / f"{prefix}.hhsearch"

    # Skip if already done
    if hhsearch_file.exists():
        print(f"  SKIP {prefix}: .hhsearch already exists")
        _write_state(prefix, working_dir)
        return True

    # 1. addss.pl (secondary structure annotation)
    if not skip_addss:
        a3m_ss = working_dir / f"{prefix}.a3m.ss"
        try:
            addss = AddSS()
            addss.run(a3m_file, a3m_ss, working_dir)
            shutil.move(str(a3m_ss), str(a3m_file))
            print(f"  {prefix}: addss.pl done")
        except Exception as e:
            print(f"  {prefix}: addss.pl failed ({e}), continuing without SS")
    else:
        print(f"  {prefix}: skipping addss.pl")

    # 2. hhmake
    hhmake = HHMake()
    hhmake.run(a3m_file, hmm_file, working_dir)
    print(f"  {prefix}: hhmake done")

    # 3. hhsearch
    pdb70_db = data_dir / "pdb70"
    if not (pdb70_db.parent / f"{pdb70_db.name}_cs219.ffdata").exists():
        pdb70_db = data_dir / "pdb70" / "pdb70"
    hhsearch = HHSearch()
    hhsearch.run(hmm_file, pdb70_db, hhsearch_file, cpus, 100000, working_dir)
    print(f"  {prefix}: hhsearch done")

    # 4. Write state file marking steps 1-2 complete
    _write_state(prefix, working_dir)
    return True


def _write_state(prefix, working_dir):
    """Write checkpoint marking HHSEARCH done; PREPARE runs via 'dpam run'."""
    state = {
        "prefix": prefix,
        "working_dir": str(working_dir),
        "completed_steps": ["HHSEARCH"],
        "failed_steps": {},
        "metadata": {}
    }
    state_file = working_dir / f".{prefix}.dpam_state.json"
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Prep DPAM from pre-existing a3m files")
    parser.add_argument("proteins", help="File with one prefix per line")
    parser.add_argument("working_dir", help="Working directory with .a3m/.cif/.json files")
    parser.add_argument("data_dir", help="ECOD reference data directory")
    parser.add_argument("--cpus", type=int, default=4, help="CPUs for hhsearch")
    parser.add_argument("--skip-addss", action="store_true",
                        help="Skip addss.pl (faster, slightly lower quality)")
    args = parser.parse_args()

    working_dir = Path(args.working_dir)
    data_dir = Path(args.data_dir)

    with open(args.proteins) as f:
        prefixes = [line.strip() for line in f if line.strip()]

    print(f"Prepping {len(prefixes)} proteins: addss → hhmake → hhsearch")
    ok, fail = 0, 0
    for prefix in prefixes:
        print(f"Processing {prefix}...")
        try:
            if prep_protein(prefix, working_dir, data_dir, args.cpus, args.skip_addss):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  FAILED {prefix}: {e}")
            fail += 1

    print(f"\nDone: {ok} succeeded, {fail} failed")


if __name__ == "__main__":
    main()
```

## Step 4: Run the Prep + Pipeline on Lonestar6

### Option A: Single SLURM Job (Recommended)

```bash
#!/bin/bash
#SBATCH --job-name=dpam
#SBATCH --output=dpam_%j.out
#SBATCH --error=dpam_%j.err
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=128
#SBATCH --time=48:00:00
#SBATCH --account=YOUR_ALLOCATION

SIF=$WORK/dpam/dpam.sif
DATA=$WORK/dpam/ecod_data
WORKDIR=$SCRATCH/dpam_work

# Phase 1: Complete HHsearch from pre-existing a3m files
echo "=== Phase 1: Completing HHsearch pipeline ==="
apptainer exec --cleanenv \
  --bind $DATA:/data \
  --bind $WORKDIR:/work \
  $SIF \
  python3 /work/prep_from_a3m.py \
    /work/proteins.txt /work /data \
    --cpus $SLURM_CPUS_PER_TASK

# Phase 2: Run steps 3-24 (foldseek, DALI, DOMASS, etc.)
echo "=== Phase 2: Running DPAM pipeline (steps 3-24) ==="
apptainer exec --cleanenv \
  --bind $DATA:/data \
  --bind $WORKDIR:/work \
  --bind /tmp:/tmp \
  $SIF \
  dpam batch-run /work/proteins.txt \
    --working-dir /work \
    --data-dir /data \
    --cpus $SLURM_CPUS_PER_TASK \
    --scratch-dir /tmp \
    --dali-workers 64 \
    --skip-addss \
    --resume

echo "=== DPAM complete: $(date) ==="
```

Save as `dpam_job.sh` and submit:
```bash
sbatch dpam_job.sh
```

### Option B: Interactive Testing (Small Runs)

```bash
# Get an interactive node
idev -N 1 -n 128 -p normal -t 04:00:00

SIF=$WORK/dpam/dpam.sif
DATA=$WORK/dpam/ecod_data
WORKDIR=$SCRATCH/dpam_work

# Prep one protein
apptainer exec --cleanenv \
  --bind $DATA:/data \
  --bind $WORKDIR:/work \
  $SIF \
  python3 /work/prep_from_a3m.py \
    /work/proteins.txt /work /data \
    --cpus 128

# Run pipeline (--resume skips steps 1-2 via checkpoint)
apptainer exec --cleanenv \
  --bind $DATA:/data \
  --bind $WORKDIR:/work \
  --bind /tmp:/tmp \
  $SIF \
  dpam run AF-P12345-F1-model_v4 \
    --working-dir /work \
    --data-dir /data \
    --cpus 128 \
    --scratch-dir /tmp \
    --dali-workers 64 \
    --skip-addss \
    --resume
```

## What Each Flag Does

| Flag | Purpose |
|------|---------|
| `--cleanenv` | Prevents host env vars from leaking in (critical for OMP_PROC_BIND) |
| `--resume` | Skips steps already marked complete in checkpoint file |
| `--skip-addss` | Skips addss.pl in later pipeline stages (already run in prep) |
| `--scratch-dir /tmp` | DALI temp I/O on local disk instead of NFS |
| `--dali-workers 64` | Oversubscribe DALI workers (I/O-bound, not CPU-bound) |
| `--bind ...:/data:ro` | Optional read-only mount for reference data |

## Expected Runtime

For a typical ~500-residue protein:

| Phase | Time | Notes |
|-------|------|-------|
| Prep (addss+hhmake+hhsearch) | ~5-15 min/protein | hhsearch dominates; parallelizes with `--cpus` |
| Steps 3-6 (foldseek+mapping) | ~2-5 min | Fast with batch mode |
| Step 7 (DALI) | ~30-90 min | I/O-bound; `--scratch-dir` helps enormously |
| Steps 8-24 (analysis+ML) | ~10-30 min | DOMASS model load ~22s, then fast |

Batch mode amortizes expensive resource loading across all proteins.

## Monitoring

```bash
# Check SLURM job status
squeue -u $USER

# Check DPAM batch progress (from login node)
apptainer exec --cleanenv \
  --bind $SCRATCH/dpam_work:/work \
  $WORK/dpam/dpam.sif \
  dpam batch-status --working-dir /work

# Tail job output
tail -f dpam_*.out
```

## Troubleshooting

**"FASTA file not found"**: Step 1 (PREPARE) needs `.cif` or `.pdb` in
the working directory. Make sure you transferred structure files.

**"Database is missing"**: The pdb70 database path is wrong. Check that
`$WORK/dpam/ecod_data/pdb70/` contains HHsearch database files.

**hhsearch slow**: hhsearch against pdb70 is CPU-bound. Use all available
cores with `--cpus $SLURM_CPUS_PER_TASK`.

**Step 7 hangs or is very slow**: You're probably hitting NFS. Make sure
`--scratch-dir /tmp` is set to use local disk for DALI temp files.
