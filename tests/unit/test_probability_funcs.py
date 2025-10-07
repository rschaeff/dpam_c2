"""
Unit tests for Step 13 probability functions.

These functions have exact binned thresholds that must match v1.0.
Testing boundary conditions is critical for backward compatibility.
"""

import pytest
from dpam.steps.step13_parse_domains import (
    get_PDB_prob,
    get_PAE_prob,
    get_HHS_prob,
    get_DALI_prob,
    aggregate_hhs_score,
    aggregate_dali_score
)


class TestPDBProbability:
    """Tests for PDB distance probability function."""

    def test_exact_thresholds(self):
        """Test exact threshold values."""
        assert get_PDB_prob(3.0) == 0.95
        assert get_PDB_prob(6.0) == 0.94
        assert get_PDB_prob(8.0) == 0.88
        assert get_PDB_prob(10.0) == 0.84
        assert get_PDB_prob(12.0) == 0.79
        assert get_PDB_prob(20.0) == 0.59
        assert get_PDB_prob(200.0) == 0.08

    def test_boundary_conditions(self):
        """Test values just above and below thresholds."""
        # Just below threshold should stay in same bin
        assert get_PDB_prob(2.99) == 0.95  # <= 3
        assert get_PDB_prob(3.0) == 0.95   # <= 3
        assert get_PDB_prob(5.99) == 0.94  # <= 6 but > 3
        assert get_PDB_prob(6.0) == 0.94   # <= 6
        assert get_PDB_prob(7.99) == 0.88  # <= 8 but > 6

        # Just above threshold moves to next bin
        assert get_PDB_prob(3.01) == 0.94  # <= 6 but > 3
        assert get_PDB_prob(6.01) == 0.88  # <= 8 but > 6
        assert get_PDB_prob(8.01) == 0.84  # <= 10 but > 8

    def test_extreme_values(self):
        """Test extreme distance values."""
        # Very small distance
        assert get_PDB_prob(0.0) == 0.95
        assert get_PDB_prob(1.0) == 0.95

        # Very large distance
        assert get_PDB_prob(1000.0) == 0.06
        assert get_PDB_prob(10000.0) == 0.06

    def test_all_bins(self):
        """Test all probability bins are reachable."""
        distances = [2, 5, 7, 9, 11, 13, 15, 17, 19, 22, 28, 33, 38, 45, 55, 70, 90, 120, 180, 250]
        expected = [0.95, 0.94, 0.88, 0.84, 0.79, 0.74, 0.69, 0.64, 0.59,
                    0.51, 0.43, 0.38, 0.34, 0.28, 0.23, 0.18, 0.14, 0.1, 0.08, 0.06]

        for dist, exp_prob in zip(distances, expected):
            assert get_PDB_prob(dist) == exp_prob, f"Failed for distance {dist}"


class TestPAEProbability:
    """Tests for PAE error probability function."""

    def test_exact_thresholds(self):
        """Test exact threshold values."""
        assert get_PAE_prob(1.0) == 0.97
        assert get_PAE_prob(2.0) == 0.89
        assert get_PAE_prob(5.0) == 0.74
        assert get_PAE_prob(10.0) == 0.56
        assert get_PAE_prob(20.0) == 0.35
        assert get_PAE_prob(28.0) == 0.19

    def test_boundary_conditions(self):
        """Test values around thresholds."""
        assert get_PAE_prob(0.99) == 0.97  # <= 1
        assert get_PAE_prob(1.0) == 0.97   # <= 1
        assert get_PAE_prob(1.01) == 0.89  # <= 2 but > 1
        assert get_PAE_prob(3.99) == 0.78  # <= 4 but > 3
        assert get_PAE_prob(4.0) == 0.78   # <= 4
        assert get_PAE_prob(4.99) == 0.74  # <= 5 but > 4
        assert get_PAE_prob(5.0) == 0.74   # <= 5
        assert get_PAE_prob(5.01) == 0.7   # <= 6 but > 5

    def test_extreme_values(self):
        """Test extreme error values."""
        # Very low error (high confidence)
        assert get_PAE_prob(0.0) == 0.97
        assert get_PAE_prob(0.5) == 0.97

        # Very high error (low confidence)
        assert get_PAE_prob(30.0) == 0.11
        assert get_PAE_prob(100.0) == 0.11

    def test_all_bins(self):
        """Test all probability bins."""
        errors = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5,
                 11, 13, 15, 17, 19, 21, 23, 25, 27, 30]
        expected = [0.97, 0.89, 0.83, 0.78, 0.74, 0.7, 0.66, 0.62, 0.59, 0.56,
                    0.51, 0.46, 0.42, 0.38, 0.35, 0.31, 0.27, 0.23, 0.19, 0.11]

        for error, exp_prob in zip(errors, expected):
            assert get_PAE_prob(error) == exp_prob, f"Failed for error {error}"


