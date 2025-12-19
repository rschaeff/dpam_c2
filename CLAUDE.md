# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DPAM v2.0 is a modern Python 3 reimplementation of the Domain Parser for AlphaFold Models. It identifies structural domains through a 24-step pipeline integrating sequence homology (HHsearch), structural similarity (Foldseek, DALI), geometric analysis, confidence metrics (pLDDT, PAE), and machine learning (DOMASS/TensorFlow) for ECOD classification.

## Development Setup

```bash
# Install package in development mode
pip install -e . --break-system-packages

# With development dependencies (testing, type checking, formatting)
pip install -e ".[dev]" --break-system-packages

# Run tests
pytest tests/                    # All tests
pytest tests/unit/               # Unit tests only (fast, no external deps)
pytest tests/integration/        # Integration tests (require external tools)
pytest -m "not slow"             # Skip slow tests
pytest tests/integration/test_step02_hhsearch.py::TestStep02HHsearch::test_hhsearch_basic  # Single test

# With coverage
pytest --cov=dpam tests/

# Type checking
mypy dpam/

# Code formatting
black dpam/
flake8 dpam/
```

## Running the Pipeline

### Single Structure
```bash
# Full pipeline with checkpointing
dpam run AF-P12345 \
  --working-dir ./work \
  --data-dir /path/to/ecod_data \
  --cpus 4 \
  --resume

# Run specific step only
dpam run-step AF-P12345 \
  --step HHSEARCH \
  --working-dir ./work \
  --data-dir /path/to/ecod_data \
  --cpus 4
```

### Batch Processing
```bash
# Local parallel processing
dpam batch prefixes.txt \
  --working-dir ./work \
  --data-dir /path/to/ecod_data \
  --cpus 4 \
  --parallel 2 \
  --resume \
  --log-dir ./logs

# SLURM cluster submission
dpam slurm-submit prefixes.txt \
  --working-dir ./work \
  --data-dir /path/to/ecod_data \
  --cpus-per-task 8 \
  --mem-per-cpu 4G \
  --time 4:00:00 \
  --partition compute \
  --array-size 100
```

**CRITICAL - SLURM I/O Performance:**
The SLURM submission automatically copies the UniRef30 database (~260GB) to each node's local scratch space before running. HHblits is extremely I/O intensive - running hundreds of jobs against a shared NFS mount will saturate network bandwidth and destroy cluster performance for all users. Database copy takes 2-5 minutes but prevents hours of NFS thrashing. The generated SLURM script in `dpam/pipeline/slurm.py` handles this automatically via rsync to `$TMPDIR` or `/tmp/slurm-$SLURM_JOB_ID`.

### Manual SLURM Array Job Template

When running DPAM manually on SLURM (not via `dpam slurm-submit`), use this template:

```bash
#!/bin/bash
#SBATCH --job-name=dpam
#SBATCH --output=slurm_logs/%A_%a.out
#SBATCH --error=slurm_logs/%A_%a.err
#SBATCH --partition=96GB
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=4G
#SBATCH --time=8:00:00
#SBATCH --array=0-999

# Get protein prefix from list file
PREFIX=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" proteins.txt)

if [ -z "$PREFIX" ]; then
    echo "No prefix found for task $SLURM_ARRAY_TASK_ID"
    exit 0
fi

echo "Processing $PREFIX (task $SLURM_ARRAY_TASK_ID)"

# CRITICAL: Set up Anaconda environment with required packages
# The system Python (/usr/bin/python3) does NOT have gemmi, tensorflow, etc.
export PATH="/sw/apps/Anaconda3-2023.09-0/bin:$PATH"

# Copy UniRef30 to local scratch (optional but recommended for HHblits performance)
UNIREF_SRC="/home/rschaeff_1/data/dpam_reference/ecod_data/UniRef30_2022_02"
LOCAL_DB="/tmp/slurm-$SLURM_JOB_ID/UniRef30_2022_02"
if [ -d "$UNIREF_SRC" ]; then
    mkdir -p "$LOCAL_DB"
    rsync -a "$UNIREF_SRC/" "$LOCAL_DB/" 2>/dev/null || true
fi

# CRITICAL: Unset OMP_PROC_BIND for foldseek compatibility
# SLURM sets this by default, causing foldseek to fail
unset OMP_PROC_BIND

# Run pipeline - use Python invocation since 'dpam' may not be in PATH
cd /home/rschaeff/dev/dpam_c2
python3 -c "
import sys
sys.argv = ['dpam', 'run', '$PREFIX',
    '--working-dir', '/path/to/working_dir',
    '--data-dir', '/home/rschaeff_1/data/dpam_reference/ecod_data',
    '--cpus', '8',
    '--resume']
from dpam.cli.main import main
main()
"

# Cleanup local scratch
rm -rf "/tmp/slurm-$SLURM_JOB_ID" 2>/dev/null || true
```

