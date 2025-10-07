"""
Step 3: Foldseek Structure Search.

Runs Foldseek easy-search to find structural homologs in ECOD database.
"""

from pathlib import Path

from dpam.tools.foldseek import Foldseek
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.foldseek')


def run_step3(
    prefix: str,
    working_dir: Path,
    data_dir: Path,
    threads: int = 1
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
    
    Returns:
        True if successful
    """
    logger.info(f"=== Step 3: Foldseek Structure Search for {prefix} ===")
    
    try:
        # Check input files
        pdb_file = working_dir / f'{prefix}.pdb'
        if not pdb_file.exists():
            logger.error(f"PDB file not found: {pdb_file}")
            return False
        
        # Define output and database paths
        output_file = working_dir / f'{prefix}.foldseek'
        tmp_dir = working_dir / 'foldseek_tmp'
        database = data_dir / 'ECOD_foldseek_DB' / 'ECOD_foldseek_DB'
        
        # Check if database exists
        if not (data_dir / 'ECOD_foldseek_DB').exists():
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
            max_seqs=1000000,  # Allow many hits
            working_dir=working_dir
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
