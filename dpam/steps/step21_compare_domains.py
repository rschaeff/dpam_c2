"""
Step 21: Compare Domain Connectivity

Determine if merge candidate domain pairs are structurally connected.
Two domains should merge only if they are either sequence-connected or structure-connected.

Input:
    - step19/{prefix}.result: Merge candidate pairs
    - step14/{prefix}.domains: All parsed domains (for structured residues)
    - step20/{prefix}_{domain}.pdb: Domain PDB files

Output:
    - {prefix}.step21_comparisons: Judgment for each pair (0/1/2)

Connectivity Types:
    - 0: Not connected (reject merge)
    - 1: Sequence-connected (≤5 structured residues apart)
    - 2: Structure-connected (≥9 residue pairs at ≤8Å distance)

Algorithm:
    1. Load all structured residues from step 14
    2. For each merge pair:
        a. Check sequence distance in structured region
        b. If not sequence-connected, check structural interface
        c. Write judgment
"""

from pathlib import Path
from typing import Set, List, Tuple
import logging
import math

from ..utils.ranges import parse_range

logger = logging.getLogger(__name__)


def get_sequence_distance(
    resids_a: Set[int],
    resids_b: Set[int],
    structured_resids: List[int]
) -> bool:
    """
    Check if two domains are connected in sequence space.

    Domains are sequence-connected if any pair of residues (one from each domain)
    are within 5 positions in the structured region.

    Args:
        resids_a: Residue set for domain A
        resids_b: Residue set for domain B
        structured_resids: Ordered list of all structured residues

    Returns:
        True if sequence-connected, False otherwise
    """
    # Map residues to indices in structured region
    resid_to_index = {res: idx for idx, res in enumerate(structured_resids)}

    indices_a = [resid_to_index[res] for res in resids_a if res in resid_to_index]
    indices_b = [resid_to_index[res] for res in resids_b if res in resid_to_index]

    if not indices_a or not indices_b:
        return False

    # Check if any pair is within 5 positions
    for idx_a in indices_a:
        for idx_b in indices_b:
            if abs(idx_a - idx_b) <= 5:
                return True

    return False


def load_atom_coordinates(pdb_file: Path) -> dict:
    """
    Load all atom coordinates from PDB file.

    Args:
        pdb_file: PDB file path

    Returns:
        Dictionary mapping residue ID to list of [x, y, z] coordinates
    """
    resid_to_coords = {}

    with open(pdb_file, 'r') as f:
        for line in f:
            if not line.startswith('ATOM'):
                continue

            try:
                resid = int(line[22:26].strip())
                x = float(line[30:38].strip())
                y = float(line[38:46].strip())
                z = float(line[46:54].strip())

                if resid not in resid_to_coords:
                    resid_to_coords[resid] = []
                resid_to_coords[resid].append([x, y, z])

            except (ValueError, IndexError):
                continue

    return resid_to_coords


def get_structure_distance(
    pdb1: Path,
    pdb2: Path,
    resids_a: Set[int],
    resids_b: Set[int]
) -> int:
    """
    Check if two domains form a structural interface.

    Counts residue pairs where the minimum inter-atomic distance is ≤8Å.

    Args:
        pdb1: PDB file for domain A
        pdb2: PDB file for domain B
        resids_a: Residue set for domain A
        resids_b: Residue set for domain B

    Returns:
        Number of residue pairs with inter-atomic distance ≤8Å
    """
    # Load coordinates from both domains
    coords = {}

    for pdb_file in [pdb1, pdb2]:
        file_coords = load_atom_coordinates(pdb_file)
        coords.update(file_coords)

    # Count interface contacts
    interface_count = 0

    for res_a in resids_a:
        if res_a not in coords:
            continue

        for res_b in resids_b:
            if res_b not in coords:
                continue

            # Find minimum distance between any atoms
            min_dist = float('inf')

            for coord_a in coords[res_a]:
                for coord_b in coords[res_b]:
                    dist = math.sqrt(
                        (coord_a[0] - coord_b[0]) ** 2 +
                        (coord_a[1] - coord_b[1]) ** 2 +
                        (coord_a[2] - coord_b[2]) ** 2
                    )
                    min_dist = min(min_dist, dist)

            if min_dist <= 8.0:
                interface_count += 1

    return interface_count


