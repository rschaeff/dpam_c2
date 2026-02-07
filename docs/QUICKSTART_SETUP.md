# DPAM v2.0 Quick Setup Guide

**One-stop guide for setting up DPAM runs.** This document covers all configuration requirements for running DPAM v2.0, including common pitfalls and their solutions.

---

## Prerequisites Checklist

Before running DPAM, ensure all of the following are satisfied:

- [ ] Conda environment `dpam` activated (or CONDA_PREFIX set)
- [ ] HH-suite binaries in PATH
- [ ] DALI (DaliLite.v5) accessible
- [ ] Reference data directory accessible
- [ ] Custom HHPaths.pm configured (if using addss.pl)

---

## Critical: Environment Setup

### 1. Conda Environment Activation

**The `dpam` conda environment MUST be properly activated.** Simply adding Anaconda to PATH is NOT sufficient.

```bash
# CORRECT: Full conda activation
source /sw/apps/Anaconda3-2023.09-0/etc/profile.d/conda.sh
conda activate dpam

# WRONG: Just adding to PATH (does NOT set CONDA_PREFIX)
export PATH="/sw/apps/Anaconda3-2023.09-0/bin:$PATH"
```

**Why this matters:** The custom `HHPaths.pm` uses `$CONDA_PREFIX` to locate PSIPRED and legacy BLAST binaries. Without it, `addss.pl` will fail.

### 2. Verify Conda Activation

```bash
# Check CONDA_PREFIX is set
echo $CONDA_PREFIX
# Expected: /home/rschaeff/.conda/envs/dpam (or similar)

# Check required binaries are accessible
which psipred blastpgp makemat
# Should all point to $CONDA_PREFIX/bin/
```

---

## Custom HHPaths.pm Configuration

DPAM includes a custom `HHPaths.pm` because the system default does not work.

**Location:** `dpam/tools/scripts/HHPaths.pm`

**Current configuration:**
```perl
# PSIPRED paths (from conda)
my $conda_prefix = $ENV{"CONDA_PREFIX"} || "";
our $execdir = $conda_prefix ? "$conda_prefix/bin" : "/usr/bin";
our $datadir = $conda_prefix ? "$conda_prefix/share/psipred/data" : "/dev/null";
our $ncbidir = $conda_prefix ? "$conda_prefix/bin" : "/usr/bin";

# HH-suite paths (hardcoded)
my $hhsuite_system = "/sw/apps/hh-suite";
our $hhlib    = $hhsuite_system;
our $hhbin    = $hhsuite_system."/bin";
```

### Customizing for Your Installation

If your paths differ, edit `dpam/tools/scripts/HHPaths.pm`:

1. **HH-suite location:** Change `$hhsuite_system` to your installation path
2. **PSIPRED location:** If not using conda, hardcode `$execdir`, `$datadir`, `$ncbidir`

---

## Reference Data Setup

### Required Data Directory Structure

```
/path/to/ecod_data/
├── UniRef30_2022_02/          # HHblits database (~260 GB)
├── pdb70/                      # HHsearch template database
├── ECOD_foldseek_DB*           # Foldseek database files
├── ECOD70/                     # DALI template PDBs
├── ecod.latest.domains         # ECOD metadata
├── ECOD_length                 # Domain lengths
├── ECOD_norms                  # Normalization values
├── ECOD_pdbmap                 # PDB mappings
├── domass_epo29.*              # ML model checkpoint
├── tgroup_length               # T-group lengths
└── posi_weights/               # Position weights
```

### Verify Data Accessibility

```bash
DATA_DIR="/home/rschaeff_1/data/dpam_reference/ecod_data"

# Check key files exist
ls $DATA_DIR/ecod.latest.domains
ls $DATA_DIR/UniRef30_2022_02/
ls $DATA_DIR/ECOD_foldseek_DB
ls $DATA_DIR/ECOD70/
```

---

## SLURM Job Script Template

Use this template for SLURM array jobs:

```bash
#!/bin/bash
#SBATCH --job-name=dpam
#SBATCH --output=slurm_logs/%A_%a.out
#SBATCH --error=slurm_logs/%A_%a.err
#SBATCH --partition=96GB
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=4G
#SBATCH --time=8:00:00
#SBATCH --array=0-999

# Get protein prefix from list file
PREFIX=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" proteins.txt)
if [ -z "$PREFIX" ]; then
    echo "No prefix found for task $SLURM_ARRAY_TASK_ID"
    exit 0
fi

echo "Processing $PREFIX (task $SLURM_ARRAY_TASK_ID)"

# ============================================
# CRITICAL: Conda environment setup
# ============================================
source /sw/apps/Anaconda3-2023.09-0/etc/profile.d/conda.sh
conda activate dpam

# Verify activation
if [ -z "$CONDA_PREFIX" ]; then
    echo "ERROR: CONDA_PREFIX not set - conda activation failed"
    exit 1
fi

# ============================================
# CRITICAL: Unset OMP_PROC_BIND for foldseek
# ============================================
unset OMP_PROC_BIND

# ============================================
# OPTIONAL: Copy UniRef30 to local scratch
# ============================================
UNIREF_SRC="/home/rschaeff_1/data/dpam_reference/ecod_data/UniRef30_2022_02"
LOCAL_DB="/tmp/slurm-$SLURM_JOB_ID/UniRef30_2022_02"
if [ -d "$UNIREF_SRC" ]; then
    echo "Copying UniRef30 to local scratch..."
    mkdir -p "$LOCAL_DB"
    rsync -a "$UNIREF_SRC/" "$LOCAL_DB/" 2>/dev/null || true
    echo "Copy complete"
fi

# ============================================
# Run DPAM pipeline
# ============================================
cd /home/rschaeff/dev/dpam_c2

# --scratch-dir /tmp: DALI temp I/O on local disk (avoids NFS latency)
# --dali-workers 32: Oversubscribe workers (DALI is I/O-bound, not CPU-bound)
dpam run "$PREFIX" \
    --working-dir /path/to/working_dir \
    --data-dir /home/rschaeff_1/data/dpam_reference/ecod_data \
    --cpus 8 \
    --resume \
    --scratch-dir /tmp \
    --dali-workers 32

# Cleanup local scratch
rm -rf "/tmp/slurm-$SLURM_JOB_ID" 2>/dev/null || true
```

