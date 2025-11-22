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

    def test_step23_single_assignment_per_domain(self, test_prefix, working_dir, ecod_data_dir):
        """
        Regression test: Verify Step 23 outputs exactly ONE ECOD assignment per domain.

        Bug: Step 23 was outputting ALL ECOD predictions that passed thresholds
        instead of selecting the SINGLE BEST assignment per domain. This resulted
        in domains receiving 10-30 different ECOD family assignments.

        Expected behavior:
        - Sort ECODs by probability (descending)
        - Select best "full" match if available
        - Else select best "part" match
        - Else output top ECOD as "miss"
        - Output exactly ONE line per domain
        """
        # Setup domain with multiple ECOD predictions
        (working_dir / f"{test_prefix}.step13_domains").write_text(
            "D1\t10-70\n"
            "D2\t80-150\n"
            "D3\t160-250\n"
        )

        # Create predictions: D1 has 5 different ECODs, D2 has 3, D3 has 1
        (working_dir / f"{test_prefix}.step16_predictions").write_text(
            "Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\t"
            "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
            "Consensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n"
            # D1: 5 different ECODs (should select e1_best_full with highest prob)
            "D1\t10-70\t101.1.1\te1_best_full\t0.950\t0.984\t0.80\t0.10\t9.0\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.95\t001\t001\tna\tna\tna\tna\n"
            "D1\t10-70\t101.1.1\te1_other_full\t0.900\t0.982\t0.75\t0.10\t8.5\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.93\t002\t002\tna\tna\tna\tna\n"
            "D1\t10-70\t101.1.1\te1_part_1\t0.880\t0.980\t0.60\t0.10\t8.0\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.90\t003\t003\tna\tna\tna\tna\n"
            "D1\t10-70\t101.1.1\te1_part_2\t0.870\t0.978\t0.55\t0.10\t7.5\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.88\t004\t004\tna\tna\tna\tna\n"
            "D1\t10-70\t101.1.1\te1_miss\t0.750\t0.975\t0.40\t0.10\t7.0\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.85\t005\t005\tna\tna\tna\tna\n"
            # D2: 3 different ECODs (no full match, should select e2_best_part)
            "D2\t80-150\t102.1.1\te2_best_part\t0.920\t0.983\t0.50\t0.10\t8.8\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.92\t006\t006\tna\tna\tna\tna\n"
            "D2\t80-150\t102.1.1\te2_other_part\t0.880\t0.980\t0.45\t0.10\t8.2\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.89\t007\t007\tna\tna\tna\tna\n"
            "D2\t80-150\t102.1.1\te2_miss\t0.800\t0.978\t0.30\t0.10\t7.8\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.86\t008\t008\tna\tna\tna\tna\n"
            # D3: 1 ECOD (should output e3_only)
            "D3\t160-250\t103.1.1\te3_only\t0.890\t0.985\t0.70\t0.10\t9.2\t-1.0\t-1.0\t-1.0\t1.0\t-1.0\t0.94\t009\t009\tna\tna\tna\tna\n"
        )

        # Create mappings with varying coverage
        (working_dir / f"{test_prefix}.step18_mappings").write_text(
            "# domain\tdomain_range\tecod_id\ttgroup\tdpam_prob\tquality\thh_template_range\tdali_template_range\n"
            # D1 ECODs: e1_best_full and e1_other_full qualify as "full"
            "D1\t10-70\te1_best_full\t101.1.1\t0.950\tgood\tna\t1-100\n"  # 100/120 = 83% coverage (full)
            "D1\t10-70\te1_other_full\t101.1.1\t0.900\tgood\tna\t1-85\n"   # 85/120 = 71% coverage (full)
            "D1\t10-70\te1_part_1\t101.1.1\t0.880\tgood\tna\t1-50\n"       # 50/120 = 42% coverage (part)
            "D1\t10-70\te1_part_2\t101.1.1\t0.870\tgood\tna\t1-45\n"       # 45/120 = 38% coverage (part)
            "D1\t10-70\te1_miss\t101.1.1\t0.750\tgood\tna\t1-20\n"         # 20/120 = 17% coverage (miss)
            # D2 ECODs: only "part" matches (coverage < 66%)
            "D2\t80-150\te2_best_part\t102.1.1\t0.920\tgood\tna\t1-55\n"   # 55/130 = 42% coverage (part)
            "D2\t80-150\te2_other_part\t102.1.1\t0.880\tgood\tna\t1-50\n"  # 50/130 = 38% coverage (part)
            "D2\t80-150\te2_miss\t102.1.1\t0.800\tgood\tna\t1-25\n"        # 25/130 = 19% coverage (miss)
            # D3 ECODs: single full match
            "D3\t160-250\te3_only\t103.1.1\t0.890\tgood\tna\t1-90\n"       # 90/125 = 72% coverage (full)
        )

        # Create ECOD lengths
        (ecod_data_dir / "ECOD_length").write_text(
            "001\te1_best_full\t120\n"
            "002\te1_other_full\t120\n"
            "003\te1_part_1\t120\n"
            "004\te1_part_2\t120\n"
            "005\te1_miss\t120\n"
            "006\te2_best_part\t130\n"
            "007\te2_other_part\t130\n"
            "008\te2_miss\t130\n"
            "009\te3_only\t125\n"
        )

        (ecod_data_dir / "tgroup_length").write_text(
            "101.1.1\t60.0\n"
            "102.1.1\t70.0\n"
            "103.1.1\t90.0\n"
        )

        posi_weights_dir = ecod_data_dir / "posi_weights"
        posi_weights_dir.mkdir(parents=True, exist_ok=True)

        # Run step 23
        success = run_step23(test_prefix, working_dir, ecod_data_dir)
        assert success, "Step 23 should succeed"

        # Parse output
        output_file = working_dir / f"{test_prefix}.step23_predictions"
        with open(output_file) as f:
            lines = f.readlines()

        # Count assignments per domain
        domain_assignments = {}
        for line in lines[1:]:  # Skip header
            parts = line.strip().split('\t')
            domain = parts[1]
            ecod = parts[3]

            if domain not in domain_assignments:
                domain_assignments[domain] = []
            domain_assignments[domain].append((ecod, parts[0]))  # (ecod, classification)

        # CRITICAL: Each domain should have exactly ONE assignment
        assert len(domain_assignments['D1']) == 1, \
            f"D1 should have 1 assignment, got {len(domain_assignments['D1'])} (bug: outputs all ECODs)"
        assert len(domain_assignments['D2']) == 1, \
            f"D2 should have 1 assignment, got {len(domain_assignments['D2'])}"
        assert len(domain_assignments['D3']) == 1, \
            f"D3 should have 1 assignment, got {len(domain_assignments['D3'])}"

        # Verify correct ECOD selected (best "full" > best "part" > best "miss")
        d1_ecod, d1_class = domain_assignments['D1'][0]
        assert d1_ecod == 'e1_best_full', \
            f"D1 should select e1_best_full (highest prob full match), got {d1_ecod}"
        assert d1_class == 'full', f"D1 should be classified as 'full', got {d1_class}"

        d2_ecod, d2_class = domain_assignments['D2'][0]
        assert d2_ecod == 'e2_best_part', \
            f"D2 should select e2_best_part (no full match, highest prob part), got {d2_ecod}"
        assert d2_class == 'part', f"D2 should be classified as 'part', got {d2_class}"

        d3_ecod, d3_class = domain_assignments['D3'][0]
        assert d3_ecod == 'e3_only', f"D3 should select e3_only, got {d3_ecod}"
        assert d3_class == 'full', f"D3 should be classified as 'full', got {d3_class}"

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

        # Parse output and check that only ONE assignment is made
        output_file = working_dir / f"{test_prefix}.step23_predictions"
        with open(output_file) as f:
            lines = f.readlines()

        # Should have exactly ONE assignment (D1 with best "full" match)
        assert len(lines) == 2, f"Should have header + 1 assignment, got {len(lines)}"

        # Verify it selected the best "full" match
        parts = lines[1].strip().split('\t')
        assert parts[0] == 'full', "Should select 'full' classification"
        assert parts[3] == 'e_full', "Should select e_full (highest prob full match)"


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
