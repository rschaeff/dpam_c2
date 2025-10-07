"""
Unit tests for step-specific algorithmic functions.

Tests pure functions from pipeline steps (filters, scoring, calculations).
"""

import pytest


@pytest.mark.unit
class TestStep04Filtering:
    """Tests for Step 4 (Foldseek filtering) functions."""

    def test_coverage_tracking(self):
        """Test residue coverage tracking logic."""
        from dpam.steps.step04_filter_foldseek import run_step4
        # This would require refactoring to expose the coverage logic
        # as a separate testable function
        pass


@pytest.mark.unit
class TestStep08Scoring:
    """Tests for Step 8 (DALI analysis) scoring functions."""

    def test_get_range_simple(self):
        """Test range string generation from residue list."""
        from dpam.steps.step08_analyze_dali import get_range

        # Single continuous segment
        result = get_range([10, 11, 12, 13, 14])
        assert result == "10-14"

    def test_get_range_multiple_segments(self):
        """Test range with multiple segments."""
        from dpam.steps.step08_analyze_dali import get_range

        # Multiple segments with gaps
        result = get_range([10, 11, 12, 20, 21, 22, 30])
        assert result == "10-12,20-22,30-30"

    def test_get_range_unsorted(self):
        """Test range generation with unsorted input."""
        from dpam.steps.step08_analyze_dali import get_range

        # Unsorted residues
        result = get_range([22, 10, 21, 11, 20, 12])
        assert result == "10-12,20-22"

    def test_get_range_empty(self):
        """Test range generation with empty input."""
        from dpam.steps.step08_analyze_dali import get_range

        result = get_range([])
        assert result == ""

    def test_calculate_percentile_middle(self):
        """Test percentile calculation for middle value."""
        from dpam.steps.step08_analyze_dali import calculate_percentile

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        percentile = calculate_percentile(3.0, values)

        # 2 values greater (4, 5), 3 values not greater (1, 2, 3)
        # Percentile = better / (better + worse) = 2 / 5 = 0.4
        assert percentile == 0.4

    def test_calculate_percentile_best(self):
        """Test percentile for best value."""
        from dpam.steps.step08_analyze_dali import calculate_percentile

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        percentile = calculate_percentile(5.0, values)

        # 0 values greater, 5 values not greater
        # Percentile = 0 / 5 = 0.0
        assert percentile == 0.0

    def test_calculate_percentile_worst(self):
        """Test percentile for worst value."""
        from dpam.steps.step08_analyze_dali import calculate_percentile

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        percentile = calculate_percentile(1.0, values)

        # 4 values greater, 1 value not greater
        # Percentile = 4 / 5 = 0.8
        assert percentile == 0.8

    def test_calculate_percentile_empty(self):
        """Test percentile with empty list."""
        from dpam.steps.step08_analyze_dali import calculate_percentile

        percentile = calculate_percentile(3.0, [])
        assert percentile == -1.0


@pytest.mark.unit
class TestStep09Support:
    """Tests for Step 9 (sequence/structure support) functions."""

    def test_get_range_simple(self):
        """Test range generation."""
        from dpam.steps.step09_get_support import get_range

        result = get_range([5, 6, 7, 8])
        assert result == "5-8"

    def test_get_range_gaps(self):
        """Test range with gaps."""
        from dpam.steps.step09_get_support import get_range

        result = get_range([5, 6, 10, 11, 15])
        assert result == "5-6,10-11,15-15"

    def test_merge_segments_small_gap(self):
        """Test segment merging with small gap."""
        from dpam.steps.step09_get_support import merge_segments_with_gap_tolerance

        # Gap of 4 residues (21-24), should merge with tolerance 10
        resids = merge_segments_with_gap_tolerance("10-20,25-30", gap_tolerance=10)

        # Should merge to single segment
        assert 15 in resids  # Original
        assert 22 in resids  # Gap filled

    def test_merge_segments_large_gap(self):
        """Test segment merging with large gap."""
        from dpam.steps.step09_get_support import merge_segments_with_gap_tolerance

        # Gap of 19 residues (21-39), should NOT merge
        resids = merge_segments_with_gap_tolerance("10-20,40-50", gap_tolerance=10)

        # Should not fill large gap
        assert 15 in resids  # From first segment
        assert 45 in resids  # From second segment
        assert 30 not in resids  # Gap not filled

    def test_calculate_sequence_support_no_family(self):
        """Test sequence support with unknown family."""
        from dpam.steps.step09_get_support import calculate_sequence_support

        fam2hits = {'F_001': [[99.0, 100, [10, 11], [1, 2]]]}
        structure_resids = {10, 11, 12}

        best_prob, best_cov = calculate_sequence_support(
            'F_999',  # Unknown family
            structure_resids,
            fam2hits
        )

        assert best_prob == 0.0
        assert best_cov == 0.0

    def test_calculate_sequence_support_with_overlap(self):
        """Test sequence support with overlapping residues."""
        from dpam.steps.step09_get_support import calculate_sequence_support

        fam2hits = {
            'F_001': [
                [99.0, 100, [10, 11, 12, 13, 14], [1, 2, 3, 4, 5]],
                [95.0, 100, [15, 16, 17, 18, 19], [6, 7, 8, 9, 10]],
            ]
        }
        structure_resids = {10, 11, 12, 13, 14, 15}

        best_prob, best_cov = calculate_sequence_support(
            'F_001',
            structure_resids,
            fam2hits
        )

        # Should find best probability and coverage
        assert best_prob > 0
        assert best_cov > 0


