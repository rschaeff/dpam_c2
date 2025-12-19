"""
Integration tests for Step 20: Extract Domain PDB Files.

Tests extraction of individual domain PDB files for structural comparison.
"""

import pytest
from pathlib import Path
from dpam.steps.step20_extract_domains import run_step20, extract_domain_pdb


@pytest.mark.integration
class TestStep20ExtractDomains:
    """Integration tests for step 20 (extract domain PDB files)."""

    def test_step20_requires_step19_output(self, test_prefix, working_dir):
        """Test that step 20 gracefully skips without step 19 output."""
        success = run_step20(test_prefix, working_dir)
        assert success, "Step 20 should gracefully skip with missing merge candidates"

    def test_step20_requires_pdb_file(self, test_prefix, working_dir):
        """Test that step 20 fails without structure file."""
        # Create merge candidates but no PDB
        (working_dir / f"{test_prefix}.step19_merge_candidates").write_text(
            "# domain1\trange1\tdomain2\trange2\n"
            "dom1\t10-50\tdom2\t60-100\n"
        )

        success = run_step20(test_prefix, working_dir)
        assert not success, "Step 20 should fail without structure file"

    def test_step20_with_valid_inputs(self, test_prefix, working_dir, setup_step20_inputs):
        """Test step 20 with valid inputs."""
        if not setup_step20_inputs:
            pytest.skip("Step 20 test inputs not available")

        success = run_step20(test_prefix, working_dir)
        assert success, "Step 20 should succeed with valid inputs"

        # Check output directory exists
        output_dir = working_dir / "step20"
        assert output_dir.exists(), "Output directory should be created"

    def test_step20_creates_domain_pdbs(self, test_prefix, working_dir, setup_step20_inputs):
        """Test that step 20 creates individual domain PDB files."""
        if not setup_step20_inputs:
            pytest.skip("Step 20 test inputs not available")

        success = run_step20(test_prefix, working_dir)
        assert success

        output_dir = working_dir / "step20"

        # Check that domain PDB files were created
        expected_files = [
            f"{test_prefix}_dom1.pdb",
            f"{test_prefix}_dom2.pdb"
        ]

        for filename in expected_files:
            filepath = output_dir / filename
            assert filepath.exists(), f"Domain PDB {filename} should be created"
            assert filepath.stat().st_size > 0, f"Domain PDB {filename} should not be empty"


@pytest.mark.unit
class TestStep20HelperFunctions:
    """Unit tests for step 20 helper functions."""

    def test_extract_domain_pdb_basic(self, tmp_path):
        """Test basic domain PDB extraction."""
        input_pdb = tmp_path / "input.pdb"
        output_pdb = tmp_path / "output" / "domain.pdb"

        # Create minimal PDB file
        input_pdb.write_text(
            "ATOM      1  CA  ALA A  10      1.000   2.000   3.000  1.00 10.00           C\n"
            "ATOM      2  CA  GLY A  11      2.000   3.000   4.000  1.00 10.00           C\n"
            "ATOM      3  CA  VAL A  12      3.000   4.000   5.000  1.00 10.00           C\n"
            "ATOM      4  CA  LEU A  20      4.000   5.000   6.000  1.00 10.00           C\n"
        )

        # Extract residues 10-12
        extract_domain_pdb(input_pdb, output_pdb, {10, 11, 12})

        assert output_pdb.exists(), "Output PDB should be created"

        with open(output_pdb) as f:
            lines = f.readlines()

        assert len(lines) == 3, "Should have 3 ATOM lines for residues 10-12"
        assert all("ATOM" in line for line in lines), "All lines should be ATOM records"

    def test_extract_domain_pdb_creates_directory(self, tmp_path):
        """Test that extract_domain_pdb creates output directory."""
        input_pdb = tmp_path / "input.pdb"
        output_pdb = tmp_path / "subdir1" / "subdir2" / "domain.pdb"

        input_pdb.write_text(
            "ATOM      1  CA  ALA A  10      1.000   2.000   3.000  1.00 10.00           C\n"
        )

        extract_domain_pdb(input_pdb, output_pdb, {10})

        assert output_pdb.parent.exists(), "Output directory should be created"
        assert output_pdb.exists(), "Output file should be created"

    def test_extract_domain_pdb_filters_residues(self, tmp_path):
        """Test that only specified residues are extracted."""
        input_pdb = tmp_path / "input.pdb"
        output_pdb = tmp_path / "domain.pdb"

        input_pdb.write_text(
            "ATOM      1  CA  ALA A  10      1.000   2.000   3.000  1.00 10.00           C\n"
            "ATOM      2  CA  GLY A  15      2.000   3.000   4.000  1.00 10.00           C\n"
            "ATOM      3  CA  VAL A  20      3.000   4.000   5.000  1.00 10.00           C\n"
        )

        extract_domain_pdb(input_pdb, output_pdb, {10, 20})

        with open(output_pdb) as f:
            lines = f.readlines()

        assert len(lines) == 2, "Should have 2 ATOM lines for residues 10 and 20"

        # Verify correct residues
        assert "  10 " in lines[0], "First line should have residue 10"
        assert "  20 " in lines[1], "Second line should have residue 20"

    def test_extract_domain_pdb_handles_malformed_lines(self, tmp_path):
        """Test that malformed lines are skipped."""
        input_pdb = tmp_path / "input.pdb"
        output_pdb = tmp_path / "domain.pdb"

        input_pdb.write_text(
            "ATOM      1  CA  ALA A  10      1.000   2.000   3.000  1.00 10.00           C\n"
            "MALFORMED LINE\n"
            "ATOM      2  CA  GLY A  11      2.000   3.000   4.000  1.00 10.00           C\n"
        )

        extract_domain_pdb(input_pdb, output_pdb, {10, 11})

        with open(output_pdb) as f:
            lines = f.readlines()

        assert len(lines) == 2, "Should have 2 valid ATOM lines"

    def test_extract_domain_pdb_empty_residue_set(self, tmp_path):
        """Test extraction with empty residue set."""
        input_pdb = tmp_path / "input.pdb"
        output_pdb = tmp_path / "domain.pdb"

        input_pdb.write_text(
            "ATOM      1  CA  ALA A  10      1.000   2.000   3.000  1.00 10.00           C\n"
        )

        extract_domain_pdb(input_pdb, output_pdb, set())

        assert output_pdb.exists(), "Output file should be created"

        with open(output_pdb) as f:
            content = f.read()

        assert content == "", "Output file should be empty"


# Fixture for step 20 inputs
@pytest.fixture(scope="function")
def setup_step20_inputs(test_prefix, working_dir):
    """Setup input files for step 20 tests."""
    # Create merge candidates
    (working_dir / f"{test_prefix}.step19_merge_candidates").write_text(
        "# domain1\trange1\tdomain2\trange2\n"
        "dom1\t10-15\tdom2\t20-25\n"
    )

    # Create minimal PDB file
    pdb_content = ""
    for i in range(10, 30):
        pdb_content += f"ATOM      {i-9}  CA  ALA A  {i:3d}      1.000   2.000   3.000  1.00 10.00           C\n"

    (working_dir / f"{test_prefix}.pdb").write_text(pdb_content)

    return True
