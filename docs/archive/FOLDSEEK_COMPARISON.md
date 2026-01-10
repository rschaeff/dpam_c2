# Foldseek Parameter Comparison: v1.0 vs v2.0

**Date**: 2025-11-22
**Issue**: v2.0 finds 52% fewer hits than v1.0 (77 vs 161)

## Summary

**Root Cause**: Foldseek **prefilter** stage is filtering out 52% of hits before structural alignment

**Impact**: Cascade failures in downstream DALI steps (6-8)

## Command-Line Comparison

### v1.0 Command (from `step4_run_foldseek.py`)
```bash
foldseek easy-search \
    step2/homsa/A0A024R1R8.pdb \
    /scratch/ECOD_foldseek_DB \
    step4/homsa/A0A024R1R8.foldseek \
    /scratch/homsa_tmp \
    -e 1000 \
    --max-seqs 1000000
```

**Parameters:**
- `-e 1000` - E-value threshold
- `--max-seqs 1000000` - Maximum sequences to return
- No explicit `-s` (sensitivity) parameter → **uses default**

### v2.0 Command (from `dpam/tools/foldseek.py`)
```bash
foldseek easy-search \
    validation_run/AF-A0A024R1R8-F1.pdb \
    /home/rschaeff_1/data/dpam_reference/ecod_data/ECOD_foldseek_DB \
    validation_run/AF-A0A024R1R8-F1.foldseek \
    validation_run/foldseek_tmp_AF-A0A024R1R8-F1 \
    -e 1000000 \
    --max-seqs 1000000 \
    --threads 4
```

**Parameters:**
- `-e 1000000` - E-value threshold (1000x more permissive than v1!)
- `--max-seqs 1000000` - Maximum sequences to return
- `--threads 4` - Use 4 threads
- No explicit `-s` (sensitivity) parameter → **uses default**

## Key Difference: E-value Threshold

