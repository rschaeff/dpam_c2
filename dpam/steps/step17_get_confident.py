"""
Step 17: Filter Confident Predictions

Filter ML predictions by probability threshold and assign quality labels
based on T-group and H-group consistency.

Input:
    - {prefix}.step16_predictions: ML predictions with probabilities

Output:
    - {prefix}.step17_confident_predictions: High-confidence predictions with quality labels

Quality Labels:
    - good: Single T-group above threshold (unambiguous classification)
    - ok: Multiple T-groups but same H-group (family-level consensus)
    - bad: Multiple conflicting H-groups (ambiguous)

Filtering Rules:
    1. Minimum probability: 0.6
    2. T-group similarity window: 0.05 (if prob ≥ best_prob - 0.05)
    3. Quality based on hierarchical agreement

Algorithm:
    1. Load predictions from step 16
    2. Group predictions by domain
    3. For each domain:
        a. Find best probability per T-group
        b. Identify similar T-groups (within 0.05 of max)
        c. Extract H-groups from similar T-groups
        d. Assign quality label based on uniqueness
    4. Write high-confidence predictions (prob ≥ 0.6)
"""

from pathlib import Path
from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)


def run_step17(
    prefix: str,
    working_dir: Path,
    **kwargs
) -> bool:
    """
    Filter confident predictions and assign quality labels.

    Args:
        prefix: Structure identifier
        working_dir: Working directory containing input/output
        **kwargs: Additional arguments (unused)

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Step 17: Filtering confident predictions for {prefix}")

    # Input file
    predictions_file = working_dir / f"{prefix}.step16_predictions"

    if not predictions_file.exists():
        logger.info(f"No predictions found for {prefix}")
        return True

    # Load predictions grouped by domain
    domain_to_range = {}
    domain_to_predictions = {}

    with open(predictions_file, 'r') as f:
        for i, line in enumerate(f):
            if i == 0:  # Skip header
                continue

            parts = line.strip().split('\t')
            if len(parts) < 5:
                continue

            try:
                domain = parts[0]
                domain_range = parts[1]
                tgroup = parts[2]
                ecod_ref = parts[3]
                prob = float(parts[4])

                domain_to_range[domain] = domain_range

                if domain not in domain_to_predictions:
                    domain_to_predictions[domain] = []

                domain_to_predictions[domain].append({
                    'tgroup': tgroup,
                    'ecod_ref': ecod_ref,
                    'prob': prob,
                    'line': line.strip()
                })

            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping malformed prediction line {i}: {e}")
                continue

    if not domain_to_predictions:
        logger.info(f"No prediction data found for {prefix}")
        return True

    logger.debug(f"Loaded predictions for {len(domain_to_predictions)} domains")

    # Filter and assign quality labels
    results = []

    for domain in sorted(domain_to_predictions.keys()):
        domain_range = domain_to_range[domain]
        predictions = domain_to_predictions[domain]

        # Find best probability per T-group
        tgroup_to_best_prob = {}

        for pred in predictions:
            tgroup = pred['tgroup']
            prob = pred['prob']

            if tgroup not in tgroup_to_best_prob:
                tgroup_to_best_prob[tgroup] = prob
            else:
                tgroup_to_best_prob[tgroup] = max(tgroup_to_best_prob[tgroup], prob)

        # Sort predictions by probability (descending)
        predictions.sort(key=lambda x: x['prob'], reverse=True)

        # Process high-confidence predictions
        for pred in predictions:
            tgroup = pred['tgroup']
            ecod_ref = pred['ecod_ref']
            prob = pred['prob']

            # Filter by minimum probability
            if prob < 0.6:
                continue

            # Find similar T-groups (within 0.05 of best)
            max_prob = max(tgroup_to_best_prob.values())
            similar_tgroups = set()

            for other_tgroup, other_prob in tgroup_to_best_prob.items():
                if other_prob >= max_prob - 0.05:
                    similar_tgroups.add(other_tgroup)

            # Extract H-groups from similar T-groups
            similar_hgroups = set()
            for similar_tgroup in similar_tgroups:
                # H-group is first two parts of T-group (X.Y from X.Y.Z)
                parts = similar_tgroup.split('.')
                if len(parts) >= 2:
                    hgroup = f"{parts[0]}.{parts[1]}"
                    similar_hgroups.add(hgroup)

            # Assign quality label
            if len(similar_tgroups) == 1:
                quality = 'good'  # Unambiguous T-group
            elif len(similar_hgroups) == 1:
                quality = 'ok'  # Same H-group (family consensus)
            else:
                quality = 'bad'  # Conflicting families

            # Write result
            results.append(f"{domain}\t{domain_range}\t{tgroup}\t{ecod_ref}\t{prob:.4f}\t{quality}")

    # Write confident predictions
    output_file = working_dir / f"{prefix}.step17_confident_predictions"

    if results:
        with open(output_file, 'w') as f:
            f.write("# domain\tdomain_range\ttgroup\tecod_ref\tprob\tquality\n")
            for result in results:
                f.write(result + '\n')

        logger.info(f"Step 17 complete: {len(results)} confident predictions")

        # Summary statistics
        quality_counts = {}
        for result in results:
            quality = result.split('\t')[-1]
            quality_counts[quality] = quality_counts.get(quality, 0) + 1

        for quality, count in sorted(quality_counts.items()):
            logger.info(f"  {quality}: {count}")

    else:
        logger.info(f"No confident predictions found for {prefix}")

    return True
