# DPAM Batch Mode Refactor: Protein-First to Step-First

## Problem Statement

The current dpam_c2 architecture processes each protein through the full 23-step pipeline before starting the next protein. When parallelized via SLURM array jobs, each task independently loads databases, models, and indices — paying startup costs N times for N proteins.

Empirical comparison on identical batch_39 (263 proteins) shows this is catastrophically expensive:

| Metric | HGD native DPAM (step-first) | Leda dpam_c2 (protein-first) | Ratio |
|--------|------------------------------|-------------------------------|-------|
| Per-protein time | 0.4 min | 13.3 min | 30x |
| DALI per protein | 6.0 sec | 11.6 min | 116x |
| Foldseek per protein | 0.16 sec | 42.8 sec | 275x |
| DOMASS per protein | 0.03 sec | 21.5 sec | 628x |
| Total wall time (263 proteins) | 147 min | ~180 min (estimated) | ~1.2x |

Wall time is comparable only because leda uses 50 concurrent nodes vs HGD's single sequential process. But the CPU cost is 30x higher.

### Root Cause: Startup Cost Amortization

The three bottleneck steps dominate because they load expensive resources per invocation:

1. **Foldseek** (42.8s/protein, 5.4% of time): Loads the ECOD foldseek database index (~5GB) from disk for every single protein search. HGD runs all 263 searches with one index load.

2. **Iterative DALI** (11.6 min/protein, 87.6% of time): Spawns DaliLite per-domain with per-invocation working directory setup, PDB file copying, and DAT directory creation. For a protein with 300 ECOD candidate domains, that's 300 individual DaliLite invocations. HGD batches these operations.

3. **DOMASS/TensorFlow** (21.5s/protein, 2.7% of time): Loads the TF 1.x checkpoint (graph + weights + session) for every protein. Model loading is ~22 sec; actual inference is <0.1 sec. HGD loads the model once for all 263 proteins.

## Proposed Architecture: Step-First Batch Mode

### Core Idea

Add a `dpam batch-run` command that processes proteins step-wise: run step 1 for all proteins, then step 2 for all proteins, etc. Expensive resources load once per step, not once per protein.

```
# Current (protein-first):
for protein in proteins:
    load_foldseek_db()        # 263 times
    search(protein)
    unload()
    load_dali()               # 263 times
    align(protein)
    unload()
    load_tf_model()           # 263 times
    predict(protein)
    unload()

# Proposed (step-first):
load_foldseek_db()            # 1 time
for protein in proteins:
    search(protein)
unload()

load_dali()                   # 1 time (amortized setup)
for protein in proteins:
    align(protein)
unload()

load_tf_model()               # 1 time
for protein in proteins:
    predict(protein)
unload()
```

### Expected Improvement

If we eliminate startup overhead and match HGD's per-protein processing rate:
- Foldseek: 42.8s → ~0.2s per protein (index loaded once)
- DALI: 696s → ~6s per protein (working dir reuse, bulk setup)
- DOMASS: 21.5s → ~0.03s per protein (model loaded once)
- **Total: 13.3 min → ~0.5 min per protein** (~25x improvement)

Note: DALI improvement depends on how much of the 116x slowdown is startup vs algorithmic. Some may be DaliLite version differences or I/O patterns. The refactor addresses startup; any remaining gap needs separate investigation.

## Design

### New Components

#### 1. `BatchRunner` class (`dpam/pipeline/batch_runner.py`)

Orchestrates step-first execution across a protein list.

```python
class BatchRunner:
    """Run DPAM pipeline step-by-step across a batch of proteins."""

    def __init__(self, protein_list: List[str], working_dir: Path,
                 data_dir: Path, cpus: int = 1):
        self.proteins = protein_list
        self.working_dir = working_dir
        self.data_dir = data_dir
        self.cpus = cpus
        self.reference_data = load_ecod_data(data_dir)  # Load once
        self.state = BatchState(working_dir)             # Track progress

    def run(self, steps: Optional[List[PipelineStep]] = None):
        """Execute steps in order, each across all proteins."""
        for step in steps or ALL_STEPS:
            pending = self.state.get_pending(step)
            if not pending:
                logger.info(f"Step {step.name}: all proteins complete, skipping")
                continue

            logger.info(f"Step {step.name}: {len(pending)} proteins to process")
            step_runner = self._get_step_runner(step)
            step_runner.run_batch(pending)

    def _get_step_runner(self, step: PipelineStep) -> StepBatchRunner:
        """Get the appropriate batch runner for a step.

        Returns a BatchStepRunner that handles resource loading once
        and iterates over proteins.
        """
        ...
```