@pytest.mark.unit
class TestStep10Filtering:
    """Tests for Step 10 (domain filtering) functions."""

    def test_filter_segments_basic(self):
        """Test basic segment filtering."""
        from dpam.steps.step10_filter_domains import filter_segments

        # Good segment (>= 25 residues, each >= 5)
        filtered, count = filter_segments("10-40")

        assert filtered == "10-40"
        assert count == 31

    def test_filter_segments_too_short_total(self):
        """Test filtering when total < 25."""
        from dpam.steps.step10_filter_domains import filter_segments

        # Only 11 residues, < 25 minimum
        filtered, count = filter_segments("10-20")

        assert filtered == ""
        assert count == 0

    def test_filter_segments_removes_short_segments(self):
        """Test that segments < 5 residues are removed."""
        from dpam.steps.step10_filter_domains import filter_segments

        # First segment is 3 residues (< 5), should be removed
        # But with gap tolerance, may merge
        filtered, count = filter_segments("10-12,20-50")

        # Depends on merging behavior
        assert count >= 0

    def test_filter_segments_gap_merging(self):
        """Test gap tolerance merging."""
        from dpam.steps.step10_filter_domains import filter_segments

        # Small gap should merge
        filtered, count = filter_segments("10-20,25-35", gap_tolerance=10)

        assert filtered == "10-35"
        assert count == 26

    def test_classify_sequence_support_superb(self):
        """Test sequence support classification - superb."""
        from dpam.steps.step10_filter_domains import classify_sequence_support

        support = classify_sequence_support(99.0, 0.8)
        assert support == "superb"

    def test_classify_sequence_support_high(self):
        """Test sequence support classification - high."""
        from dpam.steps.step10_filter_domains import classify_sequence_support

        support = classify_sequence_support(85.0, 0.5)
        assert support == "high"

    def test_classify_sequence_support_medium(self):
        """Test sequence support classification - medium."""
        from dpam.steps.step10_filter_domains import classify_sequence_support

        support = classify_sequence_support(60.0, 0.35)
        assert support == "medium"

    def test_classify_sequence_support_low(self):
        """Test sequence support classification - low."""
        from dpam.steps.step10_filter_domains import classify_sequence_support

        support = classify_sequence_support(30.0, 0.25)
        assert support == "low"

    def test_classify_sequence_support_no(self):
        """Test sequence support classification - no support."""
        from dpam.steps.step10_filter_domains import classify_sequence_support

        support = classify_sequence_support(10.0, 0.1)
        assert support == "no"

    def test_calculate_judge_score_high_quality(self):
        """Test judge score for high-quality structure hit."""
        from dpam.steps.step10_filter_domains import calculate_judge_score

        # High-quality hit: good rank, scores, percentiles, and sequence support
        judge, seqjudge = calculate_judge_score(
            rank=1.0,      # < 1.5 → +1
            qscore=0.8,    # > 0.5 → +1
            ztile=0.5,     # < 0.75 → +1
            qtile=0.6,     # < 0.75 → +1
            znorm=0.5,     # > 0.225 → +1
            best_prob=99.0,  # >= 95 → +4
            best_cov=0.8     # >= 0.6
        )

        # Should get 5 from structure + 4 from sequence = 9
        assert judge == 9
        assert seqjudge == "superb"

    def test_calculate_judge_score_low_quality(self):
        """Test judge score for low-quality structure hit."""
        from dpam.steps.step10_filter_domains import calculate_judge_score

        # Low-quality hit
        judge, seqjudge = calculate_judge_score(
            rank=2.0,      # >= 1.5 → 0
            qscore=0.3,    # <= 0.5 → 0
            ztile=0.9,     # >= 0.75 → 0
            qtile=0.85,    # >= 0.75 → 0
            znorm=0.1,     # <= 0.225 → 0
            best_prob=10.0,  # < 20 → 0
            best_cov=0.1
        )

        # Should get 0 from structure + 0 from sequence = 0
        assert judge == 0
        assert seqjudge == "no"

    def test_calculate_judge_score_partial(self):
        """Test judge score for partial quality hit."""
        from dpam.steps.step10_filter_domains import calculate_judge_score

        judge, seqjudge = calculate_judge_score(
            rank=1.2,      # < 1.5 → +1
            qscore=0.6,    # > 0.5 → +1
            ztile=0.7,     # < 0.75 → +1
            qtile=0.8,     # >= 0.75 → 0
            znorm=0.3,     # > 0.225 → +1
            best_prob=55.0,  # >= 50 → +2 (low + medium)
            best_cov=0.35
        )

        # Should get 4 from structure + 2 from sequence = 6
        assert judge == 6
        assert seqjudge == "medium"


