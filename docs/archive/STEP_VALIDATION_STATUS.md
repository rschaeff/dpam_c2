# DPAM v2.0 Step Validation Status

**Last Updated**: 2025-10-09
**Test Structure**: P38326 (303 residues, experimental PDB)

---

## Summary Statistics

| Category | Count | Percentage |
|----------|-------|------------|
| **Total Steps** | 25 | 100% |
| **Implemented** | 18 | 72% |
| **Not Implemented** | 5 | 20% |
| **Optional** | 1 | 4% |
| **Duplicate** | 1 | 4% |
| | | |
| **Validated** | 2 | 8% |
| **Needs Testing** | 16 | 64% |
| **N/A (Not Impl)** | 6 | 24% |

---

## Phase 1: Domain Identification (Steps 1-13)

### Step 1: PREPARE
**Status**: ✅ Implemented | ✅ **VALIDATED**
**File**: `steps/step01_prepare.py`
**Test**: P38326
**Result**: ✓ FASTA output matches v1.0 **exactly** (2/2 lines)

**What it does**: Extract sequence from PDB, standardize structure
**Input**: `{prefix}.pdb`
**Output**: `{prefix}.fa`, standardized PDB

---

### Step 2: HHSEARCH
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step02_hhsearch.py`
**Test**: Copied v1.0 reference data (too slow)
**Blocker**: 30-60 min runtime per structure

**What it does**: Sequence homology search vs UniRef30
**Input**: `{prefix}.fa`
**Output**: `{prefix}.a3m`, `{prefix}.hhr`, `{prefix}.hhsearch`
**Dependencies**: HHblits, HHsearch (working)

---

### Step 3: FOLDSEEK
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step03_foldseek.py`
**Test**: Copied v1.0 reference data (too slow)
**Blocker**: 5-10 min runtime per structure

**What it does**: Structural search vs ECOD database
**Input**: `{prefix}.pdb`
**Output**: `{prefix}.foldseek`
**Dependencies**: Foldseek (working)

---

### Step 4: FILTER_FOLDSEEK
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step04_filter_foldseek.py`
**Test**: Not run (depends on step 3)

**What it does**: Filter Foldseek hits by alignment quality
**Input**: `{prefix}.foldseek`
**Output**: `{prefix}.foldseek.flt.result`

---

### Step 5: MAP_ECOD
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step05_map_ecod.py`
**Test**: Not run (depends on steps 2-4)

**What it does**: Map HHsearch/Foldseek hits to ECOD hierarchy
**Input**: `{prefix}.hhsearch`, `{prefix}.foldseek.flt.result`
**Output**: `{prefix}.map2ecod.result`

---

### Step 6: DALI_CANDIDATES
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step06_get_dali_candidates.py`
**Test**: Not run (depends on step 5)

**What it does**: Select ECOD domains for DALI alignment
**Input**: `{prefix}.map2ecod.result`
**Output**: `{prefix}_hits4Dali`

---

### Step 7: ITERATIVE_DALI
**Status**: ✅ Implemented | ❌ **NOT VALIDATED**
**File**: `steps/step07_iterative_dali.py`
**Test**: Not run (needs ECOD data + valid candidates)
**Blocker**: **THIS IS THE KEY STEP TO TEST**

**What it does**: Iteratively align query vs ECOD templates, remove matched regions
**Input**: `{prefix}_hits4Dali`, `{prefix}.pdb`, ECOD70 templates
**Output**: `{prefix}_iterativdDali_hits`
**Dependencies**:
- ✅ DALI (dali.pl) - integrated with DaliLite.v5
- ✅ Multiprocessing support
- ❓ Output format compatibility with v1.0

**Runtime**: 1-3 hours (400 domains × 2.5 iterations avg, 8 CPUs)

---

### Step 8: ANALYZE_DALI
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step08_analyze_dali.py`
**Test**: Not run (depends on step 7)

**What it does**: Parse DALI results, calculate z-score percentiles
**Input**: `{prefix}_iterativdDali_hits`
**Output**: `{prefix}.dali_analysis`

---

### Step 9: GET_SUPPORT
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step09_get_support.py`
**Test**: Not run (depends on steps 7-8)

**What it does**: Calculate domain support scores from HHsearch + DALI
**Input**: `{prefix}.hhsearch`, `{prefix}.dali_analysis`
**Output**: `{prefix}.support`

---

### Step 10: FILTER_DOMAINS
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step10_filter_domains.py`
**Test**: Not run (depends on steps 8-9)

**What it does**: Filter domains by support scores
**Input**: `{prefix}.support`
**Output**: `{prefix}.goodDomains`

---

