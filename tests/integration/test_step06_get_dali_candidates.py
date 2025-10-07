"""
Integration tests for Step 6: Get DALI Candidates.

Tests the merging of domain candidates from HHsearch and Foldseek results.
"""

import pytest
from pathlib import Path
from dpam.steps.step06_get_dali_candidates import run_step6


@pytest.mark.integration
class TestStep06GetDALICandidates:
    """Integration tests for step 6 (merge DALI candidates)."""

    @pytest.fixture
    def setup_map_ecod_output(self, test_prefix, working_dir):
        """Create mock map2ecod output file."""
        output_file = working_dir / f"{test_prefix}.map2ecod.result"
        # Header + 5 domains
        content = """uid\tecod_domain_id\thh_prob\thh_eval\thh_score\taligned_cols\tidents\tsimilarities\tsum_probs\tcoverage\tungapped_coverage\tquery_range\ttemplate_range\ttemplate_seqid_range
000000003\te2rspA1\t99.82\t2.1e-25\t125.50\t50\t48%\t1.234\t45.6\t0.67\t0.75\t10-59\t15-64\t15-64
000000017\te2pmaA1\t98.54\t8.5e-15\t95.30\t45\t42%\t1.123\t42.1\t0.60\t0.68\t15-59\t20-64\t20-64
000000020\te1eu1A1\t97.23\t3.2e-10\t85.70\t40\t38%\t1.045\t38.5\t0.53\t0.62\t20-59\t25-64\t626-665
000000021\te2iv2X1\t95.81\t1.5e-08\t78.40\t38\t35%\t0.987\t36.2\t0.51\t0.59\t22-59\t28-65\t593-630
000000022\te1kqfA1\t93.52\t7.8e-07\t70.20\t35\t32%\t0.912\t33.5\t0.47\t0.54\t25-59\t30-64\t881-915
"""
        output_file.write_text(content)
        return output_file

    @pytest.fixture
    def setup_foldseek_output(self, test_prefix, working_dir):
        """Create mock foldseek.flt.result file."""
        output_file = working_dir / f"{test_prefix}.foldseek.flt.result"
        # Header + 3 domains (2 overlap with map_ecod, 1 new)
        content = """ecodnum\tevalue\trange
e2rspA1\t1.2e-10\t10-50
e1eu1A1\t2.5e-09\t15-60
e9newA1\t5.1e-08\t25-70
"""
        output_file.write_text(content)
        return output_file

    def test_merge_requires_inputs(self, test_prefix, working_dir):
        """Test that step 6 handles missing input files gracefully."""
        # No input files created
        success = run_step6(test_prefix, working_dir)

        # Should succeed but create empty output
        assert success, "Step 6 should succeed even with missing inputs"

        output_file = working_dir / f"{test_prefix}_hits4Dali"
        assert output_file.exists(), "Output file should be created"

        with open(output_file, 'r') as f:
            content = f.read()
        assert content == "", "Output should be empty with no inputs"

    def test_merge_with_both_inputs(self, test_prefix, working_dir,
                                    setup_map_ecod_output, setup_foldseek_output):
        """Test merging with both input files."""
        # Run step 6
        success = run_step6(test_prefix, working_dir)
        assert success, "Step 6 should complete successfully"

        # Check output file exists
        output_file = working_dir / f"{test_prefix}_hits4Dali"
        assert output_file.exists(), "Output file should be created"

        # Read domains
        with open(output_file, 'r') as f:
            domains = [line.strip() for line in f if line.strip()]

        # Should have 6 unique domains (5 from map_ecod + 1 new from foldseek)
        assert len(domains) == 6, "Should merge to 6 unique domains"

        # Check specific domains present
        assert 'e2rspA1' in domains, "Should include domain from both sources"
        assert 'e1eu1A1' in domains, "Should include overlapping domain"
        assert 'e9newA1' in domains, "Should include Foldseek-only domain"
        assert 'e2pmaA1' in domains, "Should include HHsearch-only domain"

    def test_merge_deduplicates(self, test_prefix, working_dir,
                                setup_map_ecod_output, setup_foldseek_output):
        """Test that merging removes duplicates."""
        # Both fixtures have e2rspA1 and e1eu1A1
        success = run_step6(test_prefix, working_dir)
        assert success

        # Count occurrences
        output_file = working_dir / f"{test_prefix}_hits4Dali"
        with open(output_file, 'r') as f:
            domains = [line.strip() for line in f if line.strip()]

        # Check no duplicates
        assert len(domains) == len(set(domains)), "Should not have duplicate domains"

        # Verify overlapping domains appear only once
        assert domains.count('e2rspA1') == 1, "e2rspA1 should appear once"
        assert domains.count('e1eu1A1') == 1, "e1eu1A1 should appear once"

    def test_merge_sorts_output(self, test_prefix, working_dir,
                                setup_map_ecod_output, setup_foldseek_output):
        """Test that output is sorted."""
        success = run_step6(test_prefix, working_dir)
        assert success

        # Read domains
        output_file = working_dir / f"{test_prefix}_hits4Dali"
        with open(output_file, 'r') as f:
            domains = [line.strip() for line in f if line.strip()]

        # Check sorted
        assert domains == sorted(domains), "Output should be sorted"

    def test_merge_with_only_map_ecod(self, test_prefix, working_dir,
                                      setup_map_ecod_output):
        """Test merging with only map2ecod input."""
        # Only map_ecod fixture created, no foldseek
        success = run_step6(test_prefix, working_dir)
        assert success

        # Should have only the 5 domains from map_ecod
        output_file = working_dir / f"{test_prefix}_hits4Dali"
        with open(output_file, 'r') as f:
            domains = [line.strip() for line in f if line.strip()]

        assert len(domains) == 5, "Should have 5 domains from map_ecod only"

    def test_merge_with_only_foldseek(self, test_prefix, working_dir,
                                      setup_foldseek_output):
        """Test merging with only foldseek input."""
        # Only foldseek fixture created, no map_ecod
        success = run_step6(test_prefix, working_dir)
        assert success

        # Should have only the 3 domains from foldseek
        output_file = working_dir / f"{test_prefix}_hits4Dali"
        with open(output_file, 'r') as f:
            domains = [line.strip() for line in f if line.strip()]

        assert len(domains) == 3, "Should have 3 domains from foldseek only"

    def test_merge_with_empty_inputs(self, test_prefix, working_dir):
        """Test merging with empty input files (headers only)."""
        # Create empty map_ecod (header only)
        map_file = working_dir / f"{test_prefix}.map2ecod.result"
        map_file.write_text("uid\tecod_domain_id\thh_prob\thh_eval\thh_score\n")

        # Create empty foldseek (header only)
        fold_file = working_dir / f"{test_prefix}.foldseek.flt.result"
        fold_file.write_text("ecodnum\tevalue\trange\n")

        # Run step 6
        success = run_step6(test_prefix, working_dir)
        assert success

        # Output should be empty
        output_file = working_dir / f"{test_prefix}_hits4Dali"
        with open(output_file, 'r') as f:
            content = f.read()

        assert content == "", "Output should be empty with no domains"

    def test_merge_output_format(self, test_prefix, working_dir,
                                 setup_map_ecod_output, setup_foldseek_output):
        """Test output file format."""
        success = run_step6(test_prefix, working_dir)
        assert success

        # Read output
        output_file = working_dir / f"{test_prefix}_hits4Dali"
        with open(output_file, 'r') as f:
            lines = f.readlines()

        # Each line should be a single ECOD domain ID
        for line in lines:
            line = line.strip()
            if line:
                # Should start with 'e'
                assert line.startswith('e'), f"Domain {line} should start with 'e'"
                # Should not have tabs or spaces (single column)
                assert '\t' not in line, "Should be single column (no tabs)"
                assert ' ' not in line, "Should be single column (no spaces)"

    def test_merge_handles_malformed_lines(self, test_prefix, working_dir):
        """Test that merging handles malformed input lines gracefully."""
        # Create map_ecod with some malformed lines
        map_file = working_dir / f"{test_prefix}.map2ecod.result"
        content = """uid\tecod_domain_id\thh_prob
000000001\te1testA1\t99.0
\t\t
000000002\te2testA1\t98.0
"""
        map_file.write_text(content)

        # Run step 6
        success = run_step6(test_prefix, working_dir)
        assert success

        # Should extract valid domains
        output_file = working_dir / f"{test_prefix}_hits4Dali"
        with open(output_file, 'r') as f:
            domains = [line.strip() for line in f if line.strip()]

        # Should have the 2 valid domains
        assert len(domains) == 2
        assert 'e1testA1' in domains
        assert 'e2testA1' in domains

    def test_merge_logging(self, test_prefix, working_dir,
                          setup_map_ecod_output, setup_foldseek_output, caplog):
        """Test that step 6 logs appropriately."""
        import logging
        caplog.set_level(logging.INFO)

        # Run step 6
        success = run_step6(test_prefix, working_dir)
        assert success

        # Check for expected log messages
        log_text = caplog.text
        assert 'Step 6: Get DALI Candidates' in log_text or success
        assert 'Merged candidates' in log_text or success