**Key SLURM Environment Issues:**

1. **Python environment**: SLURM jobs don't inherit shell environment. Use absolute path to Anaconda Python (`/sw/apps/Anaconda3-2023.09-0/bin/python3`) or explicitly set PATH.

2. **`dpam` command not found**: The `dpam` entry point may not be in PATH on compute nodes. Use Python module invocation instead:
   ```python
   python3 -c "import sys; sys.argv = ['dpam', 'run', ...]; from dpam.cli.main import main; main()"
   ```

3. **`source ~/.bashrc` doesn't work**: SLURM runs non-interactive shells where `.bashrc` may not be sourced or may exit early. Set PATH explicitly.

4. **OMP_PROC_BIND conflict**: SLURM sets `OMP_PROC_BIND` which breaks foldseek. Always `unset OMP_PROC_BIND` before running.

5. **Missing packages**: System Python lacks gemmi, tensorflow, etc. Must use Anaconda or virtualenv with packages installed.

## Architecture

### Module Structure
```
dpam/
├── core/           # Type-safe dataclasses (Structure, Domain, Hit, PipelineState)
├── io/             # Readers (Gemmi-based CIF/PDB), writers, parsers (tool outputs)
├── tools/          # Wrappers for external tools (HHsuite, Foldseek, DALI, DSSP)
├── steps/          # Pipeline step implementations (step01-step24)
├── pipeline/       # Orchestration (runner, batch, slurm)
├── cli/            # Command-line interface
└── utils/          # Utilities (ranges, amino acids, logging)
```

**Critical Architecture Notes:**
- **Pipeline steps are loosely coupled**: Each step reads from working directory files and writes to working directory files. Steps only communicate via files, not in-memory objects.
- **Reference data is immutable**: ECOD databases loaded once in `DPAMPipeline.__init__()` and passed to steps as read-only data.
- **State management is external**: Pipeline state tracked in `.{prefix}.dpam_state.json` files, not in Python objects. Enables resume across process restarts.
- **Tool abstraction prevents mocking issues**: All external tools inherit from `ExternalTool` base class in `tools/base.py` with `check_availability()` and `run_command()` methods.
- **Dynamic step execution**: `DPAMPipeline._execute_step()` uses if/elif chain to import step modules dynamically. To add a new step, update `PipelineStep` enum in `core/models.py` and add corresponding elif branch in `pipeline/runner.py:_execute_step()`.

### Pipeline Steps (1-25)

**Current Status: 24/25 core steps implemented (96%); ML pipeline fully validated**

**Latest Update (2025-10-18)**: Steps 15-24 successfully tested end-to-end on validation protein O33946. All critical bugs fixed. See `docs/END_TO_END_PIPELINE.md` for complete workflow documentation.

#### Phase 1: Domain Identification (Steps 1-13)
| Step | Name | Status | File |
|------|------|--------|------|
| 1 | PREPARE | ✅ Implemented | `steps/step01_prepare.py` |
| 2 | HHSEARCH | ✅ Implemented | `steps/step02_hhsearch.py` |
| 3 | FOLDSEEK | ✅ Implemented | `steps/step03_foldseek.py` |
| 4 | FILTER_FOLDSEEK | ✅ Implemented | `steps/step04_filter_foldseek.py` |
| 5 | MAP_ECOD | ✅ Implemented | `steps/step05_map_ecod.py` |
| 6 | DALI_CANDIDATES | ✅ Implemented | `steps/step06_get_dali_candidates.py` |
| 7 | ITERATIVE_DALI | ✅ Implemented | `steps/step07_iterative_dali.py` |
| 8 | ANALYZE_DALI | ✅ Implemented | `steps/step08_analyze_dali.py` |
| 9 | GET_SUPPORT | ✅ Implemented | `steps/step09_get_support.py` |
| 10 | FILTER_DOMAINS | ✅ Implemented | `steps/step10_filter_domains.py` |
| 11 | SSE | ✅ Implemented | `steps/step11_sse.py` |
| 12 | DISORDER | ✅ Implemented | `steps/step12_disorder.py` |
| 13 | PARSE_DOMAINS | ✅ Implemented | `steps/step13_parse_domains.py` |

