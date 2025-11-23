# DPAM v2.0 Validation Guide

## Overview

This directory contains tools for validating dpam_c2 against the original DPAM v1.0 (dpam_automatic). These tools enable comprehensive testing to ensure correctness before production deployment.

### Architecture Differences: v1.0 vs v2.0

**DPAM v1.0 (dpam_automatic):**
- Orchestration via `run_DPAM.py` wrapper script
- **~70 Python scripts** total:
  - 25 `prepare_stepN.py` scripts (generate `.cmds` and `.job` files for SLURM)
  - 25 `stepN_*.py` execution scripts (actual pipeline logic)
  - 20+ utility scripts (batch_run, cleanup, check, makeup variants)
  - Step variants (step16a/o/t for different TensorFlow versions, step24a, etc.)
- SLURM-based parallel execution model with job arrays
- Steps run as separate SLURM jobs with 5-retry logic
- Intermediate state managed via file existence checks

**dpam_c2:**
- Unified Python package with modular step implementations
- Single `DPAMPipeline` class orchestrates all steps
- Steps are Python functions, not separate scripts
- Can run locally (single process) or on SLURM (via CLI)
- State management via `.dpam_state.json` checkpointing

### Validation Strategy

**These validation tools focus on OUTPUT EQUIVALENCE, not execution model:**
- ✅ Compares intermediate and final output files
- ✅ Validates algorithm correctness
- ✅ Ensures identical results regardless of execution model
- ❌ Does NOT validate SLURM job generation (v1.0-specific)
- ❌ Does NOT test parallel execution scheduling

**Rationale:** If outputs match, the algorithms are equivalent. The execution model (SLURM array jobs vs Python multiprocessing) is an implementation detail.

## Validation Tools

### 1. `validate_against_v1.py` - Full Pipeline Validation

Runs dpam_c2 on test proteins and automatically compares outputs with v1.0 reference data.

**Usage:**
```bash
python validate_against_v1.py proteins.txt v1_output_dir v2_working_dir \
    --data-dir /path/to/ecod_data \
    --report validation_report.txt
```

**Arguments:**
- `proteins.txt`: File with one protein ID per line (e.g., AF-P12345)
- `v1_output_dir`: Directory containing DPAM v1.0 reference outputs
- `v2_working_dir`: Directory where dpam_c2 will write outputs
- `--data-dir`: ECOD reference data directory
- `--report`: Output report file (default: validation_report.txt)
- `--stop-on-error`: Stop at first major difference
- `--steps`: Comma-separated list of steps to validate (default: all)

**Example:**
```bash
# Validate 10 test proteins
python validate_against_v1.py test_proteins.txt \
    /work/dpam_v1_outputs \
    /work/dpam_c2_outputs \
    --data-dir /data/ecod_data \
    --report full_validation.txt
```

**Features:**
- Runs full dpam_c2 pipeline on each protein
- Compares outputs step-by-step with v1.0
- Generates detailed validation report
- Identifies critical vs cosmetic differences
- Exit code 0 if all tests pass, 1 if any fail

---

### 2. `compare_outputs.py` - Output Comparison Only

Compares existing outputs from both versions (no pipeline execution).

**Usage:**
```bash
python compare_outputs.py protein_id v1_dir v2_dir --report comparison.txt
```

**Arguments:**
- `protein_id`: Protein ID (e.g., AF-P12345)
- `v1_dir`: DPAM v1.0 output directory for this protein
- `v2_dir`: dpam_c2 output directory for this protein
- `--report`: Output report file
- `--quiet`: Suppress progress output

**Example:**
```bash
# Compare outputs for single protein
python compare_outputs.py AF-P12345 \
    /work/dpam_v1/AF-P12345 \
    /work/dpam_c2/AF-P12345 \
    --report AF-P12345_comparison.txt
```

**Use Case:**
- Quick comparison when both versions already ran
- Debugging specific proteins
- Comparing specific steps after fixes

---

## Files Compared Per Step

