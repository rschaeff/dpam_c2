# DPAM v2.0 Validation Summary

## Quick Status

**Implementation**: 23/25 steps (92%)
**Validation Status**: 🔴 **BLOCKED** by DALI library issue

### Current Blockers

1. **DALI Missing Library** (libgfortran.so.3)
   - See: `docs/DALI_TROUBLESHOOTING.md`
   - **Action Required**: Install `libgfortran3` package
   - **Test Command**: `ldd ~/bin/DaliLite.v5/bin/puu`

2. **No v1.0 Reference Data**
   - Need to generate reference outputs from v1.0
   - See: `scripts/generate_v1_reference.sh`

## What's Been Done

### ✅ Implementation Complete (23/25 steps)

**Core Pipeline (Steps 1-13)**:
- Step 1: Structure preparation ✓
- Step 2: HHsearch sequence homology ✓
- Step 3: Foldseek structural search ✓
- Step 4: Filter Foldseek hits ✓
- Step 5: Map to ECOD hierarchy ✓
- Step 6: Get DALI candidates ✓
- Step 7: Iterative DALI alignment ✓
- Step 8: Analyze DALI results ✓
- Step 9: Get support scores ✓
- Step 10: Filter domains ✓
- Step 11: Secondary structure (SSE) ✓
- Step 12: Disorder prediction ✓
- Step 13: Parse domains ✓

**ML Pipeline (Steps 15-24)**:
- Step 15: Prepare DOMASS features ✓
- Step 16: Run DOMASS TensorFlow model ✓
- Step 17: Filter confident predictions ✓
- Step 18: Get template mappings ✓
- Step 19: Get merge candidates ✓
- Step 20: Extract domain PDBs ✓
- Step 21: Compare domain connectivity ✓
- Step 22: Merge domains ✓
- Step 23: Classify predictions (full/part/miss) ✓
- Step 24: Integrate results with SSE ✓

**Optional**:
- Step 25: Generate PDB files (visualization) - Not implemented

### ✅ Bug Fixes Applied

**DALI Implementation** (Step 7):
- Fixed path management (absolute paths)
- Removed problematic `os.chdir()` calls
- Added file existence checks
- Better error logging

**Files Modified**:
- `dpam/tools/dali.py` - Path resolution
- `dpam/steps/step07_iterative_dali.py` - Directory management

### ✅ Documentation Created

1. **VALIDATION_PLAN.md** - Comprehensive validation strategy
2. **DALI_TROUBLESHOOTING.md** - DALI debugging guide
3. **VALIDATION_SUMMARY.md** - This file

## What's Needed Next

### Priority 1: Fix DALI Dependency

**Install libgfortran.so.3:**

```bash
# Ubuntu/Debian
sudo apt-get install libgfortran3

# Or create symlink (risky):
cd /usr/lib/x86_64-linux-gnu/
sudo ln -s libgfortran.so.5 libgfortran.so.3
```

**Verify:**
```bash
# Should show all libraries resolved
ldd ~/bin/DaliLite.v5/bin/puu

# Quick test
cd ~/dev/dpam_c2/test_run
python3 -c "from dpam.tools.dali import DALI; d=DALI(); print(d.check_availability())"
```

### Priority 2: Test DALI Fix

**Single domain test:**
```bash
cd ~/dev/dpam_c2
python3 << 'EOF'
from pathlib import Path
from dpam.steps.step07_iterative_dali import run_dali

# Test single ECOD domain
result = run_dali((
    'AF-Q976I1-F1',
    '000001438',
    Path('test_run'),
    Path('/home/rschaeff_1/data/dpam_reference/ecod_data')
))

print(f"Success: {result}")
EOF

# Check output
ls -lh test_run/iterativeDali_AF-Q976I1-F1/AF-Q976I1-F1_000001438_hits
```

**Full step 7 test:**
```bash
# Clean previous attempt
rm -rf test_run/iterativeDali_AF-Q976I1-F1
rm -f test_run/AF-Q976I1-F1.iterativeDali.done
rm -f test_run/AF-Q976I1-F1_iterativdDali_hits

# Run with 2 CPUs
python3 << 'EOF'
from pathlib import Path
from dpam.steps.step07_iterative_dali import run_step7

success = run_step7(
    'AF-Q976I1-F1',
    Path('test_run'),
    Path('/home/rschaeff_1/data/dpam_reference/ecod_data'),
    cpus=2
)
print(f"Success: {success}")
EOF

# Verify output
wc -l test_run/AF-Q976I1-F1_iterativdDali_hits
head -20 test_run/AF-Q976I1-F1_iterativdDali_hits
```

### Priority 3: Generate v1.0 Reference Data

**Option A: Using script**
```bash
cd ~/dev/dpam_c2
./scripts/generate_v1_reference.sh AF-Q976I1-F1
```

Then manually run v1.0 pipeline and copy outputs to:
`tests/validation/reference/AF-Q976I1-F1/`

**Option B: Docker** (if available)
```bash
cd ~/dev/DPAM/old_docker/docker/
docker build -t dpam_v1 .
docker run -v ~/data/dpam_reference:/data \
           -v ~/dev/dpam_c2/tests/validation/reference/AF-Q976I1-F1:/output \
           dpam_v1 /work/AF-Q976I1-F1.pdb
```

**Option C: Manual**
1. Copy test structure to v1.0 working directory
2. Run v1.0 pipeline
3. Copy all intermediate files to `tests/validation/reference/AF-Q976I1-F1/`

### Priority 4: Create Validation Tests

Once reference data exists:

