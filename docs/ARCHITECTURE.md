# DPAM v2.0 Architecture Overview

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  CLI Commands:                                                   │
│  • dpam run <prefix>              → Single structure            │
│  • dpam batch-run <file>          → Step-first batch (fast)     │
│  • dpam batch <file>              → Protein-first parallel      │
│  • dpam slurm-batch <file>        → SLURM step-first batch     │
│  • dpam slurm-submit <file>       → SLURM array jobs            │
│  • dpam batch-status              → Monitor batch progress      │
│  • dpam run-step <prefix> --step  → Individual step             │
│                                                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Pipeline Orchestrators                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  DPAMPipeline (protein-first)                                    │
│  ├─ Checkpointing (.dpam_state.json)                           │
│  ├─ Error handling (continue on failure)                        │
│  ├─ Progress tracking                                            │
│  └─ Step execution (per protein)                                │
│                                                                   │
│  BatchRunner (step-first)                                        │
│  ├─ Step-first orchestration (_batch_state.json)               │
│  ├─ Optimized: FOLDSEEK (bulk search), DALI (template cache), │
│  │   DOMASS (shared TF model)                                    │
│  ├─ Cross-mode state sync (batch ↔ per-protein)                │
│  └─ Default: per-protein fallback via DPAMPipeline             │
│                                                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   ┌─────────┐    ┌─────────┐     ┌─────────┐
   │ Batch   │    │  SLURM  │     │ Single  │
   │ Runner  │    │ Manager │     │   Run   │
   │(step-1st│    │         │     │         │
   └─────────┘    └─────────┘     └─────────┘
        │                │                │
        └────────────────┴────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Pipeline Steps (1-13)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  PREPARATION         HOMOLOGY SEARCH       STRUCTURAL ALIGNMENT  │
│  ┌──────────┐       ┌──────────┐          ┌──────────┐         │
│  │ Step 1   │  ───▶ │ Step 2   │  ───────▶│ Step 7   │         │
│  │ Prepare  │       │ HHsearch │          │ DALI     │         │
│  └──────────┘       └──────────┘          │(parallel)│         │
│                            │               └──────────┘         │
│                            ▼                     │               │
│                     ┌──────────┐                │               │
│                     │ Step 3   │                │               │
│                     │ Foldseek │                │               │
│                     └──────────┘                │               │
│                            │                     │               │
│                     ┌──────┴─────┐              │               │
│                     ▼            ▼              ▼               │
│               ┌──────────┐ ┌──────────┐  ┌──────────┐         │
│               │ Step 4-6 │ │ Step 8-9 │  │ Step 11  │         │
│               │ Filter & │ │ Analyze  │  │   SSE    │         │
│               │   Map    │ │ Support  │  └──────────┘         │
│               └──────────┘ └──────────┘        │               │
│                      │           │              │               │
│                      └─────┬─────┘              │               │
│                            ▼                    ▼               │
│                      ┌──────────┐        ┌──────────┐         │
│                      │ Step 10  │        │ Step 12  │         │
│                      │  Filter  │        │ Disorder │         │
│                      └──────────┘        └──────────┘         │
│                            │                    │               │
│                            └──────┬─────────────┘               │
│                                   ▼                             │
│                             ┌──────────┐                        │
│                             │ Step 13  │                        │
│                             │  Parse   │                        │
│                             │ Domains  │                        │
│                             └──────────┘                        │
│                                   │                             │
└───────────────────────────────────┼─────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      External Tools Layer                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Tool Wrappers:                                                  │
│  ├─ HHsuite (hhblits, hhmake, hhsearch, addss.pl)             │
│  ├─ Foldseek (easy-search)                                      │
│  ├─ DALI (dali.pl)                                              │
│  └─ DSSP (mkdssp)                                               │
│                                                                   │
│  Features:                                                       │
│  • Availability checking                                        │
│  • Command execution with logging                               │
│  • Error handling and retry                                     │
│  • Output parsing                                               │
│                                                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      I/O and Data Layer                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Readers:                    Writers:                            │
│  ├─ CIF (Gemmi)              ├─ PDB (standardized)             │
│  ├─ PDB (Gemmi)              ├─ FASTA                           │
│  ├─ FASTA                    ├─ Results files                   │
│  ├─ JSON (PAE)               └─ Domain definitions              │
│  └─ Tool outputs                                                 │
│                                                                   │
│  Parsers:                    Reference Data:                     │
│  ├─ HHsearch                 ├─ ECOD lengths                    │
│  ├─ Foldseek                 ├─ ECOD norms                      │
│  ├─ DALI                     ├─ ECOD pdbmap                     │
│  └─ DSSP                     ├─ ECOD metadata                   │
│                              └─ Domain weights/info              │
│                                                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Core Data Models                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  @dataclass Structure:                                          │
│    prefix: str                                                  │
│    sequence: str                                                │
│    residue_coords: Dict[int, ndarray]                          │
│                                                                   │
│  @dataclass Domain:                                             │
│    domain_id: str                                               │
│    residue_range: str                                           │
│    residues: Set[int]                                           │
│                                                                   │
│  @dataclass Hit (Sequence/Structure):                          │
│    ecod_num, ecod_id, family                                   │
│    scores, coverage, ranges                                     │
│                                                                   │
│  @dataclass PipelineState:                                      │
│    completed_steps: Set[PipelineStep]                          │
│    failed_steps: Dict[PipelineStep, str]                       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Input Files                 Intermediate Files              Output Files
───────────                ──────────────────              ────────────

AF-P12345.cif    ─┐
AF-P12345.json   ─┤
                  │
                  ├─▶ Step 1  ─▶  .fa, .pdb (std)
                  │
                  ├─▶ Step 2  ─▶  .a3m, .hmm, .hhsearch
                  │
                  ├─▶ Step 3  ─▶  .foldseek
                  │
                  ├─▶ Step 4  ─▶  .foldseek.flt.result
                  │
                  ├─▶ Step 5  ─▶  .map2ecod.result
                  │
                  ├─▶ Step 6  ─▶  _hits4Dali
                  │
                  ├─▶ Step 7  ─▶  _iterativdDali_hits
                  │
                  ├─▶ Step 8  ─▶  _good_hits
                  │
                  ├─▶ Step 9  ─▶  _sequence.result
                  │                _structure.result
                  │
                  ├─▶ Step 10 ─▶  .goodDomains
                  │
                  ├─▶ Step 11 ─▶  .sse
                  │
                  ├─▶ Step 12 ─▶  .diso
                  │
                  └─▶ Step 13 ─▶  .finalDPAM.domains ⭐
```

## Module Dependencies

```
cli/main.py
    │
    ├─▶ pipeline/runner.py          (protein-first orchestration)
    │       │
    │       ├─▶ steps/step01-24.py
    │       │       │
    │       │       ├─▶ tools/{hhsuite,foldseek,dali,dssp}.py
    │       │       │       │
    │       │       │       └─▶ tools/base.py
    │       │       │
    │       │       ├─▶ io/{readers,writers,parsers}.py
    │       │       │       │
    │       │       │       └─▶ core/models.py
    │       │       │
    │       │       └─▶ utils/{ranges,amino_acids}.py
    │       │
    │       └─▶ io/reference_data.py
    │               │
    │               └─▶ core/models.py
    │
    ├─▶ pipeline/batch_runner.py    (step-first orchestration)
    │       │
    │       ├─▶ pipeline/runner.py  (for default per-protein fallback)
    │       │
    │       ├─▶ steps/step03_foldseek.py    (run_step3_batch)
    │       ├─▶ steps/step07_iterative_dali.py (template_cache param)
    │       └─▶ steps/step16_run_domass.py  (DomassModel context mgr)
    │
    ├─▶ pipeline/batch.py           (protein-first local parallel)
    │       │
    │       └─▶ pipeline/runner.py
    │
    └─▶ pipeline/slurm.py          (SLURM array + batch submission)
            │
            └─▶ utils/logging_config.py
```

## Parallel Processing Model

### Local Batch Processing
```
Main Process
    │
    ├─▶ Worker 1: Structure A (4 CPUs)
    │       ├─ Step 1-6: Sequential
    │       └─ Step 7: Multiprocessing (DALI iterations)
    │
    ├─▶ Worker 2: Structure B (4 CPUs)
    │       └─ ...
    │
    └─▶ Worker N: Structure N (4 CPUs)
            └─ ...
```

### Step-First Batch Processing (`dpam batch-run`)
```
BatchRunner (single process)
    │
    ├─▶ Step 3 (FOLDSEEK): Batch-optimized
    │   ├─ createdb: All PDBs → single query DB
    │   ├─ search: One search against ECOD index (loaded once)
    │   ├─ convertalis: Extract results
    │   └─ Split: Per-protein .foldseek files
    │
    ├─▶ Step 7 (DALI): Template cache
    │   ├─ Scan _hits4Dali: Collect all unique templates
    │   ├─ Bulk copy: ECOD70/ → shared cache dir (once)
    │   ├─ Per-protein: run_step7() with template_cache path
    │   └─ Cleanup: Remove cache dir
    │
    ├─▶ Step 16 (DOMASS): Shared TF model
    │   ├─ Load: TF model + session (once, ~22s)
    │   ├─ Per-protein: Inference (<10ms each)
    │   └─ Teardown: Close session
    │
    └─▶ All other steps: Per-protein via DPAMPipeline.run_step()

State tracking:
- _batch_state.json: (step, protein) → "complete"|"failed"
- .{protein}.dpam_state.json: Updated in sync for cross-mode compat
- Critical failures (HHSEARCH/FOLDSEEK/DALI) skip downstream steps
```

### SLURM Array Processing (`dpam slurm-submit`)
```
SLURM Controller
    │
    ├─▶ Task 0: Structure A (Node 1, 8 CPUs)
    │
    ├─▶ Task 1: Structure B (Node 1, 8 CPUs)
    │
    ├─▶ Task 2: Structure C (Node 2, 8 CPUs)
    │
    ├─▶ ... (up to array-size concurrent)
    │
    └─▶ Task N: Structure N (Node M, 8 CPUs)

Each task runs independently with:
- Own working directory space
- Checkpointing for resilience
- Individual log files
- No inter-task dependencies
```

## Error Handling Flow

```
Pipeline.run(prefix)
    │
    ├─▶ Load/Create State
    │
    ├─▶ For each step:
    │       │
    │       ├─▶ Execute step
    │       │       │
    │       │       ├─ Success ─▶ Mark complete ─▶ Save state
    │       │       │
    │       │       └─ Failure ─▶ Mark failed ─▶ Save state ─▶ CONTINUE
    │       │
    │       └─▶ Next step (don't break on failure)
    │
    └─▶ Return final state
            │
            ├─ completed_steps: Set[PipelineStep]
            └─ failed_steps: Dict[PipelineStep, error]
```

## Key Design Principles

1. **Type Safety**: All data structures are type-hinted dataclasses
2. **Immutability**: Input files never modified, outputs always new
3. **Idempotency**: Re-running same step produces same result
4. **Checkpointing**: State saved after each step
5. **Isolation**: Failures isolated to individual structures
6. **Logging**: Structured JSON logs for aggregation
7. **Testability**: Pure functions, dependency injection
8. **Extensibility**: Abstract base classes for tools
9. **Backward Compatibility**: File formats match v1.0

## Performance Characteristics

| Component | Complexity | Bottleneck | Optimization |
|-----------|-----------|------------|--------------|
| Step 1 | O(N) | I/O | - |
| Step 2 | O(N²) | CPU | Parallelize |
| Step 3 | O(N log N) | I/O | Database index |
| Steps 4-6 | O(N) | - | - |
| Step 7 | O(N³) | CPU + I/O | Multiprocessing |
| Steps 8-10 | O(N²) | - | - |
| Step 11 | O(N) | - | - |
| Step 12 | O(N²) | - | - |
| Step 13 | O(N³) | Memory | Sparse matrices |

N = protein length (typically 100-1000 residues)