| Step | Files Checked |
|------|---------------|
| **Step 1 (PREPARE)** | `.pdb`, `.fasta` |
| **Step 2 (HHSEARCH)** | `.hhsearch` |
| **Step 3 (FOLDSEEK)** | `.foldseek` |
| **Step 4 (FILTER_FOLDSEEK)** | `.filtered_foldseek` |
| **Step 5 (MAP_ECOD)** | `.map2ecod.result` |
| **Step 6 (DALI_CANDIDATES)** | `.good_hits` |
| **Step 7 (ITERATIVE_DALI)** | `_iterativdDali_hits` |
| **Step 9 (GET_SUPPORT)** | `.goodDomains` |
| **Step 10 (FILTER_DOMAINS)** | `.filtered_domains` |
| **Step 11 (SSE)** | `.sse` |
| **Step 12 (DISORDER)** | `.diso` |
| **Step 13 (PARSE_DOMAINS)** | `.finalDPAM.domains`, `.step13_domains` |
| **Step 15 (PREPARE_DOMASS)** | `.domass_features` |
| **Step 16 (RUN_DOMASS)** | `.step16_predictions` |
| **Step 17 (GET_CONFIDENT)** | `.step17_confident` |
| **Step 18 (GET_MAPPING)** | `.step18_mappings` |
| **Step 19 (GET_MERGE_CANDIDATES)** | `.step19_merge_candidates` |
| **Step 21 (COMPARE_DOMAINS)** | `.step21_comparisons` |
| **Step 22 (MERGE_DOMAINS)** | `.step22_merged_domains` |
| **Step 23 (GET_PREDICTIONS)** | `.step23_predictions` |
| **Step 24 (INTEGRATE_RESULTS)** | `.finalDPAM.domains` (final) |

---

## Comparison Strategy

### Exact Match
Most files are compared for exact match (line-by-line).

### Numeric Tolerance
Files with floating-point values use tolerance comparison (default: 1e-6):
- `.hhsearch` (probabilities, E-values)
- `.foldseek` (alignment scores)
- `.predictions` (ML probabilities)
- `.step23_predictions` (coverage ratios)

### Critical vs Non-Critical Differences

**Critical Differences** (cause test failure):
- File exists in v1 but missing in v2
- Major line count differences (>10% change)
- Different domain counts
- Different ECOD assignments

**Non-Critical Differences** (warnings only):
- Minor floating-point variations
- Whitespace differences
- Cosmetic formatting changes

---

## Setting Up Validation

### 1. Prepare Test Set

Create a file with test protein IDs:

```bash
# test_proteins.txt
AF-P12345
AF-Q9Y6K9
AF-O33946
AF-O66611
AF-Q99344
```

**Recommended test set:**
- 5-10 proteins for quick validation
- 20-50 proteins for comprehensive testing
- Include diverse sizes (100-1000 residues)
- Include known multi-domain proteins
- Include discontinuous domains (Rossmann folds)

### 2. Run DPAM v1.0 Reference

Use existing DPAM v1.0 installation to generate reference outputs:

```bash
# On cluster with dpam_automatic
cd /work/dpam_automatic
python run_DPAM.py test_dataset 10  # 10 = joblimit

# Outputs will be in step*/test_dataset/ directories
```

**OR** use existing BFVD/GVD outputs if available.

### 3. Prepare dpam_c2 Environment

```bash
# Install dpam_c2
cd /path/to/dpam_c2
pip install -e . --break-system-packages

# Ensure tools available
which hhsearch foldseek dali.pl mkdssp

# Set environment variables if needed
export DALI_HOME=/path/to/DaliLite.v5
```

### 4. Run Validation

```bash
# Full validation (runs pipeline + compares)
python scripts/validate_against_v1.py test_proteins.txt \
    /work/dpam_v1_outputs \
    /work/dpam_c2_outputs \
    --data-dir /data/ecod_data \
    --report validation_report.txt
```

---

## Interpreting Results

### Validation Report Structure

```
================================================================================
DPAM v2.0 Validation Report
Generated: 2025-11-22 14:30:00
================================================================================

SUMMARY
--------------------------------------------------------------------------------
Total steps validated: 240 (10 proteins × 24 steps)
Passed (no critical errors): 235 (97.9%)
Failed (critical errors): 5 (2.1%)

Total files compared: 480
Matched: 470 (97.9%)
Differed: 10 (2.1%)


PROTEIN: AF-P12345
--------------------------------------------------------------------------------

✅ PASS - PREPARE (AF-P12345): 2/2 matched, 0 differed, 0 missing in v2, 0 critical
✅ PASS - HHSEARCH (AF-P12345): 1/1 matched, 0 differed, 0 missing in v2, 0 critical
...
❌ FAIL - GET_PREDICTIONS (AF-P12345): 0/1 matched, 1 differed, 0 missing in v2, 1 critical

Differences:
  - AF-P12345.step23_predictions (CONTENT_DIFF)
    Line count differs: v1=5, v2=10
    +full	D1	10-50	e001	1.1.1	0.950	...
    +full	D1	10-50	e002	1.1.2	0.920	...
    [Bug: Multiple ECOD assignments per domain]


CRITICAL ERRORS
--------------------------------------------------------------------------------
AF-P12345 - GET_PREDICTIONS:
  ❌ AF-P12345.step23_predictions: CONTENT_DIFF
     Line count differs: v1=5, v2=10
```

### Common Issues

#### Missing Files in v2
**Symptom:** File exists in v1 but not in v2

**Possible Causes:**
- Step failed silently
- File naming mismatch
- Output directory incorrect

**Action:** Check dpam_c2 logs, verify step completed

#### Line Count Differences
**Symptom:** Different number of output lines

