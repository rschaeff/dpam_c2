#!/bin/bash
# Collect DPAM v1.0 outputs for validation
#
# Usage: ./collect_v1_outputs.sh <protein_list> <v1_base_dir> <output_tar>
#
# Run from a directory where you have write permissions (e.g., $HOME).
# Only needs READ access to v1_base_dir.
#
# Example:
#   cd ~
#   ./collect_v1_outputs.sh validation_proteins.txt \
#       /data/data1/conglab/qcong/for/domain_parser/dpam_automatic \
#       v1_outputs.tar.gz

PROTEIN_LIST=$1
V1_BASE_DIR=$2
OUTPUT_TAR=$3

if [ -z "$PROTEIN_LIST" ] || [ -z "$V1_BASE_DIR" ] || [ -z "$OUTPUT_TAR" ]; then
    echo "Usage: $0 <protein_list> <v1_base_dir> <output_tar>"
    echo
    echo "Arguments:"
    echo "  <protein_list>  File with protein IDs (e.g., AF-A0A024R1R8-F1)"
    echo "  <v1_base_dir>   DPAM v1.0 base directory (contains step1/, step2/, etc.)"
    echo "  <output_tar>    Output tar.gz file (created in current directory)"
    echo
    echo "Note: Run from a directory where you have write permissions (e.g., ~)."
    echo "      Only needs READ access to v1_base_dir."
    echo
    echo "Example:"
    echo "  cd ~"
    echo "  $0 validation_proteins.txt \\"
    echo "      /data/data1/conglab/qcong/for/domain_parser/dpam_automatic \\"
    echo "      v1_outputs.tar.gz"
    exit 1
fi

if [ ! -f "$PROTEIN_LIST" ]; then
    echo "Error: Protein list not found: $PROTEIN_LIST"
    exit 1
fi

if [ ! -d "$V1_BASE_DIR" ]; then
    echo "Error: v1.0 base directory not found: $V1_BASE_DIR"
    exit 1
fi

echo "============================================================"
echo "Collecting DPAM v1.0 outputs"
echo "============================================================"
echo "Protein list:  $PROTEIN_LIST"
echo "v1.0 base dir: $V1_BASE_DIR"
echo "Output tar:    $OUTPUT_TAR"
echo

# Count proteins
protein_count=$(wc -l < "$PROTEIN_LIST")
echo "Processing $protein_count proteins..."
echo

# Create temporary directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

mkdir -p "$TEMP_DIR/v1_outputs"

# Process each protein
current=0
total_files=0

while IFS= read -r full_id; do
    current=$((current + 1))

    # Extract UniProt ID from AF-{UNIPROT}-F1 format
    uniprot_id=$(echo "$full_id" | sed 's/^AF-//; s/-F[0-9]*$//')

    echo "[$current/$protein_count] $full_id -> $uniprot_id"

    # Create protein directory
    protein_dir="$TEMP_DIR/v1_outputs/$full_id"
    mkdir -p "$protein_dir"

    # Collect files from all step directories
    file_count=0

    # Search step1/ through step25/ and their variants
    for step_num in {1..25}; do
        # Check main step directory
        step_dir="$V1_BASE_DIR/step${step_num}/homsa"

        if [ -d "$step_dir" ]; then
            # Copy all files matching this protein
            for file in "$step_dir/${uniprot_id}."* "$step_dir/${uniprot_id}_"*; do
                if [ -f "$file" ]; then
                    cp "$file" "$protein_dir/" 2>/dev/null
                    file_count=$((file_count + 1))
                fi
            done
        fi

        # Check variant directories (step16a, step16o, step16t, etc.)
        for variant in a o t; do
            step_dir="$V1_BASE_DIR/step${step_num}${variant}/homsa"
            if [ -d "$step_dir" ]; then
                for file in "$step_dir/${uniprot_id}."* "$step_dir/${uniprot_id}_"*; do
                    if [ -f "$file" ]; then
                        cp "$file" "$protein_dir/" 2>/dev/null
                        file_count=$((file_count + 1))
                    fi
                done
            fi
        done
    done

    echo "  → Collected $file_count files"
    total_files=$((total_files + file_count))

done < "$PROTEIN_LIST"

echo
echo "Total files collected: $total_files"
echo

# Create tar archive
echo "Creating tar archive: $OUTPUT_TAR"
tar -czf "$OUTPUT_TAR" -C "$TEMP_DIR" v1_outputs

echo
echo "============================================================"
echo "Collection complete!"
echo "============================================================"
echo "Output: $OUTPUT_TAR"
echo "Size: $(du -h "$OUTPUT_TAR" | cut -f1)"
echo
echo "Extract with:"
echo "  tar -xzf $OUTPUT_TAR"
echo
echo "Files per protein:"
ls -1 "$TEMP_DIR/v1_outputs" | while read protein; do
    count=$(ls -1 "$TEMP_DIR/v1_outputs/$protein" 2>/dev/null | wc -l)
    echo "  $protein: $count files"
done
