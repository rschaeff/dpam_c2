# Test Fixtures

This directory contains minimal test data for DPAM testing.

## Required Files

For integration tests, you need:

- `test_structure.pdb` - AlphaFold structure
- `test_structure.cif` - Alternative CIF format (optional)
- `test_structure.fa` - FASTA sequence
- `test_structure.json` - AlphaFold PAE matrix

## Download Test Data

### Option 1: Use AlphaFold Database Structure

Download a small, well-characterized protein from AlphaFold DB:

```bash
# Example: Download AF-P00000-F1 (or any small protein ~100-200 residues)
UNIPROT_ID="P62988"  # Ubiquitin (76 residues - perfect test case)
AF_ID="AF-${UNIPROT_ID}-F1"

# Download PDB
wget "https://alphafold.ebi.ac.uk/files/${AF_ID}-model_v4.pdb" -O test_structure.pdb

# Download CIF (optional)
wget "https://alphafold.ebi.ac.uk/files/${AF_ID}-model_v4.cif" -O test_structure.cif

# Download PAE JSON
wget "https://alphafold.ebi.ac.uk/files/${AF_ID}-predicted_aligned_error_v4.json" -O test_structure.json

# Extract FASTA from PDB
grep "^ATOM" test_structure.pdb | awk '{print $4$5}' | sort -u | \
  awk 'BEGIN{print ">test_structure"} {printf "%s", $1} END{print ""}' > test_structure.fa
```

### Option 2: Create Minimal Mock Data

For unit tests only, you can create minimal mock files:

```python
# See scripts/create_test_fixtures.py
python scripts/create_test_fixtures.py
```

## Test Structure Recommendations

**Good test proteins:**
- **Ubiquitin (P62988)**: 76 residues, single domain, well-studied
- **Lysozyme (P00698)**: 147 residues, single domain, high quality
- **Myoglobin (P02144)**: 154 residues, single domain, all-alpha

**Avoid:**
- Very large proteins (>500 residues) - too slow for tests
- Multi-domain proteins - complex for minimal tests
- Membrane proteins - often low quality predictions

## Directory Structure

```
fixtures/
├── README.md                  # This file
├── test_structure.pdb        # Main test structure
├── test_structure.cif        # Alternative format (optional)
├── test_structure.fa         # Sequence
└── test_structure.json       # PAE matrix
```

## Validation

After downloading, verify files:

```bash
# Check PDB has ATOM records
grep -c "^ATOM" test_structure.pdb

# Check FASTA format
head -2 test_structure.fa

# Check JSON is valid
python -m json.tool test_structure.json > /dev/null && echo "JSON valid"

# Check file sizes
ls -lh test_structure.*
```

Expected sizes (for ~100 residue protein):
- PDB: ~50-100 KB
- CIF: ~100-200 KB
- FASTA: <1 KB
- JSON: ~50-100 KB