### Step 11: SSE (Secondary Structure Elements)
**Status**: ✅ Implemented | ✅ **VALIDATED**
**File**: `steps/step11_sse.py`
**Test**: P38326
**Result**: ✓ All 9 SSE segments match v1.0 **exactly**
**Fixed**: DSSP parser now handles missing residues

**What it does**: Assign secondary structure using DSSP
**Input**: `{prefix}.pdb`, `{prefix}.fa`
**Output**: `{prefix}.sse` (303/303 residues)
**Dependencies**:
- ✅ DSSP (dsspcmbi) - integrated with DaliLite.v5
- ✅ Parser handles PDB gaps

---

### Step 12: DISORDER
**Status**: ✅ Implemented | ❌ **FAILED**
**File**: `steps/step12_disorder.py`
**Test**: P38326
**Result**: ✗ Missing `{prefix}.json` (AlphaFold PAE matrix)
**Blocker**: Requires AlphaFold structures with confidence data

**What it does**: Predict disordered regions from PAE + SSE
**Input**: `{prefix}.sse`, `{prefix}.json` (PAE), `{prefix}.goodDomains`
**Output**: `{prefix}.diso`
**Note**: Not applicable to experimental PDB structures

---

### Step 13: PARSE_DOMAINS
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step13_parse_domains.py`
**Test**: Not run (depends on steps 7-12)
**Blocker**: Needs full pipeline through step 10

**What it does**: Parse final domain definitions from all evidence
**Input**: Multiple upstream files
**Output**: `{prefix}.domains`
**Complexity**: ~500 lines, probability calculations, clustering

---

## Phase 2: ECOD Assignment via DOMASS ML (Steps 14-19)

### Step 14: PARSE_DOMAINS_V1
**Status**: ✅ Duplicate of Step 13
**Note**: Compatibility layer for v1.0

---

### Step 15: PREPARE_DOMASS
**Status**: ❌ **NOT IMPLEMENTED**
**Blocker**: ML feature extraction not coded yet

**What it does**: Extract 17 ML features per domain-ECOD pair
**Features**: domain length, SSE counts, HHsearch scores, DALI scores, consensus metrics

---

### Step 16: RUN_DOMASS
**Status**: ❌ **NOT IMPLEMENTED**
**Blocker**: TensorFlow model integration not coded

**What it does**: Run TensorFlow model for ECOD classification
**Dependencies**: `domass_epo29.*` model files

---

### Step 17: GET_CONFIDENT
**Status**: ❌ **NOT IMPLEMENTED**
**Blocker**: Depends on step 16

**What it does**: Filter for high-confidence ECOD assignments

---

### Step 18: GET_MAPPING
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step18_get_mapping.py`
**Test**: Not run (depends on step 17)

**What it does**: Map domains to ECOD template residues

---

### Step 19: GET_MERGE_CANDIDATES
**Status**: ❌ **NOT IMPLEMENTED**
**Blocker**: Domain merging logic not coded

**What it does**: Identify domains that should be merged

---

## Phase 3: Domain Refinement & Output (Steps 20-25)

### Step 20: EXTRACT_DOMAINS
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step20_extract_domains.py`
**Test**: Not run (depends on step 19)

**What it does**: Extract domain PDB files for merge candidates

---

### Step 21: COMPARE_DOMAINS
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step21_compare_domains.py`
**Test**: Not run (depends on step 20)

**What it does**: Test sequence/structure connectivity between domains

---

### Step 22: MERGE_DOMAINS
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step22_merge_domains.py`
**Test**: Not run (depends on step 21)

**What it does**: Merge domains via transitive closure

---

### Step 23: GET_PREDICTIONS
**Status**: ❌ **NOT IMPLEMENTED**
**Blocker**: Classification logic not coded

**What it does**: Classify domains as full/part/miss

---

### Step 24: INTEGRATE_RESULTS
**Status**: ✅ Implemented | ⚠️ **NOT TESTED**
**File**: `steps/step24_integrate_results.py`
**Test**: Not run (depends on step 23)

**What it does**: Refine with SSE analysis, assign final labels
**Output**: `{prefix}.finalDPAM.domains`

---

### Step 25: GENERATE_PDBS
**Status**: ⚠️ **OPTIONAL** (not implemented)

**What it does**: Generate visualization (PyMOL, HTML)

---

## Critical Path for Full Validation

To complete validation, test in this order:

### Priority 1: Core Pipeline (Steps 1-13)
```
1. ✅ PREPARE (validated)
2. ⏭️ HHSEARCH (need runtime test)
3. ⏭️ FOLDSEEK (need runtime test)
4. ⏭️ FILTER_FOLDSEEK
5. ⏭️ MAP_ECOD
6. ⏭️ DALI_CANDIDATES
7. 🔴 ITERATIVE_DALI ← **CRITICAL: NOT TESTED**
8. ⏭️ ANALYZE_DALI
9. ⏭️ GET_SUPPORT
10. ⏭️ FILTER_DOMAINS
11. ✅ SSE (validated)
12. 🔴 DISORDER (needs AlphaFold JSON)
13. ⏭️ PARSE_DOMAINS
```

### Priority 2: Implement Missing ML Steps (15-17, 19, 23)
```
15. ❌ PREPARE_DOMASS
16. ❌ RUN_DOMASS
17. ❌ GET_CONFIDENT
19. ❌ GET_MERGE_CANDIDATES
23. ❌ GET_PREDICTIONS
```

### Priority 3: Test Refinement Steps (18, 20-22, 24)
```
18. ⏭️ GET_MAPPING
20. ⏭️ EXTRACT_DOMAINS
21. ⏭️ COMPARE_DOMAINS
22. ⏭️ MERGE_DOMAINS
24. ⏭️ INTEGRATE_RESULTS
```

---

## Recommended Next Test

### Test Case: Full Pipeline Through Step 13

**Structure**: Use AlphaFold model with JSON (e.g., AF-Q976I1-F1)

**Steps to run**:
```bash
cd ~/dev/dpam_c2

