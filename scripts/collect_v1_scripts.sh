#!/bin/bash
# Collect DPAM v1.0 Python scripts for analysis
#
# Usage: ./collect_v1_scripts.sh <v1_base_dir> <output_tar>
#
# Run from a directory where you have write permissions (e.g., $HOME).
# Only needs READ access to v1_base_dir.
#
# Example:
#   cd ~
#   ./collect_v1_scripts.sh \
#       /data/data1/conglab/qcong/for/domain_parser/dpam_automatic \
#       v1_scripts.tar.gz

V1_BASE_DIR=$1
OUTPUT_TAR=$2

if [ -z "$V1_BASE_DIR" ] || [ -z "$OUTPUT_TAR" ]; then
    echo "Usage: $0 <v1_base_dir> <output_tar>"
    echo
    echo "Arguments:"
    echo "  <v1_base_dir>  DPAM v1.0 base directory"
    echo "  <output_tar>   Output tar.gz file (created in current directory)"
    echo
    echo "Note: Run from a directory where you have write permissions (e.g., ~)."
    echo "      Only needs READ access to v1_base_dir."
    echo
    echo "Example:"
    echo "  cd ~"
    echo "  $0 /data/data1/conglab/qcong/for/domain_parser/dpam_automatic v1_scripts.tar.gz"
    exit 1
fi

if [ ! -d "$V1_BASE_DIR" ]; then
    echo "Error: v1.0 base directory not found: $V1_BASE_DIR"
    exit 1
fi

echo "============================================================"
echo "Collecting DPAM v1.0 Scripts"
echo "============================================================"
echo "v1.0 base dir: $V1_BASE_DIR"
echo "Output tar:    $OUTPUT_TAR"
echo

# Create temporary directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

SCRIPT_DIR="$TEMP_DIR/v1_scripts"
mkdir -p "$SCRIPT_DIR"

# Counters
step_scripts=0
prepare_scripts=0
utility_scripts=0
other_files=0

echo "Collecting scripts..."
echo

# 1. Main orchestration script
echo "[Main] run_DPAM.py"
if [ -f "$V1_BASE_DIR/run_DPAM.py" ]; then
    cp "$V1_BASE_DIR/run_DPAM.py" "$SCRIPT_DIR/"
    other_files=$((other_files + 1))
fi

# 2. Step execution scripts (step1_*.py through step25_*.py)
echo "[Steps] Execution scripts (step1_*.py - step25_*.py)"
for step_num in {1..25}; do
    for script in "$V1_BASE_DIR"/step${step_num}_*.py; do
        if [ -f "$script" ]; then
            cp "$script" "$SCRIPT_DIR/"
            step_scripts=$((step_scripts + 1))
            echo "  → $(basename $script)"
        fi
    done

    # Check for variant step scripts (e.g., step16a, step16o, step16t)
    for variant in a o t; do
        for script in "$V1_BASE_DIR"/step${step_num}${variant}_*.py; do
            if [ -f "$script" ]; then
                cp "$script" "$SCRIPT_DIR/"
                step_scripts=$((step_scripts + 1))
                echo "  → $(basename $script)"
            fi
        done
    done
done

echo

# 3. Prepare scripts (prepare_step1.py through prepare_step25.py)
echo "[Prepare] Preparation scripts (prepare_step*.py)"
for script in "$V1_BASE_DIR"/prepare_step*.py; do
    if [ -f "$script" ]; then
        cp "$script" "$SCRIPT_DIR/"
        prepare_scripts=$((prepare_scripts + 1))
        echo "  → $(basename $script)"
    fi
done

echo

# 4. Utility scripts
echo "[Utilities] Helper and utility scripts"
for pattern in batch_run check_step cleanup makeup submit monitor; do
    for script in "$V1_BASE_DIR"/*${pattern}*.py; do
        if [ -f "$script" ]; then
            # Skip if already copied
            basename_script=$(basename "$script")
            if [ ! -f "$SCRIPT_DIR/$basename_script" ]; then
                cp "$script" "$SCRIPT_DIR/"
                utility_scripts=$((utility_scripts + 1))
                echo "  → $(basename $script)"
            fi
        fi
    done
done

echo

# 5. Any other .py files in root directory
echo "[Other] Other Python files"
for script in "$V1_BASE_DIR"/*.py; do
    if [ -f "$script" ]; then
        basename_script=$(basename "$script")
        # Skip if already copied
        if [ ! -f "$SCRIPT_DIR/$basename_script" ]; then
            cp "$script" "$SCRIPT_DIR/"
            other_files=$((other_files + 1))
            echo "  → $(basename $script)"
        fi
    fi
done

echo

# 6. Documentation and READMEs
echo "[Docs] Documentation files"
for doc in "$V1_BASE_DIR"/{README,README.md,README.txt,INSTALL,INSTALL.md,*.txt}; do
    if [ -f "$doc" ]; then
        cp "$doc" "$SCRIPT_DIR/"
        other_files=$((other_files + 1))
        echo "  → $(basename $doc)"
    fi
done

echo

# 7. Configuration files
echo "[Config] Configuration files"
for config in "$V1_BASE_DIR"/{*.conf,*.cfg,*.ini,*.yaml,*.yml,*.json}; do
    if [ -f "$config" ]; then
        cp "$config" "$SCRIPT_DIR/"
        other_files=$((other_files + 1))
        echo "  → $(basename $config)"
    fi
done

echo

# Summary
total_files=$((step_scripts + prepare_scripts + utility_scripts + other_files))

echo "============================================================"
echo "Collection Summary"
echo "============================================================"
echo "Step execution scripts:    $step_scripts"
echo "Prepare scripts:           $prepare_scripts"
echo "Utility scripts:           $utility_scripts"
echo "Other files:               $other_files"
echo "----------------------------------------"
echo "Total files collected:     $total_files"
echo

# Create tar archive
echo "Creating tar archive: $OUTPUT_TAR"
tar -czf "$OUTPUT_TAR" -C "$TEMP_DIR" v1_scripts

echo
echo "============================================================"
echo "Collection complete!"
echo "============================================================"
echo "Output: $OUTPUT_TAR"
echo "Size:   $(du -h "$OUTPUT_TAR" | cut -f1)"
echo
echo "Extract with:"
echo "  tar -xzf $OUTPUT_TAR"
echo
echo "Files collected:"
echo "  v1_scripts/"
ls -1 "$SCRIPT_DIR" | head -20
if [ $(ls -1 "$SCRIPT_DIR" | wc -l) -gt 20 ]; then
    echo "  ... and $(($(ls -1 "$SCRIPT_DIR" | wc -l) - 20)) more"
fi
echo
echo "Next steps:"
echo "  1. Extract the archive: tar -xzf $OUTPUT_TAR"
echo "  2. Analyze step scripts to understand outputs"
echo "  3. Build proper file mapping for validation"
