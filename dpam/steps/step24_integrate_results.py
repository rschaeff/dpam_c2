"""
Step 24: Integrate Results with SSE Analysis

Refine domain classifications using secondary structure analysis.
Filters out simple topology domains (<3 SSEs) and assigns final quality labels.

Input:
    - step23/{prefix}.predictions: Domain predictions (full/part/miss)
    - step12/{prefix}.sse: Secondary structure elements
    - ecod.latest.domains: ECOD keywords

Output:
    - step24/{prefix}_domains: Per-protein results with SSE counts
    - step24/summary_domains: Combined results for all proteins

Classification Logic:
    miss + <3 SSEs → simple_topology
    miss + ≥3 SSEs → low_confidence
    part + <3 SSEs + high_quality → partial_domain
    part + <3 SSEs + low_quality → simple_topology
    part + ≥3 SSEs → partial_domain
    full + <3 SSEs + high_quality → good_domain
    full + <3 SSEs + low_quality → simple_topology
    full + ≥3 SSEs → good_domain

High quality criteria:
    - HH_prob ≥ 0.95
    - weighted_ratio ≥ 0.8
    - length_ratio ≥ 0.8

Algorithm:
    1. Load SSE data for all proteins
    2. For each domain prediction:
        a. Count helices (≥6 residues) and strands (≥3 residues)
        b. Refine classification based on SSE count
    3. Sort domains by sequence position
    4. Renumber as nD1, nD2, nD3...
    5. Write results
"""

from pathlib import Path
from typing import List, Dict, Set, Tuple
import logging
import statistics

from ..utils.ranges import parse_range

logger = logging.getLogger(__name__)


def count_sse_elements(
    domain_resids: Set[int],
    structured_resids: Set[int],
    resid_to_sse: Dict[int, Tuple[int, str]],
    helix_sses: Set[int],
    strand_sses: Set[int]
) -> Tuple[int, int]:
    """
    Count secondary structure elements in domain.

    Args:
        domain_resids: Residues in domain
        structured_resids: All structured residues
        resid_to_sse: Mapping of residue → (sse_id, sse_type)
        helix_sses: Set of SSE IDs that are helices
        strand_sses: Set of SSE IDs that are strands

    Returns:
        Tuple of (helix_count, strand_count)
    """
    sse_to_count = {}

    for resid in domain_resids:
        if resid in structured_resids:
            sse_id, sse_type = resid_to_sse[resid]

            if sse_id not in sse_to_count:
                sse_to_count[sse_id] = 0
            sse_to_count[sse_id] += 1

    # Count helices with ≥6 residues
    helix_count = sum(
        1 for sse_id, count in sse_to_count.items()
        if sse_id in helix_sses and count >= 6
    )

    # Count strands with ≥3 residues
    strand_count = sum(
        1 for sse_id, count in sse_to_count.items()
        if sse_id in strand_sses and count >= 3
    )

    return helix_count, strand_count


def refine_classification(
    original_class: str,
    sse_count: int,
    hh_prob: float,
    weighted_ratio: float,
    length_ratio: float
) -> str:
    """
    Refine domain classification based on SSE content.

    Args:
        original_class: Original classification (full/part/miss)
        sse_count: Total number of helices + strands
        hh_prob: HHsearch probability
        weighted_ratio: Weighted coverage ratio
        length_ratio: Length coverage ratio

    Returns:
        Refined classification label
    """
    high_quality = (hh_prob >= 0.95 and
                   weighted_ratio >= 0.8 and
                   length_ratio >= 0.8)

    if original_class == 'miss':
        if sse_count < 3:
            return 'simple_topology'
        else:
            return 'low_confidence'

    elif original_class == 'part':
        if sse_count < 3:
            if high_quality:
                return 'partial_domain'
            else:
                return 'simple_topology'
        else:
            return 'partial_domain'

    elif original_class == 'full':
        if sse_count < 3:
            if high_quality:
                return 'good_domain'
            else:
                return 'simple_topology'
        else:
            return 'good_domain'

    else:
        logger.warning(f"Unknown classification: {original_class}")
        return 'low_confidence'


