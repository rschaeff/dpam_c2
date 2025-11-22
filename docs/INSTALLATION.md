# DPAM v2.0 Installation Guide

Complete setup instructions for DPAM v2.0 on various systems.

## Quick Start

**For impatient users:**

```bash
conda env create -f environment.yml
conda activate dpam
pip install -e .
dpam --help
```

If this doesn't work, see detailed instructions below.

---

## Prerequisites

### Required Software

- **Conda/Miniconda** (Python environment management)
  - Download: https://docs.conda.io/en/latest/miniconda.html
  - Verify: `conda --version`

- **Python 3.11+**
  - Included in conda environment

- **Git** (for cloning repository)
  - Verify: `git --version`

### External Tools

DPAM requires these external bioinformatics tools:

| Tool | Purpose | Availability |
|------|---------|--------------|
| **HHsuite** | Sequence homology search | Manual install or conda |
| **Foldseek** | Structure similarity search | Included in conda env |
| **DALI** | Structural alignment | Manual install |
| **DSSP** | Secondary structure | Manual install or conda |

---

## Installation Steps

### 1. Clone Repository

```bash
# Clone DPAM repository
cd ~  # Or wherever you keep code
git clone https://github.com/your-org/dpam_c2.git
cd dpam_c2
```

### 2. Create Conda Environment

```bash
# Create environment from file (includes most dependencies)
conda env create -f environment.yml

# This will create an environment named 'dpam' with:
# - Python 3.11
# - NumPy, TensorFlow, Gemmi
# - Foldseek
# - Testing/development tools
```

**Troubleshooting:**
```bash
# If conda is slow, use mamba:
conda install -n base mamba
mamba env create -f environment.yml

# If environment already exists:
conda env remove -n dpam
conda env create -f environment.yml
```

### 3. Activate Environment

```bash
# Activate the environment
conda activate dpam

# Verify activation (should show conda env path)
which python
# Expected: /path/to/conda/envs/dpam/bin/python

# Verify Python version
python --version
# Expected: Python 3.11.x
```

**Add to ~/.bashrc for convenience:**
```bash
# Auto-activate dpam environment (optional)
echo "conda activate dpam" >> ~/.bashrc
```

### 4. Install DPAM Package

```bash
# Install in editable/development mode
pip install -e .

# Verify installation
dpam --version
dpam --help

# Verify command location
which dpam
# Expected: /path/to/conda/envs/dpam/bin/dpam
```

**If dpam command not found:**
```bash
# Ensure you're in the dpam conda environment
conda activate dpam

# Try reinstalling
pip uninstall dpam
pip install -e .

# Check if entry point was created
ls -l ~/.conda/envs/dpam/bin/dpam
```

### 5. Configure External Tools

#### HHsuite Configuration

**Option A: System installation (HGD cluster)**

```bash
# Add to ~/.bashrc
export PATH="/sw/apps/hh-suite/bin:$PATH"

# Source to apply immediately
source ~/.bashrc

# Verify
which hhblits
# Expected: /sw/apps/hh-suite/bin/hhblits
```

**Option B: Conda installation**

```bash
conda activate dpam
conda install -c bioconda hhsuite

# Verify
which hhblits
# Expected: ~/.conda/envs/dpam/bin/hhblits
```

**Option C: Manual installation**

```bash
# Download from GitHub
cd ~/src
git clone https://github.com/soedinglab/hh-suite.git
cd hh-suite
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=. ..
make -j 4
make install

# Add to PATH
export PATH="$HOME/src/hh-suite/build/bin:$PATH"
```

#### DALI Configuration

```bash
# Download DaliLite.v5
cd ~/src
mkdir -p Dali_v5
cd Dali_v5

# Download from:
wget http://ekhidna2.biocenter.helsinki.fi/downloads/dali/DaliLite.v5.tar.gz
tar -xzf DaliLite.v5.tar.gz

# Compile
cd DaliLite.v5
./configure
make

# Set environment variable (add to ~/.bashrc)
export DALI_HOME=$HOME/src/Dali_v5/DaliLite.v5
export PATH="$DALI_HOME/bin:$PATH"

# Source to apply
source ~/.bashrc

# Verify
which dali.pl
# Expected: ~/src/Dali_v5/DaliLite.v5/bin/dali.pl
```