**Possible Causes:**
- Bug in filtering logic
- Missing/extra hits
- Algorithm difference

**Action:** Compare file contents manually, check logic

#### Numeric Differences
**Symptom:** Values differ beyond tolerance

**Possible Causes:**
- Floating-point precision
- Algorithm change
- Database version difference

**Action:** Check if difference is significant, update tolerance if needed

#### Format Differences
**Symptom:** Same data, different format

**Possible Causes:**
- Column order change
- Whitespace differences
- Header changes

**Action:** Usually cosmetic, verify data equivalence

---

## Validation Workflow

### Quick Validation (1-2 proteins)

```bash
# Test single protein
echo "AF-P12345" > quick_test.txt

python scripts/validate_against_v1.py quick_test.txt \
    /work/dpam_v1 /work/dpam_c2 \
    --data-dir /data/ecod_data \
    --stop-on-error \
    --report quick_report.txt

# If fails, debug specific step
python scripts/compare_outputs.py AF-P12345 \
    /work/dpam_v1/AF-P12345 \
    /work/dpam_c2/AF-P12345
```

### Comprehensive Validation (10-50 proteins)

```bash
# Create diverse test set
cat > comprehensive_test.txt <<EOF
AF-P12345   # Small protein (150 residues)
AF-Q9Y6K9   # Medium (350 residues)
AF-O33946   # Large (500 residues)
AF-O66611   # Multi-domain
AF-Q99344   # Discontinuous (Rossmann)
# ... add more
EOF

# Run full validation
python scripts/validate_against_v1.py comprehensive_test.txt \
    /work/dpam_v1 /work/dpam_c2 \
    --data-dir /data/ecod_data \
    --report comprehensive_report.txt
```

### Regression Testing (after bug fixes)

```bash
# Test specific steps that were fixed
python scripts/validate_against_v1.py test_proteins.txt \
    /work/dpam_v1 /work/dpam_c2 \
    --data-dir /data/ecod_data \
    --steps "GET_PREDICTIONS,INTEGRATE_RESULTS" \
    --report regression_test.txt
```

---

## Production Validation Checklist

Before deploying dpam_c2 to production:

- [ ] **Test on diverse protein set** (10+ proteins, various sizes)
- [ ] **All steps pass** (0 critical errors)
- [ ] **Key steps exact match**:
  - [ ] Step 13 (PARSE_DOMAINS) - domain boundaries
  - [ ] Step 23 (GET_PREDICTIONS) - ECOD assignments
  - [ ] Step 24 (INTEGRATE_RESULTS) - final domains
- [ ] **Known differences documented** (if any)
- [ ] **Performance acceptable** (comparable to v1.0)
- [ ] **Tested on production environment** (HPC cluster)
- [ ] **BFVD/GVD comparison** (if applicable)

---

## Troubleshooting

### Validation script fails to run

**Error:** `ModuleNotFoundError: No module named 'dpam'`

**Fix:**
```bash
cd /path/to/dpam_c2
pip install -e . --break-system-packages
```

### dpam_c2 pipeline fails

**Error:** External tool not found

**Fix:**
```bash
# Check tool availability
dpam check-tools

# Set environment variables
export DALI_HOME=/path/to/DaliLite.v5

# Load modules (HPC)
module load hhsuite foldseek
```

### Comparison reports many differences

**Action:**
1. Check if v1 and v2 used same databases
2. Verify v1 outputs are complete
3. Check for known algorithm differences
4. Review differences manually to classify as critical vs cosmetic

### Exit code always 1

**Possible Causes:**
- At least one critical error present
- Check report for failed steps

**Fix:**
- Review critical errors in report
- Fix bugs causing failures
- Re-run validation

---

## Advanced Usage

### Parallel Validation

For large protein sets, run validation in parallel:

```bash
# Split protein list
split -l 10 large_protein_list.txt batch_

# Run in parallel
for batch in batch_*; do
    python scripts/validate_against_v1.py $batch \
        /work/dpam_v1 /work/dpam_c2_${batch} \
        --data-dir /data/ecod_data \
        --report report_${batch}.txt &
done
wait

# Merge reports
cat report_batch_*.txt > combined_report.txt
```

### Custom Comparison Logic

Modify `validate_against_v1.py` to add custom comparison logic:

```python
# Add custom comparator for specific file types
def compare_domain_files(v1_file, v2_file):
    """Custom comparison for .domains files."""
    # Parse both files
    # Compare domain counts, ranges, assignments
    # Return (is_match, diff_summary)
    pass

# Register in validation
CUSTOM_COMPARATORS = {
    '.domains': compare_domain_files,
    '.predictions': compare_prediction_files
}
```

---

## Contact

For issues or questions:
- File bug report: GitHub issues
- Contact: Qian Cong (original DPAM)
- Contact: dpam_c2 team
