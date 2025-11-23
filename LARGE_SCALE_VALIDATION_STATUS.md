# Large-Scale DPAM v2.0 Validation

**Date**: 2025-11-23
**Status**: 🔄 IN PROGRESS
**Job ID**: 332330

## Overview

Running large-scale validation of DPAM v2.0 on **949 AlphaFold proteins** from the ECOD database.

### Protein Selection Criteria

- **Source**: ECOD database (`ecod_commons.proteins` table)
- **Filter**: `source_type = 'afdb'` AND `sequence_length BETWEEN 50 AND 1500`
- **Total queried**: 1,000 proteins
- **Successfully downloaded**: 949 proteins (94.9% success rate)
- **Distribution**:
  - Single-domain: 581 proteins (61.2%)
  - Multi-domain: 419 proteins (44.2%)

### SLURM Job Configuration

```bash
Job ID:           332330
Array size:       0-948 (949 proteins)
Concurrent jobs:  100 (max)
Partition:        All
CPUs per task:    8
Memory per task:  32GB (4GB × 8 CPUs)
Time limit:       4:00:00 (4 hours)
Working dir:      validation_1000_run/
```

### Data Locations

- **Input structures**: `validation_1000_structures/` (949 CIF + 949 PAE files)
- **Working directory**: `validation_1000_run/` (symlinks + outputs)
- **SLURM logs**: `validation_1000_run/slurm_logs/`
- **Protein list**: `validation_afdb_downloaded.txt` (949 proteins)
- **Array mapping**: `validation_1000_run/prefixes_array.txt`

### Performance Optimization

**Node-local database caching** (critical for performance):
- Each job copies UniRef30 database (~260GB) to node scratch
- Prevents NFS I/O bottleneck from 100 concurrent HHblits processes
- Database copy takes 2-5 minutes per job
- Saves hours of NFS thrashing

### Monitoring Progress

```bash
# Check job status
squeue -j 332330

# Monitor completed jobs
ls validation_1000_run/*.dpam_state.json | wc -l

# Check success/failure counts
grep -l "\"completed_steps\":" validation_1000_run/.*.dpam_state.json | wc -l

# View recent log
tail -f validation_1000_run/slurm_logs/332330_0.out

# Check for errors
grep -i "error" validation_1000_run/slurm_logs/*.err | wc -l
```

### Expected Timeline

With 100 concurrent jobs and ~5 minutes average per protein:
- **Per protein**: ~5 minutes (HHsearch 64%, DALI 28%, ML 3%, rest 5%)
- **Serial time**: 949 × 5 min = 79 hours
- **Parallel time** (100 concurrent): ~79 / 100 × array overhead = **~1-2 hours**

### Validation Metrics

Once complete, we will analyze:

1. **Completion rate**: % of proteins that finished all 24 steps
2. **Domain detection**:
   - Single-domain proteins: # domains found vs expected
   - Multi-domain proteins: # domains found vs expected
3. **ECOD classification**: % correct t-group assignments (need ground truth)
4. **Boundary accuracy**: Comparison with ECOD/PDB domain boundaries
5. **Runtime distribution**: Identify bottlenecks and outliers

### Files Generated Per Protein

Each protein generates ~30-40 files:
- **Input**: `{prefix}.cif`, `{prefix}.json` (PAE)
- **Intermediate**: `.fa`, `.pdb`, `.hhsearch`, `.foldseek`, `.map2ecod.result`, etc.
- **Output**: `.finalDPAM.domains`, `.step23_predictions`, `.step24_final.domains`
- **State**: `.{prefix}.dpam_state.json`

**Total files expected**: ~949 proteins × 35 files = **~33,000 files**

### Next Steps

1. ✅ Download 949 proteins from AlphaFold (COMPLETE)
2. 🔄 Run DPAM pipeline on cluster (IN PROGRESS - Job 332330)
3. ⏸️ Collect and analyze results
4. ⏸️ Compare with ECOD ground truth
5. ⏸️ Generate validation report

### Quick Commands

```bash
# Check overall progress
echo "Running: $(squeue -j 332330 -h | grep ' R ' | wc -l)/100"
echo "Completed: $(ls validation_1000_run/*.dpam_state.json 2>/dev/null | wc -l)/949"

# Check for failures
grep "\"failed_steps\"" validation_1000_run/.*.dpam_state.json | grep -v "\"failed_steps\": \[\]" | wc -l

# Monitor a specific protein (e.g., array task 0)
tail -f validation_1000_run/slurm_logs/332330_0.out

# Cancel job if needed
scancel 332330
```

### Known Issues

1. **Partition name**: Had to change from `compute` to `All` for this cluster
2. **Download failures**: 51/1000 proteins (5.1%) not available in AlphaFold v6
3. **Database path**: UniRef30_2023_02 (note: year 2023, not 2022)

---

## Updates

**2025-11-23 13:00**: Job 332330 submitted successfully, 100 concurrent jobs started