class TestHHSProbability:
    """Tests for HHsearch score probability function."""

    def test_exact_thresholds(self):
        """Test exact threshold values."""
        assert get_HHS_prob(180.0) == 0.98
        assert get_HHS_prob(160.0) == 0.96
        assert get_HHS_prob(100.0) == 0.85
        assert get_HHS_prob(50.0) == 0.58
        assert get_HHS_prob(40.0) == 0.5

    def test_boundary_conditions(self):
        """Test values around thresholds."""
        assert get_HHS_prob(179.9) == 0.96
        assert get_HHS_prob(180.1) == 0.98
        assert get_HHS_prob(49.9) == 0.5
        assert get_HHS_prob(50.1) == 0.58

    def test_extreme_values(self):
        """Test extreme scores."""
        # Very low score
        assert get_HHS_prob(0.0) == 0.5
        assert get_HHS_prob(10.0) == 0.5

        # Very high score
        assert get_HHS_prob(200.0) == 0.98
        assert get_HHS_prob(1000.0) == 0.98

    def test_all_bins(self):
        """Test all probability bins."""
        scores = [40, 55, 65, 75, 85, 95, 110, 130, 150, 170, 190]
        expected = [0.5, 0.58, 0.66, 0.72, 0.77, 0.81, 0.85, 0.89, 0.93, 0.96, 0.98]

        for score, exp_prob in zip(scores, expected):
            assert get_HHS_prob(score) == exp_prob, f"Failed for score {score}"


class TestDALIProbability:
    """Tests for DALI z-score probability function."""

    def test_exact_thresholds(self):
        """Test exact threshold values."""
        assert get_DALI_prob(35.0) == 0.98
        assert get_DALI_prob(30.0) == 0.96
        assert get_DALI_prob(20.0) == 0.89
        assert get_DALI_prob(10.0) == 0.66
        assert get_DALI_prob(6.0) == 0.55
        assert get_DALI_prob(5.0) == 0.5

    def test_boundary_conditions(self):
        """Test values around thresholds."""
        assert get_DALI_prob(34.9) == 0.96
        assert get_DALI_prob(35.1) == 0.98
        assert get_DALI_prob(5.9) == 0.5
        assert get_DALI_prob(6.1) == 0.55

    def test_extreme_values(self):
        """Test extreme z-scores."""
        # Very low z-score
        assert get_DALI_prob(0.0) == 0.5
        assert get_DALI_prob(2.0) == 0.5

        # Very high z-score
        assert get_DALI_prob(50.0) == 0.98
        assert get_DALI_prob(100.0) == 0.98

    def test_all_bins(self):
        """Test all probability bins."""
        zscores = [5, 7, 9, 11, 13, 15, 17, 19, 22, 27, 32, 40]
        expected = [0.5, 0.55, 0.61, 0.66, 0.72, 0.77, 0.81, 0.85, 0.89, 0.93, 0.96, 0.98]

        for zscore, exp_prob in zip(zscores, expected):
            assert get_DALI_prob(zscore) == exp_prob, f"Failed for z-score {zscore}"


