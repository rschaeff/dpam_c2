#!/bin/bash
#
# Submit DPAM validation for a batch of proteins.
#
# Usage:
#   ./submit_batch_validation.sh validation_10k/batch_01
#

set -e

BATCH_DIR="$1"

if [ -z "$BATCH_DIR" ]; then
    echo "Usage: $0 <batch_dir>"
    echo "Example: $0 validation_10k/batch_01"
    exit 1
fi

if [ ! -d "$BATCH_DIR" ]; then
    echo "Error: Directory $BATCH_DIR does not exist"
    exit 1
fi

if [ ! -f "$BATCH_DIR/proteins.txt" ]; then
    echo "Error: $BATCH_DIR/proteins.txt not found"
    exit 1
fi

# Count proteins
NUM_PROTEINS=$(grep -v '^#' "$BATCH_DIR/proteins.txt" | grep -c .)
ARRAY_MAX=$((NUM_PROTEINS - 1))

echo "Batch directory: $BATCH_DIR"
echo "Number of proteins: $NUM_PROTEINS"
echo "Array range: 0-$ARRAY_MAX"

# Create slurm_logs directory
mkdir -p "$BATCH_DIR/slurm_logs"

# Get absolute paths
BATCH_DIR_ABS=$(cd "$BATCH_DIR" && pwd)
DPAM_DIR=$(cd "$(dirname "$0")/.." && pwd)

# Create SLURM script
SLURM_SCRIPT="$BATCH_DIR/dpam_validation.sh"
cat > "$SLURM_SCRIPT" << SLURM_EOF
#!/bin/bash
#SBATCH --job-name=dpam_val
#SBATCH --output=$BATCH_DIR_ABS/slurm_logs/%A_%a.out
#SBATCH --error=$BATCH_DIR_ABS/slurm_logs/%A_%a.err
#SBATCH --partition=96GB
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=4G
#SBATCH --time=8:00:00
#SBATCH --array=0-$ARRAY_MAX

# Get protein prefix
PREFIX=\$(sed -n "\$((SLURM_ARRAY_TASK_ID + 1))p" $BATCH_DIR_ABS/proteins.txt)

if [ -z "\$PREFIX" ]; then
    echo "No prefix found for task \$SLURM_ARRAY_TASK_ID"
    exit 0
fi

echo "Processing \$PREFIX (task \$SLURM_ARRAY_TASK_ID)"

# Setup environment
export PATH="/sw/apps/Anaconda3-2023.09-0/bin:\$PATH"

# Copy UniRef30 to local scratch
UNIREF_SRC="/home/rschaeff_1/data/dpam_reference/ecod_data/UniRef30_2022_02"
LOCAL_DB="/tmp/slurm-\$SLURM_JOB_ID/UniRef30_2022_02"
if [ -d "\$UNIREF_SRC" ]; then
    mkdir -p "\$LOCAL_DB"
    rsync -a "\$UNIREF_SRC/" "\$LOCAL_DB/" 2>/dev/null || true
fi

# Unset OMP_PROC_BIND for foldseek
unset OMP_PROC_BIND

# Run pipeline
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

# Cleanup
rm -rf "/tmp/slurm-\$SLURM_JOB_ID" 2>/dev/null || true
SLURM_EOF

echo "Created SLURM script: $SLURM_SCRIPT"
echo ""
echo "To submit:"
echo "  sbatch $SLURM_SCRIPT"
echo ""

# Optionally submit
read -p "Submit now? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sbatch "$SLURM_SCRIPT"
fi
