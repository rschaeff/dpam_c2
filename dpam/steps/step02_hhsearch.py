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
    pdb70_db: Path = None,
    skip_addss: bool = False,
    path_resolver=None
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
        skip_addss: Skip addss.pl secondary structure prediction (default False).
                    Set True when PSIPRED is not available.
        path_resolver: Optional PathResolver for sharded output directories

    Returns:
        True if successful
    """
    from dpam.core.path_resolver import PathResolver
    resolver = path_resolver or PathResolver(working_dir, sharded=False)

    logger.info(f"=== Step 2: HHsearch for {prefix} ===")

    try:
        # Convert to absolute paths
        working_dir = working_dir.resolve()
        if data_dir:
            data_dir = data_dir.resolve()

        # Input from step 1
        fasta_file = resolver.step_dir(1) / f'{prefix}.fa'
        # Output to step 2 directory
        step2_dir = resolver.step_dir(2)
        output_prefix = step2_dir / prefix

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
            pdb70_db=pdb70_db,
            skip_addss=skip_addss
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
