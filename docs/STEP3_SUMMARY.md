# Step 3: Foldseek Structure Search - Quick Reference

## Purpose

Run structure similarity search against ECOD database using Foldseek. Identifies structural homologs based on 3D structure comparison, complementing sequence-based HHsearch results.

---

## Quick Reference

**Command:**
```bash
dpam run-step PREFIX --step FOLDSEEK \
    --working-dir ./work \
    --data-dir /path/to/ecod_data \
    --cpus 8
```

**Input Files:**
```
{prefix}.pdb             # Standardized PDB structure (from Step 1)
```

**Output Files:**
```
{prefix}.foldseek        # Foldseek hit results (tab-separated)
{prefix}.foldseek.log    # Foldseek execution log
```

**Reference Data:**
```
ECOD_foldseek_DB         # Pre-built Foldseek database of ECOD domains
```

---

## Algorithm

1. Initialize Foldseek wrapper
2. Verify input PDB and database exist
3. Create unique temporary directory (`foldseek_tmp_{prefix}/`)
4. Run `foldseek easy-search` with permissive parameters:
   - E-value threshold: 1,000,000 (very permissive)
   - Max sequences: 1,000,000 (capture all potential hits)
5. Parse output to count hits
6. Clean up temporary directory

---

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `threads` | 1 | Number of threads for Foldseek |
| `evalue` | 1000000 | E-value threshold (permissive) |
| `max_seqs` | 1000000 | Maximum number of hits to return |

---

## Output Format

### Foldseek Results ({prefix}.foldseek)

Tab-separated format with alignment statistics:

```
query   target           pident  alnlen  mismatch  gapopen  qstart  qend  tstart  tend  evalue    bits
AF-P12345   e4ub3A1      0.85    145     12        2        1       147   1       145   1.2e-50   180.5
AF-P12345   e1234B2      0.72    110     25        3        20      128   45      153   3.4e-30   120.3
```

**Key Fields:**
| Column | Description |
|--------|-------------|
| `query` | Query structure ID |
| `target` | ECOD domain ID (e.g., e4ub3A1) |
| `pident` | Percent identity (0-1) |
| `alnlen` | Alignment length |
| `qstart/qend` | Query residue range |
| `tstart/tend` | Template residue range |
| `evalue` | E-value score |
| `bits` | Bit score |

---

## SLURM Compatibility

**Critical:** Foldseek fails when `OMP_PROC_BIND` is set (SLURM default).

Error message:
```
Calling program has OMP_PROC_BIND set in its environment. Please unset OMP_PROC_BIND.
```

**Solution:** The implementation automatically handles this by running Foldseek with:
```bash
env OMP_PROC_BIND=false foldseek easy-search ...
```

This tells OpenMP to disable thread binding, bypassing the check.

---

## Performance

| Metric | Typical Value | Notes |
|--------|---------------|-------|
| Runtime | 30 seconds - 2 minutes | Much faster than HHsearch |
| Memory | 2-4 GB | Scales with database size |
| Disk I/O | Moderate | Uses temporary files |

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| PDB file not found | Step 1 incomplete | Run Step 1 first |
| Foldseek database not found | Missing ECOD_foldseek_DB | Check `--data-dir` path |
| OMP_PROC_BIND error | SLURM environment | Handled automatically by wrapper |
| Empty output | No structural matches | Normal for novel folds |

---

## Dependencies

**External Tools:**
- `foldseek` - Structure similarity search tool

**Python Libraries:**
- Standard library only (subprocess, shutil)

---

## Temporary Files

Foldseek creates intermediate files during search:
```
foldseek_tmp_{prefix}/
├── query.idx
├── query.dbtype
└── ... (other index files)
```

These are automatically cleaned up after successful completion.

---

## Comparison with HHsearch (Step 2)

| Aspect | HHsearch | Foldseek |
|--------|----------|----------|
| Method | Sequence homology (HMM) | Structure similarity (3Di) |
| Speed | 30-60 minutes | 30 seconds - 2 minutes |
| Sensitivity | High for remote homologs | High for structural analogs |
| False positives | Lower | Higher (hence filtering in Step 4) |
| Complementarity | Evolutionary relationships | Structural convergence |

Both methods are used together to maximize coverage of ECOD domain assignments.

---

## Backward Compatibility

Matches v1.0 Foldseek step:
- Same database (ECOD_foldseek_DB)
- Same output format (default Foldseek tabular)
- Compatible with Step 4 filtering
