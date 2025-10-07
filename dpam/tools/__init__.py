"""
External tool wrappers for DPAM.

Provides Python interfaces to HHsuite, Foldseek, DALI, and DSSP.
"""

from dpam.tools.base import ExternalTool
from dpam.tools.hhsuite import (
    HHBlits,
    AddSS,
    HHMake,
    HHSearch,
    run_hhsearch_pipeline,
)
from dpam.tools.foldseek import Foldseek
from dpam.tools.dali import DALI, run_iterative_dali
from dpam.tools.dssp import DSSP

__all__ = [
    "ExternalTool",
    "HHBlits",
    "AddSS",
    "HHMake",
    "HHSearch",
    "run_hhsearch_pipeline",
    "Foldseek",
    "DALI",
    "run_iterative_dali",
    "DSSP",
]
