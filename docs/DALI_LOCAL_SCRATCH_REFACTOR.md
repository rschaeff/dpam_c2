# DALI Local Scratch I/O Refactor

## Status: IMPLEMENTED

## Problem

DALI structural alignment (`step07_iterative_dali.py`) is the dominant bottleneck in the DPAM pipeline, and dpam_c2 is **~25x slower** than the native HGD implementation on comparable hardware:

| Implementation | Time/Protein | I/O Location | Parallelism | Notes |
|----------------|-------------|--------------|-------------|-------|
| HGD native (hgd cluster) | ~6 sec | Local `/scratch/` (SSD) | 64 processes | Production reference |
| dpam_c2 protein-first (leda) | ~11.6 min | NFS working dir | 16 processes | Before template cache |
| dpam_c2 step-first + template cache (leda) | ~2.5 min | NFS working dir | 16 processes | Current best |

The template cache (Phase 3 of batch mode refactor) provided a **~4.6x speedup** by eliminating redundant NFS copies of ECOD70 templates across proteins. But the remaining **~25x gap** vs native is driven by the fundamental I/O pattern of DALI alignment.

## Root Cause Analysis

### DALI's I/O Pattern

Each DALI pairwise alignment involves **20-50 file operations**:

1. Create temp directory
2. Copy query PDB to temp dir
3. Copy template PDB to temp dir (or symlink from cache)
4. DALI writes intermediate files during alignment
5. DALI writes output files (`.txt` results)
6. Parse output file
7. Clean up temp directory and contents

For a typical protein with ~200 DALI candidates, this means **4,000-10,000 file operations** per protein, all executed within the iterative loop.

### NFS vs Local Disk Latency

| Operation | NFS (leda) | Local SSD (/scratch, /tmp) |
|-----------|-----------|---------------------------|
| File create | ~5-10 ms | ~0.1 ms |
| File read | ~2-5 ms | ~0.05 ms |
| mkdir | ~5-10 ms | ~0.1 ms |
| stat/exists check | ~2-5 ms | ~0.05 ms |

With ~7,500 file ops per protein at ~5ms NFS overhead each: **~37.5 seconds of pure NFS latency** per protein. Under contention from 16 parallel workers all hitting the same NFS mount, this amplifies significantly.

### The dpam_c2 I/O Path (Current)

From `step07_iterative_dali.py`:

```python
# All temp I/O goes through NFS working_dir
iterative_dir = working_dir / f'iterativeDali_{prefix}'
iterative_dir.mkdir(parents=True, exist_ok=True)

tmp_dir = iterative_dir / f'tmp_{prefix}_{edomain}'
tmp_dir.mkdir(parents=True, exist_ok=True)
output_tmp_dir = tmp_dir / 'output_tmp'
output_tmp_dir.mkdir(parents=True, exist_ok=True)

work_pdb = (tmp_dir / f'{prefix}_{edomain}.pdb').resolve()
shutil.copy(query_pdb, work_pdb)
```

Every temp directory creation, PDB copy, DALI intermediate file, and result parsing goes through NFS.

### The Native HGD I/O Path (Reference)

The native implementation uses local `/scratch/` (SSD) for ALL DALI I/O:

```python
# Query PDB -> local scratch
os.system('cp ' + wdir + '/step2/' + dataset + '/' + prot + '.pdb /scratch/' + prot + '_' + edomain + '.pdb')

# Template PDB -> local scratch (cached, only copy if missing)
if not os.path.exists('/scratch/ECOD_pdbs/' + edomain + '.pdb'):
    os.system('cp ' + wdir + '/ECOD_pdbs/' + edomain + '.pdb /scratch/ECOD_pdbs/')

# Temp dir on local scratch
os.system('mkdir /scratch/tmp_' + prot + '_' + edomain)
os.chdir('/scratch/tmp_' + prot + '_' + edomain)
```

Key design decisions:
1. **All temp I/O on local disk** - eliminates NFS latency entirely
2. **Template caching on local disk** - only copy each template once from NFS
3. **64-way parallelism** - I/O-bound work benefits from higher concurrency
4. **Results copied back to NFS only once** - final output file written to shared storage

### Secondary Factor: Parallelism

| Implementation | Workers | Rationale |
|----------------|---------|-----------|
| HGD native | 64 | I/O-bound work benefits from high concurrency |
| dpam_c2 | `cpus` (typically 16) | Assumes CPU-bound; wrong for DALI |

DALI alignment is **I/O-bound, not CPU-bound**. Each worker spends most of its time waiting for file operations to complete. With local disk I/O, 64 workers can saturate the CPU; with NFS I/O, even 16 workers spend most time waiting.

## Proposed Changes

### Change 1: Local Scratch for DALI Temp I/O

Modify `step07_iterative_dali.py` to use a configurable local scratch directory for all DALI temporary files.

**Architecture:**
```
NFS (working_dir)                    Local (/tmp or /scratch)
├── {prefix}_hits4Dali               ├── dpam_dali_{prefix}/
├── {prefix}.pdb (query)             │   ├── tmp_{prefix}_{edomain}/
│                                    │   │   ├── {prefix}_{edomain}.pdb
│                                    │   │   ├── output_tmp/
│                                    │   │   └── (DALI intermediates)
│                                    │   └── template_cache/
│                                    │       ├── {edomain1}.pdb
│                                    │       └── {edomain2}.pdb
│                                    │
├── {prefix}_iterativDali_hits  <--- (final results written back to NFS)
```

