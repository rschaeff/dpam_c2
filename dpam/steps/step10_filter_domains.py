"""
Step 10: Filter Good Domains

Filters sequence and structure domain hits by quality criteria:
1. Sequence hits: filter by segment length (>= 5 res, total >= 25 res)
2. Structure hits: apply quality scoring and filter by segment length

Input:
    {prefix}_sequence.result - Filtered sequence hits from step 9
    {prefix}_structure.result - Structure hits with support from step 9

Output:
    {prefix}.goodDomains - High-quality domain hits passing all filters

Author: DPAM v2.0
"""

from pathlib import Path
from typing import List, Tuple

from dpam.core.models import ReferenceData
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.step10')


def filter_segments(
    range_string: str,
    gap_tolerance: int = 10,
    min_segment_length: int = 5,
    min_total_length: int = 25
) -> Tuple[str, int]:
    """
    Filter segments by length criteria.

    Matches v1.0 logic:
    1. Parse range string
    2. Merge segments with gap tolerance
    3. Keep segments >= min_segment_length
    4. Require total >= min_total_length

    Args:
        range_string: Range string (e.g., "10-20,30-40")
        gap_tolerance: Maximum gap to merge segments (default 10)
        min_segment_length: Minimum segment length to keep (default 5)
        min_total_length: Minimum total residues required (default 25)

    Returns:
        Tuple of (filtered_range_string, total_count)
        Returns ("", 0) if doesn't pass filters
    """
    # Parse range to residues and merge with gap tolerance
    filt_segs = []

    for seg_str in range_string.split(','):
        if '-' not in seg_str:
            continue

        start, end = map(int, seg_str.split('-'))

        for res in range(start, end + 1):
            if not filt_segs:
                filt_segs.append([res])
            else:
                if res > filt_segs[-1][-1] + gap_tolerance:
                    filt_segs.append([res])
                else:
                    filt_segs[-1].append(res)

    # Filter segments by length
    filt_seg_strings = []
    total_good_count = 0

    for seg in filt_segs:
        start = seg[0]
        end = seg[-1]
        good_count = end - start + 1

        if good_count >= min_segment_length:
            total_good_count += good_count
            filt_seg_strings.append(f'{start}-{end}')

    # Check total length requirement
    if total_good_count >= min_total_length:
        return ','.join(filt_seg_strings), total_good_count
    else:
        return "", 0


def classify_sequence_support(best_prob: float, best_cov: float) -> str:
    """
    Classify sequence support level.

    Matches v1.0 thresholds exactly.

    Args:
        best_prob: Best sequence probability
        best_cov: Best sequence coverage

    Returns:
        Support level: "superb", "high", "medium", "low", or "no"
    """
    if best_prob >= 95 and best_cov >= 0.6:
        return "superb"
    elif best_prob >= 80 and best_cov >= 0.4:
        return "high"
    elif best_prob >= 50 and best_cov >= 0.3:
        return "medium"
    elif best_prob >= 20 and best_cov >= 0.2:
        return "low"
    else:
        return "no"


def calculate_judge_score(
    rank: float,
    qscore: float,
    ztile: float,
    qtile: float,
    znorm: float,
    best_prob: float,
    best_cov: float
) -> Tuple[int, str]:
    """
    Calculate quality judge score for structure hit.

    Matches v1.0 scoring exactly:
    - +1 if rank < 1.5
    - +1 if qscore > 0.5
    - +1 if ztile < 0.75 (and >= 0)
    - +1 if qtile < 0.75 (and >= 0)
    - +1 if znorm > 0.225
    - +1 if bestprob >= 20 and bestcov >= 0.2 (low)
    - +1 if bestprob >= 50 and bestcov >= 0.3 (medium)
    - +1 if bestprob >= 80 and bestcov >= 0.4 (high)
    - +1 if bestprob >= 95 and bestcov >= 0.6 (superb)

    Args:
        rank: Position rank
        qscore: Q-score
        ztile: Z-score percentile
        qtile: Q-score percentile
        znorm: Normalized z-score
        best_prob: Best sequence probability
        best_cov: Best sequence coverage

    Returns:
        Tuple of (judge_score, seq_support_level)
    """
    judge = 0

    # Structure quality criteria
    if rank < 1.5:
        judge += 1
    if qscore > 0.5:
        judge += 1
    if ztile < 0.75 and ztile >= 0:
        judge += 1
    if qtile < 0.75 and qtile >= 0:
        judge += 1
    if znorm > 0.225:
        judge += 1

    # Sequence support criteria (cumulative)
    seqjudge = 'no'

    if best_prob >= 20 and best_cov >= 0.2:
        judge += 1
        seqjudge = 'low'
    if best_prob >= 50 and best_cov >= 0.3:
        judge += 1
        seqjudge = 'medium'
    if best_prob >= 80 and best_cov >= 0.4:
        judge += 1
        seqjudge = 'high'
    if best_prob >= 95 and best_cov >= 0.6:
        judge += 1
        seqjudge = 'superb'

    return judge, seqjudge


