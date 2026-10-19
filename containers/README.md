# DPAM v2.0 Apptainer Container

Apptainer (formerly Singularity) container for running DPAM v2.0 on HPC systems
without root access, including TACC Lonestar6.

## What's Inside

| Tool | Source | Purpose |
|------|--------|---------|
| HHsuite (hhmake, hhsearch, addss.pl) | bioconda | Sequence homology search |
| Foldseek | bioconda | Structure similarity search |
| PSIPRED | bioconda | Secondary structure prediction (for addss.pl) |
| DaliLite.v5 (dali.pl, dsspcmbi) | Source build | Structural alignment |
| TensorFlow CPU | pip | DOMASS ML model |
| Python 3.11 + numpy + gemmi | conda/pip | Core runtime |
| DPAM v2.0 | pip install | Pipeline CLI |

**Not included**: UniRef30 database (~260 GB). HHblits profiles (`.a3m` files)
must be pre-computed before running in the container, or step 2 (HHSEARCH)
should be skipped with `--resume` on pre-existing results.

## Building the Container

### Prerequisites

- Apptainer 1.1+ (or Singularity 3.8+)
- `sudo` or `--fakeroot` capability for building
- ~10 GB disk space for the build, ~4 GB for the final SIF

### Build

From the DPAM repository root:

```bash
# With sudo
sudo apptainer build dpam.sif containers/dpam.def

# With fakeroot (no sudo needed, if configured)
apptainer build --fakeroot dpam.sif containers/dpam.def
```

The build copies the entire DPAM source tree into the container via the
`%files` section, then installs it with pip.

### Verify the Build

```bash
# Check all tools
apptainer exec dpam.sif hhsearch 2>&1 | head -1
apptainer exec dpam.sif hhmake 2>&1 | head -1
apptainer exec dpam.sif foldseek version
apptainer exec dpam.sif dali.pl 2>&1 | head -3
apptainer exec dpam.sif dsspcmbi 2>&1 | head -1
apptainer exec dpam.sif python3 -c "import numpy, gemmi, tensorflow; print('OK')"
apptainer exec dpam.sif dpam --help
```

## Deploying to TACC Lonestar6

### Transfer

```bash
scp dpam.sif username@ls6.tacc.utexas.edu:$WORK/dpam/
```

### Storage Layout (Recommended)

```
$WORK/dpam/
├── dpam.sif                    # Container image (~4 GB)
└── ecod_data/                  # Reference data (~50 GB)
    ├── pdb70/
    ├── ECOD_foldseek_DB/
    ├── ECOD70/
    ├── ECOD_length
    ├── ECOD_norms
    ├── ECOD_pdbmap
    ├── ecod.latest.domains
    ├── ecod_weights/
    ├── ecod_domain_info/
    ├── domass_epo29.*           # TF model checkpoint
    ├── tgroup_length
    └── posi_weights/

$SCRATCH/dpam_work/             # Working directory (per-run)
├── proteins.txt                # Protein list
├── AF-P12345/                  # Per-protein dirs (sharded)
│   ├── AF-P12345.cif
│   ├── AF-P12345.json
│   └── ...
└── _batch_state.json
```

**Important**: Use `$WORK` for the SIF and reference data (persistent, backed up).
Use `$SCRATCH` for working directories (high-performance, not backed up).

## Running on Lonestar6

### Interactive (for testing)

```bash
# Start an interactive session
idev -N 1 -n 128 -p normal -t 02:00:00

# Run a single protein
apptainer exec --cleanenv \
  --bind $WORK/dpam/ecod_data:/data \
  --bind $SCRATCH/dpam_work:/work \
  --bind /tmp:/tmp \
  $WORK/dpam/dpam.sif \
  dpam run AF-P12345 \
    --working-dir /work \
    --data-dir /data \
    --cpus 128 \
    --scratch-dir /tmp \
    --dali-workers 64 \
    --resume
```

### Batch Processing (Recommended)

```bash
apptainer exec --cleanenv \
  --bind $WORK/dpam/ecod_data:/data \
  --bind $SCRATCH/dpam_work:/work \
  --bind /tmp:/tmp \
  $WORK/dpam/dpam.sif \
  dpam batch-run /work/proteins.txt \
    --working-dir /work \
    --data-dir /data \
    --cpus 128 \
    --scratch-dir /tmp \
    --dali-workers 64 \
    --skip-addss \
    --resume
```

