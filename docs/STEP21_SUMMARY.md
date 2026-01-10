# Step 21 Summary: Compare Domain Connectivity

**Status:** Complete
**Implementation:** `steps/step21_compare_domains.py`
**Lines of Code:** ~280
**Complexity:** Medium

---

## Purpose

Determine if merge candidate domain pairs are connected (sequence or structure).
Two domains should merge only if they are either sequence-connected or structure-connected.

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step COMPARE_DOMAINS --working-dir ./work
```

### Input
- `{prefix}.step19_merge_candidates` - Merge candidate pairs
- `{prefix}.step13_domains` - All parsed domains (for structured residues)
- `step20/{prefix}_{domain}.pdb` - Domain PDB files

### Output
- `{prefix}.step21_comparisons` - Judgment for each pair (0/1/2)

### Performance
- **Time:** 1-10 seconds (depends on domain count)
- **Memory:** <100 MB

---

## Connectivity Types

| Code | Type | Meaning | Criteria |
|------|------|---------|----------|
| 0 | Not connected | Reject merge | Neither test passed |
| 1 | Sequence-connected | Accept merge | <=5 structured residues apart |
| 2 | Structure-connected | Accept merge | >=9 residue pairs at <=8A distance |

---

## Algorithm

```
1. Load all structured residues from step13_domains
2. For each merge pair:
   a. Parse residue ranges for both domains
   b. TEST 1: Check sequence distance
      - Map residues to indices in structured region
      - If any pair within 5 positions: judgment = 1 (accept)
   c. If not sequence-connected, TEST 2: Check structural interface
      - Load coordinates from domain PDB files
      - Count residue pairs with min inter-atomic distance <= 8A
      - If >= 9 contacts: judgment = 2 (accept)
      - Otherwise: judgment = 0 (reject)
3. Write results with judgments
```

---

## Sequence Distance Test

### Parameters
- **Distance threshold:** 5 positions in structured region

### Logic
```python
# Map residues to indices in ordered structured residue list
indices_a = [resid_to_index[res] for res in domain_a_residues]
indices_b = [resid_to_index[res] for res in domain_b_residues]

# Check if any pair is within 5 positions
for idx_a in indices_a:
    for idx_b in indices_b:
        if abs(idx_a - idx_b) <= 5:
            return True  # Sequence-connected
```

---

## Structure Distance Test

### Parameters
- **Distance threshold:** 8.0 Angstroms
- **Contact threshold:** 9 residue pairs

### Logic
```python
# For each residue pair across domains
for res_a in domain_a:
    for res_b in domain_b:
        # Find minimum distance between any atoms
        min_dist = min(distance(atom_a, atom_b)
                       for atom_a in res_a.atoms
                       for atom_b in res_b.atoms)
        if min_dist <= 8.0:
            interface_count += 1

# Accept if 9+ contacts
if interface_count >= 9:
    return True  # Structure-connected
```

---

## Output Format

**File:** `{prefix}.step21_comparisons`

**Header:**
```
# protein	domain1	domain2	judgment	range1	range2
```

**Format:** Tab-delimited
```
{prefix}<TAB>{domain1}<TAB>{domain2}<TAB>{judgment}<TAB>{range1}<TAB>{range2}
```

**Example:**
```
# protein	domain1	domain2	judgment	range1	range2
AF-P12345	D1	D2	1	10-50	55-100
AF-P12345	D2	D3	2	55-100	110-150
AF-P12345	D1	D3	0	10-50	110-150
```

---

## Key Functions

### `get_sequence_distance(resids_a, resids_b, structured_resids)`
Check if domains are connected in sequence space.

### `load_atom_coordinates(pdb_file)`
Load all atom coordinates from PDB file.
Returns dict mapping residue ID to list of [x,y,z] coordinates.

### `get_structure_distance(pdb1, pdb2, resids_a, resids_b)`
Count residue pairs with inter-atomic distance <= 8A.

---

## Typical Statistics

### 500-Residue Protein
- **Merge pairs tested:** 5-20
- **Sequence-connected:** 30-50%
- **Structure-connected:** 10-30%
- **Rejected:** 30-50%

---

## Common Issues

### No merge candidates
**Cause:** Step 19 produced no candidates
**Result:** Step completes successfully with empty output

### PDB files missing
**Cause:** Step 20 not run or failed
**Fix:** Re-run Step 20

### Low acceptance rate
**Cause:** Domains are genuinely disconnected
**Result:** Normal - prevents incorrect merges

---

## Backward Compatibility

100% v1.0 compatible
- Sequence distance threshold: 5 (exact)
- Structure distance threshold: 8.0A (exact)
- Contact threshold: 9 pairs (exact)
- Output format matches

---

## Quick Commands

```bash
# Run step 21
dpam run-step AF-P12345 --step COMPARE_DOMAINS --working-dir ./work

# Check results
cat work/AF-P12345.step21_comparisons

# Count by judgment type
cut -f4 work/AF-P12345.step21_comparisons | grep -v "^#" | sort | uniq -c

# Show only accepted pairs
grep -E "\t[12]\t" work/AF-P12345.step21_comparisons
```

---

## Summary

Step 21 is **complete** and determines domain connectivity.

**Key metrics:**
- 280 lines of code
- 1-10s execution time
- Two connectivity tests (sequence, structure)
- Clear thresholds: 5 positions, 8A distance, 9 contacts
- Outputs judgment codes (0/1/2) for Step 22
