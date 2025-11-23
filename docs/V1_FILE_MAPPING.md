# DPAM v1.0 File Mapping

**Created**: 2025-11-22
**Purpose**: Map DPAM v1.0 (dpam_automatic) file outputs to dpam_c2 pipeline steps

## Overview

DPAM v1.0 uses different step numbering and file naming conventions than dpam_c2. This document maps v1.0 outputs to v2.0 for validation purposes.

## Critical Insight: Step Number Mismatch

**v1.0 has 25 steps**, **dpam_c2 has 24 steps**.

The numbering diverges because:
- v1.0 Step 1-2: Separate FASTA and PDB extraction (2 steps)
- dpam_c2 Step 1: Combined PREPARE (1 step)

After Step 2, numbering is off by 1 until step 14, then aligns again for ML pipeline.

## Complete Step Mapping

| v1.0 Step | v1.0 Script | Output Files | dpam_c2 Step | dpam_c2 Name |
|-----------|-------------|--------------|--------------|--------------|
| **1** | `step1_get_AFDB_seqs.py` | `{prot}.fa` | **1** | PREPARE |
| **2** | `step2_get_AFDB_pdbs.py` | `{prot}.pdb` | **1** | PREPARE |
| **3** | `step3_run_hhsearch.py` | `{prot}.hhsearch`, `.a3m`, `.hmm` | **2** | HHSEARCH |
| **4** | `step4_run_foldseek.py` | `{prot}.foldseek` | **3** | FOLDSEEK |
| **5** | `step5_process_hhsearch.py` | `{prot}_sequence.result` | **5** | MAP_ECOD |
| **6** | `step6_process_foldseek.py` | `{prot}_structure.result` | **5** | MAP_ECOD |
| **7** | `step7_prepare_dali.py` | `{prot}_hits` (combined list) | **6** | DALI_CANDIDATES |
| **8** | `step8_iterative_dali.py` | `{prot}_hits` (DALI results) | **7** | ITERATIVE_DALI |
| **9** | `step9_analyze_dali.py` | `{prot}_good_hits` | **8** | ANALYZE_DALI |
| **10** | `step10_get_support.py` | `{prot}_sequence.result`, `_structure.result` | **9** | GET_SUPPORT |
| **11** | `step11_get_good_domains.py` | `{prot}.goodDomains` | **10** | FILTER_DOMAINS |
| **12** | `step12_get_sse.py` | `{prot}.sse` | **11** | SSE |
| **13** | `step13_get_diso.py` | `{prot}.diso` | **12** | DISORDER |
| **14** | `step14_parse_domains.py` | `{prot}.domains` | **13** | PARSE_DOMAINS |
| **15** | `step15_prepare_domass.py` | `{prot}.data` | **15** | PREPARE_DOMASS |
| **16** | `step16_run_domass.py` | `{prot}.result` | **16** | RUN_DOMASS |
| **17** | `step17_get_confident.py` | `{prot}.result` | **17** | GET_CONFIDENT |
| **18** | `step18_get_mapping.py` | `{prot}.data` | **18** | GET_MAPPING |
| **19** | `step19_get_merge_candidates.py` | `{prot}.result`, `.info` | **19** | GET_MERGE_CANDIDATES |
| **20** | `step20_extract_domains.py` | Domain PDB files | **20** | EXTRACT_DOMAINS |
| **21** | `step21_compare_domains.py` | `{prot}.result` | **21** | COMPARE_DOMAINS |
| **22** | `step22_merge_domains.py` | `{prot}.result` | **22** | MERGE_DOMAINS |
| **23** | `step23_get_predictions.py` | `{prot}.assign` | **23** | GET_PREDICTIONS |
| **24** | `step24_integrate_results.py` | `{prot}_domains` | **24** | INTEGRATE_RESULTS |
| **25** | `step25_generate_pdbs.py` | `.pdb`, `.pml`, `.html` (viz) | **N/A** | (Optional visualization) |

## File Naming Conventions

### Pattern Types

**Type 1: Direct extension**
```
{protein}.{ext}
```
Examples: `A0A024R1R8.fa`, `A0A024R1R8.pdb`, `A0A024R1R8.sse`

