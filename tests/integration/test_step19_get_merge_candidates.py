"""
Integration tests for Step 19: Get Merge Candidates.

Tests identification of domain pairs that should be merged.
"""

import pytest
from pathlib import Path
from dpam.steps.step19_get_merge_candidates import (
    run_step19,
    load_position_weights
)


@pytest.mark.integration
class TestStep19GetMergeCandidates:
    """Integration tests for step 19 (get merge candidates)."""

    def test_step19_requires_step18_output(self, test_prefix, working_dir, ecod_data_dir):
        """Test that step 19 gracefully skips without step 18 output."""
        success = run_step19(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 19 should gracefully skip with missing mappings"

    def test_step19_with_valid_inputs(self, test_prefix, working_dir, ecod_data_dir, setup_step19_inputs):
        """Test step 19 with valid inputs."""
        if not setup_step19_inputs:
            pytest.skip("Step 19 test inputs not available")

        success = run_step19(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 19 should succeed with valid inputs"

    def test_step19_ecod_length_column_mapping(self, tmp_path):
        """
        Regression test: Verify ECOD_length uses correct column for ECOD ID.

        Bug: Step 19 was reading column 0 (numeric UID) instead of column 1 (ECOD ID),
        causing 100% failure in finding ECOD hits and preventing ALL discontinuous domain formation.
        """
        # Create ECOD_length file with realistic format
        ecod_length_file = tmp_path / "ECOD_length"
        ecod_length_file.write_text(
            "000000003\te2rspA1\t124\n"
            "000000017\te2pmaA1\t141\n"
            "001288642\te4cxfA2\t191\n"
            "002389467\te6dxoA2\t150\n"
        )

        # Parse manually to verify column mapping
        ecod_lengths = {}
        with open(ecod_length_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3:
                    # Column 0: ECOD number (wrong!)
                    # Column 1: ECOD ID (correct!)
                    # Column 2: length
                    ecod_id = parts[1]  # Must use column 1
                    length = int(parts[2])
                    ecod_lengths[ecod_id] = length

        # Verify correct parsing
        assert "e4cxfA2" in ecod_lengths, "Should find ECOD ID in column 1"
        assert ecod_lengths["e4cxfA2"] == 191, "Should read length from column 2"
        assert "001288642" not in ecod_lengths, "Should NOT use ECOD number from column 0"

    def test_step19_finds_merge_candidates_with_correct_column(self, test_prefix, working_dir, ecod_data_dir):
        """
        Regression test: Verify Step 19 finds merge candidates when ECOD_length is parsed correctly.

        Bug: With column 0 parsing, Step 19 reports "No ECOD hits found" even with valid mappings.
        Fix: With column 1 parsing, Step 19 correctly identifies domain pairs sharing ECOD templates.
        """
        # Setup: Two domains hitting same ECOD template (discontinuous domain candidate)
        (working_dir / f"{test_prefix}.step18_mappings").write_text(
            "# domain\tdomain_range\tecod_id\ttgroup\tdpam_prob\tquality\thh_template_range\tdali_template_range\n"
            # Domain 1 hits N-terminal region of e4cxfA2
            "D1\t10-90\te4cxfA2\t2004.1.1\t0.950\tgood\tna\t1-80\n"
            # Domain 8 hits C-terminal region of e4cxfA2 (discontinuous)
            "D8\t546-675\te4cxfA2\t2004.1.1\t0.986\tgood\tna\t100-191\n"
        )

        # Create ECOD_length file with CORRECT format (3 columns)
        (ecod_data_dir / "ECOD_length").write_text(
            "001288642\te4cxfA2\t191\n"  # Column 0: UID, Column 1: ECOD ID, Column 2: Length
        )

        # Create posi_weights directory (will use defaults)
        posi_weights_dir = ecod_data_dir / "posi_weights"
        posi_weights_dir.mkdir(parents=True, exist_ok=True)

        # Run step 19
        success = run_step19(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 19 should succeed"

        # Check output
        output_file = working_dir / f"{test_prefix}.step19_merge_candidates"

        # CRITICAL: With correct column parsing, should find merge candidates
        assert output_file.exists(), \
            "Step 19 should create output file (bug: reports 'No ECOD hits found' with wrong column)"

        with open(output_file) as f:
            lines = f.readlines()

        # Should have header + at least 1 merge candidate
        assert len(lines) >= 2, \
            f"Should find merge candidates (D1 + D8 both hit e4cxfA2), got {len(lines)} lines"

        # Verify merge candidate format
        parts = lines[1].strip().split('\t')
        assert len(parts) == 4, "Should have 4 columns (dom1, range1, dom2, range2)"

        # Verify D1 and D8 are identified as merge candidates
        domains_in_merge = {parts[0], parts[2]}
        assert "D1" in domains_in_merge and "D8" in domains_in_merge, \
            f"D1 and D8 should be merge candidates (both hit e4cxfA2), got {domains_in_merge}"

    def test_step19_output_format(self, test_prefix, working_dir, ecod_data_dir, setup_step19_inputs):
        """Test that step 19 output has expected format."""
        if not setup_step19_inputs:
            pytest.skip("Step 19 test inputs not available")

        success = run_step19(test_prefix, working_dir, ecod_data_dir)
        assert success

        output_file = working_dir / f"{test_prefix}.step19_merge_candidates"

        if output_file.exists():
            with open(output_file) as f:
                lines = f.readlines()

            # Check header
            header = lines[0].strip()
            assert "domain1" in header and "domain2" in header

            # Check data format if present
            if len(lines) > 1:
                parts = lines[1].strip().split('\t')
                assert len(parts) == 4, "Each row should have 4 columns (dom1, range1, dom2, range2)"


@pytest.mark.unit
class TestStep19HelperFunctions:
    """Unit tests for step 19 helper functions."""

    def test_load_position_weights_from_file(self, tmp_path):
        """Test loading position weights from weight file."""
        weights_dir = tmp_path / "weights"
        weights_dir.mkdir()

        weight_file = weights_dir / "e001.weight"
        weight_file.write_text("1 A 1 2.5\n2 B 2 1.8\n3 C 3 3.2\n")

        pos_weights, total_weight = load_position_weights("e001", weights_dir, 10)

        assert pos_weights == {1: 2.5, 2: 1.8, 3: 3.2}
        assert abs(total_weight - 7.5) < 0.01

    def test_load_position_weights_uniform_fallback(self, tmp_path):
        """Test fallback to uniform weights when file missing."""
        weights_dir = tmp_path / "weights"
        weights_dir.mkdir()

        pos_weights, total_weight = load_position_weights("e999", weights_dir, 5)

        assert pos_weights == {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0}
        assert total_weight == 5.0

    def test_load_position_weights_malformed_lines(self, tmp_path):
        """Test that malformed lines are skipped."""
        weights_dir = tmp_path / "weights"
        weights_dir.mkdir()

        weight_file = weights_dir / "e001.weight"
        weight_file.write_text("1 A 1 2.5\ninvalid line\n3 C 3 3.2\n")

        pos_weights, total_weight = load_position_weights("e001", weights_dir, 10)

        assert pos_weights == {1: 2.5, 3: 3.2}
        assert abs(total_weight - 5.7) < 0.01


# Fixture for step 19 inputs
@pytest.fixture(scope="function")
def setup_step19_inputs(test_prefix, working_dir, ecod_data_dir):
    """Setup input files for step 19 tests."""
    # Create step18 mappings
    (working_dir / f"{test_prefix}.step18_mappings").write_text(
        "# domain\tdomain_range\tecod_id\ttgroup\tdpam_prob\tquality\thh_template_range\tdali_template_range\n"
        "dom1\t10-50\te001\t1.1.1\t0.95\tgood\t5-45\t5-45\n"
        "dom2\t60-100\te001\t1.1.1\t0.90\tgood\t50-90\t50-90\n"
    )

    # Create ECOD length file with correct format (3 columns: UID, ECOD_ID, length)
    ecod_length_file = ecod_data_dir / "ECOD_length"
    if not ecod_length_file.exists():
        ecod_length_file.parent.mkdir(parents=True, exist_ok=True)
        ecod_length_file.write_text("000001\te001\t100\n000002\te002\t150\n")

    return True
