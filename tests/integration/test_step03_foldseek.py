"""
Integration tests for Step 3: Foldseek Structure Search.

Tests the Foldseek easy-search pipeline for finding structural homologs.
"""

import pytest
from pathlib import Path
from dpam.steps.step03_foldseek import run_step3


@pytest.mark.integration
@pytest.mark.requires_foldseek
class TestStep03Foldseek:
    """Integration tests for step 3 (foldseek)."""

    @pytest.fixture
    def foldseek_database(self):
        """
        Find Foldseek database or skip test.
        """
        # Check common locations for ECOD_foldseek_DB
        possible_locations = [
            Path('/home/rschaeff/data/dpam_reference/ecod_data'),
            Path('/data/ecod/database_versions/v291'),
        ]

        for data_dir in possible_locations:
            db_path = data_dir / 'ECOD_foldseek_DB'
            # Check for index file to verify database exists
            if (data_dir / 'ECOD_foldseek_DB.index').exists():
                return data_dir

        pytest.skip("ECOD_foldseek_DB database not found")

    def test_foldseek_requires_pdb(self, test_prefix, working_dir, foldseek_database):
        """Test that step 3 fails gracefully without PDB file."""
        # Don't create PDB file
        success = run_step3(
            test_prefix,
            working_dir,
            foldseek_database,
            threads=1
        )

        assert not success, "Step 3 should fail without PDB file"

    def test_foldseek_requires_database(self, test_prefix, working_dir, setup_test_files):
        """Test that step 3 fails gracefully without database."""
        if 'pdb' not in setup_test_files:
            pytest.skip("PDB test file not available")

        # Use non-existent database directory
        fake_data_dir = Path("/nonexistent/database")

        success = run_step3(
            test_prefix,
            working_dir,
            fake_data_dir,
            threads=1
        )

        assert not success, "Step 3 should fail without database"

    @pytest.mark.slow
    def test_foldseek_with_test_structure(self, test_prefix, working_dir,
                                          foldseek_database, setup_test_files):
        """Test Foldseek search with test structure."""
        if 'pdb' not in setup_test_files:
            pytest.skip("PDB test file not available")

        # Run step 3
        success = run_step3(
            test_prefix,
            working_dir,
            foldseek_database,
            threads=2
        )

        assert success, "Step 3 should complete successfully"

        # Check output file exists
        output_file = working_dir / f"{test_prefix}.foldseek"
        assert output_file.exists(), "Foldseek output file should be created"

        # Check output has content
        assert output_file.stat().st_size > 0, "Foldseek output should not be empty"

        # Check that we got some hits
        with open(output_file, 'r') as f:
            n_hits = sum(1 for line in f)

        assert n_hits > 0, "Should find at least some structural hits"

    @pytest.mark.slow
    def test_foldseek_output_format(self, test_prefix, working_dir,
                                    foldseek_database, setup_test_files):
        """Test that Foldseek output has expected format."""
        if 'pdb' not in setup_test_files:
            pytest.skip("PDB test file not available")

        # Run step 3
        success = run_step3(
            test_prefix,
            working_dir,
            foldseek_database,
            threads=2
        )

        assert success

        # Read and validate output format
        output_file = working_dir / f"{test_prefix}.foldseek"
        with open(output_file, 'r') as f:
            first_line = f.readline().strip()

        # Foldseek easy-search output is tab-delimited
        fields = first_line.split('\t')
        assert len(fields) >= 10, "Foldseek output should have at least 10 tab-delimited fields"

        # First field should be query name
        assert fields[0] == test_prefix, "First field should be query name"

        # Second field should be target name (ECOD domain)
        assert len(fields[1]) > 0, "Target field should not be empty"

    @pytest.mark.slow
    def test_foldseek_creates_log(self, test_prefix, working_dir,
                                  foldseek_database, setup_test_files):
        """Test that Foldseek creates log file."""
        if 'pdb' not in setup_test_files:
            pytest.skip("PDB test file not available")

        # Run step 3
        success = run_step3(
            test_prefix,
            working_dir,
            foldseek_database,
            threads=2
        )

        assert success

        # Check for log file
        log_file = working_dir / f"{test_prefix}.foldseek.log"
        assert log_file.exists(), "Foldseek should create log file"

    @pytest.mark.slow
    def test_foldseek_with_multiple_threads(self, test_prefix, working_dir,
                                           foldseek_database, setup_test_files):
        """Test that Foldseek can use multiple threads."""
        if 'pdb' not in setup_test_files:
            pytest.skip("PDB test file not available")

        # Run with 4 threads
        success = run_step3(
            test_prefix,
            working_dir,
            foldseek_database,
            threads=4
        )

        assert success, "Step 3 should work with multiple threads"

        # Output should still be valid
        output_file = working_dir / f"{test_prefix}.foldseek"
        assert output_file.exists()
        assert output_file.stat().st_size > 0

    @pytest.mark.slow
    def test_foldseek_cleans_tmp_directory(self, test_prefix, working_dir,
                                           foldseek_database, setup_test_files):
        """Test that Foldseek cleans up temporary directory."""
        if 'pdb' not in setup_test_files:
            pytest.skip("PDB test file not available")

        # Run step 3
        success = run_step3(
            test_prefix,
            working_dir,
            foldseek_database,
            threads=1
        )

        assert success

        # Check that tmp directory is cleaned up
        tmp_dir = working_dir / "foldseek_tmp"
        assert not tmp_dir.exists(), "Temporary directory should be cleaned up after completion"


@pytest.mark.integration
@pytest.mark.requires_foldseek
class TestStep03Tools:
    """Test Foldseek tool wrapper."""

    def test_foldseek_available(self, foldseek_available):
        """Test that foldseek is available."""
        # This will skip if foldseek is not available
        assert foldseek_available, "foldseek should be available"

    def test_foldseek_wrapper_initialization(self):
        """Test that Foldseek wrapper can be initialized."""
        from dpam.tools.foldseek import Foldseek

        # This will raise if foldseek is not available
        try:
            foldseek = Foldseek()
            assert foldseek.is_available(), "foldseek should be available"
        except RuntimeError as e:
            pytest.skip(f"foldseek not available: {e}")
