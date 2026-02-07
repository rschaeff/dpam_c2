"""
Step 3: Foldseek Structure Search.

Runs Foldseek to find structural homologs in ECOD database.

Single-protein mode uses easy-search (one foldseek invocation per protein).
Batch mode uses createdb + search + convertalis (one invocation for all
proteins, amortizing target DB index loading).
"""

import shutil
from pathlib import Path
from typing import Dict, List

from dpam.tools.foldseek import Foldseek
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.foldseek')


def run_step3(
    prefix: str,
    working_dir: Path,
    data_dir: Path,
    threads: int = 1,
    path_resolver=None
) -> bool:
    """
    Run Step 3: Foldseek structure search.

    Searches query structure against ECOD database using Foldseek
    to find structural similarities.

    Args:
        prefix: Structure prefix
        working_dir: Working directory
        data_dir: Directory containing ECOD_foldseek_DB
        threads: Number of threads
        path_resolver: Optional PathResolver for sharded output directories

    Returns:
        True if successful
    """
    from dpam.core.path_resolver import PathResolver
    resolver = path_resolver or PathResolver(working_dir, sharded=False)

    logger.info(f"=== Step 3: Foldseek Structure Search for {prefix} ===")

    try:
        # Convert to absolute paths
        working_dir = working_dir.resolve()
        data_dir = data_dir.resolve()

        # Input from step 1
        pdb_file = resolver.step_dir(1) / f'{prefix}.pdb'
        if not pdb_file.exists():
            logger.error(f"PDB file not found: {pdb_file}")
            return False

        # Output to step 3 directory
        step3_dir = resolver.step_dir(3)
        output_file = step3_dir / f'{prefix}.foldseek'
        tmp_dir = step3_dir / f'foldseek_tmp_{prefix}'  # Unique per protein to avoid race condition

        # Foldseek database files are in data_dir directly, not in subdirectory
        database = data_dir / 'ECOD_foldseek_DB'

        # Check if database exists
        if not database.exists():
            logger.error(f"Foldseek database not found: {database}")
            return False
        
        # Run Foldseek
        foldseek = Foldseek()
        
        logger.info(
            f"Running Foldseek: {pdb_file.name} vs ECOD database "
            f"(threads={threads})"
        )
        
        foldseek.easy_search(
            query_pdb=pdb_file,
            database=database,
            output_file=output_file,
            tmp_dir=tmp_dir,
            threads=threads,
            evalue=1000000,  # Very permissive e-value
            max_seqs=1000000  # Allow many hits
        )
        
        # Verify output
        if output_file.exists():
            # Count hits
            with open(output_file, 'r') as f:
                n_hits = sum(1 for line in f)
            
            logger.info(
                f"Step 3 completed successfully for {prefix}: "
                f"{n_hits} Foldseek hits found"
            )
            return True
        else:
            logger.error(f"Foldseek output not created: {output_file}")
            return False
    
    except Exception as e:
        logger.error(f"Step 3 failed for {prefix}: {e}")
        logger.exception("Exception details:")
        return False


