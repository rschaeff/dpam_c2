"""
Utility functions for DPAM.

Includes amino acid conversions, residue range parsing,
and logging configuration.
"""

from dpam.utils.amino_acids import (
    THREE_TO_ONE,
    ONE_TO_THREE,
    three_to_one,
    one_to_three,
)
from dpam.utils.ranges import (
    residues_to_range,
    range_to_residues,
    filter_segments_by_length,
    merge_overlapping_ranges,
)
from dpam.utils.logging_config import (
    setup_logging,
    get_logger,
    LogContext,
    log_step_start,
    log_step_complete,
    log_step_failed,
)

__all__ = [
    # Amino acids
    "THREE_TO_ONE",
    "ONE_TO_THREE",
    "three_to_one",
    "one_to_three",
    # Ranges
    "residues_to_range",
    "range_to_residues",
    "filter_segments_by_length",
    "merge_overlapping_ranges",
    # Logging
    "setup_logging",
    "get_logger",
    "LogContext",
    "log_step_start",
    "log_step_complete",
    "log_step_failed",
]
