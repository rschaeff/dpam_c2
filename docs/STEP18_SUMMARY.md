# Step 18 Summary: Get Alignment Mappings

**Status:** Complete
**Implementation:** `steps/step18_get_mapping.py`
**Lines of Code:** ~350
**Complexity:** Medium

---

## Purpose

Map domain residues to ECOD template residues using original HHsearch and DALI alignments. Provides the residue-to-residue mappings needed for coverage calculations and merge candidate detection in step 19.

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step GET_MAPPING \
  --working-dir ./work --data-dir ./data
```

### Input
- `{prefix}.step17_confident_predictions` - Confident predictions (from step 17)
- `{prefix}.map2ecod.result` - HHsearch alignments (from step 5)
- `{prefix}_good_hits` - DALI alignments (from step 9)
- `ECOD_maps/{ecod_id}.map` - PDB to ECOD residue numbering
- `ECOD_length` - Template lengths and ECOD ID to UID mapping

### Output
- `{prefix}.step18_mappings` - Domain predictions with template ranges

### Performance
- **Time:** 1-3 seconds
- **Memory:** <100 MB

---

## Algorithm

```
1. Load ECOD ID to UID mapping from ECOD_length
2. Load HHsearch alignments from map2ecod.result:
   a. Extract query and template residue lists
   b. Maintain position correspondence
3. Load DALI alignments from _good_hits:
   a. Extract query and template residue lists
   b. Template residues already in ECOD numbering
4. For each confident prediction:
   a. Get domain residues from range
   b. Find overlapping HHsearch hit for this ECOD:
      - Apply strict overlap check
      - Filter template residues to domain-overlapping positions
      - Map to ECOD canonical numbering
   c. Find overlapping DALI hit for this ECOD:
      - Apply strict overlap check
      - Filter template residues to domain-overlapping positions
5. Write mappings with HH and DALI template ranges
```

---

## Overlap Criteria (Stricter than Step 15)

```python
def check_overlap_strict(resids_a, resids_b):
    overlap = resids_a & resids_b
    # Must have >=33% overlap relative to domain
    if len(overlap) >= len(resids_a) * 0.33:
        # AND either >=50% of A or >=50% of B
        if (len(overlap) >= len(resids_a) * 0.5 or
            len(overlap) >= len(resids_b) * 0.5):
            return True
    return False
```

### Comparison with Step 15

| Step | Minimum Overlap | Condition |
|------|-----------------|-----------|
| Step 15 | 50% of A OR 50% of B | Permissive |
| Step 18 | 33% of A AND (50% of A OR 50% of B) | Strict |

---

## Template Residue Filtering

### Critical Concept
Only include template residues where the aligned query residue falls within the domain range:

```
Alignment: Query 1-500 -> Template 1-300
Domain D1: Query 1-200

Filter: Keep only template residues aligned to query 1-200
Result: Template subset (e.g., 1-120) specific to domain D1
```

### Implementation
```python
filtered_template_resids = []
for i in range(len(query_resids)):
    qres = query_resids[i]
    tres = template_resids[i]
    if qres in domain_resids:  # Only if query is in THIS domain
        filtered_template_resids.append(tres)
```

---

## Output Format

**File:** `{prefix}.step18_mappings`

**Header:**
```
# domain  domain_range  ecod_id  tgroup  dpam_prob  quality  hh_template_range  dali_template_range
```

**Example:**
```
# domain	domain_range	ecod_id	tgroup	dpam_prob	quality	hh_template_range	dali_template_range
D1	10-150	e1abc1	2.30.30	0.9234	good	5-120	8-115
D1	10-150	e2xyz1	2.30.42	0.8856	ok	10-118	na
D2	160-280	e3def1	1.10.5	0.7512	good	1-95	5-92
```

### Value: 'na'
Indicates no alignment found or overlap criteria not met.

---

## ECOD Residue Mapping

### HHsearch Templates
HHsearch template residues are in PDB numbering. Map to ECOD canonical:
```python
ecod_resids, ecod_to_pdb = load_ecod_map(f"{uid}.map")
if tres in ecod_resids:
    canonical_tres = ecod_to_pdb[tres]
```

### DALI Templates
DALI template residues from step 9 are already in ECOD canonical numbering.

---

## Typical Statistics

### 500-Residue Protein
- **Input predictions:** 100-300 rows
- **Output mappings:** 100-300 rows
- **HHsearch mapped:** 70-90%
- **DALI mapped:** 60-85%
- **Both mapped:** 50-75%

### Summary Statistics Logged
```
Step 18 complete: 245 mappings generated
  HHsearch mapped: 198/245
  DALI mapped: 172/245
  Both mapped: 145/245
```

---

## Common Issues

### HHsearch hits not found
**Error:** `HHsearch hits not found: map2ecod.result`
**Fix:** Ensure step 5 completed successfully

### DALI hits not found
**Error:** `DALI hits not found: _good_hits`
**Fix:** Ensure step 9 completed successfully

### No ECOD map for template
**Cause:** Missing ECOD_maps/{uid}.map file
**Note:** Logs debug message, continues with 'na'

### Length mismatch in alignments
**Warning:** `HHsearch Q/T length mismatch`
**Cause:** Query and template residue lists have different lengths
**Fix:** Check alignment parsing, skip malformed entries

---

## Use in Step 19

Step 19 uses template ranges to identify merge candidates:
- Domains covering different regions of same ECOD template
- Non-overlapping template regions suggest domain split
- Merge if template coverage supports it

---

## Backward Compatibility

**100% v1.0 compatible**
- Overlap criteria (33%/50%) exact
- Template filtering logic exact
- ECOD mapping approach exact
- Output format exact

---

## Quick Commands

```bash
# Run step 18
dpam run-step AF-P12345 --step GET_MAPPING \
  --working-dir ./work --data-dir ./data

# Check output
head work/AF-P12345.step18_mappings | column -t

# Count mapped vs unmapped
grep -v "^#" work/AF-P12345.step18_mappings | \
  awk -F'\t' '{
    if ($7 != "na") hh++;
    if ($8 != "na") dali++;
  } END {print "HH:", hh, "DALI:", dali}'

# Find domains with both mappings
grep -v "^#" work/AF-P12345.step18_mappings | \
  awk -F'\t' '$7 != "na" && $8 != "na"' | wc -l
```

---

## Summary

Step 18 maps domain residues to ECOD template residues for merge candidate detection.

**Key metrics:**
- 350 lines of code
- 1-3s execution time
- Strict overlap criteria (33%/50%)
- Domain-specific template filtering
- Ready for merge candidate detection (step 19)