def run_step21(
    prefix: str,
    working_dir: Path,
    path_resolver=None,
    **kwargs
) -> bool:
    """
    Compare merge candidate domain pairs for connectivity.

    Args:
        prefix: Structure identifier
        working_dir: Working directory containing input/output
        path_resolver: PathResolver instance for sharded output directories
        **kwargs: Additional arguments (unused)

    Returns:
        True if successful, False otherwise
    """
    from dpam.core.path_resolver import PathResolver
    resolver = path_resolver or PathResolver(working_dir, sharded=False)

    logger.info(f"Step 21: Comparing domain connectivity for {prefix}")

    # Input files
    merge_file = resolver.step_dir(19) / f"{prefix}.step19_merge_candidates"
    domains_file = resolver.step_dir(13) / f"{prefix}.step13_domains"
    step20_dir = resolver.step_dir(20)

    # Check inputs
    if not merge_file.exists():
        logger.info(f"No merge candidates found for {prefix}")
        return True

    if not domains_file.exists():
        logger.error(f"Domains file not found: {domains_file}")
        return False

    # Output file
    output_file = resolver.step_dir(21) / f"{prefix}.step21_comparisons"

    # Load all structured residues (ordered)
    structured_resids: List[int] = []
    with open(domains_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue

            parts = line.strip().split('\t')
            if len(parts) < 2:
                continue

            domain_range = parts[1]
            resids = parse_range(domain_range)
            structured_resids.extend(resids)

    # Sort and deduplicate
    structured_resids = sorted(set(structured_resids))
    logger.debug(f"Loaded {len(structured_resids)} structured residues")

    # Process merge pairs
    results: List[str] = []

    with open(merge_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue

            parts = line.strip().split('\t')
            if len(parts) < 4:
                continue

            domain1, range1, domain2, range2 = parts[:4]

            resids_a = set(parse_range(range1))
            resids_b = set(parse_range(range2))

            # Test 1: Sequence proximity
            if get_sequence_distance(resids_a, resids_b, structured_resids):
                judgment = 1
                logger.debug(f"{domain1}-{domain2}: sequence-connected")
            else:
                # Test 2: Structural interface
                pdb1 = step20_dir / f"{prefix}_{domain1}.pdb"
                pdb2 = step20_dir / f"{prefix}_{domain2}.pdb"

                if not pdb1.exists() or not pdb2.exists():
                    logger.warning(f"PDB files missing for {domain1}-{domain2}")
                    judgment = 0
                else:
                    interface_count = get_structure_distance(pdb1, pdb2, resids_a, resids_b)

                    if interface_count >= 9:
                        judgment = 2
                        logger.debug(f"{domain1}-{domain2}: structure-connected ({interface_count} contacts)")
                    else:
                        judgment = 0
                        logger.debug(f"{domain1}-{domain2}: not connected ({interface_count} contacts)")

            results.append(f"{prefix}\t{domain1}\t{domain2}\t{judgment}\t{range1}\t{range2}")

    # Write results
    with open(output_file, 'w') as f:
        f.write("# protein\tdomain1\tdomain2\tjudgment\trange1\trange2\n")
        for result in results:
            f.write(result + '\n')

    logger.info(f"Step 21 complete: {len(results)} pairs compared")

    # Summary statistics
    judgments = [int(r.split('\t')[3]) for r in results]
    seq_conn = judgments.count(1)
    str_conn = judgments.count(2)
    rejected = judgments.count(0)

    logger.info(f"  Sequence-connected: {seq_conn}")
    logger.info(f"  Structure-connected: {str_conn}")
    logger.info(f"  Rejected: {rejected}")

    return True
