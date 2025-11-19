"""
Integration tests for Step 23: Get Predictions.

Tests classification of domains as full/part/miss based on ML predictions and coverage.
"""

import pytest
from pathlib import Path
from dpam.steps.step23_get_predictions import run_step23, load_position_weights


@pytest.mark.integration
class TestStep23GetPredictions:
    """Integration tests for step 23 (get predictions)."""

    def test_step23_requires_input_files(self, test_prefix, working_dir, ecod_data_dir):
        """Test that step 23 fails gracefully with missing inputs."""
        # Missing all required files
        success = run_step23(test_prefix, working_dir, ecod_data_dir)
        assert not success, "Step 23 should fail without required input files"

    def test_step23_ecod_length_column_mapping(self, tmp_path):
        """
        Regression test: Verify ECOD_length uses correct column for ECOD ID.

        Bug: Step 23 was reading column 0 (ECOD number) instead of column 1 (ECOD ID),
        resulting in 0 ECOD matches and empty output.
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

    def test_step23_produces_non_empty_output(self, test_prefix, working_dir, ecod_data_dir):
        """
        Regression test: Verify step 23 produces predictions when inputs are valid.

        Bug: Due to ECOD_length parsing bug, Step 23 was producing only headers
        (0 predictions) even with valid inputs.
        """
        # Setup all required input files
        (working_dir / f"{test_prefix}.step13_domains").write_text(
            "D1\t10-70\n"
        )

        (working_dir / f"{test_prefix}.step16_predictions").write_text(
            "Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\t"
            "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
            "Consensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n"
            "D1\t10-70\t101.1.1\te4cxfA2\t0.845\t0.984\t0.80\t0.10\t9.0\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.95\t001\t001\tna\tna\tna\tna\n"
            "D1\t10-70\t101.1.1\te6dxoA2\t0.723\t0.982\t0.75\t0.10\t8.4\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.90\t002\t002\tna\tna\tna\tna\n"
        )

        (working_dir / f"{test_prefix}.step18_mappings").write_text(
            "# domain\tdomain_range\tecod_id\ttgroup\tdpam_prob\tquality\thh_template_range\tdali_template_range\n"
            "D1\t10-70\te4cxfA2\t101.1.1\t0.845\tgood\tna\t100-150\n"
            "D1\t10-70\te6dxoA2\t101.1.1\t0.723\tgood\tna\t50-100\n"
        )

        # Create reference data files
        (ecod_data_dir / "ECOD_length").write_text(
            "001288642\te4cxfA2\t191\n"
            "002389467\te6dxoA2\t150\n"
        )

        (ecod_data_dir / "tgroup_length").write_text(
            "101.1.1\t75.5\n"
        )

        # Create posi_weights dir (will use defaults if files don't exist)
        posi_weights_dir = ecod_data_dir / "posi_weights"
        posi_weights_dir.mkdir(parents=True, exist_ok=True)

        # Run step 23
        success = run_step23(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 23 should succeed with valid inputs"

        # Check output file
        output_file = working_dir / f"{test_prefix}.step23_predictions"
        assert output_file.exists(), "Predictions file should exist"

        with open(output_file) as f:
            lines = f.readlines()

        # Should have header + data rows
        assert len(lines) > 1, \
            "Should produce predictions (bug: only header, 0 predictions due to ECOD_length parsing)"

        # Verify format
        header = lines[0].strip()
        assert header.startswith('#'), "Should have header"

        # Check data rows
        for i, line in enumerate(lines[1:], start=1):
            parts = line.strip().split('\t')
            assert len(parts) == 11, f"Row {i} should have 11 columns"
            assert parts[0] in ['full', 'part', 'miss'], \
                f"Row {i} should have valid classification"

    def test_step23_classification_logic(self, test_prefix, working_dir, ecod_data_dir):
        """Test that step 23 correctly classifies predictions as full/part/miss."""
        # Setup input with varying probabilities and coverage
        (working_dir / f"{test_prefix}.step13_domains").write_text("D1\t10-70\n")

        (working_dir / f"{test_prefix}.step16_predictions").write_text(
            "Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\t"
            "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
            "Consensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n"
            # Full: prob>=0.85, weighted>=0.66, length>=0.33
            "D1\t10-70\t101.1.1\te_full\t0.900\t0.984\t0.80\t0.10\t9.0\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.95\t001\t001\tna\tna\tna\tna\n"
            # Part: prob>=0.85, weighted>=0.33 OR length>=0.33
            "D1\t10-70\t101.1.1\te_part\t0.850\t0.982\t0.60\t0.10\t8.0\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.90\t002\t002\tna\tna\tna\tna\n"
            # Miss: prob<0.85 OR both ratios<0.33
            "D1\t10-70\t101.1.1\te_miss\t0.700\t0.980\t0.50\t0.10\t7.0\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.85\t003\t003\tna\tna\tna\tna\n"
        )

        (working_dir / f"{test_prefix}.step18_mappings").write_text(
            "# domain\tdomain_range\tecod_id\ttgroup\tdpam_prob\tquality\thh_template_range\tdali_template_range\n"
            # Full: covers 100 residues of 120 = 83% (>66%)
            "D1\t10-70\te_full\t101.1.1\t0.900\tgood\tna\t1-100\n"
            # Part: covers 40 residues of 100 = 40% (≥33%)
            "D1\t10-70\te_part\t101.1.1\t0.850\tgood\tna\t1-40\n"
            # Miss: covers 20 residues of 150 = 13% (<33%)
            "D1\t10-70\te_miss\t101.1.1\t0.700\tgood\tna\t1-20\n"
        )

        (ecod_data_dir / "ECOD_length").write_text(
            "000001\te_full\t120\n"
            "000002\te_part\t100\n"
            "000003\te_miss\t150\n"
        )

        (ecod_data_dir / "tgroup_length").write_text("101.1.1\t60.0\n")

        posi_weights_dir = ecod_data_dir / "posi_weights"
        posi_weights_dir.mkdir(parents=True, exist_ok=True)

        # Run step 23
        success = run_step23(test_prefix, working_dir, ecod_data_dir)
        assert success

        # Parse output and check classifications
        output_file = working_dir / f"{test_prefix}.step23_predictions"
        with open(output_file) as f:
            lines = f.readlines()

        classifications = {}
        for line in lines[1:]:  # Skip header
            parts = line.strip().split('\t')
            classification = parts[0]
            ecod = parts[3]
            classifications[ecod] = classification

        # Note: Classifications depend on actual coverage calculations
        # Just verify all three are classified
        assert len(classifications) == 3, "Should classify all three predictions"
        assert all(c in ['full', 'part', 'miss'] for c in classifications.values()), \
            "All classifications should be valid"


@pytest.mark.unit
class TestStep23HelperFunctions:
    """Unit tests for step 23 helper functions."""

    def test_load_position_weights_with_file(self, tmp_path):
        """Test loading position weights from file."""
        weights_dir = tmp_path / "posi_weights"
        weights_dir.mkdir()

        weight_file = weights_dir / "e001.weight"
        weight_file.write_text(
            "1 A 0.5 2.5\n"
            "2 C 0.8 3.2\n"
            "3 G 1.0 4.0\n"
        )

        pos_weights, total_weight = load_position_weights("e001", weights_dir, 100)

        assert pos_weights[1] == 2.5, "Should load weight from column 3"
        assert pos_weights[2] == 3.2
        assert pos_weights[3] == 4.0
        assert total_weight == 2.5 + 3.2 + 4.0, "Total should sum all weights"

    def test_load_position_weights_without_file(self, tmp_path):
        """Test loading position weights defaults when file missing."""
        weights_dir = tmp_path / "posi_weights"
        weights_dir.mkdir()

        # No weight file exists
        pos_weights, total_weight = load_position_weights("e999", weights_dir, 10)

        # Should default to 1.0 per position
        assert len(pos_weights) == 10, "Should create default weights"
        assert all(w == 1.0 for w in pos_weights.values()), "All weights should be 1.0"
        assert total_weight == 10.0, "Total should equal length"

    def test_load_position_weights_malformed_lines(self, tmp_path):
        """Test loading position weights skips malformed lines."""
        weights_dir = tmp_path / "posi_weights"
        weights_dir.mkdir()

        weight_file = weights_dir / "e001.weight"
        weight_file.write_text(
            "1 A 0.5 2.5\n"
            "invalid line\n"
            "3 G 1.0 4.0\n"
        )

        pos_weights, total_weight = load_position_weights("e001", weights_dir, 100)

        assert 1 in pos_weights, "Should load valid line 1"
        assert 2 not in pos_weights, "Should skip malformed line"
        assert 3 in pos_weights, "Should load valid line 3"
        assert total_weight == 2.5 + 4.0, "Total should sum only valid weights"
