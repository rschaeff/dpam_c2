# Step 7: Iterative DALI - Usage Guide

## ðŸš€ Quick Start

```bash
# Run step 7 as part of full pipeline
dpam run AF-P12345 \
  --working-dir ./work \
  --data-dir ./data \
  --steps PREPARE HHSEARCH FOLDSEEK FILTER_FOLDSEEK MAP_ECOD DALI_CANDIDATES ITERATIVE_DALI \
  --cpus 8

# Run step 7 only
dpam run-step AF-P12345 \
  --step ITERATIVE_DALI \
  --working-dir ./work \
  --data-dir ./data \
  --cpus 8
```

---

## âš¡ Command Options

### Basic Usage

```bash
python step07_iterative_dali.py <prefix> <working_dir> <data_dir> <cpus>
```

### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `prefix` | str | Structure prefix (e.g., AF-P12345) | Required |
| `working_dir` | Path | Working directory | Required |
| `data_dir` | Path | Data directory (contains ECOD70) | Required |
| `cpus` | int | Number of parallel workers | 1 |

### Examples

```bash
# Single CPU (slow, for testing)
python step07_iterative_dali.py AF-P12345 ./work ./data 1

# 8 CPUs (recommended for typical proteins)
python step07_iterative_dali.py AF-P12345 ./work ./data 8

# 16 CPUs (for large proteins or many candidates)
python step07_iterative_dali.py AF-P12345 ./work ./data 16
```

---

## ðŸ"‚ Required Files

### Prerequisites

**From previous steps:**
- `{prefix}.pdb` - Standardized structure (Step 1)
- `{prefix}_hits4Dali` - ECOD domain candidates (Step 6)

**In data directory:**
- `ECOD70/` - Directory containing ECOD template structures
  - `000000003.pdb`
  - `000000010.pdb`
  - ... (one file per ECOD domain)

### Check Prerequisites

```bash
# Verify input files
ls -lh work/AF-P12345.pdb
ls -lh work/AF-P12345_hits4Dali
wc -l work/AF-P12345_hits4Dali

# Verify ECOD70 directory
ls data/ECOD70/*.pdb | wc -l
# Should show ~70,000 files

# Check specific template
ls data/ECOD70/000000003.pdb
```

---

## ðŸ"Š Expected Output

### Output Files

| File | Size | Description |
|------|------|-------------|
| `{prefix}_iterativdDali_hits` | 1-50 MB | All DALI alignments |
| `{prefix}.iterativeDali.done` | <1 KB | Completion marker |

### Output Statistics

```bash
# Check output
ls -lh work/AF-P12345_iterativdDali_hits

# Count total hits
grep "^>" work/AF-P12345_iterativdDali_hits | wc -l
# Typical: 200-1000 hits

# Check hit quality
grep "^>" work/AF-P12345_iterativdDali_hits | \
  awk '{print $2}' | \
  sort -rn | \
  head -20
# Shows top 20 z-scores
```

### Output Format Example

```
>000000003_1    25.3    45  124 120
10  5
11  6
12  7
...
>000000003_2    18.7    32  79  120
50  40
51  41
...
>000000010_1    22.1    38  110 115
...
```

---

## âš™ï¸ Performance Tuning

### CPU Scaling

| Protein Size | Candidates | Recommended CPUs | Time |
|--------------|-----------|------------------|------|
| Small (<250 aa) | 100-300 | 4 | 1-2h |
| Medium (250-500 aa) | 200-500 | 8 | 1-3h |
| Large (500-1000 aa) | 400-800 | 16 | 2-4h |
| Very Large (>1000 aa) | 600-1200 | 32 | 3-6h |

### Resource Requirements

```bash
# Per CPU worker:
Memory: 1-2 GB
Disk: 2-5 GB (temporary)
Time: 5-15 minutes per domain (average)

# Total for 500-residue protein with 8 CPUs:
Memory: 8-16 GB
Disk: 20-40 GB
Time: 1-3 hours
```

### SLURM Example

```bash
#!/bin/bash
#SBATCH --job-name=dpam_step7
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=4:00:00
#SBATCH --partition=compute

# Load modules
module load dali

# Run step 7
dpam run-step AF-P12345 \
  --step ITERATIVE_DALI \
  --working-dir $WORK_DIR \
  --data-dir $DATA_DIR \
  --cpus $SLURM_CPUS_PER_TASK
```

