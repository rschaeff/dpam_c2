"""
Step 8: Analyze DALI Results

Analyzes iterative DALI structural alignments by:
1. Loading DALI hits from step 7
2. Calculating weighted alignment scores (q-score)
3. Computing percentiles (z-tile, q-tile)
4. Ranking positions by family diversity
5. Writing analyzed results

Input:
    {prefix}_iterativdDali_hits - DALI alignment results

Output:
    {prefix}_good_hits - Analyzed hits with scores and rankings

Author: DPAM v2.0
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
import numpy as np

from dpam.core.models import DALIAlignment, ReferenceData
from dpam.io.reference_data import load_ecod_weights, load_ecod_domain_info
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.step08')


def get_range(resids: List[int]) -> str:
    """
    Convert list of residue IDs to range string.

    Matches v1.0 behavior exactly.

    Args:
        resids: List of residue IDs (unsorted)

    Returns:
        Range string (e.g., "10-20,25-30")
    """
    if not resids:
        return ""

    # Sort residues
    sorted_resids = sorted(resids)

    # Build segments
    segs = []
    for resid in sorted_resids:
        if not segs:
            segs.append([resid])
        else:
            if resid > segs[-1][-1] + 1:
                # New segment
                segs.append([resid])
            else:
                # Continue segment
                segs[-1].append(resid)

    # Convert to range strings
    ranges = []
    for seg in segs:
        ranges.append(f'{seg[0]}-{seg[-1]}')

    return ','.join(ranges)


def parse_dali_hits_file(hits_file: Path) -> List[Tuple[str, float, List[Tuple[int, int]]]]:
    """
    Parse DALI hits file from step 7.

    Format:
        >{hitname}\t{zscore}\t{n_aligned}\t{q_len}\t{t_len}
        {query_resid}\t{template_resid}
        ...

    Args:
        hits_file: Path to _iterativdDali_hits file

    Returns:
        List of (hitname, zscore, alignments)
        where alignments = [(query_resid, template_resid), ...]
    """
    hits = []

    with open(hits_file, 'r') as f:
        hitname = ''
        zscore = 0.0
        maps = []

        for line in f:
            if line.startswith('>'):
                # Save previous hit
                if hitname and maps:
                    hits.append((hitname, zscore, maps))

                # Parse header
                words = line[1:].split()
                hitname = words[0]
                zscore = float(words[1])
                maps = []
            else:
                # Parse alignment line
                words = line.split()
                if len(words) >= 2:
                    pres = int(words[0])
                    eres = int(words[1])
                    maps.append((pres, eres))

        # Save last hit
        if hitname and maps:
            hits.append((hitname, zscore, maps))

    return hits


def calculate_qscore(
    alignments: List[Tuple[int, int]],
    weights: Dict[int, float]
) -> float:
    """
    Calculate weighted alignment q-score.

    Args:
        alignments: List of (query_resid, template_resid) pairs
        weights: Template position -> weight mapping

    Returns:
        Sum of weights for aligned template positions
    """
    qscore = 0.0

    for query_res, template_res in alignments:
        if template_res in weights:
            qscore += weights[template_res]

    return qscore


def calculate_percentile(value: float, values: List[float]) -> float:
    """
    Calculate percentile of value in list.

    Percentile = fraction of values GREATER than this value.
    Matches v1.0 calculation exactly.

    Args:
        value: Value to rank
        values: List of all values

    Returns:
        Percentile (0.0 to 1.0)
    """
    if not values:
        return -1.0

    better = 0
    worse = 0

    for other_value in values:
        if other_value > value:
            better += 1
        else:
            worse += 1

    return better / (better + worse)


def analyze_hits(
    raw_hits: List[Tuple[str, float, List[Tuple[int, int]]]],
    reference_data: ReferenceData,
    data_dir: Path
) -> List[Dict]:
    """
    Analyze DALI hits with scores and percentiles.

    Args:
        raw_hits: List of (hitname, zscore, alignments)
        reference_data: ECOD reference data
        data_dir: Path to data directory for loading weights/info

    Returns:
        List of analyzed hits with all scores
    """
    analyzed_hits = []

    for hitname, zscore, alignments in raw_hits:
        # Extract ECOD number
        ecod_num = hitname.split('_')[0]

        # Get metadata
        if ecod_num not in reference_data.ecod_metadata:
            logger.warning(f"ECOD number {ecod_num} not found in metadata")
            continue

        ecod_id, family = reference_data.ecod_metadata[ecod_num]

        # Load weights
        weights = load_ecod_weights(data_dir, ecod_num)

        # Load domain info (historical scores)
        domain_info = load_ecod_domain_info(data_dir, ecod_num)

        # Calculate scores
        if weights and domain_info:
            zscores_hist, qscores_hist = domain_info

            # Calculate q-score
            qscore_raw = calculate_qscore(alignments, weights)
            total_weight = sum(weights.values())
            qscore = qscore_raw / total_weight if total_weight > 0 else 0.0

            # Calculate percentiles
            ztile = calculate_percentile(zscore, zscores_hist)
            qtile = calculate_percentile(qscore, qscores_hist)

            analyzed_hits.append({
                'hitname': hitname,
                'ecod_num': ecod_num,
                'ecod_id': ecod_id,
                'family': family,
                'zscore': zscore,
                'qscore': qscore,
                'ztile': ztile,
                'qtile': qtile,
                'alignments': alignments
            })
        else:
            # No weights/info available
            analyzed_hits.append({
                'hitname': hitname,
                'ecod_num': ecod_num,
                'ecod_id': ecod_id,
                'family': family,
                'zscore': zscore,
                'qscore': -1.0,
                'ztile': -1.0,
                'qtile': -1.0,
                'alignments': alignments
            })

    return analyzed_hits


def calculate_ranks_and_ranges(analyzed_hits: List[Dict]) -> List[Dict]:
    """
    Calculate position ranks and ranges for all hits.

    Rank = average number of families seen at each aligned position
    (calculated incrementally as hits are processed in z-score order)

    Args:
        analyzed_hits: List of hits with scores

    Returns:
        Same list with rank and range fields added
    """
    # Sort by z-score (descending) - matches v1.0
    analyzed_hits.sort(key=lambda x: x['zscore'], reverse=True)

    # Track families per position
    posi2fams: Dict[int, Set[str]] = {}

    final_hits = []

    for hit in analyzed_hits:
        family = hit['family']
        alignments = hit['alignments']

        # Extract positions
        qposis = []
        eposis = []
        ranks = []

        for query_res, template_res in alignments:
            qposis.append(query_res)
            eposis.append(template_res)

            # Update family tracking
            if query_res not in posi2fams:
                posi2fams[query_res] = set()
            posi2fams[query_res].add(family)

            # Rank is number of families at this position
            ranks.append(len(posi2fams[query_res]))

        # Calculate average rank
        ave_rank = round(np.mean(ranks), 2) if ranks else 0.0

        # Convert to range strings
        qrange = get_range(qposis)
        erange = get_range(eposis)

        # Add to final hits
        final_hits.append({
            'hitname': hit['hitname'],
            'ecod_num': hit['ecod_num'],
            'ecod_id': hit['ecod_id'],
            'family': hit['family'],
            'zscore': round(hit['zscore'], 2),
            'qscore': round(hit['qscore'], 2),
            'ztile': round(hit['ztile'], 2),
            'qtile': round(hit['qtile'], 2),
            'rank': ave_rank,
            'qrange': qrange,
            'erange': erange
        })

    return final_hits


def write_good_hits(output_file: Path, hits: List[Dict]) -> None:
    """
    Write analyzed hits to output file.

    Format matches v1.0 exactly:
        hitname\tecodnum\tecodkey\thgroup\tzscore\tqscore\tztile\tqtile\trank\tqrange\terange

    Args:
        output_file: Path to output file
        hits: List of analyzed hits
    """
    with open(output_file, 'w') as f:
        # Header
        f.write('hitname\tecodnum\tecodkey\thgroup\tzscore\tqscore\tztile\tqtile\trank\tqrange\terange\n')

        # Data rows
        for hit in hits:
            f.write(
                f"{hit['hitname']}\t"
                f"{hit['ecod_num']}\t"
                f"{hit['ecod_id']}\t"
                f"{hit['family']}\t"
                f"{hit['zscore']}\t"
                f"{hit['qscore']}\t"
                f"{hit['ztile']}\t"
                f"{hit['qtile']}\t"
                f"{hit['rank']}\t"
                f"{hit['qrange']}\t"
                f"{hit['erange']}\n"
            )


def run_step8(
    prefix: str,
    working_dir: Path,
    reference_data: ReferenceData,
    data_dir: Path
) -> bool:
    """
    Run step 8: Analyze DALI results.

    Args:
        prefix: Structure prefix
        working_dir: Working directory
        reference_data: ECOD reference data
        data_dir: Path to data directory

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Step 8: Analyzing DALI results for {prefix}")

    # Input file
    hits_file = working_dir / f'{prefix}_iterativdDali_hits'

    if not hits_file.exists():
        logger.error(f"DALI hits file not found: {hits_file}")
        return False

    # Parse DALI hits
    logger.info(f"Parsing DALI hits from {hits_file}")
    raw_hits = parse_dali_hits_file(hits_file)
    logger.info(f"Parsed {len(raw_hits)} DALI hits")

    if not raw_hits:
        logger.warning("No DALI hits found")
        # Create empty output file
        output_file = working_dir / f'{prefix}_good_hits'
        write_good_hits(output_file, [])
        return True

    # Analyze hits (calculate scores and percentiles)
    logger.info("Calculating scores and percentiles")
    analyzed_hits = analyze_hits(raw_hits, reference_data, data_dir)
    logger.info(f"Analyzed {len(analyzed_hits)} hits")

    # Calculate ranks and ranges
    logger.info("Calculating position ranks and ranges")
    final_hits = calculate_ranks_and_ranges(analyzed_hits)

    # Write output
    output_file = working_dir / f'{prefix}_good_hits'
    logger.info(f"Writing results to {output_file}")
    write_good_hits(output_file, final_hits)

    logger.info(f"Step 8 complete: {len(final_hits)} hits analyzed")
    return True
