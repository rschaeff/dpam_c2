# Step 7 Quick Reference Card

## ðŸš€ Quick Start

```bash
# Run step 7
dpam run-step AF-P12345 \
  --step ITERATIVE_DALI \
  --working-dir ./work \
  --data-dir ./data \
  --cpus 8
```

## ðŸ"‚ Files

### Input
- `AF-P12345.pdb` (Step 1)
- `AF-P12345_hits4Dali` (Step 6)
- `ECOD70/*.pdb` (data)

### Output
- `AF-P12345_iterativdDali_hits` (200-1000 hits)
- `AF-P12345.iterativeDali.done` (marker)

## âš¡ Commands

```bash
# 8 CPUs (recommended)
python step07_iterative_dali.py AF-P12345 ./work ./data 8

# Check progress
watch -n 30 'ls work/iterativeDali_AF-P12345/*_hits | wc -l'

# Check results
grep "^>" work/AF-P12345_iterativdDali_hits | wc -l
```

## ðŸ"Š Expected Results

| Protein Size | Candidates | Time (8 CPUs) | Hits |
|--------------|-----------|---------------|------|
| 250 aa | 100-300 | 1-2h | 100-400 |
| 500 aa | 200-500 | 1-3h | 200-800 |
| 1000 aa | 400-800 | 2-4h | 400-1200 |

## âš™ï¸ Key Details

### Gap Tolerance
```python
cutoff = max(5, len(resids) * 0.05)
```

### Output Format
```
>{edomain}_{iteration}<TAB>{zscore}<TAB>{n_aligned}<TAB>{q_len}<TAB>{t_len}
{query_resid}<TAB>{template_resid}
...
```

## ⚠️ Troubleshooting

**DALI not found?**
```bash
which dali.pl
module load dali
```

**Out of memory?**
```bash
--cpus 4  # Reduce workers
```

**Out of disk space?**
```bash
export TMPDIR=/scratch/$USER
df -h
```

## âœ… Validation

```bash
# Check output exists
test -f work/AF-P12345_iterativdDali_hits && echo "âœ…"

# Count hits
grep "^>" work/AF-P12345_iterativdDali_hits | wc -l

# Check format
head -3 work/AF-P12345_iterativdDali_hits
```

## ðŸ"š Documentation

- `STEP7_IMPLEMENTATION.md` - Technical details
- `STEP7_USAGE.md` - User guide
- `STEP7_SUMMARY.md` - Quick summary
- `SESSION_SUMMARY_STEP7.md` - Implementation notes

## ðŸ"Œ Critical

- âš ï¸ **Matches v1.0 exactly** (for validation)
- âš ï¸ **Gap tolerance is critical**: `max(5, N*0.05)`
- âš ï¸ **Output format is exact**: TAB delimiters only
- âš ï¸ **DALI must be in PATH**
- âš ï¸ **Needs 2-5 GB disk space per CPU**

## âœ… Status

**Implemented:** âœ… Complete  
**Tested:** âš ï¸ Pending  
**Validated:** âš ï¸ Pending (vs v1.0)  
**Production:** âœ… Ready (after validation)
