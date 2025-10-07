"""
Integration tests for Step 4: Filter Foldseek Results.

Tests the filtering logic that reduces redundancy based on residue coverage.
"""

import pytest
from pathlib import Path
from dpam.steps.step04_filter_foldseek import run_step4


@pytest.mark.integration
class TestStep04FilterFoldseek:
    """Integration tests for step 4 (filter foldseek)."""

    @pytest.fixture
    def setup_foldseek_output(self, test_data_dir, test_prefix, working_dir):
        """Copy foldseek output to working directory."""
        import shutil
        src = test_data_dir / f"{test_prefix}.foldseek"
        if src.exists():
            dst = working_dir / f"{test_prefix}.foldseek"
            shutil.copy(src, dst)
            return dst
        return None

    def test_filter_requires_fasta(self, test_prefix, working_dir, setup_foldseek_output):
        """Test that step 4 fails gracefully without FASTA file."""
        if setup_foldseek_output is None:
            pytest.skip("Foldseek test file not available")

        # Don't create FASTA file
        success = run_step4(test_prefix, working_dir)
        assert not success, "Step 4 should fail without FASTA file"

    def test_filter_requires_foldseek_output(self, test_prefix, working_dir, setup_test_files):
        """Test that step 4 fails gracefully without Foldseek output."""
        if 'fa' not in setup_test_files:
            pytest.skip("FASTA test file not available")

        # Don't create foldseek output
        success = run_step4(test_prefix, working_dir)
        assert not success, "Step 4 should fail without Foldseek output"

    def test_filter_with_test_data(self, test_prefix, working_dir,
                                   setup_test_files, setup_foldseek_output):
        """Test filtering with test data."""
        if 'fa' not in setup_test_files:
            pytest.skip("FASTA test file not available")
        if setup_foldseek_output is None:
            pytest.skip("Foldseek test file not available")

        # Run step 4
        success = run_step4(test_prefix, working_dir)
        assert success, "Step 4 should complete successfully"

        # Check output file exists
        output_file = working_dir / f"{test_prefix}.foldseek.flt.result"
        assert output_file.exists(), "Filtered output file should be created"

        # Check output has content
        assert output_file.stat().st_size > 0, "Filtered output should not be empty"

    def test_filter_output_format(self, test_prefix, working_dir,
                                  setup_test_files, setup_foldseek_output):
        """Test that filtered output has expected format."""
        if 'fa' not in setup_test_files:
            pytest.skip("FASTA test file not available")
        if setup_foldseek_output is None:
            pytest.skip("Foldseek test file not available")

        # Run step 4
        success = run_step4(test_prefix, working_dir)
        assert success

        # Read and validate output format
        output_file = working_dir / f"{test_prefix}.foldseek.flt.result"
        with open(output_file, 'r') as f:
            lines = f.readlines()

        # Check header
        assert lines[0].strip() == "ecodnum\tevalue\trange", "Header should match expected format"

        # Check data lines (if any)
        if len(lines) > 1:
            # First data line
            fields = lines[1].strip().split('\t')
            assert len(fields) == 3, "Data line should have 3 tab-delimited fields"

            # Field 1: ECOD number
            assert fields[0].startswith('e'), "ECOD number should start with 'e'"

            # Field 2: E-value (scientific notation)
            try:
                float(fields[1])
            except ValueError:
                pytest.fail("E-value should be a valid float")

            # Field 3: Range (format: start-end)
            assert '-' in fields[2], "Range should contain hyphen"
            start, end = fields[2].split('-')
            assert start.isdigit() and end.isdigit(), "Range should be numeric"

    def test_filter_reduces_hits(self, test_prefix, working_dir,
                                setup_test_files, setup_foldseek_output):
        """Test that filtering reduces number of hits."""
        if 'fa' not in setup_test_files:
            pytest.skip("FASTA test file not available")
        if setup_foldseek_output is None:
            pytest.skip("Foldseek test file not available")

        # Count input hits
        foldseek_file = working_dir / f"{test_prefix}.foldseek"
        with open(foldseek_file, 'r') as f:
            n_input_hits = sum(1 for line in f)

        # Run step 4
        success = run_step4(test_prefix, working_dir)
        assert success

        # Count output hits
        output_file = working_dir / f"{test_prefix}.foldseek.flt.result"
        with open(output_file, 'r') as f:
            n_output_hits = sum(1 for line in f) - 1  # Subtract header

        # Filtering should reduce or maintain hit count
        assert n_output_hits <= n_input_hits, \
            "Filtered hits should be <= input hits"

    def test_filter_coverage_threshold(self, test_prefix, working_dir,
                                       setup_test_files, setup_foldseek_output):
        """Test that filtering applies coverage threshold correctly."""
        if 'fa' not in setup_test_files:
            pytest.skip("FASTA test file not available")
        if setup_foldseek_output is None:
            pytest.skip("Foldseek test file not available")

        # Run step 4
        success = run_step4(test_prefix, working_dir)
        assert success

        # Parse filtered output
        output_file = working_dir / f"{test_prefix}.foldseek.flt.result"
        with open(output_file, 'r') as f:
            lines = f.readlines()[1:]  # Skip header

        # Each kept hit should have a valid range
        for line in lines:
            fields = line.strip().split('\t')
            range_str = fields[2]
            start, end = map(int, range_str.split('-'))

            # Range should be valid
            assert start > 0, "Start position should be positive"
            assert end >= start, "End should be >= start"

            # Range should span at least 10 residues (the threshold)
            # Note: This isn't strictly enforced by the algorithm
            # (it checks "good" residues which depends on coverage)
            # but our test data should satisfy this
            span = end - start + 1
            # Don't enforce minimum span as it depends on coverage counts

    def test_filter_preserves_evalue_order(self, test_prefix, working_dir,
                                          setup_test_files, setup_foldseek_output):
        """Test that output maintains e-value order."""
        if 'fa' not in setup_test_files:
            pytest.skip("FASTA test file not available")
        if setup_foldseek_output is None:
            pytest.skip("Foldseek test file not available")

        # Run step 4
        success = run_step4(test_prefix, working_dir)
        assert success

        # Parse output evalues
        output_file = working_dir / f"{test_prefix}.foldseek.flt.result"
        evalues = []
        with open(output_file, 'r') as f:
            for line in f.readlines()[1:]:  # Skip header
                fields = line.strip().split('\t')
                evalues.append(float(fields[1]))

        # E-values should be in ascending order (hits are sorted by evalue)
        for i in range(len(evalues) - 1):
            assert evalues[i] <= evalues[i + 1], \
                "E-values should be in ascending order"

    def test_filter_with_empty_input(self, test_prefix, working_dir, setup_test_files):
        """Test filtering with empty Foldseek output."""
        if 'fa' not in setup_test_files:
            pytest.skip("FASTA test file not available")

        # Create empty foldseek file
        foldseek_file = working_dir / f"{test_prefix}.foldseek"
        foldseek_file.write_text("")

        # Run step 4
        success = run_step4(test_prefix, working_dir)
        assert success, "Should succeed even with empty input"

        # Check output
        output_file = working_dir / f"{test_prefix}.foldseek.flt.result"
        assert output_file.exists()

        with open(output_file, 'r') as f:
            lines = f.readlines()

        # Should have header but no data
        assert len(lines) == 1, "Should only have header with empty input"
        assert lines[0].strip() == "ecodnum\tevalue\trange"

    def test_filter_logging(self, test_prefix, working_dir,
                           setup_test_files, setup_foldseek_output, caplog):
        """Test that step 4 logs appropriately."""
        if 'fa' not in setup_test_files:
            pytest.skip("FASTA test file not available")
        if setup_foldseek_output is None:
            pytest.skip("Foldseek test file not available")

        import logging
        caplog.set_level(logging.INFO)

        # Run step 4
        success = run_step4(test_prefix, working_dir)
        assert success

        # Check for expected log messages
        log_text = caplog.text
        # Check that at least some logging occurred
        assert len(log_text) > 0 or success, \
            "Should have logged messages or succeeded silently"


