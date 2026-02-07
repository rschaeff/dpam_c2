"""
Foldseek tool wrapper.

Supports both single-query (easy-search) and batch (createdb + search +
convertalis) workflows.
"""

import os
from pathlib import Path
from typing import Optional

from dpam.tools.base import ExternalTool
from dpam.utils.logging_config import get_logger

logger = get_logger('tools.foldseek')


class Foldseek(ExternalTool):
    """
    Wrapper for Foldseek structure search tool.

    For single proteins, use easy_search() (convenience wrapper).
    For batch processing, use createdb() + search() + convertalis()
    to amortize index loading across many queries.
    """

    def __init__(self):
        super().__init__('foldseek', check_available=True, required=True)

    def _get_env(self):
        """Get environment with OMP_PROC_BIND=false for SLURM compatibility."""
        env = os.environ.copy()
        env['OMP_PROC_BIND'] = 'false'
        return env

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

    def createdb(
        self,
        input_path: Path,
        output_db: Path,
        threads: int = 1
    ) -> None:
        """
        Create a foldseek structure database from PDB/mmCIF files.

        Args:
            input_path: Directory containing PDB files, or TSV list file
            output_db: Output database path (without extension)
            threads: Number of threads
        """
        cmd = [
            self.executable, 'createdb',
            str(input_path),
            str(output_db),
            '--threads', str(threads),
            '-v', '0'
        ]

        log_file = Path(str(output_db) + '.createdb.log')
        self._execute(cmd, log_file=log_file, env=self._get_env())

        if not Path(str(output_db)).exists():
            raise RuntimeError(f"foldseek createdb failed: {output_db} not created")

        logger.info(f"Created query database: {output_db}")

    def search(
        self,
        query_db: Path,
        target_db: Path,
        result_db: Path,
        tmp_dir: Path,
        threads: int = 1,
        evalue: float = 1000000,
        max_seqs: int = 1000000
    ) -> None:
        """
        Run foldseek search (query DB vs target DB).

        Args:
            query_db: Query database path
            target_db: Target database path
            result_db: Output result database path
            tmp_dir: Temporary directory
            threads: Number of threads
            evalue: E-value threshold
            max_seqs: Maximum sequences per query
        """
        tmp_dir = Path(tmp_dir)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.executable, 'search',
            str(query_db),
            str(target_db),
            str(result_db),
            str(tmp_dir),
            '-e', str(evalue),
            '--max-seqs', str(max_seqs),
            '--threads', str(threads),
            '-v', '0'
        ]

        log_file = Path(str(result_db) + '.search.log')
        self._execute(cmd, log_file=log_file, env=self._get_env())

        logger.info(f"Search complete: results in {result_db}")

    def convertalis(
        self,
        query_db: Path,
        target_db: Path,
        result_db: Path,
        output_file: Path
    ) -> None:
        """
        Convert foldseek result database to BLAST-tab format.

        Args:
            query_db: Query database path
            target_db: Target database path
            result_db: Result database path
            output_file: Output TSV file
        """
        cmd = [
            self.executable, 'convertalis',
            str(query_db),
            str(target_db),
            str(result_db),
            str(output_file),
            '-v', '0'
        ]

        log_file = Path(str(output_file) + '.convertalis.log')
        self._execute(cmd, log_file=log_file, env=self._get_env())

        logger.info(f"Converted alignments to {output_file}")
