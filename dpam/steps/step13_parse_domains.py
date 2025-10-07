"""
Step 13: Parse Domains

Final domain parsing using all previous outputs:
1. Calculate probability matrices (PDB distance, PAE, HHsearch, DALI)
2. Initial segmentation (5-residue chunks, exclude disorder)
3. Segment clustering (mean prob > 0.54, iterative merging)
4. Domain refinement (fill gaps, remove overlaps)

Input:
    {prefix}.fa - Sequence
    {prefix}.diso - Disordered residues
    {prefix}.pdb - Structure coordinates
    {prefix}.json - PAE matrix
    {prefix}.goodDomains - High-quality domain hits

Output:
    {prefix}.finalDPAM.domains - Final parsed domains

Author: DPAM v2.0
"""

from pathlib import Path
from typing import Set, Dict, List, Tuple
import json
import math

from dpam.utils.ranges import range_to_residues, residues_to_range
from dpam.io.readers import read_fasta
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.step13')


def get_PDB_prob(dist: float) -> float:
    """
    Convert PDB distance to probability.

    Binned thresholds from v1.0.
    """
    if dist <= 3:
        return 0.95
    elif dist <= 6:
        return 0.94
    elif dist <= 8:
        return 0.88
    elif dist <= 10:
        return 0.84
    elif dist <= 12:
        return 0.79
    elif dist <= 14:
        return 0.74
    elif dist <= 16:
        return 0.69
    elif dist <= 18:
        return 0.64
    elif dist <= 20:
        return 0.59
    elif dist <= 25:
        return 0.51
    elif dist <= 30:
        return 0.43
    elif dist <= 35:
        return 0.38
    elif dist <= 40:
        return 0.34
    elif dist <= 50:
        return 0.28
    elif dist <= 60:
        return 0.23
    elif dist <= 80:
        return 0.18
    elif dist <= 100:
        return 0.14
    elif dist <= 150:
        return 0.1
    elif dist <= 200:
        return 0.08
    else:
        return 0.06


def get_PAE_prob(error: float) -> float:
    """
    Convert PAE error to probability.

    Binned thresholds from v1.0.
    """
    if error <= 1:
        return 0.97
    elif error <= 2:
        return 0.89
    elif error <= 3:
        return 0.83
    elif error <= 4:
        return 0.78
    elif error <= 5:
        return 0.74
    elif error <= 6:
        return 0.7
    elif error <= 7:
        return 0.66
    elif error <= 8:
        return 0.62
    elif error <= 9:
        return 0.59
    elif error <= 10:
        return 0.56
    elif error <= 12:
        return 0.51
    elif error <= 14:
        return 0.46
    elif error <= 16:
        return 0.42
    elif error <= 18:
        return 0.38
    elif error <= 20:
        return 0.35
    elif error <= 22:
        return 0.31
    elif error <= 24:
        return 0.27
    elif error <= 26:
        return 0.23
    elif error <= 28:
        return 0.19
    else:
        return 0.11


def get_HHS_prob(hhpro: float) -> float:
    """
    Convert HHsearch probability to probability.

    Binned thresholds from v1.0.
    """
    if hhpro >= 180:
        return 0.98
    elif hhpro >= 160:
        return 0.96
    elif hhpro >= 140:
        return 0.93
    elif hhpro >= 120:
        return 0.89
    elif hhpro >= 100:
        return 0.85
    elif hhpro >= 90:
        return 0.81
    elif hhpro >= 80:
        return 0.77
    elif hhpro >= 70:
        return 0.72
    elif hhpro >= 60:
        return 0.66
    elif hhpro >= 50:
        return 0.58
    else:
        return 0.5