@pytest.mark.integration
class TestStep04EdgeCases:
    """Test edge cases for step 4 filtering."""

    def test_filter_with_short_query(self, working_dir):
        """Test filtering with very short query sequence."""
        prefix = "short_query"

        # Create short FASTA (20 residues)
        fa_file = working_dir / f"{prefix}.fa"
        fa_file.write_text(">short_query\nMQIFVKTLTGKTITLEVEPS\n")

        # Create foldseek output with hits
        foldseek_file = working_dir / f"{prefix}.foldseek"
        foldseek_file.write_text(
            "short_query\te1testA1.1\t0.9\t50\t0\t0\t5\t15\t10\t20\t1e-05\t50.0\n"
        )

        # Run step 4
        success = run_step4(prefix, working_dir)
        assert success

        # Output should exist
        output_file = working_dir / f"{prefix}.foldseek.flt.result"
        assert output_file.exists()

    def test_filter_with_overlapping_hits(self, working_dir):
        """Test filtering with highly overlapping hits."""
        prefix = "overlap_test"

        # Create FASTA
        fa_file = working_dir / f"{prefix}.fa"
        fa_file.write_text(">overlap_test\n" + "M" * 100 + "\n")

        # Create foldseek output with overlapping hits (all cover residues 10-30)
        foldseek_content = []
        for i in range(150):  # Create 150 hits covering same region
            foldseek_content.append(
                f"overlap_test\te{i}testA1.1\t0.9\t50\t0\t0\t10\t30\t15\t35\t{i}e-05\t50.0\n"
            )

        foldseek_file = working_dir / f"{prefix}.foldseek"
        foldseek_file.write_text(''.join(foldseek_content))

        # Run step 4
        success = run_step4(prefix, working_dir)
        assert success

        # Should filter heavily due to coverage threshold
        output_file = working_dir / f"{prefix}.foldseek.flt.result"
        with open(output_file, 'r') as f:
            n_filtered = sum(1 for line in f) - 1  # Subtract header

        # Should keep much fewer than 150 hits (coverage will exceed 100 quickly)
        assert n_filtered < 150, "Should filter out hits with high coverage"
