# Step 20 Summary: Extract Domain PDB Files

**Status:** Complete
**Implementation:** `steps/step20_extract_domains.py`
**Lines of Code:** ~140
**Complexity:** Low

---

## Purpose

Extract individual PDB files for domains involved in merge candidates from Step 19.
Creates separate structure files needed for structural connectivity analysis in Step 21.

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step EXTRACT_DOMAINS --working-dir ./work
```

### Input
- `{prefix}.step19_merge_candidates` - Merge candidate pairs
- `{prefix}.pdb` - Full structure file

### Output
- `step20/{prefix}_{domain}.pdb` - Individual PDB files per domain

### Performance
- **Time:** <1 second (typical)
- **Memory:** <50 MB

---

## Algorithm

```
1. Read merge candidates from step 19
2. Collect unique domains from all pairs:
   - Parse domain1, range1, domain2, range2
   - Track seen domains to avoid duplicates
3. For each unique domain:
   a. Parse residue range to get residue IDs
   b. Read input PDB file
   c. Extract ATOM lines matching residue IDs
   d. Write to step20/{prefix}_{domain}.pdb
4. Create step20/ directory if needed
```

---

## Input Format

**File:** `{prefix}.step19_merge_candidates`

**Format:** Tab-delimited, 4+ columns
```
domain1<TAB>range1<TAB>domain2<TAB>range2[<TAB>...]
```

**Example:**
```
D1	10-50	D2	55-100
D2	55-100	D3	110-150
```

---

## Output Format

**Directory:** `step20/`

**Files:** `{prefix}_{domain}.pdb`

Standard PDB format containing only ATOM lines for domain residues.

**Example filename:** `AF-P12345_D1.pdb`

---

## Key Implementation Details

### PDB Parsing
- Extracts ATOM lines only (ignores HETATM, TER, etc.)
- Residue ID parsed from columns 23-26 (0-indexed: 22:26)
- Handles malformed lines gracefully (skip with try/except)

### Deduplication
- Uses `seen_domains` set to track processed domains
- Each domain extracted only once, even if in multiple pairs

### Range Parsing
- Uses `parse_range()` utility for range string conversion
- Example: "10-50,60-80" -> {10,11,...,50,60,61,...,80}

---

## Typical Statistics

### 500-Residue Protein
- **Merge candidates:** 5-20 pairs
- **Unique domains:** 8-15
- **PDB files created:** 8-15
- **File sizes:** 10-100 KB each

---

## Common Issues

### No merge candidates found
**Cause:** Step 19 produced no merge candidates (normal for simple proteins)
**Result:** Step completes successfully with no output files

### Structure file not found
**Cause:** `{prefix}.pdb` missing
**Fix:** Ensure Step 1 (prepare) completed successfully

### Malformed PDB lines skipped
**Cause:** Non-standard PDB formatting
**Result:** Lines silently skipped (logged at debug level)

---

## Backward Compatibility

100% v1.0 compatible
- PDB extraction logic identical
- Output directory structure matches
- File naming convention matches

---

## Quick Commands

```bash
# Run step 20
dpam run-step AF-P12345 --step EXTRACT_DOMAINS --working-dir ./work

# Check output
ls -la work/step20/

# Count extracted domains
ls work/step20/*.pdb | wc -l

# Check domain size
wc -l work/step20/AF-P12345_D1.pdb
```

---

## Summary

Step 20 is **complete**, **fast**, and **simple**.

**Key metrics:**
- 140 lines of code
- <1s execution time
- Creates individual domain PDB files
- Required for Step 21 structural comparison
- Gracefully handles no merge candidates
