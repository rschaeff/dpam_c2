# Step 8 Usage Guide: Analyze DALI Results

**Purpose:** Enrich DALI structural alignments with quality scores and rankings

**Input:** `{prefix}_iterativdDali_hits` (from Step 7)
**Output:** `{prefix}_good_hits` (analyzed hits with scores)
**Time:** 5-10 seconds typical

---

## Quick Start

### Run Step 8 Standalone

```bash
dpam run-step AF-P12345 \
  --step ANALYZE_DALI \
  --working-dir ./work \
  --data-dir ./data
```

### Run Full Pipeline Through Step 8

```bash
dpam run AF-P12345 \
  --working-dir ./work \
  --data-dir ./data \
  --steps PREPARE HHSEARCH FOLDSEEK FILTER_FOLDSEEK \
          MAP_ECOD DALI_CANDIDATES ITERATIVE_DALI ANALYZE_DALI \
  --cpus 8 \
  --resume
```

---

## Input Requirements

### Required Files

1. **{prefix}_iterativdDali_hits**
   - From Step 7 (Iterative DALI)
   - Contains structural alignments
   - Location: `working_dir/`

2. **ecod.latest.domains**
   - ECOD metadata
   - Location: `data_dir/`

### Optional Reference Data

3. **ecod_weights/{ecodnum}.weight**
   - Position conservation weights
   - Location: `data_dir/ecod_weights/`
   - If missing: q-score = -1

4. **ecod_domain_info/{ecodnum}.info**
   - Historical z-scores and q-scores
   - Location: `data_dir/ecod_domain_info/`
   - If missing: percentiles = -1

---

## Output Format

### File: `{prefix}_good_hits`

Tab-delimited file with header:

```
hitname	ecodnum	ecodkey	hgroup	zscore	qscore	ztile	qtile	rank	qrange	erange
000000003_1	000000003	e2rspA1	1.1	25.3	0.85	0.12	0.05	1.2	10-120	1-118
000000010_2	000000010	e3dkrA1	2.3	23.1	0.78	0.18	0.10	2.5	15-125	5-115
...
```

### Columns Explained

| Column | Description | Example | Range |
|--------|-------------|---------|-------|
| `hitname` | DALI hit identifier | `000000003_1` | String |
| `ecodnum` | ECOD domain number | `000000003` | String |
| `ecodkey` | ECOD domain ID | `e2rspA1` | String |
| `hgroup` | ECOD family (2 levels) | `1.1` | String |
| `zscore` | DALI z-score | `25.3` | Float |
| `qscore` | Weighted alignment score | `0.85` | 0-1 or -1 |
| `ztile` | Z-score percentile | `0.12` | 0-1 or -1 |
| `qtile` | Q-score percentile | `0.05` | 0-1 or -1 |
| `rank` | Avg position rank | `1.2` | ≥1.0 |
| `qrange` | Query alignment range | `10-120` | Range string |
| `erange` | Template alignment range | `1-118` | Range string |

---

## Understanding the Scores

### Z-Score (from DALI)

- **What it is:** DALI structural similarity score
- **Higher is better:** More significant structural match
- **Typical range:** 2-40 (varies by protein size)
- **Example:**
  - zscore > 20: Very strong hit
  - zscore 10-20: Good hit
  - zscore 5-10: Weak hit
  - zscore < 5: Very weak hit

### Q-Score (Weighted Alignment)

- **What it is:** Fraction of conserved positions aligned
- **Calculation:** Sum of position weights / total weight
- **Range:** 0.0 to 1.0 (or -1 if weights unavailable)
- **Higher is better:** More conserved positions aligned
- **Example:**
  - qscore > 0.8: Excellent coverage of conserved positions
  - qscore 0.5-0.8: Good coverage
  - qscore < 0.5: Poor coverage
  - qscore = -1: No weight data available

### Z-Tile (Z-Score Percentile)

- **What it is:** Fraction of historical hits with HIGHER z-score
- **Lower is better:** Fewer hits scored higher
- **Range:** 0.0 to 1.0 (or -1 if info unavailable)
- **Example:**
  - ztile = 0.05: Top 5% of historical hits
  - ztile = 0.50: Median historical hit
  - ztile = 0.95: Bottom 5% of historical hits
  - ztile = -1: No historical data

### Q-Tile (Q-Score Percentile)

- **What it is:** Fraction of historical hits with HIGHER q-score
- **Lower is better:** Fewer hits scored higher
- **Range:** 0.0 to 1.0 (or -1 if info unavailable)
- **Interpretation:** Same as z-tile but for q-scores

### Rank (Position Family Diversity)

- **What it is:** Average number of families at aligned positions
- **Calculation:** Mean of family counts per position
- **Range:** ≥ 1.0
- **Lower is better:** Less competition from other families
- **Example:**
  - rank = 1.0: Unique family at all positions
  - rank = 2.0: Average of 2 families per position
  - rank = 5.0: Highly competitive (many families)

