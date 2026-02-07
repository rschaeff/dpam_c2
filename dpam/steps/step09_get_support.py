"""
Step 9: Get Sequence and Structure Support

Integrates sequence (HHsearch) and structure (DALI) evidence:
1. Process sequence hits: remove redundant overlaps (≥50% new residues)
2. Process structure hits: calculate sequence support for each DALI hit

Note: Matches original DPAM behavior - NO probability/coverage filtering.
All hits passed to DOMASS ML model which decides evidence strength.

Input:
    {prefix}.map2ecod.result - HHsearch mappings from step 5
    {prefix}_good_hits - Analyzed DALI hits from step 8

Output:
    {prefix}_sequence.result - Filtered sequence hits
    {prefix}_structure.result - Structure hits with sequence support

Author: DPAM v2.0
"""

from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass

from dpam.core.models import ReferenceData
from dpam.utils.ranges import range_to_residues
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.step09')


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


@dataclass
class SequenceHit:
    """Sequence hit from HHsearch mapping"""
    ecod_num: str
    ecod_len: int
    family: str
    probability: float
    query_resids: List[int]
    template_resids: List[int]


def parse_map2ecod_file(
    map_file: Path,
    reference_data: ReferenceData
) -> List[SequenceHit]:
    """
    Parse HHsearch mapping file from step 5.

    Args:
        map_file: Path to .map2ecod.result file
        reference_data: ECOD reference data

    Returns:
        List of sequence hits
    """
    hits = []

    with open(map_file, 'r') as f:
        for line_num, line in enumerate(f):
            if line_num == 0:
                # Skip header
                continue

            words = line.split()
            if len(words) < 13:
                continue

            ecod_num = words[0]
            probability = float(words[2])
            query_range = words[11]
            template_range = words[12]

            # Get ECOD metadata
            if ecod_num not in reference_data.ecod_lengths:
                logger.warning(f"ECOD {ecod_num} not found in lengths")
                continue

            ecod_key, ecod_len = reference_data.ecod_lengths[ecod_num]

            if ecod_num not in reference_data.ecod_metadata:
                logger.warning(f"ECOD {ecod_num} not found in metadata")
                continue

            ecod_id, family = reference_data.ecod_metadata[ecod_num]

            # Parse ranges to residue lists
            query_resids = list(range_to_residues(query_range))
            template_resids = list(range_to_residues(template_range))

            hits.append(SequenceHit(
                ecod_num=ecod_num,
                ecod_len=ecod_len,
                family=family,
                probability=probability,
                query_resids=query_resids,
                template_resids=template_resids
            ))

    return hits


def process_sequence_hits(
    hits: List[SequenceHit],
    reference_data: ReferenceData
) -> Tuple[List[Dict], Dict[str, List]]:
    """
    Filter sequence hits and group by family.

    For each ECOD domain:
    - Sort hits by probability (descending)
    - Keep hits with >= 50% new residues (remove redundancy)
    - NO probability/coverage filter (matches original DPAM)

    Args:
        hits: List of sequence hits
        reference_data: ECOD reference data

    Returns:
        Tuple of (filtered_hits, family_grouped_hits)
    """
    # Group by ECOD domain
    ecod2hits: Dict[str, List[SequenceHit]] = {}

    for hit in hits:
        if hit.ecod_num not in ecod2hits:
            ecod2hits[hit.ecod_num] = []
        ecod2hits[hit.ecod_num].append(hit)

    # Group by family for later use
    fam2hits: Dict[str, List] = {}

    for hit in hits:
        fam = hit.family
        if fam not in fam2hits:
            fam2hits[fam] = []
        fam2hits[fam].append([
            hit.probability,
            hit.ecod_len,
            hit.query_resids,
            hit.template_resids
        ])

    # Process each ECOD domain
    filtered_hits = []

    for ecod_num in sorted(ecod2hits.keys()):
        # Get metadata
        if ecod_num not in reference_data.ecod_metadata:
            continue

        ecod_id, family = reference_data.ecod_metadata[ecod_num]

        # Sort by probability (descending)
        domain_hits = ecod2hits[ecod_num]
        domain_hits.sort(key=lambda x: x.probability, reverse=True)

        # Track covered residues
        covered_resids: Set[int] = set()
        hit_count = 0

        for hit in domain_hits:
            # Calculate coverage
            template_resids_set = set(hit.template_resids)
            coverage = len(template_resids_set) / hit.ecod_len

            # Match original DPAM: Keep ALL hits (no probability/coverage filter)
            # Only check for redundancy (50% new residues)
            # DOMASS ML model will decide if evidence is strong enough
            new_resids = template_resids_set.difference(covered_resids)

            if len(new_resids) >= len(template_resids_set) * 0.5:
                hit_count += 1
                covered_resids = covered_resids.union(template_resids_set)

                # Add to filtered hits
                query_range = get_range(hit.query_resids)
                template_range = get_range(hit.template_resids)

                filtered_hits.append({
                    'hitname': f'{ecod_num}_{hit_count}',
                    'ecod_id': ecod_id,
                    'family': family,
                    'probability': hit.probability,
                    'coverage': round(coverage, 2),
                    'ecod_len': hit.ecod_len,
                    'query_range': query_range,
                    'template_range': template_range
                })

    return filtered_hits, fam2hits


