"""
Pytest configuration and shared fixtures.
"""

import pytest
import shutil
from pathlib import Path
import os


@pytest.fixture(scope="session")
def test_data_dir():
    """Test data directory containing fixtures."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def test_prefix():
    """Test structure prefix."""
    return "test_structure"


@pytest.fixture(scope="session")
def ecod_data_dir():
    """
    ECOD reference data directory.

    Can be overridden with DPAM_TEST_DATA_DIR environment variable.
    """
    env_dir = os.getenv("DPAM_TEST_DATA_DIR")
    if env_dir:
        data_dir = Path(env_dir)
        if data_dir.exists():
            return data_dir

    # Default location
    default_dir = Path.home() / "data" / "ecod"
    if default_dir.exists():
        return default_dir

    pytest.skip("ECOD data directory not found. Set DPAM_TEST_DATA_DIR environment variable.")


@pytest.fixture(scope="function")
def working_dir(tmp_path):
    """Temporary working directory for each test."""
    work_dir = tmp_path / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


@pytest.fixture(scope="session")
def reference_data(ecod_data_dir):
    """
    Load ECOD reference data for tests.

    Skip test if reference data not available.
    """
    try:
        from dpam.io.reference_data import load_ecod_data
        return load_ecod_data(ecod_data_dir)
    except Exception as e:
        pytest.skip(f"Could not load ECOD reference data: {e}")


# Tool availability fixtures (skip tests if tools not available)

@pytest.fixture(scope="session")
def hhsearch_available():
    """Check if hhsearch is available."""
    if shutil.which("hhsearch") is None:
        pytest.skip("hhsearch not available")
    return True


@pytest.fixture(scope="session")
def foldseek_available():
    """Check if foldseek is available."""
    if shutil.which("foldseek") is None:
        pytest.skip("foldseek not available")
    return True


@pytest.fixture(scope="session")
def dali_available():
    """Check if DALI is available."""
    if shutil.which("dali.pl") is None:
        pytest.skip("dali.pl not available")
    return True


@pytest.fixture(scope="session")
def dssp_available():
    """Check if DSSP/mkdssp is available."""
    if shutil.which("mkdssp") is None:
        pytest.skip("mkdssp not available")
    return True


# Fixture to copy test files to working directory

@pytest.fixture(scope="function")
def setup_test_files(test_data_dir, test_prefix, working_dir):
    """
    Copy test fixture files to working directory.

    Returns dict mapping file type to path.
    """
    files = {}

    # Copy all test files if they exist
    file_types = {
        'pdb': f'{test_prefix}.pdb',
        'cif': f'{test_prefix}.cif',
        'fa': f'{test_prefix}.fa',
        'json': f'{test_prefix}.json',
    }

    for file_type, filename in file_types.items():
        src = test_data_dir / filename
        if src.exists():
            dst = working_dir / filename
            shutil.copy(src, dst)
            files[file_type] = dst

    return files
