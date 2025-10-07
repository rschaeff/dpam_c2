# Step 11 Summary: Secondary Structure Elements (SSE)

**Status:** ✅ Complete
**Implementation:** `steps/step11_sse.py`
**Lines of Code:** ~100
**Complexity:** Low

---

## Purpose

Assign secondary structure elements (SSE) using DSSP:
- Run mkdssp on PDB structure
- Identify helices and strands
- Filter by minimum length (3+ strands, 6+ helices)
- Write SSE assignments per residue

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step SSE --working-dir ./work
```

### Input
- `{prefix}.pdb` - Structure file
- `{prefix}.fa` - Sequence file (for validation)

### Output
- `{prefix}.sse` - SSE assignments per residue

### Performance
- **Time:** 5-15 seconds (depends on protein size)
- **Memory:** <100 MB

---

## Algorithm

```
1. Run mkdssp on PDB file
2. Parse DSSP output:
   - E/B → E (strand)
   - G/H/I → H (helix)
   - Other → - (coil)
3. Split by '--' (coil regions)
4. Identify SSEs:
   - Segments with 3+ E = valid strand
   - Segments with 6+ H = valid helix
5. Number SSEs sequentially
6. Write assignments
```

---

## Output Format

**File:** `{prefix}.sse`

**Format:** `resid\taa\tsse_id\tsse_type`

**Example:**
```
1	M	na	C
2	A	na	C
3	K	1	H
4	L	1	H
...
10	V	1	H
11	D	na	C
12	E	2	E
13	F	2	E
14	G	2	E
...
```

**Columns:**
1. `resid` - Residue ID
2. `aa` - Amino acid
3. `sse_id` - SSE number (or 'na' if not in SSE)
4. `sse_type` - H (helix), E (strand), C (coil)

---

## SSE Identification Criteria

### Helix
- **Minimum:** 6 consecutive H residues
- **Types:** α-helix (H), 3₁₀-helix (G), π-helix (I)

### Strand
- **Minimum:** 3 consecutive E residues
- **Types:** β-strand (E), β-bridge (B)

### Coil
- **All other residues** (not in valid SSE)
- **Type:** C

---

## Typical Statistics

### 500-Residue Protein

**SSEs identified:** 15-30 total
- Helices: 8-15
- Strands: 7-15

**Residues in SSEs:** 60-70%
**Residues in coil:** 30-40%

---

## Common Issues

### DSSP not found
**Solution:** Install mkdssp or load module: `module load dssp`

### Length mismatch
**Cause:** PDB and sequence don't match
**Fix:** Check step 1 (prepare) completed correctly

### No SSEs identified
**Cause:** All-coil protein (rare) or DSSP failed
**Check:** Review DSSP output

---

## Backward Compatibility

✅ **100% v1.0 compatible**
- DSSP parameters identical
- SSE criteria identical (3+ strands, 6+ helices)
- Output format identical
- Numbering scheme identical

---

## Quick Commands

```bash
# Run step 11
dpam run-step AF-P12345 --step SSE --working-dir ./work

# Check output
head work/AF-P12345.sse | column -t

# Count SSEs
cut -f3 work/AF-P12345.sse | grep -v "na" | sort -u | wc -l

# Count residues in SSEs
grep -v "na" work/AF-P12345.sse | wc -l

# Distribution of SSE types
cut -f4 work/AF-P12345.sse | sort | uniq -c
```

---

## Summary

Step 11 is **complete**, **fast**, and **simple**.

**Key metrics:**
- ✅ 100 lines of code
- ✅ 5-15s execution time
- ✅ Uses existing DSSP wrapper
- ✅ 100% backward compatible
- ✅ Independent step (can run standalone)
- ✅ Ready for production

**Next:** Step 12 (Disorder) - uses SSE output
