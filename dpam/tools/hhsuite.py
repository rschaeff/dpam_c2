"""
HHsuite tool wrappers.

Wrappers for hhblits, hhmake, hhsearch, and addss.pl
"""

from pathlib import Path
from typing import Optional
import subprocess

from dpam.tools.base import ExternalTool
from dpam.utils.logging_config import get_logger

logger = get_logger('tools.hhsuite')


class HHBlits(ExternalTool):
    """
    Wrapper for hhblits (profile building).
    """
    
    def __init__(self):
        super().__init__('hhblits', check_available=True, required=True)
    
    def run(
        self,
        fasta_file: Path,
        database: Path,
        output_a3m: Path,
        cpus: int = 1,
        working_dir: Optional[Path] = None
    ) -> None:
        """
        Run hhblits to build MSA.
        
        Args:
            fasta_file: Input FASTA file
            database: HHblits database path (without extension)
            output_a3m: Output A3M file
            cpus: Number of CPUs
            working_dir: Working directory
        """
        cmd = [
            self.executable,
            '-cpu', str(cpus),
            '-i', str(fasta_file),
            '-d', str(database),
            '-oa3m', str(output_a3m)
        ]
        
        log_file = output_a3m.with_suffix('.hhblits.log')
        
        logger.info(f"Running hhblits for {fasta_file.name}")
        self._execute(cmd, cwd=working_dir, log_file=log_file)
        logger.info(f"hhblits completed: {output_a3m}")


class AddSS(ExternalTool):
    """
    Wrapper for addss.pl (add secondary structure to A3M).
    """

    def __init__(self):
        super().__init__('addss.pl', check_available=True, required=True)

    def run(
        self,
        input_a3m: Path,
        output_a3m: Path,
        working_dir: Optional[Path] = None
    ) -> None:
        """
        Add secondary structure prediction to A3M.

        Args:
            input_a3m: Input A3M file
            output_a3m: Output A3M file with SS
            working_dir: Working directory
        """
        import os
        import shutil
        env = os.environ.copy()

        # Find HHsuite installation directory from addss.pl path
        addss_full_path = shutil.which(self.executable)
        if addss_full_path:
            addss_path = Path(addss_full_path).resolve()
        else:
            addss_path = Path(self.executable).resolve()

        scripts_dir = addss_path.parent
        hhsuite_dir = scripts_dir.parent  # /sw/apps/hh-suite

        # Use DPAM's custom HHPaths.pm with conda PSIPRED paths
        dpam_tools_dir = Path(__file__).parent.resolve()

        # Build command with explicit perl -I flags to ensure correct HHPaths.pm loading
        # Our custom HHPaths.pm must come FIRST to override system version
        cmd = [
            'perl',
            f'-I{dpam_tools_dir}',
            f'-I{scripts_dir}',
            str(addss_path),
            str(input_a3m),
            str(output_a3m),
            '-a3m'
        ]

        # Set HHLIB to DPAM's tools directory so addss.pl's "use lib $ENV{HHLIB}/scripts"
        # finds our custom HHPaths.pm (which uses conda PSIPRED paths)
        env['HHLIB'] = str(dpam_tools_dir)

        # Ensure CONDA_PREFIX is set for our custom HHPaths.pm
        if 'CONDA_PREFIX' not in env:
            # Try to detect conda prefix from psipred location
            psipred_path = shutil.which('psipred')
            if psipred_path:
                conda_prefix = Path(psipred_path).parent.parent
                env['CONDA_PREFIX'] = str(conda_prefix)
                logger.debug(f"Auto-detected CONDA_PREFIX={conda_prefix}")

        logger.info(f"Running addss.pl for {input_a3m.name}")
        logger.debug(f"Using HHPaths.pm from {dpam_tools_dir}, HHLIB={env['HHLIB']}, CONDA_PREFIX={env.get('CONDA_PREFIX', 'not set')}")
        self._execute(cmd, cwd=working_dir, capture_output=True, env=env)
        logger.info(f"addss.pl completed: {output_a3m}")


class HHMake(ExternalTool):
    """
    Wrapper for hhmake (build HMM from A3M).
    """
    
    def __init__(self):
        super().__init__('hhmake', check_available=True, required=True)
    
    def run(
        self,
        input_a3m: Path,
        output_hmm: Path,
        working_dir: Optional[Path] = None
    ) -> None:
        """
        Build HMM from A3M.
        
        Args:
            input_a3m: Input A3M file
            output_hmm: Output HMM file
            working_dir: Working directory
        """
        cmd = [
            self.executable,
            '-i', str(input_a3m),
            '-o', str(output_hmm)
        ]
        
        log_file = output_hmm.with_suffix('.hhmake.log')
        
        logger.info(f"Running hhmake for {input_a3m.name}")
        self._execute(cmd, cwd=working_dir, log_file=log_file)
        logger.info(f"hhmake completed: {output_hmm}")


