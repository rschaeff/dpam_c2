"""
Step 12: Disorder Prediction

Predicts disordered regions based on:
1. SSE assignments (from step 11)
2. PAE matrix (inter-SSE contacts)
3. Good domain residues (from step 10)

Algorithm (exact v1.0/dpam_automatic):
- Find 10-residue sliding windows with:
  - Total inter-SSE contacts <= 30 (PAE < 12, seq separation >= 10)
  - Hit residues <= 5 (residues in good domains)
- Mark all residues in qualifying windows as disordered

Input:
    {prefix}.sse - SSE assignments from step 11
    {prefix}.json - AlphaFold PAE matrix
    {prefix}.goodDomains - Good domains from step 10 (optional)

Output:
    {prefix}.diso - Disordered residue list

Author: DPAM v2.0
Reference: dpam_automatic/step13_get_diso.py
"""

from pathlib import Path
from typing import Set, Dict, List
import json

from dpam.utils.ranges import range_to_residues
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.step12')


def load_sse_assignments(sse_file: Path) -> Dict[int, int]:
    """
    Load SSE assignments from file.

    Args:
        sse_file: Path to .sse file

    Returns:
        Dict mapping residue_id -> sse_id for residues in SSEs
    """
    res2sse = {}

    with open(sse_file, 'r') as f:
        for line in f:
            words = line.split()
            if len(words) >= 3:
                resid = int(words[0])
                sse_id_str = words[2]

                if sse_id_str != 'na':
                    res2sse[resid] = int(sse_id_str)

    return res2sse


def load_good_domain_residues(gooddomains_file: Path) -> Set[int]:
    """
    Load residues from good domains.

    Args:
        gooddomains_file: Path to .goodDomains file

    Returns:
        Set of residue IDs in good domains
    """
    hit_resids = set()

    if not gooddomains_file.exists():
        return hit_resids

    with open(gooddomains_file, 'r') as f:
        for line in f:
            words = line.split()

            if words[0] == 'sequence':
                # Sequence hit: filtered range in column 8
                range_str = words[8]
            elif words[0] == 'structure':
                # Structure hit: filtered range in column 14
                range_str = words[14]
            else:
                continue

            # Parse range to residues
            residues = range_to_residues(range_str)
            hit_resids.update(residues)

    return hit_resids


def load_pae_matrix(json_file: Path) -> Dict[int, Dict[int, float]]:
    """
    Load PAE matrix from AlphaFold JSON file.

    Args:
        json_file: Path to AlphaFold JSON file

    Returns:
        Dict mapping res1 -> res2 -> error
    """
    with open(json_file, 'r') as f:
        # Handle JSON format with outer brackets
        text = f.read()
        if text.startswith('[') and text.endswith(']'):
            text = text[1:-1]

        json_dict = json.loads(text)

    rpair2error = {}

    if 'predicted_aligned_error' in json_dict:
        # Format 1: AlphaFold 2 - 2D array with 'predicted_aligned_error' key
        paes = json_dict['predicted_aligned_error']
        length = len(paes)

        for i in range(length):
            res1 = i + 1
            rpair2error[res1] = {}

            for j in range(length):
                res2 = j + 1
                rpair2error[res1][res2] = paes[i][j]

    elif 'pae' in json_dict:
        # Format 2: AlphaFold 3 - 2D array with 'pae' key
        paes = json_dict['pae']
        length = len(paes)

        for i in range(length):
            res1 = i + 1
            rpair2error[res1] = {}

            for j in range(length):
                res2 = j + 1
                rpair2error[res1][res2] = paes[i][j]

    elif 'distance' in json_dict:
        # Format 2: Sparse list
        resid1s = json_dict['residue1']
        resid2s = json_dict['residue2']
        distances = json_dict['distance']

        for i in range(len(distances)):
            res1 = resid1s[i]
            res2 = resid2s[i]

            if res1 not in rpair2error:
                rpair2error[res1] = {}

            rpair2error[res1][res2] = distances[i]

    else:
        raise ValueError("Unrecognized PAE format")

    return rpair2error