def process_sequence_hits(
    sequence_file: Path,
    prefix: str
) -> List[str]:
    """
    Process and filter sequence hits.

    Args:
        sequence_file: Path to _sequence.result file
        prefix: Structure prefix

    Returns:
        List of output lines for good domains
    """
    results = []

    if not sequence_file.exists():
        logger.warning(f"Sequence file not found: {sequence_file}")
        return results

    with open(sequence_file, 'r') as f:
        for line in f:
            words = line.split()
            if len(words) < 7:
                continue

            # Get query range (column 6, 0-indexed)
            query_range = words[6]

            # Filter segments
            filtered_range, total_count = filter_segments(
                query_range,
                gap_tolerance=10,
                min_segment_length=5,
                min_total_length=25
            )

            if filtered_range:
                # Format: sequence\tprefix\t{cols 0-7}\tfiltered_range
                # Cols 0-7: hitname, ecod_id, hgroup, prob, cov, len, query_range, template_range
                result_line = (
                    f"sequence\t{prefix}\t" +
                    '\t'.join(words[:8]) +
                    f"\t{filtered_range}\n"
                )
                results.append(result_line)

    return results


def process_structure_hits(
    structure_file: Path,
    reference_data: ReferenceData,
    prefix: str
) -> List[str]:
    """
    Process and filter structure hits.

    Args:
        structure_file: Path to _structure.result file
        reference_data: ECOD reference data (for norms)
        prefix: Structure prefix

    Returns:
        List of output lines for good domains
    """
    results = []

    if not structure_file.exists():
        logger.warning(f"Structure file not found: {structure_file}")
        return results

    with open(structure_file, 'r') as f:
        for line in f:
            words = line.split()
            if len(words) < 12:
                continue

            # Parse fields
            hitname = words[0]
            ecodnum = hitname.split('_')[0]
            zscore = float(words[3])
            qscore = float(words[4])
            ztile = float(words[5])
            qtile = float(words[6])
            rank = float(words[7])
            best_prob = float(words[8])
            best_cov = float(words[9])
            query_range = words[10]
            structure_range = words[11]

            # Calculate normalized z-score
            if ecodnum in reference_data.ecod_norms:
                znorm = round(zscore / reference_data.ecod_norms[ecodnum], 2)
            else:
                znorm = 0.0

            # Calculate judge score
            judge, seqjudge = calculate_judge_score(
                rank, qscore, ztile, qtile, znorm,
                best_prob, best_cov
            )

            # Only keep if judge > 0
            if judge > 0:
                # Filter segments
                filtered_range, total_count = filter_segments(
                    query_range,
                    gap_tolerance=10,
                    min_segment_length=5,
                    min_total_length=25
                )

                if filtered_range:
                    # Format: structure\tseqjudge\tprefix\tznorm\t{cols 0-9}\tquery_range\tfiltered_range
                    result_line = (
                        f"structure\t{seqjudge}\t{prefix}\t{znorm}\t" +
                        '\t'.join(words[:10]) +
                        f"\t{query_range}\t{filtered_range}\n"
                    )
                    results.append(result_line)

    return results


def run_step10(
    prefix: str,
    working_dir: Path,
    reference_data: ReferenceData
) -> bool:
    """
    Run step 10: Filter good domains.

    Args:
        prefix: Structure prefix
        working_dir: Working directory
        reference_data: ECOD reference data

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Step 10: Filtering good domains for {prefix}")

    # Input files
    sequence_file = working_dir / f'{prefix}_sequence.result'
    structure_file = working_dir / f'{prefix}_structure.result'

    # Process sequence hits
    logger.info("Processing sequence hits")
    seq_results = process_sequence_hits(sequence_file, prefix)
    logger.info(f"Filtered to {len(seq_results)} sequence domains")

    # Process structure hits
    logger.info("Processing structure hits")
    struct_results = process_structure_hits(structure_file, reference_data, prefix)
    logger.info(f"Filtered to {len(struct_results)} structure domains")

    # Combine results
    all_results = seq_results + struct_results

    # Write output (only if we have results)
    if all_results:
        output_file = working_dir / f'{prefix}.goodDomains'
        logger.info(f"Writing {len(all_results)} good domains to {output_file}")

        with open(output_file, 'w') as f:
            for line in all_results:
                f.write(line)

        logger.info(f"Step 10 complete: {len(seq_results)} sequence + {len(struct_results)} structure domains")
    else:
        logger.warning("No domains passed filters")
        # Don't create output file if no results

    return True