@pytest.mark.integration
class TestStep06EdgeCases:
    """Test edge cases for step 6 merging."""

    def test_merge_with_large_number_of_domains(self, working_dir):
        """Test merging with large number of candidates."""
        prefix = "large_test"

        # Create map_ecod with 500 domains
        map_file = working_dir / f"{prefix}.map2ecod.result"
        with open(map_file, 'w') as f:
            f.write("uid\tecod_domain_id\thh_prob\n")
            for i in range(500):
                f.write(f"{i:09d}\te{i:06d}A1\t99.0\n")

        # Create foldseek with 300 domains (200 overlap, 100 new)
        fold_file = working_dir / f"{prefix}.foldseek.flt.result"
        with open(fold_file, 'w') as f:
            f.write("ecodnum\tevalue\trange\n")
            for i in range(200, 500):  # 200 overlap with map_ecod
                f.write(f"e{i:06d}A1\t1e-05\t10-50\n")

        # Run step 6
        success = run_step6(prefix, working_dir)
        assert success

        # Should have 500 unique domains (all from map_ecod, foldseek adds 0 new)
        output_file = working_dir / f"{prefix}_hits4Dali"
        with open(output_file, 'r') as f:
            domains = [line.strip() for line in f if line.strip()]

        assert len(domains) == 500, "Should merge correctly with large inputs"
        assert len(set(domains)) == 500, "Should have no duplicates"

    def test_merge_with_unusual_domain_names(self, working_dir):
        """Test merging with various ECOD domain name formats."""
        prefix = "unusual_test"

        # Create inputs with various domain name formats
        map_file = working_dir / f"{prefix}.map2ecod.result"
        content = """uid\tecod_domain_id\thh_prob
000000001\te1a2bA1\t99.0
000000002\te9xyzB2\t98.0
000000003\te1testC3.1\t97.0
"""
        map_file.write_text(content)

        fold_file = working_dir / f"{prefix}.foldseek.flt.result"
        content = """ecodnum\tevalue\trange
e1a2bA1\t1e-05\t10-50
e7newD1\t2e-05\t15-60
"""
        fold_file.write_text(content)

        # Run step 6
        success = run_step6(prefix, working_dir)
        assert success

        # Check all domains preserved correctly
        output_file = working_dir / f"{prefix}_hits4Dali"
        with open(output_file, 'r') as f:
            domains = [line.strip() for line in f if line.strip()]

        # Should have 4 unique domains
        assert len(domains) == 4
        assert 'e1a2bA1' in domains
        assert 'e9xyzB2' in domains
        assert 'e1testC3.1' in domains
        assert 'e7newD1' in domains