**Type 2: Underscore suffix**
```
{protein}_{suffix}
```
Examples: `A0A024R1R8_hits`, `A0A024R1R8_good_hits`, `A0A024R1R8_domains`

**Type 3: Compound extensions**
```
{protein}_{type}.{ext}
```
Examples: `A0A024R1R8_sequence.result`, `A0A024R1R8_structure.result`

### Directory Structure

v1.0 outputs are stored in step-specific directories:

```
dpam_automatic/
├── step1/homsa/
│   ├── A0A024R1R8.fa
│   └── ...
├── step2/homsa/
│   ├── A0A024R1R8.pdb
│   └── ...
├── step3/homsa/
│   ├── A0A024R1R8.hhsearch
│   ├── A0A024R1R8.a3m
│   ├── A0A024R1R8.hmm
│   └── ...
├── step11/homsa/
│   ├── A0A024R1R8.goodDomains
│   └── ...
...
```

Note: Files are often **copied forward** to subsequent step directories, so the same file may appear in multiple locations.

## Complete File Extension Reference

| Extension | v1.0 Step(s) | dpam_c2 Equivalent | Description |
|-----------|--------------|-------------------|-------------|
| `.fa` | 1 | `{prefix}.fasta` | FASTA sequence |
| `.pdb` | 2, 20, 25 | `{prefix}.pdb` | PDB structure |
| `.a3m` | 3 | (temp file) | MSA from HHblits |
| `.hmm` | 3 | (temp file) | HMM profile |
| `.hhsearch` | 3 | `{prefix}.hhsearch` | HHsearch results |
| `.foldseek` | 4 | `{prefix}.foldseek` | Foldseek results |
| `.result` | 5, 6, 10, 16, 17, 19, 21, 22 | (various) | Generic result file |
| `_hits` | 7, 8 | `{prefix}_iterativdDali_hits` | DALI hit list |
| `_good_hits` | 9 | `{prefix}_good_hits` | Filtered DALI hits |
| `_sequence.result` | 5, 10 | `{prefix}.map2ecod.result` | Sequence-based ECOD mapping |
| `_structure.result` | 6, 10 | (merged with sequence) | Structure-based ECOD mapping |
| `.goodDomains` | 11 | `{prefix}.goodDomains` | Supported domains |
| `.sse` | 12 | `{prefix}.sse` | Secondary structure |
| `.diso` | 13 | `{prefix}.diso` | Disorder prediction |
| `.domains` | 14 | `{prefix}.step13_domains` | Parsed domain definitions |
| `.data` | 15, 18 | `{prefix}.domass_features` | ML features |
| `.assign` | 23 | `{prefix}.step23_predictions` | ECOD assignments |
| `_domains` | 24 | `{prefix}.finalDPAM.domains` | Final integrated domains |
| `.info` | 19 | (internal) | Merge candidate info |
| `.pml` | 25 | (optional) | PyMOL visualization |
| `.html` | 25 | (optional) | HTML visualization |

## Validation Mapping

### What We Have in v1_outputs/

Based on collected v1.0 outputs, here's what validation can check:

| v1.0 File | v1.0 Step | dpam_c2 File | dpam_c2 Step | Coverage |
|-----------|-----------|--------------|--------------|----------|
| `{p}.fa` | 1 | `{p}.fasta` | 1 (PREPARE) | ✅ 5/5 |
| `{p}.pdb` | 2 | `{p}.pdb` | 1 (PREPARE) | ✅ 5/5 |
| `{p}.hhsearch` | 3 | `{p}.hhsearch` | 2 (HHSEARCH) | ✅ 5/5 |
| `{p}.foldseek` | 4 | `{p}.foldseek` | 3 (FOLDSEEK) | ✅ 5/5 |
| `{p}_sequence.result` | 5 | `{p}.map2ecod.result` | 5 (MAP_ECOD) | ✅ 5/5 |
| `{p}_structure.result` | 6 | (merged) | 5 (MAP_ECOD) | ✅ 5/5 |
| `{p}_hits` | 7-8 | `{p}_iterativdDali_hits` | 7 (ITERATIVE_DALI) | ✅ 5/5 |
| `{p}_good_hits` | 9 | `{p}_good_hits` | 8 (ANALYZE_DALI) | ✅ 5/5 |
| `{p}.goodDomains` | 11 | `{p}.goodDomains` | 10 (FILTER_DOMAINS) | ✅ 5/5 |
| `{p}.sse` | 12 | `{p}.sse` | 11 (SSE) | ✅ 5/5 |
| `{p}.diso` | 13 | `{p}.diso` | 12 (DISORDER) | ✅ 5/5 |
| `{p}.domains` | 14 | `{p}.step13_domains` | 13 (PARSE_DOMAINS) | ⚠️ 3/5 |
| `{p}.data` | 15 | `{p}.domass_features` | 15 (PREPARE_DOMASS) | ⚠️ 3/5 |
| `{p}.assign` | 23 | `{p}.step23_predictions` | 23 (GET_PREDICTIONS) | ⚠️ 3/5 |
| `{p}_domains` | 24 | `{p}.finalDPAM.domains` | 24 (INTEGRATE_RESULTS) | ⚠️ 3/5 |