#### 2. `StepBatchRunner` base class (`dpam/pipeline/step_batch_runner.py`)

Base class for running a single step across many proteins. Key pattern: `setup()` loads resources, `process(protein)` runs per-protein, `teardown()` cleans up.

```python
class StepBatchRunner:
    """Base class for batch execution of a single pipeline step."""

    def run_batch(self, proteins: List[str]):
        """Load resources once, process all proteins, cleanup."""
        self.setup()
        results = {}
        for protein in proteins:
            try:
                results[protein] = self.process(protein)
                self.state.mark_complete(self.step, protein)
            except Exception as e:
                logger.error(f"{self.step.name} failed for {protein}: {e}")
                self.state.mark_failed(self.step, protein)
        self.teardown()
        return results

    def setup(self):
        """Load expensive resources. Override in subclasses."""
        pass

    def process(self, protein: str) -> bool:
        """Process a single protein. Override in subclasses."""
        raise NotImplementedError

    def teardown(self):
        """Release resources. Override in subclasses."""
        pass
```

#### 3. Bottleneck Step Implementations

##### `FoldseekBatchRunner`

```python
class FoldseekBatchRunner(StepBatchRunner):
    """Batch foldseek: load index once, search all proteins."""

    def setup(self):
        # Foldseek easy-search doesn't support persistent index loading.
        # But we CAN use foldseek's createdb + search workflow:
        #   1. foldseek createdb (all query PDBs -> single query DB)
        #   2. foldseek search (query DB vs ECOD DB, one invocation)
        #   3. foldseek convertalis (extract per-protein results)
        # This is a single foldseek invocation for ALL proteins.
        self.query_db = self._create_query_db()

    def process(self, protein: str) -> bool:
        # Not called per-protein — single bulk search instead
        raise NotImplementedError("Use run_batch() directly")

    def run_batch(self, proteins: List[str]):
        """Override: single foldseek search for entire batch."""
        self.setup()

        # Create query database from all PDB files
        pdb_list = self.working_dir / "_foldseek_batch_input.txt"
        with open(pdb_list, 'w') as f:
            for p in proteins:
                f.write(f"{self.working_dir / f'{p}.pdb'}\n")

        # foldseek createdb + search + convertalis
        # Single invocation, single index load
        self._run_bulk_search(pdb_list, proteins)

        # Split results into per-protein output files
        self._split_results(proteins)

        self.teardown()
```

Alternative (simpler, less invasive): keep `easy-search` per protein but use foldseek's `--preload` option or memory-mapped database. Benchmark to see if the index load is actually the bottleneck or if it's per-search overhead.

##### `DaliBatchRunner`

```python
class DaliBatchRunner(StepBatchRunner):
    """Batch DALI: reuse working directories and template PDBs."""

    def setup(self):
        # Pre-copy all needed ECOD template PDBs to a shared local dir.
        # Currently each protein copies templates individually.
        self.template_cache = self._cache_ecod_templates()

    def process(self, protein: str) -> bool:
        # Run iterative DALI for this protein using cached templates.
        # Same algorithm as step07, but with template_dir pointing to cache.
        run_step7(protein, self.working_dir, self.data_dir,
                  cpus=self.cpus, template_cache=self.template_cache)
```

Note: DALI's 116x slowdown needs deeper investigation. The per-protein multiprocessing.Pool in step07 may be creating excessive subprocess overhead. Consider:
- Whether DaliLite itself is slower on leda (version difference?)
- Whether the iterative alignment algorithm processes more candidates on average
- Whether filesystem I/O (NFS vs local) is a factor
- Whether the multiprocessing Pool per-protein has excessive fork/join cost

