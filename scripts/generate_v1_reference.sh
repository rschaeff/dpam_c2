#!/bin/bash
#
# Generate v1.0 reference outputs for validation testing
#
# This script runs DPAM v1.0 on test structures and saves all intermediate
# files for comparison with v2.0 outputs.
#

set -e

# Configuration
V1_SCRIPTS_DIR="$HOME/dev/DPAM/old_docker/docker/scripts"
DATA_DIR="$HOME/data/dpam_reference/ecod_data"
REFERENCE_DIR="$HOME/dev/dpam_c2/tests/validation/reference"
TEST_STRUCTURES="$HOME/dev/dpam_c2/tests/validation/test_structures"

# Test cases
TEST_CASES=("AF-Q976I1-F1" "O05012" "O05023")

usage() {
    echo "Usage: $0 [test_case]"
    echo ""
    echo "Generate DPAM v1.0 reference outputs for validation"
    echo ""
    echo "Arguments:"
    echo "  test_case    Specific test case to run (default: all)"
    echo ""
    echo "Test cases:"
    for case in "${TEST_CASES[@]}"; do
        echo "  - $case"
    done
    echo ""
    echo "Example:"
    echo "  $0                    # Run all test cases"
    echo "  $0 AF-Q976I1-F1       # Run specific test case"
    exit 1
}

check_dependencies() {
    echo "Checking dependencies..."

    # Check v1.0 scripts exist
    if [ ! -d "$V1_SCRIPTS_DIR" ]; then
        echo "ERROR: v1.0 scripts not found at $V1_SCRIPTS_DIR"
        exit 1
    fi

    # Check data directory
    if [ ! -d "$DATA_DIR" ]; then
        echo "ERROR: ECOD data not found at $DATA_DIR"
        exit 1
    fi

    # Check for required tools
    for tool in hhblits foldseek dali.pl mkdssp; do
        if ! command -v "$tool" &> /dev/null; then
            echo "WARNING: $tool not found in PATH"
        fi
    done

    echo "✓ Dependencies OK"
}

setup_directories() {
    local case=$1

    # Create reference directory structure
    mkdir -p "$REFERENCE_DIR/$case"
    mkdir -p "$TEST_STRUCTURES"

    echo "Reference output: $REFERENCE_DIR/$case"
}

run_v1_pipeline() {
    local case=$1
    local work_dir="$REFERENCE_DIR/$case"

    echo ""
    echo "========================================="
    echo "Running v1.0 pipeline for: $case"
    echo "========================================="
    echo ""

    # Change to working directory
    cd "$work_dir"

    # Copy structure file if needed
    if [ ! -f "$case.pdb" ] && [ ! -f "$case.cif" ]; then
        echo "Copying structure file..."
        if [ -f "$HOME/dev/dpam_c2/test_run/$case.pdb" ]; then
            cp "$HOME/dev/dpam_c2/test_run/$case.pdb" .
        elif [ -f "$HOME/dev/dpam_c2/test_run/$case.cif" ]; then
            cp "$HOME/dev/dpam_c2/test_run/$case.cif" .
        elif [ -f "$HOME/dev/DPAM/old_examples/example/test/$case.cif" ]; then
            cp "$HOME/dev/DPAM/old_examples/example/test/$case.cif" .
        else
            echo "ERROR: Structure file not found for $case"
            return 1
        fi
    fi

    # Copy PAE JSON if exists
    if [ -f "$HOME/dev/dpam_c2/test_run/$case-predicted_aligned_error_v4.json" ]; then
        cp "$HOME/dev/dpam_c2/test_run/$case-predicted_aligned_error_v4.json" .
    fi

    echo "Running v1.0 steps..."

    # Note: This is a template - actual v1.0 script invocation will vary
    # depending on how v1.0 is structured (Docker vs direct scripts)

    # Option A: If using Docker
    # docker run -v "$work_dir:/work" -v "$DATA_DIR:/data" dpam_v1 ...

    # Option B: If using direct scripts
    # This would require modifying v1.0 scripts to be callable

    echo "⚠️  Manual step required:"
    echo "   Please run v1.0 pipeline on $case in $work_dir"
    echo "   Save all intermediate files (step01-step25 outputs)"
    echo ""
    echo "   Recommended approach:"
    echo "   1. Copy $work_dir contents to v1.0 working directory"
    echo "   2. Run v1.0 pipeline"
    echo "   3. Copy all output files back to $work_dir"
    echo ""
}

