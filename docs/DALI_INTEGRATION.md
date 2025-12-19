# DaliLite.v5 Integration

DPAM v2.0 integrates with DaliLite.v5 for structural alignment (DALI) and secondary structure assignment (DSSP). This document describes the integration and configuration.

## Overview

The DPAM toolchain now automatically detects and uses DaliLite.v5 binaries:
- **dali.pl**: Structural alignment tool
- **dsspcmbi**: Secondary structure assignment (DSSP implementation)

## Installation

### Standard Location

Install DaliLite.v5 at the standard location:
```bash
mkdir -p ~/src/Dali_v5
cd ~/src/Dali_v5
# ... extract/install DaliLite.v5 ...
cd DaliLite.v5/bin
make  # Compile all binaries
```

This creates binaries in `~/src/Dali_v5/DaliLite.v5/bin/`:
- `dali.pl` - Main DALI script
- `dsspcmbi` - DSSP implementation
- `serialcompare` - Comparison engine
- Other support binaries

### Custom Location

If installed elsewhere, set the `DALI_HOME` environment variable:
```bash
export DALI_HOME=/path/to/DaliLite.v5
```

Add to your `.bashrc` or `.bash_profile` for persistence.

## Tool Detection

### DALI (dali.pl)

Search order:
1. `$DALI_HOME/bin/dali.pl` (if DALI_HOME set)
2. `~/src/Dali_v5/DaliLite.v5/bin/dali.pl` (standard location)
3. `dali.pl` in system PATH

### DSSP

Search order (prefers DaliLite version):
1. `$DALI_HOME/bin/dsspcmbi` (if DALI_HOME set)
2. `~/src/Dali_v5/DaliLite.v5/bin/dsspcmbi` (standard location)
3. `mkdssp` in system PATH (modern version)
4. `dsspcmbi` in system PATH

## Implementation Details

### DALI Wrapper (`dpam/tools/dali.py`)

The DALI wrapper (`dpam.tools.dali.DALI` class):
- Automatically finds `dali.pl` using the search order above
- Converts PDB file paths to absolute paths (DALI changes directories internally)
- Handles alignment output parsing from `mol*.txt` files
- Supports iterative DALI for domain detection

**Key methods:**
- `align(pdb1, pdb2, output_dir, ...)`: Run pairwise alignment
- `_parse_dali_output(output_dir)`: Parse Z-scores and alignments

### DSSP Wrapper (`dpam/tools/dssp.py`)

The DSSP wrapper (`dpam.tools.dssp.DSSP` class):
- Supports both `dsspcmbi` (DaliLite) and `mkdssp` (modern)
- Auto-detects variant and adjusts command-line interface
- Stores variant type in `self.variant` attribute

**Command differences:**
- `dsspcmbi`: `dsspcmbi -c PDB_File DSSP_File`
- `mkdssp`: `mkdssp --output-format dssp PDB_File DSSP_File`

**Key methods:**
- `run(pdb_file, output_file, ...)`: Run DSSP
- `run_and_parse(pdb_file, sequence, ...)`: Run and parse results

## Testing

### Quick Test

Verify tool detection:
```bash
python test_dali_integration.py
```

Expected output:
```
DALI executable: /home/USER/src/Dali_v5/DaliLite.v5/bin/dali.pl
✓ DALI initialized successfully

DSSP executable: /home/USER/src/Dali_v5/DaliLite.v5/bin/dsspcmbi
DSSP variant: dsspcmbi
✓ DSSP initialized successfully
```

### Functionality Test

Test with sample PDB files:
```bash
python test_dali_functionality.py
```

This tests:
- DSSP secondary structure assignment
- DALI structural alignment
- Output file parsing

## Usage in Pipeline

The DPAM pipeline automatically uses these tools in various steps:

### Step 7 (Iterative DALI)
```python
from dpam.tools.dali import run_iterative_dali

hits = run_iterative_dali(
    query_pdb=query_pdb,
    template_pdb=template_pdb,
    template_ecod=ecod_id,
    data_dir=data_dir,
    output_dir=output_dir
)
```

### Step 11 (SSE)
```python
from dpam.tools.dssp import DSSP

dssp = DSSP()
sse_dict = dssp.run_and_parse(
    pdb_file=structure_file,
    sequence=protein_sequence,
    working_dir=working_dir
)
```

## Troubleshooting

### DALI not found

```
RuntimeError: dali.pl not found in PATH
```

**Solutions:**
1. Install DaliLite.v5 at `~/src/Dali_v5/DaliLite.v5/`
2. Set `DALI_HOME` environment variable
3. Add `dali.pl` to system PATH

### DSSP not found

```
RuntimeError: mkdssp not found in PATH
```

**Solutions:**
1. Install DaliLite.v5 (includes `dsspcmbi`)
2. Install modern `mkdssp` via conda: `conda install dssp`
3. Set `DALI_HOME` or add to PATH

### dsspcmbi fails on PDB file

Check PDB file format - dsspcmbi requires classic PDB format, not mmCIF:
```bash
# Convert CIF to PDB if needed
gemmi convert input.cif output.pdb
```

### DALI gives Z-score 0.0

This is expected for:
- Very small proteins (< 20 residues)
- Proteins with no structural similarity
- Proteins with different folds

Check the DALI output files in the output directory for detailed results.

## Performance Notes

### DALI
- Step 7 (Iterative DALI) is I/O + CPU intensive
- Uses multiprocessing for parallel domain comparisons
- Typical runtime: 1-3 hours for 400 domains with 8 CPUs
- Each iteration runs structural alignment and removes matched regions

### DSSP
- Fast: typically < 1 second per structure
- dsspcmbi is faster than mkdssp for small proteins
- mkdssp has better support for modern PDB/mmCIF formats

## References

- DaliLite.v5 documentation: `~/src/Dali_v5/DaliLite.v5/MANUAL.html`
- DSSP paper: Kabsch & Sander, Biopolymers 22 (1983) 2577-2637
- DALI paper: Holm & Sander, Science 273 (1996) 595-602
