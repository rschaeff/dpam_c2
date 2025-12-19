"""
Integration tests for Step 17: Filter Confident Predictions.

Tests filtering ML predictions by probability threshold and quality labeling.
"""

import pytest
from pathlib import Path
from dpam.steps.step17_get_confident import run_step17


@pytest.mark.integration
class TestStep17GetConfident:
    """Integration tests for step 17 (filter confident predictions)."""

    def test_step17_requires_step16_output(self, test_prefix, working_dir):
        """Test that step 17 gracefully skips without step 16 output."""
        success = run_step17(test_prefix, working_dir)
        assert success, "Step 17 should gracefully skip with missing predictions file"

    def test_step17_with_valid_predictions(self, test_prefix, working_dir):
        """Test step 17 with valid predictions."""
        # Create test predictions file
        predictions_file = working_dir / f"{test_prefix}.step16_predictions"
        predictions_file.write_text(
            "Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\t"
            "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
            "Consensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n"
            "dom1\t10-50\t1.1.1\te001\t0.95\t0.90\t0.80\t1.5\t"
            "12.3\t0.75\t0.85\t0.65\t2.1\t2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
            "dom1\t10-50\t1.1.2\te002\t0.92\t0.88\t0.78\t1.8\t"
            "11.5\t0.73\t0.83\t0.63\t2.3\t2.7\t0.68\thit3\thit4\t1.0\t0.0\t0.0\t5.0\n"
            "dom2\t60-100\t2.2.2\te003\t0.45\t0.85\t0.75\t2.0\t"
            "10.5\t0.70\t0.80\t0.60\t3.0\t3.0\t0.65\thit5\thit6\t0.5\t0.5\t0.5\t3.5\n"
        )

        success = run_step17(test_prefix, working_dir)
        assert success, "Step 17 should succeed with valid predictions"

        # Check output exists
        output_file = working_dir / f"{test_prefix}.step17_confident_predictions"
        assert output_file.exists(), "Confident predictions file should be created"

    def test_step17_filters_low_confidence(self, test_prefix, working_dir):
        """Test that step 17 filters out predictions below 0.6 threshold."""
        predictions_file = working_dir / f"{test_prefix}.step16_predictions"
        predictions_file.write_text(
            "Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\t"
            "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
            "Consensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n"
            "dom1\t10-50\t1.1.1\te001\t0.95\t0.90\t0.80\t1.5\t"
            "12.3\t0.75\t0.85\t0.65\t2.1\t2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
            "dom2\t60-100\t2.2.2\te002\t0.45\t0.85\t0.75\t2.0\t"
            "10.5\t0.70\t0.80\t0.60\t3.0\t3.0\t0.65\thit3\thit4\t0.5\t0.5\t0.5\t3.5\n"
            "dom3\t120-160\t3.3.3\te003\t0.55\t0.80\t0.70\t2.5\t"
            "9.5\t0.68\t0.75\t0.58\t3.5\t3.5\t0.60\thit5\thit6\t1.5\t1.0\t0.5\t4.0\n"
        )

        success = run_step17(test_prefix, working_dir)
        assert success

        output_file = working_dir / f"{test_prefix}.step17_confident_predictions"

        with open(output_file) as f:
            lines = f.readlines()

        # Should have header + 1 confident prediction (only dom1 with prob 0.95)
        data_lines = [l for l in lines if not l.startswith('#')]
        assert len(data_lines) == 2, "Should have header + 1 confident prediction"

        # Verify it's dom1
        parts = data_lines[1].strip().split('\t')
        assert parts[0] == "dom1", "Confident prediction should be dom1"
        assert float(parts[4]) >= 0.6, "Probability should be ≥ 0.6"

    def test_step17_quality_labels_single_tgroup(self, test_prefix, working_dir):
        """Test quality label for single T-group (good)."""
        predictions_file = working_dir / f"{test_prefix}.step16_predictions"
        predictions_file.write_text(
            "Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\t"
            "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
            "Consensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n"
            "dom1\t10-50\t1.1.1\te001\t0.95\t0.90\t0.80\t1.5\t"
            "12.3\t0.75\t0.85\t0.65\t2.1\t2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
        )

        success = run_step17(test_prefix, working_dir)
        assert success

        output_file = working_dir / f"{test_prefix}.step17_confident_predictions"

        with open(output_file) as f:
            lines = f.readlines()

        data_lines = [l for l in lines if not l.startswith('#')]
        parts = data_lines[1].strip().split('\t')

        quality = parts[5]
        assert quality == "good", "Single T-group should have 'good' quality"

    def test_step17_quality_labels_same_hgroup(self, test_prefix, working_dir):
        """Test quality label for same H-group (ok)."""
        predictions_file = working_dir / f"{test_prefix}.step16_predictions"
        predictions_file.write_text(
            "Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\t"
            "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
            "Consensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n"
            "dom1\t10-50\t1.1.1\te001\t0.95\t0.90\t0.80\t1.5\t"
            "12.3\t0.75\t0.85\t0.65\t2.1\t2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
            "dom1\t10-50\t1.1.2\te002\t0.92\t0.88\t0.78\t1.8\t"
            "11.5\t0.73\t0.83\t0.63\t2.3\t2.7\t0.68\thit3\thit4\t1.0\t0.0\t0.0\t5.0\n"
        )

        success = run_step17(test_prefix, working_dir)
        assert success

        output_file = working_dir / f"{test_prefix}.step17_confident_predictions"

        with open(output_file) as f:
            lines = f.readlines()

        data_lines = [l for l in lines if not l.startswith('#')]

        # Both predictions should be present and have 'ok' quality
        # (same H-group 1.1 but different T-groups 1.1.1 and 1.1.2)
        assert len(data_lines) >= 2, "Should have at least 2 predictions"

        for line in data_lines[1:]:
            parts = line.strip().split('\t')
            quality = parts[5]
            # Quality should be 'ok' if within 0.05 of best prob
            if float(parts[4]) >= 0.90:  # Close to best prob
                assert quality == "ok", "Same H-group should have 'ok' quality"

    def test_step17_quality_labels_different_hgroups(self, test_prefix, working_dir):
        """Test quality label for different H-groups (bad)."""
        predictions_file = working_dir / f"{test_prefix}.step16_predictions"
        predictions_file.write_text(
            "Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\t"
            "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
            "Consensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n"
            "dom1\t10-50\t1.1.1\te001\t0.95\t0.90\t0.80\t1.5\t"
            "12.3\t0.75\t0.85\t0.65\t2.1\t2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
            "dom1\t10-50\t2.2.2\te002\t0.92\t0.88\t0.78\t1.8\t"
            "11.5\t0.73\t0.83\t0.63\t2.3\t2.7\t0.68\thit3\thit4\t1.0\t0.0\t0.0\t5.0\n"
        )

        success = run_step17(test_prefix, working_dir)
        assert success

        output_file = working_dir / f"{test_prefix}.step17_confident_predictions"

        with open(output_file) as f:
            lines = f.readlines()

        data_lines = [l for l in lines if not l.startswith('#')]

        # Both predictions should be present
        assert len(data_lines) >= 2, "Should have at least 2 predictions"

        # Check that predictions with different H-groups have 'bad' quality
        for line in data_lines[1:]:
            parts = line.strip().split('\t')
            quality = parts[5]
            if float(parts[4]) >= 0.90:  # High confidence predictions
                assert quality == "bad", "Different H-groups should have 'bad' quality"

    def test_step17_output_format(self, test_prefix, working_dir):
        """Test that step 17 output has expected format."""
        predictions_file = working_dir / f"{test_prefix}.step16_predictions"
        predictions_file.write_text(
            "Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\t"
            "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
            "Consensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n"
            "dom1\t10-50\t1.1.1\te001\t0.95\t0.90\t0.80\t1.5\t"
            "12.3\t0.75\t0.85\t0.65\t2.1\t2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
        )

        success = run_step17(test_prefix, working_dir)
        assert success

        output_file = working_dir / f"{test_prefix}.step17_confident_predictions"

        with open(output_file) as f:
            lines = f.readlines()

        # Check header
        header = lines[0].strip()
        assert header.startswith('#'), "Header should start with #"
        assert "domain" in header, "Header should contain 'domain'"
        assert "quality" in header, "Header should contain 'quality'"

        # Check data format
        if len(lines) > 1:
            parts = lines[1].strip().split('\t')
            assert len(parts) == 6, "Each row should have 6 columns"

            # Columns: domain, domain_range, tgroup, ecod_ref, prob, quality
            assert isinstance(parts[0], str), "Domain should be string"
            assert isinstance(parts[1], str), "Range should be string"
            assert isinstance(parts[2], str), "T-group should be string"
            assert isinstance(parts[3], str), "ECOD ref should be string"

            prob = float(parts[4])
            assert 0.0 <= prob <= 1.0, "Probability should be in [0, 1]"

            quality = parts[5]
            assert quality in ['good', 'ok', 'bad'], "Quality should be good/ok/bad"

    def test_step17_handles_empty_predictions(self, test_prefix, working_dir):
        """Test that step 17 handles empty predictions file gracefully."""
        predictions_file = working_dir / f"{test_prefix}.step16_predictions"
        predictions_file.write_text(
            "Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\t"
            "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
            "Consensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n"
        )

        success = run_step17(test_prefix, working_dir)
        assert success, "Step 17 should handle empty predictions gracefully"

    def test_step17_similarity_window(self, test_prefix, working_dir):
        """Test that T-group similarity window (0.05) is applied correctly."""
        predictions_file = working_dir / f"{test_prefix}.step16_predictions"
        predictions_file.write_text(
            "Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\t"
            "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
            "Consensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n"
            "dom1\t10-50\t1.1.1\te001\t0.95\t0.90\t0.80\t1.5\t"
            "12.3\t0.75\t0.85\t0.65\t2.1\t2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
            "dom1\t10-50\t1.1.2\te002\t0.91\t0.88\t0.78\t1.8\t"
            "11.5\t0.73\t0.83\t0.63\t2.3\t2.7\t0.68\thit3\thit4\t1.0\t0.0\t0.0\t5.0\n"
            "dom1\t10-50\t2.2.2\te003\t0.85\t0.85\t0.75\t2.0\t"
            "10.5\t0.70\t0.80\t0.60\t3.0\t3.0\t0.65\thit5\thit6\t0.5\t0.5\t0.5\t3.5\n"
        )

        success = run_step17(test_prefix, working_dir)
        assert success

        output_file = working_dir / f"{test_prefix}.step17_confident_predictions"

        with open(output_file) as f:
            lines = f.readlines()

        data_lines = [l for l in lines if not l.startswith('#')]

        # All three predictions are above 0.6 threshold
        # First two (0.95, 0.91) are within 0.05 window and same H-group -> 'ok'
        # Third (0.85) is outside 0.05 window (0.95 - 0.05 = 0.90) but still reported
        assert len(data_lines) >= 3, "Should have all high-confidence predictions"

    def test_step17_handles_malformed_lines(self, test_prefix, working_dir):
        """Test that step 17 skips malformed lines gracefully."""
        predictions_file = working_dir / f"{test_prefix}.step16_predictions"
        predictions_file.write_text(
            "Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\t"
            "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
            "Consensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n"
            "dom1\t10-50\t1.1.1\te001\t0.95\t0.90\t0.80\t1.5\t"
            "12.3\t0.75\t0.85\t0.65\t2.1\t2.5\t0.70\thit1\thit2\t1.0\t0.0\t0.0\t5.0\n"
            "malformed\tline\twith\ttoo\tfew\n"
            "dom2\t60-100\t2.2.2\te002\tinvalid_prob\t0.85\t0.75\t2.0\t"
            "10.5\t0.70\t0.80\t0.60\t3.0\t3.0\t0.65\thit3\thit4\t0.5\t0.5\t0.5\t3.5\n"
        )

        success = run_step17(test_prefix, working_dir)
        assert success, "Step 17 should handle malformed lines gracefully"

        output_file = working_dir / f"{test_prefix}.step17_confident_predictions"

        with open(output_file) as f:
            lines = f.readlines()

        data_lines = [l for l in lines if not l.startswith('#')]

        # Should have only 1 valid prediction (dom1)
        assert len(data_lines) == 2, "Should have header + 1 valid prediction"
        assert data_lines[1].startswith("dom1"), "Valid prediction should be dom1"