---

## ðŸ›  Troubleshooting

### Problem: "DALI not found"

```bash
# Check if DALI is in PATH
which dali.pl

# If not found:
module load dali  # On HPC
# or
export PATH=/path/to/dali:$PATH
```

### Problem: "Template not found"

```bash
# Check ECOD70 directory
ls data/ECOD70/ | head

# Verify candidates are valid
head work/AF-P12345_hits4Dali

# Check specific template
ECOD=$(head -1 work/AF-P12345_hits4Dali)
ls data/ECOD70/${ECOD}.pdb
```

### Problem: Step 7 takes too long

```bash
# Check number of candidates
wc -l work/AF-P12345_hits4Dali

# If >600, this is expected for large proteins

# Monitor progress (in another terminal)
watch -n 30 'ls work/iterativeDali_AF-P12345/ | wc -l'

# Check CPU usage
htop  # or top
# Should see multiple dali.pl processes
```

### Problem: Out of memory

```bash
# Reduce parallel workers
dpam run-step AF-P12345 --step ITERATIVE_DALI --cpus 4
# Instead of --cpus 16

# Or request more memory (SLURM)
#SBATCH --mem-per-cpu=4G
```

### Problem: Out of disk space

```bash
# Check disk usage
df -h $PWD

# Use local scratch if available
export TMPDIR=/scratch/$USER
mkdir -p $TMPDIR

# Then run step 7
```

### Problem: Step 7 seems stuck

```bash
# Check if DALI processes are running
ps aux | grep dali.pl

# Check logs (if using SLURM)
tail -f slurm-*.out

# Check individual domain progress
ls work/iterativeDali_AF-P12345/*_hits | wc -l
# This should increase over time

# If truly stuck, may need to kill and restart
# (Future: implement timeout mechanism)
```

---

## ðŸ"Š Monitoring Progress

### Real-time Monitoring

```bash
# Watch completed domains
watch -n 30 'ls work/iterativeDali_AF-P12345/*_hits 2>/dev/null | wc -l'

# Check CPU utilization
htop
# Look for dali.pl processes

# Monitor disk I/O
iostat -x 5
```

### Post-Run Analysis

```bash
# Count total hits
grep "^>" work/AF-P12345_iterativdDali_hits | wc -l

# Hits per domain
grep "^>" work/AF-P12345_iterativdDali_hits | \
  cut -d'_' -f1 | \
  cut -d'>' -f2 | \
  sort | \
  uniq -c | \
  sort -rn | \
  head -10
# Shows domains with most iterations

# Z-score distribution
grep "^>" work/AF-P12345_iterativdDali_hits | \
  awk '{print $2}' | \
  sort -n | \
  awk '{
    sum+=$1; 
    array[NR]=$1
  } END {
    print "Count:", NR
    print "Mean:", sum/NR
    print "Median:", array[int(NR/2)]
    print "Max:", array[NR]
  }'
```

---

## ðŸ"„ Resume After Failure

If step 7 is interrupted:

```bash
# Check if partially complete
ls work/AF-P12345.iterativeDali.done
# If exists: step completed
# If not: step incomplete

# Check partial output
ls work/AF-P12345_iterativdDali_hits
# May exist but be incomplete

# To resume:
# 1. Remove partial output
rm -f work/AF-P12345_iterativdDali_hits
rm -f work/AF-P12345.iterativeDali.done

# 2. Clean up temporary files
rm -rf work/iterativeDali_AF-P12345/

# 3. Rerun
dpam run-step AF-P12345 --step ITERATIVE_DALI --cpus 8
```

**Note:** Step 7 currently does not support partial resume (reprocesses all domains). This is a future enhancement.

---

## âœ… Validation

### Check Output Quality

