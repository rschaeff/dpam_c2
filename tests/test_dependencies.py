"""
Test external dependencies and tools.

These tests verify that all required external tools and data are available.
Run these first to fail fast if dependencies are missing.
"""

import pytest
import shutil
import subprocess
from pathlib import Path


# External tool availability tests

def test_hhsearch_available():
    """Check if hhsearch is available in PATH."""
    assert shutil.which("hhsearch") is not None, "hhsearch not found in PATH"


def test_hhsearch_version():
    """Check hhsearch can be executed."""
    result = subprocess.run(
        ["hhsearch", "-h"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "hhsearch failed to execute"


def test_foldseek_available():
    """Check if foldseek is available in PATH."""
    assert shutil.which("foldseek") is not None, "foldseek not found in PATH"


def test_foldseek_version():
    """Check foldseek can be executed."""
    result = subprocess.run(
        ["foldseek", "-h"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "foldseek failed to execute"


def test_dali_available():
    """Check if dali.pl is available in PATH."""
    assert shutil.which("dali.pl") is not None, "dali.pl not found in PATH"


def test_dssp_available():
    """Check if mkdssp is available in PATH."""
    assert shutil.which("mkdssp") is not None, "mkdssp not found in PATH"


def test_dssp_version():
    """Check mkdssp can be executed."""
    result = subprocess.run(
        ["mkdssp", "--version"],
        capture_output=True,
        text=True
    )
    # mkdssp returns version info even on non-zero exit
    assert "DSSP" in result.stdout or "dssp" in result.stdout.lower(), \
        "mkdssp version check failed"


# Python dependencies

def test_numpy_available():
    """Check if numpy is available."""
    try:
        import numpy as np
        assert np.__version__ >= "1.20.0"
    except ImportError:
        pytest.fail("numpy not available")


def test_gemmi_available():
    """Check if gemmi is available."""
    try:
        import gemmi
        assert gemmi.__version__ >= "0.6.0"
    except ImportError:
        pytest.fail("gemmi not available")


# DPAM module imports

def test_dpam_core_imports():
    """Check core DPAM modules can be imported."""
    from dpam.core import models
    from dpam.core.models import PipelineStep, Structure, Domain


def test_dpam_utils_imports():
    """Check DPAM utils can be imported."""
    from dpam.utils import ranges
    from dpam.utils import amino_acids
    from dpam.utils import logging_config


def test_dpam_io_imports():
    """Check DPAM IO modules can be imported."""
    from dpam.io import readers
    from dpam.io import writers


def test_dpam_tools_imports():
    """Check DPAM tool wrappers can be imported."""
    from dpam.tools import hhsuite
    from dpam.tools import foldseek
    from dpam.tools import dali
    from dpam.tools import dssp


def test_dpam_steps_imports():
    """Check all step modules can be imported."""
    from dpam.steps import step01_prepare
    from dpam.steps import step02_hhsearch
    from dpam.steps import step03_foldseek
    from dpam.steps import step04_filter_foldseek
    from dpam.steps import step05_map_ecod
    from dpam.steps import step06_dali_candidates
    from dpam.steps import step07_iterative_dali
    from dpam.steps import step08_analyze_dali
    from dpam.steps import step09_get_support
    from dpam.steps import step10_filter_domains
    from dpam.steps import step11_sse
    from dpam.steps import step12_disorder
    from dpam.steps import step13_parse_domains


def test_dpam_pipeline_imports():
    """Check pipeline modules can be imported."""
    from dpam.pipeline import runner
    from dpam.pipeline.runner import DPAMPipeline


def test_dpam_cli_imports():
    """Check CLI can be imported."""
    from dpam.cli import main


# ECOD reference data tests (marked to allow skipping)

@pytest.mark.requires_ecod
def test_ecod_data_dir_exists(ecod_data_dir):
    """Check ECOD data directory exists."""
    assert ecod_data_dir.exists(), f"ECOD data directory not found: {ecod_data_dir}"
    assert ecod_data_dir.is_dir(), f"ECOD data path is not a directory: {ecod_data_dir}"


@pytest.mark.requires_ecod
def test_ecod_domain_list_exists(ecod_data_dir):
    """Check ECOD domain list file exists."""
    domain_list = ecod_data_dir / "ecod.latest.domains.txt"
    assert domain_list.exists(), f"ECOD domain list not found: {domain_list}"


@pytest.mark.requires_ecod
def test_ecod_can_load_reference_data(reference_data):
    """Check reference data can be loaded."""
    assert reference_data is not None
    assert hasattr(reference_data, 'domain2size')
    assert len(reference_data.domain2size) > 0, "No domains loaded from reference data"


# Test data fixtures

def test_fixtures_directory_exists(test_data_dir):
    """Check test fixtures directory exists."""
    assert test_data_dir.exists(), f"Test data directory not found: {test_data_dir}"


def test_test_prefix_defined(test_prefix):
    """Check test prefix is defined."""
    assert test_prefix is not None
    assert isinstance(test_prefix, str)
    assert len(test_prefix) > 0
