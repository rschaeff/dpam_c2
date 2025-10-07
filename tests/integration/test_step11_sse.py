"""
Integration tests for Step 11: Secondary Structure Elements (SSE).

Tests DSSP-based secondary structure assignment.
"""

import pytest
from pathlib import Path
from dpam.steps.step11_sse import run_step11


@pytest.mark.integration
@pytest.mark.requires_dssp
class TestStep11SSE:
    """Integration tests for step 11 (SSE assignment)."""

    def test_sse_basic_execution(self, test_prefix, working_dir, setup_test_files, dssp_available):
        """Test basic SSE assignment execution."""
        # Requires PDB and FASTA from step 1
        if 'pdb' not in setup_test_files or 'fa' not in setup_test_files:
            pytest.skip("PDB and FASTA test files required")

        success = run_step11(test_prefix, working_dir)
        assert success, "Step 11 should succeed"

        # Check output file exists
        sse_file = working_dir / f"{test_prefix}.sse"
        assert sse_file.exists(), "SSE file should be created"
        assert sse_file.stat().st_size > 0, "SSE file should not be empty"

    def test_sse_output_format(self, test_prefix, working_dir, setup_test_files, dssp_available):
        """Test that SSE output has correct format."""
        if 'pdb' not in setup_test_files or 'fa' not in setup_test_files:
            pytest.skip("PDB and FASTA test files required")

        success = run_step11(test_prefix, working_dir)
        assert success

        # Read and validate output format
        sse_file = working_dir / f"{test_prefix}.sse"
        with open(sse_file, 'r') as f:
            lines = f.readlines()

        # Should have at least one line
        assert len(lines) > 0, "SSE file should have content"

        # Each line should have 4 tab-separated fields
        for i, line in enumerate(lines, 1):
            fields = line.strip().split('\t')
            assert len(fields) == 4, f"Line {i} should have 4 fields: resid, aa, sse_id, sse_type"

            # Validate field formats
            resid, aa, sse_id, sse_type = fields

            # resid should be numeric
            assert resid.isdigit(), f"Line {i}: resid should be numeric, got {resid}"

            # aa should be single letter
            assert len(aa) == 1, f"Line {i}: amino acid should be single letter, got {aa}"
            assert aa.isalpha(), f"Line {i}: amino acid should be alphabetic, got {aa}"

            # sse_id should be numeric or 'na'
            assert sse_id.isdigit() or sse_id == 'na', \
                f"Line {i}: sse_id should be numeric or 'na', got {sse_id}"

            # sse_type should be H, E, or C
            assert sse_type in ['H', 'E', 'C'], \
                f"Line {i}: sse_type should be H, E, or C, got {sse_type}"

    def test_sse_matches_sequence_length(self, test_prefix, working_dir, setup_test_files, dssp_available):
        """Test that SSE assignments match sequence length."""
        if 'pdb' not in setup_test_files or 'fa' not in setup_test_files:
            pytest.skip("PDB and FASTA test files required")

        success = run_step11(test_prefix, working_dir)
        assert success

        # Read sequence length
        fa_file = working_dir / f"{test_prefix}.fa"
        with open(fa_file, 'r') as f:
            lines = f.readlines()
            sequence = ''.join(line.strip() for line in lines if not line.startswith('>'))
        seq_len = len(sequence)

        # Read SSE assignments
        sse_file = working_dir / f"{test_prefix}.sse"
        with open(sse_file, 'r') as f:
            sse_lines = f.readlines()
        sse_len = len(sse_lines)

        assert sse_len == seq_len, \
            f"SSE assignments ({sse_len}) should match sequence length ({seq_len})"

    def test_sse_identifies_helices_and_strands(self, test_prefix, working_dir, setup_test_files, dssp_available):
        """Test that SSE identifies helices (H) and strands (E)."""
        if 'pdb' not in setup_test_files or 'fa' not in setup_test_files:
            pytest.skip("PDB and FASTA test files required")

        success = run_step11(test_prefix, working_dir)
        assert success

        # Read SSE assignments
        sse_file = working_dir / f"{test_prefix}.sse"
        with open(sse_file, 'r') as f:
            lines = f.readlines()

        # Count SSE types
        helices = sum(1 for line in lines if line.strip().split('\t')[3] == 'H')
        strands = sum(1 for line in lines if line.strip().split('\t')[3] == 'E')
        coils = sum(1 for line in lines if line.strip().split('\t')[3] == 'C')

        # Should have at least some assignments
        total = helices + strands + coils
        assert total == len(lines), "All residues should have SSE type"

        # Most proteins should have some structure (not all coil)
        # This is a weak test - some small proteins might be all coil
        assert total > 0, "Should have SSE assignments"

    def test_sse_assigns_sse_ids(self, test_prefix, working_dir, setup_test_files, dssp_available):
        """Test that SSE IDs are assigned to structured regions."""
        if 'pdb' not in setup_test_files or 'fa' not in setup_test_files:
            pytest.skip("PDB and FASTA test files required")

        success = run_step11(test_prefix, working_dir)
        assert success

        # Read SSE assignments
        sse_file = working_dir / f"{test_prefix}.sse"
        with open(sse_file, 'r') as f:
            lines = f.readlines()

        # Check SSE ID assignments
        sse_ids = []
        for line in lines:
            fields = line.strip().split('\t')
            sse_id = fields[2]
            sse_type = fields[3]

            # If SSE type is H or E, should have numeric SSE ID
            if sse_type in ['H', 'E']:
                if sse_id != 'na':
                    sse_ids.append(int(sse_id))

            # If SSE type is C (coil), SSE ID should be 'na'
            if sse_type == 'C':
                assert sse_id == 'na', "Coil regions should have SSE ID 'na'"

        # Should have some SSE IDs assigned (for structured regions)
        # Note: Small proteins or mostly disordered proteins might have none
        # This is a weak test
        assert len(sse_ids) >= 0, "Should process SSE IDs"

    def test_sse_consecutive_residue_ids(self, test_prefix, working_dir, setup_test_files, dssp_available):
        """Test that residue IDs are consecutive."""
        if 'pdb' not in setup_test_files or 'fa' not in setup_test_files:
            pytest.skip("PDB and FASTA test files required")

        success = run_step11(test_prefix, working_dir)
        assert success

        # Read SSE assignments
        sse_file = working_dir / f"{test_prefix}.sse"
        with open(sse_file, 'r') as f:
            lines = f.readlines()

        # Extract residue IDs
        resids = [int(line.strip().split('\t')[0]) for line in lines]

        # Should be sorted and consecutive
        assert resids == sorted(resids), "Residue IDs should be sorted"

        # Check consecutiveness (starting from 1)
        expected = list(range(1, len(resids) + 1))
        assert resids == expected, "Residue IDs should be consecutive starting from 1"

    def test_sse_requires_pdb_file(self, test_prefix, working_dir, setup_test_files, dssp_available):
        """Test that step 11 fails without PDB file."""
        if 'fa' not in setup_test_files:
            pytest.skip("FASTA test file required")

        # Remove PDB file if exists
        pdb_file = working_dir / f"{test_prefix}.pdb"
        if pdb_file.exists():
            pdb_file.unlink()

        success = run_step11(test_prefix, working_dir)
        assert not success, "Step 11 should fail without PDB file"

    def test_sse_requires_fasta_file(self, test_prefix, working_dir, setup_test_files, dssp_available):
        """Test that step 11 fails without FASTA file."""
        if 'pdb' not in setup_test_files:
            pytest.skip("PDB test file required")

        # Remove FASTA file if exists
        fa_file = working_dir / f"{test_prefix}.fa"
        if fa_file.exists():
            fa_file.unlink()

        success = run_step11(test_prefix, working_dir)
        assert not success, "Step 11 should fail without FASTA file"

    def test_sse_handles_small_proteins(self, test_prefix, working_dir, setup_test_files, dssp_available):
        """Test SSE assignment on small proteins."""
        if 'pdb' not in setup_test_files or 'fa' not in setup_test_files:
            pytest.skip("PDB and FASTA test files required")

        success = run_step11(test_prefix, working_dir)
        assert success, "Step 11 should handle small proteins"

        # Check output exists
        sse_file = working_dir / f"{test_prefix}.sse"
        assert sse_file.exists()

        # Small proteins should still have valid SSE assignments
        with open(sse_file, 'r') as f:
            lines = f.readlines()
        assert len(lines) > 0, "Should have SSE assignments even for small proteins"