class TestHHSScoreAggregation:
    """Tests for HHsearch score aggregation."""

    def test_empty_scores(self):
        """Test with no scores."""
        assert aggregate_hhs_score([]) == 20.0

    def test_single_score(self):
        """Test with single score."""
        # count=1: max + 1*10 - 10 = max
        assert aggregate_hhs_score([50.0]) == 50.0

    def test_two_scores(self):
        """Test with two scores."""
        # count=2: max + 2*10 - 10 = max + 10
        assert aggregate_hhs_score([50.0, 30.0]) == 60.0

    def test_ten_scores(self):
        """Test with ten scores."""
        # count=10: max + 10*10 - 10 = max + 90
        scores = [50.0] * 10
        assert aggregate_hhs_score(scores) == 140.0

    def test_more_than_ten_scores(self):
        """Test with more than 10 scores."""
        # count>10: max + 100
        scores = [50.0] * 15
        assert aggregate_hhs_score(scores) == 150.0

    def test_eleven_scores_boundary(self):
        """Test boundary at 11 scores."""
        # count=11: max + 100
        scores = [50.0] * 11
        assert aggregate_hhs_score(scores) == 150.0

    def test_max_selection(self):
        """Test that maximum score is selected."""
        scores = [20.0, 80.0, 50.0, 30.0]
        # count=4: max(80) + 4*10 - 10 = 110
        assert aggregate_hhs_score(scores) == 110.0


class TestDALIScoreAggregation:
    """Tests for DALI score aggregation."""

    def test_empty_scores(self):
        """Test with no scores."""
        assert aggregate_dali_score([]) == 1.0

    def test_single_score(self):
        """Test with single score."""
        # count=1: max + 1 - 1 = max
        assert aggregate_dali_score([10.0]) == 10.0

    def test_two_scores(self):
        """Test with two scores."""
        # count=2: max + 2 - 1 = max + 1
        assert aggregate_dali_score([10.0, 8.0]) == 11.0

    def test_five_scores(self):
        """Test with five scores."""
        # count=5: max + 5 - 1 = max + 4
        scores = [10.0] * 5
        assert aggregate_dali_score(scores) == 14.0

    def test_more_than_five_scores(self):
        """Test with more than 5 scores."""
        # count>5: max + 5
        scores = [10.0] * 8
        assert aggregate_dali_score(scores) == 15.0

    def test_six_scores_boundary(self):
        """Test boundary at 6 scores."""
        # count=6: max + 5
        scores = [10.0] * 6
        assert aggregate_dali_score(scores) == 15.0

    def test_max_selection(self):
        """Test that maximum score is selected."""
        scores = [5.0, 15.0, 10.0, 8.0]
        # count=4: max(15) + 4 - 1 = 18
        assert aggregate_dali_score(scores) == 18.0


class TestCombinedProbability:
    """Tests for combined probability calculation."""

    def test_formula_calculation(self):
        """Test the combined probability formula."""
        # Formula: dist^0.1 * pae^0.1 * hhs^0.4 * dali^0.4
        dist_prob = get_PDB_prob(10.0)  # 0.84
        pae_prob = get_PAE_prob(5.0)    # 0.74
        hhs_prob = get_HHS_prob(100.0)  # 0.85
        dali_prob = get_DALI_prob(20.0) # 0.89

        # Calculate combined
        combined = (dist_prob ** 0.1) * (pae_prob ** 0.1) * (hhs_prob ** 0.4) * (dali_prob ** 0.4)

        # Verify it's reasonable (between 0 and 1)
        assert 0.0 <= combined <= 1.0

        # Verify it's close to weighted average (HHS and DALI dominate)
        # Should be closer to sqrt(hhs * dali) than to dist or pae
        expected_approx = (hhs_prob * dali_prob) ** 0.5
        assert abs(combined - expected_approx) < 0.1

    def test_extreme_combinations(self):
        """Test extreme probability combinations."""
        # All high
        combined_high = (0.95 ** 0.1) * (0.97 ** 0.1) * (0.98 ** 0.4) * (0.98 ** 0.4)
        assert combined_high > 0.97

        # All low
        combined_low = (0.06 ** 0.1) * (0.11 ** 0.1) * (0.5 ** 0.4) * (0.5 ** 0.4)
        assert combined_low < 0.6

        # Mixed (HHS/DALI high, PDB/PAE low)
        combined_mixed = (0.06 ** 0.1) * (0.11 ** 0.1) * (0.98 ** 0.4) * (0.98 ** 0.4)
        # HHS/DALI weights (0.4 each) don't fully overcome very low PDB/PAE (0.06, 0.11)
        # Result is ~0.596
        assert 0.55 < combined_mixed < 0.65