def calculate_inter_sse_contacts(
    length: int,
    rpair2error: Dict[int, Dict[int, float]],
    insses: Set[int],
    res2sse: Dict[int, int]
) -> Dict[int, List[int]]:
    """
    Calculate inter-SSE contacts based on PAE.

    Contact criteria (v1.0/dpam_automatic):
    - Sequence separation >= 10
    - PAE < 12
    - At least one residue in SSE
    - Residues in different SSEs (or one not in SSE)

    Args:
        length: Protein length
        rpair2error: PAE matrix
        insses: Set of residues in SSEs
        res2sse: Mapping of residue -> SSE ID

    Returns:
        Dict mapping residue -> list of contacting residues
    """
    res2contacts = {}

    for i in range(length):
        for j in range(length):
            res1 = i + 1
            res2 = j + 1

            # Check sequence separation (v1.0: >= 10)
            if res1 + 10 > res2:
                continue

            # Check PAE (v1.0: < 12)
            if res1 not in rpair2error or res2 not in rpair2error[res1]:
                continue

            error = rpair2error[res1][res2]
            if error >= 12:
                continue

            # Check if res2 is in SSE
            if res2 in insses:
                # Skip if both in same SSE
                if res1 in insses and res2sse[res1] == res2sse[res2]:
                    continue

                # Add contact for res1
                if res1 not in res2contacts:
                    res2contacts[res1] = []
                res2contacts[res1].append(res2)

            # Check if res1 is in SSE
            if res1 in insses:
                # Skip if both in same SSE
                if res2 in insses and res2sse[res2] == res2sse[res1]:
                    continue

                # Add contact for res2
                if res2 not in res2contacts:
                    res2contacts[res2] = []
                res2contacts[res2].append(res1)

    return res2contacts


def find_disordered_regions(
    length: int,
    res2contacts: Dict[int, List[int]],
    insses: Set[int],
    hit_resids: Set[int]
) -> Set[int]:
    """
    Find disordered regions using sliding window.

    Window criteria (v1.0/dpam_automatic - 10 residues):
    - Total inter-SSE contacts <= 30
    - Hit residues (in good domains) <= 5

    Args:
        length: Protein length
        res2contacts: Inter-SSE contacts per residue
        insses: Residues in SSEs
        hit_resids: Residues in good domains

    Returns:
        Set of disordered residue IDs
    """
    diso_resids = set()

    for start in range(1, length - 9):
        total_contact = 0
        hitres_count = 0

        for res in range(start, start + 10):
            # Count hit residues
            if res in hit_resids:
                hitres_count += 1

            # Count contacts for residues in SSEs
            if res in insses:
                if res in res2contacts:
                    total_contact += len(res2contacts[res])

        # Apply criteria (v1.0: contacts <= 30, hits <= 5)
        if total_contact <= 30 and hitres_count <= 5:
            for res in range(start, start + 10):
                diso_resids.add(res)

    return diso_resids


def run_step12(
    prefix: str,
    working_dir: Path,
    path_resolver=None
) -> bool:
    """
    Run step 12: Predict disordered regions.

    Args:
        prefix: Structure prefix
        working_dir: Working directory
        path_resolver: Optional PathResolver for sharded output directories

    Returns:
        True if successful, False otherwise
    """
    from dpam.core.path_resolver import PathResolver
    resolver = path_resolver or PathResolver(working_dir, sharded=False)

    logger.info(f"Step 12: Predicting disorder for {prefix}")

    # Input files
    sse_file = resolver.step_dir(11) / f'{prefix}.sse'
    json_file = resolver.root / f'{prefix}.json'
    gooddomains_file = resolver.step_dir(10) / f'{prefix}.goodDomains'

    if not sse_file.exists():
        logger.error(f"SSE file not found: {sse_file}")
        return False

    if not json_file.exists():
        logger.error(f"JSON file not found: {json_file}")
        return False

    # Load SSE assignments
    logger.info("Loading SSE assignments")
    res2sse = load_sse_assignments(sse_file)
    insses = set(res2sse.keys())
    logger.info(f"Loaded {len(insses)} residues in SSEs")

    # Load good domain residues
    logger.info("Loading good domain residues")
    hit_resids = load_good_domain_residues(gooddomains_file)
    logger.info(f"Loaded {len(hit_resids)} residues in good domains")

    # Load PAE matrix
    logger.info("Loading PAE matrix")
    rpair2error = load_pae_matrix(json_file)

    # Get protein length from PAE matrix
    length = max(rpair2error.keys())
    logger.info(f"Protein length: {length}")

    # Calculate inter-SSE contacts
    logger.info("Calculating inter-SSE contacts")
    res2contacts = calculate_inter_sse_contacts(
        length, rpair2error, insses, res2sse
    )
    logger.info(f"Calculated contacts for {len(res2contacts)} residues")

    # Find disordered regions
    logger.info("Finding disordered regions (10-residue windows)")
    diso_resids = find_disordered_regions(
        length, res2contacts, insses, hit_resids
    )
    logger.info(f"Identified {len(diso_resids)} disordered residues")

    # Write output
    output_file = resolver.step_dir(12) / f'{prefix}.diso'
    logger.info(f"Writing disorder predictions to {output_file}")

    with open(output_file, 'w') as f:
        for resid in sorted(diso_resids):
            f.write(f'{resid}\n')

    logger.info(f"Step 12 complete: {len(diso_resids)} disordered residues")

    return True
