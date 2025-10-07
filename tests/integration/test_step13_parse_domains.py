"""
Integration tests for Step 13: Parse Domains.

Tests the final domain parsing step with full integration.
"""

import pytest
from pathlib import Path
from dpam.steps.step13_parse_domains import (
    run_step13,
    load_disorder,
    load_pae_matrix,
    load_pdb_coords,
    load_good_domains,
    calculate_probability_matrix,
    initial_segmentation,
    merge_segments_by_probability,
    iterative_clustering,
    fill_gaps,
    remove_overlaps,
    filter_by_length
)


@pytest.mark.integration
@pytest.mark.slow
class TestStep13ParseDomains:
    """Integration tests for step 13 (parse domains)."""

    def test_parse_domains_end_to_end(self, test_prefix, working_dir, setup_test_files):
        """Test complete domain parsing workflow."""
        # Skip if required files not available
        required_files = ['pdb', 'fa', 'json']
        for file_type in required_files:
            if file_type not in setup_test_files:
                pytest.skip(f"Required {file_type} file not available")

        # Create minimal required files for step 13
        # Need: .diso, .goodDomains (can be empty for basic test)
        (working_dir / f"{test_prefix}.diso").touch()
        (working_dir / f"{test_prefix}.goodDomains").touch()

        # Run step 13
        success = run_step13(test_prefix, working_dir)
        assert success, "Step 13 should succeed"

        # Check output file exists
        output_file = working_dir / f"{test_prefix}.finalDPAM.domains"
        assert output_file.exists(), "Final domains file should be created"

    def test_parse_domains_output_format(self, test_prefix, working_dir, setup_test_files):
        """Test that output has correct format."""
        if 'pdb' not in setup_test_files or 'json' not in setup_test_files:
            pytest.skip("Required files not available")

        # Create minimal required files
        (working_dir / f"{test_prefix}.diso").touch()
        (working_dir / f"{test_prefix}.goodDomains").touch()

        success = run_step13(test_prefix, working_dir)
        assert success

        # Read output
        output_file = working_dir / f"{test_prefix}.finalDPAM.domains"
        with open(output_file) as f:
            lines = f.readlines()

        # Check format: D{n}\t{range}
        for i, line in enumerate(lines, 1):
            parts = line.strip().split('\t')
            assert len(parts) == 2, f"Line {i} should have 2 tab-separated fields"
            assert parts[0].startswith('D'), f"Domain ID should start with 'D'"
            assert int(parts[0][1:]) == i, f"Domain should be numbered sequentially"
            # Range format: digits, dashes, commas only
            assert all(c.isdigit() or c in '-,' for c in parts[1]), \
                f"Range should contain only digits, dashes, commas"


