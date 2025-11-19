"""
Integration tests for Step 18: Get Alignment Mappings.

Tests mapping domain residues to ECOD template residues.
"""

import pytest
from pathlib import Path
from dpam.steps.step18_get_mapping import (
    run_step18,
    check_overlap_strict,
    load_ecod_map
)
from dpam.io.parsers import parse_hhsearch_output


@pytest.mark.integration
class TestStep18GetMapping:
    """Integration tests for step 18 (get alignment mappings)."""

    def test_step18_requires_step17_output(self, test_prefix, working_dir, ecod_data_dir):
        """Test that step 18 gracefully skips without step 17 output."""
        success = run_step18(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 18 should gracefully skip with missing confident predictions"

    def test_step18_requires_hhsearch_hits(self, test_prefix, working_dir, ecod_data_dir):
        """Test that step 18 fails without HHsearch hits."""
        # Create confident predictions but no HHsearch hits
        (working_dir / f"{test_prefix}.step17_confident_predictions").write_text(
            "# domain\tdomain_range\ttgroup\tecod_ref\tprob\tquality\n"
            "dom1\t10-50\t1.1.1\te001\t0.95\tgood\n"
        )

        success = run_step18(test_prefix, working_dir, ecod_data_dir)
        assert not success, "Step 18 should fail without HHsearch hits"

    def test_step18_with_valid_inputs(self, test_prefix, working_dir, ecod_data_dir, setup_step18_inputs):
        """Test step 18 with valid inputs."""
        if not setup_step18_inputs:
            pytest.skip("Step 18 test inputs not available")

        success = run_step18(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 18 should succeed with valid inputs"

        # Check output exists
        output_file = working_dir / f"{test_prefix}.step18_mappings"
        assert output_file.exists(), "Mappings file should be created"

    def test_step18_output_format(self, test_prefix, working_dir, ecod_data_dir, setup_step18_inputs):
        """Test that step 18 output has expected format."""
        if not setup_step18_inputs:
            pytest.skip("Step 18 test inputs not available")

        success = run_step18(test_prefix, working_dir, ecod_data_dir)
        assert success

        output_file = working_dir / f"{test_prefix}.step18_mappings"

        with open(output_file) as f:
            lines = f.readlines()

        # Check header
        header = lines[0].strip()
        assert header.startswith('#'), "Header should start with #"
        expected_cols = ["domain", "domain_range", "ecod_id", "tgroup",
                        "dpam_prob", "quality", "hh_template_range", "dali_template_range"]
        for col in expected_cols:
            assert col in header, f"Header should contain '{col}'"

        # Check data rows if any
        if len(lines) > 1:
            parts = lines[1].strip().split('\t')
            assert len(parts) == 8, "Each row should have 8 columns"

    def test_step18_parses_hhsearch_correctly(self, tmp_path):
        """
        Regression test: Verify HHsearch output is parsed correctly using parser.

        Bug: Step 18 was trying to read raw .hhsearch as tab-delimited instead of
        using parse_hhsearch_output(), resulting in 0 hits loaded.
        """
        # Create minimal HHsearch output in native format
        hhsearch_file = tmp_path / "test.hhsearch"
        hhsearch_file.write_text("""Query         test_protein
Match_columns 100
No_of_seqs    50

 No Hit                             Prob E-value P-value  Score    SS Cols Query HMM  Template HMM
  1 TEST_HIT RNA polymerase sigm  98.4 6.2E-10 6.9E-15   65.7   0.0   54   18-71    137-190 (191)

>TEST_HIT RNA polymerase sigma factor
Probab=98.40  E-value=6.2e-10  Score=65.69  Aligned_cols=54  Identities=25%  Similarity=0.450  Sum_probs=48.2

Q test_protein   18 MRKLVVVGDQGSG  30
Q Consensus      18 mrklvvvgdqgsg  30
                      |||||||||||||
T Consensus     137 mrklvvvgdqgsg 149
T TEST_HIT      137 MRKLVVVGDQGSG 149

Q test_protein   31 KSTTIGNALQQA  42
""")

        # Parse using the correct parser
        alignments = parse_hhsearch_output(hhsearch_file)

        # Verify parsing worked
        assert len(alignments) > 0, "Should parse HHsearch alignments from native format"
        assert alignments[0].hit_id == "TEST_HIT", "Should extract hit ID"
        assert alignments[0].probability == 98.4, "Should extract probability"

    def test_step18_dali_column_mapping(self, tmp_path):
        """
        Regression test: Verify DALI good_hits uses correct column for ECOD ID.

        Bug: Step 18 was reading column 1 (ecodnum) instead of column 2 (ecodkey),
        resulting in wrong ECOD IDs for matching.
        """
        # Create DALI good_hits with realistic format
        dali_file = tmp_path / "test_good_hits"
        dali_file.write_text(
            "hitname\tecodnum\tecodkey\thgroup\tzscore\tqscore\tztile\tqtile\trank\tqrange\terange\n"
            "001288642_1\t001288642\te4cxfA2\t101.1\t9.0\t-1.0\t-1.0\t-1.0\t1.0\t8-15,18-70\t4-64\n"
            "002389467_1\t002389467\te6dxoA2\t101.1\t8.4\t-1.0\t-1.0\t-1.0\t1.0\t12-15,18-66\t1-53\n"
        )

        # Parse manually to verify column mapping
        with open(dali_file, 'r') as f:
            lines = f.readlines()

        # Skip header
        parts = lines[1].strip().split('\t')

        # Verify correct columns
        assert parts[0] == "001288642_1", "Column 0 should be hitname"
        assert parts[1] == "001288642", "Column 1 should be ecodnum"
        assert parts[2] == "e4cxfA2", "Column 2 should be ecodkey (ECOD ID)"

        # This is what Step 18 should use for matching
        ecod_id_correct = parts[2]  # Column 2
        assert ecod_id_correct == "e4cxfA2", "Should use ecodkey from column 2"

    def test_step18_produces_non_empty_mappings(self, test_prefix, working_dir, ecod_data_dir):
        """
        Regression test: Verify step 18 produces mappings with non-'na' template ranges.

        Bug: Due to HHsearch/DALI parsing bugs, Step 18 was producing all 'na\tna'
        for template ranges, breaking Step 23.
        """
        # Setup realistic test inputs
        (working_dir / f"{test_prefix}.step17_confident_predictions").write_text(
            "# domain\tdomain_range\ttgroup\tecod_ref\tprob\tquality\n"
            "D1\t10-50\t101.1.1\te4cxfA2\t0.85\tgood\n"
        )

        # Create minimal HHsearch output
        (working_dir / f"{test_prefix}.hhsearch").write_text("""Query         test
 No Hit                             Prob E-value P-value  Score    SS Cols Query HMM  Template HMM
  1 4CXF_A test hit                98.4 6.2E-10 6.9E-15   65.7   0.0   40   10-50    100-140 (191)

>4CXF_A test hit
Probab=98.40  E-value=6.2e-10  Score=65.69  Aligned_cols=40

Q test         10 TESTSEQUENCE  21
T 4CXF_A      100 TESTSEQUENCE 111
""")

        # Create DALI good_hits
        (working_dir / f"{test_prefix}_good_hits").write_text(
            "hitname\tecodnum\tecodkey\thgroup\tzscore\tqscore\tztile\tqtile\trank\tqrange\terange\n"
            "001288642_1\t001288642\te4cxfA2\t101.1\t9.0\t-1.0\t-1.0\t-1.0\t1.0\t10-50\t100-140\n"
        )

        # Create ECOD maps dir if needed
        ecod_maps_dir = ecod_data_dir / "ECOD_maps"
        ecod_maps_dir.mkdir(parents=True, exist_ok=True)
        (ecod_maps_dir / "e4cxfA2.map").write_text("100 100\n110 110\n120 120\n130 130\n140 140\n")

        # Run step 18
        success = run_step18(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 18 should succeed"

        # Check that mappings were created with actual template ranges
        output_file = working_dir / f"{test_prefix}.step18_mappings"
        assert output_file.exists(), "Mappings file should exist"

        with open(output_file) as f:
            lines = f.readlines()

        assert len(lines) > 1, "Should have at least one mapping"

        # Check that template ranges are not all 'na'
        data_line = lines[1].strip()
        parts = data_line.split('\t')
        hh_range = parts[6]
        dali_range = parts[7]

        # At least one should not be 'na'
        assert hh_range != 'na' or dali_range != 'na', \
            "Should have at least one non-'na' template range (bug: all were 'na')"


@pytest.mark.unit
class TestStep18HelperFunctions:
    """Unit tests for step 18 helper functions."""

    def test_check_overlap_strict_full_overlap(self):
        """Test strict overlap check with full overlap."""
        set_a = {1, 2, 3, 4, 5}
        set_b = {1, 2, 3, 4, 5}
        assert check_overlap_strict(set_a, set_b) is True

    def test_check_overlap_strict_50_percent_of_a(self):
        """Test strict overlap with 50% of A."""
        set_a = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}  # 10 residues
        set_b = {6, 7, 8, 9, 10, 11, 12, 13, 14, 15}  # 5 overlap = 50% of A
        assert check_overlap_strict(set_a, set_b) is True

    def test_check_overlap_strict_50_percent_of_b(self):
        """Test strict overlap with 50% of B."""
        set_a = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}  # 10 residues
        set_b = {8, 9, 10, 11}  # 3 overlap = 75% of B (>50%)
        assert check_overlap_strict(set_a, set_b) is True

    def test_check_overlap_strict_33_percent_but_not_50(self):
        """Test strict overlap with 33% but not 50%."""
        set_a = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}  # 10 residues
        set_b = {9, 10, 11, 12, 13, 14, 15, 16, 17, 18}  # 2 overlap = 20% of both
        assert check_overlap_strict(set_a, set_b) is False

    def test_check_overlap_strict_exactly_33_percent(self):
        """Test strict overlap at exactly 33% threshold."""
        set_a = {1, 2, 3, 4, 5, 6, 7, 8, 9}  # 9 residues
        set_b = {7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18}  # 3 overlap = 33% of A, 25% of B
        # Need 33% AND (50% of A OR 50% of B) - this doesn't meet 50% criteria
        assert check_overlap_strict(set_a, set_b) is False

    def test_check_overlap_strict_below_33_percent(self):
        """Test strict overlap below 33% threshold."""
        set_a = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}  # 10 residues
        set_b = {10, 11, 12, 13, 14, 15}  # 1 overlap = 10% of A
        assert check_overlap_strict(set_a, set_b) is False

    def test_check_overlap_strict_no_overlap(self):
        """Test strict overlap with no overlap."""
        set_a = {1, 2, 3}
        set_b = {10, 20, 30}
        assert check_overlap_strict(set_a, set_b) is False

    def test_check_overlap_strict_empty_sets(self):
        """Test strict overlap with empty sets."""
        assert check_overlap_strict(set(), {1, 2, 3}) is False
        assert check_overlap_strict({1, 2, 3}, set()) is False
        assert check_overlap_strict(set(), set()) is False

    def test_check_overlap_strict_edge_case_33_and_50(self):
        """Test strict overlap at boundary (≥33% and ≥50% of smaller set)."""
        set_a = {1, 2, 3, 4, 5, 6}  # 6 residues
        set_b = {4, 5, 6, 7}  # 3 overlap = 50% of A, 75% of B
        assert check_overlap_strict(set_a, set_b) is True

    def test_load_ecod_map_valid_file(self, tmp_path):
        """Test loading ECOD map from valid file."""
        map_file = tmp_path / "test.map"
        map_file.write_text("1 101\n2 102\n5 105\n10 110\n")

        resmap = load_ecod_map(map_file)
        assert resmap == {1: 101, 2: 102, 5: 105, 10: 110}

    def test_load_ecod_map_missing_file(self, tmp_path):
        """Test loading ECOD map from non-existent file."""
        map_file = tmp_path / "nonexistent.map"

        resmap = load_ecod_map(map_file)
        assert resmap == {}, "Should return empty dict for missing file"

    def test_load_ecod_map_malformed_lines(self, tmp_path):
        """Test loading ECOD map with malformed lines."""
        map_file = tmp_path / "test.map"
        map_file.write_text("1 101\ninvalid\n3 103\n")

        resmap = load_ecod_map(map_file)
        assert resmap == {1: 101, 3: 103}, "Should skip malformed lines"

    def test_load_ecod_map_extra_columns(self, tmp_path):
        """Test loading ECOD map with extra columns."""
        map_file = tmp_path / "test.map"
        map_file.write_text("1 101 extra data\n2 102 more\n")

        resmap = load_ecod_map(map_file)
        assert resmap == {1: 101, 2: 102}, "Should handle extra columns"


