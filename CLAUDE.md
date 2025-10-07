# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DPAM v2.0 is a modern Python 3 reimplementation of the Domain Parser for AlphaFold Models. It identifies structural domains through a 13-step pipeline integrating sequence homology (HHsearch), structural similarity (Foldseek, DALI), geometric analysis, and confidence metrics (pLDDT, PAE).

## Development Setup

```bash
# Install package in development mode
pip install -e . --break-system-packages

# With development dependencies (testing, type checking, formatting)
pip install -e ".[dev]" --break-system-packages

# Run tests
pytest tests/

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

## Architecture

### Module Structure
```
dpam/
├── core/           # Type-safe dataclasses (Structure, Domain, Hit, PipelineState)
├── io/             # Readers (Gemmi-based CIF/PDB), writers, parsers (tool outputs)
├── tools/          # Wrappers for external tools (HHsuite, Foldseek, DALI, DSSP)
├── steps/          # Pipeline step implementations (step01-step13)
├── pipeline/       # Orchestration (runner, batch, slurm)
├── cli/            # Command-line interface
└── utils/          # Utilities (ranges, amino acids, logging)
```

### Pipeline Steps (1-13)

**Current Status: 13/13 steps implemented (100%) ✅**

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
- **DALI**: dali.pl
- **DSSP**: mkdssp

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

### Remaining Steps (8-13)

**Next priority**: Step 8 (Analyze DALI) - parses iterative DALI results, calculates scores and percentiles

**Independent step**: Step 11 (SSE) can be implemented independently using existing DSSP wrapper

**Most complex**: Step 13 (Parse Domains) requires probability calculations, clustering, and multiple refinement passes (~500 lines estimated)