def merge_segments_with_gap_tolerance(
    query_range: str,
    gap_tolerance: int = 10
) -> Set[int]:
    """
    Merge query segments with gap tolerance.

    Matches v1.0 logic:
    - Parse range string to residues
    - Merge segments if gap <= gap_tolerance
    - Fill in gaps

    Args:
        query_range: Range string (e.g., "10-20,30-40")
        gap_tolerance: Maximum gap size to merge (default 10)

    Returns:
        Set of residues after merging
    """
    # Parse range to get initial residues
    segments = []

    for seg_str in query_range.split(','):
        if '-' in seg_str:
            start, end = map(int, seg_str.split('-'))
            for res in range(start, end + 1):
                if not segments:
                    segments.append([res])
                else:
                    if res > segments[-1][-1] + gap_tolerance:
                        segments.append([res])
                    else:
                        segments[-1].append(res)

    # Convert segments to residue set (filling gaps)
    resids = set()
    for seg in segments:
        start = seg[0]
        end = seg[-1]
        for res in range(start, end + 1):
            resids.add(res)

    return resids


def calculate_sequence_support(
    structure_hit_family: str,
    structure_hit_resids: Set[int],
    fam2hits: Dict[str, List]
) -> Tuple[float, float]:
    """
    Calculate best sequence probability and coverage for structure hit.

    Args:
        structure_hit_family: Family of structure hit
        structure_hit_resids: Query residues in structure hit (merged)
        fam2hits: Family -> sequence hits mapping

    Returns:
        Tuple of (best_probability, best_coverage)
    """
    if structure_hit_family not in fam2hits:
        return 0.0, 0.0

    good_hits = []

    for seq_hit in fam2hits[structure_hit_family]:
        prob = seq_hit[0]
        template_len = seq_hit[1]
        query_resids = seq_hit[2]
        template_resids = seq_hit[3]

        # Find template residues that align to structure hit query residues
        aligned_template_resids = set()
        for i in range(len(query_resids)):
            if query_resids[i] in structure_hit_resids:
                aligned_template_resids.add(template_resids[i])

        # Calculate coverage
        coverage = len(aligned_template_resids) / template_len
        good_hits.append([prob, coverage])

    if not good_hits:
        return 0.0, 0.0

    # Find best probability
    best_prob = max(hit[0] for hit in good_hits)

    # Find best coverage among hits with probability >= best_prob - 0.1
    best_covs = [
        hit[1] for hit in good_hits
        if hit[0] >= best_prob - 0.1
    ]

    best_cov = round(max(best_covs), 2) if best_covs else 0.0

    return best_prob, best_cov


def process_structure_hits(
    good_hits_file: Path,
    fam2hits: Dict[str, List]
) -> List[Dict]:
    """
    Process DALI hits and calculate sequence support.

    Args:
        good_hits_file: Path to _good_hits file from step 8
        fam2hits: Family -> sequence hits mapping

    Returns:
        List of structure hits with sequence support
    """
    structure_hits = []

    with open(good_hits_file, 'r') as f:
        for line_num, line in enumerate(f):
            if line_num == 0:
                # Skip header
                continue

            words = line.split()
            if len(words) < 11:
                continue

            hitname = words[0]
            ecod_num = words[1]
            ecod_id = words[2]
            family = words[3]
            zscore = words[4]
            qscore = words[5]
            ztile = words[6]
            qtile = words[7]
            rank = words[8]
            query_range = words[9]
            structure_range = words[10]

            # Merge query segments with gap tolerance of 10
            merged_resids = merge_segments_with_gap_tolerance(query_range, gap_tolerance=10)

            # Calculate sequence support
            best_prob, best_cov = calculate_sequence_support(
                family,
                merged_resids,
                fam2hits
            )

            structure_hits.append({
                'hitname': hitname,
                'ecod_id': ecod_id,
                'family': family,
                'zscore': zscore,
                'qscore': qscore,
                'ztile': ztile,
                'qtile': qtile,
                'rank': rank,
                'best_prob': best_prob,
                'best_cov': best_cov,
                'query_range': query_range,
                'structure_range': structure_range
            })

    return structure_hits


