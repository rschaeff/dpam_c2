# DPAM v2.0 Documentation

## Core Documentation

| Document | Description |
|----------|-------------|
| [V2_VALIDATION_REPORT.md](V2_VALIDATION_REPORT.md) | Comprehensive V1 vs V2 validation results (~10,000 proteins) |
| [PAPER_VS_IMPLEMENTATION.md](PAPER_VS_IMPLEMENTATION.md) | Comparison of published paper vs V1 vs V2 algorithm |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, data flow, and design patterns |
| [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) | Guide for adding new pipeline steps |
| [ML_PIPELINE_SETUP.md](ML_PIPELINE_SETUP.md) | TensorFlow model configuration and setup |
| [INSTALLATION.md](INSTALLATION.md) | Detailed installation instructions |

## Reference Documentation

| Document | Description |
|----------|-------------|
| [KNOWN_ISSUES.md](KNOWN_ISSUES.md) | Current known issues and workarounds |
| [DEPENDENCIES.md](DEPENDENCIES.md) | External tool requirements |
| [TESTING.md](TESTING.md) | Testing guide and practices |
| [DALI_INTEGRATION.md](DALI_INTEGRATION.md) | DALI tool integration details |
| [DALI_TROUBLESHOOTING.md](DALI_TROUBLESHOOTING.md) | DALI troubleshooting guide |
| [GEMMI_PYTHON_API.md](GEMMI_PYTHON_API.md) | Gemmi library usage reference |
| [DOMASS_SMALL_DOMAIN_LIMITATIONS.md](DOMASS_SMALL_DOMAIN_LIMITATIONS.md) | ML model limitations for small domains |

## Step Summaries

Quick reference for each pipeline step:

### Phase 1: Domain Identification (Steps 1-13)

| Step | Document | Description |
|------|----------|-------------|
| Step 1 | [STEP1_SUMMARY.md](STEP1_SUMMARY.md) | Prepare - Structure preparation |
| Step 2 | [STEP2_SUMMARY.md](STEP2_SUMMARY.md) | HHsearch - Sequence homology search |
| Step 3 | [STEP3_SUMMARY.md](STEP3_SUMMARY.md) | Foldseek - Structure similarity search |
| Step 4 | [STEP4_SUMMARY.md](STEP4_SUMMARY.md) | Filter Foldseek - Hit filtering |
| Step 5 | [STEP5_SUMMARY.md](STEP5_SUMMARY.md) | Map ECOD - Domain mapping |
| Step 6 | [STEP6_SUMMARY.md](STEP6_SUMMARY.md) | DALI Candidates - Candidate selection |
| Step 7 | [STEP7_SUMMARY.md](STEP7_SUMMARY.md) | Iterative DALI - Detailed alignment |
| Step 8 | [STEP8_SUMMARY.md](STEP8_SUMMARY.md) | Analyze DALI - Hit analysis |
| Step 9 | [STEP9_SUMMARY.md](STEP9_SUMMARY.md) | Get Support - Evidence integration |
| Step 10 | [STEP10_SUMMARY.md](STEP10_SUMMARY.md) | Filter Domains - Quality filtering |
| Step 11 | [STEP11_SUMMARY.md](STEP11_SUMMARY.md) | SSE - Secondary structure |
| Step 12 | [STEP12_SUMMARY.md](STEP12_SUMMARY.md) | Disorder - Disorder prediction |
| Step 13 | [STEP13_SUMMARY.md](STEP13_SUMMARY.md) | Parse Domains - Domain parsing |

### Phase 2: ECOD Assignment via DOMASS ML (Steps 14-19)

| Step | Document | Description |
|------|----------|-------------|
| Step 14 | [STEP14_SUMMARY.md](STEP14_SUMMARY.md) | Parse Domains V1 - Legacy duplicate |
| Step 15 | [STEP15_SUMMARY.md](STEP15_SUMMARY.md) | Prepare DOMASS - ML feature extraction |
| Step 16 | [STEP16_SUMMARY.md](STEP16_SUMMARY.md) | Run DOMASS - TensorFlow prediction |
| Step 17 | [STEP17_SUMMARY.md](STEP17_SUMMARY.md) | Get Confident - Confidence filtering |
| Step 18 | [STEP18_SUMMARY.md](STEP18_SUMMARY.md) | Get Mapping - Residue mapping |
| Step 19 | [STEP19_SUMMARY.md](STEP19_SUMMARY.md) | Get Merge Candidates - Merge identification |

### Phase 3: Domain Refinement & Output (Steps 20-24)

| Step | Document | Description |
|------|----------|-------------|
| Step 20 | [STEP20_SUMMARY.md](STEP20_SUMMARY.md) | Extract Domains - Domain PDB extraction |
| Step 21 | [STEP21_SUMMARY.md](STEP21_SUMMARY.md) | Compare Domains - Connectivity testing |
| Step 22 | [STEP22_SUMMARY.md](STEP22_SUMMARY.md) | Merge Domains - Transitive closure |
| Step 23 | [STEP23_SUMMARY.md](STEP23_SUMMARY.md) | Get Predictions - Classification |
| Step 24 | [STEP24_SUMMARY.md](STEP24_SUMMARY.md) | Integrate Results - Final output |

## Historical Documentation

Development history, session summaries, and superseded documents are in the `archive/` subdirectory. See [archive/README.md](archive/README.md) for details.

## Quick Links

- **Main README**: [../README.md](../README.md)
- **Claude Code Guide**: [../CLAUDE.md](../CLAUDE.md)
- **Validation Report**: [V2_VALIDATION_REPORT.md](V2_VALIDATION_REPORT.md)