##### `DomassBatchRunner`

```python
class DomassBatchRunner(StepBatchRunner):
    """Batch DOMASS: load TF model once, predict all proteins."""

    def setup(self):
        # Load TensorFlow session and model ONCE
        import tensorflow as tf
        self.sess = tf.Session()
        saver = tf.train.import_meta_graph(str(self.model_path) + '.meta')
        saver.restore(self.sess, str(self.model_path))
        self.input_tensor = self.sess.graph.get_tensor_by_name('input:0')
        self.output_tensor = self.sess.graph.get_tensor_by_name('output:0')

    def process(self, protein: str) -> bool:
        # Load features, run inference (model already loaded)
        features = load_step15_features(protein)
        predictions = self.sess.run(self.output_tensor,
                                     {self.input_tensor: features})
        write_step16_predictions(protein, predictions)
        return True

    def teardown(self):
        self.sess.close()
```

This is the most straightforward fix. Current step16 spends 22 of 21.5 seconds loading the model.

#### 4. `BatchState` class (`dpam/pipeline/batch_state.py`)

Track progress at (step, protein) granularity. Supports resume.

```python
class BatchState:
    """Track batch execution state: which (step, protein) pairs are done."""

    def __init__(self, working_dir: Path):
        self.state_file = working_dir / "_batch_state.json"
        self.state = self._load()  # {step_name: {protein: "complete"|"failed"}}

    def get_pending(self, step: PipelineStep) -> List[str]:
        """Get proteins that haven't completed this step."""
        ...

    def mark_complete(self, step: PipelineStep, protein: str):
        """Mark (step, protein) as complete. Auto-saves."""
        ...

    def mark_failed(self, step: PipelineStep, protein: str):
        """Mark (step, protein) as failed."""
        ...
```

### CLI Addition

```python
# dpam/cli/main.py
@cli.command()
@click.argument('protein_list', type=click.Path(exists=True))
@click.option('--working-dir', type=click.Path(), required=True)
@click.option('--data-dir', type=click.Path(), required=True)
@click.option('--cpus', default=4, type=int)
@click.option('--resume', is_flag=True)
def batch_run(protein_list, working_dir, data_dir, cpus, resume):
    """Run DPAM pipeline step-first across a batch of proteins.

    Loads expensive resources (foldseek index, DALI templates, TF model)
    once per step rather than once per protein.
    """
    with open(protein_list) as f:
        proteins = [line.strip() for line in f if line.strip()]

    runner = BatchRunner(proteins, Path(working_dir), Path(data_dir), cpus)
    runner.run()
```

### SLURM Integration

Two deployment options:

**Option A: Single-node batch mode (simplest)**
One SLURM job per batch, step-first within that job:

```bash
#!/bin/bash
#SBATCH --job-name=dpam_batch_39
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=24:00:00

dpam batch-run proteins.txt \
    --working-dir /data/ecod/archaea/dpam_tier1_batched/batch_39 \
    --data-dir /home/rschaeff_1/data/dpam_reference/ecod_data \
    --cpus 16
```

Expected time: ~263 proteins * 0.5 min = ~2 hours on a single node.

**Option B: Step-wise array jobs (maximum parallelism)**
Separate SLURM jobs per step, with dependencies. Lightweight steps run as single jobs; heavy steps run as arrays:

```bash
# Step 1-6: PREPARE through DALI_CANDIDATES (fast, single job)
JOB1=$(sbatch --parsable submit_steps_1_6.sh)

# Step 7: ITERATIVE_DALI (heavy, array job with shared template cache)
JOB7=$(sbatch --parsable --dependency=afterok:$JOB1 submit_step7_dali.sh)

# Step 8-15: Analysis steps (fast, single job)
JOB8=$(sbatch --parsable --dependency=afterok:$JOB7 submit_steps_8_15.sh)

# Step 16: DOMASS (moderate, single job with persistent TF session)
JOB16=$(sbatch --parsable --dependency=afterok:$JOB8 submit_step16_domass.sh)

# Step 17-24: Final steps (fast, single job)
JOB17=$(sbatch --parsable --dependency=afterok:$JOB16 submit_steps_17_24.sh)
```