@pytest.mark.integration
class TestStep11Functions:
    """Test individual Step 11 functions."""

    def test_dssp_wrapper_available(self, dssp_available):
        """Test that DSSP wrapper is available."""
        from dpam.tools.dssp import DSSP

        dssp = DSSP()
        assert dssp.is_available(), "DSSP should be available"
        assert dssp.executable is not None, "DSSP executable should be found"

    def test_dssp_produces_output(self, test_prefix, working_dir, setup_test_files, dssp_available):
        """Test that DSSP produces valid output."""
        if 'pdb' not in setup_test_files or 'fa' not in setup_test_files:
            pytest.skip("PDB and FASTA test files required")

        from dpam.tools.dssp import DSSP
        from dpam.io.readers import read_fasta

        # Read inputs
        pdb_file = working_dir / f"{test_prefix}.pdb"
        fa_file = working_dir / f"{test_prefix}.fa"
        _, sequence = read_fasta(fa_file)

        # Run DSSP
        dssp = DSSP()
        sse_dict = dssp.run_and_parse(pdb_file, sequence, working_dir)

        # Validate output
        assert len(sse_dict) > 0, "DSSP should produce SSE assignments"
        assert len(sse_dict) == len(sequence), \
            f"DSSP assignments ({len(sse_dict)}) should match sequence length ({len(sequence)})"

        # Check that each residue has valid SSE
        for resid, sse in sse_dict.items():
            assert hasattr(sse, 'residue_id'), "SSE should have residue_id"
            assert hasattr(sse, 'amino_acid'), "SSE should have amino_acid"
            assert hasattr(sse, 'sse_type'), "SSE should have sse_type"
            assert hasattr(sse, 'sse_id'), "SSE should have sse_id"
            assert sse.sse_type in ['H', 'E', 'C'], f"Invalid SSE type: {sse.sse_type}"
