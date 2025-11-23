"""
Step 7: Iterative DALI Structural Alignment.

Runs iterative DALI alignment against ECOD70 templates in parallel.
This implementation EXACTLY matches v1.0 behavior for validation.

Algorithm per ECOD domain:
1. Copy query PDB as working file
2. Iteratively align against template:
   - Run DALI, parse z-score and alignments
   - If n_aligned < 20, stop
   - Record hit with alignments
   - Remove aligned residues from query (with gap tolerance)
   - If remaining < 20, stop
3. Write all hits to individual file

All domains processed in parallel using multiprocessing.Pool.
"""

from pathlib import Path
from typing import List, Tuple, Set
from multiprocessing import Pool
import shutil
import time
import os

from dpam.tools.dali import DALI
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.iterative_dali')


def get_domain_range(resids: List[int]) -> str:
    """
    Calculate domain range with gap tolerance - EXACTLY matches v1.0.
    
    This is the v1.0 get_domain_range() function replicated exactly:
    - cutoff = max(5, len(resids) * 0.05)
    - segments split when gap > cutoff
    
    Args:
        resids: List of residue IDs (will be sorted)
    
    Returns:
        Range string like "10-50,60-100"
    """
    resids = sorted(resids)
    
    # Calculate gap tolerance cutoff (v1.0 formula)
    cutoff1 = 5
    cutoff2 = len(resids) * 0.05
    cutoff = max(cutoff1, cutoff2)
    
    # Segment residues by gap tolerance
    segs = []
    for resid in resids:
        if not segs:
            segs.append([resid])
        else:
            if resid > segs[-1][-1] + cutoff:
                segs.append([resid])
            else:
                segs[-1].append(resid)
    
    # Format as range string
    seg_string = []
    for seg in segs:
        start = str(seg[0])
        end = str(seg[-1])
        seg_string.append(start + '-' + end)
    
    return ','.join(seg_string)


