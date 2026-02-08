"""
Integration tests for Step 8: Analyze DALI Results.

Tests the analysis of structural alignments including scoring and ranking.
"""

import pytest
from pathlib import Path
from dpam.steps.step08_analyze_dali import run_step8
from dpam.core.models import ReferenceData


@pytest.mark.integration
class TestStep08AnalyzeDALI:
    """Integration tests for step 8 (analyze DALI results)."""

    @pytest.fixture
    def mock_reference_data(self):
        """Create minimal mock ECOD reference data for testing."""
        # Mock ECOD_metadata: ecod_num -> (ecod_id, family)
        ecod_metadata = {
            '000000003': ('e2rspA1', 'F_001'),
            '000000017': ('e2pmaA1', 'F_002'),
            '000000020': ('e1eu1A1', 'F_001'),  # Same family as 003
        }

        # Create ReferenceData with minimal required fields
        return ReferenceData(
            ecod_lengths={},
            ecod_norms={},
            ecod_pdbmap={},
            ecod_domain_info={},
            ecod_weights={},
            ecod_metadata=ecod_metadata
        )

    @pytest.fixture
    def setup_mock_data_files(self, working_dir):
        """Create mock ecod_weights and ecod_domain_info directories."""
        # Create directories (match actual ECOD reference data layout)
        weights_dir = working_dir / 'posi_weights'
        info_dir = working_dir / 'ecod_internal'
        weights_dir.mkdir()
        info_dir.mkdir()

        # Create weight files
        # Format: position ... ... weight
        weight_file_003 = weights_dir / '000000003.weight'
        weight_file_003.write_text("""1 X X 0.8
2 X X 0.9
3 X X 1.0
4 X X 0.7
5 X X 0.6
""")

        weight_file_017 = weights_dir / '000000017.weight'
        weight_file_017.write_text("""1 X X 0.5
2 X X 0.6
3 X X 0.7
""")

        weight_file_020 = weights_dir / '000000020.weight'
        weight_file_020.write_text("""1 X X 1.0
2 X X 0.9
3 X X 0.8
""")

        # Create domain info files
        # Format: ... zscore qscore
        info_file_003 = info_dir / '000000003.info'
        info_file_003.write_text("""X 5.0 0.75
X 6.0 0.80
X 7.0 0.85
X 8.0 0.90
X 4.0 0.70
""")

        info_file_017 = info_dir / '000000017.info'
        info_file_017.write_text("""X 3.0 0.60
X 4.0 0.65
X 5.0 0.70
""")

        info_file_020 = info_dir / '000000020.info'
        info_file_020.write_text("""X 6.0 0.80
X 7.0 0.85
X 8.0 0.90
""")

        return working_dir

    @pytest.fixture
    def setup_dali_hits(self, test_prefix, working_dir):
        """Create mock DALI hits file from step 7.

        Note: Hit names use ECOD UIDs (000000003) for testing simplicity.
        In real data, these would be domain IDs and require reverse lookup.
        """
        dali_file = working_dir / f'{test_prefix}_iterativdDali_hits'
        content = """>000000003_1\t8.5\t5\t75\t124
10\t1
11\t2
12\t3
13\t4
14\t5
>000000017_1\t6.2\t3\t75\t141
20\t1
21\t2
22\t3
>000000020_1\t7.8\t3\t75\t155
30\t1
31\t2
32\t3
"""
        dali_file.write_text(content)
        return dali_file

    def test_analyze_requires_dali_hits(self, test_prefix, working_dir,
                                       mock_reference_data, setup_mock_data_files):
        """Test that step 8 fails gracefully without DALI hits file."""
        # Don't create DALI hits file
        success = run_step8(test_prefix, working_dir,
                           mock_reference_data, setup_mock_data_files)
        assert not success, "Step 8 should fail without DALI hits file"

    def test_analyze_with_test_data(self, test_prefix, working_dir,
                                    mock_reference_data, setup_mock_data_files,
                                    setup_dali_hits):
        """Test analysis with test data."""
        # Run step 8
        success = run_step8(test_prefix, working_dir,
                           mock_reference_data, setup_mock_data_files)
        assert success, "Step 8 should complete successfully"

        # Check output file exists
        output_file = working_dir / f'{test_prefix}_good_hits'
        assert output_file.exists(), "Output file should be created"

        # Check output has content
        assert output_file.stat().st_size > 0, "Output should not be empty"

    def test_analyze_output_format(self, test_prefix, working_dir,
                                   mock_reference_data, setup_mock_data_files,
                                   setup_dali_hits):
        """Test that output has expected format."""
        # Run step 8
        success = run_step8(test_prefix, working_dir,
                           mock_reference_data, setup_mock_data_files)
        assert success

        # Read and validate output format
        output_file = working_dir / f'{test_prefix}_good_hits'
        with open(output_file, 'r') as f:
            lines = f.readlines()

        # Check header
        header = lines[0].strip().split('\t')
        expected_fields = [
            'hitname', 'ecodnum', 'ecodkey', 'hgroup',
            'zscore', 'qscore', 'ztile', 'qtile', 'rank',
            'qrange', 'erange',
            'rotation1', 'rotation2', 'rotation3', 'translation'
        ]
        assert header == expected_fields, "Header should match expected format"

        # Check data lines
        if len(lines) > 1:
            # First data line
            fields = lines[1].strip().split('\t')
            assert len(fields) == 15, "Data line should have 15 tab-delimited fields"

            # Field validations
            assert '_' in fields[0], "Hitname should contain underscore"

            # Z-score should be float
            try:
                zscore = float(fields[4])
                assert zscore > 0, "Z-score should be positive"
            except ValueError:
                pytest.fail("zscore should be a valid float")

            # Q-score should be float
            try:
                qscore = float(fields[5])
            except ValueError:
                pytest.fail("qscore should be a valid float")

    def test_analyze_calculates_scores(self, test_prefix, working_dir,
                                       mock_reference_data, setup_mock_data_files,
                                       setup_dali_hits):
        """Test that analysis calculates q-scores."""
        # Run step 8
        success = run_step8(test_prefix, working_dir,
                           mock_reference_data, setup_mock_data_files)
        assert success

        # Parse output
        output_file = working_dir / f'{test_prefix}_good_hits'
        with open(output_file, 'r') as f:
            lines = f.readlines()[1:]  # Skip header

        # Check q-scores are calculated
        for line in lines:
            fields = line.strip().split('\t')
            qscore = float(fields[5])
            # Q-score should be between 0 and 1 (or -1 if no weights)
            assert -1 <= qscore <= 1, "Q-score should be normalized 0-1 or -1"

    def test_analyze_calculates_percentiles(self, test_prefix, working_dir,
                                            mock_reference_data,
                                            setup_mock_data_files,
                                            setup_dali_hits):
        """Test that analysis calculates percentiles."""
        # Run step 8
        success = run_step8(test_prefix, working_dir,
                           mock_reference_data, setup_mock_data_files)
        assert success

        # Parse output
        output_file = working_dir / f'{test_prefix}_good_hits'
        with open(output_file, 'r') as f:
            lines = f.readlines()[1:]  # Skip header

        # Check percentiles are calculated
        for line in lines:
            fields = line.strip().split('\t')
            ztile = float(fields[6])
            qtile = float(fields[7])

            # Percentiles should be between 0 and 1 (or -1 if no data)
            assert -1 <= ztile <= 1, "Z-tile should be 0-1 or -1"
            assert -1 <= qtile <= 1, "Q-tile should be 0-1 or -1"

    def test_analyze_calculates_ranks(self, test_prefix, working_dir,
                                      mock_reference_data, setup_mock_data_files,
                                      setup_dali_hits):
        """Test that analysis calculates position ranks."""
        # Run step 8
        success = run_step8(test_prefix, working_dir,
                           mock_reference_data, setup_mock_data_files)
        assert success

        # Parse output
        output_file = working_dir / f'{test_prefix}_good_hits'
        with open(output_file, 'r') as f:
            lines = f.readlines()[1:]  # Skip header

        # Check ranks are calculated
        for line in lines:
            fields = line.strip().split('\t')
            rank = float(fields[8])

            # Rank should be positive
            assert rank > 0, "Rank should be positive"

    def test_analyze_preserves_zscore(self, test_prefix, working_dir,
                                      mock_reference_data, setup_mock_data_files,
                                      setup_dali_hits):
        """Test that z-scores from DALI are preserved."""
        # Run step 8
        success = run_step8(test_prefix, working_dir,
                           mock_reference_data, setup_mock_data_files)
        assert success

        # Parse output
        output_file = working_dir / f'{test_prefix}_good_hits'
        with open(output_file, 'r') as f:
            lines = f.readlines()[1:]  # Skip header

        # Extract z-scores
        zscores = [float(line.split('\t')[4]) for line in lines]

        # Should match input z-scores (8.5, 6.2, 7.8)
        assert 8.5 in zscores, "Should preserve z-score 8.5"
        assert 6.2 in zscores, "Should preserve z-score 6.2"
        assert 7.8 in zscores, "Should preserve z-score 7.8"

    def test_analyze_sorts_by_zscore(self, test_prefix, working_dir,
                                     mock_reference_data, setup_mock_data_files,
                                     setup_dali_hits):
        """Test that output is sorted by z-score descending."""
        # Run step 8
        success = run_step8(test_prefix, working_dir,
                           mock_reference_data, setup_mock_data_files)
        assert success

        # Parse output
        output_file = working_dir / f'{test_prefix}_good_hits'
        with open(output_file, 'r') as f:
            lines = f.readlines()[1:]  # Skip header

        # Extract z-scores
        zscores = [float(line.split('\t')[4]) for line in lines]

        # Check sorted descending
        for i in range(len(zscores) - 1):
            assert zscores[i] >= zscores[i + 1], "Z-scores should be sorted descending"

    def test_analyze_includes_ranges(self, test_prefix, working_dir,
                                     mock_reference_data, setup_mock_data_files,
                                     setup_dali_hits):
        """Test that query and template ranges are included."""
        # Run step 8
        success = run_step8(test_prefix, working_dir,
                           mock_reference_data, setup_mock_data_files)
        assert success

        # Parse output
        output_file = working_dir / f'{test_prefix}_good_hits'
        with open(output_file, 'r') as f:
            lines = f.readlines()[1:]  # Skip header

        # Check ranges are present
        for line in lines:
            fields = line.strip().split('\t')
            qrange = fields[9]
            erange = fields[10]

            # Ranges should contain hyphen
            assert '-' in qrange, "Query range should contain hyphen"
            assert '-' in erange, "Template range should contain hyphen"

    def test_analyze_with_empty_input(self, test_prefix, working_dir,
                                      mock_reference_data, setup_mock_data_files):
        """Test analysis with empty DALI hits file."""
        # Create empty DALI hits file
        dali_file = working_dir / f'{test_prefix}_iterativdDali_hits'
        dali_file.write_text("")

        # Run step 8
        success = run_step8(test_prefix, working_dir,
                           mock_reference_data, setup_mock_data_files)
        assert success, "Should succeed with empty input"

        # Check output
        output_file = working_dir / f'{test_prefix}_good_hits'
        with open(output_file, 'r') as f:
            lines = f.readlines()

        # Should have header but no data
        assert len(lines) == 1, "Should only have header with empty input"

    def test_analyze_with_missing_weights(self, test_prefix, working_dir,
                                          mock_reference_data):
        """Test analysis when weight files are missing."""
        # Create DALI hits but no weight/info files
        dali_file = working_dir / f'{test_prefix}_iterativdDali_hits'
        dali_file.write_text(""">000000003_1\t5.0\t3\t75\t124
10\t1
11\t2
12\t3
""")

        # Run step 8 without setup_mock_data_files
        success = run_step8(test_prefix, working_dir,
                           mock_reference_data, working_dir)
        assert success, "Should succeed even without weight files"

        # Check output
        output_file = working_dir / f'{test_prefix}_good_hits'
        with open(output_file, 'r') as f:
            lines = f.readlines()

        # Should have header and data
        assert len(lines) >= 1, "Should have at least header"

        if len(lines) > 1:
            # Check that q-score/percentiles are -1 (missing data indicator)
            fields = lines[1].strip().split('\t')
            qscore = float(fields[5])
            ztile = float(fields[6])
            qtile = float(fields[7])

            # Missing weights should result in -1 values
            assert qscore == -1.0 or qscore >= 0, "Q-score should be -1 or valid"
            assert ztile == -1.0 or (0 <= ztile <= 1), "Z-tile should be -1 or 0-1"
            assert qtile == -1.0 or (0 <= qtile <= 1), "Q-tile should be -1 or 0-1"


