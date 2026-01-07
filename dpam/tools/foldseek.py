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

        # Foldseek requires OMP_PROC_BIND to be unset or set to "false"
        #
        # Background: Foldseek/MMseqs2 checks for OMP_PROC_BIND in two ways:
        # - OpenMP 4.0+: Uses omp_get_proc_bind() runtime function
        # - Older OpenMP: Uses getenv("OMP_PROC_BIND")
        #
        # The omp_get_proc_bind() function returns the OpenMP runtime's binding state,
        # which can be affected by SLURM's CPU affinity settings at the cgroup level.
        # Simply unsetting OMP_PROC_BIND doesn't work because the OpenMP runtime
        # has already initialized with affinity enabled.
        #
        # Solution: Set OMP_PROC_BIND=false BEFORE foldseek starts. This tells the
        # OpenMP runtime to disable thread binding, making omp_get_proc_bind()
        # return omp_proc_bind_false, which passes foldseek's check.
        #
        # See: lib/mmseqs/src/commons/CommandCaller.cpp in foldseek source
        import os
        import subprocess

        # Log the current state for debugging
        if 'OMP_PROC_BIND' in os.environ:
            logger.debug(f"OMP_PROC_BIND was set to: {os.environ.get('OMP_PROC_BIND')}")

        logger.info(f"Running foldseek for {query_pdb.name}")

        # Set OMP_PROC_BIND=false to disable OpenMP thread binding
        # This is required for SLURM compatibility where CPU affinity may be set
        env_cmd = ['env', 'OMP_PROC_BIND=false'] + cmd

        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'w') as f:
            result = subprocess.run(
                env_cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=working_dir,
                text=True
            )

        if result.returncode != 0:
            # Check if output was still produced (foldseek returns 1 for OMP_PROC_BIND warning
            # but still completes successfully)
            if output_file.exists() and output_file.stat().st_size > 0:
                logger.warning(
                    f"foldseek returned code {result.returncode} but output exists "
                    f"({output_file.stat().st_size} bytes) - treating as success"
                )
            else:
                logger.error(f"foldseek failed with return code {result.returncode}")
                raise subprocess.CalledProcessError(result.returncode, cmd)
        logger.info(f"Foldseek completed: {output_file}")
        
        # Clean up tmp directory
        import shutil
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
            logger.debug(f"Cleaned up tmp directory: {tmp_dir}")
