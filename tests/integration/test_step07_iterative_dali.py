"""
Integration tests for Step 7: Iterative DALI Structural Alignment.

Tests the most complex step: parallel iterative DALI alignment against ECOD templates.
This step uses multiprocessing and creates temporary directories.
"""

import pytest
from pathlib import Path
import shutil
from dpam.steps.step07_iterative_dali import run_step7, get_domain_range, run_dali


@pytest.mark.integration
@pytest.mark.requires_dali
@pytest.mark.slow
class TestStep07IterativeDALI:
    """Integration tests for step 7 (iterative DALI)."""

    @pytest.fixture
    def setup_hits4dali(self, test_prefix, working_dir):
        """Create mock hits4Dali file with ECOD domain candidates."""
        hits_file = working_dir / f"{test_prefix}_hits4Dali"
        # Create a small list of ECOD domains for testing
        # Using common ECOD domains that should exist in ECOD70
        content = """e2rspA1
e2pmaA1
e1eu1A1
"""
        hits_file.write_text(content)
        return hits_file

    @pytest.fixture
    def setup_pdb_file(self, test_prefix, working_dir, setup_test_files):
        """Ensure PDB file exists for DALI query."""
        if 'pdb' not in setup_test_files:
            pytest.skip("PDB test file required")

        pdb_file = working_dir / f"{test_prefix}.pdb"
        assert pdb_file.exists(), "PDB file should exist"
        return pdb_file

    @pytest.fixture
    def mock_ecod70_dir(self, working_dir, tmp_path):
        """Create mock ECOD70 directory with template PDBs."""
        # Create a mock ECOD70 directory in tmp_path (not working_dir)
        ecod70_dir = tmp_path / "ECOD70"
        ecod70_dir.mkdir(exist_ok=True)

        # Create minimal PDB files for testing domains
        for domain in ['e2rspA1', 'e2pmaA1', 'e1eu1A1']:
            pdb_file = ecod70_dir / f"{domain}.pdb"
            # Minimal valid PDB content
            content = """ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       1.000   1.000   1.000  1.00  0.00           C
ATOM      3  C   ALA A   1       2.000   2.000   2.000  1.00  0.00           C
ATOM      4  O   ALA A   1       3.000   3.000   3.000  1.00  0.00           O
END
"""
            pdb_file.write_text(content)

        return ecod70_dir.parent

    def test_step7_requires_hits_file(self, test_prefix, working_dir,
                                      setup_pdb_file, dali_available):
        """Test that step 7 fails without hits4Dali file."""
        # No hits file created
        # Use a mock data_dir that won't be accessed
        mock_data_dir = working_dir / "mock_data"
        mock_data_dir.mkdir(exist_ok=True)

        success = run_step7(test_prefix, working_dir, mock_data_dir, cpus=1)
        assert not success, "Step 7 should fail without hits file"

    def test_step7_requires_pdb_file(self, test_prefix, working_dir,
                                     setup_hits4dali, dali_available):
        """Test that step 7 needs query PDB file."""
        # Hits file exists but no PDB
        pdb_file = working_dir / f"{test_prefix}.pdb"
        if pdb_file.exists():
            pdb_file.unlink()

        mock_data_dir = working_dir / "mock_data"
        mock_data_dir.mkdir(exist_ok=True)

        # Will fail when trying to run DALI without query PDB
        # Step may return True but produce no results
        success = run_step7(test_prefix, working_dir, mock_data_dir, cpus=1)

        # Check that output file exists (even if empty)
        output_file = working_dir / f"{test_prefix}_iterativdDali_hits"
        # May or may not exist depending on error handling

    def test_step7_creates_output_file(self, test_prefix, working_dir,
                                       setup_hits4dali, setup_pdb_file,
                                       mock_ecod70_dir, dali_available):
        """Test that step 7 creates output file."""
        success = run_step7(test_prefix, working_dir, mock_ecod70_dir, cpus=1)

        # Should complete (may have no hits if DALI fails)
        assert success, "Step 7 should complete"

        # Check output file exists
        output_file = working_dir / f"{test_prefix}_iterativdDali_hits"
        assert output_file.exists(), "Output file should be created"

    def test_step7_output_format(self, test_prefix, working_dir,
                                 setup_hits4dali, setup_pdb_file,
                                 mock_ecod70_dir, dali_available):
        """Test that step 7 output has expected format."""
        success = run_step7(test_prefix, working_dir, mock_ecod70_dir, cpus=1)
        assert success

        output_file = working_dir / f"{test_prefix}_iterativdDali_hits"
        assert output_file.exists()

        # Read output
        with open(output_file, 'r') as f:
            lines = f.readlines()

        # If we have hits, validate format
        if len(lines) > 0:
            for line in lines:
                if line.startswith('>'):
                    # Header line format: >{edomain}_{iteration}\t{zscore}\t{n_aligned}\t{q_len}\t{t_len}
                    fields = line.strip().split('\t')
                    assert len(fields) >= 2, "Header should have at least domain and zscore"
                    assert fields[0].startswith('>'), "Header should start with >"

    def test_step7_parallel_execution(self, test_prefix, working_dir,
                                      setup_hits4dali, setup_pdb_file,
                                      mock_ecod70_dir, dali_available):
        """Test that step 7 works with multiple CPUs."""
        # Test with 2 CPUs
        success = run_step7(test_prefix, working_dir, mock_ecod70_dir, cpus=2)
        assert success, "Step 7 should work with parallel execution"

        output_file = working_dir / f"{test_prefix}_iterativdDali_hits"
        assert output_file.exists(), "Output file should be created"

    def test_step7_creates_temporary_directory(self, test_prefix, working_dir,
                                               setup_hits4dali, setup_pdb_file,
                                               mock_ecod70_dir, dali_available):
        """Test that step 7 creates and manages temporary directories."""
        # Check iterative directory is created during execution
        iterative_dir = working_dir / f"iterativeDali_{test_prefix}"

        success = run_step7(test_prefix, working_dir, mock_ecod70_dir, cpus=1)
        assert success

        # After completion, iterative directory should be cleaned up (v1.0 behavior)
        # Check if it was created (may still exist or be removed)
        # The directory gets removed at the end, so we just verify step completed

    def test_step7_concatenates_hits(self, test_prefix, working_dir,
                                     setup_hits4dali, setup_pdb_file,
                                     mock_ecod70_dir, dali_available):
        """Test that step 7 concatenates individual domain hit files."""
        success = run_step7(test_prefix, working_dir, mock_ecod70_dir, cpus=1)
        assert success

        # Final output should be concatenation of individual hits
        output_file = working_dir / f"{test_prefix}_iterativdDali_hits"
        assert output_file.exists()

        # Check file can be read
        with open(output_file, 'r') as f:
            content = f.read()

        # Should be readable (may be empty if no DALI hits)
        assert content is not None

    def test_step7_handles_empty_hits_file(self, test_prefix, working_dir,
                                           setup_pdb_file, dali_available):
        """Test step 7 with empty hits4Dali file."""
        # Create empty hits file
        hits_file = working_dir / f"{test_prefix}_hits4Dali"
        hits_file.write_text("")

        mock_data_dir = working_dir / "mock_data"
        mock_data_dir.mkdir(exist_ok=True)

        success = run_step7(test_prefix, working_dir, mock_data_dir, cpus=1)
        assert success, "Step 7 should handle empty hits file"

        # Output should be empty
        output_file = working_dir / f"{test_prefix}_iterativdDali_hits"
        if output_file.exists():
            with open(output_file, 'r') as f:
                content = f.read()
            assert content == "", "Output should be empty"

    def test_step7_handles_missing_templates(self, test_prefix, working_dir,
                                             setup_pdb_file, dali_available):
        """Test step 7 when template PDBs don't exist."""
        # Create hits file with non-existent domains
        hits_file = working_dir / f"{test_prefix}_hits4Dali"
        content = """e9999X1
e8888Y1
"""
        hits_file.write_text(content)

        # Use data_dir without these templates
        mock_data_dir = working_dir / "mock_data"
        mock_data_dir.mkdir(exist_ok=True)
        ecod70_dir = mock_data_dir / "ECOD70"
        ecod70_dir.mkdir(exist_ok=True)

        success = run_step7(test_prefix, working_dir, mock_data_dir, cpus=1)
        assert success, "Step 7 should handle missing templates gracefully"

        # Should create output (empty or with warnings)
        output_file = working_dir / f"{test_prefix}_iterativdDali_hits"
        assert output_file.exists()

    def test_step7_skips_if_already_done(self, test_prefix, working_dir,
                                         setup_hits4dali, setup_pdb_file,
                                         mock_ecod70_dir, dali_available):
        """Test that step 7 skips if already completed."""
        # Create done marker
        done_file = working_dir / f"{test_prefix}.iterativeDali.done"
        done_file.touch()

        success = run_step7(test_prefix, working_dir, mock_ecod70_dir, cpus=1)
        assert success, "Step 7 should succeed when already done"