@pytest.mark.integration
class TestStep08Functions:
    """Test individual Step 8 functions."""

    def test_get_range_basic(self):
        """Test range string generation."""
        from dpam.steps.step08_analyze_dali import get_range

        # Single segment
        assert get_range([10, 11, 12, 13]) == "10-13"

        # Multiple segments
        assert get_range([10, 11, 15, 16, 20]) == "10-11,15-16,20-20"

        # Unsorted input
        assert get_range([15, 10, 11, 20, 16]) == "10-11,15-16,20-20"

        # Empty input
        assert get_range([]) == ""

    def test_calculate_percentile(self):
        """Test percentile calculation."""
        from dpam.steps.step08_analyze_dali import calculate_percentile

        values = [1.0, 2.0, 3.0, 4.0, 5.0]

        # Value in middle
        pct = calculate_percentile(3.0, values)
        assert pct == 0.4, "Middle value should be 40th percentile"

        # Highest value
        pct = calculate_percentile(5.0, values)
        assert pct == 0.0, "Highest value should be 0th percentile"

        # Lowest value
        pct = calculate_percentile(1.0, values)
        assert pct == 0.8, "Lowest value should be 80th percentile"

        # Empty list
        pct = calculate_percentile(3.0, [])
        assert pct == -1.0, "Empty list should return -1"
