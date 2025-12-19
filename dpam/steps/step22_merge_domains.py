"""
Step 22: Merge Domains via Transitive Closure

Perform actual domain merging using graph clustering to handle multi-domain merge groups.
If domain A merges with B, and B merges with C, then all three (A, B, C) merge into one domain.

Input:
    - {prefix}.step21_comparisons: Validated domain pairs with judgments

Output:
    - {prefix}.step22_merged_domains: Merged domain groups with combined ranges

Algorithm:
    1. Load validated pairs (judgment > 0)
    2. Build merge groups via transitive closure:
        a. Start with each pair as a separate group
        b. Iteratively merge groups that share any domain
        c. Repeat until no more merges occur (convergence)
    3. For each final group:
        a. Combine all residues from member domains
        b. Convert to compact range string
        c. Write result

Example Transitive Closure:
    Input pairs: {A,B}, {B,C}, {D,E}
    Iteration 1: {A,B,C}, {D,E}  (merged {A,B} and {B,C})
    Iteration 2: No change (converged)
    Output: Two merged groups
"""

from pathlib import Path
from typing import Set, List
import logging

from ..utils.ranges import parse_range, format_range

logger = logging.getLogger(__name__)


def transitive_closure(pairs: List[Set[str]]) -> List[Set[str]]:
    """
    Compute transitive closure of domain pairs via iterative merging.

    Args:
        pairs: List of domain pairs (each pair is a set of 2 domain names)

    Returns:
        List of merged groups (each group is a set of domain names)

    Algorithm:
        Repeatedly merge groups that share any member until convergence.
    """
    if not pairs:
        return []

    # Initialize groups from pairs
    groups = [pair.copy() for pair in pairs]

    # Iteratively merge intersecting groups
    while True:
        new_groups = []
        merged = False

        for group in groups:
            # Check if this group intersects any existing new_group
            found_intersection = False

            for new_group in new_groups:
                if group & new_group:  # Set intersection
                    # Merge groups
                    new_group.update(group)
                    found_intersection = True
                    merged = True
                    break

            if not found_intersection:
                # No intersection - add as new group
                new_groups.append(group.copy())

        # Check convergence
        if len(groups) == len(new_groups):
            break

        groups = new_groups

    return groups


def run_step22(
    prefix: str,
    working_dir: Path,
    **kwargs
) -> bool:
    """
    Merge domains via transitive closure.

    Args:
        prefix: Structure identifier
        working_dir: Working directory containing input/output
        **kwargs: Additional arguments (unused)

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Step 22: Merging domains for {prefix}")

    # Input file
    comparison_file = working_dir / f"{prefix}.step21_comparisons"

    if not comparison_file.exists():
        logger.info(f"No comparison results found for {prefix}")
        return True

    # Output file
    output_file = working_dir / f"{prefix}.step22_merged_domains"

    # Load validated merge pairs (judgment > 0)
    domain_to_resids = {}  # Track residue sets for each domain
    merge_pairs: List[Set[str]] = []

    with open(comparison_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue

            parts = line.strip().split('\t')
            if len(parts) < 6:
                continue

            prot, domain1, domain2, judgment, range1, range2 = parts[:6]

            judgment = int(judgment)

            if judgment > 0:  # Connected (either sequence or structure)
                # Store residue sets
                if domain1 not in domain_to_resids:
                    domain_to_resids[domain1] = parse_range(range1)
                if domain2 not in domain_to_resids:
                    domain_to_resids[domain2] = parse_range(range2)

                # Add pair
                merge_pairs.append({domain1, domain2})

    if not merge_pairs:
        logger.info(f"No validated merge pairs for {prefix}")
        return True

    logger.info(f"Processing {len(merge_pairs)} validated pairs")

    # Compute transitive closure
    merged_groups = transitive_closure(merge_pairs)

    logger.info(f"Merged into {len(merged_groups)} groups")

    # Write results
    results = []

    for group in merged_groups:
        # Sort domain names for consistent output
        domain_list = sorted(list(group))

        # Combine all residues
        merged_resids = set()
        for domain in domain_list:
            merged_resids.update(domain_to_resids[domain])

        # Convert to range string
        merged_range = format_range(sorted(merged_resids))

        results.append(f"{prefix}\t{','.join(domain_list)}\t{merged_range}")

        logger.debug(f"Merged group: {','.join(domain_list)} → {len(merged_resids)} residues")

    # Write output
    with open(output_file, 'w') as f:
        f.write("# protein\tmerged_domains\tmerged_range\n")
        for result in results:
            f.write(result + '\n')

    logger.info(f"Step 22 complete: {len(merged_groups)} merged groups")

    # Summary statistics
    group_sizes = [len(group) for group in merged_groups]
    max_size = max(group_sizes) if group_sizes else 0
    avg_size = sum(group_sizes) / len(group_sizes) if group_sizes else 0

    logger.info(f"  Largest group: {max_size} domains")
    logger.info(f"  Average group size: {avg_size:.1f} domains")

    return True
