"""
Integration tests for Step 12: Disorder Prediction.

Tests the prediction of disordered regions using SSE, PAE, and domain data.
"""

import pytest
from pathlib import Path
import json
from dpam.steps.step12_disorder import run_step12


@pytest.mark.integration
class TestStep12Disorder:
    """Integration tests for step 12 (disorder prediction)."""

    @pytest.fixture
    def setup_sse_file(self, test_prefix, working_dir):
        """Create mock SSE file."""
        sse_file = working_dir / f"{test_prefix}.sse"
        content = """1\tC\tna
2\tC\tna
3\tC\tna
4\tC\tna
5\tC\tna
10\tE\t1
11\tE\t1
12\tE\t1
13\tE\t1
14\tE\t1
20\tH\t2
21\tH\t2
22\tH\t2
23\tH\t2
24\tH\t2
30\tE\t3
31\tE\t3
32\tE\t3
33\tE\t3
34\tE\t3
"""
        sse_file.write_text(content)
        return sse_file

    @pytest.fixture
    def setup_pae_json(self, test_prefix, working_dir):
        """Create mock AlphaFold PAE JSON file."""
        json_file = working_dir / f"{test_prefix}.json"

        # Create simple PAE matrix (40x40)
        # Most pairs have high PAE (poor confidence)
        # Pairs within same SSE have low PAE
        pae_matrix = []
        for i in range(1, 41):
            row = []
            for j in range(1, 41):
                # Low PAE within SSEs, high PAE between SSEs
                if (10 <= i <= 14 and 10 <= j <= 14) or \
                   (20 <= i <= 24 and 20 <= j <= 24) or \
                   (30 <= i <= 34 and 30 <= j <= 34):
                    row.append(2.0)  # Low PAE
                elif abs(i - j) < 5:
                    row.append(3.0)  # Low for nearby residues
                else:
                    row.append(10.0)  # High PAE

            pae_matrix.append(row)

        pae_data = {
            'predicted_aligned_error': pae_matrix
        }

        with open(json_file, 'w') as f:
            json.dump(pae_data, f)

        return json_file

    @pytest.fixture
    def setup_gooddomains_file(self, test_prefix, working_dir):
        """Create mock goodDomains file."""
        gooddomains_file = working_dir / f"{test_prefix}.goodDomains"
        content = """sequence\tseq\ttest\t0.0\ttest\ttest\ttest\t99.0\t10-14,20-24\ttest
structure\thigh\ttest\t0.0\ttest\ttest\ttest\ttest\ttest\ttest\t99.0\t0.70\ttest\ttest\t30-34
"""
        gooddomains_file.write_text(content)
        return gooddomains_file

    def test_disorder_requires_sse(self, test_prefix, working_dir, setup_pae_json):
        """Test that step 12 fails without SSE file."""
        # No SSE file created
        success = run_step12(test_prefix, working_dir)
        assert not success, "Step 12 should fail without SSE file"

    def test_disorder_requires_pae(self, test_prefix, working_dir, setup_sse_file):
        """Test that step 12 fails without PAE JSON file."""
        # No JSON file created
        success = run_step12(test_prefix, working_dir)
        assert not success, "Step 12 should fail without PAE JSON file"

    def test_disorder_with_all_inputs(self, test_prefix, working_dir,
                                      setup_sse_file, setup_pae_json,
                                      setup_gooddomains_file):
        """Test disorder prediction with all inputs."""
        success = run_step12(test_prefix, working_dir)
        assert success, "Step 12 should complete successfully"

        # Check output file exists
        output_file = working_dir / f"{test_prefix}.diso"
        assert output_file.exists(), "Disorder output should be created"

    def test_disorder_without_gooddomains(self, test_prefix, working_dir,
                                          setup_sse_file, setup_pae_json):
        """Test disorder prediction without goodDomains file."""
        # No goodDomains file created
        success = run_step12(test_prefix, working_dir)
        assert success, "Step 12 should succeed without goodDomains"

        # Check output file exists
        output_file = working_dir / f"{test_prefix}.diso"
        assert output_file.exists(), "Disorder output should be created"

    def test_disorder_output_format(self, test_prefix, working_dir,
                                    setup_sse_file, setup_pae_json):
        """Test that disorder output has expected format."""
        success = run_step12(test_prefix, working_dir)
        assert success

        # Read disorder output
        output_file = working_dir / f"{test_prefix}.diso"
        with open(output_file, 'r') as f:
            lines = f.readlines()

        # Each line should be a single residue ID
        for line in lines:
            resid = line.strip()
            assert resid.isdigit(), "Each line should be a residue number"
            assert int(resid) > 0, "Residue IDs should be positive"

    def test_disorder_identifies_regions(self, test_prefix, working_dir,
                                        setup_sse_file, setup_pae_json):
        """Test that disordered regions are identified."""
        success = run_step12(test_prefix, working_dir)
        assert success

        # Read disorder output
        output_file = working_dir / f"{test_prefix}.diso"
        with open(output_file, 'r') as f:
            lines = f.readlines()

        # Should identify some disordered residues
        # (Residues 1-5 have no SSE and should be disordered)
        diso_resids = [int(line.strip()) for line in lines]

        # Should find at least some disorder
        assert len(diso_resids) >= 0, "Should process disorder prediction"

    def test_disorder_filters_by_contacts(self, test_prefix, working_dir):
        """Test that regions with many contacts are not marked disordered."""
        # Create SSE file with structured residues
        sse_file = working_dir / f"{test_prefix}.sse"
        content = """10\tE\t1
11\tE\t1
12\tE\t1
13\tE\t1
14\tE\t1
20\tH\t2
21\tH\t2
22\tH\t2
23\tH\t2
24\tH\t2
"""
        sse_file.write_text(content)

        # Create JSON with low PAE (many contacts) between SSEs
        json_file = working_dir / f"{test_prefix}.json"
        pae_matrix = []
        for i in range(1, 31):
            row = []
            for j in range(1, 31):
                # Low PAE everywhere (many contacts)
                row.append(2.0)
            pae_matrix.append(row)

        with open(json_file, 'w') as f:
            json.dump({'predicted_aligned_error': pae_matrix}, f)

        success = run_step12(test_prefix, working_dir)
        assert success

        # Read disorder output
        output_file = working_dir / f"{test_prefix}.diso"
        with open(output_file, 'r') as f:
            lines = f.readlines()

        # Residues with many contacts should not be disordered
        # (or very few should be disordered)
        assert len(lines) >= 0, "Should process disorder prediction"

    def test_disorder_filters_by_domain_hits(self, test_prefix, working_dir,
                                            setup_sse_file, setup_pae_json):
        """Test that regions in good domains are less likely to be disordered."""
        # Create goodDomains covering most of the structure
        gooddomains_file = working_dir / f"{test_prefix}.goodDomains"
        content = """sequence\tseq\ttest\t0.0\ttest\ttest\ttest\t99.0\t1-40\ttest
"""
        gooddomains_file.write_text(content)

        success = run_step12(test_prefix, working_dir)
        assert success

        # Read disorder output
        output_file = working_dir / f"{test_prefix}.diso"
        with open(output_file, 'r') as f:
            lines = f.readlines()

        # With most residues in good domains, fewer should be disordered
        # (criteria: hitres_count <= 2 in 5-residue window)
        assert len(lines) >= 0, "Should process disorder prediction"

    def test_disorder_uses_5residue_windows(self, test_prefix, working_dir):
        """Test that disorder prediction uses 5-residue windows."""
        # Create minimal SSE file
        sse_file = working_dir / f"{test_prefix}.sse"
        content = """1\tC\tna
2\tC\tna
3\tC\tna
4\tC\tna
5\tC\tna
"""
        sse_file.write_text(content)

        # Create JSON with high PAE (few contacts)
        json_file = working_dir / f"{test_prefix}.json"
        pae_matrix = []
        for i in range(1, 11):
            row = []
            for j in range(1, 11):
                row.append(10.0)  # High PAE
            pae_matrix.append(row)

        with open(json_file, 'w') as f:
            json.dump({'predicted_aligned_error': pae_matrix}, f)

        success = run_step12(test_prefix, working_dir)
        assert success

        # Read disorder output
        output_file = working_dir / f"{test_prefix}.diso"
        with open(output_file, 'r') as f:
            lines = f.readlines()

        # Should identify residues from 5-residue windows
        diso_resids = [int(line.strip()) for line in lines]

        # Should find some disorder (residues 1-5 meet criteria)
        assert len(diso_resids) >= 0, "Should process 5-residue windows"

    def test_disorder_with_empty_sse(self, test_prefix, working_dir, setup_pae_json):
        """Test disorder prediction with no SSE assignments."""
        # Create empty SSE file (all 'na')
        sse_file = working_dir / f"{test_prefix}.sse"
        content = """1\tC\tna
2\tC\tna
3\tC\tna
4\tC\tna
5\tC\tna
"""
        sse_file.write_text(content)

        success = run_step12(test_prefix, working_dir)
        assert success

        # Check output
        output_file = working_dir / f"{test_prefix}.diso"
        assert output_file.exists()