```bash
# 1. File exists
test -f work/AF-P12345_iterativdDali_hits && echo "âœ… Output exists"

# 2. Has hits
NHITS=$(grep "^>" work/AF-P12345_iterativdDali_hits | wc -l)
if [ $NHITS -gt 0 ]; then
  echo "âœ… Found $NHITS hits"
else
  echo "❌ No hits found"
fi

# 3. Format is valid
grep "^>" work/AF-P12345_iterativdDali_hits | head -1
# Should match: >XXXXXXXXX_N<TAB>Z<TAB>N<TAB>QL<TAB>TL

# 4. Alignments present
HEAD_LINES=$(grep "^>" work/AF-P12345_iterativdDali_hits | wc -l)
TOTAL_LINES=$(wc -l < work/AF-P12345_iterativdDali_hits)
if [ $TOTAL_LINES -gt $HEAD_LINES ]; then
  echo "âœ… Alignments present"
else
  echo "❌ No alignment data"
fi

# 5. Done marker
test -f work/AF-P12345.iterativeDali.done && echo "âœ… Step marked complete"
```

### Compare with v1.0 (if available)

```bash
# Compare hit counts
HITS_V1=$(grep "^>" work_v1/AF-P12345_iterativdDali_hits | wc -l)
HITS_V2=$(grep "^>" work/AF-P12345_iterativdDali_hits | wc -l)
echo "v1.0: $HITS_V1 hits"
echo "v2.0: $HITS_V2 hits"

# Should be identical or very close
# Small differences possible due to:
# - Floating point rounding
# - DALI version differences
# - Random tie-breaking
```

---

## ðŸ"š Next Steps

After Step 7 completes:

```bash
# Proceed to Step 8: Analyze DALI
dpam run-step AF-P12345 \
  --step ANALYZE_DALI \
  --working-dir ./work \
  --data-dir ./data

# Or run remaining steps
dpam run AF-P12345 \
  --working-dir ./work \
  --data-dir ./data \
  --steps ANALYZE_DALI GET_SUPPORT FILTER_DOMAINS SSE DISORDER PARSE_DOMAINS \
  --cpus 4
```

---

## ðŸ" Example Session

```bash
# 1. Setup
export WORK_DIR=./work
export DATA_DIR=./data/ecod
PREFIX=AF-P12345

# 2. Check prerequisites
ls $WORK_DIR/${PREFIX}.pdb
ls $WORK_DIR/${PREFIX}_hits4Dali
wc -l $WORK_DIR/${PREFIX}_hits4Dali
# Shows 423 candidates

# 3. Run step 7
dpam run-step $PREFIX \
  --step ITERATIVE_DALI \
  --working-dir $WORK_DIR \
  --data-dir $DATA_DIR \
  --cpus 8

# Output:
# [INFO] Starting Step 7: Iterative DALI for AF-P12345
# [INFO] Processing 423 ECOD domains with 8 CPUs
# [INFO] Completed DALI for 418/423 domains
# [INFO] Wrote combined hits to AF-P12345_iterativdDali_hits
# [INFO] Step 7 completed successfully

# 4. Check results
ls -lh $WORK_DIR/${PREFIX}_iterativdDali_hits
# 3.2M

grep "^>" $WORK_DIR/${PREFIX}_iterativdDali_hits | wc -l
# 867 hits

# 5. View sample hits
head -20 $WORK_DIR/${PREFIX}_iterativdDali_hits

# 6. Statistics
grep "^>" $WORK_DIR/${PREFIX}_iterativdDali_hits | \
  awk '{print $2}' | \
  sort -rn | \
  head -10
# Top z-scores:
# 45.2
# 38.7
# 35.1
# ...

# 7. Proceed to step 8
dpam run-step $PREFIX --step ANALYZE_DALI ...
```

---

## ðŸ'¡ Tips & Best Practices

1. **Start with fewer CPUs** for testing:
   ```bash
   # Test with 1-2 CPUs first
   dpam run-step AF-P12345 --step ITERATIVE_DALI --cpus 2
   ```

2. **Monitor the first few domains**:
   ```bash
   # Watch progress
   watch -n 10 'ls work/iterativeDali_AF-P12345/*_hits | wc -l'
   ```

3. **Use local scratch for I/O**:
   ```bash
   export TMPDIR=/scratch/$USER
   ```

4. **Check DALI availability before submitting large batches**:
   ```bash
   which dali.pl || echo "DALI not found!"
   ```

5. **For large proteins (>1000 residues)**:
   - Expect 600+ candidates
   - Request 16-32 CPUs
   - Allow 4-6 hours

6. **If disk space is limited**:
   - Process in batches (future enhancement)
   - Clean up immediately after each domain
   - Use streaming concatenation

---

**Last Updated:** 2025-10-06  
**Status:** Production-ready  
**Next:** Step 8 (Analyze DALI)
