# Step 1: Structure Preparation - Quick Reference

## Purpose

Extract sequences and create standardized PDB files from AlphaFold structure files (CIF or PDB format). Validates sequence integrity and prepares inputs for downstream pipeline steps.

---

## Quick Reference

**Command:**
```bash
dpam run-step PREFIX --step PREPARE --working-dir ./work
```

**Input Files:**
```
{prefix}.cif     # AlphaFold CIF structure (preferred)
  OR
{prefix}.pdb     # Alternative PDB format
```

**Output Files:**
```
{prefix}.fa      # FASTA sequence file
{prefix}.pdb     # Standardized PDB file (if input was CIF)
```

---

## Algorithm

### Phase 1: Sequence Extraction

1. Check if FASTA file already exists (skip if present)
2. If CIF input:
   - Extract sequence from CIF using Gemmi library
   - Write FASTA with prefix as header
3. If PDB input:
   - Try pdb2fasta.pl from HH-suite (external tool)
   - Fallback: Use Gemmi to read PDB and extract sequence
   - Write FASTA with prefix as header

### Phase 2: Structure Standardization

1. Load reference sequence from FASTA file
2. If CIF input:
   - Read structure using Gemmi
   - Validate sequence matches reference (handle gaps)
   - Write standardized PDB file (ATOM records only)
   - Truncate coordinates to standard precision
3. If PDB input:
   - Read and validate structure
   - Verify sequence matches reference
   - Keep existing PDB (already in correct format)

---

## Key Functions

```python
def extract_sequence(prefix: str, working_dir: Path) -> bool
    """Extract sequence from structure file to FASTA."""

def standardize_structure(prefix: str, working_dir: Path) -> bool
    """Create standardized PDB with validation."""

def run_step1(prefix: str, working_dir: Path, path_resolver=None) -> bool
    """Main entry point - runs both phases.
    path_resolver: Optional PathResolver for sharded output layout.
    """
```

---

## Output Format

### FASTA File ({prefix}.fa)
```
>{prefix}
MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFP...
```

### PDB File ({prefix}.pdb)
Standard PDB format with:
- ATOM records only (no HETATM, no header records)
- Chain ID: A
- Coordinates truncated to 3 decimal places
- B-factor column contains pLDDT values (0-100)

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `StructurePreparationError: No structure file found` | Missing .cif and .pdb | Ensure structure file in working directory |
| `StructurePreparationError: CIF extraction failed` | Invalid CIF format | Check CIF file integrity |
| `StructurePreparationError: Sequence mismatch` | Structure/sequence disagreement | Verify correct structure file |

---

## Dependencies

**Python Libraries:**
- `gemmi` - Structure parsing and coordinate extraction

**External Tools (Optional):**
- `pdb2fasta.pl` - HH-suite script for PDB sequence extraction

---

## Performance

| Metric | Typical Value |
|--------|---------------|
| Runtime | < 5 seconds |
| Memory | < 100 MB |
| Disk I/O | Minimal |

---

## Backward Compatibility

Matches v1.0 behavior from:
- `step1_get_AFDB_seqs.py` - Sequence extraction
- `step1_get_AFDB_pdbs.py` - Structure standardization

Output format identical to v1.0 for downstream compatibility.
