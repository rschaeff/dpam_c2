"""
Integration tests for Step 1: Prepare.

Tests the preparation step that validates and processes input files.
"""

import pytest
from pathlib import Path
from dpam.steps.step01_prepare import run_step1


@pytest.mark.integration
class TestStep01Prepare:
    """Integration tests for step 1 (prepare)."""

    def test_prepare_with_pdb(self, test_prefix, working_dir, setup_test_files):
        """Test prepare step with PDB input."""
        if 'pdb' not in setup_test_files:
            pytest.skip("PDB test file not available")

        # Run step 1
        success = run_step1(test_prefix, working_dir)
        assert success, "Step 1 should succeed with valid PDB"

        # Check outputs exist
        pdb_out = working_dir / f"{test_prefix}.pdb"
        fa_out = working_dir / f"{test_prefix}.fa"

        assert pdb_out.exists(), "PDB file should be created"
        assert fa_out.exists(), "FASTA file should be created"

    def test_prepare_with_cif(self, test_prefix, working_dir, setup_test_files):
        """Test prepare step with CIF input."""
        if 'cif' not in setup_test_files:
            pytest.skip("CIF test file not available")

        # Remove PDB if exists to force CIF usage
        pdb_file = working_dir / f"{test_prefix}.pdb"
        if pdb_file.exists():
            pdb_file.unlink()

        # Run step 1
        success = run_step1(test_prefix, working_dir)
        assert success, "Step 1 should succeed with valid CIF"

        # Check outputs
        pdb_out = working_dir / f"{test_prefix}.pdb"
        fa_out = working_dir / f"{test_prefix}.fa"

        assert pdb_out.exists(), "PDB file should be created from CIF"
        assert fa_out.exists(), "FASTA file should be created"

    def test_prepare_validates_sequence_length(self, test_prefix, working_dir, setup_test_files):
        """Test that prepare validates sequence length."""
        if 'fa' not in setup_test_files:
            pytest.skip("FASTA test file not available")

        success = run_step1(test_prefix, working_dir)
        assert success

        # Read sequence
        fa_file = working_dir / f"{test_prefix}.fa"
        with open(fa_file) as f:
            lines = f.readlines()
            seq = ''.join(line.strip() for line in lines if not line.startswith('>'))

        # Should be reasonable length (not empty, not too long)
        assert len(seq) > 0, "Sequence should not be empty"
        assert len(seq) < 10000, "Sequence should be reasonable length"

    def test_prepare_creates_expected_files(self, test_prefix, working_dir, setup_test_files):
        """Test that all expected output files are created."""
        if 'pdb' not in setup_test_files:
            pytest.skip("PDB test file not available")

        success = run_step1(test_prefix, working_dir)
        assert success

        # Check all expected outputs
        expected_files = [
            f"{test_prefix}.pdb",
            f"{test_prefix}.fa",
        ]

        for filename in expected_files:
            filepath = working_dir / filename
            assert filepath.exists(), f"{filename} should be created"
            assert filepath.stat().st_size > 0, f"{filename} should not be empty"

    def test_prepare_fails_with_missing_input(self, test_prefix, working_dir):
        """Test that prepare fails gracefully with missing input."""
        # Don't copy any test files - working_dir is empty

        success = run_step1(test_prefix, working_dir)
        assert not success, "Step 1 should fail with missing input files"

    def test_prepare_handles_alphafold_json(self, test_prefix, working_dir, setup_test_files):
        """Test that PAE JSON file is preserved if present."""
        if 'json' not in setup_test_files:
            pytest.skip("JSON test file not available")

        success = run_step1(test_prefix, working_dir)
        assert success

        # Check JSON file is still present
        json_file = working_dir / f"{test_prefix}.json"
        assert json_file.exists(), "PAE JSON should be preserved"

        # Validate it's valid JSON
        import json
        with open(json_file) as f:
            data = json.load()
        assert data is not None, "JSON should be valid"
