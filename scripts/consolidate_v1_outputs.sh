#!/bin/bash
# Consolidate DPAM v1.0 outputs for validation
#
# Takes outputs from step-specific directories (step1_dataset/, step2_dataset/, etc.)
# and consolidates them into per-protein directories for validation.
#
# Usage:
#   ./consolidate_v1_outputs.sh <dataset> <protein_list> <output_dir>
#
# Example:
#   ./consolidate_v1_outputs.sh homsa test_proteins.txt validation/v1_outputs

DATASET=$1
PROTEIN_LIST=$2
OUTPUT_DIR=$3

if [ -z "$DATASET" ] || [ -z "$PROTEIN_LIST" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: $0 <dataset> <protein_list> <output_dir>"
    echo
    echo "Arguments:"
    echo "  <dataset>      Dataset name (e.g., 'homsa', 'mouse', 'ecoli')"
    echo "  <protein_list> File with protein IDs (one per line)"
    echo "  <output_dir>   Output directory for consolidated outputs"
    echo
    echo "Example:"
    echo "  $0 homsa test_proteins.txt validation/v1_outputs"
    echo
    echo "Expects DPAM v1.0 directory structure:"
    echo "  step1_${DATASET}/, step2_${DATASET}/, ..., step24_${DATASET}/"
    exit 1
fi

if [ ! -f "$PROTEIN_LIST" ]; then
    echo "Error: Protein list file not found: $PROTEIN_LIST"
    exit 1
fi

echo "="============================================================
echo "Consolidating DPAM v1.0 outputs"
echo "="============================================================
echo "Dataset:       $DATASET"
echo "Protein list:  $PROTEIN_LIST"
echo "Output dir:    $OUTPUT_DIR"
echo

# Count proteins
protein_count=$(wc -l < "$PROTEIN_LIST")
echo "Processing $protein_count proteins..."
echo

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Process each protein
current=0
while IFS= read -r protein; do
    current=$((current + 1))
    echo "[$current/$protein_count] Processing: $protein"

    # Create protein directory
    protein_dir="$OUTPUT_DIR/$protein"
    mkdir -p "$protein_dir"

    # Copy outputs from all step directories
    file_count=0
    for step_dir in step*_${DATASET}/; do
        if [ -d "$step_dir" ]; then
            # Copy all files matching protein prefix
            for file in "$step_dir"/${protein}.*; do
                if [ -f "$file" ]; then
                    cp "$file" "$protein_dir/"
                    file_count=$((file_count + 1))
                fi
            done

            # Also check for underscore variants (e.g., protein_iterativdDali_hits)
            for file in "$step_dir"/${protein}_*; do
                if [ -f "$file" ]; then
                    cp "$file" "$protein_dir/"
                    file_count=$((file_count + 1))
                fi
            done
        fi
    done

    echo "  → Copied $file_count files"

done < "$PROTEIN_LIST"

echo
echo "="============================================================
echo "Consolidation complete!"
echo "="============================================================
echo "Outputs in: $OUTPUT_DIR"
echo
echo "Verify with:"
echo "  ls -lh $OUTPUT_DIR/<protein>/"
echo
echo "Next step - run validation:"
echo "  python scripts/validate_against_v1.py $PROTEIN_LIST \\"
echo "      $OUTPUT_DIR \\"
echo "      <v2_working_dir> \\"
echo "      --data-dir <ecod_data> \\"
echo "      --report validation_report.txt"
