# DALI Troubleshooting Guide

## Current Status

**Version**: DaliLite.v5
**Location**: `/home/rschaeff/bin/DaliLite.v5/`
**Status**: ❌ Missing dependency (libgfortran.so.3)

## Issues Found

### 1. Missing Library: libgfortran.so.3

**Error:**
```
/home/rschaeff/bin/DaliLite.v5/bin/puu: error while loading shared libraries:
libgfortran.so.3: cannot open shared object file: No such file or directory
```

**Cause**: DALI's `puu` binary was compiled against older GCC/gfortran (GCC 4.x-6.x) which provided libgfortran.so.3. Modern systems use libgfortran.so.5 (GCC 10+).

**Solutions** (in order of preference):

#### Option A: Install Compatibility Library (Recommended)

Ubuntu/Debian:
```bash
sudo apt-get install libgfortran3
```

CentOS/RHEL 7:
```bash
sudo yum install compat-gcc-34-g77
```

CentOS/RHEL 8+:
```bash
# Enable PowerTools/CRB repo
sudo dnf config-manager --set-enabled powertools
sudo dnf install libgfortran
```

#### Option B: Create Symlink (Quick but risky)

```bash
# Find current libgfortran
find /usr/lib* -name "libgfortran.so*"

# Create symlink (may cause ABI issues!)
cd /usr/lib/x86_64-linux-gnu/
sudo ln -s libgfortran.so.5 libgfortran.so.3
```

**Warning**: This may cause crashes due to ABI incompatibility between versions 3 and 5.

#### Option C: Use Docker (Safest for production)

```dockerfile
FROM ubuntu:18.04
RUN apt-get update && apt-get install -y \
    libgfortran3 \
    perl \
    wget

# Install DaliLite
RUN wget http://ekhidna2.biocenter.helsinki.fi/dali/DaliLite.v5.tar.gz && \
    tar xzf DaliLite.v5.tar.gz && \
    mv DaliLite.v5 /opt/

ENV PATH="/opt/DaliLite.v5/bin:${PATH}"
```

#### Option D: Recompile DALI from Source

```bash
# Download source
wget http://ekhidna2.biocenter.helsinki.fi/dali/src/dali-src.tar.gz
tar xzf dali-src.tar.gz
cd dali-src

# Compile with modern gfortran
make clean
make FC=gfortran

# Install to local bin
cp bin/* ~/bin/DaliLite_custom/bin/
```

### 2. Path Management Issues (✅ FIXED)

**Issue**: DALI changes working directory but code used relative paths, causing "Can't open test_run/AF-Q976I1-F1.pdb"

**Fix Applied**:
- `dpam/tools/dali.py`: Convert all paths to absolute using `.resolve()`
- `dpam/steps/step07_iterative_dali.py`: Use absolute paths throughout
- Removed unnecessary `os.chdir()` calls

**Changes:**
```python
# Before (broken):
query_pdb = working_dir / f'{prefix}.pdb'
os.chdir(output_tmp_dir)
dali.align(query_pdb, ...)  # Path now invalid!

# After (fixed):
query_pdb = (working_dir / f'{prefix}.pdb').resolve()  # Absolute
dali.align(query_pdb, ...)  # Works from any directory
```

### 3. Working Directory Chaos (✅ FIXED)

**Issue**: Multiple `os.chdir()` calls without proper tracking

**Fix Applied**:
- Removed directory changes from main loop
- Use absolute paths so directory doesn't matter
- DALI's `cwd` parameter handles execution directory

## Testing DALI Installation

### Quick Test

```bash
cd ~/dev/dpam_c2/test_run/
python3 << 'EOF'
from pathlib import Path
from dpam.tools.dali import DALI

# Simple test
dali = DALI()
print(f"DALI executable: {dali.executable}")
print(f"Available: {dali.check_availability()}")

# Test alignment
pdb1 = Path("AF-Q976I1-F1.pdb").resolve()
pdb2 = Path("/home/rschaeff_1/data/dpam_reference/ecod_data/ECOD70/000001438.pdb").resolve()
outdir = Path("test_dali").resolve()

z_score, alignments = dali.align(pdb1, pdb2, outdir)
print(f"Z-score: {z_score}")
print(f"Alignments: {len(alignments)}")
EOF
```

