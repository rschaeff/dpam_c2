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

    def run(self, **kwargs):
        """
        Run foldseek easy-search (required by ExternalTool base class).

        Delegates to easy_search method.
        """
        return self.easy_search(**kwargs)

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

        # Foldseek requires OMP_PROC_BIND to be unset
        # SLURM sets this but foldseek refuses to run with it set
        # Use shell wrapper to ensure OMP_PROC_BIND is unset before foldseek starts
        import os
        env = os.environ.copy()
        env.pop('OMP_PROC_BIND', None)  # Remove if present
        env.pop('OMP_NUM_THREADS', None)  # Also remove OMP_NUM_THREADS to be safe

        # Log the current state for debugging
        if 'OMP_PROC_BIND' in os.environ:
            logger.debug(f"OMP_PROC_BIND was set to: {os.environ.get('OMP_PROC_BIND')}")

        logger.info(f"Running foldseek for {query_pdb.name}")

        # Use shell=True with explicit unset to ensure env is clean
        shell_cmd = f"unset OMP_PROC_BIND OMP_NUM_THREADS; {' '.join(cmd)}"
        import subprocess

        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'w') as f:
            result = subprocess.run(
                shell_cmd,
                shell=True,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=working_dir,
                env=env,
                text=True
            )

        if result.returncode != 0:
            logger.error(f"foldseek failed with return code {result.returncode}")
            raise subprocess.CalledProcessError(result.returncode, cmd)
        logger.info(f"Foldseek completed: {output_file}")
        
        # Clean up tmp directory
        import shutil
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
            logger.debug(f"Cleaned up tmp directory: {tmp_dir}")
