# DPAM v2.0 Validation Framework

**Created**: 2025-11-22
**Purpose**: Enable comprehensive validation of dpam_c2 against DPAM v1.0 for production deployment

## Executive Summary

Created a validation framework that compares dpam_c2 outputs with DPAM v1.0 (dpam_automatic) reference data to ensure algorithmic correctness. This enables production deployment with confidence by systematically identifying any differences.

### Key Features

- **Automated validation**: Runs dpam_c2 and compares with v1.0 outputs step-by-step
- **Comprehensive coverage**: Validates all 24 pipeline steps
- **Smart comparison**: Distinguishes critical errors from cosmetic differences
- **Detailed reporting**: Generates structured validation reports
- **Flexible usage**: Full pipeline validation or output-only comparison

## Architecture Context

### DPAM v1.0 Complexity

**Original DPAM (dpam_automatic) consists of ~70 Python scripts:**

| Category | Count | Examples |
|----------|-------|----------|
| Preparation scripts | 25 | `prepare_step1.py` through `prepare_step25.py` |
| Execution scripts | 25 | `step1_get_AFDB_seqs.py` through `step25_generate_pdbs.py` |
| Utilities | 20+ | `batch_run.py`, `cleanup.py`, `check_step*.py` |
| Variants | Several | `step16a/o/t` (TensorFlow), `step24a`, makeup scripts |

**Orchestration:**
- `run_DPAM.py` wrapper (500+ lines)
- Each step: prepare → generate SLURM job → submit → monitor → retry (up to 5×)
- State management via file existence
- Complex dependency handling

### dpam_c2 Simplification

**Unified Python package:**
- Single `DPAMPipeline` class
- 24 step modules (one per step)
- Shared utilities and tools
- State management via JSON checkpointing
- Can run locally or on SLURM

**Complexity reduction:**
- 70 scripts → 24 step modules + 1 pipeline class
- 500-line wrapper → Simple Python API or CLI
- Manual SLURM job generation → Automatic via CLI
- File-based state → Structured JSON state

## Validation Tools

### 1. `validate_against_v1.py` - Full Validation

Runs dpam_c2 pipeline and compares with v1.0 reference outputs.

**Command:**
```bash
python scripts/validate_against_v1.py proteins.txt v1_dir v2_dir \
    --data-dir /data/ecod_data \
    --report validation_report.txt
```

**Process:**
1. For each protein:
   - Run dpam_c2 (all steps 1-24)
   - Compare each step's outputs with v1.0
   - Log differences
2. Generate comprehensive report
3. Exit code 0 if all pass, 1 if any critical errors

**Use case:** Full end-to-end validation before production deployment

---

### 2. `compare_outputs.py` - Comparison Only

Compares existing outputs without running pipeline.

**Command:**
```bash
python scripts/compare_outputs.py AF-P12345 v1_dir v2_dir \
    --report comparison.txt
```

**Process:**
1. Compare all output files for single protein
2. Report differences
3. No pipeline execution

**Use case:** Quick comparison when both versions already ran, debugging specific proteins

---

## Comparison Strategy

### Files Validated Per Step

**Early steps (domain identification):**
- Step 1: `.pdb`, `.fasta`
- Step 2: `.hhsearch`
- Step 3: `.foldseek`
- Step 7: `_iterativdDali_hits`
- Step 13: `.finalDPAM.domains`, `.step13_domains`

**ML pipeline:**
- Step 15: `.domass_features`
- Step 16: `.step16_predictions`
- Step 17: `.step17_confident`
- Step 18: `.step18_mappings`
- Step 19: `.step19_merge_candidates`

**Domain refinement:**
- Step 22: `.step22_merged_domains`
- Step 23: `.step23_predictions`
- Step 24: `.finalDPAM.domains` (final output)

### Comparison Methods

**Exact match** (most files):
- Line-by-line comparison
- Reports line count differences
- Shows sample diffs

**Numeric tolerance** (files with floats):
- `.hhsearch`, `.foldseek`, `.predictions`, `.step23_predictions`
- Default tolerance: 1e-6
- Allows minor floating-point variations

**Critical vs Non-Critical:**

| Critical (test fails) | Non-Critical (warning) |
|----------------------|------------------------|
| File missing in v2 | Minor float differences |
| Major line count difference (>10%) | Whitespace changes |
| Different domain counts | Cosmetic formatting |
| Different ECOD assignments | Numeric precision (<1e-6) |

## Validation Workflow

### Phase 1: Quick Validation (1-2 proteins)

**Purpose:** Verify basic functionality

```bash
echo "AF-P12345" > quick_test.txt

python scripts/validate_against_v1.py quick_test.txt \
    /work/dpam_v1 /work/dpam_c2 \
    --data-dir /data/ecod_data \
    --stop-on-error \
    --report quick_report.txt
```

**Expected time:** ~30-60 minutes per protein
**Pass criteria:** 0 critical errors

---

### Phase 2: Comprehensive Validation (10-20 proteins)

**Purpose:** Test diverse protein types

**Test set composition:**
- 3× small proteins (100-200 residues)
- 5× medium proteins (300-500 residues)
- 3× large proteins (600-1000 residues)
- 3× multi-domain proteins
- 3× discontinuous domains (Rossmann folds)
- 3× proteins with modified residues