# Setup test structure
PREFIX="AF-Q976I1-F1"
WORK_DIR="test_run/${PREFIX}"
DATA_DIR="/path/to/ecod_data"

# Run full pipeline
dpam run ${PREFIX} \
  --working-dir ${WORK_DIR} \
  --data-dir ${DATA_DIR} \
  --cpus 8 \
  --resume
```

**Expected outputs**:
- Step 1: `{prefix}.fa` ✓
- Step 2: `{prefix}.hhsearch` (30-60 min)
- Step 3: `{prefix}.foldseek` (5-10 min)
- Step 4: `{prefix}.foldseek.flt.result`
- Step 5: `{prefix}.map2ecod.result`
- Step 6: `{prefix}_hits4Dali`
- **Step 7**: `{prefix}_iterativdDali_hits` ← **KEY TEST**
- Step 8-10: Domain filtering
- Step 11: `{prefix}.sse` ✓
- Step 12: `{prefix}.diso` (needs JSON)
- Step 13: `{prefix}.domains`

**Validation**: Compare all outputs with v1.0 reference

---

## Validation Criteria

### Exact Match Required
- ✅ Step 1: FASTA sequence
- Step 13: Final domain boundaries
- Step 24: Final DPAM output

### Close Match Acceptable (±5%)
- Step 2: HHsearch hits (order may vary)
- Step 3: Foldseek hits (order may vary)
- Step 7: DALI z-scores (±0.1)
- Step 11: SSE segments (minor type differences OK)

### Format Match Required
- All intermediate files must be parseable by downstream steps
- Column orders must match v1.0
- Numeric precision (typically 2 decimals)

---

## Blockers to Full Validation

1. **Step 7 (ITERATIVE_DALI)**:
   - ✅ DALI integrated
   - ❓ Output format not validated
   - ❓ Performance not tested
   - **Action**: Run on test structure with ECOD data

2. **Step 12 (DISORDER)**:
   - ❌ Requires AlphaFold JSON
   - Not applicable to experimental structures
   - **Action**: Test with AlphaFold model or make optional

3. **Steps 15-17, 19, 23**:
   - ❌ Not implemented
   - ML pipeline not critical for basic functionality
   - **Action**: Can skip for initial validation

4. **Runtime Tests**:
   - Steps 2, 3, 7 not performance-tested
   - **Action**: Run on small test set, measure time

---

## Test Data Requirements

### For Complete Testing
- ✅ Experimental PDB (P38326) - no JSON
- ⏭️ AlphaFold model with JSON - full pipeline
- ⏭️ Small protein (< 200 residues) - fast testing
- ⏭️ Large protein (> 500 residues) - stress test
- ⏭️ Multi-domain protein - domain parsing
- ⏭️ Single-domain protein - negative test

### Available Reference Data
- ✅ P38326 (303 residues, experimental)
- ⏭️ AF-Q976I1-F1 (partial outputs exist)
- ⏭️ O05012, O05023 (v1.0 examples)

---

## Key Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Steps Implemented | 24/25 (96%) | 18/25 (72%) |
| Steps Validated | 13/24 (54%) | 2/24 (8%) |
| Phase 1 Complete | 13/13 (100%) | 13/13 (100%) ✓ |
| Phase 1 Validated | 13/13 (100%) | 2/13 (15%) |
| Core Tools Working | 4/4 (100%) | 4/4 (100%) ✓ |
| End-to-End Test | 1 structure | 0 structures |