### Ranges

- **qrange:** Query protein alignment range
- **erange:** Template (ECOD domain) alignment range
- **Format:** "10-20,25-30" (comma-separated segments)

---

## Typical Output Statistics

### 500-Residue Protein

```bash
# Count total hits
grep -v "^hitname" work/AF-P12345_good_hits | wc -l
# Expected: 200-600 hits

# Distribution of scores
cut -f5 work/AF-P12345_good_hits | tail -n +2 | sort -rn | head -20
# Top z-scores: 20-40 typical

# Count hits with weights
awk '$6 != -1' work/AF-P12345_good_hits | wc -l
# Expected: 50-80% of hits

# Count hits with info
awk '$7 != -1' work/AF-P12345_good_hits | wc -l
# Expected: 50-80% of hits
```

### Quality Indicators

**Good run:**
- 200+ hits analyzed
- 50%+ have q-scores (not -1)
- 50%+ have percentiles (not -1)
- Top z-scores > 15

**Problematic run:**
- <50 hits analyzed → Step 7 may have failed
- All q-scores = -1 → Missing weight data
- All percentiles = -1 → Missing historical data

---

## Common Workflows

### Inspect Top Hits

```bash
# Top 10 hits by z-score
head -11 work/AF-P12345_good_hits | column -t

# Top hits with low percentiles (best quality)
awk 'NR==1 || ($7 != -1 && $7 < 0.1)' work/AF-P12345_good_hits | column -t

# Unique families in top 20
head -21 work/AF-P12345_good_hits | tail -20 | cut -f4 | sort -u
```

### Filter by Quality

```bash
# High-quality hits (z>15, qtile<0.2)
awk 'NR==1 || ($5>15 && $8<0.2 && $8!=-1)' work/AF-P12345_good_hits > high_quality.txt

# Low-rank hits (unique families)
awk 'NR==1 || $9<2' work/AF-P12345_good_hits > unique_families.txt
```

### Export for Analysis

```bash
# Convert to CSV
cat work/AF-P12345_good_hits | tr '\t' ',' > AF-P12345_good_hits.csv

# Extract specific columns
cut -f1,4,5,6,7,8,9 work/AF-P12345_good_hits > scores_only.txt
```

---

## Troubleshooting

### No Output File Created

**Symptom:** `{prefix}_good_hits` doesn't exist

**Check:**
```bash
ls work/*_iterativdDali_hits
```

**Solution:**
- Run Step 7 first
- Check Step 7 completed successfully
- Look for errors in logs

### Empty Output File (Header Only)

**Symptom:** File exists but has only header line

**Check:**
```bash
wc -l work/*_iterativdDali_hits
```

**Causes:**
- Step 7 found no hits (normal for some proteins)
- All hits filtered out (rare)

**Action:**
- Review Step 7 output
- May be normal for small/unusual proteins

### All Q-Scores are -1

**Symptom:** Column 6 is all -1

**Check:**
```bash
ls data/ecod_weights/ | wc -l
```

**Solution:**
- Download ECOD weight files
- Or accept -1 values (q-score optional)

### All Percentiles are -1

**Symptom:** Columns 7 and 8 are all -1

**Check:**
```bash
ls data/ecod_domain_info/ | wc -l
```

**Solution:**
- Download ECOD domain info files
- Or accept -1 values (percentiles optional)

### Very Few Hits

**Symptom:** <50 hits in output

**Check:**
```bash
grep ">" work/*_iterativdDali_hits | wc -l
```

**Causes:**
- Step 7 stringent filtering (normal)
- Small protein (fewer candidates)
- Unusual structure (few matches)

**Action:**
- Usually normal
- Review Step 7 settings if concerned

### Unexpected ECOD Numbers

**Symptom:** Warning "ECOD number X not found in metadata"

**Check:**
```bash
grep "^${ecodnum}" data/ecod.latest.domains
```

**Causes:**
- Outdated ECOD database
- Template database mismatch

**Solution:**
- Update ecod.latest.domains
- Ensure ECOD70 and metadata are synchronized

---

## Performance Tuning

### Typical Performance

**500-residue protein:**
- Parse hits: <1s
- Load reference: 1-2s
- Calculate scores: 1-2s
- Calculate ranks: <1s
- Write output: <1s
- **Total: 5-10s**

### No Tuning Needed

Step 8 is already very fast. No optimization needed.

### Batch Processing

For processing many structures:

```bash
# Process batch
dpam batch prefixes.txt \
  --working-dir ./work \
  --data-dir ./data \
  --steps PREPARE HHSEARCH FOLDSEEK FILTER_FOLDSEEK \
          MAP_ECOD DALI_CANDIDATES ITERATIVE_DALI ANALYZE_DALI \
  --cpus 8 \
  --parallel 4 \
  --resume
```

