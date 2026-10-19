#!/bin/bash
#SBATCH --job-name=dpam_b39
#SBATCH --output=dpam_b39_%j.out
#SBATCH --error=dpam_b39_%j.err
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=128
#SBATCH --time=08:00:00
#SBATCH --mail-type=END,FAIL
# ============================================================================
# DPAM v2.0 Batch Validation — batch_39 (263 archaea proteins) on TACC LS6
# ============================================================================
#
# Runs full DPAM pipeline on batch_39 inside the container, then compares
# results against the leda reference. Single-node, 128 cores, 8h walltime.
#
# Setup (run once):
#   # Transfer from leda to LS6:
#   scp leda:/tmp/batch_39_ls6.tar.gz $SCRATCH/dpam/
#   cd $SCRATCH/dpam && tar xzf batch_39_ls6.tar.gz
#
#   # Container and ecod_data should already be on LS6:
#   ls $WORK/dpam/dpam.sif          # container
#   ls $WORK/dpam/ecod_data/        # reference data
#
# Submit:
#   cd $SCRATCH/dpam
#   sbatch run_batch_39_ls6.sh
#
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Load TACC modules
# ---------------------------------------------------------------------------
module load tacc-apptainer 2>/dev/null || module load apptainer 2>/dev/null || true

if ! command -v apptainer &>/dev/null; then
    echo "ERROR: apptainer not found after module load"
    exit 1
fi

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SIF="${WORK}/dpam/dpam.sif"
DATA="${WORK}/dpam/ecod_data"
BATCH_DIR="${SCRATCH}/dpam/batch_39"
INPUTS="${BATCH_DIR}/inputs"
REFERENCE="${BATCH_DIR}/reference"
WORKDIR="${SCRATCH}/dpam/batch_39_run_${SLURM_JOB_ID}"
PROTEINS="${BATCH_DIR}/proteins.txt"

# Apptainer cache on $SCRATCH
export APPTAINER_CACHEDIR="${SCRATCH}/.apptainer/cache"
export APPTAINER_TMPDIR="${SCRATCH}/.apptainer/tmp"
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
section() { echo -e "\n=== $1 ==="; }
timer_start() { T_START=$(date +%s); }
timer_stop() {
    local elapsed=$(( $(date +%s) - T_START ))
    local min=$((elapsed / 60))
    local sec=$((elapsed % 60))
    echo "  Time: ${min}m ${sec}s (${elapsed}s)"
}

NCPUS=$(nproc)
MEM_GB=$(free -g | awk '/Mem:/{print $2}')
DALI_WORKERS=$(( NCPUS * 4 ))
if (( DALI_WORKERS > 128 )); then DALI_WORKERS=128; fi

# ---------------------------------------------------------------------------
# 0. Preflight
# ---------------------------------------------------------------------------
section "Preflight"

echo "  Job ID:       ${SLURM_JOB_ID}"
echo "  Node:         $(hostname) — ${NCPUS} cores, ${MEM_GB} GB RAM"
echo "  Start:        $(date '+%Y-%m-%d %H:%M:%S')"

for f in "$SIF" "$PROTEINS"; do
    if [[ ! -f "$f" ]]; then
        echo "ERROR: Not found: $f"
        exit 1
    fi
done
for d in "$DATA" "$INPUTS" "$REFERENCE"; do
    if [[ ! -d "$d" ]]; then
        echo "ERROR: Not found: $d"
        exit 1
    fi
done

NPROTEINS=$(wc -l < "$PROTEINS")
echo "  Container:    $SIF ($(du -h "$SIF" | cut -f1))"
echo "  Data:         $DATA"
echo "  Inputs:       $INPUTS ($NPROTEINS proteins)"
echo "  Reference:    $REFERENCE ($(ls "$REFERENCE" | wc -l) domain files)"
echo "  Working:      $WORKDIR"
echo "  Workers:      DALI=$DALI_WORKERS"

# ---------------------------------------------------------------------------
# 1. Setup working directory
# ---------------------------------------------------------------------------
section "Setup"
timer_start

mkdir -p "$WORKDIR"

