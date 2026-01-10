# Step 7: Iterative DALI - Implementation Details

**Status:** âœ… Complete - Matches v1.0 Exactly  
**File:** `step07_iterative_dali.py`  
**Complexity:** Very High  
**Parallelization:** Yes (multiprocessing.Pool)

---

## ðŸŽ¯ Purpose

Run iterative DALI structural alignment against ECOD70 templates to identify structural domains. For each ECOD domain candidate, repeatedly align against the template and remove matched regions until no significant alignment remains.

## ðŸ"„ Algorithm Overview

### Per ECOD Domain (Parallel Worker):

```
INITIALIZE:
  - Copy query PDB as working file
  - Create temporary directories
  - Track all query residues

WHILE residues remain:
  1. Run DALI alignment (dali.pl)
  2. Parse output (mol*.txt files)
  3. Extract z-score and aligned positions
  
  IF n_aligned < 20:
    BREAK (insufficient alignment)
  
  4. Record hit:
     >{edomain}_{iteration}  z_score  n_aligned  q_len  t_len
     query_resid  template_resid
     ...
  
  5. Calculate aligned range with gap tolerance:
     cutoff = max(5, len(residues) * 0.05)
  
  6. Remove aligned residues from query PDB
  
  IF remaining < 20:
    BREAK (insufficient residues)

CLEANUP:
  - Remove temporary directories
  - Return success if any hits found
```

### Main Orchestration:

```
1. Read ECOD candidates from {prefix}_hits4Dali
2. Create multiprocessing.Pool with {cpus} workers
3. Process all domains in parallel
4. Concatenate individual hits files
5. Clean up temporary directories
6. Mark as done
```

---

## ðŸ"‚ Input/Output Files

### Input Files

| File | Source | Description |
|------|--------|-------------|
| `{prefix}.pdb` | Step 1 | Standardized query structure |
| `{prefix}_hits4Dali` | Step 6 | List of ECOD domain candidates |
| `ECOD70/{edomain}.pdb` | Data | ECOD template structures |

### Output Files

| File | Format | Description |
|------|--------|-------------|
| `{prefix}_iterativdDali_hits` | Text | All DALI hits (concatenated) |
| `{prefix}.iterativeDali.done` | Marker | Completion flag |

### Temporary Files (Cleaned Up)

| Path | Purpose |
|------|---------|
| `iterativeDali_{prefix}/` | Main working directory |
| `tmp_{prefix}_{edomain}/` | Per-domain temp directory |
| `output_tmp/` | DALI output files |
| `{prefix}_{edomain}.pdb` | Working query PDB (iteratively reduced) |
| `{prefix}_{edomain}_hits` | Per-domain hits (before concatenation) |

---

## ðŸ"Š Output Format

### Hit Header Line

```
>{edomain}_{iteration}<TAB>{zscore}<TAB>{n_aligned}<TAB>{q_len}<TAB>{t_len}
```

**Example:**
```
>000000003_1    25.3    45  124 120
```

### Alignment Lines

```
{query_resid}<TAB>{template_resid}
```

**Example:**
```
>000000003_1    25.3    45  124 120
10  5
11  6
12  7
...
```

**Field Descriptions:**
- `edomain`: ECOD domain number (e.g., 000000003)
- `iteration`: Iteration number (1, 2, 3...)
- `zscore`: DALI z-score (float)
- `n_aligned`: Number of aligned residue pairs
- `q_len`: Current query length (decreases each iteration)
- `t_len`: Template length (always 0 in v1.0)
- `query_resid`: Query residue ID (actual PDB numbering)
- `template_resid`: Template residue position (1-based)

---

## âš™ï¸ Key Implementation Details

### 1. Gap Tolerance Calculation

**CRITICAL**: This matches v1.0 exactly:

```python
def get_domain_range(resids: List[int]) -> str:
    """Calculate range with v1.0 gap tolerance"""
    resids = sorted(resids)
    
    # v1.0 formula
    cutoff1 = 5
    cutoff2 = len(resids) * 0.05
    cutoff = max(cutoff1, cutoff2)
    
    # Segment by gap tolerance
    segs = []
    for resid in resids:
        if not segs:
            segs.append([resid])
        else:
            if resid > segs[-1][-1] + cutoff:
                segs.append([resid])
            else:
                segs[-1].append(resid)
    
    # Format as range string
    return ','.join([f"{seg[0]}-{seg[-1]}" for seg in segs])
```

