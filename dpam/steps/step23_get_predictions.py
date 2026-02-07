"""
Step 23: Get Predictions

Classify merged domains as "full", "part", or "miss" based on ML probability and template coverage.

Input:
    - {prefix}.step22_merged_domains: Merged domain groups
    - {prefix}.step13_domains: Original parsed domains
    - {prefix}.step16_predictions: ML predictions
    - {prefix}.step18_mappings: Template alignments
    - tgroup_length: Average T-group lengths
    - ECOD_length: Template lengths
    - posi_weights/*.weight: Position-specific weights

Output:
    - {prefix}.step23_predictions: Domain classifications (full/part/miss)

Classification Logic (V1-compatible):
    full:  prob ≥0.85, (weighted_ratio ≥0.66 OR length_ratio ≥0.66) AND both ≥0.33
    part:  prob ≥0.85, (weighted_ratio ≥0.33 OR length_ratio ≥0.33)
    miss:  prob <0.85 OR both ratios <0.33

Algorithm:
    1. Load merged domain groups from step 22
    2. Identify domains not merged
    3. For each final domain (merged or single):
        a. Find all ECOD predictions
        b. Calculate weighted and length-based coverage
        c. Classify based on probability and coverage
    4. Write classifications
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
    """Load position-specific weights for ECOD template."""
    weight_file = weights_dir / f"{ecod_id}.weight"

    if weight_file.exists():
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
        pos_weights = {i: 1.0 for i in range(1, ecod_length + 1)}
        total_weight = float(ecod_length)

    return pos_weights, total_weight


def run_step23(
    prefix: str,
    working_dir: Path,
    data_dir: Path,
    path_resolver=None,
    **kwargs
) -> bool:
    """
    Classify domains as full/part/miss predictions.

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

    logger.info(f"Step 23: Getting predictions for {prefix}")

    # Input files
    merged_file = resolver.step_dir(22) / f"{prefix}.step22_merged_domains"
    domains_file = resolver.step_dir(13) / f"{prefix}.step13_domains"
    predictions_file = resolver.step_dir(16) / f"{prefix}.step16_predictions"
    mappings_file = resolver.step_dir(18) / f"{prefix}.step18_mappings"

    # Check inputs
    for required_file in [domains_file, predictions_file, mappings_file]:
        if not required_file.exists():
            logger.error(f"Required file not found: {required_file}")
            return False

    # Reference data
    tgroup_length_file = data_dir / "tgroup_length"
    ecod_length_file = data_dir / "ECOD_length"
    weights_dir = data_dir / "posi_weights"

    if not tgroup_length_file.exists() or not ecod_length_file.exists():
        logger.error("Missing reference data files")
        return False

    # Load T-group lengths
    tgroup_lengths = {}

    with open(tgroup_length_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                tgroup = parts[0]
                length = float(parts[1])
                tgroup_lengths[tgroup] = length

    # Load ECOD lengths
    ecod_lengths = {}

    with open(ecod_length_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3:
                ecod_id = parts[1]  # Fixed: ECOD ID is in column 1, not 0
                length = int(parts[2])
                ecod_lengths[ecod_id] = length

    # Load merged domains
    merged_domains = []  # [(merged_domain_list, merged_range), ...]
    merged_domain_names = set()

    if merged_file.exists():
        with open(merged_file, 'r') as f:
            for line in f:
                if line.startswith('#'):
                    continue

                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    domain_list = parts[1]
                    merged_range = parts[2]

                    merged_domains.append((domain_list, merged_range))

                    for domain in domain_list.split(','):
                        merged_domain_names.add(domain)

    # Load original domains (identify non-merged)
    all_domains = {}  # domain_name -> range

    with open(domains_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue

            parts = line.strip().split('\t')
            if len(parts) >= 2:
                domain = parts[0]
                domain_range = parts[1]

                if domain not in merged_domain_names:
                    all_domains[domain] = domain_range

    logger.debug(f"Loaded {len(merged_domains)} merged groups, {len(all_domains)} single domains")

    # Load predictions (grouped by domain)
    domain_to_predictions = {}

    with open(predictions_file, 'r') as f:
        for i, line in enumerate(f):
            if i == 0:  # Skip header
                continue

            parts = line.strip().split('\t')
            if len(parts) < 16:
                continue

            try:
                domain = parts[0]
                ecod_id = parts[3]
                tgroup = parts[2]
                dpam_prob = float(parts[4])
                hh_prob = float(parts[5])
                dali_zscore = float(parts[8])

                if domain not in domain_to_predictions:
                    domain_to_predictions[domain] = []

                domain_to_predictions[domain].append({
                    'ecod': ecod_id,
                    'tgroup': tgroup,
                    'dpam_prob': dpam_prob,
                    'hh_prob': hh_prob,
                    'dali_zscore': dali_zscore
                })

            except (ValueError, IndexError):
                continue

    # Load mappings (for coverage calculation)
    domain_ecod_to_mapping = {}  # (domain, ecod) -> (hh_range, dali_range, quality)

    with open(mappings_file, 'r') as f:
        for i, line in enumerate(f):
            if line.startswith('#') or i == 0:
                continue

            parts = line.strip().split('\t')
            if len(parts) >= 8:
                domain = parts[0]
                ecod_id = parts[2]
                quality = parts[5]
                hh_range = parts[6]
                dali_range = parts[7]

                domain_ecod_to_mapping[(domain, ecod_id)] = (hh_range, dali_range, quality)

    # Process domains (merged and single)
    results = []

    # Process merged domains
    for domain_list, merged_range in merged_domains:
        domains_in_group = domain_list.split(',')
        merged_length = len(parse_range(merged_range))

        # Collect all predictions from member domains
        all_preds = []
        for domain in domains_in_group:
            if domain in domain_to_predictions:
                all_preds.extend(domain_to_predictions[domain])

        # Keep best prediction per ECOD
        ecod_to_best = {}
        for pred in all_preds:
            ecod = pred['ecod']
            if ecod not in ecod_to_best:
                ecod_to_best[ecod] = pred
            elif pred['dpam_prob'] > ecod_to_best[ecod]['dpam_prob']:
                ecod_to_best[ecod] = pred

        # V1 logic: Sort merged domain ECODs by prob * domain_length (not just prob)
        # This gives preference to longer domains when probability is similar
        sorted_ecods = sorted(
            ecod_to_best.items(),
            key=lambda x: x[1]['dpam_prob'] * merged_length,
            reverse=True
        )

        # Find best "full" and "part" candidates
        best_full = None
        best_part = None
        best_miss = None

        for ecod, pred in sorted_ecods:
            if ecod not in ecod_lengths:
                continue

            tgroup = pred['tgroup']
            dpam_prob = pred['dpam_prob']
            hh_prob = pred['hh_prob']
            dali_zscore = pred['dali_zscore']

            # Get template residues from mappings and collect qualities
            template_resids = set()
            qualities = []

            for domain in domains_in_group:
                key = (domain, ecod)
                if key in domain_ecod_to_mapping:
                    hh_range, dali_range, quality = domain_ecod_to_mapping[key]
                    qualities.append(quality)

                    # V1 logic: Use DALI only if it covers >50% of HH residues
                    hh_resids = set(parse_range(hh_range)) if hh_range != 'na' else set()
                    dali_resids = set(parse_range(dali_range)) if dali_range != 'na' else set()

                    if len(dali_resids) > len(hh_resids) * 0.5:
                        template_resids.update(dali_resids)
                    else:
                        template_resids.update(hh_resids)

            if not template_resids:
                continue

            # Determine best quality (good > ok > bad)
            if 'good' in qualities:
                quality_value = 'good'
            elif 'ok' in qualities:
                quality_value = 'ok'
            else:
                quality_value = 'bad' if qualities else 'na'

            # Calculate coverage ratios
            ecod_length = ecod_lengths[ecod]
            pos_weights, total_weight = load_position_weights(
                ecod, weights_dir, ecod_length
            )

            covered_weight = sum(pos_weights.get(res, 0.0) for res in template_resids)
            weighted_ratio = covered_weight / total_weight if total_weight > 0 else 0.0

            if tgroup in tgroup_lengths:
                length_ratio = merged_length / tgroup_lengths[tgroup]
            else:
                length_ratio = len(template_resids) / ecod_length

            # Classify using V1 logic:
            # full: (ratio1 >= 0.66 OR ratio2 >= 0.66) AND (ratio1 >= 0.33 AND ratio2 >= 0.33)
            if dpam_prob >= 0.85:
                if (weighted_ratio >= 0.66 or length_ratio >= 0.66):
                    if weighted_ratio >= 0.33 and length_ratio >= 0.33:
                        classification = 'full'
                    else:
                        classification = 'part'
                elif weighted_ratio >= 0.33 or length_ratio >= 0.33:
                    classification = 'part'
                else:
                    classification = 'miss'
            else:
                classification = 'miss'

            # Build candidate tuple
            candidate = (
                classification, domain_list, merged_range, ecod, tgroup,
                dpam_prob, hh_prob, dali_zscore, weighted_ratio, length_ratio, quality_value
            )

            # Keep best candidate of each type
            if classification == 'full' and best_full is None:
                best_full = candidate
            elif classification == 'part' and best_part is None:
                best_part = candidate
            elif best_miss is None:
                best_miss = candidate

        # Output single best match (prefer full > part > miss)
        best_candidate = best_full or best_part or best_miss

        if best_candidate:
            classification, domain_list, merged_range, ecod, tgroup, dpam_prob, hh_prob, dali_zscore, weighted_ratio, length_ratio, quality = best_candidate
            results.append(
                f"{classification}\t{domain_list}\t{merged_range}\t{ecod}\t{tgroup}\t"
                f"{dpam_prob:.3f}\t{hh_prob:.3f}\t{dali_zscore:.3f}\t"
                f"{weighted_ratio:.3f}\t{length_ratio:.3f}\t{quality}"
            )

    # Process single (non-merged) domains
    for domain, domain_range in all_domains.items():
        domain_length = len(parse_range(domain_range))

        if domain not in domain_to_predictions:
            # No predictions for this domain
            results.append(
                f"miss\t{domain}\t{domain_range}\tna\tna\t"
                f"na\tna\tna\tna\tna\tna"
            )
            continue

        # Keep best prediction per ECOD
        ecod_to_best = {}
        for pred in domain_to_predictions[domain]:
            ecod = pred['ecod']
            if ecod not in ecod_to_best:
                ecod_to_best[ecod] = pred
            elif pred['dpam_prob'] > ecod_to_best[ecod]['dpam_prob']:
                ecod_to_best[ecod] = pred

        # Sort ECODs by probability (descending) to prioritize best matches
        sorted_ecods = sorted(
            ecod_to_best.items(),
            key=lambda x: x[1]['dpam_prob'],
            reverse=True
        )

        # Find best "full" and "part" candidates
        best_full = None
        best_part = None
        best_miss = None

        for ecod, pred in sorted_ecods:
            if ecod not in ecod_lengths:
                continue

            tgroup = pred['tgroup']
            dpam_prob = pred['dpam_prob']
            hh_prob = pred['hh_prob']
            dali_zscore = pred['dali_zscore']

            # Get template residues and quality
            key = (domain, ecod)
            template_resids = set()
            quality_value = 'na'

            if key in domain_ecod_to_mapping:
                hh_range, dali_range, quality_value = domain_ecod_to_mapping[key]

                # V1 logic: Use DALI only if it covers >50% of HH residues
                hh_resids = set(parse_range(hh_range)) if hh_range != 'na' else set()
                dali_resids = set(parse_range(dali_range)) if dali_range != 'na' else set()

                if len(dali_resids) > len(hh_resids) * 0.5:
                    template_resids.update(dali_resids)
                else:
                    template_resids.update(hh_resids)

            if not template_resids:
                continue

            # Calculate coverage
            ecod_length = ecod_lengths[ecod]
            pos_weights, total_weight = load_position_weights(
                ecod, weights_dir, ecod_length
            )

            covered_weight = sum(pos_weights.get(res, 0.0) for res in template_resids)
            weighted_ratio = covered_weight / total_weight if total_weight > 0 else 0.0

            if tgroup in tgroup_lengths:
                length_ratio = domain_length / tgroup_lengths[tgroup]
            else:
                length_ratio = len(template_resids) / ecod_length

            # Classify using V1 logic:
            # full: (ratio1 >= 0.66 OR ratio2 >= 0.66) AND (ratio1 >= 0.33 AND ratio2 >= 0.33)
            if dpam_prob >= 0.85:
                if (weighted_ratio >= 0.66 or length_ratio >= 0.66):
                    if weighted_ratio >= 0.33 and length_ratio >= 0.33:
                        classification = 'full'
                    else:
                        classification = 'part'
                elif weighted_ratio >= 0.33 or length_ratio >= 0.33:
                    classification = 'part'
                else:
                    classification = 'miss'
            else:
                classification = 'miss'

            # Build candidate tuple
            candidate = (
                classification, domain, domain_range, ecod, tgroup,
                dpam_prob, hh_prob, dali_zscore, weighted_ratio, length_ratio, quality_value
            )

            # Keep best candidate of each type
            if classification == 'full' and best_full is None:
                best_full = candidate
            elif classification == 'part' and best_part is None:
                best_part = candidate
            elif best_miss is None:
                best_miss = candidate

        # Output single best match (prefer full > part > miss)
        best_candidate = best_full or best_part or best_miss

        if best_candidate:
            classification, domain, domain_range, ecod, tgroup, dpam_prob, hh_prob, dali_zscore, weighted_ratio, length_ratio, quality = best_candidate
            results.append(
                f"{classification}\t{domain}\t{domain_range}\t{ecod}\t{tgroup}\t"
                f"{dpam_prob:.3f}\t{hh_prob:.3f}\t{dali_zscore:.3f}\t"
                f"{weighted_ratio:.3f}\t{length_ratio:.3f}\t{quality}"
            )

    # Write results
    output_file = resolver.step_dir(23) / f"{prefix}.step23_predictions"

    with open(output_file, 'w') as f:
        f.write("# classification\tdomain\trange\tecod\ttgroup\t"
                "dpam_prob\thh_prob\tdali_zscore\tweighted_ratio\tlength_ratio\tquality\n")
        for result in results:
            f.write(result + '\n')

    logger.info(f"Step 23 complete: {len(results)} predictions classified")

    # Summary statistics
    class_counts = {}
    for result in results:
        classification = result.split('\t')[0]
        class_counts[classification] = class_counts.get(classification, 0) + 1

    for classification, count in sorted(class_counts.items()):
        logger.info(f"  {classification}: {count}")

    return True