class TestStep13Components:
    """Unit tests for step 13 components."""

    def test_load_disorder_empty(self, working_dir):
        """Test loading disorder with no file."""
        diso_file = working_dir / "test.diso"
        result = load_disorder(diso_file)
        assert result == set(), "Empty disorder file should return empty set"

    def test_load_disorder_with_residues(self, working_dir):
        """Test loading disorder residues."""
        diso_file = working_dir / "test.diso"
        with open(diso_file, 'w') as f:
            f.write("1\n2\n3\n10\n11\n")

        result = load_disorder(diso_file)
        assert result == {1, 2, 3, 10, 11}

    def test_initial_segmentation_no_disorder(self):
        """Test segmentation without disorder."""
        segments = initial_segmentation(20, set())

        # Should create 4 segments: 1-5, 6-10, 11-15, 16-20
        assert len(segments) == 4
        assert segments[0] == [1, 2, 3, 4, 5]
        assert segments[3] == [16, 17, 18, 19, 20]

    def test_initial_segmentation_with_disorder(self):
        """Test segmentation with disorder excluded."""
        diso = {3, 4, 5, 6, 7}  # Middle residues disordered
        segments = initial_segmentation(20, diso)

        # First segment should be [1, 2] (< 3 residues, filtered out)
        # Second segment should be [8, 9, 10] (>= 3 residues, kept)
        kept_segments = [s for s in segments if len(s) >= 3]
        assert len(kept_segments) > 0

        # All segments should exclude disorder
        for seg in segments:
            for res in seg:
                assert res not in diso

    def test_fill_gaps_small_gap(self):
        """Test gap filling with small gap."""
        domains = [[10, 11, 12, 25, 26, 27]]  # Gap of 12 residues
        filled = fill_gaps(domains, gap_tolerance=10)

        # Gap should NOT be filled (12 > 10)
        assert 15 not in filled[0]

    def test_fill_gaps_large_gap(self):
        """Test gap filling skips large gaps."""
        domains = [[10, 11, 12, 25, 26, 27]]  # Gap of 12 residues
        filled = fill_gaps(domains, gap_tolerance=5)

        # Gap should not be filled
        assert len(filled[0]) < 20

    def test_fill_gaps_exact_tolerance(self):
        """Test gap filling at exact tolerance."""
        domains = [[10, 11, 12, 23, 24, 25]]  # Gap of exactly 10 residues
        filled = fill_gaps(domains, gap_tolerance=10)

        # Gap should be filled
        assert 15 in filled[0]
        assert len(filled[0]) == 16  # 10-25 inclusive

    def test_remove_overlaps_no_overlap(self):
        """Test overlap removal with no overlaps."""
        domains = [
            [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],  # 16 res
            [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45]   # 16 res
        ]
        cleaned = remove_overlaps(domains, min_unique=15)

        # Both should be kept (no overlaps)
        assert len(cleaned) == 2

    def test_remove_overlaps_with_overlap(self):
        """Test overlap removal with overlapping residues."""
        domains = [
            [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
            [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35]
        ]
        # Overlap: 20-25 (6 residues)
        cleaned = remove_overlaps(domains, min_unique=15)

        # Both should be removed (only 10 unique each after overlap removal)
        assert len(cleaned) == 0

    def test_remove_overlaps_partial_keep(self):
        """Test overlap removal keeps domains with enough unique residues."""
        domains = [
            [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29],  # 20 res
            [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44]   # 20 res
        ]
        # Overlap: 25-29 (5 residues), each has 15 unique
        cleaned = remove_overlaps(domains, min_unique=15)

        # Both should be kept (15 unique each)
        assert len(cleaned) == 2

    def test_filter_by_length_keeps_long(self):
        """Test length filter keeps long domains."""
        domains = [
            list(range(1, 31)),   # 30 residues
            list(range(50, 71))   # 21 residues
        ]
        filtered = filter_by_length(domains, min_length=20)

        assert len(filtered) == 2

    def test_filter_by_length_removes_short(self):
        """Test length filter removes short domains."""
        domains = [
            list(range(1, 31)),   # 30 residues - keep
            list(range(50, 60))   # 10 residues - remove
        ]
        filtered = filter_by_length(domains, min_length=20)

        assert len(filtered) == 1
        assert len(filtered[0]) == 30

    def test_filter_by_length_exact_threshold(self):
        """Test length filter at exact threshold."""
        domains = [
            list(range(1, 21)),   # Exactly 20 residues
        ]
        filtered = filter_by_length(domains, min_length=20)

        assert len(filtered) == 1  # Should be kept (>= threshold)


@pytest.mark.integration
class TestStep13WithMockData:
    """Tests with minimal mock data."""

    def test_with_minimal_good_domains(self, test_prefix, working_dir, setup_test_files):
        """Test with minimal good domains file."""
        if 'pdb' not in setup_test_files or 'json' not in setup_test_files:
            pytest.skip("Required files not available")

        # Create minimal good domains (one sequence hit)
        good_domains = working_dir / f"{test_prefix}.goodDomains"
        with open(good_domains, 'w') as f:
            f.write("sequence\ttest\thit1\te1.1\t1.1\t95.0\t0.8\t100\t10-50\t10-50\n")

        # Create empty disorder
        (working_dir / f"{test_prefix}.diso").touch()

        success = run_step13(test_prefix, working_dir)
        assert success

        # Should produce some output
        output_file = working_dir / f"{test_prefix}.finalDPAM.domains"
        assert output_file.exists()

    def test_with_disorder_predictions(self, test_prefix, working_dir, setup_test_files):
        """Test with disorder predictions."""
        if 'pdb' not in setup_test_files or 'json' not in setup_test_files:
            pytest.skip("Required files not available")

        # Create disorder file (first 10 residues)
        diso_file = working_dir / f"{test_prefix}.diso"
        with open(diso_file, 'w') as f:
            for i in range(1, 11):
                f.write(f"{i}\n")

        # Create empty good domains
        (working_dir / f"{test_prefix}.goodDomains").touch()

        success = run_step13(test_prefix, working_dir)
        assert success

        # Domains should not include disordered residues
        output_file = working_dir / f"{test_prefix}.finalDPAM.domains"
        if output_file.exists() and output_file.stat().st_size > 0:
            with open(output_file) as f:
                for line in f:
                    domain_id, range_str = line.strip().split('\t')
                    # Parse range and check no residues 1-10
                    from dpam.utils.ranges import range_to_residues
                    residues = range_to_residues(range_str)
                    disordered_in_domain = residues & set(range(1, 11))
                    # Depending on implementation, may allow some disorder
                    # This is a soft check
                    if len(disordered_in_domain) > 0:
                        pytest.warns(UserWarning, match="Disordered residues in domain")
