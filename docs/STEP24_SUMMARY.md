# Step 24 Summary: Integrate Results with SSE Analysis

**Status:** Complete
**Implementation:** `steps/step24_integrate_results.py`
**Lines of Code:** ~360
**Complexity:** Medium

---

## Purpose

Refine domain classifications using secondary structure analysis.
Filters out simple topology domains (<3 SSEs) and assigns final quality labels.

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step INTEGRATE_RESULTS \
  --working-dir ./work --data-dir ./data
```

### Input
- `{prefix}.step23_predictions` - Domain predictions (full/part/miss)
- `{prefix}.sse` - Secondary structure elements from Step 11
- `ecod.latest.domains` - ECOD keywords (optional)

### Output
- `step24/{prefix}_domains` - Per-protein results with SSE counts
- `{prefix}.finalDPAM.domains` - Final domain definitions

### Performance
- **Time:** <1 second
- **Memory:** <50 MB

---

## Classification Refinement Logic

### SSE Counting Criteria
- **Helix:** >= 6 consecutive residues
- **Strand:** >= 3 consecutive residues

### Decision Tree

| Original | SSE Count | Quality | Final Label |
|----------|-----------|---------|-------------|
| miss | < 3 | any | simple_topology |
| miss | >= 3 | any | low_confidence |
| part | < 3 | high | partial_domain |
| part | < 3 | low | simple_topology |
| part | >= 3 | any | partial_domain |
| full | < 3 | high | good_domain |
| full | < 3 | low | simple_topology |
| full | >= 3 | any | good_domain |

### High Quality Criteria
All three must be true:
- HH_prob >= 0.95
- weighted_ratio >= 0.8
- length_ratio >= 0.8

---

## Algorithm

```
1. Load SSE data from step 11:
   - Build residue -> (sse_id, sse_type) mapping
   - Identify helix and strand SSE IDs
2. For each domain prediction:
   a. Parse domain residue range
   b. Count helices with >= 6 domain residues
   c. Count strands with >= 3 domain residues
   d. Calculate total SSE count
   e. Determine high_quality flag
   f. Apply refinement logic to get final label
3. Sort domains by mean residue position
4. Renumber as nD1, nD2, nD3...
5. Write step24/{prefix}_domains
6. Update {prefix}.finalDPAM.domains
```

---

## SSE Counting Details

### Per-Domain SSE Analysis
```python
# Count residues per SSE in domain
sse_to_count = {}
for resid in domain_resids:
    if resid in structured_resids:
        sse_id, sse_type = resid_to_sse[resid]
        sse_to_count[sse_id] = sse_to_count.get(sse_id, 0) + 1

# Count valid SSEs
helix_count = sum(1 for sse_id, count in sse_to_count.items()
                  if sse_id in helix_sses and count >= 6)

strand_count = sum(1 for sse_id, count in sse_to_count.items()
                   if sse_id in strand_sses and count >= 3)

sse_count = helix_count + strand_count
```

---

## Output Format

### File: `step24/{prefix}_domains`

**Header:**
```
Domain	Range	ECOD_num	ECOD_key	T-group	DPAM_prob	HH_prob	DALI_zscore	Hit_cov	Tgroup_cov	Judge	Hcount	Scount
```

**Example:**
```
nD1	10-150	e2rspA1	PH	1.1.1	0.950	9.5	25.3	0.850	0.920	good_domain	4	3
nD2	200-280	e3dkrA1	SH3	2.3.1	0.870	8.9	18.5	0.450	0.380	partial_domain	2	2
nD3	300-350	na	na	na	0.420	0.0	0.0	0.000	0.000	simple_topology	1	0
```

### File: `{prefix}.finalDPAM.domains`

Simple two-column format for downstream use:
```
nD1	10-150
nD2	200-280
nD3	300-350
```

---

## Final Label Values

| Label | Meaning | Typical Action |
|-------|---------|----------------|
| **good_domain** | High-confidence ECOD match | Accept |
| **partial_domain** | Partial match or coverage | Review manually |
| **low_confidence** | Complex structure, poor match | Review manually |
| **simple_topology** | Too simple or poor quality | May be linker/coil |

---

## Key Functions

### `count_sse_elements(domain_resids, structured_resids, resid_to_sse, helix_sses, strand_sses)`
Count helices (>=6 res) and strands (>=3 res) in domain.

### `refine_classification(original_class, sse_count, hh_prob, weighted_ratio, length_ratio)`
Apply SSE-based refinement to get final label.

### `run_step24(prefix, working_dir, data_dir, path_resolver=None, **kwargs) -> bool`
Main integration function. `path_resolver`: Optional PathResolver for sharded output layout.

---

## Typical Statistics

### 500-Residue Protein
- **Domains:** 3-8
- **good_domain:** 40-60%
- **partial_domain:** 20-30%
- **low_confidence:** 5-15%
- **simple_topology:** 10-20%

---

## Common Issues

### SSE file not found
**Cause:** Step 11 (SSE) not run
**Fix:** Run Step 11 before Step 24

### No predictions found
**Cause:** Step 23 produced no predictions
**Result:** Step completes with no output

### All simple_topology
**Cause:** Small domains or all-coil protein
**Check:** Review SSE counts in output

### ECOD keywords missing
**Cause:** ecod.latest.domains not in data_dir
**Result:** ECOD_key column shows "na" (non-fatal)

---

## Backward Compatibility

100% V1-compatible
- SSE counting thresholds (6 helix, 3 strand)
- High quality criteria (0.95, 0.8, 0.8)
- Refinement logic
- Domain renumbering (nD1, nD2, ...)
- Output format matches

---

## Quick Commands

```bash
# Run step 24
dpam run-step AF-P12345 --step INTEGRATE_RESULTS \
  --working-dir ./work --data-dir ./data

# Check detailed output
cat work/step24/AF-P12345_domains | column -t

# Check final domains
cat work/AF-P12345.finalDPAM.domains

# Count by final label
cut -f11 work/step24/AF-P12345_domains | grep -v "Judge" | sort | uniq -c

# Show good domains
grep "good_domain" work/step24/AF-P12345_domains
```

---

## Domain Ordering

Domains are ordered by mean residue position:
1. Calculate mean of all residue IDs in domain
2. Sort domains by mean value (N-terminal first)
3. Renumber sequentially as nD1, nD2, nD3...

This ensures consistent ordering regardless of processing order.

---

## Summary

Step 24 is **complete** and produces final domain classifications.

**Key metrics:**
- 360 lines of code
- <1s execution time
- SSE-based classification refinement
- Four final labels: good_domain, partial_domain, low_confidence, simple_topology
- Outputs final .finalDPAM.domains file
- Last step in ML pipeline (Phase 3)
