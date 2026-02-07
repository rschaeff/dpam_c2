# Step 12 Summary: Disorder Prediction

**Status:** ✅ Complete
**Implementation:** `steps/step12_disorder.py`
**Lines of Code:** ~340
**Complexity:** Medium

---

## Purpose

Predict disordered regions based on:
- **SSE assignments** (structured vs unstructured)
- **PAE matrix** (inter-SSE contacts)
- **Good domains** (annotated regions)

Uses sliding 10-residue window to find regions with:
- Low inter-SSE contacts (≤ 30)
- Few good domain residues (≤ 5)

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step DISORDER --working-dir ./work
```

### Input
- `{prefix}.sse` - SSE assignments from step 11
- `{prefix}.json` - AlphaFold PAE matrix
- `{prefix}.goodDomains` - Good domains from step 10 (optional)

### Output
- `{prefix}.diso` - Disordered residue list

### Performance
- **Time:** 5-20 seconds (depends on protein size)
- **Memory:** <500 MB (for PAE matrix)

---

## Algorithm

```
1. Load SSE assignments
   - Track which residues are in SSEs

2. Load good domain residues
   - Track annotated regions

3. Load PAE matrix
   - Parse AlphaFold confidence scores

4. Calculate inter-SSE contacts
   - Sequence separation >= 10
   - PAE < 12 (confident contact)
   - Between different SSEs
   - Contacts counted bidirectionally

5. Sliding window (10 residues)
   For each window:
   - Count total inter-SSE contacts
   - Count good domain residues
   - If contacts <= 30 AND hit_res <= 5:
     - Mark all 10 residues as disordered

6. Write disordered residues
```

---

## Contact Criteria

**Inter-SSE contact** defined as:
1. **Sequence separation:** ≥ 10 residues apart
2. **PAE threshold:** < 12 Å (confident contact)
3. **SSE requirement:** At least one residue in SSE
4. **Different SSEs:** Not in same SSE element

---

## Window Criteria (10 residues)

**Disordered if BOTH:**
1. **Total contacts ≤ 30**
   - Sum of inter-SSE contacts for all residues in window
2. **Hit residues ≤ 5**
   - Number of residues in good domains within window

**Rationale:**
- Low contacts = poorly structured
- Few annotated residues = not in confident domains

---

## Output Format

**File:** `{prefix}.diso`

**Format:** One residue ID per line (no header)

**Example:**
```
1
2
3
25
26
27
28
29
150
151
...
```

---

## Typical Statistics

### 500-Residue Protein

**Disordered residues:** 50-150 (10-30%)

**Common patterns:**
- N-terminal tails: ~10-20 residues
- C-terminal tails: ~10-20 residues
- Linkers between domains: ~5-15 residues
- Loops: ~3-10 residues each

---

## Common Issues

### No disorder file created
**Cause:** Missing input files (SSE, JSON, goodDomains)
**Fix:** Run steps 10-11 first

### All residues disordered
**Cause:** No good domains or no SSEs
**Check:** Review steps 10-11 outputs

### No residues disordered
**Cause:** All regions well-structured and annotated
**Normal:** For compact, well-folded proteins

### PAE format error
**Cause:** Unexpected JSON format
**Check:** AlphaFold JSON file format

---

## Key Functions

### `run_step12(prefix, working_dir, path_resolver=None)`
Main entry point. Predicts disordered regions.
`path_resolver`: Optional `PathResolver` for sharded output layout.

---

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Window size | 10 | Residues evaluated together |
| Contact threshold | ≤ 30 | Max inter-SSE contacts for disorder |
| Hit threshold | ≤ 5 | Max good domain residues for disorder |
| Sequence separation | ≥ 10 | Min residue separation for contact |
| PAE threshold | < 12 | Max PAE for confident contact |

---

## Integration with Pipeline

### Upstream Dependencies
- **Step 11 (SSE):** Provides SSE assignments
- **Step 10 (Filter Domains):** Provides good domains (optional)
- **AlphaFold JSON:** Provides PAE matrix

### Downstream Usage
- **Step 13 (Parse Domains):** Uses disorder predictions to avoid placing domains in disordered regions

---

## Performance Characteristics

### Scaling
- **Time:** O(N²) for contact calculation (N = protein length)
- **Memory:** O(N²) for PAE matrix storage
- **Typical:** Fast for proteins < 1000 residues

### Bottleneck
- **PAE matrix loading:** Dominates for large proteins
- **Contact calculation:** Nested loops over residues

---

## Summary

Step 12 predicts disordered regions using a 10-residue sliding window approach that integrates secondary structure, PAE confidence, and good domain annotations.

**Key metrics:**
- ✅ ~340 lines of code
- ✅ 5-20s execution time
- ✅ Handles both PAE formats (v4 and v6)
- ✅ Integrates SSE, PAE, and domain data

**Next:** Step 13 (Parse Domains) - final domain parsing using all previous outputs
