"""
Test foldseek OMP_PROC_BIND environment variable handling.

This test verifies that foldseek works correctly even when OMP_PROC_BIND
is set in the environment (as SLURM does by default). The foldseek tool
wrapper sets OMP_PROC_BIND=false before calling foldseek.

Background on the fix:
- Foldseek/MMseqs2 checks OMP_PROC_BIND using omp_get_proc_bind() for OpenMP 4.0+
- Simply unsetting the env var doesn't work because the OpenMP runtime may already
  have affinity enabled via SLURM's cgroup-level CPU binding
- Setting OMP_PROC_BIND=false tells the OpenMP runtime to disable thread binding,
  which makes omp_get_proc_bind() return omp_proc_bind_false
- See: lib/mmseqs/src/commons/CommandCaller.cpp in foldseek source
"""

import os
import pytest
from pathlib import Path
import tempfile
import shutil

from dpam.tools.foldseek import Foldseek


@pytest.fixture
def test_structure():
    """
    Provide path to a test structure file.

    Foldseek requires PDB format, so prefer PDB files over CIF.
    """
    # Try to find PDB files from validation or test data
    test_dirs = [
        Path('validation_1000_run'),  # PDB files from step 1
        Path('validation/working'),
        Path('test_run'),
        Path('validation_run'),
    ]

    for test_dir in test_dirs:
        if test_dir.exists():
            # Prefer PDB files (foldseek requirement)
            pdb_files = list(test_dir.glob('*.pdb'))
            if pdb_files:
                # Use smallest file for faster tests
                smallest = min(pdb_files, key=lambda p: p.stat().st_size)
                return smallest

    pytest.skip("No test PDB structure file available")