**Note:** DPAM auto-detects DALI in these locations:
1. `$DALI_HOME/bin/dali.pl`
2. `~/src/Dali_v5/DaliLite.v5/bin/dali.pl`
3. System PATH

#### DSSP Configuration

```bash
# Option A: Use DaliLite's DSSP
# (Already configured if DALI_HOME is set)
which dsspcmbi
# Expected: ~/src/Dali_v5/DaliLite.v5/bin/dsspcmbi

# Option B: Install modern DSSP
conda install -c salilab dssp

# Verify
which mkdssp
# Expected: ~/.conda/envs/dpam/bin/mkdssp
```

### 6. Verify Complete Installation

```bash
# Check all commands are available
conda activate dpam

# DPAM itself
dpam --help                 # ✓ Should show help message
dpam-clean --help           # ✓ Cleanup utility

# External tools
which hhblits               # ✓ HHsuite
which hhmake                # ✓ HHsuite
which hhsearch              # ✓ HHsuite
which foldseek              # ✓ Foldseek
which dali.pl               # ✓ DALI
which mkdssp                # ✓ DSSP (or dsspcmbi)

# Python packages
python -c "import numpy; print('NumPy:', numpy.__version__)"
python -c "import tensorflow; print('TensorFlow:', tensorflow.__version__)"
python -c "import gemmi; print('Gemmi:', gemmi.__version__)"
```

**Create verification script:**
```bash
# Save as check_dpam_tools.sh
cat > check_dpam_tools.sh << 'EOF'
#!/bin/bash
echo "Checking DPAM installation..."

check_tool() {
    if command -v $1 &> /dev/null; then
        echo "✓ $1 found: $(which $1)"
    else
        echo "✗ $1 NOT FOUND"
    fi
}

check_tool dpam
check_tool dpam-clean
check_tool hhblits
check_tool hhmake
check_tool hhsearch
check_tool foldseek
check_tool dali.pl
check_tool mkdssp
check_tool dsspcmbi

echo ""
echo "Python packages:"
python -c "import numpy; print('✓ NumPy:', numpy.__version__)" 2>/dev/null || echo "✗ NumPy NOT FOUND"
python -c "import tensorflow; print('✓ TensorFlow:', tensorflow.__version__)" 2>/dev/null || echo "✗ TensorFlow NOT FOUND"
python -c "import gemmi; print('✓ Gemmi:', gemmi.__version__)" 2>/dev/null || echo "✗ Gemmi NOT FOUND"
EOF

chmod +x check_dpam_tools.sh
./check_dpam_tools.sh
```

---

## System-Specific Instructions

### HGD Cluster (leda.cns.utexas.edu)

```bash
# 1. Setup conda (if not already done)
source ~/.bashrc

# 2. Clone and install DPAM
cd ~/dev
git clone <repo>
cd dpam_c2
conda env create -f environment.yml
conda activate dpam
pip install -e .

# 3. Configure HHsuite (cluster-specific)
echo 'export PATH="/sw/apps/hh-suite/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 4. Configure DALI (if not installed)
# Follow DALI configuration steps above

# 5. Verify
./check_dpam_tools.sh
```

### Personal Workstation

```bash
# 1. Install Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# 2. Clone and install DPAM
cd ~/projects
git clone <repo>
cd dpam_c2
conda env create -f environment.yml
conda activate dpam
pip install -e .

# 3. Install external tools via conda
conda install -c bioconda hhsuite dssp

# 4. Install DALI manually
# Follow DALI configuration steps above

# 5. Verify
./check_dpam_tools.sh
```

---

## Reference Data Setup

DPAM requires ECOD reference databases. Download and extract:

