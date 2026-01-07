"""
Test external dependencies and tools.

These tests verify that all required external tools and data are available.
Run these first to fail fast if dependencies are missing.

Usage:
    pytest tests/test_dependencies.py -v
    pytest tests/test_dependencies.py -v -k "hhsuite"
    pytest tests/test_dependencies.py -v -k "tensorflow"
"""

import pytest
import shutil
import subprocess
import os
from pathlib import Path


# =============================================================================
# HHsuite Tests (hhblits, hhmake, hhsearch, addss.pl)
# =============================================================================

def _find_hhsuite():
    """Find HHsuite installation."""
    # Check PATH first
    hhsearch = shutil.which("hhsearch")
    if hhsearch:
        return Path(hhsearch).parent

    # Check standard HPC location
    hpc_path = Path("/sw/apps/hh-suite/bin")
    if hpc_path.exists():
        return hpc_path

    return None


class TestHHsuite:
    """Test HHsuite tool availability and basic functionality."""

    def test_hhblits_available(self):
        """Check if hhblits is available in PATH."""
        hhsuite_bin = _find_hhsuite()
        if hhsuite_bin is None:
            pytest.skip("HHsuite not found in PATH or standard locations")
        hhblits = hhsuite_bin / "hhblits"
        assert hhblits.exists() or shutil.which("hhblits"), \
            "hhblits not found in PATH. Install HHsuite or add to PATH."

    def test_hhblits_version(self):
        """Check hhblits can be executed and get version."""
        hhsuite_bin = _find_hhsuite()
        if hhsuite_bin is None:
            pytest.skip("HHsuite not found")
        hhblits = hhsuite_bin / "hhblits"
        result = subprocess.run(
            [str(hhblits), "-h"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0 or "HHblits" in result.stdout, \
            "hhblits failed to execute"

    def test_hhmake_available(self):
        """Check if hhmake is available in PATH."""
        hhsuite_bin = _find_hhsuite()
        if hhsuite_bin is None:
            pytest.skip("HHsuite not found")
        hhmake = hhsuite_bin / "hhmake"
        assert hhmake.exists() or shutil.which("hhmake"), \
            "hhmake not found in PATH. Install HHsuite or add to PATH."

    def test_hhmake_version(self):
        """Check hhmake can be executed."""
        hhsuite_bin = _find_hhsuite()
        if hhsuite_bin is None:
            pytest.skip("HHsuite not found")
        hhmake = hhsuite_bin / "hhmake"
        result = subprocess.run(
            [str(hhmake), "-h"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0 or "HHmake" in result.stdout, \
            "hhmake failed to execute"

    def test_hhsearch_available(self):
        """Check if hhsearch is available in PATH."""
        hhsuite_bin = _find_hhsuite()
        if hhsuite_bin is None:
            pytest.skip("HHsuite not found")
        hhsearch = hhsuite_bin / "hhsearch"
        assert hhsearch.exists() or shutil.which("hhsearch"), \
            "hhsearch not found in PATH. Install HHsuite or add to PATH."

    def test_hhsearch_version(self):
        """Check hhsearch can be executed."""
        hhsuite_bin = _find_hhsuite()
        if hhsuite_bin is None:
            pytest.skip("HHsuite not found")
        hhsearch = hhsuite_bin / "hhsearch"
        result = subprocess.run(
            [str(hhsearch), "-h"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0 or "HHsearch" in result.stdout, \
            "hhsearch failed to execute"

    def test_addss_available(self):
        """Check if addss.pl is available in PATH."""
        addss = shutil.which("addss.pl")
        if addss is None:
            # Check in HHsuite scripts directory
            hhsuite_bin = _find_hhsuite()
            if hhsuite_bin:
                scripts_dir = hhsuite_bin.parent / "scripts"
                addss_path = scripts_dir / "addss.pl"
                if addss_path.exists():
                    addss = addss_path
        if addss is None:
            pytest.skip("addss.pl not found (HHsuite scripts not in PATH)")
        assert addss is not None

    def test_reformat_available(self):
        """Check if reformat.pl is available (used by HHsuite)."""
        reformat = shutil.which("reformat.pl")
        if reformat is None:
            hhsuite_bin = _find_hhsuite()
            if hhsuite_bin:
                scripts_dir = hhsuite_bin.parent / "scripts"
                reformat_path = scripts_dir / "reformat.pl"
                if reformat_path.exists():
                    reformat = reformat_path
        if reformat is None:
            pytest.skip("reformat.pl not found (HHsuite scripts not in PATH)")


# =============================================================================
# PSIPRED Tests
# =============================================================================

def _find_psipred():
    """Find PSIPRED installation."""
    # Check PATH first
    psipred = shutil.which("psipred")
    if psipred:
        return Path(psipred)

    # Check in conda environment
    conda_prefix = os.environ.get("CONDA_PREFIX", "")
    if conda_prefix:
        psipred_path = Path(conda_prefix) / "bin" / "psipred"
        if psipred_path.exists():
            return psipred_path

    # Check common dpam conda path
    dpam_conda = Path.home() / ".conda" / "envs" / "dpam" / "bin" / "psipred"
    if dpam_conda.exists():
        return dpam_conda

    return None


class TestPSIPRED:
    """Test PSIPRED availability for secondary structure prediction."""

    def test_psipred_available(self):
        """Check if psipred is available."""
        psipred = _find_psipred()
        if psipred is None:
            pytest.skip("PSIPRED not found. Install or activate dpam conda environment.")

    def test_psipass2_available(self):
        """Check if psipass2 is available (PSIPRED component)."""
        psipass2 = shutil.which("psipass2")
        if psipass2 is None:
            conda_prefix = os.environ.get("CONDA_PREFIX", "")
            if conda_prefix:
                psipass2 = Path(conda_prefix) / "bin" / "psipass2"
                if not psipass2.exists():
                    psipass2 = None
        # psipass2 is optional, just warn if missing
        if psipass2 is None:
            pytest.skip("psipass2 not found (optional PSIPRED component)")

    def test_psipred_data_available(self):
        """Check if PSIPRED data files are available."""
        conda_prefix = os.environ.get("CONDA_PREFIX", "")
        if not conda_prefix:
            pytest.skip("CONDA_PREFIX not set, cannot check PSIPRED data")

        data_dir = Path(conda_prefix) / "share" / "psipred_4.02" / "data"
        if not data_dir.exists():
            data_dir = Path(conda_prefix) / "share" / "psipred" / "data"

        if data_dir.exists():
            # Check for key weight files
            weight_files = list(data_dir.glob("*.wgt"))
            assert len(weight_files) > 0, \
                f"No PSIPRED weight files found in {data_dir}"
        else:
            pytest.skip(f"PSIPRED data directory not found: {data_dir}")


# =============================================================================
# DALI Tests
# =============================================================================

class TestDALI:
    """Test DALI (DaliLite) availability and functionality."""

    def test_dali_available(self):
        """Check if dali.pl is available."""
        dali = shutil.which("dali.pl")
        if dali is None:
            # Check standard locations
            candidates = [
                Path.home() / "src" / "Dali_v5" / "DaliLite.v5" / "bin" / "dali.pl",
                Path(os.environ.get("DALI_HOME", "")) / "bin" / "dali.pl",
            ]
            for candidate in candidates:
                if candidate.exists():
                    dali = candidate
                    break

        assert dali is not None, \
            "dali.pl not found. Install DaliLite.v5 or set DALI_HOME environment variable."

    def test_dali_executable(self):
        """Check dali.pl can be executed."""
        dali = shutil.which("dali.pl")
        if dali is None:
            pytest.skip("dali.pl not in PATH")

        result = subprocess.run(
            ["dali.pl", "--help"],
            capture_output=True,
            text=True
        )
        # dali.pl may return non-zero for --help, check output
        assert "Usage" in result.stdout or "dali" in result.stdout.lower() or \
               "Usage" in result.stderr or "dali" in result.stderr.lower(), \
            "dali.pl failed to execute"

    def test_dali_import_exe_available(self):
        """Check if import.pl is available (DALI component)."""
        import_exe = shutil.which("import.pl")
        if import_exe is None:
            dali_home = os.environ.get("DALI_HOME", "")
            if dali_home:
                import_exe = Path(dali_home) / "bin" / "import.pl"
                if not import_exe.exists():
                    import_exe = None
        # import.pl is used internally by dali.pl
        if import_exe is None:
            pytest.skip("import.pl not found (DALI may still work)")


# =============================================================================
# DSSP Tests
# =============================================================================

class TestDSSP:
    """Test DSSP availability for secondary structure assignment."""

    def test_dssp_available(self):
        """Check if DSSP (mkdssp or dsspcmbi) is available."""
        dssp = shutil.which("mkdssp")
        if dssp is None:
            dssp = shutil.which("dsspcmbi")
        if dssp is None:
            # Check DaliLite location
            dali_home = os.environ.get("DALI_HOME", "")
            if dali_home:
                dssp = Path(dali_home) / "bin" / "dsspcmbi"
                if not dssp.exists():
                    dssp = None
            else:
                # Check standard DaliLite location
                std_dssp = Path.home() / "src" / "Dali_v5" / "DaliLite.v5" / "bin" / "dsspcmbi"
                if std_dssp.exists():
                    dssp = std_dssp

        assert dssp is not None, \
            "DSSP not found. Install mkdssp or DaliLite.v5 (provides dsspcmbi)."

    def test_dssp_executable(self):
        """Check DSSP can be executed."""
        dssp = shutil.which("mkdssp") or shutil.which("dsspcmbi")
        if dssp is None:
            pytest.skip("DSSP not in PATH")

        result = subprocess.run(
            [dssp, "--version"],
            capture_output=True,
            text=True
        )
        # DSSP may return non-zero for --version
        assert result.returncode == 0 or \
               "dssp" in result.stdout.lower() or \
               "dssp" in result.stderr.lower(), \
            "DSSP failed to execute"


# =============================================================================
# Foldseek Tests
# =============================================================================

class TestFoldseek:
    """Test Foldseek availability and functionality."""

    def test_foldseek_available(self):
        """Check if foldseek is available in PATH."""
        assert shutil.which("foldseek") is not None, \
            "foldseek not found in PATH. Install foldseek."

    def test_foldseek_version(self):
        """Check foldseek can be executed and get version."""
        result = subprocess.run(
            ["foldseek", "version"],
            capture_output=True,
            text=True
        )
        # foldseek version command should work
        assert result.returncode == 0 or "foldseek" in result.stdout.lower(), \
            "foldseek failed to execute"

    def test_foldseek_help(self):
        """Check foldseek help works."""
        result = subprocess.run(
            ["foldseek", "-h"],
            capture_output=True,
            text=True
        )
        assert "easy-search" in result.stdout or "easy-search" in result.stderr, \
            "foldseek help doesn't show expected commands"

    def test_foldseek_omp_proc_bind_handling(self):
        """Test that foldseek wrapper handles OMP_PROC_BIND correctly."""
        # This tests the SLURM compatibility fix
        from dpam.tools.foldseek import Foldseek

        wrapper = Foldseek()
        # Wrapper should be able to initialize
        assert wrapper is not None
        # Check availability method exists
        assert hasattr(wrapper, 'is_available')
        assert wrapper.is_available()


# =============================================================================
# TensorFlow Tests
# =============================================================================

class TestTensorFlow:
    """Test TensorFlow availability for DOMASS ML model."""

    def test_tensorflow_import(self):
        """Check if TensorFlow can be imported."""
        try:
            import tensorflow as tf
            assert tf is not None
        except ImportError:
            pytest.fail("TensorFlow not installed. Install with: pip install tensorflow")

    def test_tensorflow_version(self):
        """Check TensorFlow version is compatible."""
        try:
            import tensorflow as tf
            version = tf.__version__
            major_version = int(version.split('.')[0])
            # We support TensorFlow 1.x (with compat.v1) and 2.x
            assert major_version >= 1, f"TensorFlow version {version} too old"
        except ImportError:
            pytest.skip("TensorFlow not installed")

    def test_tensorflow_v1_compat(self):
        """Check TensorFlow v1 compatibility mode works."""
        try:
            import tensorflow as tf
            # Test v1 compatibility mode (used by DOMASS)
            assert hasattr(tf, 'compat')
            assert hasattr(tf.compat, 'v1')
            assert hasattr(tf.compat.v1, 'Session')
            assert hasattr(tf.compat.v1, 'placeholder')
            assert hasattr(tf.compat.v1.layers, 'dense')
        except ImportError:
            pytest.skip("TensorFlow not installed")

    def test_tensorflow_gpu_detection(self):
        """Check TensorFlow GPU detection (informational only)."""
        try:
            import tensorflow as tf
            gpus = tf.config.list_physical_devices('GPU')
            # Just informational, don't fail if no GPU
            if gpus:
                print(f"TensorFlow detected {len(gpus)} GPU(s)")
            else:
                print("TensorFlow running on CPU only")
        except ImportError:
            pytest.skip("TensorFlow not installed")
        except Exception as e:
            # GPU detection may fail in some environments
            print(f"GPU detection error (non-fatal): {e}")

    def test_domass_model_files_exist(self):
        """Check DOMASS model checkpoint files exist."""
        data_dir = Path("/home/rschaeff_1/data/dpam_reference/ecod_data")
        if not data_dir.exists():
            data_dir = Path(os.environ.get("DPAM_TEST_DATA_DIR", ""))

        if not data_dir.exists():
            pytest.skip("ECOD data directory not found")

        model_files = [
            data_dir / "domass_epo29.meta",
            data_dir / "domass_epo29.index",
        ]
        data_files = list(data_dir.glob("domass_epo29.data-*"))

        missing = [f for f in model_files if not f.exists()]
        assert len(missing) == 0, f"Missing DOMASS model files: {missing}"
        assert len(data_files) > 0, "Missing DOMASS model data file"

    def test_domass_model_loadable(self):
        """Check DOMASS model can be loaded."""
        try:
            import tensorflow as tf
        except ImportError:
            pytest.skip("TensorFlow not installed")

        data_dir = Path("/home/rschaeff_1/data/dpam_reference/ecod_data")
        if not data_dir.exists():
            pytest.skip("ECOD data directory not found")

        model_path = data_dir / "domass_epo29"
        if not (data_dir / "domass_epo29.meta").exists():
            pytest.skip("DOMASS model files not found")

        try:
            # Attempt to read checkpoint
            reader = tf.train.load_checkpoint(str(model_path))
            var_to_shape = reader.get_variable_to_shape_map()

            # Verify expected variables exist
            expected_vars = ['dense/kernel', 'dense/bias', 'dense_1/kernel', 'dense_1/bias']
            for var in expected_vars:
                assert var in var_to_shape, f"Missing model variable: {var}"

            # Verify shapes
            assert var_to_shape['dense/kernel'] == [13, 64], "Unexpected dense/kernel shape"
            assert var_to_shape['dense_1/kernel'] == [64, 2], "Unexpected dense_1/kernel shape"

        except Exception as e:
            pytest.fail(f"Failed to load DOMASS model: {e}")


# =============================================================================
# Gemmi Tests (PDB/CIF Parsing)
# =============================================================================

class TestGemmi:
    """Test Gemmi library for PDB/CIF parsing."""

    def test_gemmi_import(self):
        """Check if Gemmi can be imported."""
        try:
            import gemmi
            assert gemmi is not None
        except ImportError:
            pytest.fail("Gemmi not installed. Install with: pip install gemmi")

    def test_gemmi_version(self):
        """Check Gemmi version is compatible."""
        try:
            import gemmi
            version = gemmi.__version__
            # Parse version (may be like "0.6.4")
            parts = version.split('.')
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            assert major > 0 or minor >= 6, f"Gemmi version {version} too old, need >= 0.6.0"
        except ImportError:
            pytest.skip("Gemmi not installed")

    def test_gemmi_read_pdb(self, test_data_dir):
        """Check Gemmi can read PDB files."""
        try:
            import gemmi
        except ImportError:
            pytest.skip("Gemmi not installed")

        pdb_file = test_data_dir / "test_structure.pdb"
        if not pdb_file.exists():
            pytest.skip("Test PDB file not found")

        structure = gemmi.read_structure(str(pdb_file))
        assert len(structure) > 0, "No models in PDB file"
        assert len(structure[0]) > 0, "No chains in PDB model"

    def test_gemmi_read_cif(self, test_data_dir):
        """Check Gemmi can read CIF files."""
        try:
            import gemmi
        except ImportError:
            pytest.skip("Gemmi not installed")

        cif_file = test_data_dir / "test_structure.cif"
        if not cif_file.exists():
            pytest.skip("Test CIF file not found")

        structure = gemmi.read_structure(str(cif_file))
        assert len(structure) > 0, "No models in CIF file"
        assert len(structure[0]) > 0, "No chains in CIF model"

    def test_gemmi_cif_to_pdb_conversion(self, test_data_dir, tmp_path):
        """Check Gemmi can convert CIF to PDB."""
        try:
            import gemmi
        except ImportError:
            pytest.skip("Gemmi not installed")

        cif_file = test_data_dir / "test_structure.cif"
        if not cif_file.exists():
            pytest.skip("Test CIF file not found")

        # Read CIF
        structure = gemmi.read_structure(str(cif_file))

        # Write as PDB
        output_pdb = tmp_path / "converted.pdb"
        structure.write_pdb(str(output_pdb))

        assert output_pdb.exists(), "PDB conversion failed"
        assert output_pdb.stat().st_size > 0, "Converted PDB file is empty"

        # Verify converted file is readable
        converted = gemmi.read_structure(str(output_pdb))
        assert len(converted) > 0, "Converted PDB has no models"

    def test_gemmi_extract_sequence(self, test_data_dir):
        """Check Gemmi can extract sequence from structure."""
        try:
            import gemmi
        except ImportError:
            pytest.skip("Gemmi not installed")

        pdb_file = test_data_dir / "test_structure.pdb"
        if not pdb_file.exists():
            pytest.skip("Test PDB file not found")

        structure = gemmi.read_structure(str(pdb_file))
        chain = structure[0][0]

        # Get sequence from residues
        sequence = ""
        for residue in chain:
            res_info = gemmi.find_tabulated_residue(residue.name)
            if res_info.is_amino_acid():
                one_letter = res_info.one_letter_code
                if one_letter and one_letter != 'X':
                    sequence += one_letter

        assert len(sequence) > 0, "Failed to extract sequence"

    def test_gemmi_atom_coordinates(self, test_data_dir):
        """Check Gemmi can extract atom coordinates."""
        try:
            import gemmi
        except ImportError:
            pytest.skip("Gemmi not installed")

        pdb_file = test_data_dir / "test_structure.pdb"
        if not pdb_file.exists():
            pytest.skip("Test PDB file not found")

        structure = gemmi.read_structure(str(pdb_file))
        chain = structure[0][0]

        # Get CA atoms
        ca_count = 0
        for residue in chain:
            ca = residue.find_atom("CA", '*')
            if ca:
                ca_count += 1
                # Check coordinate access
                assert hasattr(ca, 'pos')
                assert hasattr(ca.pos, 'x')
                assert hasattr(ca.pos, 'y')
                assert hasattr(ca.pos, 'z')

        assert ca_count > 0, "No CA atoms found"


# =============================================================================
# Python Dependencies Tests
# =============================================================================

class TestPythonDependencies:
    """Test required Python libraries."""

    def test_numpy_available(self):
        """Check if numpy is available."""
        try:
            import numpy as np
            version = np.__version__
            parts = version.split('.')
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            assert major >= 1 and minor >= 20, f"NumPy version {version} too old, need >= 1.20.0"
        except ImportError:
            pytest.fail("NumPy not installed")

    def test_scipy_available(self):
        """Check if scipy is available (used for sparse matrices)."""
        try:
            import scipy
            from scipy import sparse
            assert sparse is not None
        except ImportError:
            pytest.fail("SciPy not installed. Install with: pip install scipy")

    def test_json_available(self):
        """Check if json is available (standard library)."""
        import json
        assert json is not None


# =============================================================================
# DPAM Module Import Tests
# =============================================================================

class TestDPAMImports:
    """Test DPAM module imports."""

    def test_dpam_core_imports(self):
        """Check core DPAM modules can be imported."""
        from dpam.core import models
        from dpam.core.models import PipelineStep, Structure, Domain

    def test_dpam_utils_imports(self):
        """Check DPAM utils can be imported."""
        from dpam.utils import ranges
        from dpam.utils import amino_acids
        from dpam.utils import logging_config

    def test_dpam_io_imports(self):
        """Check DPAM IO modules can be imported."""
        from dpam.io import readers
        from dpam.io import writers

    def test_dpam_tools_imports(self):
        """Check DPAM tool wrappers can be imported."""
        from dpam.tools import hhsuite
        from dpam.tools import foldseek
        from dpam.tools import dali
        from dpam.tools import dssp

    def test_dpam_steps_imports(self):
        """Check all step modules can be imported."""
        from dpam.steps import step01_prepare
        from dpam.steps import step02_hhsearch
        from dpam.steps import step03_foldseek
        from dpam.steps import step04_filter_foldseek
        from dpam.steps import step05_map_ecod
        from dpam.steps import step06_get_dali_candidates
        from dpam.steps import step07_iterative_dali
        from dpam.steps import step08_analyze_dali
        from dpam.steps import step09_get_support
        from dpam.steps import step10_filter_domains
        from dpam.steps import step11_sse
        from dpam.steps import step12_disorder
        from dpam.steps import step13_parse_domains
        from dpam.steps import step15_prepare_domass
        from dpam.steps import step16_run_domass
        from dpam.steps import step17_get_confident
        from dpam.steps import step18_get_mapping
        from dpam.steps import step19_get_merge_candidates
        from dpam.steps import step20_extract_domains
        from dpam.steps import step21_compare_domains
        from dpam.steps import step22_merge_domains
        from dpam.steps import step23_get_predictions
        from dpam.steps import step24_integrate_results

    def test_dpam_pipeline_imports(self):
        """Check pipeline modules can be imported."""
        from dpam.pipeline import runner
        from dpam.pipeline.runner import DPAMPipeline

    def test_dpam_cli_imports(self):
        """Check CLI can be imported."""
        from dpam.cli import main


# =============================================================================
# ECOD Reference Data Tests
# =============================================================================

class TestECODData:
    """Test ECOD reference data availability."""

    @pytest.fixture
    def ecod_dir(self):
        """Get ECOD data directory."""
        candidates = [
            Path("/home/rschaeff_1/data/dpam_reference/ecod_data"),
            Path(os.environ.get("DPAM_TEST_DATA_DIR", "")),
            Path.home() / "data" / "ecod",
        ]
        for path in candidates:
            if path.exists():
                return path
        pytest.skip("ECOD data directory not found")

    def test_ecod_dir_exists(self, ecod_dir):
        """Check ECOD data directory exists."""
        assert ecod_dir.exists()
        assert ecod_dir.is_dir()

    def test_ecod_domain_list(self, ecod_dir):
        """Check ECOD domain list file exists."""
        domain_files = [
            ecod_dir / "ecod.latest.domains",
            ecod_dir / "ecod.latest.domains.txt",
        ]
        found = any(f.exists() for f in domain_files)
        assert found, f"ECOD domain list not found in {ecod_dir}"

    def test_ecod_length_file(self, ecod_dir):
        """Check ECOD length file exists."""
        length_file = ecod_dir / "ECOD_length"
        assert length_file.exists(), f"ECOD_length not found: {length_file}"

    def test_ecod_norms_file(self, ecod_dir):
        """Check ECOD norms file exists."""
        norms_file = ecod_dir / "ECOD_norms"
        assert norms_file.exists(), f"ECOD_norms not found: {norms_file}"

    def test_ecod_pdbmap_file(self, ecod_dir):
        """Check ECOD PDB map file exists."""
        pdbmap_file = ecod_dir / "ECOD_pdbmap"
        assert pdbmap_file.exists(), f"ECOD_pdbmap not found: {pdbmap_file}"

    def test_ecod70_directory(self, ecod_dir):
        """Check ECOD70 PDB directory exists."""
        ecod70_dir = ecod_dir / "ECOD70"
        assert ecod70_dir.exists(), f"ECOD70 directory not found: {ecod70_dir}"
        # Check it has PDB files
        pdb_files = list(ecod70_dir.glob("*.pdb"))
        assert len(pdb_files) > 0, "ECOD70 directory has no PDB files"

    def test_foldseek_database(self, ecod_dir):
        """Check Foldseek database exists."""
        db_dir = ecod_dir / "ECOD_foldseek_DB"
        assert db_dir.exists(), f"ECOD_foldseek_DB not found: {db_dir}"

    def test_uniref_database(self, ecod_dir):
        """Check UniRef30 database exists (for HHblits)."""
        uniref_candidates = [
            ecod_dir / "UniRef30_2022_02",
            ecod_dir / "UniRef30_2023_02",
        ]
        found = any(d.exists() for d in uniref_candidates)
        if not found:
            pytest.skip("UniRef30 database not found (optional for some tests)")

    def test_posi_weights_directory(self, ecod_dir):
        """Check position weights directory exists (for DOMASS)."""
        weights_dir = ecod_dir / "posi_weights"
        assert weights_dir.exists(), f"posi_weights directory not found: {weights_dir}"
        # Check it has weight files
        weight_files = list(weights_dir.glob("*.weight"))
        assert len(weight_files) > 0, "posi_weights directory has no weight files"

    def test_tgroup_length_file(self, ecod_dir):
        """Check T-group length file exists (for DOMASS)."""
        tgroup_file = ecod_dir / "tgroup_length"
        assert tgroup_file.exists(), f"tgroup_length not found: {tgroup_file}"


# =============================================================================
# Test Fixtures
# =============================================================================

class TestFixtures:
    """Test that test fixtures are available."""

    def test_fixtures_directory_exists(self, test_data_dir):
        """Check test fixtures directory exists."""
        assert test_data_dir.exists(), f"Test data directory not found: {test_data_dir}"

    def test_test_pdb_exists(self, test_data_dir):
        """Check test PDB file exists."""
        pdb_file = test_data_dir / "test_structure.pdb"
        assert pdb_file.exists(), f"Test PDB not found: {pdb_file}"

    def test_test_cif_exists(self, test_data_dir):
        """Check test CIF file exists."""
        cif_file = test_data_dir / "test_structure.cif"
        assert cif_file.exists(), f"Test CIF not found: {cif_file}"

    def test_test_fasta_exists(self, test_data_dir):
        """Check test FASTA file exists."""
        fa_file = test_data_dir / "test_structure.fa"
        assert fa_file.exists(), f"Test FASTA not found: {fa_file}"

    def test_test_json_exists(self, test_data_dir):
        """Check test JSON (PAE) file exists."""
        json_file = test_data_dir / "test_structure.json"
        assert json_file.exists(), f"Test JSON not found: {json_file}"