```bash
mkdir -p tests/validation
cd tests/validation

# Create validation test for each step
cat > test_step07_validation.py << 'EOF'
import pytest
from pathlib import Path

def test_step7_output_matches_v1():
    """Validate step 7 output matches v1.0."""
    ref_file = Path("reference/AF-Q976I1-F1/AF-Q976I1-F1_iterativdDali_hits")
    out_file = Path("../../test_run/AF-Q976I1-F1_iterativdDali_hits")

    # Parse files and compare
    # ... validation logic ...
EOF
```

## Test Cases

### Primary: AF-Q976I1-F1
- **Source**: AlphaFold structure
- **Size**: 108 residues (small, fast)
- **Status**: Partial outputs exist in `test_run/`
- **Steps Complete**: 1-6 ✓
- **Steps Failed**: 7 (DALI library issue)

### Secondary: O05012, O05023
- **Source**: v1.0 examples
- **Location**: `~/dev/DPAM/old_examples/example/test/`
- **Status**: Not yet tested

## Success Criteria

### Step 7 (DALI) Working
- [ ] Library dependency resolved
- [ ] Produces non-empty output
- [ ] ~50-150 hits for AF-Q976I1-F1 (434 candidates)
- [ ] Output format matches v1.0

### Full Pipeline Validation
- [ ] All 24 steps produce output
- [ ] File formats match v1.0
- [ ] Domain boundaries match exactly
- [ ] ECOD assignments match (>95%)
- [ ] Final predictions match v1.0

## Timeline Estimate

**If DALI fixed in next session:**
- Fix verification: 15 min
- Single domain test: 5 min
- Full step 7 test: 30-60 min
- Generate v1.0 reference: 1-2 hours
- Create validation tests: 2-3 hours
- Validate steps 8-13: 2-3 hours
- Validate steps 15-24: 3-4 hours

**Total: ~8-13 hours** (after DALI fix)

## Current Test Results

### Steps 1-6: ✅ PASSING
```
test_run/AF-Q976I1-F1.pdb               # 253 KB
test_run/AF-Q976I1-F1.fa                # 378 bytes
test_run/AF-Q976I1-F1.a3m               # 706 KB
test_run/AF-Q976I1-F1.hhr               # 1.7 MB
test_run/AF-Q976I1-F1.foldseek          # 3.3 MB
test_run/AF-Q976I1-F1.foldseek.flt.result  # 10 KB
test_run/AF-Q976I1-F1.map2ecod.result   # 548 bytes
test_run/AF-Q976I1-F1_hits4Dali         # 4.3 KB (434 candidates)
```

### Step 7: 🔴 FAILED
```
test_run/AF-Q976I1-F1_iterativdDali_hits  # 0 bytes (empty)
test_run/test_dali/log                     # Shows library error
```

**Error:**
```
libgfortran.so.3: cannot open shared object file
```

### Steps 8-24: ⏳ NOT TESTED
- Blocked by step 7 failure
- Will test once DALI working

## Files Created This Session

```
docs/VALIDATION_PLAN.md           # Comprehensive validation strategy
docs/DALI_TROUBLESHOOTING.md      # DALI debugging guide
docs/VALIDATION_SUMMARY.md        # This summary
scripts/generate_v1_reference.sh  # Helper script for reference generation
```

## Code Changes This Session

```
dpam/tools/dali.py                    # Fixed path management
dpam/steps/step07_iterative_dali.py  # Fixed directory handling
dpam/steps/step15_prepare_domass.py  # New: ML features
dpam/steps/step16_run_domass.py      # New: TensorFlow model
dpam/steps/step17_get_confident.py   # New: Filter predictions
dpam/steps/step18_get_mapping.py     # New: Template mappings
dpam/steps/step19_get_merge_candidates.py  # New: Merge candidates
dpam/steps/step20_extract_domains.py  # New: Extract PDBs
dpam/steps/step21_compare_domains.py  # New: Connectivity tests
dpam/steps/step22_merge_domains.py    # New: Merge via transitive closure
dpam/steps/step23_get_predictions.py  # New: Classify full/part/miss
dpam/steps/step24_integrate_results.py  # New: Integrate with SSE
dpam/pipeline/runner.py              # Updated: Added steps 15-24
dpam/core/models.py                  # Updated: Added pipeline steps enum
```

## Next Session Checklist

1. **Install libgfortran.so.3**
   ```bash
   sudo apt-get install libgfortran3
   # OR
   sudo ln -s /usr/lib/x86_64-linux-gnu/libgfortran.so.5 /usr/lib/x86_64-linux-gnu/libgfortran.so.3
   ```

2. **Verify DALI works**
   ```bash
   ldd ~/bin/DaliLite.v5/bin/puu
   python3 -c "from dpam.tools.dali import DALI; DALI().check_availability()"
   ```

3. **Test step 7**
   ```bash
   cd ~/dev/dpam_c2
   # Run test commands from Priority 2 above
   ```

4. **Generate reference data**
   ```bash
   ./scripts/generate_v1_reference.sh AF-Q976I1-F1
   # Then run v1.0 manually
   ```

5. **Create validation tests**
   - Set up `tests/validation/` structure
   - Write comparison functions
   - Test each step's output

## Contact Points

**Documentation:**
- Validation plan: `docs/VALIDATION_PLAN.md`
- DALI troubleshooting: `docs/DALI_TROUBLESHOOTING.md`
- Implementation guide: `docs/IMPLEMENTATION_GUIDE.md`

**Test Data:**
- Current outputs: `test_run/`
- Reference data (when ready): `tests/validation/reference/`
- ECOD data: `~/data/dpam_reference/ecod_data/`

**Key Files:**
- DALI wrapper: `dpam/tools/dali.py`
- Step 7 implementation: `dpam/steps/step07_iterative_dali.py`
- Pipeline runner: `dpam/pipeline/runner.py`