#### Phase 2: ECOD Assignment via DOMASS ML (Steps 14-19)
| Step | Name | Status | Description |
|------|------|--------|-------------|
| 14 | PARSE_DOMAINS_V1 | ✅ Duplicate | Same as step 13 in v1.0 |
| 15 | PREPARE_DOMASS | ✅ Implemented | Extract 17 ML features per domain-ECOD pair (`steps/step15_prepare_domass.py`) |
| 16 | RUN_DOMASS | ✅ Implemented | Run TensorFlow model for ECOD classification (`steps/step16_run_domass.py`) |
| 17 | GET_CONFIDENT | ✅ Implemented | Filter for high-confidence assignments (`steps/step17_get_confident.py`) |
| 18 | GET_MAPPING | ✅ Implemented | Map domains to ECOD template residues (`steps/step18_get_mapping.py`) |
| 19 | GET_MERGE_CANDIDATES | ✅ Implemented | Identify domains to merge (`steps/step19_get_merge_candidates.py`) |

#### Phase 3: Domain Refinement & Output (Steps 20-25)
| Step | Name | Status | Description |
|------|------|--------|-------------|
| 20 | EXTRACT_DOMAINS | ✅ Implemented | Extract domain PDB files for merge candidates (`steps/step20_extract_domains.py`) |
| 21 | COMPARE_DOMAINS | ✅ Implemented | Test sequence/structure connectivity (`steps/step21_compare_domains.py`) |
| 22 | MERGE_DOMAINS | ✅ Implemented | Merge domains via transitive closure (`steps/step22_merge_domains.py`) |
| 23 | GET_PREDICTIONS | ✅ Implemented | Classify domains as full/part/miss (`steps/step23_get_predictions.py`) |
| 24 | INTEGRATE_RESULTS | ✅ Implemented | Refine with SSE analysis, assign final labels (`steps/step24_integrate_results.py`) |
| 25 | GENERATE_PDBS | ⚠️ Optional | Generate visualization (PyMOL, HTML) |

**DOMASS ML Model**: Steps 15-19, 23 use a trained TensorFlow model (`domass_epo29.*` files) to assign ECOD classifications. The model uses 13 of 17 extracted features: domain properties (length, SSE counts), HHsearch scores (probability, coverage, rank), DALI scores (z-score, q-score, percentiles, rank), and consensus metrics (alignment agreement). See `docs/ML_PIPELINE_SETUP.md` for setup instructions.

**ML Pipeline Requirements**:
- TensorFlow installed (`pip install tensorflow`)
- Trained model checkpoint files: `domass_epo29.meta`, `.index`, `.data-*` in data directory
- Additional reference files: `tgroup_length`, `posi_weights/` directory

**ML Pipeline Validation (2025-10-18)**:
- ✅ **Batch tested on 15 validation proteins** (70-1245 residues, 1-9 domains)
- ✅ **100% completion rate** (15/15 proteins processed successfully)
- ✅ Fixed step 15 input file paths (`.goodDomains` instead of `.hhsearch`)
- ✅ Fixed step 15 ECOD hierarchy loading (column 1 instead of column 0)
- ✅ Fixed step 16 TensorFlow model architecture (layer names `dense`/`dense_1`)
- ✅ All steps (15-24) functional across diverse protein sizes
- 📊 Performance: 4.8s average per protein (range: 1.7-14.6s for 9-1872 features)
- 📊 Feature generation: avg 537.7 features, avg 62.2 high-confidence predictions
- ⚠️ Known issue: Small proteins (<100 features) need dynamic batch size fix
- See `docs/END_TO_END_PIPELINE.md` for single-protein validation details
- See `docs/ML_PIPELINE_BATCH_TEST.md` for comprehensive batch testing results

### Key Design Patterns

