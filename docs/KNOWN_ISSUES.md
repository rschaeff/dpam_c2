# DPAM v2.0 Known Issues and Future Work

## Domain Range Accuracy Issues

### Issue 1: PAE-detected insertion domains not in ECOD

**Status:** Potential enhancement
**Severity:** Low
**Example:** Q9ZK07 (4 domains vs ECOD's 3)

**Description:**
DPAM v2.0 detects insertion/subdomain structures based on PAE uncertainty that ECOD classifies as single domains. In Q9ZK07, residues 126-180 show high PAE (6.77) relative to flanking regions 106-125 and 181-325, which are confidently connected (PAE 2.87). Step 13 correctly identifies this as a discontinuous domain with an insertion.

**Analysis:**
- PAE matrix shows 126-180 is structurally uncertain relative to surrounding regions
- ECOD lumps 101-325 as a single 206.1.3 domain
- DPAM v2.0 output may be more structurally accurate

**Potential Actions:**
- [ ] Add option to merge insertion domains for ECOD compatibility
- [ ] Flag insertion domains in output for manual review
- [ ] No action needed - current behavior may be preferred

---

### Issue 2: HHsearch/ECOD T-group boundary mismatch causing over-segmentation

**Status:** Reference data issue
**Severity:** Medium
**Example:** Q42524 (5 domains vs ECOD's 3)

**Description:**
HHsearch template database (pdb70) has different T-group coverage boundaries than current ECOD classification. This causes step 13 to create domain boundaries where T-group coverage changes, even when PAE indicates the regions should be connected.

**Analysis:**
```
Region      HHsearch T-group    ECOD expects
22-380      7584.1              323.1.1 (D1: 21-200)
373-470     4011.1              327.5.1 (D2: 201-455)
447-560     327.5               7584.1.1 (D3: 456-560)
```

Key boundaries:
- 380-381: PAE = 2.21 (LOW, should merge) but HHsearch T-group changes
- 510-511: PAE = 2.52 (LOW, should merge) but creates boundary

**Potential Actions:**
- [ ] Update pdb70 database to match current ECOD classification
- [ ] Add PAE-based merge post-processing for adjacent domains with low inter-domain PAE
- [ ] Weight PAE more heavily than HHsearch in step 13 probability calculation
- [ ] Add configurable threshold for PAE-based domain merging

---

### Issue 3: T-group assignment reversal in large proteins

**Status:** Reference data issue
**Severity:** Medium
**Example:** Q42524

**Description:**
HHsearch assigns T-groups that are completely reversed from ECOD classification:

| ECOD Domain | ECOD T-group | HHsearch T-group |
|-------------|--------------|------------------|
| D1 (21-200) | 323.1.1 | 7584.1 |
| D2 (201-455) | 327.5.1 | 7584.1 |
| D3 (456-560) | 7584.1.1 | 327.5 |

**Root Cause:**
The pdb70 HHsearch database templates were likely built from an older ECOD version with different T-group assignments, or there is structural similarity between these T-groups that HHsearch cannot distinguish.

**Potential Actions:**
- [ ] Rebuild pdb70 database from current ECOD version
- [ ] Add DALI-based T-group validation as tiebreaker
- [ ] Flag cases where HHsearch and DALI T-groups disagree

---

### Issue 4: Linker regions with no structural homology cause over-segmentation

**Status:** Reference data limitation
**Severity:** Medium
**Example:** A0B5E9 (3 domains vs ECOD's 2)

**Description:**
Linker/insertion regions that have no structural homologs in HHsearch/DALI databases are identified as separate domains, even when PAE indicates they should be connected to flanking regions.

**Analysis:**
```
Expected:  D1: 1-165, D2: 166-495
DPAM v2.0: D1: 1-160, D2: 266-295, D3: 166-265,296-495
```

Region 266-295 has **no coverage** in structural databases:
- HHsearch: covers 200-265, GAP, then 295-400+
- DALI: covers 165-265, GAP, then 294-500
- PAE at boundaries: 2.38 (265-266), 2.09 (295-296) - LOW, should merge

The 30-residue linker (266-295) lacks homologs, so step 13 cannot find evidence to merge it with flanking regions, despite PAE indicating structural connectivity.

**Key Insight:**
This differs from Issue 2 (T-group boundaries) - here there's simply NO structural evidence for the region, not conflicting evidence.

**Potential Actions:**
- [ ] Add PAE-based merge for isolated regions with no HHsearch/DALI coverage
- [ ] Lower the evidence threshold for merging when PAE strongly supports connectivity
- [ ] Flag regions with no structural homology for manual review
- [ ] Consider secondary structure continuity as additional merge signal

---

## Proposed Enhancement: PAE-based Domain Merging

**Rationale:**
When adjacent domains have low inter-domain PAE (<3.0), they are likely part of the same structural unit. Currently, HHsearch/DALI evidence can override this signal.

**Proposed Algorithm:**
```python
def pae_based_merge(domains, pae_matrix, threshold=3.0):
    """Merge adjacent domains with low inter-domain PAE."""
    merged = []
    i = 0
    while i < len(domains):
        current = domains[i]
        while i + 1 < len(domains):
            next_domain = domains[i + 1]
            boundary_pae = get_boundary_pae(current, next_domain, pae_matrix)
            if boundary_pae < threshold:
                current = merge(current, next_domain)
                i += 1
            else:
                break
        merged.append(current)
        i += 1
    return merged
```

**Implementation Location:** Post-processing after step 13 or as step 13b

---

## Summary Table

| Issue | Type | Severity | Affects | Fix Complexity |
|-------|------|----------|---------|----------------|
| 1. PAE insertion domains | Algorithm behavior | Low | Range accuracy | Low (optional merge) |
| 2. HHsearch T-group boundaries | Reference data | Medium | Range accuracy | High (rebuild DB) |
| 3. T-group reversal | Reference data | Medium | T-group accuracy | High (rebuild DB) |
| 4. Linker regions no homology | Reference data | Medium | Range accuracy | Medium (PAE merge) |
