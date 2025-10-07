"""
DPAM - Domain Parser for AlphaFold Models

A modern reimplementation of the DPAM pipeline for identifying structural
domains in AlphaFold predicted structures.
"""

__version__ = "2.0.0"
__author__ = "DPAM Development Team"

from dpam.core.models import (
    Structure,
    Domain,
    SequenceHit,
    StructureHit,
    PAEMatrix,
    SecondaryStructure,
)

__all__ = [
    "Structure",
    "Domain",
    "SequenceHit",
    "StructureHit",
    "PAEMatrix",
    "SecondaryStructure",
]