**Recommendation**: Start with Option A. It's simpler and the expected 2-hour single-node time is acceptable for a 263-protein batch.

## Implementation Plan

### Phase 1: Low-hanging fruit (DOMASS, ~1 hour)

DOMASS is the easiest win: 628x slowdown entirely due to model loading.

1. Add `setup()/teardown()` pattern to `step16_run_domass.py`
2. Extract TF session creation into reusable function
3. Add `run_step16_batch(proteins, ...)` entry point
4. Test: 263 proteins should go from 94 min → <1 min total

### Phase 2: Foldseek batch search (~2-3 hours)

275x slowdown from per-protein index loading.

1. Investigate foldseek `createdb` + `search` workflow vs `easy-search`
   - `easy-search` is a convenience wrapper that creates a temporary DB per query
   - `createdb` + `search` creates a single query DB for all proteins
2. Implement `FoldseekBatchRunner` using bulk search
3. Add result-splitting logic to create per-protein `.foldseek` files
4. Test: 263 proteins should go from 187 min → <2 min total

### Phase 3: DALI investigation and optimization (~1 day)

116x slowdown is the biggest time contributor but hardest to fix. Need to disentangle causes:

1. **Benchmark DaliLite directly**: Same protein, same template, leda vs HGD. Is DaliLite itself slower?
2. **Profile subprocess overhead**: How much time is fork/exec/setup vs actual alignment?
3. **Compare candidate counts**: Are we generating more Dali candidates than HGD per protein?
4. **Test filesystem impact**: NFS vs local /tmp for Dali working directories
5. **Implement template caching**: Pre-copy ECOD70 templates once per batch
6. **Consider shared working directory**: Reuse DAT/ directories across proteins

### Phase 4: Wire up BatchRunner + CLI (~2-3 hours)

1. Implement `BatchRunner` orchestrator
2. Implement `BatchState` for (step, protein) checkpoint/resume
3. Add `dpam batch-run` CLI command
4. Add SLURM submit script generator
5. Integration test on batch_39

### Phase 5: Validate against HGD results

1. Run batch_39 through new batch mode
2. Compare domain assignments against HGD DPAM results
3. Verify per-protein timing is in expected range (< 1 min/protein)

## Compatibility

- **No changes to individual step implementations** (step01-step24 functions unchanged)
- **Existing `dpam run` command preserved** (protein-first still available for single proteins)
- **Existing checkpoint files compatible** (BatchState reads existing `.dpam_state.json`)
- **Same output file formats** (per-protein result files identical)

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Foldseek bulk search produces different results than easy-search | Validate hit counts and scores on test batch |
| DALI slowdown is algorithmic, not startup | Phase 3 benchmarking will reveal; may need to also compare DaliLite versions |
| TF model behaves differently with batch input | DOMASS already processes in 100-sample batches internally; just loading once |
| Memory pressure from loading all protein data | Process proteins in streaming fashion, don't hold all results in memory |
| BatchState file corruption on crash | Write atomic (write to temp, rename) |

## Files to Create/Modify

### New files:
- `dpam/pipeline/batch_runner.py` - BatchRunner orchestrator
- `dpam/pipeline/batch_state.py` - (step, protein) progress tracking
- `dpam/pipeline/step_batch_runner.py` - Base class + bottleneck implementations

### Modified files:
- `dpam/cli/main.py` - Add `batch-run` command
- `dpam/steps/step03_foldseek.py` - Add batch search entry point
- `dpam/steps/step07_iterative_dali.py` - Add template cache parameter
- `dpam/steps/step16_run_domass.py` - Extract TF session management

### Not modified:
- All other step files (step01, step02, step04-06, step08-15, step17-24)
- `dpam/tools/` (foldseek.py, dali.py wrappers may need minor additions)
- `dpam/io/reference_data.py` (already loads once)
- `dpam/core/models.py` (data structures unchanged)