def write_sequence_results(output_file: Path, hits: List[Dict]) -> None:
    """
    Write sequence results file.

    Format:
        hitname\tecodid\tfamily\tprobability\tcoverage\tecodlen\tqrange\ttrange

    Args:
        output_file: Path to output file
        hits: List of sequence hits
    """
    with open(output_file, 'w') as f:
        for hit in hits:
            f.write(
                f"{hit['hitname']}\t"
                f"{hit['ecod_id']}\t"
                f"{hit['family']}\t"
                f"{hit['probability']}\t"
                f"{hit['coverage']}\t"
                f"{hit['ecod_len']}\t"
                f"{hit['query_range']}\t"
                f"{hit['template_range']}\n"
            )


def write_structure_results(output_file: Path, hits: List[Dict]) -> None:
    """
    Write structure results file.

    Format:
        hitname\tecodid\tfamily\tzscore\tqscore\tztile\tqtile\trank\tbestprob\tbestcov\tqrange\tsrange

    Args:
        output_file: Path to output file
        hits: List of structure hits
    """
    with open(output_file, 'w') as f:
        for hit in hits:
            f.write(
                f"{hit['hitname']}\t"
                f"{hit['ecod_id']}\t"
                f"{hit['family']}\t"
                f"{hit['zscore']}\t"
                f"{hit['qscore']}\t"
                f"{hit['ztile']}\t"
                f"{hit['qtile']}\t"
                f"{hit['rank']}\t"
                f"{hit['best_prob']}\t"
                f"{hit['best_cov']}\t"
                f"{hit['query_range']}\t"
                f"{hit['structure_range']}\n"
            )


def run_step9(
    prefix: str,
    working_dir: Path,
    reference_data: ReferenceData,
    path_resolver=None
) -> bool:
    """
    Run step 9: Get sequence and structure support.

    Args:
        prefix: Structure prefix
        working_dir: Working directory
        reference_data: ECOD reference data
        path_resolver: Optional PathResolver for sharded output directories

    Returns:
        True if successful, False otherwise
    """
    from dpam.core.path_resolver import PathResolver
    resolver = path_resolver or PathResolver(working_dir, sharded=False)

    logger.info(f"Step 9: Getting sequence and structure support for {prefix}")

    # Input files
    map_file = resolver.step_dir(5) / f'{prefix}.map2ecod.result'
    good_hits_file = resolver.step_dir(8) / f'{prefix}_good_hits'

    # Check map file exists
    if not map_file.exists():
        logger.error(f"Map file not found: {map_file}")
        return False

    # Parse sequence hits
    logger.info("Parsing sequence hits from map2ecod file")
    seq_hits = parse_map2ecod_file(map_file, reference_data)
    logger.info(f"Parsed {len(seq_hits)} sequence hits")

    # Process sequence hits (filter and group by family)
    logger.info("Processing sequence hits")
    filtered_seq_hits, fam2hits = process_sequence_hits(seq_hits, reference_data)
    logger.info(f"Filtered to {len(filtered_seq_hits)} sequence hits")

    # Write sequence results
    seq_output = resolver.step_dir(9) / f'{prefix}_sequence.result'
    logger.info(f"Writing sequence results to {seq_output}")
    write_sequence_results(seq_output, filtered_seq_hits)

    # Process structure hits if available
    if good_hits_file.exists():
        logger.info("Processing structure hits")
        struct_hits = process_structure_hits(good_hits_file, fam2hits)
        logger.info(f"Processed {len(struct_hits)} structure hits")

        # Write structure results
        struct_output = resolver.step_dir(9) / f'{prefix}_structure.result'
        logger.info(f"Writing structure results to {struct_output}")
        write_structure_results(struct_output, struct_hits)
    else:
        logger.warning(f"Good hits file not found: {good_hits_file}")
        logger.info("Skipping structure results (no DALI hits available)")

    logger.info(f"Step 9 complete: {len(filtered_seq_hits)} sequence hits, "
                f"{len(struct_hits) if good_hits_file.exists() else 0} structure hits")

    return True
