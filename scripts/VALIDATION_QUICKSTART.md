# DPAM v2.0 Validation Quick-Start

## Using Existing DPAM v1.0 Outputs

If you have access to a DPAM v1.0 (dpam_automatic) installation with existing outputs, you can quickly validate dpam_c2.

### Step 1: Extract Protein IDs from v1.0 Dataset

```bash
# Extract first 10 proteins from human dataset
python scripts/extract_protein_ids.py /path/to/dpam_automatic/homsa \
    --output test_proteins.txt \
    --limit 10
```

**Output:**
```
Extracted 10 protein IDs
Written to: test_proteins.txt

First 5 proteins:
  AF-A0A024R1R8-F1
  AF-A0A024RBG1-F1
  AF-A0A024RCN7-F1
  AF-A0A075B6H5-F1
  AF-A0A075B6H7-F1
  ... and 5 more
```

**File format (test_proteins.txt):**
```
AF-A0A024R1R8-F1
AF-A0A024RBG1-F1
AF-A0A024RCN7-F1
...
```

---

### Step 2: Locate v1.0 Outputs

DPAM v1.0 outputs are in step-specific directories:

```bash
/path/to/dpam_automatic/
├── homsa/                    # Input CIF/JSON files
│   ├── AF-A0A024R1R8-F1-model_v4.cif
│   ├── AF-A0A024R1R8-F1-predicted_aligned_error_v4.json
│   └── ...
├── step1_homsa/              # Step 1 outputs (.pdb, .fasta)
├── step2_homsa/              # Step 2 outputs (.hhsearch)
├── step3_homsa/              # Step 3 outputs (.foldseek)
├── step7_homsa/              # Step 7 outputs (iterative DALI)
├── step13_homsa/             # Step 13 outputs (.finalDPAM.domains)
├── step15_homsa/             # Step 15 outputs (.domass_features)
└── ...
```

For validation, you need to **consolidate outputs per protein** into a single directory:

```bash
# Create reference directory structure
mkdir -p validation/v1_outputs

# For each protein, copy all outputs to protein-specific directory
for protein in $(cat test_proteins.txt); do
    mkdir -p validation/v1_outputs/${protein}

    # Copy outputs from step directories
    cp step1_homsa/${protein}.* validation/v1_outputs/${protein}/ 2>/dev/null || true
    cp step2_homsa/${protein}.* validation/v1_outputs/${protein}/ 2>/dev/null || true
    cp step3_homsa/${protein}.* validation/v1_outputs/${protein}/ 2>/dev/null || true
    # ... repeat for all steps
    cp step13_homsa/${protein}.* validation/v1_outputs/${protein}/ 2>/dev/null || true
    cp step24_homsa/${protein}.* validation/v1_outputs/${protein}/ 2>/dev/null || true
done
```

**Alternative:** Use existing consolidated outputs if available (BFVD/GVD format).

---

### Step 3: Run dpam_c2 on Test Set

```bash
# Create working directory for v2 outputs
mkdir -p validation/v2_outputs

# Run validation (this runs dpam_c2 and compares)
python scripts/validate_against_v1.py test_proteins.txt \
    validation/v1_outputs \
    validation/v2_outputs \
    --data-dir /data/ecod_data \
    --report validation_report.txt \
    --cpus 4
```

**What happens:**
1. For each protein in `test_proteins.txt`:
   - Runs full dpam_c2 pipeline (steps 1-24)
   - Compares each step's outputs with v1 reference
   - Logs differences
2. Generates `validation_report.txt` with detailed results
3. Exit code 0 if all pass, 1 if any critical errors

**Expected time:** ~30-60 minutes per protein (depends on size)

---

### Step 4: Review Results

```bash
# View report
less validation_report.txt

# Check summary
head -50 validation_report.txt
```

**Report structure:**
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


PROTEIN: AF-A0A024R1R8-F1
--------------------------------------------------------------------------------
✅ PASS - PREPARE (AF-A0A024R1R8-F1): 2/2 matched
✅ PASS - HHSEARCH (AF-A0A024R1R8-F1): 1/1 matched
✅ PASS - FOLDSEEK (AF-A0A024R1R8-F1): 1/1 matched
...
✅ PASS - INTEGRATE_RESULTS (AF-A0A024R1R8-F1): 1/1 matched


CRITICAL ERRORS
--------------------------------------------------------------------------------
(none if validation passed)
```

---

## Quick Comparison (If Both Already Ran)

If you already have outputs from both versions:

```bash
# Compare single protein
python scripts/compare_outputs.py AF-A0A024R1R8-F1 \
    validation/v1_outputs/AF-A0A024R1R8-F1 \
    validation/v2_outputs/AF-A0A024R1R8-F1 \
    --report comparison.txt
```

---

## Helper Script: Consolidate v1.0 Outputs

Create `scripts/consolidate_v1_outputs.sh`:

```bash
#!/bin/bash
# Consolidate DPAM v1.0 outputs for validation

DATASET=$1  # e.g., "homsa"
PROTEIN_LIST=$2  # e.g., "test_proteins.txt"
OUTPUT_DIR=$3  # e.g., "validation/v1_outputs"

