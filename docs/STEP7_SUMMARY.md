# Step 7: Iterative DALI Structural Alignment - Quick Reference

## Purpose

Run iterative DALI structural alignment against ECOD domain candidates from Step 6. Each candidate is aligned repeatedly, removing matched residues between iterations, to capture multi-domain coverage. Uses multiprocessing for parallelism.

---

## Quick Reference

**Command:**
```bash
dpam run-step PREFIX --step ITERATIVE_DALI \
    --working-dir ./work \
    --data-dir /path/to/ecod_data \
    --cpus 8

# With local scratch I/O (recommended on SLURM)
dpam run-step PREFIX --step ITERATIVE_DALI \
    --working-dir ./work \
    --data-dir /path/to/ecod_data \
    --cpus 8 \
    --scratch-dir /tmp \
    --dali-workers 32
```

**Input Files:**
```
{prefix}_hits4Dali          # ECOD domain candidates (from Step 6)
{prefix}.pdb                # Standardized PDB structure (from Step 1)
ECOD70/{edomain}.pdb        # ECOD template PDB files (reference data)
```

**Output Files:**
```
{prefix}_iterativdDali_hits  # Concatenated DALI hit results (note: "iterativd" typo preserved from v1.0)
```

---

## Algorithm

1. Read candidate ECOD domains from `{prefix}_hits4Dali`
2. Create temporary directory `iterativeDali_{prefix}/`
3. Process each candidate in parallel via `multiprocessing.Pool`:
   a. Copy query PDB to temp working directory
   b. Run DALI alignment against ECOD template
   c. Parse alignment: extract matched residues, z-score, alignment length
   d. If alignment >= 20 residues:
      - Record hit with residue mapping
      - Remove matched residues from query PDB (expand by gap tolerance)
      - Repeat from (b) with reduced PDB
   e. Stop when alignment < 20 residues or < 20 residues remain
4. Concatenate per-domain hit files into final output
5. Clean up temporary directories

**Gap tolerance formula (v1.0-exact):**
```python
cutoff = max(5, len(resids) * 0.05)
```

---

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cpus` | 1 | Worker processes for multiprocessing.Pool |
| `template_cache` | None | Shared directory of pre-cached ECOD template PDBs |
| `scratch_dir` | None | Local scratch for DALI temp I/O (e.g., `/tmp`) |
| `dali_workers` | None | Override worker count (default: `cpus`). Set higher than `cpus` for I/O-bound oversubscription |
| `path_resolver` | None | Optional PathResolver for sharded output layout |

---

## Key Functions

```python
def get_domain_range(resids: List[int]) -> str
    # Convert residue list to range string with v1.0 gap tolerance.

def run_dali(args: Tuple) -> bool
    # Worker function for Pool.map(). Processes single ECOD domain.
    # args: (prefix, edomain, working_dir, data_dir, template_cache, scratch_base)

def run_step7(prefix, working_dir, data_dir, cpus=1,
              template_cache=None, scratch_dir=None, dali_workers=None,
              path_resolver=None) -> bool
    # Main orchestration function.
    # path_resolver: Optional PathResolver for sharded output layout.
```

---

## Output Format

### Hit File ({prefix}_iterativdDali_hits)

Tab-delimited with header lines per hit:

```
>{edomain}_{iteration}<TAB>{zscore}<TAB>{n_aligned}<TAB>{q_len}<TAB>{t_len}
{query_resid}<TAB>{template_resid}
{query_resid}<TAB>{template_resid}
...
```

**Header fields:**
| Field | Description |
|-------|-------------|
| `edomain` | ECOD domain ID (e.g., e4ub3A1) |
| `iteration` | Iteration number (1-based) |
| `zscore` | DALI Z-score |
| `n_aligned` | Number of aligned residues |
| `q_len` | Query length at this iteration |
| `t_len` | Template length (0 in v1.0) |

---

## Batch Mode

For multi-protein runs via `dpam batch-run`, Step 7 uses two optimizations:

### Template Caching
- `BatchRunner._run_dali_batch()` scans all proteins' `_hits4Dali` files
- Copies unique ECOD template PDBs to a shared cache directory
- Each protein's `run_step7()` reads templates from cache instead of ECOD70/
- Savings depend on template overlap between proteins (~1% for 3 proteins, more for larger batches)

### Local Scratch I/O
- DALI generates 20-50 file operations per candidate domain
- A typical protein with ~200 candidates = 4,000-10,000 NFS operations
- `--scratch-dir` redirects DALI temp I/O to local disk (e.g., `/tmp`)
- Hit files remain on NFS for orchestrator reads
- Workers populate a local template cache via atomic rename on first access
- Per-protein scratch cleaned up in `finally` block

---

## Performance

### NFS vs Local Scratch

| Mode | Workers | Typical Time (500-res protein) |
|------|---------|-------------------------------|
| NFS only | 8 CPUs | ~1.4 hours |
| Local scratch | 8 CPUs + 32 workers | Estimated 5-15x faster |

### Scaling

```
Total time ~ N_domains x N_iterations x T_dali / N_workers

Bottleneck: DALI execution (I/O-bound, not CPU-bound)
Parallelization: Domain-level (embarrassingly parallel)
Speedup: Near-linear up to 8-16 CPUs on NFS; higher with local scratch
```

### Resource Requirements

| Resource | Per Worker | Total (8 CPUs) |
|----------|-----------|----------------|
| Memory | 1-2 GB | 8-16 GB |
| Disk (temp) | 2-5 GB | 16-40 GB |
| Disk (output) | - | 5-50 MB |

---

## Backward Compatibility

100% v1.0 compatible:
- Gap tolerance formula: `max(5, N*0.05)` (exact)
- Minimum alignment: 20 residues (exact)
- Minimum remaining: 20 residues (exact)
- TAB delimiters (exact)
- Iteration numbering: 1-based (exact)
- File naming: `_iterativdDali_hits` (typo preserved)
- Output format: character-by-character match

---

## Common Issues

| Error | Cause | Resolution |
|-------|-------|------------|
| `_hits4Dali` not found | Step 6 incomplete | Run Step 6 first |
| DALI hangs | Template too large or DALI bug | Kill and re-run; consider timeout |
| OMP_PROC_BIND error | SLURM environment | Unset before running |
| High disk I/O | Many temp files on NFS | Use `--scratch-dir /tmp` |
| Memory exhaustion | Too many parallel workers | Reduce `--cpus` or `--dali-workers` |

---

## Dependencies

**External Tools:**
- `dali.pl` (from DaliLite.v5) - Structural alignment
- `dsspcmbi` or `mkdssp` - Secondary structure assignment (used by DALI)

**Python Libraries:**
- `multiprocessing` (standard library)
- `shutil`, `subprocess` (standard library)