### SLURM Job Script

```bash
#!/bin/bash
#SBATCH --job-name=dpam
#SBATCH --output=dpam_%j.out
#SBATCH --error=dpam_%j.err
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=128
#SBATCH --time=24:00:00
#SBATCH --account=YOUR_ALLOCATION

SIF=$WORK/dpam/dpam.sif
DATA=$WORK/dpam/ecod_data
WORKDIR=$SCRATCH/dpam_work
PROTEINS=$WORKDIR/proteins.txt

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

echo "DPAM batch complete: $(date)"
```

Submit with:
```bash
sbatch dpam_job.sh
```

### SLURM Array Job (Multiple Batches)

For very large runs (thousands of proteins), split into batches and use array jobs:

```bash
#!/bin/bash
#SBATCH --job-name=dpam
#SBATCH --output=dpam_%A_%a.out
#SBATCH --error=dpam_%A_%a.err
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=128
#SBATCH --time=24:00:00
#SBATCH --array=0-9
#SBATCH --account=YOUR_ALLOCATION

SIF=$WORK/dpam/dpam.sif
DATA=$WORK/dpam/ecod_data
WORKDIR=$SCRATCH/dpam_work

# Each array task processes a different batch file
PROTEINS=$WORKDIR/batch_${SLURM_ARRAY_TASK_ID}.txt

if [ ! -f "$PROTEINS" ]; then
    echo "No batch file for task $SLURM_ARRAY_TASK_ID"
    exit 0
fi

apptainer exec --cleanenv \
  --bind $DATA:/data \
  --bind $WORKDIR:/work \
  --bind /tmp:/tmp \
  $SIF \
  dpam batch-run /work/batch_${SLURM_ARRAY_TASK_ID}.txt \
    --working-dir /work \
    --data-dir /data \
    --cpus $SLURM_CPUS_PER_TASK \
    --scratch-dir /tmp \
    --dali-workers 64 \
    --skip-addss \
    --resume
```

## Bind Mount Reference

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `$WORK/dpam/ecod_data` | `/data` | ECOD reference databases (read-only) |
| `$SCRATCH/dpam_work` | `/work` | Working directory (read-write) |
| `/tmp` | `/tmp` | Local scratch for DALI I/O (read-write) |

You can add `--bind /path:mount:ro` for read-only mounts to protect reference data:

```bash
--bind $WORK/dpam/ecod_data:/data:ro
```

## Environment Variables

The container sets these automatically via `%environment`:

| Variable | Value | Purpose |
|----------|-------|---------|
| `DALI_HOME` | `/opt/dali` | DPAM finds dali.pl here |
| `CONDA_PREFIX` | `/opt/conda/envs/dpam` | HHPaths.pm uses this for PSIPRED |
| `PATH` | conda + dali bins | All tools in PATH |
| `OMP_PROC_BIND` | `false` | Prevents foldseek SLURM conflict |
| `HHLIB` | `/opt/conda/envs/dpam` | HHsuite data directory |

Use `--cleanenv` with `apptainer exec` to prevent host environment variables
from leaking in and overriding these.

## Troubleshooting

### "foldseek: Calling program has OMP_PROC_BIND set"

The container sets `OMP_PROC_BIND=false` by default. If you see this error,
make sure you're using `--cleanenv` to prevent the host SLURM environment
from overriding the container setting:

```bash
apptainer exec --cleanenv --bind ... dpam.sif dpam ...
```

### "No module named 'tensorflow'"

Verify the container was built correctly:
```bash
apptainer exec dpam.sif python3 -c "import tensorflow; print(tensorflow.__version__)"
```

### Permission denied on /tmp

Some HPC systems restrict `/tmp` access inside containers. Try binding a
different scratch location:

```bash
--bind $SCRATCH/tmp:/tmp
```

### DALI "cannot find dali.pl"

Verify `DALI_HOME` is set:
```bash
apptainer exec dpam.sif bash -c 'echo $DALI_HOME && ls $DALI_HOME/bin/'
```

### Container too large for $HOME

Store the SIF on `$WORK` (not `$HOME`), which typically has much more quota
on TACC systems.
