"""
Integration tests for Step 2: HHsearch.

Tests the HHsearch pipeline that runs hhblits → (addss) → hhmake → hhsearch.

KNOWN LIMITATION:
    addss.pl (secondary structure prediction via PSIPRED) is currently skipped
    by default due to missing PSIPRED dependencies. This may affect result quality
    and compatibility with DPAM v1.0 output. The pipeline works without it, but
    results should be validated once PSIPRED is properly configured.

    To enable addss.pl: Install PSIPRED and configure paths in HHPaths.pm, then
    set skip_addss=False in run_hhsearch_pipeline().
"""

import pytest
from pathlib import Path
from dpam.steps.step02_hhsearch import run_step2


@pytest.mark.integration
@pytest.mark.requires_hhsearch
class TestStep02HHsearch:
    """Integration tests for step 2 (hhsearch)."""

    @pytest.fixture
    def small_test_fasta(self, working_dir, test_data_dir):
        """Create a small test FASTA for faster testing."""
        from shutil import copy
        small_fa = test_data_dir / "test_small.fa"
        if small_fa.exists():
            dest = working_dir / "test_small.fa"
            copy(small_fa, dest)
            return dest, "test_small"
        return None, None

    @pytest.fixture
    def hhsearch_databases(self):
        """
        Find HHsearch databases or skip test.

        Returns dict with base_dir and database availability flags.
        """
        # Check for databases in common locations
        uniref_candidates = [
            Path('/home/rschaeff/search_libs/UniRef30_2023_02'),
            Path('/data/ecod/external_hhlibs/UniRef30_2022_02/UniRef30_2022_02'),
        ]

        pdb70_candidates = [
            Path('/data/ecod/external_hhlibs/PDB70/pdb70'),
        ]

        # Find UniRef database
        uniref_path = None
        for candidate in uniref_candidates:
            if Path(str(candidate) + '_a3m.ffindex').exists():
                uniref_path = candidate
                break

        # Find PDB70 database
        pdb70_path = None
        for candidate in pdb70_candidates:
            if Path(str(candidate) + '_hhm.ffindex').exists():
                pdb70_path = candidate
                break

        if not pdb70_path:
            pytest.skip("PDB70 database not found (minimum requirement)")

        # Determine base directory structure for step
        # We need to create a structure like: base_dir/UniRef30_*/UniRef30_* and base_dir/pdb70/pdb70
        return {
            'uniref_path': uniref_path,
            'pdb70_path': pdb70_path,
            'uniref_exists': uniref_path is not None,
            'pdb70_exists': pdb70_path is not None,
        }

    def test_hhsearch_requires_fasta(self, test_prefix, working_dir, hhsearch_databases):
        """Test that step 2 fails gracefully without FASTA file."""
        # Don't create FASTA file
        success = run_step2(
            test_prefix,
            working_dir,
            uniref_db=hhsearch_databases['uniref_path'],
            pdb70_db=hhsearch_databases['pdb70_path'],
            cpus=1
        )

        assert not success, "Step 2 should fail without FASTA file"

    @pytest.mark.slow
    def test_hhsearch_with_small_sequence(self, working_dir,
                                          hhsearch_databases, small_test_fasta):
        """Test HHsearch pipeline with small test sequence."""
        if not hhsearch_databases['uniref_exists']:
            pytest.skip("UniRef database required for full pipeline")

        fasta_file, prefix = small_test_fasta
        if fasta_file is None:
            pytest.skip("Small test FASTA not available")

        # Run step 2 with small sequence (~75 residues, much faster)
        success = run_step2(
            prefix,
            working_dir,
            uniref_db=hhsearch_databases['uniref_path'],
            pdb70_db=hhsearch_databases['pdb70_path'],
            cpus=2
        )

        assert success, "Step 2 should complete successfully"

        # Check intermediate files
        a3m_file = working_dir / f"{prefix}.a3m"
        hmm_file = working_dir / f"{prefix}.hmm"
        hhsearch_file = working_dir / f"{prefix}.hhsearch"

        assert a3m_file.exists(), "A3M file should be created"
        assert hmm_file.exists(), "HMM file should be created"
        assert hhsearch_file.exists(), "HHsearch output should be created"

        # Check HHsearch output has content
        assert hhsearch_file.stat().st_size > 0, "HHsearch output should not be empty"

    @pytest.mark.slow
    def test_hhsearch_output_format(self, working_dir,
                                    hhsearch_databases, small_test_fasta):
        """Test that HHsearch output has expected format."""
        if not hhsearch_databases['uniref_exists']:
            pytest.skip("UniRef database required for full pipeline")

        fasta_file, prefix = small_test_fasta
        if fasta_file is None:
            pytest.skip("Small test FASTA not available")

        # Run step 2
        success = run_step2(
            prefix,
            working_dir,
            uniref_db=hhsearch_databases['uniref_path'],
            pdb70_db=hhsearch_databases['pdb70_path'],
            cpus=2
        )

        assert success

        # Read and validate HHsearch output
        hhsearch_file = working_dir / f"{prefix}.hhsearch"
        content = hhsearch_file.read_text()

        # Check for HHsearch header
        assert "Query" in content or "HHsearch" in content, \
            "HHsearch output should have proper header"

        # Check for alignment section
        assert "No Hit" in content or "Probab" in content, \
            "HHsearch output should have results section"

    @pytest.mark.slow
    def test_hhsearch_creates_logs(self, working_dir,
                                   hhsearch_databases, small_test_fasta):
        """Test that pipeline creates log files."""
        if not hhsearch_databases['uniref_exists']:
            pytest.skip("UniRef database required for full pipeline")

        fasta_file, prefix = small_test_fasta
        if fasta_file is None:
            pytest.skip("Small test FASTA not available")

        # Run step 2
        success = run_step2(
            prefix,
            working_dir,
            uniref_db=hhsearch_databases['uniref_path'],
            pdb70_db=hhsearch_databases['pdb70_path'],
            cpus=2
        )

        assert success

        # Check for log files
        hhblits_log = working_dir / f"{prefix}.hhblits.log"
        hhmake_log = working_dir / f"{prefix}.hhmake.log"

        # At least one log should exist
        logs_exist = hhblits_log.exists() or hhmake_log.exists()
        assert logs_exist, "Pipeline should create log files"

    @pytest.mark.slow
    def test_hhsearch_with_multiple_cpus(self, working_dir,
                                        hhsearch_databases, small_test_fasta):
        """Test that HHsearch can use multiple CPUs."""
        if not hhsearch_databases['uniref_exists']:
            pytest.skip("UniRef database required for full pipeline")

        fasta_file, prefix = small_test_fasta
        if fasta_file is None:
            pytest.skip("Small test FASTA not available")

        # Run with 4 CPUs
        success = run_step2(
            prefix,
            working_dir,
            uniref_db=hhsearch_databases['uniref_path'],
            pdb70_db=hhsearch_databases['pdb70_path'],
            cpus=4
        )

        assert success, "Step 2 should work with multiple CPUs"

        # Output should still be valid
        hhsearch_file = working_dir / f"{prefix}.hhsearch"
        assert hhsearch_file.exists()
        assert hhsearch_file.stat().st_size > 0


@pytest.mark.integration
@pytest.mark.requires_hhsearch
class TestStep02Tools:
    """Test individual HHsuite tools."""

    def test_hhblits_available(self):
        """Test that hhblits is available."""
        from dpam.tools.hhsuite import HHBlits

        hhblits = HHBlits()
        assert hhblits.is_available(), "hhblits should be available"

    def test_addss_available(self):
        """Test that addss.pl is available."""
        from dpam.tools.hhsuite import AddSS

        addss = AddSS()
        assert addss.is_available(), "addss.pl should be available"

    def test_hhmake_available(self):
        """Test that hhmake is available."""
        from dpam.tools.hhsuite import HHMake

        hhmake = HHMake()
        assert hhmake.is_available(), "hhmake should be available"

    def test_hhsearch_available(self):
        """Test that hhsearch is available."""
        from dpam.tools.hhsuite import HHSearch

        hhsearch = HHSearch()
        assert hhsearch.is_available(), "hhsearch should be available"