# Copy inputs — CIF, JSON, hhsearch, hmm are already named correctly
cp "$INPUTS"/*.cif "$WORKDIR/"
cp "$INPUTS"/*.json "$WORKDIR/"
cp "$INPUTS"/*.hhsearch "$WORKDIR/"
cp "$INPUTS"/*.hmm "$WORKDIR/"

# Protein list in workdir
cp "$PROTEINS" "$WORKDIR/proteins.txt"

# Seed per-protein state files: mark HHSEARCH as complete
while read prefix; do
    cat > "$WORKDIR/.${prefix}.dpam_state.json" << STATEEOF
{"prefix": "$prefix", "working_dir": "/work", "completed_steps": ["HHSEARCH"], "failed_steps": {}, "metadata": {}}
STATEEOF
done < "$PROTEINS"

timer_stop
echo "  Staged $NPROTEINS proteins with HHSEARCH pre-seeded"

# ---------------------------------------------------------------------------
# 2. Run batch pipeline
# ---------------------------------------------------------------------------
section "Pipeline: batch-run (steps 1-24, skip HHSEARCH)"

echo "  Start: $(date '+%Y-%m-%d %H:%M:%S')"
timer_start

run_container() {
    apptainer exec --cleanenv \
        --bind "${DATA}:/data" \
        --bind "${WORKDIR}:/work" \
        --bind /tmp:/tmp \
        "$SIF" "$@"
}

run_container dpam batch-run /work/proteins.txt \
    --working-dir /work \
    --data-dir /data \
    --cpus "$NCPUS" \
    --scratch-dir /tmp \
    --dali-workers "$DALI_WORKERS" \
    --skip-addss \
    --resume 2>&1 | tee "$WORKDIR/pipeline.log"

PIPELINE_RC=${PIPESTATUS[0]}
timer_stop
echo "  End: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Pipeline exit code: $PIPELINE_RC"

# ---------------------------------------------------------------------------
# 3. Compare results against leda reference
# ---------------------------------------------------------------------------
section "Comparison: LS6 vs Leda Reference"

total=0
match=0
differ=0
ls6_only=0
leda_only=0

while read prefix; do
    total=$((total + 1))
    ls6_file="$WORKDIR/${prefix}.finalDPAM.domains"
    leda_file="$REFERENCE/${prefix}.finalDPAM.domains"

    if [[ -f "$ls6_file" && -f "$leda_file" ]]; then
        if diff -q "$ls6_file" "$leda_file" > /dev/null 2>&1; then
            match=$((match + 1))
        else
            differ=$((differ + 1))
            if (( differ <= 10 )); then
                echo "  DIFF $prefix:"
                echo "    LS6:  $(cat "$ls6_file")"
                echo "    Leda: $(cat "$leda_file")"
            fi
        fi
    elif [[ -f "$ls6_file" && ! -f "$leda_file" ]]; then
        ls6_only=$((ls6_only + 1))
    elif [[ ! -f "$ls6_file" && -f "$leda_file" ]]; then
        leda_only=$((leda_only + 1))
        if (( leda_only <= 5 )); then
            echo "  MISSING on LS6: $prefix (leda: $(cat "$leda_file"))"
        fi
    fi
done < "$PROTEINS"

echo ""
echo "  Total proteins:     $total"
echo "  Exact match:        $match"
echo "  Differ:             $differ"
echo "  LS6 only:           $ls6_only"
echo "  Leda only:          $leda_only"

# Calculate agreement rate
pct="N/A"
if (( match + differ > 0 )); then
    pct=$(python3 -c "print(f'{$match / ($match + $differ) * 100:.1f}')")
    echo "  Agreement rate:     ${pct}% (exact match / proteins with both outputs)"
fi

# ---------------------------------------------------------------------------
# 4. Check batch state
# ---------------------------------------------------------------------------
section "Batch State"

if [[ -f "$WORKDIR/_batch_state.json" ]]; then
    python3 -c "
import json
from collections import Counter
with open('$WORKDIR/_batch_state.json') as f:
    d = json.load(f)
for step in ['PREPARE', 'FOLDSEEK', 'ITERATIVE_DALI', 'RUN_DOMASS', 'INTEGRATE_RESULTS']:
    if step in d:
        c = Counter(d[step].values())
        total = sum(c.values())
        complete = c.get('complete', 0)
        failed = c.get('failed', 0)
        print(f'  {step:25s}: {complete:3d}/{total:3d} complete, {failed:3d} failed')
"
fi

# ---------------------------------------------------------------------------
# 5. Per-protein state summary
# ---------------------------------------------------------------------------
section "Per-Protein Step Completion"

python3 -c "
import json, os, sys
from collections import Counter

workdir = '$WORKDIR'
proteins_file = '$PROTEINS'
with open(proteins_file) as f:
    proteins = [l.strip() for l in f if l.strip()]

step_counts = Counter()
failed_proteins = []
for prefix in proteins:
    state_file = os.path.join(workdir, f'.{prefix}.dpam_state.json')
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
        n_complete = len(state.get('completed_steps', []))
        n_failed = len(state.get('failed_steps', {}))
        step_counts[n_complete] += 1
        if n_failed > 0:
            failed_proteins.append((prefix, list(state['failed_steps'].keys())))
    else:
        step_counts[0] += 1
        failed_proteins.append((prefix, ['NO_STATE']))

for n_steps in sorted(step_counts.keys()):
    print(f'  {step_counts[n_steps]:3d} proteins completed {n_steps} steps')

if failed_proteins:
    print(f'')
    print(f'  Proteins with failures: {len(failed_proteins)}')
    for prefix, steps in failed_proteins[:10]:
        print(f'    {prefix}: {steps}')
    if len(failed_proteins) > 10:
        print(f'    ... and {len(failed_proteins) - 10} more')
"

# ---------------------------------------------------------------------------
# 6. Summary
# ---------------------------------------------------------------------------
section "Summary"

echo "  Job ID:         ${SLURM_JOB_ID}"
echo "  Node:           $(hostname) — ${NCPUS} cores, ${MEM_GB} GB RAM"
echo "  DALI workers:   $DALI_WORKERS"
echo "  Proteins:       $NPROTEINS"
echo "  Exact match:    $match / $((match + differ)) (${pct}%)"
echo "  Pipeline RC:    $PIPELINE_RC"
echo ""
echo "  Working dir:    $WORKDIR"
echo "  Pipeline log:   $WORKDIR/pipeline.log"
echo "  SLURM log:      dpam_b39_${SLURM_JOB_ID}.out"
echo ""
echo "  Finished:       $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "  To clean up:    rm -rf $WORKDIR"
