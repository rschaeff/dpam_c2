# Step 2: HHsearch - Quick Reference

## Purpose

Run sequence homology search to find ECOD domain templates. Executes a four-stage pipeline: hhblits (MSA building) -> addss (secondary structure) -> hhmake (HMM building) -> hhsearch (database search).

---

## Quick Reference

**Command:**
```bash
dpam run-step PREFIX --step HHSEARCH \
    --working-dir ./work \
    --data-dir /path/to/ecod_data \
    --cpus 8
```

**Input Files:**
```
{prefix}.fa              # FASTA sequence (from Step 1)
```

**Output Files:**
```
{prefix}.a3m             # Multiple sequence alignment
{prefix}.hmm             # Hidden Markov Model
{prefix}.hhsearch        # HHsearch results (hit list)
{prefix}.hhblits.log     # hhblits execution log
```

**Reference Data:**
```
UniRef30_2022_02/        # UniRef database for hhblits
pdb70/                   # PDB70 database for hhsearch
```

---

## Algorithm

### Stage 1: MSA Building (hhblits)

1. Run hhblits against UniRef30 database
2. Build multiple sequence alignment (A3M format)
3. Captures evolutionary information from homologs

### Stage 2: Secondary Structure (addss.pl)

1. Run PSIPRED secondary structure prediction
2. Add SS annotation to A3M file
3. Improves alignment quality in hhsearch
4. **Optional:** Can be skipped with `--skip-addss` if PSIPRED unavailable

### Stage 3: HMM Building (hhmake)

1. Convert A3M alignment to HMM profile
2. Creates position-specific scoring matrix
3. Captures amino acid preferences at each position

### Stage 4: Database Search (hhsearch)

1. Search HMM against PDB70 database
2. Score alignments using HMM-HMM comparison
3. Return ranked list of template hits
4. Configured for permissive output (-Z 100000 -B 100000)

---

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cpus` | 1 | Number of CPUs for hhblits/hhsearch |
| `skip_addss` | False | Skip secondary structure prediction |
| `uniref_db` | Auto | Direct path to UniRef database |
| `pdb70_db` | Auto | Direct path to PDB70 database |
| `path_resolver` | None | Optional `PathResolver` for sharded output layout |

---

## Output Format

### HHsearch Results ({prefix}.hhsearch)

```
Query         {prefix}
Match_columns 150
No_of_seqs    500

 No Hit                             Prob E-value P-value  Score    SS Cols Query HMM  Template HMM
  1 e4ub3A1 2.40.30.10 277:1-277    99.8 2.3E-30 1.4E-34  221.4   0.0  147   1-150     1-150 (150)
  2 e1234B2 2.40.30.10 123:45-167   98.5 3.1E-18 1.9E-22  134.2   0.0  110  20-130    45-155 (170)
```

**Key Fields:**
- `Prob` - Match probability (0-100%)
- `E-value` - Expected false positives
- `Score` - HMM alignment score
- `Query HMM` - Query residue range
- `Template HMM` - Template residue range

---

## Performance

| Metric | Typical Value | Notes |
|--------|---------------|-------|
| Runtime | 30-60 minutes | Dominates pipeline time (90-95%) |
| Memory | 4-8 GB | Scales with UniRef database size |
| Disk I/O | High | UniRef database is ~260 GB |

### SLURM Considerations

**Critical:** Copy UniRef30 to local scratch before running to avoid NFS saturation:
```bash
rsync -a $UNIREF_SRC/ $TMPDIR/UniRef30_2022_02/
```

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| FASTA file not found | Step 1 incomplete | Run Step 1 first |
| hhblits database error | UniRef path incorrect | Check `--data-dir` path |
| addss.pl failed | PSIPRED not installed | Install PSIPRED or use `--skip-addss` |
| hhsearch timeout | Large protein | Increase time limit, reduce hits |

---

## Dependencies

**External Tools (Required):**
- `hhblits` - HH-suite MSA builder
- `hhmake` - HH-suite HMM builder
- `hhsearch` - HH-suite database search

**External Tools (Optional):**
- `addss.pl` - HH-suite secondary structure script
- `psipred` - Secondary structure predictor (required by addss.pl)

**Custom Configuration:**
- `dpam/tools/scripts/HHPaths.pm` - Custom path configuration for addss.pl
- The default system HHPaths.pm does not work; DPAM uses its own version
- See `docs/DEPENDENCIES.md` for details on customizing HHPaths.pm

---

## Backward Compatibility

Matches v1.0 hhsearch step exactly:
- Same database versions (UniRef30, PDB70)
- Same command-line parameters
- Same output format for downstream parsing