**Type Safety**: All data structures are type-hinted dataclasses validated with mypy. Every Structure, Domain, and Hit type has explicit field types.

**Checkpointing**: Pipeline state saved to `.dpam_state.json` after each step. Enables resume via `--resume` flag. State tracks completed_steps and failed_steps.

**Error Isolation**: Individual step failures don't stop pipeline execution. Failed steps logged but pipeline continues to next step. Critical for batch processing where some structures may fail.

**Lazy Loading**: Reference data (ECOD databases) loaded once per pipeline run in `DPAMPipeline.__init__()` and passed to steps that need it.

**Tool Abstraction**: External tools wrapped via abstract base class in `tools/base.py`. Each tool (HHsuite, Foldseek, DALI, DSSP) has availability checking, command execution, and error handling.

**Dynamic Step Execution**: `pipeline/runner.py` dynamically imports step modules based on PipelineStep enum. To add/modify steps, update the `_execute_step()` method in `DPAMPipeline` class.

## Implementation Guide

### Pipeline Step Pattern

Steps 1-7 are fully implemented and serve as reference examples. Remaining steps (8-13) should follow this pattern:

1. Create module in `steps/stepXX_<name>.py`
2. Define `run_stepX(prefix: str, working_dir: Path, ...) -> bool` function
3. Import and call external tools from `tools/`
4. Parse tool outputs using functions from `io/parsers.py`
5. Write results using functions from `io/writers.py`
6. Return True on success, False on failure (or raise exception)
7. Add import case to `DPAMPipeline._execute_step()` in `pipeline/runner.py`

**Reference implementations:**
- Simple step: `steps/step01_prepare.py` (structure preparation)
- CPU-bound: `steps/step02_hhsearch.py` (sequence search)
- I/O-bound: `steps/step03_foldseek.py` (structure search)
- Filtering: `steps/step04_filter_foldseek.py` (hit filtering)
- Mapping: `steps/step05_map_ecod.py` (ECOD domain mapping)
- Merging: `steps/step06_get_dali_candidates.py` (candidate merging)
- Parallel processing: `steps/step07_iterative_dali.py` (multiprocessing with Pool)

See `docs/IMPLEMENTATION_GUIDE.md` and step-specific docs in `docs/STEP*_*.md` for detailed patterns.

### Backward Compatibility Requirements

All intermediate file formats must match v1.0 exactly:
- Numeric precision (typically 2 decimals for scores)
- Column orders in result files
- Range string format (e.g., "10-50,60-100")
- File naming conventions

Compare outputs with v1.0 during testing to ensure compatibility.

## External Tool Dependencies

Required in PATH:
- **HHsuite**: hhblits, hhmake, hhsearch, addss.pl
- **Foldseek**: foldseek (easy-search command)
- **DALI**: dali.pl (from DaliLite.v5)
- **DSSP**: mkdssp or dsspcmbi (from DaliLite.v5)

### DaliLite.v5 Integration

DPAM now supports automatic detection of DaliLite.v5 installation:

**Search order for DALI (dali.pl):**
1. `$DALI_HOME/bin/dali.pl` (if DALI_HOME env var set)
2. `~/src/Dali_v5/DaliLite.v5/bin/dali.pl` (standard location)
3. System PATH

**Search order for DSSP:**
1. `$DALI_HOME/bin/dsspcmbi` (DaliLite version, preferred)
2. `~/src/Dali_v5/DaliLite.v5/bin/dsspcmbi` (standard location)
3. `mkdssp` in PATH (modern version)
4. `dsspcmbi` in PATH

**To use custom DALI installation:**
```bash
export DALI_HOME=/path/to/DaliLite.v5
```

**Standard installation location:**
- DaliLite.v5 should be installed at `~/src/Dali_v5/DaliLite.v5/`
- Binaries in `bin/` directory: `dali.pl`, `dsspcmbi`, `serialcompare`, etc.

On HPC clusters, load via modules:
```bash
module load hhsuite foldseek dali
```

## Reference Data Structure