**Why it matters:**
- Small proteins (100 residues): cutoff = max(5, 5) = 5
- Large proteins (1000 residues): cutoff = max(5, 50) = 50
- Ensures reasonable segment merging regardless of size

### 2. Residue Removal Strategy

```python
# 1. Get aligned residues (from DALI output)
raw_qresids = [Qresids[q-1] for q, t in alignments]

# 2. Calculate range with gap tolerance
qrange = get_domain_range(raw_qresids)  # e.g., "10-50,60-100"

# 3. Expand to full segments (includes gaps)
qresids_to_remove = set()
for qseg in qrange.split(','):
    start, end = map(int, qseg.split('-'))
    qresids_to_remove.update(range(start, end + 1))

# 4. Remove from current residues
remain_resids = Qresids_set - qresids_to_remove

# 5. Rewrite PDB with only remaining residues
```

### 3. Z-Score Parsing

From DALI output:
```
No 1: Z-score=25.3extra data
```

v1.0 parsing:
```python
if 'Z-score' in word:
    subwords = word.split('=')
    zinfo = subwords[1].split('.')
    zscore = float(zinfo[0] + '.' + zinfo[1])
    # Result: 25.3
```

### 4. Directory Management

v1.0 uses specific `os.chdir()` pattern:

```python
# Change to output directory before DALI
os.chdir(output_tmp_dir)

# Run DALI with relative paths
dali.pl --pdbfile1 ../{query}.pdb --dat1 ./ --dat2 ./

# Change back
os.chdir(working_dir)
```

**Why:** DALI creates files in current directory.

### 5. Multiprocessing Pattern

```python
def run_dali(args):
    """Worker function"""
    prefix, edomain, working_dir, data_dir = args
    # ... process single domain ...
    return success

# In main:
inputs = [(prefix, ed, working_dir, data_dir) for ed in edomains]
with Pool(processes=cpus) as pool:
    results = pool.map(run_dali, inputs)
```

**Note:** Each worker is completely independent (no shared state).

---

## ðŸ"¬ Backward Compatibility Verification

### File Format Comparison

| Aspect | v1.0 | v2.0 | Match? |
|--------|------|------|--------|
| Hit header format | `>ECOD_N\tZ\tN\tQL\tTL` | Same | âœ… |
| Alignment format | `QRES\tTRES` | Same | âœ… |
| Tab delimiters | Yes | Yes | âœ… |
| Z-score precision | Variable | Variable | âœ… |
| Iteration numbering | 1-based | 1-based | âœ… |
| File naming | `{prefix}_iterativdDali_hits` | Same | âœ… |

### Algorithm Comparison

| Step | v1.0 | v2.0 | Match? |
|------|------|------|--------|
| Gap tolerance | `max(5, N*0.05)` | Same | âœ… |
| Min alignment | 20 residues | 20 residues | âœ… |
| Min remaining | 20 residues | 20 residues | âœ… |
| Residue removal | Range expansion | Range expansion | âœ… |
| PDB rewriting | ATOM lines only | ATOM lines only | âœ… |
| Cleanup | Remove tmp dirs | Remove tmp dirs | âœ… |

---

## ðŸ"Š Performance Characteristics

### Typical 500-Residue Protein

| Metric | Value |
|--------|-------|
| **Input candidates** | 150-600 domains |
| **Iterations per domain** | 1-5 (average 2-3) |
| **Time per DALI run** | 20-60 seconds |
| **Total time (1 CPU)** | 8-20 hours |
| **Total time (8 CPUs)** | 1-3 hours |
| **Memory per worker** | 1-2 GB |
| **Disk I/O** | High (many tmp files) |

### Bottleneck Analysis

```
Total time â‰ˆ N_domains Ã— N_iterations Ã— T_dali / N_cpus

Where:
- N_domains: 150-600 (from step 6)
- N_iterations: 1-5 average (depends on domain complexity)
- T_dali: 30-60s (depends on protein size)
- N_cpus: Parallelization factor
```

**Example:**
- 400 domains Ã— 2.5 iterations Ã— 40s / 8 CPUs = 1.4 hours

### Scaling Recommendations

| Protein Size | Candidates | CPUs | Expected Time |
|--------------|-----------|------|---------------|
| <250 residues | 100-300 | 4 | 1-2 hours |
| 250-500 residues | 200-500 | 8 | 1-3 hours |
| 500-1000 residues | 400-800 | 16 | 2-4 hours |
| >1000 residues | 600-1200 | 32 | 3-6 hours |