def run_dali(args: Tuple) -> bool:
    """
    Run iterative DALI for single ECOD domain - EXACTLY matches v1.0.
    
    This is the worker function for multiprocessing.Pool.
    Replicates v1.0 run_dali() function behavior exactly.
    
    Args:
        args: Tuple of (prefix, edomain, working_dir, data_dir)
    
    Returns:
        True if any hits found
    """
    prefix, edomain, working_dir, data_dir = args
    
    # Setup paths - use absolute paths to avoid directory confusion
    query_pdb = (working_dir / f'{prefix}.pdb').resolve()
    template_pdb_source = (data_dir / 'ECOD70' / f'{edomain}.pdb').resolve()

    # Check files exist
    if not query_pdb.exists():
        logger.error(f"Query PDB not found: {query_pdb}")
        return False

    if not template_pdb_source.exists():
        logger.warning(f"Template not found: {template_pdb_source}")
        return False
    
    # Create working directories - match v1.0 structure
    iterative_dir = working_dir / f'iterativeDali_{prefix}'
    iterative_dir.mkdir(parents=True, exist_ok=True)
    
    tmp_dir = iterative_dir / f'tmp_{prefix}_{edomain}'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    output_tmp_dir = tmp_dir / 'output_tmp'
    output_tmp_dir.mkdir(parents=True, exist_ok=True)

    # Copy query PDB with v1.0 naming - use absolute path
    work_pdb = (tmp_dir / f'{prefix}_{edomain}.pdb').resolve()
    shutil.copy(query_pdb, work_pdb)

    # CRITICAL: Copy template locally to avoid DaliLite 80-char path limit
    template_pdb = (tmp_dir / f'{edomain}.pdb').resolve()
    shutil.copy(template_pdb_source, template_pdb)
    
    # Output file for this domain
    output_file = iterative_dir / f'{prefix}_{edomain}_hits'
    
    # Initialize DALI tool
    dali = DALI()
    
    # Track alignment count
    alicount = 0
    
    # Iterative DALI loop - EXACTLY matches v1.0
    try:
        while True:
            # Run DALI alignment (absolute paths, so no need to change directory)
            # DALI will change to output_tmp_dir internally via cwd parameter
            z_score, alignments = dali.align(
                work_pdb,
                template_pdb,
                output_tmp_dir,
                dat1_dir=Path('./'),
                dat2_dir=Path('./')
            )

            logger.debug(f"{edomain}: DALI returned z={z_score}, alignments={len(alignments) if alignments else 0}")

            if z_score is None or len(alignments) < 20:
                logger.debug(f"No significant alignment for {edomain} (z={z_score}, n={len(alignments) if alignments else 0})")
                break

            # Read current query residues
            with open(work_pdb, 'r') as f:
                Qresids_set = set()
                for line in f:
                    if line.startswith('ATOM'):
                        resid = int(line[22:26])
                        Qresids_set.add(resid)

            Qresids = sorted(Qresids_set)
            qlen = len(Qresids)
            slen = 0  # Template length (not needed in v1.0)
            match = len(alignments)

            # Record hit
            alicount += 1
            with open(output_file, 'a') as f:
                f.write(f'>{edomain}_{alicount}\t{z_score}\t{match}\t{qlen}\t{slen}\n')
                for qind, tind in alignments:
                    # Convert alignment index (1-based) to actual residue ID
                    actual_qresid = Qresids[qind - 1]
                    f.write(f'{actual_qresid}\t{tind}\n')

            logger.debug(f"{edomain}_{alicount}: z={z_score:.2f}, n={match}, q_len={qlen}")

            # Calculate range of aligned residues with gap tolerance
            raw_qresids = [Qresids[q - 1] for q, t in alignments]
            qrange = get_domain_range(raw_qresids)

            # Expand range to remove (includes gaps)
            qresids_to_remove = set()
            qsegs = qrange.split(',')
            for qseg in qsegs:
                qedges = qseg.split('-')
                qstart = int(qedges[0])
                qend = int(qedges[1])
                for qres in range(qstart, qend + 1):
                    qresids_to_remove.add(qres)

            # Calculate remaining residues
            remain_resids = Qresids_set - qresids_to_remove

            if len(remain_resids) < 20:
                logger.debug(f"{edomain}: Insufficient residues remaining ({len(remain_resids)})")
                # Clean output directory before breaking
                for f in output_tmp_dir.glob('*'):
                    if f.is_file():
                        f.unlink()
                break

            # Write new PDB with only remaining residues
            with open(tmp_dir / f'{prefix}_{edomain}.pdb', 'r') as fin:
                with open(tmp_dir / f'{prefix}_{edomain}.pdbnew', 'w') as fout:
                    for line in fin:
                        if line.startswith('ATOM'):
                            resid = int(line[22:26])
                            if resid in remain_resids:
                                fout.write(line)

            # Replace working PDB
            shutil.move(
                str(tmp_dir / f'{prefix}_{edomain}.pdbnew'),
                str(tmp_dir / f'{prefix}_{edomain}.pdb')
            )

            # Clean output directory for next iteration
            for f in output_tmp_dir.glob('*'):
                if f.is_file():
                    f.unlink()

    except Exception as e:
        logger.error(f"{edomain}: Exception in iterative DALI loop: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up temporary directory (match v1.0)
        time.sleep(0.1)  # Small delay to ensure file handles are released
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return alicount > 0


def run_step7(
    prefix: str,
    working_dir: Path,
    data_dir: Path,
    cpus: int = 1
) -> bool:
    """
    Run Step 7: Iterative DALI alignment.
    
    Processes all ECOD domain candidates from step 6 in parallel,
    running iterative DALI for each domain.
    
    Args:
        prefix: Structure prefix
        working_dir: Working directory
        data_dir: Directory containing ECOD70 templates
        cpus: Number of parallel workers
    
    Returns:
        True if successful
    """
    logger.info(f"=== Step 7: Iterative DALI for {prefix} ===")

    # Convert paths to absolute to avoid relative path issues after chdir
    working_dir = Path(working_dir).resolve()
    data_dir = Path(data_dir).resolve()

    # Change to working directory (v1.0 does this)
    original_cwd = os.getcwd()
    if os.getcwd() != str(working_dir):
        os.chdir(working_dir)

    try:
        # Check if already done - use absolute path
        done_file = working_dir / f'{prefix}.iterativeDali.done'
        if done_file.exists():
            logger.info(f"Step 7 already completed for {prefix}")
            return True

        # Create output directory - use absolute path
        iterative_dir = working_dir / f'iterativeDali_{prefix}'
        if not iterative_dir.exists():
            iterative_dir.mkdir(parents=True)

        # Read ECOD domain candidates from step 6 - use absolute path
        hits_file = working_dir / f'{prefix}_hits4Dali'

        # Debug logging to help diagnose path issues
        logger.debug(f"Looking for hits file: {hits_file}")
        logger.debug(f"File exists: {hits_file.exists()}")
        logger.debug(f"Current working directory: {os.getcwd()}")

        if not hits_file.exists():
            logger.error(f"Hits file not found: {hits_file}")
            logger.error(f"Current directory contents: {list(Path('.').glob(f'{prefix}*'))}")
            return False
        
        with open(hits_file, 'r') as f:
            edomains = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Processing {len(edomains)} ECOD domains with {cpus} CPUs")
        
        # Prepare arguments for parallel processing
        inputs = [(prefix, edomain, working_dir, data_dir) for edomain in edomains]
        
        # Run in parallel (match v1.0 multiprocessing pattern)
        with Pool(processes=cpus) as pool:
            results = pool.map(run_dali, inputs)
        
        n_success = sum(1 for r in results if r)
        logger.info(f"Completed DALI for {n_success}/{len(edomains)} domains")
        
        # Concatenate all hits files
        final_file = working_dir / f'{prefix}_iterativdDali_hits'
        with open(final_file, 'w') as outf:
            for hit_file in sorted(iterative_dir.glob(f'{prefix}_*_hits')):
                with open(hit_file, 'r') as inf:
                    outf.write(inf.read())
        
        logger.info(f"Wrote combined hits to {final_file}")

        # Clean up temporary directories (match v1.0)
        for tmp_dir in iterative_dir.glob('tmp_*'):
            shutil.rmtree(tmp_dir, ignore_errors=True)

        # Remove main iterative directory (match v1.0)
        shutil.rmtree(iterative_dir, ignore_errors=True)
        
        # Mark as done
        with open(done_file, 'w') as f:
            f.write('done\n')
        
        logger.info(f"Step 7 completed successfully for {prefix}")
        return True
    
    except Exception as e:
        logger.error(f"Step 7 failed for {prefix}: {e}")
        return False
    
    finally:
        # Restore original directory
        os.chdir(original_cwd)


if __name__ == '__main__':
    """
    Test/debug Step 7 standalone.
    
    Usage:
        python step07_iterative_dali.py <prefix> <working_dir> <data_dir> <cpus>
    """
    import sys
    from dpam.utils.logging_config import setup_logging
    
    if len(sys.argv) < 4:
        print("Usage: python step07_iterative_dali.py <prefix> <working_dir> <data_dir> [cpus]")
        sys.exit(1)
    
    prefix = sys.argv[1]
    working_dir = Path(sys.argv[2])
    data_dir = Path(sys.argv[3])
    cpus = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    
    setup_logging(json_format=False)
    
    success = run_step7(prefix, working_dir, data_dir, cpus)
    sys.exit(0 if success else 1)