**Tips:**
- Reference data loaded once per structure
- No parallelization within step 8
- Bottleneck is Step 2 and Step 7, not Step 8

---

## Integration with Pipeline

### Upstream Dependencies

**Step 7 (Iterative DALI):**
- Provides: `{prefix}_iterativdDali_hits`
- Must complete successfully
- Step 8 will create empty output if Step 7 has no hits

**Reference Data:**
- ecod.latest.domains (required)
- ecod_weights/* (optional, improves q-scores)
- ecod_domain_info/* (optional, enables percentiles)

### Downstream Usage

**Step 9 (Get Support):**
- Reads: `{prefix}_good_hits`
- Uses: z-scores, q-scores, ranges
- Integrates with sequence evidence

**Step 10 (Filter Domains):**
- Reads: Output from Step 9 (which uses Step 8 output)
- Filters by: z-scores, percentiles, ranks

---

## Python API

### Basic Usage

```python
from pathlib import Path
from dpam.steps.step08_analyze_dali import run_step8
from dpam.io.reference_data import load_ecod_data

# Setup
working_dir = Path("./work")
data_dir = Path("./data")

# Load reference data
reference_data = load_ecod_data(data_dir)

# Run step 8
success = run_step8(
    prefix="AF-P12345",
    working_dir=working_dir,
    reference_data=reference_data,
    data_dir=data_dir
)

print(f"Step 8 {'succeeded' if success else 'failed'}")
```

### Read Output

```python
import pandas as pd

# Load results
hits = pd.read_csv(
    "work/AF-P12345_good_hits",
    sep='\t'
)

# Filter high-quality hits
good_hits = hits[
    (hits['zscore'] > 15) &
    (hits['qtile'] < 0.2) &
    (hits['qtile'] != -1)
]

print(f"Found {len(good_hits)} high-quality hits")
```

### Parse Manually

```python
from pathlib import Path

def read_good_hits(prefix: str, working_dir: Path):
    hits_file = working_dir / f'{prefix}_good_hits'

    hits = []
    with open(hits_file, 'r') as f:
        header = f.readline()  # Skip header

        for line in f:
            fields = line.strip().split('\t')
            hit = {
                'hitname': fields[0],
                'ecodnum': fields[1],
                'ecodkey': fields[2],
                'hgroup': fields[3],
                'zscore': float(fields[4]),
                'qscore': float(fields[5]),
                'ztile': float(fields[6]),
                'qtile': float(fields[7]),
                'rank': float(fields[8]),
                'qrange': fields[9],
                'erange': fields[10]
            }
            hits.append(hit)

    return hits

# Usage
hits = read_good_hits("AF-P12345", Path("./work"))
print(f"Loaded {len(hits)} hits")
```

---

## Examples

### Example 1: Human Protein

```bash
# Run through step 8
dpam run AF-P12345 \
  --working-dir ./work \
  --data-dir ./data \
  --steps PREPARE HHSEARCH FOLDSEEK FILTER_FOLDSEEK \
          MAP_ECOD DALI_CANDIDATES ITERATIVE_DALI ANALYZE_DALI \
  --cpus 8

# Check output
wc -l work/AF-P12345_good_hits
# Output: 401 work/AF-P12345_good_hits (400 hits + header)

# Top 5 hits
head -6 work/AF-P12345_good_hits | column -t

# Distribution
cut -f5 work/AF-P12345_good_hits | tail -n +2 | \
  awk '{print int($1/5)*5}' | sort -n | uniq -c
```

### Example 2: Small Protein (200 residues)

```bash
# Smaller proteins have fewer hits
dpam run-step AF-Q9Y6K9 \
  --step ANALYZE_DALI \
  --working-dir ./work \
  --data-dir ./data

# Check
wc -l work/AF-Q9Y6K9_good_hits
# Output: 151 work/AF-Q9Y6K9_good_hits (150 hits)

# Still plenty for analysis
```

### Example 3: Batch Processing

```bash
# Create prefix list
cat > prefixes.txt << EOF
AF-P12345
AF-Q9Y6K9
AF-P53814
EOF

# Process batch through step 8
dpam batch prefixes.txt \
  --working-dir ./work \
  --data-dir ./data \
  --cpus 8 \
  --parallel 2

# Check all outputs
ls work/*_good_hits
```

---

## Summary

**Step 8** enriches DALI hits with quality metrics:

- **Fast:** 5-10 seconds typical
- **Comprehensive:** 11 fields per hit
- **Robust:** Handles missing reference data gracefully
- **Essential:** Required for downstream filtering

**Key Outputs:**
- Z-scores and Q-scores
- Percentiles vs historical data
- Position ranks
- Alignment ranges

**Next Steps:**
- Step 9: Integrate with sequence evidence
- Step 10: Filter by quality thresholds
