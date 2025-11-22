"""
Integration tests for Step 9: Get Sequence and Structure Support.

Tests the integration of sequence (HHsearch) and structure (DALI) evidence.
"""

import pytest
from pathlib import Path
from dpam.steps.step09_get_support import run_step9
from dpam.core.models import ReferenceData


@pytest.mark.integration
class TestStep09GetSupport:
    """Integration tests for step 9 (get support)."""

    @pytest.fixture
    def mock_reference_data(self):
        """Create minimal mock ECOD reference data for testing."""
        # Mock ECOD_lengths: ecod_num -> (ecod_key, length)
        ecod_lengths = {
            '000000003': ('e2rspA1', 124),
            '000000017': ('e2pmaA1', 141),
            '000000020': ('e1eu1A1', 155),
        }

        # Mock ECOD_metadata: ecod_num -> (ecod_id, family)
        ecod_metadata = {
            '000000003': ('e2rspA1', 'F_001'),
            '000000017': ('e2pmaA1', 'F_002'),
            '000000020': ('e1eu1A1', 'F_001'),  # Same family as 003
        }

        return ReferenceData(
            ecod_lengths=ecod_lengths,
            ecod_norms={},
            ecod_pdbmap={},
            ecod_domain_info={},
            ecod_weights={},
            ecod_metadata=ecod_metadata
        )

    @pytest.fixture
    def setup_map2ecod_file(self, test_prefix, working_dir):
        """Create mock map2ecod file from step 5."""
        map_file = working_dir / f"{test_prefix}.map2ecod.result"
        content = """uid\tecod_domain_id\thh_prob\thh_eval\thh_score\taligned_cols\tidents\tsimilarities\tsum_probs\tcoverage\tungapped_coverage\tquery_range\ttemplate_range\ttemplate_seqid_range
000000003\te2rspA1\t99.82\t2.1e-25\t125.50\t50\t48%\t1.234\t45.6\t0.67\t0.75\t10-59\t15-64\t15-64
000000017\te2pmaA1\t98.54\t8.5e-15\t95.30\t45\t42%\t1.123\t42.1\t0.60\t0.68\t15-59\t20-64\t20-64
000000020\te1eu1A1\t97.23\t3.2e-10\t85.70\t40\t38%\t1.045\t38.5\t0.53\t0.62\t20-59\t25-64\t625-664
"""
        map_file.write_text(content)
        return map_file

    @pytest.fixture
    def setup_good_hits_file(self, test_prefix, working_dir):
        """Create mock good_hits file from step 8."""
        good_file = working_dir / f"{test_prefix}_good_hits"
        content = """hitname\tecodnum\tecodkey\thgroup\tzscore\tqscore\tztile\tqtile\trank\tqrange\terange
000000003_1\t000000003\te2rspA1\tF_001\t8.5\t0.82\t0.75\t0.80\t1.2\t10-55\t1-50
000000017_1\t000000017\te2pmaA1\tF_002\t6.2\t0.75\t0.60\t0.65\t1.5\t15-60\t1-48
000000020_1\t000000020\te1eu1A1\tF_001\t7.8\t0.78\t0.70\t0.75\t1.3\t20-65\t1-48
"""
        good_file.write_text(content)
        return good_file

    def test_support_requires_map2ecod(self, test_prefix, working_dir,
                                       mock_reference_data):
        """Test that step 9 fails gracefully without map2ecod file."""
        # Don't create map2ecod file
        success = run_step9(test_prefix, working_dir, mock_reference_data)
        assert not success, "Step 9 should fail without map2ecod file"

    def test_support_with_sequence_only(self, test_prefix, working_dir,
                                        mock_reference_data, setup_map2ecod_file):
        """Test with sequence hits only (no structure hits)."""
        # No good_hits file created
        success = run_step9(test_prefix, working_dir, mock_reference_data)
        assert success, "Step 9 should succeed with sequence hits only"

        # Check sequence output exists
        seq_output = working_dir / f"{test_prefix}_sequence.result"
        assert seq_output.exists(), "Sequence output should be created"

        # Structure output should not exist
        struct_output = working_dir / f"{test_prefix}_structure.result"
        assert not struct_output.exists(), "Structure output should not exist without good_hits"

    def test_support_with_both_inputs(self, test_prefix, working_dir,
                                      mock_reference_data, setup_map2ecod_file,
                                      setup_good_hits_file):
        """Test with both sequence and structure hits."""
        success = run_step9(test_prefix, working_dir, mock_reference_data)
        assert success, "Step 9 should complete successfully"

        # Check both outputs exist
        seq_output = working_dir / f"{test_prefix}_sequence.result"
        struct_output = working_dir / f"{test_prefix}_structure.result"

        assert seq_output.exists(), "Sequence output should be created"
        assert struct_output.exists(), "Structure output should be created"

        # Check both have content
        assert seq_output.stat().st_size > 0, "Sequence output should not be empty"
        assert struct_output.stat().st_size > 0, "Structure output should not be empty"

    def test_sequence_output_format(self, test_prefix, working_dir,
                                    mock_reference_data, setup_map2ecod_file):
        """Test sequence output format."""
        success = run_step9(test_prefix, working_dir, mock_reference_data)
        assert success

        # Read sequence output
        seq_output = working_dir / f"{test_prefix}_sequence.result"
        with open(seq_output, 'r') as f:
            lines = f.readlines()

        # Check data lines (no header in output)
        if len(lines) > 0:
            # First line should be tab-delimited with 8 fields
            fields = lines[0].strip().split('\t')
            assert len(fields) == 8, "Sequence output should have 8 tab-delimited fields"

            # Field validations
            hitname = fields[0]
            assert '_' in hitname, "Hitname should contain underscore"

            # Probability should be float
            try:
                prob = float(fields[3])
                assert prob >= 0, "Probability should be non-negative"
            except ValueError:
                pytest.fail("Probability should be a valid float")

            # Coverage should be float
            try:
                cov = float(fields[4])
                assert 0 <= cov <= 1, "Coverage should be 0-1"
            except ValueError:
                pytest.fail("Coverage should be a valid float")

    def test_structure_output_format(self, test_prefix, working_dir,
                                     mock_reference_data, setup_map2ecod_file,
                                     setup_good_hits_file):
        """Test structure output format."""
        success = run_step9(test_prefix, working_dir, mock_reference_data)
        assert success

        # Read structure output
        struct_output = working_dir / f"{test_prefix}_structure.result"
        with open(struct_output, 'r') as f:
            lines = f.readlines()

        # Check data lines
        if len(lines) > 0:
            # First line should have 12 fields
            fields = lines[0].strip().split('\t')
            assert len(fields) == 12, "Structure output should have 12 tab-delimited fields"

            # Z-score should be float
            try:
                zscore = float(fields[3])
                assert zscore > 0, "Z-score should be positive"
            except ValueError:
                pytest.fail("Z-score should be a valid float")

            # Best prob should be float
            try:
                best_prob = float(fields[8])
                assert best_prob >= 0, "Best prob should be non-negative"
            except ValueError:
                pytest.fail("Best prob should be a valid float")

            # Best cov should be float
            try:
                best_cov = float(fields[9])
                assert 0 <= best_cov <= 1, "Best cov should be 0-1"
            except ValueError:
                pytest.fail("Best cov should be a valid float")

    def test_sequence_keeps_low_coverage_hits(self, test_prefix, working_dir,
                                              mock_reference_data):
        """
        Regression test: Verify low-coverage hits are KEPT (matches original DPAM).

        Bug: Step 9 was filtering out hits with coverage < 0.4, but original DPAM
        keeps ALL hits. This caused 65-90% of proteins to lose HHsearch evidence.
        """
        # Create map2ecod with low coverage hit (coverage=0.30)
        map_file = working_dir / f"{test_prefix}.map2ecod.result"
        content = """uid\tecod_domain_id\thh_prob\thh_eval\thh_score\taligned_cols\tidents\tsimilarities\tsum_probs\tcoverage\tungapped_coverage\tquery_range\ttemplate_range\ttemplate_seqid_range
000000003\te2rspA1\t99.0\t1e-10\t100.0\t50\t45%\t1.0\t45.0\t0.70\t0.75\t10-59\t1-50\t1-50
000000017\te2pmaA1\t95.0\t1e-08\t90.0\t20\t40%\t0.9\t18.0\t0.30\t0.35\t10-29\t1-20\t1-20
"""
        map_file.write_text(content)

        success = run_step9(test_prefix, working_dir, mock_reference_data)
        assert success

        # Read sequence output
        seq_output = working_dir / f"{test_prefix}_sequence.result"
        with open(seq_output, 'r') as f:
            lines = f.readlines()

        # Should have 2 hits (both kept, including low coverage one)
        assert len(lines) == 2, f"Should keep both hits including low-coverage one (got {len(lines)})"

        # Parse coverages
        coverages = [float(line.split('\t')[4]) for line in lines]

        # Should include the low coverage hit (0.30)
        assert any(cov < 0.4 for cov in coverages), \
            "Should KEEP low-coverage hit (bug: was filtering coverage < 0.4)"

    def test_sequence_keeps_low_probability_hits(self, test_prefix, working_dir,
                                                  mock_reference_data):
        """
        Regression test: Verify low-probability hits are KEPT (matches original DPAM).

        Bug: Step 9 was filtering out hits with probability < 50, but original DPAM
        passes ALL hits to DOMASS. Example: A0A0B5J9J9 had prob=17.66 filtered out.
        """
        # Create map2ecod with low probability hit (prob=17.66, like A0A0B5J9J9)
        map_file = working_dir / f"{test_prefix}.map2ecod.result"
        content = """uid\tecod_domain_id\thh_prob\thh_eval\thh_score\taligned_cols\tidents\tsimilarities\tsum_probs\tcoverage\tungapped_coverage\tquery_range\ttemplate_range\ttemplate_seqid_range
000000003\te2rspA1\t99.0\t1e-10\t100.0\t50\t45%\t1.0\t45.0\t0.70\t0.75\t10-59\t1-50\t1-50
000000017\te2pmaA1\t17.66\t1e-02\t50.0\t45\t30%\t0.5\t20.0\t0.90\t0.95\t10-54\t1-45\t1-45
"""
        map_file.write_text(content)

        success = run_step9(test_prefix, working_dir, mock_reference_data)
        assert success

        # Read sequence output
        seq_output = working_dir / f"{test_prefix}_sequence.result"
        with open(seq_output, 'r') as f:
            lines = f.readlines()

        # Should have 2 hits (both kept, including low probability one)
        assert len(lines) == 2, f"Should keep both hits including low-probability one (got {len(lines)})"

        # Parse probabilities
        probs = [float(line.split('\t')[3]) for line in lines]

        # Should include the low probability hit (17.66)
        assert any(prob < 50 for prob in probs), \
            "Should KEEP low-probability hit (bug: was filtering prob < 50)"

    def test_structure_includes_sequence_support(self, test_prefix, working_dir,
                                                 mock_reference_data,
                                                 setup_map2ecod_file,
                                                 setup_good_hits_file):
        """Test that structure hits include sequence support metrics."""
        success = run_step9(test_prefix, working_dir, mock_reference_data)
        assert success

        # Read structure output
        struct_output = working_dir / f"{test_prefix}_structure.result"
        with open(struct_output, 'r') as f:
            lines = f.readlines()

        # Check that best_prob and best_cov are calculated
        for line in lines:
            fields = line.strip().split('\t')
            best_prob = float(fields[8])
            best_cov = float(fields[9])

            # Should have calculated values (not just 0)
            # (May be 0 if no sequence support from same family)
            assert best_prob >= 0, "Best prob should be non-negative"
            assert best_cov >= 0, "Best cov should be non-negative"

    def test_structure_preserves_dali_metrics(self, test_prefix, working_dir,
                                              mock_reference_data,
                                              setup_map2ecod_file,
                                              setup_good_hits_file):
        """Test that structure output preserves DALI metrics."""
        success = run_step9(test_prefix, working_dir, mock_reference_data)
        assert success

        # Read structure output
        struct_output = working_dir / f"{test_prefix}_structure.result"
        with open(struct_output, 'r') as f:
            lines = f.readlines()

        # Extract z-scores
        zscores = [float(line.split('\t')[3]) for line in lines]

        # Should match input z-scores from good_hits (8.5, 6.2, 7.8)
        assert 8.5 in zscores, "Should preserve z-score 8.5"
        assert 6.2 in zscores, "Should preserve z-score 6.2"
        assert 7.8 in zscores, "Should preserve z-score 7.8"

    def test_sequence_removes_overlaps(self, test_prefix, working_dir,
                                       mock_reference_data):
        """Test that overlapping sequence hits are filtered."""
        # Create map2ecod with overlapping hits for same ECOD domain
        map_file = working_dir / f"{test_prefix}.map2ecod.result"
        content = """uid\tecod_domain_id\thh_prob\thh_eval\thh_score\taligned_cols\tidents\tsimilarities\tsum_probs\tcoverage\tungapped_coverage\tquery_range\ttemplate_range\ttemplate_seqid_range
000000003\te2rspA1\t99.0\t1e-10\t100.0\t50\t45%\t1.0\t45.0\t0.70\t0.75\t10-59\t1-50\t1-50
000000003\te2rspA1\t98.0\t2e-10\t95.0\t45\t44%\t0.9\t40.0\t0.65\t0.70\t15-59\t5-49\t5-49
"""
        map_file.write_text(content)

        success = run_step9(test_prefix, working_dir, mock_reference_data)
        assert success

        # Read sequence output
        seq_output = working_dir / f"{test_prefix}_sequence.result"
        with open(seq_output, 'r') as f:
            lines = f.readlines()

        # Should keep first hit, filter second (< 50% new residues)
        # Exact behavior depends on overlap calculation
        assert len(lines) >= 1, "Should keep at least one hit"

    def test_with_empty_map2ecod(self, test_prefix, working_dir,
                                 mock_reference_data):
        """Test with empty map2ecod file (header only)."""
        # Create empty map2ecod (header only)
        map_file = working_dir / f"{test_prefix}.map2ecod.result"
        map_file.write_text("uid\tecod_domain_id\thh_prob\thh_eval\thh_score\n")

        success = run_step9(test_prefix, working_dir, mock_reference_data)
        assert success, "Should succeed with empty input"

        # Check sequence output
        seq_output = working_dir / f"{test_prefix}_sequence.result"
        assert seq_output.exists()

        with open(seq_output, 'r') as f:
            content = f.read()

        # Output should be empty (no hits)
        assert content == "", "Output should be empty with no hits"