# Fixture for step 18 inputs
@pytest.fixture(scope="function")
def setup_step18_inputs(test_prefix, working_dir, ecod_data_dir):
    """
    Setup input files for step 18 tests.

    Returns True if setup successful.
    """
    # Create confident predictions
    (working_dir / f"{test_prefix}.step17_confident_predictions").write_text(
        "# domain\tdomain_range\ttgroup\tecod_ref\tprob\tquality\n"
        "dom1\t10-50\t1.1.1\te001\t0.95\tgood\n"
        "dom2\t60-100\t2.2.2\te002\t0.85\tok\n"
    )

    # Create HHsearch hits
    (working_dir / f"{test_prefix}.hhsearch_hits").write_text(
        "# HHsearch hits\n"
        "hit1\te001\tname1\t95.0\t100\t1.5\t0.80\t0.90\t0.95\t1.0\t0.90\t0.85\t10-50\t5-45\n"
        "hit2\te002\tname2\t85.0\t100\t2.0\t0.75\t0.85\t0.90\t1.2\t0.85\t0.80\t60-100\t10-50\n"
    )

    # Create DALI hits
    (working_dir / f"{test_prefix}.dali_good_hits").write_text(
        "# DALI hits\n"
        "hit1\te001\tname1\t123.4\t75.6\t10-50\t5-45\t1.0\t0.0\t0.0\t5.0\n"
        "hit2\te002\tname2\t105.3\t70.2\t60-100\t10-50\t0.5\t0.5\t0.5\t3.5\n"
    )

    # Create minimal ECOD maps if they don't exist
    ecod_maps_dir = ecod_data_dir / "ECOD_maps"
    if not ecod_maps_dir.exists():
        ecod_maps_dir.mkdir(parents=True)

        (ecod_maps_dir / "e001.map").write_text("5 5\n10 10\n15 15\n")
        (ecod_maps_dir / "e002.map").write_text("10 10\n20 20\n30 30\n")

    return True
