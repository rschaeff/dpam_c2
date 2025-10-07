"""
DPAM Pipeline Implementation Guide
===================================

This document provides the complete architecture and implementation patterns
for all 13 pipeline steps. Steps 1 and 2 are fully implemented as examples.

COMPLETED IMPLEMENTATIONS:
--------------------------
✓ Step 1: Structure Preparation (steps/step01_prepare.py)
✓ Step 2: HHsearch (steps/step02_hhsearch.py)

IMPLEMENTATION PATTERNS FOR REMAINING STEPS:
--------------------------------------------

STEP 3: Foldseek Structure Search
----------------------------------
File: steps/step03_foldseek.py

```python
from dpam.tools.foldseek import Foldseek

def run_step3(prefix: str, working_dir: Path, data_dir: Path, threads: int = 1) -> bool:
    foldseek = Foldseek()
    pdb_file = working_dir / f'{prefix}.pdb'
    output_file = working_dir / f'{prefix}.foldseek'
    tmp_dir = working_dir / 'foldseek_tmp'
    database = data_dir / 'ECOD_foldseek_DB' / 'ECOD_foldseek_DB'
    
    foldseek.easy_search(
        query_pdb=pdb_file,
        database=database,
        output_file=output_file,
        tmp_dir=tmp_dir,
        threads=threads,
        evalue=1000000,
        max_seqs=1000000,
        working_dir=working_dir
    )
    return output_file.exists()
```

STEP 4: Filter Foldseek Results
--------------------------------
File: steps/step04_filter_foldseek.py

Algorithm:
1. Parse Foldseek hits
2. Track residue coverage (qres2count)
3. Keep hits where good_res >= 10 (residues with coverage <= 100)
4. Write filtered results

```python
def run_step4(prefix: str, working_dir: Path) -> bool:
    from dpam.io.parsers import parse_foldseek_output
    
    foldseek_file = working_dir / f'{prefix}.foldseek'
    output_file = working_dir / f'{prefix}.foldseek.flt.result'
    
    # Parse hits
    hits = parse_foldseek_output(foldseek_file)
    hits.sort(key=lambda x: x.evalue)
    
    # Track coverage
    fasta_file = working_dir / f'{prefix}.fa'
    _, sequence = read_fasta(fasta_file)
    qres2count = {res: 0 for res in range(1, len(sequence) + 1)}
    
    # Filter hits
    filtered_hits = []
    for hit in hits:
        qresids = hit.get_query_residues()
        for res in qresids:
            qres2count[res] += 1
        
        good_res = sum(1 for res in qresids if qres2count[res] <= 100)
        if good_res >= 10:
            filtered_hits.append(hit)
    
    # Write results
    with open(output_file, 'w') as f:
        f.write('ecodnum\tevalue\trange\n')
        for hit in filtered_hits:
            f.write(f'{hit.ecod_num}\t{hit.evalue}\t{hit.query_start}-{hit.query_end}\n')
    
    return True
```

STEP 5: Map HHsearch Hits to ECOD
----------------------------------
File: steps/step05_map_ecod.py

Algorithm:
1. Parse HHsearch alignments
2. Map PDB chains to ECOD domains using ECOD_pdbmap
3. Calculate coverage and ungapped coverage
4. Write mapping results

Key functions:
- parse_hhsearch_output() -> List[HHSearchAlignment]
- map_to_ecod_domains(alignments, ecod_pdbmap) -> List[mapping]
- calculate_coverage(aligned_residues, domain_length)

STEP 6: Get DALI Candidates
----------------------------
File: steps/step06_dali_candidates.py

Simple step: Merge domains from step 5 and step 4 into hits4Dali file.

```python
def run_step6(prefix: str, working_dir: Path) -> bool:
    domains = set()
    
    # From HHsearch mapping
    map_file = working_dir / f'{prefix}.map2ecod.result'
    if map_file.exists():
        with open(map_file, 'r') as f:
            for line in f:
                if not line.startswith('uid'):
                    domains.add(line.split()[0])
    
    # From Foldseek
    foldseek_file = working_dir / f'{prefix}.foldseek.flt.result'
    if foldseek_file.exists():
        with open(foldseek_file, 'r') as f:
            for line in f:
                if not line.startswith('ecodnum'):
                    domains.add(line.split()[0])
    
    # Write candidates
    output_file = working_dir / f'{prefix}_hits4Dali'
    with open(output_file, 'w') as f:
        for domain in sorted(domains):
            f.write(f'{domain}\n')
    
    return True
```

STEP 7: Iterative DALI (PARALLEL)
----------------------------------
File: steps/step07_iterative_dali.py

**This is a bottleneck step - uses multiprocessing**

```python
from multiprocessing import Pool
from dpam.tools.dali import run_iterative_dali

def process_single_domain(args):
    prefix, edomain, working_dir, data_dir = args
    return run_iterative_dali(
        query_pdb=working_dir / f'{prefix}.pdb',
        template_pdb=data_dir / 'ECOD70' / f'{edomain}.pdb',
        template_ecod=edomain,
        data_dir=data_dir,
        output_dir=working_dir / f'iterativeDali_{prefix}'
    )

def run_step7(prefix: str, working_dir: Path, data_dir: Path, cpus: int = 1) -> bool:
    # Check if already done
    done_file = working_dir / f'{prefix}.iterativeDali.done'
    if done_file.exists():
        return True
    
    # Read candidates
    hits_file = working_dir / f'{prefix}_hits4Dali'
    with open(hits_file, 'r') as f:
        edomains = [line.strip() for line in f]
    
    # Run in parallel
    with Pool(processes=cpus) as pool:
        args = [(prefix, ed, working_dir, data_dir) for ed in edomains]
        results = pool.map(process_single_domain, args)
    
    # Concatenate results
    output_dir = working_dir / f'iterativeDali_{prefix}'
    all_hits_file = working_dir / f'{prefix}_iterativdDali_hits'
    
    with open(all_hits_file, 'w') as outf:
        for hit_file in output_dir.glob(f'{prefix}_*_hits'):
            with open(hit_file, 'r') as inf:
                outf.write(inf.read())
    
    # Mark done
    with open(done_file, 'w') as f:
        f.write('done\n')
    
    return True
```

STEP 8: Analyze DALI Results
-----------------------------
File: steps/step08_analyze_dali.py

Algorithm:
1. Parse DALI hits
2. Load ECOD weights and domain info
3. Calculate q-scores and percentiles (z-tile, q-tile)
4. Rank by position2family mapping
5. Write analyzed results

STEP 9: Get Sequence/Structure Support
---------------------------------------
File: steps/step09_get_support.py

Algorithm:
1. Process sequence hits from step 5:
   - Group by ECOD domain
   - Filter by coverage >= 0.4 and probability >= 50
   - Remove overlaps (keep if 50%+ new residues)
   
2. Process structure hits from step 8:
   - Match with sequence hits by family
   - Calculate best sequence probability and coverage support
   
3. Write sequence_result and structure_result files

STEP 10: Filter Good Domains
-----------------------------
File: steps/step10_filter_domains.py

Algorithm:
1. Load ECOD norms
2. For sequence hits:
   - Filter segments (gap <= 10)
   - Keep segments >= 5 residues
   - Total >= 25 residues
   
3. For structure hits:
   - Calculate normalized z-score
   - Apply judge criteria (rank, qscore, ztile, qtile, znorm, seq support)
   - Filter segments same as sequence
   - Classify seq support (superb/high/medium/low/no)
   
4. Write goodDomains file

STEP 11: Secondary Structure (SSE)
-----------------------------------
File: steps/step11_sse.py

```python
from dpam.tools.dssp import DSSP

def run_step11(prefix: str, working_dir: Path) -> bool:
    dssp = DSSP()
    pdb_file = working_dir / f'{prefix}.pdb'
    fasta_file = working_dir / f'{prefix}.fa'
    
    _, sequence = read_fasta(fasta_file)
    
    sse_dict = dssp.run_and_parse(pdb_file, sequence, working_dir)
    
    # Write SSE file
    sse_file = working_dir / f'{prefix}.sse'
    with open(sse_file, 'w') as f:
        for resid in sorted(sse_dict.keys()):
            sse = sse_dict[resid]
            sse_id = sse.sse_id if sse.sse_id else 'na'
            f.write(f'{resid}\t{sse.amino_acid}\t{sse_id}\t{sse.sse_type}\n')
    
    return True
```

STEP 12: Disorder Prediction
-----------------------------
File: steps/step12_disorder.py

Algorithm:
1. Load SSE assignments
2. Load PAE matrix from JSON
3. Calculate inter-SSE contacts (PAE < 6, sequence separation >= 20)
4. Find windows of 5 residues with:
   - Total contacts <= 5
   - Hit residues (from goodDomains) <= 2
5. Write disorder residues

STEP 13: Parse Domains (COMPLEX)
---------------------------------
File: steps/step13_parse_domains.py

**Most complex step - requires helper functions**

Algorithm:
1. Load inputs:
   - Structure (PDB coordinates)
   - PAE matrix
   - Disorder regions
   - Good domains (HH/DALI scores)
   
2. Calculate probability matrices:
   - PDB distance probability: get_PDB_prob(dist)
   - PAE probability: get_PAE_prob(error)
   - HHS probability: get_HHS_prob(hhpro)
   - DALI probability: get_DALI_prob(daliz)
   - Combined: prob = dist^0.1 * pae^0.1 * hhs^0.4 * dali^0.4
   
3. Initial segmentation (5-residue chunks, exclude disorder)

4. Segment clustering:
   - Calculate mean probability between segments
   - Merge if prob > 0.54
   - Iteratively merge based on intra vs inter probabilities (1.07 threshold)
   
5. Domain refinement v0 → v1:
   - Fill gaps <= 10 residues
   - Keep domains >= 20 residues
   
6. Domain refinement v1 → v2:
   - Remove segments overlapping other domains
   - Keep segments >= 15 good residues
   
7. Write final domains

Key helper functions:
```python
def get_PDB_prob(dist: float) -> float:
    # Binned probability by distance
    
def get_PAE_prob(error: float) -> float:
    # Binned probability by PAE
    
def get_HHS_prob(hhpro: float) -> float:
    # Binned probability by HHsearch score
    
def get_DALI_prob(daliz: float) -> float:
    # Binned probability by DALI z-score
```

IMPLEMENTATION ORDER RECOMMENDATION:
------------------------------------
1. Steps 3-6 (straightforward tool wrappers and parsers)
2. Step 11 (SSE - independent, simple)
3. Step 8 (DALI analysis - complex but no dependencies)
4. Step 7 (Iterative DALI - parallel, test with small set first)
5. Steps 9-10 (Integration and filtering)
6. Step 12 (Disorder - needs PAE and SSE)
7. Step 13 (Final parsing - most complex, needs everything)

TESTING STRATEGY:
-----------------
1. Unit tests for each step with sample data
2. Integration test with 1-2 full AFDB structures
3. Batch test with 10-100 structures
4. Performance profiling on steps 2, 7, 13
5. SLURM array job testing

BACKWARD COMPATIBILITY CHECKLIST:
----------------------------------
- All intermediate file formats match exactly
- Output file column orders preserved
- Numeric precision matches (e.g., 2 decimals for scores)
- Range string format consistent (e.g., "10-50,60-100")
- Error handling produces same exit codes
"""