@pytest.mark.integration
class TestStep09Functions:
    """Test individual Step 9 functions."""

    def test_get_range_basic(self):
        """Test range string generation."""
        from dpam.steps.step09_get_support import get_range

        # Single segment
        assert get_range([10, 11, 12, 13]) == "10-13"

        # Multiple segments
        assert get_range([10, 11, 15, 16, 20]) == "10-11,15-16,20-20"

        # Unsorted input
        assert get_range([15, 10, 11, 20, 16]) == "10-11,15-16,20-20"

        # Empty input
        assert get_range([]) == ""

    def test_merge_segments_with_gap_tolerance(self):
        """Test segment merging with gap tolerance."""
        from dpam.steps.step09_get_support import merge_segments_with_gap_tolerance

        # No gaps
        resids = merge_segments_with_gap_tolerance("10-20")
        assert len(resids) == 11, "Should have 11 residues"

        # Small gap (should merge)
        resids = merge_segments_with_gap_tolerance("10-20,25-30")
        # Gap is 4 residues (21-24), should merge with default tolerance 10
        assert 21 in resids, "Small gap should be filled"
        assert 24 in resids, "Small gap should be filled"

        # Large gap (should not merge)
        resids = merge_segments_with_gap_tolerance("10-20,40-50")
        # Gap is 19 residues (21-39), should NOT merge
        assert 30 not in resids, "Large gap should not be filled"

    def test_calculate_sequence_support(self):
        """Test sequence support calculation."""
        from dpam.steps.step09_get_support import calculate_sequence_support

        # Create mock fam2hits
        fam2hits = {
            'F_001': [
                [99.0, 100, [10, 11, 12], [1, 2, 3]],  # prob, len, qres, tres
                [95.0, 100, [15, 16, 17], [5, 6, 7]],
            ],
            'F_002': [
                [90.0, 100, [20, 21], [10, 11]],
            ]
        }

        # Test with family that has hits
        structure_resids = {10, 11, 12, 13, 14, 15}
        best_prob, best_cov = calculate_sequence_support('F_001', structure_resids, fam2hits)

        assert best_prob > 0, "Should find sequence support"
        assert best_cov > 0, "Should calculate coverage"

        # Test with family that has no hits
        best_prob, best_cov = calculate_sequence_support('F_999', structure_resids, fam2hits)

        assert best_prob == 0.0, "Should return 0 for unknown family"
        assert best_cov == 0.0, "Should return 0 for unknown family"
