# Gemmi Python API Reference

**Version:** gemmi v0.7.1 (installed in dpam conda environment)

## ⚠️ Important Note
Gemmi documentation often mixes C++ and Python APIs. This document provides the **correct Python API** as verified in the actual environment.

## Hierarchy

```
Structure (gemmi.Structure)
  ├─> Model (gemmi.Model) - accessed via structure[index]
  │     ├─> Chain (gemmi.Chain) - accessed via model[index]
  │     │     ├─> Residue (gemmi.Residue) - accessed via chain iteration
  │     │     │     └─> Atom (gemmi.Atom) - accessed via residue iteration
```

## Reading Structures

```python
import gemmi

# Read structure from file
structure = gemmi.read_structure('file.pdb')   # PDB format
structure = gemmi.read_structure('file.cif')   # mmCIF format

# Structure object does NOT have 'chains' attribute!
# Instead, access via models:
```

## Accessing Structure Components

### Models
```python
# Get number of models
n_models = len(structure)

# Get first model
model = structure[0]

# Iterate over all models
for model in structure:
    print(f"Model: {model.name}")
```

### Chains
```python
# Get number of chains in model
n_chains = len(model)

# Get first chain
chain = model[0]

# Get chain by name
chain = model['A']

# Iterate over chains
for chain in model:
    print(f"Chain: {chain.name}")
```

### Residues
```python
# Iterate over residues in chain
for residue in chain:
    print(f"{residue.name} {residue.seqid.num}")

# Convert to list
residues = list(chain)

# Get residue properties
res = residues[0]
res.name        # Three-letter code (e.g., 'ALA')
res.seqid.num   # Sequence ID number
```

### Atoms
```python
# Iterate over atoms in residue
for atom in residue:
    print(f"{atom.name} {atom.pos}")

# Atom properties
atom.name       # Atom name (e.g., 'CA')
atom.element    # Element (e.g., gemmi.Element('C'))
atom.pos        # Position (gemmi.Position)
atom.b_iso      # B-factor
atom.occ        # Occupancy
```

## Sequence Extraction

### From PDB/CIF Structure
```python
import gemmi

structure = gemmi.read_structure('file.pdb')
model = structure[0]
chain = model[0]

# Extract sequence from chain
sequence = ''.join([
    gemmi.find_tabulated_residue(r.name).one_letter_code
    for r in chain
])

# Example output:
# 'MLGMEKYFINEDWSPLKVFINRPDGFRVIEEISYKPATEWK...'
```

### Handling Multiple Chains
```python
sequences = {}
for chain in model:
    seq = ''.join([
        gemmi.find_tabulated_residue(r.name).one_letter_code
        for r in chain
    ])
    sequences[chain.name] = seq
```

## Common Patterns for DPAM

### Read PDB and Extract Sequence
```python
def extract_sequence_from_pdb(pdb_file):
    """Extract sequence from first chain of first model."""
    structure = gemmi.read_structure(str(pdb_file))
    model = structure[0]
    chain = model[0]

    sequence = ''.join([
        gemmi.find_tabulated_residue(r.name).one_letter_code
        for r in chain
    ])

    return sequence
```

### Read CIF and Extract Sequence
```python
def extract_sequence_from_cif(cif_file, chain_id='A'):
    """Extract sequence from specific chain."""
    structure = gemmi.read_structure(str(cif_file))
    model = structure[0]

    # Find specific chain
    chain = model[chain_id]

    sequence = ''.join([
        gemmi.find_tabulated_residue(r.name).one_letter_code
        for r in chain
    ])

    return sequence
```

### Write PDB
```python
def write_pdb(structure, output_file):
    """Write structure to PDB file."""
    structure.write_minimal_pdb(str(output_file))
```

## ❌ Common Mistakes (What NOT to Do)

### WRONG: Accessing 'chains' attribute
```python
# This DOES NOT work in Python API
structure.chains  # AttributeError: 'Structure' object has no attribute 'chains'
```

### CORRECT: Access via model indexing
```python
# This is the correct way
model = structure[0]
chain = model[0]
```

### WRONG: Direct chain iteration on structure
```python
# This DOES NOT work
for chain in structure.chains:  # AttributeError
    pass
```

### CORRECT: Iterate through models first
```python
# This is the correct way
for model in structure:
    for chain in model:
        print(chain.name)
```

## Residue Name Conversion

```python
import gemmi

# Three-letter to one-letter code
three_letter = 'ALA'
one_letter = gemmi.find_tabulated_residue(three_letter).one_letter_code  # 'A'

# One-letter to three-letter code
one_letter = 'A'
three_letter = gemmi.find_tabulated_residue(one_letter).name  # 'ALA'

# Check if residue is standard
residue_info = gemmi.find_tabulated_residue('ALA')
is_standard = residue_info.is_amino_acid()  # True
```

## Structure Properties

```python
structure.name              # Structure name
structure.resolution        # Resolution (if available)
structure.cell             # Unit cell
structure.spacegroup_hm    # Space group
structure.entities         # Entity information
```

## Tested and Verified Examples

### Example 1: Extract sequence from AF-Q976I1-F1.pdb
```python
import gemmi

structure = gemmi.read_structure('AF-Q976I1-F1.pdb')
model = structure[0]
chain = model[0]
sequence = ''.join([gemmi.find_tabulated_residue(r.name).one_letter_code for r in chain])

print(f"Chain: {chain.name}")
print(f"Length: {len(sequence)}")
print(f"Sequence: {sequence}")

# Output:
# Chain: A
# Length: 363
# Sequence: MLGMEKYFINEDWSPLKVFINRPDGFRVIEEISYKPATEWK...
```

## Quick Reference Card

| Task | Code |
|------|------|
| Read structure | `structure = gemmi.read_structure(file)` |
| Get model | `model = structure[0]` |
| Get chain | `chain = model[0]` or `chain = model['A']` |
| Get residues | `for res in chain:` |
| Extract sequence | `''.join([gemmi.find_tabulated_residue(r.name).one_letter_code for r in chain])` |
| Write PDB | `structure.write_minimal_pdb(file)` |

## Version Information

This document is based on gemmi v0.7.1 as installed in the dpam conda environment (October 2025).

## See Also

- Official gemmi documentation: https://gemmi.readthedocs.io/
- **Note:** Official docs mix C++ and Python - always test Python code!
