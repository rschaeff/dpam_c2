"""
Step 19: Get Merge Candidates

Identify domain pairs that should potentially be merged based on shared ECOD template coverage.

Input:
    - {prefix}.step18_mappings: Domain-ECOD mappings with template ranges
    - ECOD_length: Template lengths
    - posi_weights/*.weight: Position-specific weights (optional)

Output:
    - {prefix}.step19_merge_candidates: Domain pairs to merge
    - {prefix}.step19_merge_info: Supporting ECOD information (debug)

Merge Criteria:
    1. Shared Template: Both domains hit same ECOD template
    2. High Confidence: Both predictions within 0.1 of their respective best scores
    3. Non-overlapping: Template regions overlap < 25%
    4. Support > Opposition: Supporting ECODs outnumber opposing ECODs

Algorithm:
    1. Load position-specific weights for coverage calculation
    2. Calculate weighted coverage for each domain-ECOD hit
    3. Find domain pairs sharing ECOD templates
    4. Filter by confidence and overlap criteria
    5. Count supporting vs opposing ECODs
    6. Write validated merge candidates
"""

from pathlib import Path
from typing import Dict, Set, List, Tuple
import logging

from ..utils.ranges import parse_range

logger = logging.getLogger(__name__)


def load_position_weights(
    ecod_id: str,
    weights_dir: Path,
    ecod_length: int
) -> Tuple[Dict[int, float], float]:
    """
    Load position-specific weights for ECOD template.

    Args:
        ecod_id: ECOD identifier
        weights_dir: Directory containing weight files
        ecod_length: Length of ECOD template

    Returns:
        Tuple of (position_weights, total_weight)
    """
    weight_file = weights_dir / f"{ecod_id}.weight"

    if weight_file.exists():
        # Load empirical weights
        pos_weights = {}

        with open(weight_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    try:
                        resid = int(parts[0])
                        weight = float(parts[3])
                        pos_weights[resid] = weight
                    except (ValueError, IndexError):
                        continue

        total_weight = sum(pos_weights.values())

    else:
        # Uniform weights if no data available
        pos_weights = {i: 1.0 for i in range(1, ecod_length + 1)}
        total_weight = float(ecod_length)

    return pos_weights, total_weight


def run_step19(
    prefix: str,
    working_dir: Path,
    data_dir: Path,
    **kwargs
) -> bool:
    """
    Identify merge candidate domain pairs.

    Args:
        prefix: Structure identifier
        working_dir: Working directory containing input/output
        data_dir: Reference data directory
        **kwargs: Additional arguments (unused)

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Step 19: Getting merge candidates for {prefix}")

    # Input file
    mappings_file = working_dir / f"{prefix}.step18_mappings"

    if not mappings_file.exists():
        logger.info(f"No mappings found for {prefix}")
        return True

    # Reference data
    ecod_length_file = data_dir / "ECOD_length"
    weights_dir = data_dir / "posi_weights"

    if not ecod_length_file.exists():
        logger.error(f"ECOD length file not found: {ecod_length_file}")
        return False

    # Load ECOD lengths
    ecod_lengths = {}

    with open(ecod_length_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3:
                ecod_id = parts[1]  # Fixed: ECOD ID is in column 1, not 0
                length = int(parts[2])
                ecod_lengths[ecod_id] = length

    logger.debug(f"Loaded {len(ecod_lengths)} ECOD lengths")

    # Load mappings and calculate weighted coverage
    domain_to_range = {}
    domain_to_hits = {}  # domain -> [(ecod, tgroup, prob, coverage, template_resids), ...]
    ecod_to_hits = {}    # ecod -> [(domain, tgroup, prob, template_resids), ...]
    domain_to_best_prob = {}

    with open(mappings_file, 'r') as f:
        for i, line in enumerate(f):
            if line.startswith('#') or i == 0:
                continue

            parts = line.strip().split('\t')
            if len(parts) < 8:
                continue

            try:
                domain = parts[0]
                domain_range = parts[1]
                ecod_id = parts[2]
                tgroup = parts[3]
                prob = float(parts[4])
                quality = parts[5]
                hh_template_range = parts[6]
                dali_template_range = parts[7]

                domain_to_range[domain] = domain_range

                # Track best probability per domain
                if domain not in domain_to_best_prob:
                    domain_to_best_prob[domain] = prob
                else:
                    domain_to_best_prob[domain] = max(domain_to_best_prob[domain], prob)

                # Get template residues (prefer DALI > HHsearch)
                if dali_template_range != 'na':
                    template_resids = set(parse_range(dali_template_range))
                elif hh_template_range != 'na':
                    template_resids = set(parse_range(hh_template_range))
                else:
                    continue  # No template mapping

                # Calculate weighted coverage
                if ecod_id in ecod_lengths:
                    ecod_length = ecod_lengths[ecod_id]
                    pos_weights, total_weight = load_position_weights(
                        ecod_id,
                        weights_dir,
                        ecod_length
                    )

                    covered_weight = sum(
                        pos_weights.get(res, 0.0)
                        for res in template_resids
                    )

                    coverage = covered_weight / total_weight if total_weight > 0 else 0.0

                    # Store hit information
                    if domain not in domain_to_hits:
                        domain_to_hits[domain] = []

                    domain_to_hits[domain].append({
                        'ecod': ecod_id,
                        'tgroup': tgroup,
                        'prob': prob,
                        'coverage': coverage,
                        'template_resids': template_resids
                    })

                    # Track by ECOD
                    if ecod_id not in ecod_to_hits:
                        ecod_to_hits[ecod_id] = []

                    ecod_to_hits[ecod_id].append({
                        'domain': domain,
                        'tgroup': tgroup,
                        'prob': prob,
                        'template_resids': template_resids
                    })

            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping malformed mapping line {i}: {e}")
                continue

    if not ecod_to_hits:
        logger.info(f"No ECOD hits found for {prefix}")
        return True

    logger.debug(f"Loaded {len(domain_to_hits)} domains with hits")

    # Find domain pairs sharing ECOD templates
    merge_candidates = {}  # (domain1, domain2) -> [supporting_ecods]

    for ecod_id, hits in ecod_to_hits.items():
        if len(hits) < 2:
            continue

        # Check all pairs of domains hitting this ECOD
        for i, hit1 in enumerate(hits):
            for hit2 in hits[i+1:]:
                domain1 = hit1['domain']
                domain2 = hit2['domain']
                prob1 = hit1['prob']
                prob2 = hit2['prob']
                tres1 = hit1['template_resids']
                tres2 = hit2['template_resids']

                # Both must have high confidence (within 0.1 of their best)
                if (prob1 + 0.1 < domain_to_best_prob[domain1] or
                    prob2 + 0.1 < domain_to_best_prob[domain2]):
                    continue

                # Template regions must cover different areas (< 25% overlap)
                common = tres1 & tres2

                if (len(common) >= 0.25 * len(tres1) or
                    len(common) >= 0.25 * len(tres2)):
                    continue

                # Record as potential merge candidate
                pair = tuple(sorted([domain1, domain2]))

                if pair not in merge_candidates:
                    merge_candidates[pair] = []

                merge_candidates[pair].append(ecod_id)

    logger.debug(f"Found {len(merge_candidates)} potential merge pairs")

    # Filter by support vs opposition
    validated_merges = []
    merge_info = []

    for (domain1, domain2), supporting_ecods in merge_candidates.items():
        support_count = len(supporting_ecods)

        # Count ECODs opposing merge for domain1
        against1 = set()
        if domain1 in domain_to_hits:
            for hit in domain_to_hits[domain1]:
                if (hit['prob'] + 0.1 >= domain_to_best_prob[domain1] and
                    hit['coverage'] > 0.5 and
                    hit['ecod'] not in supporting_ecods):
                    against1.add(hit['ecod'])

        # Count ECODs opposing merge for domain2
        against2 = set()
        if domain2 in domain_to_hits:
            for hit in domain_to_hits[domain2]:
                if (hit['prob'] + 0.1 >= domain_to_best_prob[domain2] and
                    hit['coverage'] > 0.5 and
                    hit['ecod'] not in supporting_ecods):
                    against2.add(hit['ecod'])

        # Merge if support exceeds opposition for at least one domain
        if (support_count > len(against1) or
            support_count > len(against2)):
            range1 = domain_to_range[domain1]
            range2 = domain_to_range[domain2]

            validated_merges.append(f"{domain1}\t{range1}\t{domain2}\t{range2}")
            merge_info.append(f"{domain1},{domain2}\t{','.join(supporting_ecods)}")

    # Write results
    output_file = working_dir / f"{prefix}.step19_merge_candidates"
    info_file = working_dir / f"{prefix}.step19_merge_info"

    if validated_merges:
        with open(output_file, 'w') as f:
            f.write("# domain1\trange1\tdomain2\trange2\n")
            for merge in validated_merges:
                f.write(merge + '\n')

        with open(info_file, 'w') as f:
            for info in merge_info:
                f.write(info + '\n')

        logger.info(f"Step 19 complete: {len(validated_merges)} merge candidates identified")

    else:
        logger.info(f"No validated merge candidates found for {prefix}")

    return True
