"""
Utilities for handling residue ranges.

Functions for converting between residue lists and range strings (e.g., "10-50,60-100").
"""

from typing import List, Set


def residues_to_range(
    residues: List[int],
    chain_id: str = "",
    gap_tolerance: int = 0
) -> str:
    """
    Convert list of residue IDs to range string.
    
    Args:
        residues: Sorted list of residue IDs
        chain_id: Optional chain ID prefix
        gap_tolerance: Maximum gap size to bridge (0 = no bridging)
    
    Returns:
        Range string like "10-50,60-100" or "A:10-50,A:60-100"
    
    Examples:
        >>> residues_to_range([1, 2, 3, 5, 6, 7])
        "1-3,5-7"
        >>> residues_to_range([1, 2, 3, 5, 6, 7], chain_id="A")
        "A:1-3,A:5-7"
        >>> residues_to_range([1, 2, 3, 5, 6, 7], gap_tolerance=1)
        "1-7"
    """
    if not residues:
        return ""
    
    residues = sorted(residues)
    segments = []
    current_seg = [residues[0]]
    
    for resid in residues[1:]:
        if resid <= current_seg[-1] + 1 + gap_tolerance:
            current_seg.append(resid)
        else:
            segments.append(current_seg)
            current_seg = [resid]
    
    segments.append(current_seg)
    
    # Format segments
    ranges = []
    for seg in segments:
        if len(seg) == 1:
            range_str = str(seg[0])
        else:
            range_str = f"{seg[0]}-{seg[-1]}"
        
        if chain_id:
            range_str = f"{chain_id}:{range_str}"
        
        ranges.append(range_str)
    
    return ','.join(ranges)


def range_to_residues(range_string: str) -> Set[int]:
    """
    Parse range string into set of residue IDs.

    Args:
        range_string: Range like "10-50,60-100" or "A:10-50,A:60-100"

    Returns:
        Set of residue IDs

    Examples:
        >>> range_to_residues("10-50,60-100")
        {10, 11, ..., 50, 60, 61, ..., 100}
        >>> range_to_residues("A:10-20")
        {10, 11, ..., 20}
    """
    if not range_string:
        return set()

    residues = set()

    for segment in range_string.split(','):
        segment = segment.strip()
        if not segment:
            continue

        # Remove chain ID if present
        if ':' in segment:
            segment = segment.split(':', 1)[1]

        if '-' in segment:
            start, end = segment.split('-')
            residues.update(range(int(start), int(end) + 1))
        else:
            residues.add(int(segment))

    return residues


def filter_segments_by_length(
    residues: List[int],
    min_segment_length: int = 5,
    max_gap: int = 10
) -> List[int]:
    """
    Filter residues by grouping into segments and keeping only long ones.
    
    Args:
        residues: List of residue IDs
        min_segment_length: Minimum segment length to keep
        max_gap: Maximum gap to consider residues in same segment
    
    Returns:
        Filtered list of residues in segments >= min_segment_length
    """
    if not residues:
        return []
    
    residues = sorted(residues)
    segments = []
    current_seg = [residues[0]]
    
    for resid in residues[1:]:
        if resid > current_seg[-1] + max_gap:
            segments.append(current_seg)
            current_seg = [resid]
        else:
            current_seg.append(resid)
    
    segments.append(current_seg)
    
    # Keep only long segments
    filtered = []
    for seg in segments:
        if len(seg) >= min_segment_length:
            filtered.extend(seg)
    
    return filtered


def merge_overlapping_ranges(ranges: List[str]) -> str:
    """
    Merge overlapping or adjacent range strings.

    Args:
        ranges: List of range strings

    Returns:
        Merged range string
    """
    all_residues = set()
    for r in ranges:
        all_residues.update(range_to_residues(r))

    return residues_to_range(sorted(all_residues))


def range_to_residues_list(range_string: str) -> List[int]:
    """
    Parse range string into ordered list of residue IDs.

    Unlike range_to_residues which returns a set, this preserves the order
    of residues as they appear in the alignment. This is critical for
    maintaining position correspondence between query and template alignments.

    Args:
        range_string: Range like "10-50,60-100" or "A:10-50,A:60-100"

    Returns:
        List of residue IDs in order

    Examples:
        >>> range_to_residues_list("10-15,20-22")
        [10, 11, 12, 13, 14, 15, 20, 21, 22]
    """
    if not range_string or range_string == 'na':
        return []

    residues = []

    for segment in range_string.split(','):
        segment = segment.strip()
        if not segment:
            continue

        # Remove chain ID if present
        if ':' in segment:
            segment = segment.split(':', 1)[1]

        if '-' in segment:
            start, end = segment.split('-')
            residues.extend(range(int(start), int(end) + 1))
        else:
            residues.append(int(segment))

    return residues


# Aliases for backward compatibility with v1.0 code
parse_range = range_to_residues
format_range = residues_to_range
