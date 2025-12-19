# DPAM v2.0 Validation Plan

## Overview

This document describes the strategy for validating DPAM v2.0 against v1.0 reference outputs to ensure backward compatibility.

## Validation Strategy

### 1. Test Case Selection

**Primary test case**: `AF-Q976I1-F1` (Small protein, ~108 residues)
- AlphaFold structure with PAE data
- Located in `test_run/`
- Fast enough for rapid iteration

**Secondary test cases** (from v1.0):
- `O05012.cif` - Located in `old_examples/example/test/`
- `O05023.cif` - Located in `old_examples/example/test/`

### 2. Reference Data Generation

#### Option A: Use v1.0 Docker Container
```bash
cd ~/dev/DPAM/old_docker/docker/
docker build -t dpam_v1 .
docker run -v ~/data/dpam_reference:/data -v ~/test_outputs:/output dpam_v1 <structure>
```

#### Option B: Run v1.0 Scripts Directly
```bash
cd ~/dev/DPAM/old_docker/docker/scripts/
# Run each step sequentially, saving intermediate files
```

### 3. Validation Approach

**Per-Step Validation:**
Each step's output must match v1.0 within acceptable tolerances.

#### Steps 1-6 (✅ Currently Passing)
- Step 1 (PREPARE): PDB, FASTA extraction
- Step 2 (HHSEARCH): HHblits MSA, HHsearch hits
- Step 3 (FOLDSEEK): Structural search results
- Step 4 (FILTER_FOLDSEEK): Filtered hits
- Step 5 (MAP_ECOD): ECOD domain mapping
- Step 6 (DALI_CANDIDATES): Candidate list for DALI

#### Steps 7-13 (🔧 Need Validation)
- **Step 7 (ITERATIVE_DALI)**: ⚠️ **BROKEN** - See DALI issues below
- Step 8 (ANALYZE_DALI): Not yet tested
- Step 9 (GET_SUPPORT): Not yet tested
- Step 10 (FILTER_DOMAINS): Not yet tested
- Step 11 (SSE): Not yet tested
- Step 12 (DISORDER): Not yet tested
- Step 13 (PARSE_DOMAINS): Not yet tested

#### Steps 14-25 (❌ Need Reference Data)
- Steps 15-24: Need v1.0 reference outputs
- Step 25: Optional (visualization)

### 4. Comparison Criteria

#### Exact Match Required:
- File formats (column count, order)
- Range strings (e.g., "10-50,60-100")
- Domain boundaries
- ECOD ID assignments

#### Tolerance Allowed:
- Floating-point scores (±0.001)
- Timestamps and logs
- Temporary file locations

### 5. Known Issues

#### DALI Implementation (Step 7)

**Status**: 🔴 **BROKEN**

**Root Causes:**
1. **Path Management Issue**
   - DALI code changes to `output_tmp_dir` but uses relative paths
   - Query PDB path becomes invalid: "test_run/AF-Q976I1-F1.pdb"
   - **Fix**: Use absolute paths everywhere

2. **System Dependency Missing**
   - Error: `libgfortran.so.3: cannot open shared object file`
   - DALI executable requires older Fortran library
   - **Fix**: Install compatibility library or use static binary

3. **Working Directory Chaos**
   - Multiple `os.chdir()` calls without proper restoration
   - Nested temporary directories cause confusion
   - **Fix**: Use absolute paths, avoid changing directories

**DALI Test Results:**
- Input: 434 ECOD candidates from step 6
- Output: 0 bytes (empty file)
- Log shows library error on first domain

#### Proposed DALI Fixes:

```python
# Fix 1: Use absolute paths
work_pdb = tmp_dir / f'{prefix}_{edomain}.pdb'
work_pdb = work_pdb.absolute()  # Make absolute

template_pdb = (data_dir / 'ECOD70' / f'{edomain}.pdb').absolute()

# Fix 2: Don't change directories - pass absolute paths to DALI
# Remove: os.chdir(output_tmp_dir)
# Keep: Run from working_dir with absolute paths

# Fix 3: Fix DALI wrapper to accept working directory parameter
dali.align(
    work_pdb,
    template_pdb,
    output_tmp_dir,
    cwd=working_dir  # New parameter
)
```