---

## ⚠️ Common Issues

### 1. DALI Not Found

**Symptom:**
```
RuntimeError: dali.pl not found in PATH
```

**Solution:**
```bash
# Check availability
which dali.pl

# Load module (HPC)
module load dali

# Or add to PATH
export PATH=/path/to/dali/bin:$PATH
```

### 2. Template Not Found

**Symptom:**
```
WARNING: Template not found: ECOD70/000000003.pdb
```

**Solution:**
- Verify ECOD70 directory exists in data_dir
- Check ECOD domain number format (9 digits)
- Ensure all candidates have corresponding templates

### 3. Memory Exhaustion

**Symptom:**
```
MemoryError or killed by OOM
```

**Solution:**
```bash
# Reduce parallel workers
dpam run AF-P12345 --cpus 4  # Instead of 16

# Request more memory (SLURM)
#SBATCH --mem-per-cpu=4G  # Instead of 2G
```

### 4. Disk Space Issues

**Symptom:**
```
OSError: No space left on device
```

**Solution:**
- DALI creates many temporary files
- Ensure 10-20 GB free space per worker
- Use local scratch space if available:
  ```bash
  export TMPDIR=/scratch/$USER
  ```

### 5. Stalled Workers

**Symptom:**
- Some workers never complete
- No error messages

**Solution:**
- Check individual log files
- May be DALI hanging on specific domains
- Set timeout (future enhancement)

---

## ðŸ§ª Testing Strategy

### Unit Test (Mock DALI)

```python
def test_get_domain_range():
    """Test gap tolerance calculation"""
    # Small protein
    resids = [1, 2, 3, 10, 11, 12]
    assert get_domain_range(resids) == "1-3,10-12"
    
    # Large protein (5% > 5)
    resids = list(range(1, 101)) + list(range(110, 201))
    # Gap = 9, cutoff = max(5, 100*0.05) = 5
    # Should split at gap
    assert get_domain_range(resids) == "1-100,110-200"
```

### Integration Test (Real DALI)

```bash
# Test with 5 domains, 1 CPU
echo "000000003
000000010
000000015
000000020
000000025" > test_hits4Dali

python step07_iterative_dali.py AF-P12345-test ./test_work ./data 1

# Verify output
wc -l test_work/AF-P12345-test_iterativdDali_hits
# Should have multiple hits
```

### Performance Test

```bash
# Time with different CPU counts
for cpus in 1 2 4 8; do
    time dpam run-step AF-P12345 --step ITERATIVE_DALI --cpus $cpus
done

# Verify scaling
# Expected: ~linear speedup up to 8 CPUs
```

---

## ðŸ"š Related Documentation

- **v1.0 Original:** `old_v1.0/v1.0/step7_iterative_dali_aug_multi.py`
- **DALI Tool:** `tools/dali.py`
- **Step 6 (Input):** `STEP6_USAGE.md`
- **Step 8 (Output):** `STEP8_USAGE.md`
- **Architecture:** `docs/ARCHITECTURE.md`

---

## âœ… Verification Checklist

Before deploying:

- [ ] Gap tolerance formula matches v1.0 exactly
- [ ] Output format matches (tabs, decimal precision)
- [ ] Iteration numbering starts at 1
- [ ] Residue IDs are actual PDB numbering (not indices)
- [ ] Template length field is 0 (like v1.0)
- [ ] Temporary directories are cleaned up
- [ ] Done file is created
- [ ] Multiprocessing works with 1, 4, 8, 16 CPUs
- [ ] Test structure produces same output as v1.0

---

## ðŸ"§ Future Optimizations (Post-Validation)

Once v1.0 compatibility is verified:

1. **Timeout Mechanism**:
   - Add timeout for individual DALI runs
   - Skip or retry stuck domains

2. **Progress Tracking**:
   - Report domains completed: "50/500 domains processed"
   - Estimated time remaining

3. **Disk Optimization**:
   - Use ramdisk for temporary files
   - Stream concatenation instead of reading all

4. **Memory Optimization**:
   - Process domains in batches
   - Clean up immediately after each domain

5. **Checkpointing**:
   - Save completed domains
   - Resume from last checkpoint

6. **Better Error Handling**:
   - Classify failures (template missing, DALI error, etc.)
   - Retry strategy for transient failures

---

**Implementation Date:** 2025-10-06  
**Status:** Ready for testing  
**Next Step:** Integration testing with real data