create_manifest() {
    local case=$1
    local work_dir="$REFERENCE_DIR/$case"
    local manifest="$work_dir/MANIFEST.txt"

    echo "Creating file manifest..."

    cat > "$manifest" << EOF
# DPAM v1.0 Reference Outputs
# Test Case: $case
# Generated: $(date)
# Location: $work_dir

## Expected Files

### Step 1: PREPARE
$case.pdb                           # Extracted PDB
$case.fa                            # FASTA sequence

### Step 2: HHSEARCH
$case.a3m                           # MSA from HHblits
$case.hmm                           # HMM profile
$case.hhr                           # HHsearch results

### Step 3: FOLDSEEK
$case.foldseek                      # Raw Foldseek results

### Step 4: FILTER_FOLDSEEK
$case.foldseek.flt.result           # Filtered Foldseek hits

### Step 5: MAP_ECOD
$case.map2ecod.result               # ECOD domain mapping

### Step 6: DALI_CANDIDATES
${case}_hits4Dali                   # ECOD domains for DALI

### Step 7: ITERATIVE_DALI
${case}_iterativdDali_hits          # DALI alignment results

### Step 8: ANALYZE_DALI
$case.step8_dali_analysis           # DALI scores and percentiles

### Step 9-13: Domain Parsing
$case.step9_support                 # Support scores
$case.step10_filtered_domains       # Filtered domains
$case.step11_sse                    # Secondary structure
$case.step12_disorder               # Disorder regions
$case.step13_domains                # Parsed domains

### Step 15-24: ML Pipeline
$case.step15_features               # ML features
$case.step16_predictions            # DOMASS predictions
$case.step17_confident_predictions  # High-confidence predictions
$case.step18_mappings               # Template mappings
$case.step19_merge_candidates       # Merge candidates
$case.step20_extracted_domains/     # Extracted PDB files
$case.step21_connectivity           # Connectivity tests
$case.step22_merged_domains         # Merged domains
$case.step23_predictions            # Final predictions
$case.step24_integrated_results     # Integrated results

### Final Output
$case.finalDPAM.domains             # Final domain definitions
EOF

    echo "✓ Manifest created: $manifest"
}

validate_reference() {
    local case=$1
    local work_dir="$REFERENCE_DIR/$case"

    echo ""
    echo "Validating reference outputs for $case..."

    local required_files=(
        "$case.pdb"
        "$case.fa"
        "$case.foldseek"
        "${case}_hits4Dali"
    )

    local found=0
    local total=${#required_files[@]}

    for file in "${required_files[@]}"; do
        if [ -f "$work_dir/$file" ]; then
            ((found++))
            echo "  ✓ $file"
        else
            echo "  ✗ $file (missing)"
        fi
    done

    echo ""
    echo "Found $found/$total required files"

    if [ $found -eq $total ]; then
        echo "✓ Reference data complete"
        return 0
    else
        echo "⚠️  Reference data incomplete"
        return 1
    fi
}

main() {
    local target_case=""

    # Parse arguments
    if [ $# -gt 0 ]; then
        if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
            usage
        fi
        target_case="$1"
    fi

    check_dependencies

    # Determine which cases to run
    local cases_to_run=()
    if [ -n "$target_case" ]; then
        cases_to_run=("$target_case")
    else
        cases_to_run=("${TEST_CASES[@]}")
    fi

    # Process each case
    for case in "${cases_to_run[@]}"; do
        setup_directories "$case"
        create_manifest "$case"
        run_v1_pipeline "$case"
        echo ""
    done

    echo ""
    echo "========================================="
    echo "Summary"
    echo "========================================="
    echo ""

    for case in "${cases_to_run[@]}"; do
        validate_reference "$case" || true
    done

    echo ""
    echo "Next steps:"
    echo "  1. Run v1.0 pipeline manually for each test case"
    echo "  2. Verify all intermediate files are present"
    echo "  3. Run validation tests: pytest tests/validation/"
    echo ""
}

# Run main
main "$@"