def run_step3_batch(
    proteins: List[str],
    working_dir: Path,
    data_dir: Path,
    threads: int = 1,
    path_resolver=None
) -> Dict[str, bool]:
    """
    Run Step 3 for multiple proteins using batch foldseek workflow.

    Uses createdb + search + convertalis instead of per-protein easy-search,
    loading the target database index once for all queries.

    Args:
        proteins: List of structure prefixes
        working_dir: Working directory containing PDB files
        data_dir: Directory containing ECOD_foldseek_DB
        threads: Number of threads for foldseek search
        path_resolver: Optional PathResolver for sharded output directories

    Returns:
        Dict mapping protein prefix to success (True/False)
    """
    from dpam.core.path_resolver import PathResolver
    resolver = path_resolver or PathResolver(working_dir, sharded=False)

    logger.info(
        f"=== Step 3 Batch: Foldseek for {len(proteins)} proteins ==="
    )

    working_dir = working_dir.resolve()
    data_dir = data_dir.resolve()
    results: Dict[str, bool] = {}

    # Check database
    database = data_dir / 'ECOD_foldseek_DB'
    if not database.exists():
        logger.error(f"Foldseek database not found: {database}")
        for p in proteins:
            results[p] = False
        return results

    # Filter to proteins that have PDB files (from step 1)
    step1_dir = resolver.step_dir(1)
    valid_proteins = []
    for p in proteins:
        pdb_file = step1_dir / f'{p}.pdb'
        if pdb_file.exists():
            valid_proteins.append(p)
        else:
            logger.warning(f"PDB file not found for {p}, skipping")
            results[p] = False

    if not valid_proteins:
        logger.warning("No valid PDB files found for batch foldseek")
        return results

    # Set up batch directories
    batch_dir = resolver.batch_dir() / '_foldseek_batch'
    query_pdb_dir = batch_dir / 'query_pdbs'
    query_pdb_dir.mkdir(parents=True, exist_ok=True)

    # Output directory for per-protein results
    step3_dir = resolver.step_dir(3)

    try:
        foldseek = Foldseek()

        # Create symlinks to query PDB files
        for p in valid_proteins:
            src = step1_dir / f'{p}.pdb'
            dst = query_pdb_dir / f'{p}.pdb'
            if dst.exists():
                dst.unlink()
            dst.symlink_to(src)

        # Step 1: Create query database
        query_db = batch_dir / 'queryDB'
        logger.info(
            f"Creating query database from {len(valid_proteins)} PDB files..."
        )
        foldseek.createdb(query_pdb_dir, query_db, threads=threads)

        # Step 2: Search all queries against ECOD DB
        result_db = batch_dir / 'resultDB'
        tmp_dir = batch_dir / 'tmp'
        logger.info(
            f"Searching {len(valid_proteins)} queries vs ECOD database "
            f"(threads={threads})..."
        )
        foldseek.search(
            query_db, database, result_db, tmp_dir,
            threads=threads,
            evalue=1000000,
            max_seqs=1000000
        )

        # Step 3: Convert to tabular format
        combined_output = batch_dir / 'all_results.tsv'
        logger.info("Converting alignments to tabular format...")
        foldseek.convertalis(query_db, database, result_db, combined_output)

        # Split combined output into per-protein files
        logger.info("Splitting results into per-protein files...")
        hit_counts = _split_foldseek_results(
            combined_output, step3_dir, valid_proteins
        )

        for p in valid_proteins:
            n_hits = hit_counts.get(p, 0)
            output_file = step3_dir / f'{p}.foldseek'
            if output_file.exists():
                logger.info(f"  {p}: {n_hits} hits")
                results[p] = True
            else:
                logger.error(f"  {p}: output file not created")
                results[p] = False

    except Exception as e:
        logger.error(f"Batch foldseek failed: {e}")
        logger.exception("Exception details:")
        # Mark all remaining proteins as failed
        for p in valid_proteins:
            if p not in results:
                results[p] = False

    finally:
        # Clean up batch directory
        if batch_dir.exists():
            shutil.rmtree(batch_dir)
            logger.debug("Cleaned up batch foldseek directory")

    return results


def _split_foldseek_results(
    combined_file: Path,
    output_dir: Path,
    proteins: List[str]
) -> Dict[str, int]:
    """
    Split combined foldseek output into per-protein files.

    Args:
        combined_file: Combined BLAST-tab output from convertalis
        output_dir: Directory to write per-protein .foldseek files
        proteins: List of expected protein prefixes

    Returns:
        Dict mapping protein prefix to hit count
    """
    # Open file handles for all proteins
    protein_set = set(proteins)
    file_handles: Dict[str, object] = {}
    hit_counts: Dict[str, int] = {p: 0 for p in proteins}

    try:
        for p in proteins:
            file_handles[p] = open(output_dir / f'{p}.foldseek', 'w')

        with open(combined_file, 'r') as f:
            for line in f:
                # Column 1 is the query name (protein prefix)
                query = line.split('\t', 1)[0]
                if query in protein_set:
                    file_handles[query].write(line)
                    hit_counts[query] += 1

    finally:
        for fh in file_handles.values():
            fh.close()

    return hit_counts