---

## Common Errors and Solutions

### Error: `blastpgp: command not found`

**Cause:** `CONDA_PREFIX` not set, HHPaths.pm can't find legacy BLAST.

**Solution:**
```bash
# Activate conda properly
source /sw/apps/Anaconda3-2023.09-0/etc/profile.d/conda.sh
conda activate dpam

# Verify
echo $CONDA_PREFIX  # Should be set
which blastpgp      # Should find it
```

### Error: `OMP_PROC_BIND` (Foldseek fails)

**Cause:** SLURM sets `OMP_PROC_BIND` which conflicts with Foldseek.

**Solution:**
```bash
unset OMP_PROC_BIND
```

### Error: `addss.pl` fails

**Cause:** System HHPaths.pm being used instead of custom one.

**Solution:** Ensure DPAM's custom HHPaths.pm is being loaded. The AddSS wrapper should set HHLIB automatically. If issues persist:
```bash
export HHLIB=/path/to/dpam_c2/dpam/tools
```

### Error: Pipeline completes with Foldseek-only results

**Cause:** HHsearch failed but pipeline continued (graceful degradation).

**Solution:** Check SLURM logs for HHsearch errors. Fix environment setup. DPAM now halts on critical step failures (HHsearch, Foldseek, DALI).

### Error: `dpam: command not found`

**Cause:** DPAM not installed in environment.

**Solution:**
```bash
cd /home/rschaeff/dev/dpam_c2
pip install -e . --break-system-packages
```

Or use Python module invocation:
```python
python3 -c "
import sys
sys.argv = ['dpam', 'run', 'AF-P12345-F1', '--working-dir', './work', '--data-dir', '/path/to/data', '--cpus', '8']
from dpam.cli.main import main
main()
"
```

---

## Verification Commands

Run these before submitting batch jobs:

```bash
# 1. Check conda activation
source /sw/apps/Anaconda3-2023.09-0/etc/profile.d/conda.sh
conda activate dpam
echo "CONDA_PREFIX: $CONDA_PREFIX"

# 2. Check critical binaries
which hhblits hhmake hhsearch  # HH-suite
which psipred blastpgp makemat # PSIPRED/BLAST (in conda)
which foldseek                  # Foldseek
which dali.pl || echo "DALI: Check ~/bin/DaliLite.v5/bin/dali.pl"

# 3. Check reference data
DATA_DIR="/home/rschaeff_1/data/dpam_reference/ecod_data"
test -f "$DATA_DIR/ecod.latest.domains" && echo "ECOD domains: OK"
test -d "$DATA_DIR/UniRef30_2022_02" && echo "UniRef30: OK"
test -f "$DATA_DIR/ECOD_foldseek_DB" && echo "Foldseek DB: OK"

# 4. Test single protein
dpam run AF-P12345-F1 --working-dir ./test_run --data-dir $DATA_DIR --cpus 4
```

---

## Quick Reference: Environment Variables

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `CONDA_PREFIX` | Conda env path (auto-set by `conda activate`) | `/home/user/.conda/envs/dpam` |
| `HHLIB` | HH-suite lib path (set by AddSS wrapper) | `/path/to/dpam_c2/dpam/tools` |
| `OMP_PROC_BIND` | Must be UNSET for Foldseek | (unset) |
| `PATH` | Must include HH-suite bin | `/sw/apps/hh-suite/bin:$PATH` |

---

## File Locations Summary

| Component | Location |
|-----------|----------|
| Custom HHPaths.pm | `dpam/tools/scripts/HHPaths.pm` |
| HH-suite | `/sw/apps/hh-suite/` |
| DALI | `~/bin/DaliLite.v5/` or `~/src/Dali_v5/DaliLite.v5/` |
| Reference data | `/home/rschaeff_1/data/dpam_reference/ecod_data/` |
| Conda environment | `/home/rschaeff/.conda/envs/dpam/` |

---

## See Also

- `docs/DEPENDENCIES.md` - Full dependency documentation
- `docs/INSTALLATION.md` - Installation guide
- `docs/STEP2_SUMMARY.md` - HHsearch step details
- `CLAUDE.md` - Developer notes and pipeline overview
