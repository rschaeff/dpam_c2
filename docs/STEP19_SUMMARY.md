# Step 19 Summary: Get Merge Candidates

**Status:** Complete
**Implementation:** `steps/step19_get_merge_candidates.py`
**Lines of Code:** ~320
**Complexity:** Medium

---

## Purpose

Identify domain pairs that should potentially be merged based on shared ECOD template coverage. Uses position-specific weights to calculate coverage and applies support vs opposition counting to validate merge candidates.

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step GET_MERGE_CANDIDATES \
  --working-dir ./work --data-dir ./data
```

### Input
- `{prefix}.step18_mappings` - Domain-ECOD mappings with template ranges (from step 18)
- `ECOD_length` - Template lengths
- `posi_weights/*.weight` - Position-specific weights (optional)

### Output
- `{prefix}.step19_merge_candidates` - Domain pairs to merge
- `{prefix}.step19_merge_info` - Supporting ECOD information (debug)

### Performance
- **Time:** 1-5 seconds
- **Memory:** <100 MB

---

## Algorithm

```
1. Load ECOD template lengths
2. For each mapping entry:
   a. Select template range (DALI if >50% of HHsearch, else HHsearch)
   b. Load position-specific weights for ECOD template
   c. Calculate weighted coverage
   d. Track by domain and by ECOD
3. Find domain pairs sharing ECOD templates:
   For each ECOD with >=2 domain hits:
      For each domain pair (D1, D2):
         a. Both must be high confidence (within 0.1 of their best)
         b. Template regions must not overlap (< 25% overlap)
         c. Record as potential merge candidate
4. Validate merge candidates:
   For each candidate pair:
      a. Count supporting ECODs
      b. Count opposing ECODs (>50% coverage, not in support set)
      c. Merge if support > opposition for either domain
5. Write validated merge candidates
```

---

## Merge Criteria

### 1. Shared Template
Both domains must hit the same ECOD template.

### 2. High Confidence
Both predictions must be within 0.1 of their respective best scores:
```python
prob1 + 0.1 > domain_to_best_prob[domain1] and
prob2 + 0.1 > domain_to_best_prob[domain2]
```

### 3. Non-overlapping Template Regions
Template overlap must be < 25% for BOTH domains:
```python
common = tres1 & tres2
# Skip only if BOTH have high overlap (AND condition)
if (len(common) >= 0.25 * len(tres1) and
    len(common) >= 0.25 * len(tres2)):
    continue  # Skip this pair
```

### 4. Support > Opposition
Supporting ECODs must outnumber opposing ECODs for at least one domain:
```python
if (support_count > len(against1) or
    support_count > len(against2)):
    # Valid merge candidate
```

---

## Position-Specific Weights

### Weight File Format
```
resid  aa  secondary_structure  weight
1      M   C                    0.85
2      A   H                    1.20
3      K   H                    1.35
...
```

### Weighted Coverage Calculation
```python
covered_weight = sum(pos_weights.get(res, 0.0) for res in template_resids)
coverage = covered_weight / total_weight
```

### Default Weights
If no weight file exists, use uniform weights:
```python
pos_weights = {i: 1.0 for i in range(1, ecod_length + 1)}
```

---

## Template Range Selection

Uses V1 logic: DALI only if it covers >50% of HHsearch residues:
```python
hh_resids = parse_range(hh_template_range) if hh_template_range != 'na' else set()
dali_resids = parse_range(dali_template_range) if dali_template_range != 'na' else set()

if len(dali_resids) > len(hh_resids) * 0.5:
    template_resids = dali_resids
else:
    template_resids = hh_resids
```

---

## Output Format

### Merge Candidates File
**File:** `{prefix}.step19_merge_candidates`

**Header:**
```
# domain1  range1  domain2  range2
```

**Example:**
```
# domain1	range1	domain2	range2
D1	10-150	D2	160-280
D3	290-400	D4	410-500
```

### Merge Info File (Debug)
**File:** `{prefix}.step19_merge_info`

**Format:**
```
domain1,domain2  supporting_ecod1,supporting_ecod2,...
```

**Example:**
```
D1,D2	e1abc1,e2xyz1,e3def1
D3,D4	e4ghi1
```

---

## Supporting vs Opposing ECODs

### Supporting ECODs
ECODs where both domains:
- Hit the same template
- Have high confidence
- Cover non-overlapping regions

### Opposing ECODs
ECODs where a domain:
- Has high confidence (within 0.1 of best)
- Has high coverage (>50%)
- Is NOT in the supporting set

### Validation Logic
```python
# Count opposing for domain1
against1 = set()
for hit in domain_to_hits[domain1]:
    if (hit['prob'] + 0.1 > domain_to_best_prob[domain1] and
        hit['coverage'] > 0.5 and
        hit['ecod'] not in supporting_ecods):
        against1.add(hit['ecod'])

# Merge if support exceeds opposition for either domain
if support_count > len(against1) or support_count > len(against2):
    validated_merges.append(...)
```

---

## Typical Statistics

### 500-Residue Protein (3 domains)
- **Input mappings:** 100-300 rows
- **Domains with shared ECODs:** 2-3 pairs
- **Potential merge candidates:** 1-5 pairs
- **Validated merges:** 0-2 pairs

### Multi-domain Proteins
More domains typically yield more merge candidates.

---

## Common Issues

### No merge candidates found
**Cause:** Domains hit different ECOD templates, or overlap too much
**Note:** Normal for well-separated domains

### Many merge candidates
**Cause:** Large protein with many similar domains
**Note:** Step 22 will merge transitively

### Missing position weights
**Warning:** Falls back to uniform weights
**Fix:** Ensure posi_weights/ directory exists in data_dir

---

## Example Scenario

```
Domain D1 (10-150) hits:
  e1abc1: template 1-100, prob=0.95, coverage=0.70
  e2xyz1: template 5-95,  prob=0.88, coverage=0.65

Domain D2 (160-280) hits:
  e1abc1: template 110-200, prob=0.92, coverage=0.60
  e3def1: template 1-80,    prob=0.75, coverage=0.55

Analysis for e1abc1:
  D1 covers template 1-100
  D2 covers template 110-200
  Overlap: 0 residues (0%)
  Both high confidence: Yes
  Result: MERGE CANDIDATE

Supporting ECODs: {e1abc1}
Opposing for D1: {e2xyz1} if coverage > 0.5
Support (1) > Opposition (1)? No
Opposing for D2: {} (e3def1 coverage 0.55, in support? No, but coverage <=0.5? Yes)
Support (1) > Opposition (0)? Yes -> VALIDATED
```

---

## Key Functions

```python
def run_step19(prefix, working_dir, data_dir, path_resolver=None, **kwargs) -> bool
    # path_resolver: Optional PathResolver for sharded output layout.
```

---

## Backward Compatibility

**100% v1.0 compatible**
- Confidence threshold: 0.1 (exact)
- Overlap threshold: 25% (exact)
- Template selection logic (exact)
- Support/opposition counting (exact)
- AND condition for overlap check (exact)

---

## Quick Commands

```bash
# Run step 19
dpam run-step AF-P12345 --step GET_MERGE_CANDIDATES \
  --working-dir ./work --data-dir ./data

# Check merge candidates
cat work/AF-P12345.step19_merge_candidates

# Check supporting ECODs
cat work/AF-P12345.step19_merge_info

# Count merge candidates
grep -v "^#" work/AF-P12345.step19_merge_candidates | wc -l
```

---

## Summary

Step 19 identifies domain pairs to merge based on shared ECOD template coverage.

**Key metrics:**
- 320 lines of code
- 1-5s execution time
- Confidence threshold: 0.1
- Overlap threshold: 25%
- Coverage threshold: 50%
- Position-weighted coverage
- Support vs opposition validation
- Ready for domain extraction (step 20)