def run_step24(
    prefix: str,
    working_dir: Path,
    data_dir: Path,
    path_resolver=None,
    **kwargs
) -> bool:
    """
    Integrate SSE analysis with domain predictions.

    Args:
        prefix: Structure identifier
        working_dir: Working directory containing input/output
        data_dir: Reference data directory
        path_resolver: PathResolver instance for sharded output directories
        **kwargs: Additional arguments (unused)

    Returns:
        True if successful, False otherwise
    """
    from dpam.core.path_resolver import PathResolver
    resolver = path_resolver or PathResolver(working_dir, sharded=False)

    logger.info(f"Step 24: Integrating SSE analysis for {prefix}")

    # Input files
    predictions_file = resolver.step_dir(23) / f"{prefix}.step23_predictions"
    sse_file = resolver.step_dir(11) / f"{prefix}.sse"

    # Check inputs
    if not predictions_file.exists():
        logger.info(f"No predictions found for {prefix}")
        return True

    if not sse_file.exists():
        logger.error(f"SSE file not found: {sse_file}")
        return False

    # ECOD keywords (optional)
    ecod_domains_file = data_dir / "ecod.latest.domains"
    ecod_keywords = {}

    if ecod_domains_file.exists():
        with open(ecod_domains_file, 'r') as f:
            for line in f:
                if line.startswith('#'):
                    continue

                parts = line.strip().split()
                if len(parts) >= 2:
                    ecod_id = parts[0]
                    keyword = parts[1]
                    ecod_keywords[ecod_id] = keyword
    else:
        logger.warning(f"ECOD keywords file not found: {ecod_domains_file}")

    # Load SSE data
    structured_resids = set()
    resid_to_sse = {}
    helix_sses = set()
    strand_sses = set()

    with open(sse_file, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 4:
                continue

            try:
                resid = int(parts[0])
                sse_id_str = parts[2]

                if sse_id_str == 'na':
                    continue

                sse_id = int(sse_id_str)
                sse_type = parts[3]

                structured_resids.add(resid)
                resid_to_sse[resid] = (sse_id, sse_type)

                if sse_type == 'H':
                    helix_sses.add(sse_id)
                elif sse_type == 'E':
                    strand_sses.add(sse_id)

            except (ValueError, IndexError):
                continue

    logger.debug(f"Loaded {len(structured_resids)} structured residues, "
                f"{len(helix_sses)} helices, {len(strand_sses)} strands")

    # Process predictions
    results = []

    with open(predictions_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue

            parts = line.strip().split('\t')
            if len(parts) < 11:
                continue

            try:
                classification = parts[0]  # full/part/miss
                domain_name = parts[1]
                domain_range = parts[2]
                ecod_num = parts[3]
                tgroup = parts[4]
                dpam_prob = float(parts[5])
                hh_prob_scaled = float(parts[6]) if parts[6] != 'na' else 0.0
                dali_zscore = float(parts[7]) if parts[7] != 'na' else 0.0
                weighted_ratio = float(parts[8]) if parts[8] != 'na' else 0.0
                length_ratio = float(parts[9]) if parts[9] != 'na' else 0.0
                quality = parts[10] if len(parts) > 10 else 'na'

                # Convert HH prob back from scaled format (step 23 multiplies by 10)
                hh_prob = hh_prob_scaled / 10.0

                # Parse domain residues
                domain_resids = set(parse_range(domain_range))

                # Count SSEs
                helix_count, strand_count = count_sse_elements(
                    domain_resids,
                    structured_resids,
                    resid_to_sse,
                    helix_sses,
                    strand_sses
                )

                sse_count = helix_count + strand_count

                # Refine classification
                final_label = refine_classification(
                    classification,
                    sse_count,
                    hh_prob,
                    weighted_ratio,
                    length_ratio
                )

                # Get ECOD keyword
                ecod_key = ecod_keywords.get(ecod_num, 'na')

                # Store result with mean residue for sorting
                mean_resid = statistics.mean(domain_resids)

                results.append({
                    'mean_resid': mean_resid,
                    'domain_range': domain_range,
                    'ecod_num': ecod_num,
                    'ecod_key': ecod_key,
                    'tgroup': tgroup,
                    'dpam_prob': dpam_prob,
                    'hh_prob': hh_prob_scaled,  # Keep scaled for output
                    'dali_zscore': dali_zscore,
                    'weighted_ratio': weighted_ratio,
                    'length_ratio': length_ratio,
                    'final_label': final_label,
                    'helix_count': helix_count,
                    'strand_count': strand_count
                })

            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping malformed line: {e}")
                continue

    if not results:
        logger.info(f"No results to integrate for {prefix}")
        return True

    # Sort by sequence position
    results.sort(key=lambda x: x['mean_resid'])

    # Output directory
    output_dir = resolver.step_dir(24)
    output_dir.mkdir(exist_ok=True)

    # Write per-protein file
    output_file = output_dir / f"{prefix}_domains"

    with open(output_file, 'w') as f:
        f.write("Domain\tRange\tECOD_num\tECOD_key\tT-group\tDPAM_prob\t"
               "HH_prob\tDALI_zscore\tHit_cov\tTgroup_cov\tJudge\tHcount\tScount\n")

        for i, result in enumerate(results, 1):
            f.write(
                f"nD{i}\t{result['domain_range']}\t{result['ecod_num']}\t"
                f"{result['ecod_key']}\t{result['tgroup']}\t"
                f"{result['dpam_prob']:.3f}\t{result['hh_prob']:.1f}\t"
                f"{result['dali_zscore']:.1f}\t{result['weighted_ratio']:.3f}\t"
                f"{result['length_ratio']:.3f}\t{result['final_label']}\t"
                f"{result['helix_count']}\t{result['strand_count']}\n"
            )

    logger.info(f"Step 24 complete: {len(results)} domains integrated")

    # Update the main .finalDPAM.domains file with merged domains
    # Write to resolver.root for backward compatibility
    final_domains_root = resolver.root / f"{prefix}.finalDPAM.domains"
    # Write to results_dir for sharded output
    final_domains_results = resolver.results_dir() / f"{prefix}.finalDPAM.domains"

    domain_lines = []
    for i, result in enumerate(results, 1):
        domain_lines.append(f"nD{i}\t{result['domain_range']}\n")

    with open(final_domains_root, 'w') as f:
        f.writelines(domain_lines)

    with open(final_domains_results, 'w') as f:
        f.writelines(domain_lines)

    logger.info(f"Updated {final_domains_root.name} with {len(results)} domains")

    # Summary statistics
    label_counts = {}
    for result in results:
        label = result['final_label']
        label_counts[label] = label_counts.get(label, 0) + 1

    for label, count in sorted(label_counts.items()):
        logger.info(f"  {label}: {count}")

    return True