ECOD databases required in `--data-dir`:
```
data/
├── UniRef30_2022_02/       # HHsearch database
├── pdb70/                  # HHsearch template database
├── ECOD_foldseek_DB/       # Foldseek database
├── ECOD70/                 # DALI templates (PDB files)
├── ECOD_length             # Domain lengths
├── ECOD_norms              # Normalization values
├── ECOD_pdbmap             # PDB→ECOD mapping
├── ecod.latest.domains     # ECOD metadata
├── ecod_weights/           # Position weights
└── ecod_domain_info/       # Domain statistics
```

## Performance Characteristics

**Bottleneck Steps**:
- **Step 2 (HHSEARCH)**: CPU-bound, parallelizes with `--cpus` (30-60 min typical, 90-95% of steps 1-6 time)
- **Step 7 (ITERATIVE_DALI)**: I/O + CPU-bound, uses multiprocessing.Pool (1-3h with 8 CPUs, ~400 domains × 2.5 iterations avg)
- **Step 13 (PARSE_DOMAINS)**: Memory-bound for large proteins, uses sparse matrices

**Resource Recommendations** (500-residue protein):
- Steps 1-6: 4 CPUs, 4GB memory, ~35-65 min total
- Step 7: 8-16 CPUs, 8-16GB memory, ~1.4h (scales near-linearly up to 8-16 CPUs)
- Steps 8-13: 1-4 CPUs, 4GB memory, ~30min

## File I/O Patterns

**Input**: Structure files (`.cif` or `.pdb`) and AlphaFold JSON (`.json` with PAE) placed in working directory.

**Intermediate**: Each step writes output files to working directory following naming convention `{prefix}.{extension}` (e.g., `AF-P12345.hhsearch`).

**Output**: Final domain definitions in `{prefix}.finalDPAM.domains`.

**State**: Hidden checkpoints in `.{prefix}.dpam_state.json` track pipeline progress.

Use `io/readers.py` for reading CIF/PDB (via Gemmi), FASTA, JSON. Use `io/writers.py` for writing PDB, FASTA, results. Use `io/parsers.py` for parsing tool outputs.

## Logging

Structured logging via `utils/logging_config.py`:
- Standard format for terminal output
- JSON format for SLURM jobs (`--json-log` flag)
- Step start/complete/failed logged with timestamps and durations
- Use `get_logger(__name__)` in each module

## Documentation

Comprehensive documentation available in `docs/`:
- **PROGRESS.md**: Current implementation status and timeline
- **ARCHITECTURE.md**: System architecture and data flow
- **IMPLEMENTATION_GUIDE.md**: Developer guide for adding steps
- **STEP*_IMPLEMENTATION.md**: Technical details for each step
- **STEP*_USAGE.md**: Usage guides for each step
- **STEP*_SUMMARY.md**: Quick reference summaries

## Key Implementation Notes

### Step 7 (Iterative DALI) - Critical Details

Step 7 uses **exact v1.0 gap tolerance formula** for domain range calculation:
```python
cutoff = max(5, len(resids) * 0.05)
```
This affects how residues are grouped into segments and is critical for matching v1.0 output.

**Multiprocessing pattern**: Uses `multiprocessing.Pool` with domain-level parallelism. Each ECOD domain is processed independently by a worker process, enabling near-linear speedup up to 8-16 CPUs.

**Temporary files**: Creates `iterativeDali_{prefix}/` directory with per-domain subdirectories. All temporary directories are cleaned up after completion, keeping only the final `{prefix}_iterativdDali_hits` file.

**Output format**: Tab-delimited with specific format required for downstream steps. Header line format:
```
>{edomain}_{iteration}\t{zscore}\t{n_aligned}\t{q_len}\t{t_len}
```

### ML Pipeline Integration (Steps 15-23)

**Implementation Status**: All ML steps fully implemented and integrated into pipeline runner.

**Key Integration Points**:
- Step 13 writes both `.finalDPAM.domains` and `.step13_domains` for ML pipeline compatibility
- Utility functions `parse_range` and `format_range` added as aliases for ML step imports
- All steps integrated into `DPAMPipeline._execute_step()` method
- PipelineStep enum includes all ML steps

**Setup Requirements**:
- Install TensorFlow: `pip install tensorflow`
- Obtain trained model files: `domass_epo29.*` checkpoint in data directory
- Ensure reference data includes: `tgroup_length`, `posi_weights/` directory

**Documentation**: See `docs/ML_PIPELINE_SETUP.md` for complete setup and usage guide
- current alphafold version is v6