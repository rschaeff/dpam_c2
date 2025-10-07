"""
Foldseek tool wrapper.
"""

from pathlib import Path
from typing import Optional

from dpam.tools.base import ExternalTool
from dpam.utils.logging_config import get_logger

logger = get_logger('tools.foldseek')


class Foldseek(ExternalTool):
    """
    Wrapper for Foldseek structure search tool.
    """
    
    def __init__(self):
        super().__init__('foldseek', check_available=True, required=True)
    
    def easy_search(
        self,
        query_pdb: Path,
        database: Path,
        output_file: Path,
        tmp_dir: Path,
        threads: int = 1,
        evalue: float = 1000000,
        max_seqs: int = 1000000,
        working_dir: Optional[Path] = None
    ) -> None:
        """
        Run foldseek easy-search.
        
        Args:
            query_pdb: Query PDB file
            database: Foldseek database path
            output_file: Output result file
            tmp_dir: Temporary directory for Foldseek
            threads: Number of threads
            evalue: E-value threshold
            max_seqs: Maximum number of sequences
            working_dir: Working directory
        """
        # Create tmp directory
        tmp_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.executable,
            'easy-search',
            str(query_pdb),
            str(database),
            str(output_file),
            str(tmp_dir),
            '-e', str(evalue),
            '--max-seqs', str(max_seqs),
            '--threads', str(threads)
        ]
        
        log_file = output_file.with_suffix('.foldseek.log')
        
        logger.info(f"Running foldseek for {query_pdb.name}")
        self._execute(cmd, cwd=working_dir, log_file=log_file)
        logger.info(f"Foldseek completed: {output_file}")
        
        # Clean up tmp directory
        import shutil
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
            logger.debug(f"Cleaned up tmp directory: {tmp_dir}")