**Flow:**
1. At step start: create local scratch dir, copy query PDB from NFS
2. During DALI: all temp dirs, copies, and DALI I/O on local disk
3. Template cache on local disk (copy from NFS or shared cache on first use)
4. At step end: write final `_iterativDali_hits` result file back to NFS
5. Clean up local scratch dir

**Configuration:**
- New parameter: `--scratch-dir` (default: platform-dependent)
  - leda SLURM jobs: `/tmp` (262 GB local ext4 on `/dev/sda4`, exclusive node access)
  - Interactive/other: `tempfile.mkdtemp()` in system temp
  - TACC: `$SCRATCH` or `$TMPDIR`
- Fallback: if scratch dir is unavailable or too small, fall back to NFS working_dir with a warning

### Change 2: Increased DALI Parallelism

When using local scratch, increase the default DALI worker count beyond `cpus`:

```python
# I/O-bound DALI benefits from oversubscription
dali_workers = min(cpus * 4, 64)  # Up to 4x CPU count, capped at 64
```

This should be a separate parameter (`--dali-workers`) to allow tuning independently of `--cpus`.

### Change 3: Per-Protein Local Template Cache

Within each protein's DALI step, cache templates on local disk:

```python
local_template = scratch_dir / 'template_cache' / f'{edomain}.pdb'
if not local_template.exists():
    shutil.copy(template_source, local_template)
```

This complements the existing batch-mode NFS template cache. The copy path becomes:
- **Without batch cache**: ECOD data dir (NFS) -> local scratch (1 NFS read per unique template per protein)
- **With batch cache**: batch template cache (NFS) -> local scratch (same, but shorter NFS path)

In batch mode with many proteins on the same node, the local template cache will warm up quickly across the first few proteins.

### Change 4: Integration with BatchRunner

The `BatchRunner._run_iterative_dali()` method should:
1. Pass scratch_dir to the step function
2. Create a shared local template cache directory at batch start
3. Clean up local scratch at batch end (or on failure)

```python
# In BatchRunner, at ITERATIVE_DALI step start:
local_scratch = Path(scratch_dir) / f'dpam_dali_batch'
local_template_cache = local_scratch / 'template_cache'
local_template_cache.mkdir(parents=True, exist_ok=True)

# Pre-warm local cache from NFS batch cache (background, during first protein)
# This avoids redundant NFS reads across proteins
```

## Expected Performance

Based on the native HGD numbers and the I/O analysis:

| Configuration | Est. Time/Protein | Speedup vs Current |
|---------------|------------------|--------------------|
| Current (NFS + 16 workers) | ~2.5 min | 1x |
| Local scratch + 16 workers | ~20-30 sec | 5-7x |
| Local scratch + 64 workers | ~6-10 sec | 15-25x |

The native implementation achieves ~6 sec/protein with local scratch + 64 workers, which is consistent with the upper bound estimate.

## Impact on Production Runs

For batch_39 (263 proteins) as a concrete example:

| Configuration | DALI Step Time | Total Pipeline |
|---------------|---------------|----------------|
| Current (NFS, 16 workers) | ~11 hours | ~13 hours |
| Local scratch + 64 workers | ~26-44 min | ~2-3 hours |

For the full Tier 1 dataset (~28,000 proteins across 29 batches):
- Current: ~29 batch jobs x ~11 hours = ~13 days (3 partitions, staggered)
- With refactor: ~29 batch jobs x ~0.7 hours = ~20 hours (3 partitions, staggered)

## Files to Modify

| File | Change |
|------|--------|
| `dpam/steps/step07_iterative_dali.py` | Add scratch_dir parameter, redirect temp I/O to local disk, add local template cache |
| `dpam/pipeline/batch_runner.py` | Pass scratch_dir to DALI step, manage local scratch lifecycle |
| `dpam/pipeline/slurm.py` | Add `--scratch-dir` to generated SLURM scripts (default `/tmp`) |
| `dpam/cli/main.py` | Add `--scratch-dir` and `--dali-workers` CLI parameters |
| `dpam/pipeline/__init__.py` | Pass scratch_dir through single-protein pipeline |

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Local `/tmp` fills up | Check available space at start; clean up per-protein; fall back to NFS |
| SLURM job preemption loses local scratch | Results are ephemeral temp files; resume will re-run DALI for incomplete proteins |
| Platform differences (no local scratch) | Graceful fallback to NFS with warning; scratch_dir is configurable |
| 64 workers causing memory pressure | Cap at `min(cpus * 4, 64)`; each DALI process is lightweight (~50MB) |
| Template cache coherency | Read-only after initial copy; no coherency issues |

## Implementation Priority

This refactor should be implemented **before** submitting the remaining Tier 1 batches (11-38). The DALI step dominates total runtime, and a ~15-25x speedup would reduce the full Tier 1 processing from ~13 days to ~1 day of wall time.

The change is isolated to the DALI step and its callers - it does not affect any other pipeline steps or the correctness of results (same DALI binary, same inputs, same outputs, just different temp file locations).