### Expected Output (Working):
```
DALI executable: /home/rschaeff/bin/DaliLite.v5/bin/dali.pl
Available: True
Z-score: 2.5
Alignments: 45
```

### Expected Output (Library Missing):
```
DALI executable: /home/rschaeff/bin/DaliLite.v5/bin/dali.pl
Available: True
Z-score: None
Alignments: 0
```

Check log file:
```bash
cat test_dali/log
```

## Full Step 7 Test

Once library issue is fixed:

```bash
cd ~/dev/dpam_c2

# Clean previous run
rm -rf test_run/iterativeDali_AF-Q976I1-F1
rm -f test_run/AF-Q976I1-F1.iterativeDali.done
rm -f test_run/AF-Q976I1-F1_iterativdDali_hits

# Run step 7 with debug logging
python3 << 'EOF'
from pathlib import Path
from dpam.steps.step07_iterative_dali import run_step7
from dpam.utils.logging_config import setup_logging
import logging

setup_logging(json_format=False)
logging.getLogger('steps.iterative_dali').setLevel(logging.DEBUG)
logging.getLogger('tools.dali').setLevel(logging.DEBUG)

success = run_step7(
    prefix='AF-Q976I1-F1',
    working_dir=Path('test_run'),
    data_dir=Path('/home/rschaeff_1/data/dpam_reference/ecod_data'),
    cpus=2
)

print(f"\nSuccess: {success}")
EOF

# Check output
ls -lh test_run/AF-Q976I1-F1_iterativdDali_hits
wc -l test_run/AF-Q976I1-F1_iterativdDali_hits
head -20 test_run/AF-Q976I1-F1_iterativdDali_hits
```

### Expected Results

**If working correctly:**
- Output file > 0 bytes
- Multiple hit entries (one per successful DALI alignment)
- Format: `>{edomain}_{iteration}\t{zscore}\t{n_match}\t{q_len}\t{t_len}`

**Example output:**
```
>000001438_1	12.5	85	108	108
45	12
46	13
...
>000001521_1	8.2	42	23	95
10	5
11	6
...
```

## Performance Expectations

**Test case**: AF-Q976I1-F1 (108 residues)
- Candidates from step 6: 434 ECOD domains
- Expected runtime (8 CPUs): ~30-60 minutes
- Expected hits: ~50-150 significant alignments
- Output file size: ~50-200 KB

**Bottlenecks:**
- DALI is single-threaded per domain
- I/O intensive (creates many temp files)
- Scales linearly with CPU count via multiprocessing

## Alternative: Skip DALI for Initial Testing

If DALI library cannot be fixed immediately, you can test downstream steps using mock data:

```bash
# Create mock DALI output for testing
cat > test_run/AF-Q976I1-F1_iterativdDali_hits << 'EOF'
>000001438_1	12.5	85	108	108
45	12
46	13
47	14
...
EOF

# Mark step as complete
touch test_run/AF-Q976I1-F1.iterativeDali.done

# Continue with step 8
dpam run-step AF-Q976I1-F1 --step ANALYZE_DALI --working-dir test_run --data-dir ...
```

## References

- DALI website: http://ekhidna2.biocenter.helsinki.fi/dali/
- DaliLite documentation: http://ekhidna2.biocenter.helsinki.fi/dali/README.v5.html
- Fortran library compatibility: https://gcc.gnu.org/wiki/GFortranBinariesCompatibility

## Contact

If issues persist:
1. Check DALI log files in `{working_dir}/test_dali/log`
2. Verify ECOD70 templates exist: `ls -lh ~/data/dpam_reference/ecod_data/ECOD70/ | head`
3. Test with single domain instead of full batch
4. Consider using Docker environment with correct dependencies