```bash
# Create data directory
mkdir -p ~/data/dpam_reference/ecod_data
cd ~/data/dpam_reference/ecod_data

# Download ECOD data (contact DPAM maintainers for access)
# Expected structure:
# ecod_data/
# ├── UniRef30_2022_02/        # HHsearch database
# ├── pdb70/                   # HHsearch templates
# ├── ECOD_foldseek_DB/        # Foldseek database
# ├── ECOD70/                  # DALI templates (PDB files)
# ├── ECOD_length              # Domain lengths
# ├── ECOD_norms               # Normalization values
# ├── ECOD_pdbmap              # PDB→ECOD mapping
# ├── ecod.latest.domains      # ECOD metadata
# ├── ECOD_maps/               # Residue numbering maps
# ├── ecod_weights/            # Position weights
# └── ecod_domain_info/        # Domain statistics

# Verify data structure
ls -lh ~/data/dpam_reference/ecod_data/
```

---

## Testing Installation

### Basic Test

```bash
# Activate environment
conda activate dpam

# Test CLI
dpam --help
dpam run --help
dpam batch --help

# Test cleanup utility
dpam-clean --help
```

### Test with Sample Data

```bash
# Create test directory
mkdir -p ~/dpam_test
cd ~/dpam_test

# Copy sample structure (replace with actual path)
cp /path/to/sample/AF-P12345.cif .
cp /path/to/sample/AF-P12345.json .

# Run single structure (will fail at step 2 if tools not configured)
dpam run AF-P12345 \
    --working-dir . \
    --data-dir ~/data/dpam_reference/ecod_data \
    --cpus 2

# Check for errors
tail -100 AF-P12345.log
```

### Run Test Suite

```bash
cd ~/dev/dpam_c2

# Run unit tests (fast, no external tools needed)
pytest tests/unit/ -v

# Run integration tests (requires external tools)
pytest tests/integration/ -v

# Run specific test
pytest tests/integration/test_step02_hhsearch.py::TestStep02HHsearch::test_hhsearch_basic -v
```

---

## Troubleshooting

### Problem: dpam command not found

```bash
# Solution 1: Ensure conda environment is activated
conda activate dpam
which dpam  # Should show path

# Solution 2: Reinstall package
pip uninstall dpam
pip install -e .

# Solution 3: Check PATH
echo $PATH | grep -o '/conda/envs/dpam/bin'
```

### Problem: hhblits not found

```bash
# Solution 1: Add to PATH
export PATH="/sw/apps/hh-suite/bin:$PATH"
which hhblits

# Solution 2: Install via conda
conda install -c bioconda hhsuite

# Solution 3: Check module system
module avail hhsuite
module load hhsuite
```

### Problem: Import errors (gemmi, tensorflow)

```bash
# Solution: Ensure conda environment is activated
conda activate dpam
python -c "import gemmi"  # Should not error

# If still fails, reinstall package
conda install gemmi tensorflow numpy
```

### Problem: DALI not found

```bash
# Solution 1: Set DALI_HOME
export DALI_HOME=~/src/Dali_v5/DaliLite.v5
which dali.pl

# Solution 2: Add to PATH
export PATH="$HOME/src/Dali_v5/DaliLite.v5/bin:$PATH"

# Solution 3: Check DPAM auto-detection
python -c "
from dpam.tools.dali import DALITool
tool = DALITool()
print('DALI found:', tool.check_availability())
"
```

### Problem: Multiple failed processes

```bash
# Find running dpam processes
ps aux | grep "dpam batch" | grep -v grep

# Kill them
pkill -f "dpam batch"

# Or manually
kill <PID>
```

---

## Uninstallation

```bash
# Remove DPAM package
pip uninstall dpam

# Remove conda environment
conda deactivate
conda env remove -n dpam

# Remove repository (optional)
rm -rf ~/dev/dpam_c2

# Remove reference data (optional)
rm -rf ~/data/dpam_reference/ecod_data
```

---

## Next Steps

After installation:

1. **Read CLAUDE.md** for project overview and development patterns
2. **Run validation tests** to ensure everything works
3. **Process test structures** to verify pipeline
4. **Configure SLURM** if using HPC cluster
5. **Set up batch processing** for production runs

---

## Support

If installation fails after following this guide:

1. Run `./check_dpam_tools.sh` and save output
2. Check `pip list` for installed packages
3. Check `conda list` for conda packages
4. Report issue with:
   - System information (`uname -a`)
   - Conda version (`conda --version`)
   - Python version (`python --version`)
   - Error messages
   - Output from `check_dpam_tools.sh`
