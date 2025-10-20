# DPAM v2.0 - Domain Parser for AlphaFold Models

Modern, type-safe reimplementation of the DPAM pipeline for identifying structural domains in AlphaFold predicted structures.

## Overview

DPAM identifies structural domains through a 13-step pipeline that integrates:
- **Sequence homology** (HHsearch against ECOD)
- **Structural similarity** (Foldseek, DALI against ECOD)
- **Geometric analysis** (inter-residue distances, PAE matrices)
- **Confidence metrics** (pLDDT, secondary structure, disorder prediction)

## Key Features

✨ **Modern Python 3** with type hints and dataclasses  
🔄 **Automatic checkpointing** and resume capability  
🚀 **SLURM integration** for HPC clusters  
📊 **Structured logging** (JSON format for aggregation)  
🔧 **Backward compatible** intermediate file formats  
⚡ **Parallel processing** for batch jobs  
🛡️ **Robust error handling** continues on individual failures  

## Installation

### Prerequisites

External tools (must be in PATH):
```bash
# HHsuite (hhblits, hhmake, hhsearch, addss.pl)
# Foldseek
# DALI (dali.pl)
# DSSP (mkdssp)
```

### Install DPAM

```bash
# Clone repository
git clone https://github.com/your-org/dpam.git
cd dpam

# Install package
pip install -e . --break-system-packages

# Or with development dependencies
pip install -e ".[dev]" --break-system-packages
```

## Quick Start

### Single Structure

```bash
# Run full pipeline
dpam run AF-P12345 \
  --working-dir ./work \
  --data-dir /path/to/ecod_data \
  --cpus 4 \
  --resume

# Run specific step
dpam run-step AF-P12345 \
  --step HHSEARCH \
  --working-dir ./work \
  --data-dir /path/to/ecod_data \
  --cpus 4
```

### Batch Processing (Local)

```bash
# Create prefix file
cat > prefixes.txt << EOF
AF-P12345
AF-P67890
AF-Q11111
EOF

# Process batch
dpam batch prefixes.txt \
  --working-dir ./work \
  --data-dir /path/to/ecod_data \
  --cpus 4 \
  --parallel 2 \
  --resume \
  --log-dir ./logs
```

### SLURM Cluster

```bash
# Submit job array
dpam slurm-submit prefixes.txt \
  --working-dir ./work \
  --data-dir /path/to/ecod_data \
  --cpus-per-task 4 \
  --mem-per-cpu 4G \
  --time 4:00:00 \
  --partition compute \
  --array-size 100

# Check job status
squeue -u $USER

# Monitor specific job
tail -f logs/12345_0.out
```

## Pipeline Steps

| Step | Name | Description | Bottleneck |
|------|------|-------------|------------|
| 1 | PREPARE | Extract & validate sequences | |
| 2 | HHSEARCH | Sequence homology search | ⚠️ High CPU |
| 3 | FOLDSEEK | Structure similarity search | |
| 4 | FILTER_FOLDSEEK | Filter redundant hits | |
| 5 | MAP_ECOD | Map hits to ECOD domains | |
| 6 | DALI_CANDIDATES | Merge candidate list | |
| 7 | ITERATIVE_DALI | Structural alignment | ⚠️ High CPU + Parallel |
| 8 | ANALYZE_DALI | Score DALI alignments | |
| 9 | GET_SUPPORT | Integrate sequence/structure | |
| 10 | FILTER_DOMAINS | Apply quality thresholds | |
| 11 | SSE | Secondary structure (DSSP) | |
| 12 | DISORDER | Disorder prediction | |
| 13 | PARSE_DOMAINS | Final domain parsing | ⚠️ Complex |

## Input Files

Place in working directory:
```
work/
├── AF-P12345.cif (or .pdb)    # Structure file
└── AF-P12345.json             # AlphaFold confidence (PAE)
```

## Output Files

```
work/
├── AF-P12345.fa                    # Extracted sequence
├── AF-P12345.pdb                   # Standardized structure
├── AF-P12345.hhsearch              # HHsearch results
├── AF-P12345.foldseek              # Foldseek results
├── AF-P12345.map2ecod.result       # ECOD mappings
├── AF-P12345_iterativdDali_hits    # DALI alignments
├── AF-P12345_good_hits             # Analyzed DALI
├── AF-P12345_sequence.result       # Sequence support
├── AF-P12345_structure.result      # Structure support
├── AF-P12345.goodDomains           # Filtered domains
├── AF-P12345.sse                   # Secondary structure
├── AF-P12345.diso                  # Disorder regions
└── AF-P12345.finalDPAM.domains     # Final domain definitions ⭐
```