**Note**: `{p}` = protein UniProt ID (e.g., `A0A024R1R8`)

### Missing from v1_outputs/

The following v1.0 outputs are **not present** in our collected reference data:

- Step 10 `.result` files (GET_SUPPORT outputs)
- Step 16 `.result` files (RUN_DOMASS predictions)
- Step 17-19 intermediate ML files
- Step 20-22 domain extraction/merge intermediates

These may have been cleaned up or use different naming patterns. Need to investigate actual v1.0 directory structure.

## Key Differences: v1.0 vs v2.0

### File Naming

1. **Protein ID format**:
   - v1.0: Uses bare UniProt ID (`A0A024R1R8`)
   - dpam_c2: Uses full AlphaFold ID (`AF-A0A024R1R8-F1`) as prefix

2. **Extension conventions**:
   - v1.0: Underscore separators (`_hits`, `_domains`, `_sequence.result`)
   - dpam_c2: Dot separators + step numbers (`.step13_domains`, `.step23_predictions`)

3. **Directory structure**:
   - v1.0: Step-specific directories (`step1/homsa/`, `step2/homsa/`, ...)
   - dpam_c2: Single working directory with all outputs

### Content Differences

While file formats should be similar, there may be minor differences:

1. **Floating-point precision**: Different rounding in scores
2. **Column order**: Some files may have reordered columns
3. **Header lines**: v2.0 may add/change headers
4. **Whitespace**: Spacing differences

These should be handled by validation framework's tolerance settings.

## Validation Strategy

### Phase 1: Early Steps (Full Coverage)

Validate steps 1-9 using all 5 proteins:
- Structure preparation (v1.0 steps 1-2 → dpam_c2 step 1)
- Sequence/structure search (v1.0 steps 3-4 → dpam_c2 steps 2-3)
- ECOD mapping (v1.0 steps 5-6 → dpam_c2 step 5)
- DALI alignment (v1.0 steps 7-9 → dpam_c2 steps 6-8)

### Phase 2: Domain Filtering (Full Coverage)

Validate steps 10-12 using all 5 proteins:
- Domain filtering (v1.0 step 11 → dpam_c2 step 10)
- SSE/disorder (v1.0 steps 12-13 → dpam_c2 steps 11-12)

### Phase 3: ML Pipeline (Partial Coverage)

Validate steps 13-24 using 3 proteins (RBG1, B6H5, B6H7):
- Domain parsing (v1.0 step 14 → dpam_c2 step 13)
- ML features (v1.0 step 15 → dpam_c2 step 15)
- ECOD assignment (v1.0 step 23 → dpam_c2 step 23)
- Integration (v1.0 step 24 → dpam_c2 step 24)

## Next Steps

1. **Update validation framework** to use correct v1.0 file names
2. **Map v1.0 file formats** to understand content structure
3. **Collect missing v1.0 outputs** for comprehensive validation
4. **Test validation** on 5-protein subset
5. **Document known differences** between v1.0 and v2.0 outputs

## References

- v1.0 source code: `v1_scripts/`
- v1.0 outputs: `v1_outputs/`
- dpam_c2 documentation: `docs/CLAUDE.md`
- Validation framework: `scripts/validate_against_v1.py`