```bash
python scripts/validate_against_v1.py comprehensive_test.txt \
    /work/dpam_v1 /work/dpam_c2 \
    --data-dir /data/ecod_data \
    --report comprehensive_report.txt
```

**Expected time:** 8-12 hours
**Pass criteria:** >95% steps pass, 0 critical errors in final output

---

### Phase 3: Production Validation (BFVD/GVD comparison)

**Purpose:** Validate against production reference database

```bash
# Use existing BFVD outputs as reference
python scripts/compare_outputs.py <protein> \
    /path/to/BFVD/outputs \
    /work/dpam_c2 \
    --report bfvd_comparison.txt
```

**Pass criteria:** Final outputs (.finalDPAM.domains) match BFVD assignments

---

## Expected Differences

### Acceptable (Non-Critical)

**Numeric precision:**
- Floating-point differences <1e-6 in scores
- Rounding differences in percentages

**Format changes:**
- Whitespace differences
- Column order (if semantically equivalent)
- Header formatting

**Tool version differences:**
- HHsuite 3.2 vs 3.3 may have minor E-value differences
- Foldseek version changes
- DALI output format variations

### Unacceptable (Critical)

**Missing outputs:**
- File exists in v1 but not in v2 = step failed

**Domain differences:**
- Different number of domains identified
- Different domain boundaries (>5 residue shift)
- Different ECOD family assignments

**Major algorithm changes:**
- >10% difference in hit counts
- Completely different alignment results
- Missing steps in pipeline

## Known Issues and Workarounds

### Issue: Database Version Differences

**Problem:** v1 uses 2022 UniRef30, v2 uses 2023

**Impact:** HHsearch hits may differ slightly

**Workaround:** Use same database version for validation

**Fix:** Validation tools support database version detection

---

### Issue: Tool Variant Differences

**Problem:** v1 uses dsspcmbi, v2 uses mkdssp

**Impact:** SSE assignments may have minor differences

**Workaround:** Use same tool variant

**Fix:** dpam_c2 auto-detects and supports both variants

---

### Issue: Floating-Point Precision

**Problem:** Different compilers/libraries cause FP differences

**Impact:** Scores differ in 7th decimal place

**Workaround:** Use numeric tolerance comparison

**Fix:** Already implemented (tolerance=1e-6)

---

## Production Readiness Checklist

Before deploying dpam_c2 to production:

**Testing:**
- [ ] Quick validation passed (1-2 proteins)
- [ ] Comprehensive validation passed (10-20 proteins)
- [ ] BFVD/GVD comparison passed
- [ ] Tested on production HPC environment
- [ ] Performance acceptable (comparable to v1.0)

**Critical steps validated:**
- [ ] Step 13 (PARSE_DOMAINS) - domain boundaries match
- [ ] Step 23 (GET_PREDICTIONS) - ECOD assignments match
- [ ] Step 24 (INTEGRATE_RESULTS) - final outputs match

**Documentation:**
- [ ] Known differences documented
- [ ] Migration guide created
- [ ] User guide updated
- [ ] Installation instructions verified

**Deployment:**
- [ ] Conda environment created
- [ ] External tools available (HHsuite, Foldseek, DALI, DSSP)
- [ ] Reference databases installed
- [ ] Batch submission tested

## Troubleshooting Guide

### Validation Script Errors

**Error:** `ModuleNotFoundError: No module named 'dpam'`

**Fix:**
```bash
pip install -e /path/to/dpam_c2 --break-system-packages
```

---

**Error:** `External tool not found: dali.pl`

**Fix:**
```bash
export DALI_HOME=/path/to/DaliLite.v5
# OR
module load dali  # On HPC
```

---

### Many Differences Reported

**Check:**
1. Same databases used? (UniRef30 version, ECOD version)
2. v1 outputs complete? (all steps finished)
3. Same tool versions? (HHsuite, Foldseek, DALI)

**Action:**
- Review differences manually
- Classify as critical vs cosmetic
- Update comparison tolerances if needed

---

### Low Match Rate (<90%)

**Possible causes:**
- Different algorithm implementations (check recent bug fixes)
- Different reference databases
- Incomplete v1 outputs

**Action:**
- Check validation report for patterns
- Focus on critical steps (13, 23, 24)
- Review recent code changes

---

## Files

**Validation scripts:**
- `scripts/validate_against_v1.py` - Full pipeline validation
- `scripts/compare_outputs.py` - Output comparison only
- `scripts/VALIDATION_GUIDE.md` - User guide

**Documentation:**
- `docs/VALIDATION_FRAMEWORK.md` - This file
- Describes architecture, workflow, troubleshooting

## Future Enhancements

**Planned:**
1. Parallel validation for large protein sets
2. Detailed diff visualization (HTML reports)
3. Automated regression testing
4. Performance benchmarking
5. SLURM batch validation wrapper

**Possible:**
1. Web-based validation dashboard
2. Continuous validation (CI/CD integration)
3. Historical comparison (track validation over time)
4. Per-step regression tests

## Contact

**For validation issues:**
- Check VALIDATION_GUIDE.md first
- File GitHub issue with validation report attached
- Include protein IDs and environment details

**For algorithm questions:**
- Original DPAM: Qian Cong
- dpam_c2: Development team
