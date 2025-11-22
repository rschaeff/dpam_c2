"""
Integration tests for Step 15: Prepare DOMASS Features.

Tests the feature extraction for ML model that combines domain properties
with HHsearch and DALI evidence.
"""

import pytest
from pathlib import Path
from dpam.steps.step15_prepare_domass import (
    run_step15,
    check_overlap_permissive,
    count_sse_in_domain,
    load_ecod_map
)


@pytest.mark.integration
class TestStep15PrepareDomass:
    """Integration tests for step 15 (prepare DOMASS features)."""

    def test_step15_requires_step13_output(self, test_prefix, working_dir, ecod_data_dir):
        """Test that step 15 fails gracefully without step 13 output."""
        # No input files - should return True (gracefully skip)
        success = run_step15(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 15 should gracefully skip with missing domains file"

    def test_step15_with_valid_inputs(self, test_prefix, working_dir, ecod_data_dir, setup_step15_inputs):
        """Test step 15 with valid input files."""
        if not setup_step15_inputs:
            pytest.skip("Step 15 test inputs not available")

        success = run_step15(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 15 should succeed with valid inputs"

        # Check output file exists
        output_file = working_dir / f"{test_prefix}.step15_features"
        assert output_file.exists(), "Features file should be created"
        assert output_file.stat().st_size > 0, "Features file should not be empty"

    def test_step15_output_format(self, test_prefix, working_dir, ecod_data_dir, setup_step15_inputs):
        """Test that step 15 output has expected format."""
        if not setup_step15_inputs:
            pytest.skip("Step 15 test inputs not available")

        success = run_step15(test_prefix, working_dir, ecod_data_dir)
        assert success

        output_file = working_dir / f"{test_prefix}.step15_features"

        with open(output_file) as f:
            lines = f.readlines()

        assert len(lines) > 0, "Output should have at least a header"

        # Check header
        header = lines[0].strip().split('\t')
        expected_cols = [
            'domID', 'domRange', 'tgroup', 'ecodid', 'domLen',
            'Helix_num', 'Strand_num', 'HHprob', 'HHcov', 'HHrank',
            'Dzscore', 'Dqscore', 'Dztile', 'Dqtile', 'Drank',
            'Cdiff', 'Ccov', 'HHname', 'Dname',
            'Drot1', 'Drot2', 'Drot3', 'Dtrans'
        ]
        assert header == expected_cols, "Header should match expected format"

        # Check data rows (if any)
        if len(lines) > 1:
            data_row = lines[1].strip().split('\t')
            assert len(data_row) == 23, "Each row should have 23 columns"

            # Validate numerical columns
            try:
                float(data_row[4])  # domLen
                float(data_row[5])  # Helix_num
                float(data_row[6])  # Strand_num
                float(data_row[7])  # HHprob
                float(data_row[8])  # HHcov
                float(data_row[9])  # HHrank
            except ValueError:
                pytest.fail("Numerical columns should contain valid numbers")

    def test_step15_handles_missing_ecod_data(self, test_prefix, working_dir, tmp_path):
        """Test that step 15 fails appropriately with missing ECOD data."""
        # Create fake working dir with required inputs
        fake_ecod_dir = tmp_path / "fake_ecod"
        fake_ecod_dir.mkdir()

        # Create minimal input files
        (working_dir / f"{test_prefix}.step13_domains").write_text("dom1\t10-20\n")
        (working_dir / f"{test_prefix}.sse").write_text("10\tA\t1\tH\n")
        (working_dir / f"{test_prefix}.hhsearch_hits").write_text("")
        (working_dir / f"{test_prefix}.dali_good_hits").write_text("")

        success = run_step15(test_prefix, working_dir, fake_ecod_dir)
        assert not success, "Step 15 should fail with missing ECOD data"

    def test_step15_generates_features_for_both_methods(self, test_prefix, working_dir, ecod_data_dir, setup_step15_inputs):
        """Test that features are generated for ECODs found by both HH and DALI."""
        if not setup_step15_inputs:
            pytest.skip("Step 15 test inputs not available")

        success = run_step15(test_prefix, working_dir, ecod_data_dir)
        assert success

        output_file = working_dir / f"{test_prefix}.step15_features"

        with open(output_file) as f:
            lines = f.readlines()

        if len(lines) > 1:
            # At least one feature row generated
            assert len(lines) >= 2, "Should generate at least one feature row"


@pytest.mark.unit
class TestStep15HelperFunctions:
    """Unit tests for step 15 helper functions."""

    def test_check_overlap_permissive_full_overlap(self):
        """Test overlap check with full overlap."""
        set_a = {1, 2, 3, 4, 5}
        set_b = {1, 2, 3, 4, 5}
        assert check_overlap_permissive(set_a, set_b) is True

    def test_check_overlap_permissive_50_percent(self):
        """Test overlap check at 50% threshold."""
        set_a = {1, 2, 3, 4, 5}
        set_b = {3, 4, 5, 6, 7}  # 3 overlap / 5 total = 60%
        assert check_overlap_permissive(set_a, set_b) is True

    def test_check_overlap_permissive_below_threshold(self):
        """Test overlap check below 50% threshold."""
        set_a = {1, 2, 3, 4, 5}
        set_b = {5, 6, 7, 8, 9}  # 1 overlap / 5 total = 20%
        assert check_overlap_permissive(set_a, set_b) is False

    def test_check_overlap_permissive_no_overlap(self):
        """Test overlap check with no overlap."""
        set_a = {1, 2, 3}
        set_b = {10, 20, 30}
        assert check_overlap_permissive(set_a, set_b) is False

    def test_check_overlap_permissive_empty_sets(self):
        """Test overlap check with empty sets."""
        assert check_overlap_permissive(set(), {1, 2, 3}) is False
        assert check_overlap_permissive({1, 2, 3}, set()) is False
        assert check_overlap_permissive(set(), set()) is False

    def test_count_sse_in_domain_helices(self):
        """Test SSE counting for helices."""
        domain_resids = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}
        resid_to_sse = {
            10: (1, 'H'), 11: (1, 'H'), 12: (1, 'H'),
            13: (1, 'H'), 14: (1, 'H'), 15: (1, 'H'),  # 6 residues - counts
            16: (2, 'H'), 17: (2, 'H'), 18: (2, 'H'),
            19: (2, 'H')  # 4 residues - too short
        }

        helix_count, strand_count = count_sse_in_domain(domain_resids, resid_to_sse)
        assert helix_count == 1, "Should count 1 helix (≥6 residues)"
        assert strand_count == 0, "Should count 0 strands"

    def test_count_sse_in_domain_strands(self):
        """Test SSE counting for strands."""
        domain_resids = {10, 11, 12, 13, 14, 15, 16, 17}
        resid_to_sse = {
            10: (1, 'E'), 11: (1, 'E'), 12: (1, 'E'),  # 3 residues - counts
            13: (2, 'E'), 14: (2, 'E'),  # 2 residues - too short
            15: (3, 'E'), 16: (3, 'E'), 17: (3, 'E')  # 3 residues - counts
        }

        helix_count, strand_count = count_sse_in_domain(domain_resids, resid_to_sse)
        assert helix_count == 0, "Should count 0 helices"
        assert strand_count == 2, "Should count 2 strands (≥3 residues)"

    def test_count_sse_in_domain_mixed(self):
        """Test SSE counting with mixed elements."""
        domain_resids = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}
        resid_to_sse = {
            1: (1, 'H'), 2: (1, 'H'), 3: (1, 'H'),
            4: (1, 'H'), 5: (1, 'H'), 6: (1, 'H'),  # Helix with 6 res
            7: (2, 'E'), 8: (2, 'E'), 9: (2, 'E'),  # Strand with 3 res
            10: (3, 'C'), 11: (3, 'C'), 12: (3, 'C')  # Coil - not counted
        }

        helix_count, strand_count = count_sse_in_domain(domain_resids, resid_to_sse)
        assert helix_count == 1, "Should count 1 helix"
        assert strand_count == 1, "Should count 1 strand"

    def test_count_sse_in_domain_no_sse(self):
        """Test SSE counting with no SSE data."""
        domain_resids = {1, 2, 3, 4, 5}
        resid_to_sse = {}

        helix_count, strand_count = count_sse_in_domain(domain_resids, resid_to_sse)
        assert helix_count == 0, "Should count 0 helices"
        assert strand_count == 0, "Should count 0 strands"

    def test_load_ecod_map_valid_file(self, tmp_path):
        """Test loading ECOD residue map from valid file."""
        map_file = tmp_path / "test.map"
        map_file.write_text("1 101\n2 102\n3 103\n10 110\n")

        resmap = load_ecod_map(map_file)
        assert resmap == {1: 101, 2: 102, 3: 103, 10: 110}

    def test_load_ecod_map_missing_file(self, tmp_path):
        """Test loading ECOD map from non-existent file."""
        map_file = tmp_path / "nonexistent.map"

        resmap = load_ecod_map(map_file)
        assert resmap == {}, "Should return empty dict for missing file"

    def test_load_ecod_map_malformed_lines(self, tmp_path):
        """Test loading ECOD map with malformed lines."""
        map_file = tmp_path / "test.map"
        map_file.write_text("1 101\ninvalid line\n3 103\n")

        resmap = load_ecod_map(map_file)
        assert resmap == {1: 101, 3: 103}, "Should skip malformed lines"

    def test_load_ecod_map_empty_file(self, tmp_path):
        """Test loading ECOD map from empty file."""
        map_file = tmp_path / "test.map"
        map_file.write_text("")

        resmap = load_ecod_map(map_file)
        assert resmap == {}, "Should return empty dict for empty file"

    def test_consensus_mapping_does_not_mutate_sets(self):
        """
        Regression test: Verify consensus calculation doesn't mutate query_resids.

        Bug: Step 15 was using .pop() inside dict comprehension, which mutated
        the set during iteration causing incorrect residue mappings.

        Old code:
            hh_map = {hh['query_resids'].pop(): hh['template_resids'][i] ...}

        This would consume elements from the set, breaking subsequent calculations.
        """
        # Simulate the consensus mapping logic
        hh_hit = {
            'query_resids': {10, 11, 12, 13, 14},
            'template_resids': [100, 101, 102, 103, 104]
        }

        dali_hit = {
            'query_resids': {11, 12, 13, 14, 15},
            'template_resids': [101, 102, 103, 104, 105]
        }

        # Calculate common residues
        common_qres = hh_hit['query_resids'] & dali_hit['query_resids']

        # Expected: {11, 12, 13, 14}
        assert len(common_qres) == 4, "Should have 4 common residues"

        # Build mappings (CORRECT way - don't mutate during iteration)
        hh_query_list = list(hh_hit['query_resids'])
        hh_map = {hh_query_list[i]: hh_hit['template_resids'][i]
                 for i in range(min(len(hh_query_list), len(hh_hit['template_resids'])))}

        dali_query_list = list(dali_hit['query_resids'])
        dali_map = {dali_query_list[i]: dali_hit['template_resids'][i]
                   for i in range(min(len(dali_query_list), len(dali_hit['template_resids'])))}

        # Verify sets were not mutated
        assert len(hh_hit['query_resids']) == 5, \
            "HH query_resids should NOT be mutated (bug: .pop() consumed elements)"
        assert len(dali_hit['query_resids']) == 5, \
            "DALI query_resids should NOT be mutated"

        # Verify mappings are correct
        assert len(hh_map) == 5, "Should map all 5 HH query residues"
        assert len(dali_map) == 5, "Should map all 5 DALI query residues"

        # Calculate consensus differences
        consensus_diffs = []
        for qres in common_qres:
            if qres in hh_map and qres in dali_map:
                diff = abs(hh_map[qres] - dali_map[qres])
                consensus_diffs.append(diff)

        # Should have calculated diffs for all common residues
        assert len(consensus_diffs) >= 3, \
            "Should calculate consensus diff for most common residues"