@pytest.fixture
def foldseek_db():
    """Provide path to foldseek database."""
    db_path = Path('/home/rschaeff_1/data/dpam_reference/ecod_data/ECOD_foldseek_DB')

    if not db_path.exists():
        pytest.skip("Foldseek database not available")

    return db_path


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for test outputs."""
    tmpdir = tempfile.mkdtemp(prefix='test_foldseek_')
    yield Path(tmpdir)
    shutil.rmtree(tmpdir)


class TestFoldseekOMPProcBind:
    """Test suite for foldseek OMP_PROC_BIND handling."""

    def test_foldseek_available(self):
        """Test that foldseek executable is available."""
        fs = Foldseek()
        assert fs.is_available(), "Foldseek not found in PATH"

    def test_foldseek_without_omp_proc_bind(
        self,
        test_structure,
        foldseek_db,
        temp_workspace
    ):
        """
        Test foldseek works normally without OMP_PROC_BIND set.

        This is the baseline test - foldseek should work fine when
        OMP_PROC_BIND is not in the environment.
        """
        # Ensure OMP_PROC_BIND is not set
        original_value = os.environ.pop('OMP_PROC_BIND', None)

        try:
            fs = Foldseek()

            output_file = temp_workspace / 'test_output.foldseek'
            tmp_dir = temp_workspace / 'foldseek_tmp'

            # Should complete without error
            fs.easy_search(
                query_pdb=test_structure,
                database=foldseek_db,
                output_file=output_file,
                tmp_dir=tmp_dir,
                threads=2,
                evalue=1000000,
                max_seqs=100,  # Limit results for faster test
                working_dir=temp_workspace
            )

            # Verify output was created
            assert output_file.exists(), "Foldseek output file not created"
            assert output_file.stat().st_size > 0, "Foldseek output file is empty"

        finally:
            # Restore original value if it was set
            if original_value is not None:
                os.environ['OMP_PROC_BIND'] = original_value

    def test_foldseek_with_omp_proc_bind_true(
        self,
        test_structure,
        foldseek_db,
        temp_workspace
    ):
        """
        Test foldseek works when OMP_PROC_BIND='true' (SLURM default).

        This is the critical test - foldseek fails without our fix when
        OMP_PROC_BIND is set. Our wrapper sets OMP_PROC_BIND=false to
        disable OpenMP thread binding before calling foldseek.
        """
        # Set OMP_PROC_BIND as SLURM does
        original_value = os.environ.get('OMP_PROC_BIND')
        os.environ['OMP_PROC_BIND'] = 'true'

        try:
            fs = Foldseek()

            output_file = temp_workspace / 'test_output_with_omp.foldseek'
            tmp_dir = temp_workspace / 'foldseek_tmp_omp'

            # Should complete without error despite OMP_PROC_BIND being set
            # Our fix in foldseek.py should unset it before calling foldseek
            fs.easy_search(
                query_pdb=test_structure,
                database=foldseek_db,
                output_file=output_file,
                tmp_dir=tmp_dir,
                threads=2,
                evalue=1000000,
                max_seqs=100,
                working_dir=temp_workspace
            )

            # Verify output was created
            assert output_file.exists(), "Foldseek output file not created with OMP_PROC_BIND set"
            assert output_file.stat().st_size > 0, "Foldseek output file is empty with OMP_PROC_BIND set"

        finally:
            # Restore original value
            if original_value is not None:
                os.environ['OMP_PROC_BIND'] = original_value
            else:
                os.environ.pop('OMP_PROC_BIND', None)

    def test_foldseek_with_various_omp_proc_bind_values(
        self,
        test_structure,
        foldseek_db,
        temp_workspace
    ):
        """
        Test foldseek works with various OMP_PROC_BIND values.

        SLURM can set OMP_PROC_BIND to different values depending on
        configuration. Test that our fix works for all of them.
        """
        test_values = ['true', 'false', 'close', 'master', 'spread']

        for value in test_values:
            original_value = os.environ.get('OMP_PROC_BIND')
            os.environ['OMP_PROC_BIND'] = value

            try:
                fs = Foldseek()

                output_file = temp_workspace / f'test_output_{value}.foldseek'
                tmp_dir = temp_workspace / f'foldseek_tmp_{value}'

                # Should work with any OMP_PROC_BIND value
                fs.easy_search(
                    query_pdb=test_structure,
                    database=foldseek_db,
                    output_file=output_file,
                    tmp_dir=tmp_dir,
                    threads=2,
                    evalue=1000000,
                    max_seqs=100,
                    working_dir=temp_workspace
                )

                assert output_file.exists(), f"Foldseek failed with OMP_PROC_BIND={value}"

            finally:
                if original_value is not None:
                    os.environ['OMP_PROC_BIND'] = original_value
                else:
                    os.environ.pop('OMP_PROC_BIND', None)

    def test_omp_proc_bind_not_leaked(
        self,
        test_structure,
        foldseek_db,
        temp_workspace
    ):
        """
        Test that setting OMP_PROC_BIND=false doesn't affect parent process.

        Verify that our modification of the environment for foldseek
        doesn't leak back to the calling process.
        """
        # Set OMP_PROC_BIND
        os.environ['OMP_PROC_BIND'] = 'true'

        try:
            fs = Foldseek()

            output_file = temp_workspace / 'test_no_leak.foldseek'
            tmp_dir = temp_workspace / 'foldseek_tmp_no_leak'

            # Run foldseek
            fs.easy_search(
                query_pdb=test_structure,
                database=foldseek_db,
                output_file=output_file,
                tmp_dir=tmp_dir,
                threads=2,
                evalue=1000000,
                max_seqs=100,
                working_dir=temp_workspace
            )

            # Verify OMP_PROC_BIND is still set in parent process
            assert 'OMP_PROC_BIND' in os.environ, "OMP_PROC_BIND was removed from parent process"
            assert os.environ['OMP_PROC_BIND'] == 'true', "OMP_PROC_BIND value changed in parent process"

        finally:
            os.environ.pop('OMP_PROC_BIND', None)


@pytest.mark.slow
class TestFoldseekIntegration:
    """
    Integration tests for foldseek (slower, run full searches).

    Mark these as slow so they can be skipped with: pytest -m "not slow"
    """

    def test_foldseek_full_search_with_slurm_env(
        self,
        test_structure,
        foldseek_db,
        temp_workspace
    ):
        """
        Test full foldseek search with SLURM environment variables set.

        This simulates the actual SLURM environment more completely.
        """
        # Set multiple SLURM-related environment variables
        slurm_env = {
            'OMP_PROC_BIND': 'true',
            'SLURM_JOB_ID': '12345',
            'SLURM_CPUS_PER_TASK': '8',
            'SLURM_ARRAY_TASK_ID': '0',
        }

        original_values = {}
        for key, value in slurm_env.items():
            original_values[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            fs = Foldseek()

            output_file = temp_workspace / 'test_slurm_env.foldseek'
            tmp_dir = temp_workspace / 'foldseek_tmp_slurm'

            # Run with full SLURM environment
            fs.easy_search(
                query_pdb=test_structure,
                database=foldseek_db,
                output_file=output_file,
                tmp_dir=tmp_dir,
                threads=8,
                evalue=1000000,
                max_seqs=1000000,  # Full search
                working_dir=temp_workspace
            )

            # Verify results
            assert output_file.exists(), "Foldseek failed in SLURM environment"

            # Check that we got reasonable results
            with open(output_file) as f:
                lines = f.readlines()
                assert len(lines) > 0, "No foldseek results produced"

        finally:
            # Restore original environment
            for key, value in original_values.items():
                if value is not None:
                    os.environ[key] = value
                else:
                    os.environ.pop(key, None)