def get_DALI_prob(daliz: float) -> float:
    """
    Convert DALI z-score to probability.

    Binned thresholds from v1.0.
    """
    if daliz >= 35:
        return 0.98
    elif daliz >= 30:
        return 0.96
    elif daliz >= 25:
        return 0.93
    elif daliz >= 20:
        return 0.89
    elif daliz >= 18:
        return 0.85
    elif daliz >= 16:
        return 0.81
    elif daliz >= 14:
        return 0.77
    elif daliz >= 12:
        return 0.72
    elif daliz >= 10:
        return 0.66
    elif daliz >= 8:
        return 0.61
    elif daliz >= 6:
        return 0.55
    else:
        return 0.5


def load_disorder(diso_file: Path) -> Set[int]:
    """Load disordered residues."""
    diso_resids = set()

    if not diso_file.exists():
        return diso_resids

    with open(diso_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                diso_resids.add(int(line))

    return diso_resids


def load_pae_matrix(json_file: Path) -> Dict[int, Dict[int, float]]:
    """Load PAE matrix from AlphaFold JSON."""
    with open(json_file, 'r') as f:
        text = f.read()
        if text.startswith('[') and text.endswith(']'):
            text = text[1:-1]
        json_dict = json.loads(text)

    rpair2error = {}

    if 'predicted_aligned_error' in json_dict:
        paes = json_dict['predicted_aligned_error']
        length = len(paes)

        for i in range(length):
            res1 = i + 1
            rpair2error[res1] = {}
            for j in range(length):
                res2 = j + 1
                rpair2error[res1][res2] = paes[i][j]

    elif 'distance' in json_dict:
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


def load_pdb_coords(pdb_file: Path) -> Dict[int, List[Tuple[float, float, float]]]:
    """
    Load PDB coordinates.

    Returns dict mapping residue -> list of (x, y, z) atom coords.
    """
    res2coords = {}

    with open(pdb_file, 'r') as f:
        for line in f:
            if not line.startswith('ATOM'):
                continue

            resid = int(line[22:26].strip())
            x = float(line[30:38].strip())
            y = float(line[38:46].strip())
            z = float(line[46:54].strip())

            if resid not in res2coords:
                res2coords[resid] = []
            res2coords[resid].append((x, y, z))

    return res2coords


def calculate_distance(coords1: List[Tuple[float, float, float]],
                      coords2: List[Tuple[float, float, float]]) -> float:
    """Calculate minimum atom-atom distance between two residues."""
    min_dist = float('inf')

    for x1, y1, z1 in coords1:
        for x2, y2, z2 in coords2:
            dist = math.sqrt((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2)
            min_dist = min(min_dist, dist)

    return min_dist


def load_good_domains(gooddomains_file: Path) -> Tuple[Dict[Tuple[int, int], List[float]],
                                                        Dict[Tuple[int, int], List[float]]]:
    """
    Load HHsearch and DALI scores from good domains.

    Returns:
        hhs_scores: Dict mapping (res1, res2) -> list of HHsearch probs
        dali_scores: Dict mapping (res1, res2) -> list of DALI z-scores
    """
    hhs_scores = {}
    dali_scores = {}

    if not gooddomains_file.exists():
        return hhs_scores, dali_scores

    with open(gooddomains_file, 'r') as f:
        for line in f:
            words = line.split()

            if words[0] == 'sequence':
                # Sequence hit: prob in column 5, range in column 8
                prob = float(words[5])
                range_str = words[8]
                resids = list(range_to_residues(range_str))

                # Add HHsearch scores for all pairs
                for i, res1 in enumerate(resids):
                    for res2 in resids[i+1:]:
                        key = (res1, res2)
                        if key not in hhs_scores:
                            hhs_scores[key] = []
                        hhs_scores[key].append(prob)

            elif words[0] == 'structure':
                # Structure hit: zscore in column 7, bestprob in column 12, range in column 14
                zscore = float(words[7])
                bestprob = float(words[12])
                range_str = words[14]
                resids = list(range_to_residues(range_str))

                # Add DALI scores for all pairs
                for i, res1 in enumerate(resids):
                    for res2 in resids[i+1:]:
                        key = (res1, res2)
                        if key not in dali_scores:
                            dali_scores[key] = []
                        dali_scores[key].append(zscore)

                # Add HHsearch scores if sequence support exists
                if bestprob > 0:
                    for i, res1 in enumerate(resids):
                        for res2 in resids[i+1:]:
                            key = (res1, res2)
                            if key not in hhs_scores:
                                hhs_scores[key] = []
                            hhs_scores[key].append(bestprob)

    return hhs_scores, dali_scores


def aggregate_hhs_score(scores: List[float]) -> float:
    """
    Aggregate HHsearch scores.

    If count > 10: max + 100
    Else: max + count*10 - 10
    """
    if not scores:
        return 20.0  # Default

    max_score = max(scores)
    count = len(scores)

    if count > 10:
        return max_score + 100
    else:
        return max_score + count * 10 - 10


def aggregate_dali_score(scores: List[float]) -> float:
    """
    Aggregate DALI scores.

    If count > 5: max + 5
    Else: max + count - 1
    """
    if not scores:
        return 1.0  # Default

    max_score = max(scores)
    count = len(scores)

    if count > 5:
        return max_score + 5
    else:
        return max_score + count - 1


def calculate_probability_matrix(
    length: int,
    res2coords: Dict[int, List[Tuple[float, float, float]]],
    rpair2error: Dict[int, Dict[int, float]],
    hhs_scores: Dict[Tuple[int, int], List[float]],
    dali_scores: Dict[Tuple[int, int], List[float]]
) -> Dict[Tuple[int, int], float]:
    """
    Calculate combined probability matrix.

    Combined: dist^0.1 * pae^0.1 * hhs^0.4 * dali^0.4
    """
    prob_matrix = {}

    for res1 in range(1, length + 1):
        for res2 in range(res1 + 1, length + 1):
            # Calculate distance probability
            if res1 in res2coords and res2 in res2coords:
                dist = calculate_distance(res2coords[res1], res2coords[res2])
                dist_prob = get_PDB_prob(dist)
            else:
                dist_prob = 0.06  # Default for missing coords

            # Calculate PAE probability
            if res1 in rpair2error and res2 in rpair2error[res1]:
                error = rpair2error[res1][res2]
                pae_prob = get_PAE_prob(error)
            else:
                pae_prob = 0.11  # Default for missing PAE

            # Calculate HHsearch probability
            key = (res1, res2)
            if key in hhs_scores:
                hhs_score = aggregate_hhs_score(hhs_scores[key])
            else:
                hhs_score = 20.0  # Default
            hhs_prob = get_HHS_prob(hhs_score)

            # Calculate DALI probability
            if key in dali_scores:
                dali_score = aggregate_dali_score(dali_scores[key])
            else:
                dali_score = 1.0  # Default
            dali_prob = get_DALI_prob(dali_score)

            # Combined probability
            combined = (dist_prob ** 0.1) * (pae_prob ** 0.1) * (hhs_prob ** 0.4) * (dali_prob ** 0.4)
            prob_matrix[(res1, res2)] = combined

    return prob_matrix


def get_prob(prob_matrix: Dict[Tuple[int, int], float], res1: int, res2: int) -> float:
    """Get probability for residue pair (handles ordering)."""
    if res1 == res2:
        return 1.0
    key = (min(res1, res2), max(res1, res2))
    return prob_matrix.get(key, 0.5)


def initial_segmentation(length: int, diso_resids: Set[int]) -> List[List[int]]:
    """
    Create initial 5-residue segments excluding disorder.

    Keep segments with >= 3 residues.
    """
    segments = []

    for start in range(1, length + 1, 5):
        segment = []
        for res in range(start, min(start + 5, length + 1)):
            if res not in diso_resids:
                segment.append(res)

        if len(segment) >= 3:
            segments.append(segment)

    return segments


def calculate_segment_pair_prob(seg1: List[int], seg2: List[int],
                                prob_matrix: Dict[Tuple[int, int], float]) -> float:
    """Calculate mean probability between two segments."""
    total = 0.0
    count = 0

    for res1 in seg1:
        for res2 in seg2:
            total += get_prob(prob_matrix, res1, res2)
            count += 1

    return total / count if count > 0 else 0.0


def merge_segments_by_probability(segments: List[List[int]],
                                  prob_matrix: Dict[Tuple[int, int], float]) -> List[List[int]]:
    """
    Merge segments with mean probability > 0.54.

    Returns merged segments.
    """
    merged = []
    used = set()

    for i, seg1 in enumerate(segments):
        if i in used:
            continue

        cluster = seg1[:]
        used.add(i)

        # Find all segments to merge with seg1
        changed = True
        while changed:
            changed = False
            for j, seg2 in enumerate(segments):
                if j in used:
                    continue

                prob = calculate_segment_pair_prob(cluster, seg2, prob_matrix)
                if prob > 0.54:
                    cluster.extend(seg2)
                    used.add(j)
                    changed = True

        merged.append(sorted(cluster))

    return merged


def calculate_intra_prob(segment: List[int], prob_matrix: Dict[Tuple[int, int], float]) -> float:
    """Calculate mean intra-segment probability."""
    if len(segment) <= 1:
        return 1.0

    total = 0.0
    count = 0

    for i, res1 in enumerate(segment):
        for res2 in segment[i+1:]:
            total += get_prob(prob_matrix, res1, res2)
            count += 1

    return total / count if count > 0 else 0.0


def iterative_clustering(segments: List[List[int]],
                        prob_matrix: Dict[Tuple[int, int], float]) -> List[List[int]]:
    """
    Iteratively merge segments based on intra vs inter probability.

    Merge if: inter_prob * 1.07 >= min(intra1, intra2)
    """
    clusters = [seg[:] for seg in segments]

    changed = True
    while changed:
        changed = False

        # Calculate intra probabilities
        intra_probs = [calculate_intra_prob(c, prob_matrix) for c in clusters]

        # Find best merge candidate
        best_i, best_j = -1, -1
        best_ratio = 0.0

        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                inter_prob = calculate_segment_pair_prob(clusters[i], clusters[j], prob_matrix)
                min_intra = min(intra_probs[i], intra_probs[j])

                if inter_prob * 1.07 >= min_intra:
                    ratio = inter_prob / min_intra if min_intra > 0 else float('inf')
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_i, best_j = i, j

        # Merge if candidate found
        if best_i >= 0:
            merged = sorted(clusters[best_i] + clusters[best_j])
            clusters = [c for idx, c in enumerate(clusters) if idx not in (best_i, best_j)]
            clusters.append(merged)
            changed = True

    return clusters


def fill_gaps(domains: List[List[int]], gap_tolerance: int = 10) -> List[List[int]]:
    """
    Fill gaps <= gap_tolerance between residues in each domain.

    Domain refinement v0 -> v1.
    """
    filled = []

    for domain in domains:
        if not domain:
            continue

        sorted_res = sorted(domain)
        new_domain = [sorted_res[0]]

        for res in sorted_res[1:]:
            # Fill gap if <= tolerance
            if res - new_domain[-1] <= gap_tolerance + 1:
                for fill_res in range(new_domain[-1] + 1, res + 1):
                    if fill_res not in new_domain:
                        new_domain.append(fill_res)
            else:
                new_domain.append(res)

        filled.append(sorted(new_domain))

    return filled


def remove_overlaps(domains: List[List[int]], min_unique: int = 15) -> List[List[int]]:
    """
    Remove overlaps between domains.

    Keep segments with >= min_unique residues not in other domains.
    Domain refinement v1 -> v2.
    """
    # Find all overlapping residues
    all_resids = []
    for domain in domains:
        all_resids.extend(domain)

    overlap_resids = set()
    seen = set()
    for res in all_resids:
        if res in seen:
            overlap_resids.add(res)
        seen.add(res)

    # Remove overlaps from each domain
    cleaned = []
    for domain in domains:
        unique_resids = [res for res in domain if res not in overlap_resids]

        if len(unique_resids) >= min_unique:
            # Keep full domain with overlaps removed
            cleaned.append(unique_resids)

    return cleaned


def filter_by_length(domains: List[List[int]], min_length: int = 20) -> List[List[int]]:
    """Filter domains by minimum length."""
    return [d for d in domains if len(d) >= min_length]


def run_step13(prefix: str, working_dir: Path) -> bool:
    """
    Run step 13: Parse final domains.

    Args:
        prefix: Structure prefix
        working_dir: Working directory

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Step 13: Parsing domains for {prefix}")

    # Input files
    fasta_file = working_dir / f'{prefix}.fa'
    diso_file = working_dir / f'{prefix}.diso'
    pdb_file = working_dir / f'{prefix}.pdb'
    json_file = working_dir / f'{prefix}.json'
    gooddomains_file = working_dir / f'{prefix}.goodDomains'

    # Check required files
    for file in [fasta_file, pdb_file, json_file]:
        if not file.exists():
            logger.error(f"Required file not found: {file}")
            return False

    # Load sequence
    _, sequence = read_fasta(fasta_file)
    length = len(sequence)
    logger.info(f"Protein length: {length}")

    # Load disorder
    logger.info("Loading disorder predictions")
    diso_resids = load_disorder(diso_file)
    logger.info(f"Disordered residues: {len(diso_resids)}")

    # Load PDB coordinates
    logger.info("Loading PDB coordinates")
    res2coords = load_pdb_coords(pdb_file)
    logger.info(f"Loaded coordinates for {len(res2coords)} residues")

    # Load PAE matrix
    logger.info("Loading PAE matrix")
    rpair2error = load_pae_matrix(json_file)

    # Load good domains scores
    logger.info("Loading good domain scores")
    hhs_scores, dali_scores = load_good_domains(gooddomains_file)
    logger.info(f"HHsearch pairs: {len(hhs_scores)}, DALI pairs: {len(dali_scores)}")

    # Calculate probability matrix
    logger.info("Calculating probability matrix")
    prob_matrix = calculate_probability_matrix(
        length, res2coords, rpair2error, hhs_scores, dali_scores
    )
    logger.info(f"Calculated {len(prob_matrix)} residue pair probabilities")

    # Initial segmentation
    logger.info("Creating initial 5-residue segments")
    segments = initial_segmentation(length, diso_resids)
    logger.info(f"Initial segments: {len(segments)}")

    # Merge by probability
    logger.info("Merging segments by probability (threshold > 0.54)")
    merged = merge_segments_by_probability(segments, prob_matrix)
    logger.info(f"Merged to {len(merged)} segments")

    # Iterative clustering
    logger.info("Iterative clustering (intra/inter threshold 1.07)")
    clusters = iterative_clustering(merged, prob_matrix)
    logger.info(f"Clustered to {len(clusters)} domains")

    # Domain refinement v0: filter by length
    domains_v0 = filter_by_length(clusters, min_length=20)
    logger.info(f"Domains v0 (>= 20 residues): {len(domains_v0)}")

    # Domain refinement v1: fill gaps
    domains_v1 = fill_gaps(domains_v0, gap_tolerance=10)
    logger.info(f"Domains v1 (gaps filled): {len(domains_v1)}")

    # Domain refinement v2: remove overlaps
    domains_v2 = remove_overlaps(domains_v1, min_unique=15)
    logger.info(f"Domains v2 (overlaps removed): {len(domains_v2)}")

    # Final filter
    final_domains = filter_by_length(domains_v2, min_length=20)
    logger.info(f"Final domains: {len(final_domains)}")

    # Write output
    output_file = working_dir / f'{prefix}.finalDPAM.domains'
    logger.info(f"Writing final domains to {output_file}")

    with open(output_file, 'w') as f:
        for i, domain in enumerate(final_domains, 1):
            range_str = residues_to_range(sorted(domain))
            f.write(f"D{i}\t{range_str}\n")

    logger.info(f"Step 13 complete: {len(final_domains)} domains parsed")

    return True
