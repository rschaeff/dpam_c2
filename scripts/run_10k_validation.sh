#!/bin/bash
#
# Master script to run 10,000 protein validation.
#
# This script orchestrates the full validation process:
# 1. Select proteins (excluding existing validation sets)
# 2. Download structures for each batch
# 3. Create reference files for each batch
# 4. Submit SLURM jobs for each batch
#
# Usage:
#   ./run_10k_validation.sh [--setup-only] [--submit-only]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DPAM_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$DPAM_DIR/validation_10k"

# Existing validation directories to exclude
EXCLUDE_DIRS=(
    "$DPAM_DIR/validation_1000"
    "$DPAM_DIR/validation_1000_round2"
)

NUM_PROTEINS=10000
BATCH_SIZE=1000
PARALLEL_DOWNLOADS=10

echo "=============================================="
echo "DPAM 10,000 Protein Validation"
echo "=============================================="
echo "Output directory: $OUTPUT_DIR"
echo "Proteins: $NUM_PROTEINS"
echo "Batch size: $BATCH_SIZE"
echo ""

# Parse arguments
SETUP_ONLY=false
SUBMIT_ONLY=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --setup-only)
            SETUP_ONLY=true
            shift
            ;;
        --submit-only)
            SUBMIT_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ "$SUBMIT_ONLY" = false ]; then
    # Step 1: Select proteins
    echo "Step 1: Selecting proteins..."
    source ~/.bashrc
    python3 "$SCRIPT_DIR/select_validation_proteins.py" \
        --output-dir "$OUTPUT_DIR" \
        --num-proteins $NUM_PROTEINS \
        --batch-size $BATCH_SIZE \
        --exclude-dirs "${EXCLUDE_DIRS[@]}"
    echo ""

    # Step 2: Download structures for each batch
    echo "Step 2: Downloading structures..."
    for batch_dir in "$OUTPUT_DIR"/batch_*; do
        if [ -d "$batch_dir" ]; then
            echo "  Downloading for $(basename "$batch_dir")..."
            python3 "$SCRIPT_DIR/download_batch_structures.py" \
                --batch-dir "$batch_dir" \
                --parallel $PARALLEL_DOWNLOADS
        fi
    done
    echo ""

    # Step 3: Create reference files
    echo "Step 3: Creating reference files..."
    for batch_dir in "$OUTPUT_DIR"/batch_*; do
        if [ -d "$batch_dir" ]; then
            echo "  Creating reference for $(basename "$batch_dir")..."
            python3 "$SCRIPT_DIR/create_batch_reference.py" \
                --batch-dir "$batch_dir"
        fi
    done
    echo ""
fi

if [ "$SETUP_ONLY" = true ]; then
    echo "Setup complete. Run with --submit-only to submit jobs."
    exit 0
fi

# Step 4: Submit SLURM jobs
echo "Step 4: Submitting SLURM jobs..."
for batch_dir in "$OUTPUT_DIR"/batch_*; do
    if [ -d "$batch_dir" ]; then
        batch_name=$(basename "$batch_dir")
        proteins_file="$batch_dir/proteins.txt"

        if [ ! -f "$proteins_file" ]; then
            echo "  Skipping $batch_name: no proteins.txt"
            continue
        fi

        NUM=$(grep -v '^#' "$proteins_file" | grep -c . || echo 0)
        if [ "$NUM" -eq 0 ]; then
            echo "  Skipping $batch_name: no proteins"
            continue
        fi

        ARRAY_MAX=$((NUM - 1))

        # Create SLURM script
        SLURM_SCRIPT="$batch_dir/dpam_validation.sh"
        BATCH_DIR_ABS=$(cd "$batch_dir" && pwd)

        cat > "$SLURM_SCRIPT" << SLURM_EOF
#!/bin/bash
#SBATCH --job-name=dpam_$batch_name
#SBATCH --output=$BATCH_DIR_ABS/slurm_logs/%A_%a.out
#SBATCH --error=$BATCH_DIR_ABS/slurm_logs/%A_%a.err
#SBATCH --partition=96GB
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=4G
#SBATCH --time=8:00:00
#SBATCH --array=0-$ARRAY_MAX

PREFIX=\$(sed -n "\$((SLURM_ARRAY_TASK_ID + 1))p" $BATCH_DIR_ABS/proteins.txt)

if [ -z "\$PREFIX" ]; then
    echo "No prefix found for task \$SLURM_ARRAY_TASK_ID"
    exit 0
fi

echo "Processing \$PREFIX (task \$SLURM_ARRAY_TASK_ID)"

# Initialize conda and activate dpam environment (has PSIPRED)
source /sw/apps/Anaconda3-2023.09-0/etc/profile.d/conda.sh
conda activate dpam

# Add HHsuite to PATH
export PATH="/sw/apps/hh-suite/bin:/sw/apps/hh-suite/scripts:\$PATH"

# Set CONDA_PREFIX for HHPaths.pm to find PSIPRED
export CONDA_PREFIX="/home/rschaeff/.conda/envs/dpam"

# Copy UniRef30 to local scratch for better I/O
UNIREF_SRC="/home/rschaeff_1/data/dpam_reference/ecod_data/UniRef30_2022_02"
LOCAL_DB="/tmp/slurm-\$SLURM_JOB_ID/UniRef30_2022_02"
if [ -d "\$UNIREF_SRC" ]; then
    mkdir -p "\$LOCAL_DB"
    rsync -a "\$UNIREF_SRC/" "\$LOCAL_DB/" 2>/dev/null || true
fi

unset OMP_PROC_BIND

cd $DPAM_DIR
python3 -c "
import sys
sys.argv = ['dpam', 'run', '\$PREFIX',
    '--working-dir', '$BATCH_DIR_ABS',
    '--data-dir', '/home/rschaeff_1/data/dpam_reference/ecod_data',
    '--cpus', '8',
    '--resume']
from dpam.cli.main import main
main()
"

rm -rf "/tmp/slurm-\$SLURM_JOB_ID" 2>/dev/null || true
SLURM_EOF

        mkdir -p "$batch_dir/slurm_logs"

        echo "  Submitting $batch_name ($NUM proteins)..."
        JOB_ID=$(sbatch --parsable "$SLURM_SCRIPT")
        echo "    Job ID: $JOB_ID"
    fi
done

echo ""
echo "=============================================="
echo "All jobs submitted!"
echo ""
echo "Monitor with:"
echo "  squeue -u \$USER"
echo ""
echo "Analyze results with:"
echo "  python3 $SCRIPT_DIR/analyze_all_batches.py $OUTPUT_DIR/batch_*"
echo "=============================================="
