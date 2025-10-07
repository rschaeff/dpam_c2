"""
Step 2: Run HHsearch sequence homology search.

Runs hhblits → addss → hhmake → hhsearch pipeline.
"""

from pathlib import Path

from dpam.tools.hhsuite import run_hhsearch_pipeline
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.hhsearch')


def run_step2(
    prefix: str,
    working_dir: Path,
    data_dir: Path = None,
    cpus: int = 1,
    uniref_db: Path = None,
    pdb70_db: Path = None
) -> bool:
    """
    Run Step 2: HHsearch pipeline.

    Args:
        prefix: Structure prefix
        working_dir: Working directory
        data_dir: Directory containing HHsearch databases (legacy)
        cpus: Number of CPUs
        uniref_db: Direct path to UniRef database (optional)
        pdb70_db: Direct path to PDB70 database (optional)

    Returns:
        True if successful
    """
    logger.info(f"=== Step 2: HHsearch for {prefix} ===")

    try:
        fasta_file = working_dir / f'{prefix}.fa'
        output_prefix = working_dir / prefix

        if not fasta_file.exists():
            logger.error(f"FASTA file not found: {fasta_file}")
            return False

        # Run complete pipeline
        hhsearch_file = run_hhsearch_pipeline(
            fasta_file=fasta_file,
            database_dir=data_dir,
            output_prefix=output_prefix,
            cpus=cpus,
            working_dir=working_dir,
            uniref_db=uniref_db,
            pdb70_db=pdb70_db
        )
        
        if hhsearch_file.exists():
            logger.info(f"Step 2 completed successfully for {prefix}")
            return True
        else:
            logger.error(f"HHsearch output not found: {hhsearch_file}")
            return False
    
    except Exception as e:
        logger.error(f"Step 2 failed for {prefix}: {e}")
        return False