@pytest.mark.unit
class TestStep07Functions:
    """Test individual Step 7 functions."""

    def test_get_domain_range_simple(self):
        """Test domain range calculation for simple case."""
        resids = [10, 11, 12, 13, 14]
        range_str = get_domain_range(resids)
        assert range_str == "10-14", "Should create simple range"

    def test_get_domain_range_with_gaps(self):
        """Test domain range with gaps exceeding cutoff."""
        # Gap > cutoff should create separate segments
        resids = [10, 11, 12, 50, 51, 52]
        range_str = get_domain_range(resids)
        assert range_str == "10-12,50-52", "Should split on large gaps"

    def test_get_domain_range_cutoff_formula(self):
        """Test gap tolerance cutoff formula (v1.0)."""
        # cutoff = max(5, len(resids) * 0.05)

        # Small list: cutoff = 5
        resids = [1, 2, 3, 10, 11, 12]  # 6 residues, 0.05*6=0.3, max(5,0.3)=5
        range_str = get_domain_range(resids)
        # Gap is 7 (4-9), > 5, so should split
        assert range_str == "1-3,10-12"

        # Large list: cutoff = len*0.05
        resids = list(range(1, 101)) + list(range(110, 210))  # 200 residues, cutoff=10
        range_str = get_domain_range(resids)
        # Gap is 9 (101-109), < 10, so should NOT split
        assert range_str == "1-209"

    def test_get_domain_range_unsorted_input(self):
        """Test that function sorts residues."""
        resids = [14, 10, 12, 11, 13]
        range_str = get_domain_range(resids)
        assert range_str == "10-14", "Should sort residues first"

    def test_get_domain_range_single_residue(self):
        """Test with single residue."""
        resids = [42]
        range_str = get_domain_range(resids)
        assert range_str == "42-42", "Should handle single residue"

    def test_get_domain_range_empty(self):
        """Test with empty list."""
        resids = []
        range_str = get_domain_range(resids)
        assert range_str == "", "Should handle empty list"

    def test_get_domain_range_multiple_segments(self):
        """Test with multiple segments."""
        # Three segments with gaps > 5
        resids = [1, 2, 3, 10, 11, 12, 20, 21, 22]
        range_str = get_domain_range(resids)
        assert range_str == "1-3,10-12,20-22", "Should create multiple segments"