class HHSearch(ExternalTool):
    """
    Wrapper for hhsearch (search HMM against database).
    """
    
    def __init__(self):
        super().__init__('hhsearch', check_available=True, required=True)
    
    def run(
        self,
        input_hmm: Path,
        database: Path,
        output_file: Path,
        cpus: int = 1,
        max_hits: int = 100000,
        working_dir: Optional[Path] = None
    ) -> None:
        """
        Search HMM against database.
        
        Args:
            input_hmm: Input HMM file
            database: HHsearch database path
            output_file: Output file
            cpus: Number of CPUs
            max_hits: Maximum number of hits
            working_dir: Working directory
        """
        cmd = [
            self.executable,
            '-cpu', str(cpus),
            '-Z', str(max_hits),
            '-B', str(max_hits),
            '-i', str(input_hmm),
            '-d', str(database),
            '-o', str(output_file)
        ]
        
        logger.info(f"Running hhsearch for {input_hmm.name}")
        self._execute(cmd, cwd=working_dir, capture_output=True)
        logger.info(f"hhsearch completed: {output_file}")


def run_hhsearch_pipeline(
    fasta_file: Path,
    database_dir: Optional[Path] = None,
    output_prefix: Optional[Path] = None,
    cpus: int = 1,
    working_dir: Optional[Path] = None,
    uniref_db: Optional[Path] = None,
    pdb70_db: Optional[Path] = None,
    skip_addss: bool = False
) -> Path:
    """
    Run complete HHsearch pipeline: hhblits → (addss) → hhmake → hhsearch.

    Args:
        fasta_file: Input FASTA file
        database_dir: Directory containing databases (legacy, auto-finds DBs)
        output_prefix: Output file prefix (no extension)
        cpus: Number of CPUs
        working_dir: Working directory
        uniref_db: Direct path to UniRef database (overrides database_dir)
        pdb70_db: Direct path to PDB70 database (overrides database_dir)
        skip_addss: Skip addss.pl (secondary structure prediction). Default False.
                    Requires PSIPRED in conda environment. Set True to skip.

    Returns:
        Path to hhsearch output file
    """
    logger.info(f"Starting HHsearch pipeline for {fasta_file.name}")

    # Define file paths
    if output_prefix is None:
        output_prefix = fasta_file.with_suffix('')

    a3m_file = output_prefix.with_suffix('.a3m')
    a3m_ss_file = output_prefix.with_suffix('.a3m.ss')
    hmm_file = output_prefix.with_suffix('.hmm')
    hhsearch_file = output_prefix.with_suffix('.hhsearch')

    # Determine database paths
    if uniref_db is None and database_dir is not None:
        # Legacy mode: construct from database_dir
        # Try 2023 version first (symlinked), fallback to 2022
        uniref_2023 = database_dir / 'UniRef30_2023_02'
        if (uniref_2023.parent / f'{uniref_2023.name}_cs219.ffdata').exists():
            uniref_db = uniref_2023
        else:
            uniref_db = database_dir / 'UniRef30_2022_02' / 'UniRef30_2022_02'

    if pdb70_db is None and database_dir is not None:
        # Legacy mode: construct from database_dir
        # Try symlinked version first
        pdb70_direct = database_dir / 'pdb70'
        if (pdb70_direct.parent / f'{pdb70_direct.name}_cs219.ffdata').exists():
            pdb70_db = pdb70_direct
        else:
            pdb70_db = database_dir / 'pdb70' / 'pdb70'

    if uniref_db is None or pdb70_db is None:
        raise ValueError("Must provide either database_dir or both uniref_db and pdb70_db")
    
    # Run pipeline
    hhblits = HHBlits()
    hhblits.run(fasta_file, uniref_db, a3m_file, cpus, working_dir)

    # Secondary structure prediction (optional, requires PSIPRED)
    if not skip_addss:
        addss = AddSS()
        addss.run(a3m_file, a3m_ss_file, working_dir)

        # Replace original A3M with SS-annotated version
        import shutil
        shutil.move(str(a3m_ss_file), str(a3m_file))
    else:
        logger.warning(
            "Skipping addss.pl (secondary structure prediction). "
            "This may affect result quality and compatibility with DPAM v1.0. "
            "To enable, set skip_addss=False and ensure PSIPRED is installed."
        )
    
    hhmake = HHMake()
    hhmake.run(a3m_file, hmm_file, working_dir)
    
    hhsearch = HHSearch()
    hhsearch.run(hmm_file, pdb70_db, hhsearch_file, cpus, 100000, working_dir)
    
    logger.info(f"HHsearch pipeline completed: {hhsearch_file}")
    return hhsearch_file