## Reference Data Structure

```
data/
├── UniRef30_2022_02/               # HHsearch database
│   └── UniRef30_2022_02.*
├── pdb70/                          # HHsearch template database
│   └── pdb70.*
├── ECOD_foldseek_DB/               # Foldseek database
│   └── ECOD_foldseek_DB.*
├── ECOD70/                         # DALI templates
│   ├── 000000003.pdb
│   └── ...
├── ECOD_length                     # Domain lengths
├── ECOD_norms                      # Normalization values
├── ECOD_pdbmap                     # PDB→ECOD mapping
├── ecod.latest.domains             # ECOD metadata
├── ecod_weights/                   # Position weights
│   └── 000000003.weight
└── ecod_domain_info/               # Domain statistics
    └── 000000003.info
```

## Configuration

### Resource Recommendations

| Pipeline Stage | CPUs | Memory | Time |
|---------------|------|--------|------|
| Steps 1-6 | 4 | 4GB | 1h |
| Step 7 (DALI) | 8-16 | 8GB | 2-3h |
| Steps 8-13 | 1-4 | 4GB | 30min |

### SLURM Best Practices

```bash
# For large batches (>1000 structures)
dpam slurm-submit prefixes.txt \
  --working-dir ./work \
  --data-dir /data/ecod \
  --cpus-per-task 8 \
  --mem-per-cpu 2G \
  --time 6:00:00 \
  --array-size 200      # Limit concurrent jobs

# Monitor progress
watch -n 30 'squeue -u $USER | grep dpam'

# Aggregate logs
cat logs/*.log | jq '. | select(.level=="ERROR")'
```

## Architecture

### Core Components

```
dpam/
├── core/           # Data models (Structure, Domain, Hit, etc.)
├── io/             # Readers, writers, parsers
├── tools/          # External tool wrappers (HHsuite, Foldseek, DALI)
├── steps/          # Pipeline step implementations
├── pipeline/       # Orchestration (runner, batch, slurm)
├── cli/            # Command-line interface
└── utils/          # Utilities (logging, ranges, amino acids)
```

### Key Design Patterns

- **Type Safety**: Full type hints, validated with mypy
- **Checkpointing**: `.dpam_state.json` tracks progress
- **Error Isolation**: Individual structure failures don't stop batch
- **Lazy Loading**: Reference data loaded once per pipeline
- **Tool Abstraction**: External tools wrapped for testing/mocking

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# With coverage
pytest --cov=dpam tests/

# Type checking
mypy dpam/
```

### Code Style

```bash
# Format code
black dpam/

# Lint
flake8 dpam/
```

### Adding New Steps

See `IMPLEMENTATION_GUIDE.md` for detailed patterns and examples.

## Troubleshooting

### Common Issues

**1. Tool not found**
```bash
# Check PATH
which hhsearch foldseek dali.pl mkdssp

# Load modules on HPC
module load hhsuite foldseek dali
```

**2. GEMMI import error**
```bash
pip install gemmi --break-system-packages
```

**3. Resume not working**
```bash
# State files are hidden
ls -la work/.*.dpam_state.json

# Manually reset
rm work/.AF-P12345.dpam_state.json
```

**4. SLURM job failures**
```bash
# Check logs
tail -100 logs/12345_0.err

# Resubmit failed
dpam batch prefixes_failed.txt ...
```

## Performance Optimization

### Bottleneck Analysis

**Step 2 (HHsearch)**: 
- CPU-bound
- Parallelize: Use `--cpus 8+`
- Database: Pre-built indices

**Step 7 (DALI)**:
- I/O-bound + CPU-bound
- Parallelize: Multiple structures × CPUs per structure
- Optimize: Local scratch space for temp files

**Step 13 (Parsing)**:
- Memory-bound for large proteins
- Optimize: Sparse matrices, chunked processing

## Citation

If you use DPAM in your research, please cite:

```
[Citation information to be added]
```

## License

[License information to be added]

## Support

- **Issues**: https://github.com/your-org/dpam/issues
- **Documentation**: https://dpam.readthedocs.io
- **Email**: support@yourdomain.com

## Changelog

### Version 2.0.0
- Complete reimplementation in modern Python 3
- Added type hints and dataclasses
- Replaced pdbx with Gemmi
- Added SLURM integration
- Implemented checkpointing
- Improved error handling
- Added structured logging
- Batch processing support