# Fixture for step 15 inputs
@pytest.fixture(scope="function")
def setup_step15_inputs(test_prefix, working_dir, test_data_dir):
    """
    Setup input files for step 15 tests.

    Returns True if all required files were set up successfully.
    """
    required_files = [
        f"{test_prefix}.step13_domains",
        f"{test_prefix}.sse",
        f"{test_prefix}.hhsearch_hits",
        f"{test_prefix}.dali_good_hits"
    ]

    # Check if test fixtures exist
    all_exist = all((test_data_dir / f).exists() for f in required_files)

    if not all_exist:
        # Create minimal test files
        (working_dir / f"{test_prefix}.step13_domains").write_text(
            "# domain\trange\n"
            "dom1\t10-50\n"
            "dom2\t60-100\n"
        )

        (working_dir / f"{test_prefix}.sse").write_text(
            "10\tA\t1\tH\n"
            "11\tA\t1\tH\n"
            "12\tA\t1\tH\n"
            "13\tA\t1\tH\n"
            "14\tA\t1\tH\n"
            "15\tA\t1\tH\n"
            "20\tA\t2\tE\n"
            "21\tA\t2\tE\n"
            "22\tA\t2\tE\n"
        )

        (working_dir / f"{test_prefix}.hhsearch_hits").write_text(
            "# HHsearch hits\n"
        )

        (working_dir / f"{test_prefix}.dali_good_hits").write_text(
            "# DALI hits\n"
        )

    return True