if [ -z "$DATASET" ] || [ -z "$PROTEIN_LIST" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: $0 <dataset> <protein_list> <output_dir>"
    echo "Example: $0 homsa test_proteins.txt validation/v1_outputs"
    exit 1
fi

echo "Consolidating v1.0 outputs for dataset: $DATASET"
echo "Using protein list: $PROTEIN_LIST"
echo "Output directory: $OUTPUT_DIR"
echo

# Create output directory
mkdir -p $OUTPUT_DIR

# For each protein
while IFS= read -r protein; do
    echo "Processing: $protein"

    # Create protein directory
    mkdir -p $OUTPUT_DIR/$protein

    # Copy outputs from all step directories
    for step_dir in step*_${DATASET}/; do
        if [ -d "$step_dir" ]; then
            cp $step_dir/${protein}.* $OUTPUT_DIR/$protein/ 2>/dev/null || true
        fi
    done

    # Count files
    file_count=$(ls -1 $OUTPUT_DIR/$protein/ 2>/dev/null | wc -l)
    echo "  Copied $file_count files"

done < "$PROTEIN_LIST"

echo
echo "Consolidation complete!"
echo "Outputs in: $OUTPUT_DIR"
```

**Usage:**
```bash
chmod +x scripts/consolidate_v1_outputs.sh

./scripts/consolidate_v1_outputs.sh homsa test_proteins.txt validation/v1_outputs
```

---

## Typical Workflow

### Scenario 1: First-Time Validation

```bash
# 1. Extract test proteins
python scripts/extract_protein_ids.py /path/to/dpam_automatic/homsa \
    --output test_proteins.txt --limit 5

# 2. Consolidate v1.0 outputs
./scripts/consolidate_v1_outputs.sh homsa test_proteins.txt validation/v1_outputs

# 3. Run validation
python scripts/validate_against_v1.py test_proteins.txt \
    validation/v1_outputs validation/v2_outputs \
    --data-dir /data/ecod_data \
    --report validation_report.txt

# 4. Review report
less validation_report.txt
```

---

### Scenario 2: Debug Single Protein

```bash
# If validation found issues with specific protein
protein="AF-A0A024R1R8-F1"

# Run detailed comparison
python scripts/compare_outputs.py $protein \
    validation/v1_outputs/$protein \
    validation/v2_outputs/$protein \
    --report ${protein}_debug.txt

# Review differences
less ${protein}_debug.txt

# Manual file comparison
diff validation/v1_outputs/$protein/${protein}.finalDPAM.domains \
     validation/v2_outputs/$protein.finalDPAM.domains
```

---

### Scenario 3: Regression Testing After Bug Fix

```bash
# After fixing a bug in step 23

# Re-run just step 23 for test proteins
for protein in $(cat test_proteins.txt); do
    dpam run-step $protein --step GET_PREDICTIONS \
        --working-dir validation/v2_outputs \
        --data-dir /data/ecod_data
done

# Validate only step 23
python scripts/validate_against_v1.py test_proteins.txt \
    validation/v1_outputs validation/v2_outputs \
    --data-dir /data/ecod_data \
    --steps "GET_PREDICTIONS,INTEGRATE_RESULTS" \
    --report regression_report.txt
```

---

## Troubleshooting

### Issue: "No protein IDs found"

**Cause:** CIF files not in expected location/format

**Fix:**
```bash
# Check file names
ls /path/to/dpam_automatic/homsa/*.cif | head

# Should see: AF-{UNIPROT}-F1-model_v4.cif format
# If different format, adjust regex in extract_protein_ids.py
```

---

### Issue: "Required file not found" in v1_outputs

**Cause:** v1.0 outputs incomplete or not consolidated

**Fix:**
```bash
# Check which files exist for a protein
ls -la validation/v1_outputs/AF-A0A024R1R8-F1/

# Should see outputs from all steps (.hhsearch, .foldseek, .domains, etc.)
# If missing, re-run consolidate script or check v1.0 logs
```

---

### Issue: Many differences reported

**Check:**
1. Same ECOD database version?
2. Same tool versions (HHsuite, Foldseek)?
3. v1.0 run completed successfully?

**Action:**
```bash
# Focus on critical steps
python scripts/validate_against_v1.py test_proteins.txt \
    validation/v1_outputs validation/v2_outputs \
    --data-dir /data/ecod_data \
    --steps "PARSE_DOMAINS,GET_PREDICTIONS,INTEGRATE_RESULTS" \
    --report critical_steps.txt
```

---

## Expected Results

**Ideal outcome:**
- ✅ 100% steps pass (0 critical errors)
- ✅ Final outputs (.finalDPAM.domains) match exactly
- ⚠️ Minor numeric differences acceptable (<1e-6)

**Acceptable outcome:**
- ✅ >95% steps pass
- ✅ Critical steps match (13, 23, 24)
- ⚠️ Known differences documented

**Requires investigation:**
- ❌ <90% steps pass
- ❌ Different domain counts
- ❌ Different ECOD assignments in final output

---

## Next Steps

After successful validation:

1. **Expand test set**: Validate 20-50 diverse proteins
2. **Production testing**: Test on HPC cluster environment
3. **BFVD comparison**: Validate against BFVD reference database
4. **Performance benchmark**: Compare runtime with v1.0
5. **Deploy to production**: Update documentation and deploy

See `VALIDATION_GUIDE.md` for comprehensive instructions.