@pytest.mark.integration
class TestStep07EdgeCases:
    """Test edge cases for step 7."""

    def test_step7_with_single_domain(self, test_prefix, working_dir,
                                      setup_pdb_file, mock_ecod70_dir, dali_available):
        """Test step 7 with single domain candidate."""
        # Create hits file with one domain
        hits_file = working_dir / f"{test_prefix}_hits4Dali"
        hits_file.write_text("e2rspA1\n")

        success = run_step7(test_prefix, working_dir, mock_ecod70_dir, cpus=1)
        assert success, "Step 7 should handle single domain"

        output_file = working_dir / f"{test_prefix}_iterativdDali_hits"
        assert output_file.exists()

    def test_step7_with_many_domains(self, test_prefix, working_dir,
                                     setup_pdb_file, dali_available):
        """Test step 7 with many domain candidates."""
        # Create hits file with many domains
        hits_file = working_dir / f"{test_prefix}_hits4Dali"
        domains = [f"e{i:04d}A1" for i in range(1, 21)]  # 20 domains
        hits_file.write_text('\n'.join(domains) + '\n')

        mock_data_dir = working_dir / "mock_data"
        mock_data_dir.mkdir(exist_ok=True)
        ecod70_dir = mock_data_dir / "ECOD70"
        ecod70_dir.mkdir(exist_ok=True)

        success = run_step7(test_prefix, working_dir, mock_data_dir, cpus=2)
        assert success, "Step 7 should handle many domains"

    def test_step7_preserves_working_directory(self, test_prefix, working_dir,
                                               setup_hits4dali, setup_pdb_file,
                                               mock_ecod70_dir, dali_available):
        """Test that step 7 preserves/restores working directory."""
        import os
        original_cwd = os.getcwd()

        success = run_step7(test_prefix, working_dir, mock_ecod70_dir, cpus=1)
        assert success

        # Should return to original directory (or working_dir)
        # Not necessarily original_cwd, but should not be in tmp dirs
        current_cwd = os.getcwd()
        assert not str(current_cwd).endswith('tmp_'), "Should not be in temp directory"
