"""
Integration tests for Step 16: Run DOMASS Neural Network.

Tests the TensorFlow model inference for ECOD classification.
"""

import pytest
from pathlib import Path
import numpy as np
from dpam.steps.step16_run_domass import (
    run_step16,
    load_features
)


@pytest.mark.integration
class TestStep16RunDomass:
    """Integration tests for step 16 (run DOMASS)."""

    def test_step16_requires_step15_output(self, test_prefix, working_dir, ecod_data_dir):
        """Test that step 16 gracefully skips without step 15 output."""
        success = run_step16(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 16 should gracefully skip with missing features file"

    def test_step16_requires_model_checkpoint(self, test_prefix, working_dir, tmp_path):
        """Test that step 16 fails without model checkpoint."""
        # Create fake features file
        features_file = working_dir / f"{test_prefix}.step15_features"
        features_file.write_text(
            "domID\tdomRange\ttgroup\tecodid\tdomLen\tHelix_num\tStrand_num\t"
            "HHprob\tHHcov\tHHrank\tDzscore\tDqscore\tDztile\tDqtile\tDrank\t"
            "Cdiff\tCcov\tHHname\tDname\tDrot1\tDrot2\tDrot3\tDtrans\n"
            "dom1\t10-50\t1.1.1\te001\t40\t2\t3\t"
            "0.95\t0.80\t1.5\t12.3\t0.75\t0.85\t0.65\t2.1\t"
            "2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
        )

        # Fake data dir without model
        fake_data_dir = tmp_path / "fake_data"
        fake_data_dir.mkdir()

        success = run_step16(test_prefix, working_dir, fake_data_dir)
        assert not success, "Step 16 should fail without model checkpoint"

    @pytest.mark.slow
    @pytest.mark.skipif(
        True,  # Skip by default - requires TensorFlow and trained model
        reason="Requires TensorFlow and trained DOMASS model"
    )
    def test_step16_with_valid_inputs(self, test_prefix, working_dir, ecod_data_dir):
        """Test step 16 with valid inputs and model."""
        # Create test features file
        features_file = working_dir / f"{test_prefix}.step15_features"
        features_file.write_text(
            "domID\tdomRange\ttgroup\tecodid\tdomLen\tHelix_num\tStrand_num\t"
            "HHprob\tHHcov\tHHrank\tDzscore\tDqscore\tDztile\tDqtile\tDrank\t"
            "Cdiff\tCcov\tHHname\tDname\tDrot1\tDrot2\tDrot3\tDtrans\n"
            "dom1\t10-50\t1.1.1\te001\t40\t2\t3\t"
            "0.95\t0.80\t1.5\t12.3\t0.75\t0.85\t0.65\t2.1\t"
            "2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
        )

        # Check if model exists
        model_path = ecod_data_dir / "domass_epo29"
        if not model_path.with_suffix('.meta').exists():
            pytest.skip("DOMASS model checkpoint not found")

        success = run_step16(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 16 should succeed with valid inputs and model"

        # Check output exists
        output_file = working_dir / f"{test_prefix}.step16_predictions"
        assert output_file.exists(), "Predictions file should be created"

    @pytest.mark.slow
    @pytest.mark.skipif(
        True,
        reason="Requires TensorFlow and trained DOMASS model"
    )
    def test_step16_output_format(self, test_prefix, working_dir, ecod_data_dir):
        """Test that step 16 output has expected format."""
        # Create test features file with multiple rows
        features_file = working_dir / f"{test_prefix}.step15_features"
        features_file.write_text(
            "domID\tdomRange\ttgroup\tecodid\tdomLen\tHelix_num\tStrand_num\t"
            "HHprob\tHHcov\tHHrank\tDzscore\tDqscore\tDztile\tDqtile\tDrank\t"
            "Cdiff\tCcov\tHHname\tDname\tDrot1\tDrot2\tDrot3\tDtrans\n"
            "dom1\t10-50\t1.1.1\te001\t40\t2\t3\t"
            "0.95\t0.80\t1.5\t12.3\t0.75\t0.85\t0.65\t2.1\t"
            "2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
            "dom2\t60-100\t2.2.2\te002\t40\t3\t2\t"
            "0.90\t0.75\t2.0\t10.5\t0.70\t0.80\t0.60\t3.0\t"
            "3.0\t0.65\thit3\thit4\t0.5\t0.5\t0.5\t3.5\n"
        )

        model_path = ecod_data_dir / "domass_epo29"
        if not model_path.with_suffix('.meta').exists():
            pytest.skip("DOMASS model checkpoint not found")

        success = run_step16(test_prefix, working_dir, ecod_data_dir)
        assert success

        output_file = working_dir / f"{test_prefix}.step16_predictions"

        with open(output_file) as f:
            lines = f.readlines()

        assert len(lines) >= 1, "Output should have at least a header"

        # Check header format
        header = lines[0].strip().split('\t')
        expected_start = ['Domain', 'Range', 'Tgroup', 'ECOD_ref', 'DPAM_prob']
        assert header[:5] == expected_start, "Header should start with expected columns"

        # Check data rows
        if len(lines) > 1:
            for i, line in enumerate(lines[1:], 1):
                parts = line.strip().split('\t')
                assert len(parts) >= 20, f"Row {i} should have at least 20 columns"

                # Validate DPAM probability is in [0, 1]
                prob = float(parts[4])
                assert 0.0 <= prob <= 1.0, f"DPAM probability should be in [0, 1], got {prob}"

    def test_step16_handles_empty_features(self, test_prefix, working_dir, ecod_data_dir):
        """Test that step 16 handles empty features file gracefully."""
        # Create features file with only header
        features_file = working_dir / f"{test_prefix}.step15_features"
        features_file.write_text(
            "domID\tdomRange\ttgroup\tecodid\tdomLen\tHelix_num\tStrand_num\t"
            "HHprob\tHHcov\tHHrank\tDzscore\tDqscore\tDztile\tDqtile\tDrank\t"
            "Cdiff\tCcov\tHHname\tDname\tDrot1\tDrot2\tDrot3\tDtrans\n"
        )

        success = run_step16(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 16 should handle empty features gracefully"


@pytest.mark.unit
class TestStep16HelperFunctions:
    """Unit tests for step 16 helper functions."""

    def test_load_features_valid_file(self, tmp_path):
        """Test loading features from valid file."""
        feature_file = tmp_path / "test.step15_features"
        feature_file.write_text(
            "domID\tdomRange\ttgroup\tecodid\tdomLen\tHelix_num\tStrand_num\t"
            "HHprob\tHHcov\tHHrank\tDzscore\tDqscore\tDztile\tDqtile\tDrank\t"
            "Cdiff\tCcov\tHHname\tDname\tDrot1\tDrot2\tDrot3\tDtrans\n"
            "dom1\t10-50\t1.1.1\te001\t40\t2\t3\t"
            "0.95\t0.80\t1.5\t12.3\t0.75\t0.85\t0.65\t2.1\t"
            "2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
            "dom2\t60-100\t2.2.2\te002\t50\t3\t4\t"
            "0.90\t0.75\t2.0\t10.5\t0.70\t0.80\t0.60\t3.0\t"
            "3.0\t0.65\thit3\thit4\t0.5\t0.5\t0.5\t3.5\n"
        )

        metadata, features = load_features(feature_file)

        # Check metadata
        assert len(metadata) == 2, "Should load 2 metadata rows"
        assert metadata[0][0] == "dom1", "First domain should be dom1"
        assert metadata[0][1] == "10-50", "First range should be 10-50"
        assert metadata[0][2] == "1.1.1", "First tgroup should be 1.1.1"
        assert metadata[0][3] == "e001", "First ecod should be e001"

        # Check features
        assert features.shape == (2, 13), "Should have 2 rows and 13 features"
        assert features.dtype == np.float32, "Features should be float32"

        # Check first row values
        assert features[0, 0] == 40, "First domain length should be 40"
        assert features[0, 1] == 2, "First helix count should be 2"
        assert features[0, 2] == 3, "First strand count should be 3"
        assert abs(features[0, 3] - 0.95) < 0.01, "HH prob should be ~0.95"

    def test_load_features_empty_file(self, tmp_path):
        """Test loading features from file with only header."""
        feature_file = tmp_path / "test.step15_features"
        feature_file.write_text(
            "domID\tdomRange\ttgroup\tecodid\tdomLen\tHelix_num\tStrand_num\t"
            "HHprob\tHHcov\tHHrank\tDzscore\tDqscore\tDztile\tDqtile\tDrank\t"
            "Cdiff\tCcov\tHHname\tDname\tDrot1\tDrot2\tDrot3\tDtrans\n"
        )

        metadata, features = load_features(feature_file)

        assert len(metadata) == 0, "Should have no metadata rows"
        assert features.shape == (0, 13), "Should have 0 rows and 13 columns"

    def test_load_features_malformed_rows(self, tmp_path):
        """Test that malformed rows are skipped."""
        feature_file = tmp_path / "test.step15_features"
        feature_file.write_text(
            "domID\tdomRange\ttgroup\tecodid\tdomLen\tHelix_num\tStrand_num\t"
            "HHprob\tHHcov\tHHrank\tDzscore\tDqscore\tDztile\tDqtile\tDrank\t"
            "Cdiff\tCcov\tHHname\tDname\tDrot1\tDrot2\tDrot3\tDtrans\n"
            "dom1\t10-50\t1.1.1\te001\t40\t2\t3\t"
            "0.95\t0.80\t1.5\t12.3\t0.75\t0.85\t0.65\t2.1\t"
            "2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
            "malformed\trow\twith\ttoo\tfew\tcolumns\n"
            "dom2\t60-100\t2.2.2\te002\t50\t3\t4\t"
            "0.90\t0.75\t2.0\t10.5\t0.70\t0.80\t0.60\t3.0\t"
            "3.0\t0.65\thit3\thit4\t0.5\t0.5\t0.5\t3.5\n"
        )

        metadata, features = load_features(feature_file)

        assert len(metadata) == 2, "Should skip malformed row and load 2 valid rows"
        assert features.shape == (2, 13), "Should have 2 rows and 13 features"

    def test_load_features_invalid_numbers(self, tmp_path):
        """Test that rows with invalid numbers are skipped."""
        feature_file = tmp_path / "test.step15_features"
        feature_file.write_text(
            "domID\tdomRange\ttgroup\tecodid\tdomLen\tHelix_num\tStrand_num\t"
            "HHprob\tHHcov\tHHrank\tDzscore\tDqscore\tDztile\tDqtile\tDrank\t"
            "Cdiff\tCcov\tHHname\tDname\tDrot1\tDrot2\tDrot3\tDtrans\n"
            "dom1\t10-50\t1.1.1\te001\t40\t2\t3\t"
            "0.95\t0.80\t1.5\t12.3\t0.75\t0.85\t0.65\t2.1\t"
            "2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
            "dom2\t60-100\t2.2.2\te002\tinvalid\t3\t4\t"
            "0.90\t0.75\t2.0\t10.5\t0.70\t0.80\t0.60\t3.0\t"
            "3.0\t0.65\thit3\thit4\t0.5\t0.5\t0.5\t3.5\n"
        )

        metadata, features = load_features(feature_file)

        assert len(metadata) == 1, "Should skip row with invalid number"
        assert features.shape == (1, 13), "Should have 1 valid row"

    def test_load_features_feature_extraction(self, tmp_path):
        """Test that correct features are extracted."""
        feature_file = tmp_path / "test.step15_features"
        feature_file.write_text(
            "domID\tdomRange\ttgroup\tecodid\tdomLen\tHelix_num\tStrand_num\t"
            "HHprob\tHHcov\tHHrank\tDzscore\tDqscore\tDztile\tDqtile\tDrank\t"
            "Cdiff\tCcov\tHHname\tDname\tDrot1\tDrot2\tDrot3\tDtrans\n"
            "dom1\t10-50\t1.1.1\te001\t100\t5\t7\t"
            "0.99\t0.95\t1.0\t15.5\t0.85\t0.90\t0.75\t1.5\t"
            "1.2\t0.88\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
        )

        metadata, features = load_features(feature_file)

        # Verify all 13 features are correct
        expected = [
            100,   # domain_length
            5,     # helix_count
            7,     # strand_count
            0.99,  # hh_prob
            0.95,  # hh_coverage
            1.0,   # hh_rank
            15.5,  # dali_zscore
            0.85,  # dali_qscore
            0.90,  # dali_ztile
            0.75,  # dali_qtile
            1.5,   # dali_rank
            1.2,   # consensus_diff
            0.88   # consensus_cov
        ]

        for i, expected_val in enumerate(expected):
            assert abs(features[0, i] - expected_val) < 0.01, \
                f"Feature {i} should be {expected_val}, got {features[0, i]}"
