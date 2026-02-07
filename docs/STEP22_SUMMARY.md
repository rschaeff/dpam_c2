# Step 22 Summary: Merge Domains via Transitive Closure

**Status:** Complete
**Implementation:** `steps/step22_merge_domains.py`
**Lines of Code:** ~190
**Complexity:** Medium

---

## Purpose

Merge connected domains using graph clustering via transitive closure.
If domain A merges with B, and B merges with C, then all three (A, B, C) merge into one domain.

---

## Quick Reference

### Command
```bash
dpam run-step AF-P12345 --step MERGE_DOMAINS --working-dir ./work
```

### Input
- `{prefix}.step21_comparisons` - Domain pairs with connectivity judgments

### Output
- `{prefix}.step22_merged_domains` - Merged domain groups with combined ranges

### Performance
- **Time:** <1 second
- **Memory:** <50 MB

---

## Algorithm

```
1. Load validated pairs (judgment > 0) from step 21
2. Build merge groups via transitive closure:
   a. Start with each pair as a separate group
   b. Iteratively merge groups that share any domain
   c. Repeat until no more merges occur (convergence)
3. For each final group:
   a. Combine all residues from member domains
   b. Sort residue IDs
   c. Convert to compact range string
4. Write results
```

---

## Transitive Closure

### Example
```
Input pairs:
  {A, B}  - A merges with B
  {B, C}  - B merges with C
  {D, E}  - D merges with E

Iteration 1:
  {A, B, C}  - Merged A-B and B-C (share B)
  {D, E}     - Unchanged

Iteration 2:
  No change (converged)

Output:
  Group 1: A, B, C
  Group 2: D, E
```

### Implementation
```python
def transitive_closure(pairs):
    groups = [pair.copy() for pair in pairs]

    while True:
        new_groups = []
        for group in groups:
            # Check intersection with existing groups
            found = False
            for new_group in new_groups:
                if group & new_group:  # Set intersection
                    new_group.update(group)
                    found = True
                    break
            if not found:
                new_groups.append(group.copy())

        if len(groups) == len(new_groups):
            break  # Converged
        groups = new_groups

    return groups
```

---

## Input Format

**File:** `{prefix}.step21_comparisons`

**Header:**
```
# protein	domain1	domain2	judgment	range1	range2
```

**Only processes:** Lines with judgment > 0 (connected pairs)

---

## Output Format

**File:** `{prefix}.step22_merged_domains`

**Header:**
```
# protein	merged_domains	merged_range
```

**Format:** Tab-delimited
```
{prefix}<TAB>{domain_list}<TAB>{merged_range}
```

**Example:**
```
# protein	merged_domains	merged_range
AF-P12345	D1,D2,D3	10-150
AF-P12345	D4,D5	200-350
```

---

## Range Combination

### Process
1. Collect residue sets from all member domains
2. Union all residue sets
3. Sort residue IDs
4. Convert to compact range string using `format_range()`

### Example
```
Domain D1: 10-50
Domain D2: 55-100
Domain D3: 110-150

Union: {10,...,50,55,...,100,110,...,150}
Range: "10-50,55-100,110-150"
```

---

## Key Functions

### `transitive_closure(pairs)`
Compute transitive closure via iterative merging.
- **Input:** List of domain pairs (sets of 2 names)
- **Output:** List of merged groups (sets of N names)

### `run_step22(prefix, working_dir, path_resolver=None)`
Main entry point.
- Loads validated pairs
- Computes transitive closure
- Writes merged groups with combined ranges
- `path_resolver`: Optional `PathResolver` for sharded output layout

---

## Typical Statistics

### 500-Residue Protein
- **Input pairs:** 3-10 validated pairs
- **Output groups:** 2-5 merged groups
- **Largest group:** 2-4 domains
- **Average group size:** 2-3 domains

---

## Common Issues

### No validated merge pairs
**Cause:** Step 21 rejected all pairs (judgment = 0)
**Result:** Step completes successfully with no output

### No comparisons file
**Cause:** Step 21 not run or failed
**Fix:** Re-run Step 21

### Single-member groups
**Cause:** Domain only connected to itself (shouldn't happen)
**Check:** Verify step 21 output

---

## Backward Compatibility

100% v1.0 compatible
- Transitive closure algorithm identical
- Domain list format (comma-separated, sorted)
- Range combination logic
- Output format matches

---

## Quick Commands

```bash
# Run step 22
dpam run-step AF-P12345 --step MERGE_DOMAINS --working-dir ./work

# Check output
cat work/AF-P12345.step22_merged_domains

# Count merged groups
grep -v "^#" work/AF-P12345.step22_merged_domains | wc -l

# Show largest group
grep -v "^#" work/AF-P12345.step22_merged_domains | \
  awk -F'\t' '{n=split($2,a,","); print n, $2}' | sort -rn | head -1
```

---

## Summary

Step 22 is **complete** and merges connected domains.

**Key metrics:**
- 190 lines of code
- <1s execution time
- Transitive closure via iterative set merging
- Combines residue ranges from all group members
- Outputs merged groups for Step 23 classification