| Parameter | v1.0 | v2.0 | Difference |
|-----------|------|------|------------|
| E-value (-e) | 1000 | 1000000 | v2.0 is 1000x MORE permissive |
| Max seqs (--max-seqs) | 1000000 | 1000000 | Same |
| Threads (--threads) | Not specified | 4 | Different (shouldn't affect results) |
| Sensitivity (-s) | Default | Default | Same |

**Paradox**: v2.0 uses a MORE permissive E-value (1000000 vs 1000) but finds FEWER hits (77 vs 161)!

## Prefiltering Analysis

From v2.0 Foldseek log (`validation_run/AF-A0A024R1R8-F1.foldseek.log`):

```
k-mer similarity threshold: 78
Starting prefiltering scores calculation (step 1 of 1)
Query db start 1 to 1
Target db start 1 to 63064
[=================================================================] 1 0s 0ms

0.453125 k-mers per position
3712 DB matches per sequence
0 overflows
77 sequences passed prefiltering per query sequence  ← KEY LINE
77 median result list length
0 sequences with 0 size result lists
```

**Critical finding**: Only **77 sequences passed prefiltering** out of 63,064 total ECOD domains

The prefilter uses k-mer matching (k=6) to quickly identify potential hits before doing expensive structural alignment. The prefilter is the bottleneck, NOT the E-value threshold.

## Hit Overlap Analysis

```bash
v1.0 hits:     161
v2.0 hits:      77
Common:         76 (47.2% of v1)
v1 only:        85 (52.8% missing in v2)
v2 only:         1 (new hit not in v1)
```

**v2.0 is missing 85 hits from v1.0** but found 1 new hit (000063491.pdb)

### Example Missing Hits

Sample of v1 hits NOT found by v2 (with E-values):

| ECOD Domain | E-value | Bit Score | Alignment Length |
|-------------|---------|-----------|------------------|
| 000008118.pdb | 2.591E+01 | 21 | 25 |
| 000006353.pdb | 5.909E+01 | 11 | 39 |
| 000000332.pdb | 5.909E+01 | 11 | 10 |
| 000006288.pdb | 8.155E+01 | 7 | 24 |
| 000156638.pdb | 9.533E+01 | 5 | 12 |
| 000041996.pdb | 1.273E+02 | 1 | 4 |
| 000162420.pdb | 1.273E+02 | 1 | 8 |
| 000148972.pdb | 1.357E+02 | 0 | 10 |

**Analysis**: Missing hits have E-values ranging from 25.9 to 170, all well below both thresholds (1000 and 1000000). They are being filtered out during **prefiltering**, not E-value filtering.

## Foldseek Version Information

From v2.0 log:
```
MMseqs Version: 10.941cd33
```

**Hypothesis**: v1.0 may have used an older Foldseek version with different default prefiltering parameters.

## Prefilter Parameters (v2.0 actual values)

From detailed log output:

```
Sensitivity: 9.5
k-mer length: 6
Target search mode: 0
k-score: seq:2147483647,prof:2147483647
Max results per query: 1000000
Diagonal scoring: true
Exact k-mer matching: 0
Minimum diagonal score: 30
Spaced k-mers: 1
```

**Key parameter**: `Sensitivity: 9.5` (default for Foldseek)

## Possible Causes

### 1. **Different Foldseek Version** (MOST LIKELY)
- v1.0 may have used older Foldseek with looser prefiltering
- Foldseek developers may have changed default sensitivity between versions
- **Evidence**: No way for us to verify v1.0 Foldseek version without logs

### 2. **Different Sensitivity Setting**
- v1.0 script doesn't explicitly set `-s` parameter
- Both use default, but defaults may have changed
- **Solution**: Try higher sensitivity in v2.0 (e.g., `-s 10` or `-s 11`)

### 3. **Database Differences**
- ECOD_foldseek_DB may have been updated between v1.0 and v2.0 runs
- **Evidence**: Database has 63,064 domains in v2.0 log

### 4. **Different PDB Input**
- v2.0 uses CIF → PDB conversion (via gemmi)
- v1.0 directly uses PDB files
- Coordinate differences could affect k-mer hashing
- **Unlikely**: Top hit matches perfectly, suggesting structure is identical

## Proposed Solutions

### Solution 1: Increase Sensitivity (RECOMMENDED)

Try running Foldseek with higher sensitivity:

```python
# In dpam/steps/step03_foldseek.py
foldseek.easy_search(
    query_pdb=pdb_file,
    database=database,
    output_file=output_file,
    tmp_dir=tmp_dir,
    threads=threads,
    evalue=1000000,
    max_seqs=1000000,
    sensitivity=10.0  # Add this parameter (higher = more sensitive)
)
```

Then update `dpam/tools/foldseek.py` to accept `sensitivity` parameter:

```python
def easy_search(
    self,
    query_pdb: Path,
    database: Path,
    output_file: Path,
    tmp_dir: Path,
    threads: int = 1,
    evalue: float = 1000000,
    max_seqs: int = 1000000,
    sensitivity: float = 9.5,  # Add parameter
    working_dir: Optional[Path] = None
) -> None:
    cmd = [
        self.executable,
        'easy-search',
        str(query_pdb),
        str(database),
        str(output_file),
        str(tmp_dir),
        '-e', str(evalue),
        '--max-seqs', str(max_seqs),
        '-s', str(sensitivity),  # Add to command
        '--threads', str(threads)
    ]
```

**Test values**: Try `-s 10.0`, `-s 11.0`, or `-s 12.0`

### Solution 2: Accept the Difference (Document as Known Issue)

If the 85 missing hits are:
- Low-quality alignments (short, low identity)
- Not critical for downstream DALI analysis
- An improvement (stricter quality control)

Then document as acceptable difference and update validation framework to allow some hit count variation.

### Solution 3: Contact v1.0 Authors for Exact Parameters

If possible, get the exact Foldseek version and parameters used in v1.0 production runs.

## Testing Plan

### Test 1: Sensitivity Sweep

Run v2.0 with different sensitivity values and compare hit counts:

```bash
for sens in 9.5 10.0 10.5 11.0 11.5 12.0; do
    echo "Testing sensitivity: $sens"
    foldseek easy-search \
        validation_run/AF-A0A024R1R8-F1.pdb \
        $DATA_DIR/ECOD_foldseek_DB \
        validation_run/foldseek_s${sens}.out \
        /tmp/foldseek_tmp \
        -e 1000000 \
        --max-seqs 1000000 \
        -s $sens \
        --threads 4
    wc -l validation_run/foldseek_s${sens}.out
done
```

**Expected**: Higher sensitivity → more prefilter hits → closer to v1.0's 161 hits

### Test 2: E-value Matching

Try using v1.0's exact E-value (1000 instead of 1000000):

```python
evalue=1000  # Match v1.0 exactly
```

**Expected**: Should not make a difference (current E-values of missing hits are all < 1000)

### Test 3: Compare Top Hits Quality

Check if the 76 common hits are the highest-quality ones:

```bash
# Get bit scores of v1 hits
awk '{print $2, $12}' v1_outputs/AF-A0A024R1R8-F1/A0A024R1R8.foldseek | \
    sort -k2 -nr > v1_sorted_by_bits.txt

# Compare with common hits
comm -12 <(sort v1_sorted_by_bits.txt) <(sort /tmp/v2_foldseek_hits.txt)
```

**Hypothesis**: v2.0 is finding the 76 best hits and filtering out 85 lower-quality hits

## Impact on Downstream Steps

### DALI Pipeline (Steps 6-8)

**Step 6 (DALI_CANDIDATES)**:
- Filters Foldseek hits by z-score
- Fewer input hits → fewer DALI candidates
- **Impact**: May miss some domain assignments

**Step 7 (ITERATIVE_DALI)**:
- Runs DALI on candidates
- Fewer candidates → less comprehensive search
- **Impact**: May miss some structural homologs

**Step 8 (ANALYZE_DALI)**:
- Filters DALI results
- Depends on step 7 completeness
- **Impact**: Fewer domain assignments

### Overall Pipeline Impact

**Best case**: Missing 85 hits are low-quality and don't contribute meaningful domain assignments
**Worst case**: Missing hits contain critical domain assignments, reducing coverage

## Recommendation

**Immediate action**: Test Solution 1 (increase sensitivity)

1. Add `sensitivity` parameter to `Foldseek.easy_search()`
2. Run sensitivity sweep (9.5 to 12.0)
3. Find sensitivity value that gives ~161 hits (matching v1.0)
4. Validate that hit quality is maintained (compare top hits)
5. If successful, update dpam_c2 to use optimal sensitivity

**If sensitivity doesn't help**:
- Contact v1.0 developers for exact Foldseek version and parameters
- Consider accepting difference as algorithm improvement
- Validate end-to-end pipeline on proteins with known domain annotations

## Files for Reference

**v1.0**:
- Script: `v1_scripts/step4_run_foldseek.py`
- Output: `v1_outputs/AF-A0A024R1R8-F1/A0A024R1R8.foldseek` (161 lines)

**v2.0**:
- Script: `dpam/steps/step03_foldseek.py`
- Tool wrapper: `dpam/tools/foldseek.py`
- Output: `validation_run/AF-A0A024R1R8-F1.foldseek` (77 lines)
- Log: `validation_run/AF-A0A024R1R8-F1.foldseek.log` (175 lines)

**Analysis**:
- v1 hits only: `/tmp/v1_foldseek_hits.txt` (sorted)
- v2 hits only: `/tmp/v2_foldseek_hits.txt` (sorted)
