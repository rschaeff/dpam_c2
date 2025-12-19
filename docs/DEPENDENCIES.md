# DPAM v2.0 Dependencies

This document enumerates all external dependencies for DPAM v2.0 and their locations on the current filesystem.

## External Tool Dependencies

### 1. HHsuite (v3.3.0)

**Location:** `/sw/apps/hh-suite/`

**Required executables:**
- `hhblits`: `/sw/apps/hh-suite/bin/hhblits`
- `hhmake`: `/sw/apps/hh-suite/bin/hhmake`
- `hhsearch`: `/sw/apps/hh-suite/bin/hhsearch`

**Required scripts:**
- `addss.pl`: `/sw/apps/hh-suite/scripts/addss.pl`

**Usage:**
```bash
# Add to PATH
export PATH="/sw/apps/hh-suite/bin:$PATH"

# Or use module system
module load hh-suite
```

**Citation:**
Steinegger M, Meier M, Mirdita M, Vöhringer H, Haunsberger SJ, and Söding J (2019) HH-suite3 for fast remote homology detection and deep protein annotation.

---

### 2. Foldseek (v10.941cd33)

**Location:** Installed in `dpam` conda environment

**Executable:** Available in conda environment PATH when activated

**Usage:**
```bash
conda activate dpam
foldseek easy-search <query> <target> <output> <tmpdir>
```

**Citation:**
van Kempen M, Kim SS, Tumescheit C, Mirdita M, Lee J, Gilchrist CLM, Söding J, and Steinegger M (2023) Fast and accurate protein structure search with Foldseek. Nature Biotechnology, doi:10.1038/s41587-023-01773-0

---

### 3. DALI (DaliLite v5)

**Location:** `~/bin/DaliLite.v5/`

**Main executable:**
- `dali.pl`: `~/bin/DaliLite.v5/bin/dali.pl`

**Supporting executables:**
- `import.pl`: `~/bin/DaliLite.v5/bin/import.pl`
- Binary tools in: `~/bin/DaliLite.v5/bin/`

**Usage:**
```bash
# Add to PATH
export PATH="$HOME/bin/DaliLite.v5/bin:$PATH"

# Pairwise alignment
~/bin/DaliLite.v5/bin/dali.pl \
  --pdbfile1 query.pdb \
  --pdbfile2 template.pdb \
  --dat1 ./DAT/ \
  --dat2 ./DAT/ \
  --outfmt summary,alignments
```

**Citation:**
Holm L (2019) Benchmarking fold detection by DaliLite.v5 (unpublished)

**Note:** This is DaliLite v5 with modern `dali.pl` interface. DO NOT confuse with older DaliLite v3.3 at `~/bin/DaliLite_3.3/` which uses incompatible command-line syntax.

---

### 4. DSSP (mkdssp v4.4.11)

**Location:** Installed in `dpam` conda environment

**Executable:** `mkdssp` available in conda environment PATH when activated

**Usage:**
```bash
conda activate dpam
mkdssp -i input.pdb -o output.dssp
```

**Citation:**
Kabsch W, Sander C (1983) Dictionary of protein secondary structure: pattern recognition of hydrogen-bonded and geometrical features. Biopolymers 22:2577-2637

---

## Python Dependencies

### Core Requirements

Install via:
```bash
pip install -e . --break-system-packages
```

**Required packages (from `setup.py`):**
- `numpy>=1.20.0` (installed: v1.26.4)
- `gemmi>=0.6.0` (installed: v0.7.1)

**Development packages (optional):**
```bash
pip install -e ".[dev]" --break-system-packages
```

Includes:
- `pytest>=6.0.0`
- `pytest-cov>=2.0.0`
- `black>=21.0`
- `mypy>=0.900`
- `flake8>=3.9.0`

---

## Reference Data

### Location

**Base directory:** `/home/rschaeff_1/data/dpam_reference/ecod_data/`

### Required Files and Directories

**ECOD domain databases:**
- `ecod.latest.domains` - ECOD domain metadata (183 MB)
- `ECOD_length` - Domain length information (1.3 MB)
- `ECOD_norms` - Normalization values for scoring (938 KB)
- `ECOD_pdbmap` - PDB to ECOD domain mapping (1.5 MB)

**Foldseek database:**
- `ECOD_foldseek_DB*` - Foldseek searchable database files
  - Main database: `ECOD_foldseek_DB`
  - C-alpha coordinates: `ECOD_foldseek_DB_ca*`
  - Secondary structure: `ECOD_foldseek_DB_ss*`
  - Headers: `ECOD_foldseek_DB_h*`
  - Index/lookup files: `*.index`, `*.lookup`, `*.source`

**PDB structure files:**
- `ECOD_pdbs/` - Directory containing ~100k ECOD domain PDB files
  - Format: `{ecod_id}.pdb` (e.g., `000000400.pdb`)
  - Also contains pre-computed DSSP files: `{ecod_id}.dssp`

**Position-specific data:**
- `posi_weights/` - Position-specific weights for domains
- `ecod_internal/` - Internal ECOD data files
- `ECOD_maps/` - Additional mapping files

**Machine learning models (optional):**
- `domass_epo29.*` - Domain assignment model files

**Usage in DPAM:**
```bash
dpam run AF-P12345 \
  --working-dir ./work \
  --data-dir /home/rschaeff_1/data/dpam_reference/ecod_data \
  --cpus 4
```

---

## HHsearch Databases (Not Yet Verified)

According to documentation, these databases are also required but not yet verified on this filesystem:

**Expected locations:**
- `UniRef30_2022_02/` - HHblits database for sequence search
- `pdb70/` - HHsearch template database

**Status:** ⚠️ Not verified - may need to be set up or located

---

## Conda Environment Setup

**Environment name:** `dpam`

**Activation:**
```bash
source ~/.bashrc
conda activate dpam
```

**Contains:**
- Python 3.x
- foldseek v10.941cd33
- mkdssp v4.4.11
- numpy v1.26.4
- gemmi v0.7.1
- Other Python packages via pip install

---

## PATH Configuration

For full functionality, ensure these directories are in your PATH:

```bash
# Add to ~/.bashrc or session
export PATH="/sw/apps/hh-suite/bin:$PATH"
export PATH="$HOME/bin/DaliLite.v5/bin:$PATH"

# Or use with conda activation
source ~/.bashrc
conda activate dpam
```

---

## Verification Commands

Test all dependencies:

```bash
# Activate environment
source ~/.bashrc
conda activate dpam

# Test HHsuite
/sw/apps/hh-suite/bin/hhblits -h
/sw/apps/hh-suite/bin/hhmake -h
/sw/apps/hh-suite/bin/hhsearch -h

# Test Foldseek
foldseek --help

# Test DALI
~/bin/DaliLite.v5/bin/dali.pl --help

# Test DSSP
mkdssp --version

# Test Python packages
python -c "import numpy, gemmi; print('OK')"

# Test reference data
ls /home/rschaeff_1/data/dpam_reference/ecod_data/ecod.latest.domains
```

---

## Notes

- All critical dependencies are currently satisfied on this system
- HHsuite tools require explicit PATH configuration or module loading
- DaliLite v5 has a different interface than v3.3 (use v5)
- Reference data is ~4.3 GB total
- DPAM wrapper classes in `dpam/tools/` handle tool invocation