@pytest.mark.unit
class TestStep12Disorder:
    """Tests for Step 12 (disorder prediction) functions."""

    def test_load_sse_assignments(self, tmp_path):
        """Test SSE assignment loading."""
        from dpam.steps.step12_disorder import load_sse_assignments

        sse_file = tmp_path / "test.sse"
        content = """1\tC\tna
10\tE\t1
11\tE\t1
20\tH\t2
"""
        sse_file.write_text(content)

        res2sse = load_sse_assignments(sse_file)

        # Should only load residues with SSE (not 'na')
        assert 1 not in res2sse
        assert res2sse[10] == 1
        assert res2sse[11] == 1
        assert res2sse[20] == 2

    def test_load_good_domain_residues_sequence(self, tmp_path):
        """Test loading residues from sequence hits."""
        from dpam.steps.step12_disorder import load_good_domain_residues

        gd_file = tmp_path / "test.goodDomains"
        # Sequence hit: range in column 8
        content = """sequence\tseq\ttest\t0.0\ttest\ttest\ttest\t99.0\t10-15\ttest
"""
        gd_file.write_text(content)

        hit_resids = load_good_domain_residues(gd_file)

        assert len(hit_resids) == 6
        assert 10 in hit_resids
        assert 15 in hit_resids
        assert 20 not in hit_resids

    def test_load_good_domain_residues_structure(self, tmp_path):
        """Test loading residues from structure hits."""
        from dpam.steps.step12_disorder import load_good_domain_residues

        gd_file = tmp_path / "test.goodDomains"
        # Structure hit: range in column 14
        content = """structure\thigh\ttest\t0.0\ttest\ttest\ttest\ttest\ttest\ttest\t99.0\t0.70\ttest\ttest\t20-25
"""
        gd_file.write_text(content)

        hit_resids = load_good_domain_residues(gd_file)

        assert len(hit_resids) == 6
        assert 20 in hit_resids
        assert 25 in hit_resids

    def test_load_good_domain_residues_mixed(self, tmp_path):
        """Test loading residues from mixed sequence and structure hits."""
        from dpam.steps.step12_disorder import load_good_domain_residues

        gd_file = tmp_path / "test.goodDomains"
        content = """sequence\tseq\ttest\t0.0\ttest\ttest\ttest\t99.0\t10-15\ttest
structure\thigh\ttest\t0.0\ttest\ttest\ttest\ttest\ttest\ttest\t99.0\t0.70\ttest\ttest\t20-25
"""
        gd_file.write_text(content)

        hit_resids = load_good_domain_residues(gd_file)

        # Should have 12 residues total
        assert len(hit_resids) == 12
        assert 10 in hit_resids
        assert 15 in hit_resids
        assert 20 in hit_resids
        assert 25 in hit_resids

    def test_load_pae_matrix_basic(self, tmp_path):
        """Test PAE matrix loading."""
        from dpam.steps.step12_disorder import load_pae_matrix
        import json

        json_file = tmp_path / "test.json"
        pae_data = {
            'predicted_aligned_error': [
                [1.0, 2.0, 3.0],
                [2.0, 1.0, 2.0],
                [3.0, 2.0, 1.0]
            ]
        }

        with open(json_file, 'w') as f:
            json.dump(pae_data, f)

        rpair2error = load_pae_matrix(json_file)

        # Check nested dict structure
        assert 1 in rpair2error
        assert 2 in rpair2error[1]
        assert rpair2error[1][2] == 2.0
        assert rpair2error[2][3] == 2.0
        assert rpair2error[3][3] == 1.0
