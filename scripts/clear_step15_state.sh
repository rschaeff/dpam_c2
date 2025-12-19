#!/bin/bash
# Clear step 15-24 state for revalidation after normalization fix
# Usage: ./scripts/clear_step15_state.sh <working_dir>

set -e

WORK_DIR="${1:-.}"

if [ ! -d "$WORK_DIR" ]; then
    echo "Error: Directory $WORK_DIR does not exist"
    exit 1
fi

echo "=== Clearing Step 15-24 State in $WORK_DIR ==="

# Steps to clear from state files
STEPS_TO_CLEAR=(
    "PREPARE_DOMASS"
    "RUN_DOMASS"
    "GET_CONFIDENT"
    "GET_MAPPING"
    "GET_MERGE_CANDIDATES"
    "EXTRACT_DOMAINS"
    "COMPARE_DOMAINS"
    "MERGE_DOMAINS"
    "GET_PREDICTIONS"
    "INTEGRATE_RESULTS"
)

# Count state files
STATE_COUNT=$(ls "$WORK_DIR"/.*.dpam_state.json 2>/dev/null | wc -l)
echo "Found $STATE_COUNT state files"

# Process each state file
PROCESSED=0
for state_file in "$WORK_DIR"/.*.dpam_state.json; do
    if [ ! -f "$state_file" ]; then
        continue
    fi

    # Extract prefix from filename
    prefix=$(basename "$state_file" | sed 's/^\.\(.*\)\.dpam_state\.json$/\1/')

    # Use Python to modify JSON (safer than sed for JSON)
    python3 << EOF
import json
import sys

state_file = "$state_file"
steps_to_clear = ${STEPS_TO_CLEAR[@]@Q}
steps_to_clear = ["PREPARE_DOMASS", "RUN_DOMASS", "GET_CONFIDENT", "GET_MAPPING",
                  "GET_MERGE_CANDIDATES", "EXTRACT_DOMAINS", "COMPARE_DOMAINS",
                  "MERGE_DOMAINS", "GET_PREDICTIONS", "INTEGRATE_RESULTS"]

try:
    with open(state_file, 'r') as f:
        state = json.load(f)

    # Remove steps from completed_steps
    if 'completed_steps' in state:
        state['completed_steps'] = [s for s in state['completed_steps'] if s not in steps_to_clear]

    # Remove steps from failed_steps
    if 'failed_steps' in state:
        state['failed_steps'] = {k: v for k, v in state['failed_steps'].items() if k not in steps_to_clear}

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

except Exception as e:
    print(f"Error processing {state_file}: {e}", file=sys.stderr)
    sys.exit(1)
EOF

    PROCESSED=$((PROCESSED + 1))

    if [ $((PROCESSED % 100)) -eq 0 ]; then
        echo "  Processed $PROCESSED/$STATE_COUNT state files..."
    fi
done

echo "Updated $PROCESSED state files"

# Delete output files
echo ""
echo "=== Deleting Step 15-24 Output Files ==="

# File patterns to delete
FILE_PATTERNS=(
    "*.step15_features"
    "*.step16_predictions"
    "*.step17_confident"
    "*.step18_mapping"
    "*.step19_merge_candidates"
    "*.step20_*"
    "*.step21_*"
    "*.step22_*"
    "*.step23_predictions"
    "*.finalDPAM.domains"
)

TOTAL_DELETED=0
for pattern in "${FILE_PATTERNS[@]}"; do
    count=$(ls "$WORK_DIR"/$pattern 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
        echo "  Deleting $count files matching $pattern"
        rm -f "$WORK_DIR"/$pattern
        TOTAL_DELETED=$((TOTAL_DELETED + count))
    fi
done

echo ""
echo "=== Summary ==="
echo "  State files updated: $PROCESSED"
echo "  Output files deleted: $TOTAL_DELETED"
echo ""
echo "Ready for revalidation. Run:"
echo "  dpam slurm-submit proteins.txt --working-dir $WORK_DIR --resume ..."