### 6. Validation Test Structure

```
tests/
├── validation/              # NEW: Validation tests
│   ├── reference/          # v1.0 outputs
│   │   ├── AF-Q976I1-F1/
│   │   │   ├── step01.pdb
│   │   │   ├── step02.hhsearch
│   │   │   ├── step03.foldseek
│   │   │   ├── ...
│   │   │   └── step24.finalDPAM.domains
│   │   └── O05012/
│   ├── test_step01_validation.py
│   ├── test_step02_validation.py
│   └── ...
```

**Test Pattern:**
```python
def test_step7_matches_v1(reference_dir, test_output):
    """Validate step 7 output matches v1.0 reference."""
    ref_file = reference_dir / "step07_iterativdDali_hits"
    out_file = test_output / "AF-Q976I1-F1_iterativdDali_hits"

    # Parse both files
    ref_hits = parse_dali_hits(ref_file)
    out_hits = parse_dali_hits(out_file)

    # Compare structure
    assert len(ref_hits) == len(out_hits), "Hit count mismatch"

    for ref, out in zip(ref_hits, out_hits):
        assert ref.edomain == out.edomain
        assert abs(ref.zscore - out.zscore) < 0.01
        assert ref.alignments == out.alignments
```

### 7. Action Items

**Priority 1: Fix DALI (Step 7)**
1. Install libgfortran.so.3 or find static DALI binary
2. Fix path handling in `dpam/tools/dali.py`
3. Fix directory management in `dpam/steps/step07_iterative_dali.py`
4. Test with single ECOD domain first
5. Test with full 434 domains

**Priority 2: Generate Reference Data**
1. Set up v1.0 environment (Docker or direct)
2. Run v1.0 on AF-Q976I1-F1
3. Save all intermediate files to `tests/validation/reference/`
4. Document exact v1.0 command used

**Priority 3: Create Validation Tests**
1. Create `tests/validation/` directory
2. Write comparison utilities (parse_dali_hits, compare_ranges, etc.)
3. Write per-step validation tests
4. Integrate into pytest suite

**Priority 4: Validate Steps 8-13**
1. Run steps 8-13 on test case
2. Compare with v1.0 references
3. Fix any discrepancies
4. Document differences (if any)

**Priority 5: Validate Steps 15-24**
1. Run ML pipeline steps
2. Compare with v1.0 references
3. Validate TensorFlow model produces same results
4. Test merge candidates logic

### 8. Success Criteria

**Step 7 Fixed:**
- [ ] DALI produces non-empty output
- [ ] Number of hits matches v1.0 (±5%)
- [ ] Z-scores match within 0.1
- [ ] Alignment counts match exactly
- [ ] Residue mappings match exactly

**Full Pipeline:**
- [ ] All steps 1-24 produce output
- [ ] Final domain predictions match v1.0
- [ ] Domain boundaries match exactly
- [ ] ECOD assignments match (>95%)

### 9. Timeline Estimate

- **DALI fix**: 2-4 hours (dependencies + debugging)
- **Reference generation**: 1-2 hours (v1.0 setup + run)
- **Validation framework**: 2-3 hours (test infrastructure)
- **Steps 8-13 validation**: 3-5 hours (testing + fixes)
- **Steps 15-24 validation**: 4-6 hours (ML steps + testing)

**Total**: ~12-20 hours

### 10. Resources Needed

**Software:**
- [ ] libgfortran.so.3 (or DALI static binary)
- [ ] v1.0 Docker image (or working v1.0 installation)
- [ ] TensorFlow (for steps 16)

**Data:**
- [✓] Test structure: AF-Q976I1-F1
- [✓] ECOD reference data: ~/data/dpam_reference/ecod_data/
- [ ] v1.0 reference outputs
- [✓] DOMASS model: domass_epo29.*

**Compute:**
- CPU: 4-8 cores for parallel DALI
- Memory: 8-16 GB
- Storage: ~10 GB for intermediate files
