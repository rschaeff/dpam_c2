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
        cmd = [
            self.executable,
            str(input_a3m),
            str(output_a3m),
            '-a3m'
        ]
        
        logger.info(f"Running addss.pl for {input_a3m.name}")
        self._execute(cmd, cwd=working_dir, capture_output=True)
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
    database_dir: Path,
    output_prefix: Path,
    cpus: int = 1,
    working_dir: Optional[Path] = None
) -> Path:
    """
    Run complete HHsearch pipeline: hhblits → addss → hhmake → hhsearch.
    
    Args:
        fasta_file: Input FASTA file
        database_dir: Directory containing databases
        output_prefix: Output file prefix (no extension)
        cpus: Number of CPUs
        working_dir: Working directory
    
    Returns:
        Path to hhsearch output file
    """
    logger.info(f"Starting HHsearch pipeline for {fasta_file.name}")
    
    # Define file paths
    a3m_file = output_prefix.with_suffix('.a3m')
    a3m_ss_file = output_prefix.with_suffix('.a3m.ss')
    hmm_file = output_prefix.with_suffix('.hmm')
    hhsearch_file = output_prefix.with_suffix('.hhsearch')
    
    # Databases
    uniref_db = database_dir / 'UniRef30_2022_02' / 'UniRef30_2022_02'
    pdb70_db = database_dir / 'pdb70' / 'pdb70'
    
    # Run pipeline
    hhblits = HHBlits()
    hhblits.run(fasta_file, uniref_db, a3m_file, cpus, working_dir)
    
    addss = AddSS()
    addss.run(a3m_file, a3m_ss_file, working_dir)
    
    # Replace original A3M with SS-annotated version
    import shutil
    shutil.move(str(a3m_ss_file), str(a3m_file))
    
    hhmake = HHMake()
    hhmake.run(a3m_file, hmm_file, working_dir)
    
    hhsearch = HHSearch()
    hhsearch.run(hmm_file, pdb70_db, hhsearch_file, cpus, 100000, working_dir)
    
    logger.info(f"HHsearch pipeline completed: {hhsearch_file}")
    return hhsearch_file