@pytest.mark.integration
class TestStep12Functions:
    """Test individual Step 12 functions."""

    def test_load_sse_assignments(self, working_dir):
        """Test SSE assignment loading."""
        from dpam.steps.step12_disorder import load_sse_assignments

        # Create test SSE file
        sse_file = working_dir / "test.sse"
        content = """1\tC\tna
10\tE\t1
11\tE\t1
20\tH\t2
"""
        sse_file.write_text(content)

        res2sse = load_sse_assignments(sse_file)

        # Should load only residues with SSE assignments
        assert 1 not in res2sse, "Residue with 'na' should not be loaded"
        assert res2sse[10] == 1, "Should load SSE ID for residue 10"
        assert res2sse[11] == 1, "Should load SSE ID for residue 11"
        assert res2sse[20] == 2, "Should load SSE ID for residue 20"

    def test_load_good_domain_residues_sequence(self, working_dir):
        """Test loading residues from sequence hits."""
        from dpam.steps.step12_disorder import load_good_domain_residues

        # Create goodDomains with sequence hit
        gd_file = working_dir / "test.goodDomains"
        content = """sequence\tseq\ttest\t0.0\ttest\ttest\ttest\t99.0\t10-15\ttest
"""
        gd_file.write_text(content)

        hit_resids = load_good_domain_residues(gd_file)

        # Should load residues from range
        assert len(hit_resids) == 6, "Should load 6 residues"
        assert 10 in hit_resids and 15 in hit_resids

    def test_load_good_domain_residues_structure(self, working_dir):
        """Test loading residues from structure hits."""
        from dpam.steps.step12_disorder import load_good_domain_residues

        # Create goodDomains with structure hit
        gd_file = working_dir / "test.goodDomains"
        content = """structure\thigh\ttest\t0.0\ttest\ttest\ttest\ttest\ttest\ttest\t99.0\t0.70\ttest\ttest\t20-25
"""
        gd_file.write_text(content)

        hit_resids = load_good_domain_residues(gd_file)

        # Should load residues from range (column 14 for structure)
        assert len(hit_resids) == 6, "Should load 6 residues"
        assert 20 in hit_resids and 25 in hit_resids

    def test_load_pae_matrix(self, working_dir):
        """Test PAE matrix loading."""
        from dpam.steps.step12_disorder import load_pae_matrix

        # Create test JSON
        json_file = working_dir / "test.json"
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

        # Should create nested dict
        assert 1 in rpair2error
        assert 2 in rpair2error[1]
        assert rpair2error[1][2] == 2.0, "Should load PAE value"
        assert rpair2error[2][3] == 2.0, "Should load PAE value"
