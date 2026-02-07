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

    Exact v1.0 thresholds (step13_parse_domains.py lines 24-69).
    """
    if dist <= 3:
        return 0.95
    elif dist <= 6:
        return 0.94
    elif dist <= 9:
        return 0.93
    elif dist <= 12:
        return 0.91
    elif dist <= 15:
        return 0.89
    elif dist <= 18:
        return 0.85
    elif dist <= 21:
        return 0.81
    elif dist <= 24:
        return 0.77
    elif dist <= 27:
        return 0.71
    elif dist <= 30:
        return 0.66
    elif dist <= 35:
        return 0.58
    elif dist <= 40:
        return 0.48
    elif dist <= 45:
        return 0.40
    elif dist <= 50:
        return 0.33
    elif dist <= 55:
        return 0.28
    elif dist <= 60:
        return 0.24
    elif dist <= 70:
        return 0.22
    elif dist <= 80:
        return 0.20
    elif dist <= 120:
        return 0.19
    elif dist <= 160:
        return 0.15
    elif dist <= 200:
        return 0.1
    else:
        return 0.06


def get_PAE_prob(error: float) -> float:
    """
    Convert PAE error to probability.

    Exact v1.0 thresholds (step13_parse_domains.py lines 72-115).
    """
    if error <= 1:
        return 0.97
    elif error <= 2:
        return 0.89
    elif error <= 3:
        return 0.77
    elif error <= 4:
        return 0.67
    elif error <= 5:
        return 0.61
    elif error <= 6:
        return 0.57
    elif error <= 7:
        return 0.54
    elif error <= 8:
        return 0.52
    elif error <= 9:
        return 0.50
    elif error <= 10:
        return 0.48
    elif error <= 11:
        return 0.47
    elif error <= 12:
        return 0.45
    elif error <= 14:
        return 0.44
    elif error <= 16:
        return 0.42
    elif error <= 18:
        return 0.41
    elif error <= 20:
        return 0.39
    elif error <= 22:
        return 0.37
    elif error <= 24:
        return 0.32
    elif error <= 26:
        return 0.25
    elif error <= 28:
        return 0.16
    else:
        return 0.11


def get_HHS_prob(hhpro: float) -> float:
    """
    Convert HHsearch probability to probability.

    Exact v1.0 thresholds (step13_parse_domains.py lines 118-135).
    """
    if hhpro >= 180:
        return 0.98
    elif hhpro >= 160:
        return 0.94
    elif hhpro >= 140:
        return 0.92
    elif hhpro >= 120:
        return 0.88
    elif hhpro >= 110:
        return 0.87
    elif hhpro >= 100:
        return 0.81
    elif hhpro >= 50:
        return 0.76
    else:
        return 0.5


def get_DALI_prob(daliz: float) -> float:
    """
    Convert DALI z-score to probability.

    Exact v1.0 thresholds (step14_parse_domains.py lines 138-167).
    """
    if daliz >= 35:
        return 0.95
    elif daliz >= 25:
        return 0.94
    elif daliz >= 20:
        return 0.93
    elif daliz >= 18:
        return 0.9
    elif daliz >= 16:
        return 0.87
    elif daliz >= 14:
        return 0.85
    elif daliz >= 12:
        return 0.8
    elif daliz >= 11:
        return 0.77
    elif daliz >= 10:
        return 0.74
    elif daliz >= 9:
        return 0.71
    elif daliz >= 8:
        return 0.68
    elif daliz >= 7:
        return 0.63
    elif daliz >= 6:
        return 0.60
    elif daliz >= 5:
        return 0.57
    elif daliz >= 4:
        return 0.54
    elif daliz >= 3:
        return 0.53
    elif daliz >= 2:
        return 0.52
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
        # AlphaFold 2 format
        paes = json_dict['predicted_aligned_error']
        length = len(paes)

        for i in range(length):
            res1 = i + 1
            rpair2error[res1] = {}
            for j in range(length):
                res2 = j + 1
                rpair2error[res1][res2] = paes[i][j]

    elif 'pae' in json_dict:
        # AlphaFold 3 format
        paes = json_dict['pae']
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

    v1.0-compatible: No T-group tracking (lines 279-344).

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
                # Structure hit: zscore in column 7, range in column 14
                zscore = float(words[7])
                range_str = words[14]
                resids = list(range_to_residues(range_str))

                # Add DALI scores for all pairs
                for i, res1 in enumerate(resids):
                    for res2 in resids[i+1:]:
                        key = (res1, res2)
                        if key not in dali_scores:
                            dali_scores[key] = []
                        dali_scores[key].append(zscore)

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

    Combined: (dist * pae * hhs * dali) ^ 0.25 (geometric mean, v1.0 formula)

    CRITICAL (matches v1.0):
    1. Aggregate HHS/DALI scores from goodDomains
    2. Fill in DEFAULT values (HHS=20, DALI=1) for ALL residue pairs
    3. Calculate probability ONLY for pairs where PDB distance and PAE exist

    This ensures the check for "all four sources exist" always passes for HHS/DALI,
    making the real constraint just PDB distance + PAE availability.
    """
    # Step 1: Aggregate scores for pairs that have data
    aggregated_hhs = {}
    for key, scores in hhs_scores.items():
        aggregated_hhs[key] = aggregate_hhs_score(scores)

    aggregated_dali = {}
    for key, scores in dali_scores.items():
        aggregated_dali[key] = aggregate_dali_score(scores)

    # Step 2: Fill in DEFAULT values for ALL pairs (v1.0 lines 366-401)
    # This is the CRITICAL difference - v1.0 ensures HHS and DALI exist for ALL pairs
    for res1 in range(1, length + 1):
        for res2 in range(res1 + 1, length + 1):
            key = (res1, res2)
            if key not in aggregated_hhs:
                aggregated_hhs[key] = 20.0  # Default HHS score
            if key not in aggregated_dali:
                aggregated_dali[key] = 1.0   # Default DALI score

    # Step 3: Calculate probabilities for pairs where PDB distance and PAE exist
    prob_matrix = {}
    for res1 in range(1, length + 1):
        for res2 in range(res1 + 1, length + 1):
            # v1.0: HHS and DALI now ALWAYS exist (filled with defaults above)
            # Real check is only: does PDB distance and PAE exist?
            has_dist = (res1 in res2coords and res2 in res2coords)
            has_pae = (res1 in rpair2error and res2 in rpair2error[res1])

            if not (has_dist and has_pae):
                continue  # Skip if no structural data

            # Calculate probability with guaranteed HHS/DALI values
            key = (res1, res2)

            dist = calculate_distance(res2coords[res1], res2coords[res2])
            dist_prob = get_PDB_prob(dist)

            error = rpair2error[res1][res2]
            pae_prob = get_PAE_prob(error)

            hhs_prob = get_HHS_prob(aggregated_hhs[key])
            dali_prob = get_DALI_prob(aggregated_dali[key])

            # Combined probability - v1.0 geometric mean formula
            combined = (dist_prob * pae_prob * hhs_prob * dali_prob) ** 0.25
            prob_matrix[(res1, res2)] = combined

    return prob_matrix


def get_prob(prob_matrix: Dict[Tuple[int, int], float], res1: int, res2: int) -> float:
    """
    Get probability for residue pair (handles ordering).

    CRITICAL (matches v1.0): Return 0.0 for missing pairs instead of default 0.5.
    v1.0 directly accesses rpair2prob dict (would KeyError if missing).
    Missing pairs should NOT contribute to domain merging.
    """
    if res1 == res2:
        return 1.0
    key = (min(res1, res2), max(res1, res2))
    return prob_matrix.get(key, 0.0)  # 0.0 prevents merging when data missing


def initial_segmentation(length: int, diso_resids: Set[int]) -> List[List[int]]:
    """
    Create initial 5-residue segments excluding disorder.

    Keep segments with >= 3 residues (v1.0 lines 446-456).
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
    """
    Calculate mean probability between two segments.

    CRITICAL (v1.0 line 489): Only count pairs with sequence separation >= 5.
    This prevents nearby residues in sequence from inflating similarity scores.
    """
    total = 0.0
    count = 0

    for res1 in seg1:
        for res2 in seg2:
            # v1.0 filter: only count pairs separated by >= 5 residues
            if res1 + 5 < res2 or res2 + 5 < res1:
                total += get_prob(prob_matrix, res1, res2)
                count += 1

    return total / count if count > 0 else 0.0


def cluster_segments_v1(segments: List[List[int]],
                        prob_matrix: Dict[Tuple[int, int], float]) -> List[List[int]]:
    """
    Cluster segments using exact v1.0 algorithm (lines 457-592).

    Key differences from previous implementation:
    1. Pre-calculate all segment pair counts/totals
    2. Sort pairs by mean probability (descending)
    3. Single-pass merge with candidate cluster logic

    Returns clustered segments.
    """
    import numpy as np

    # Step 1: Pre-calculate segment pair statistics (v1.0 lines 457-498)
    segment_probs = []
    spair2count = {}
    spair2total = {}

    for i in range(len(segments)):
        for j in range(len(segments)):
            if i < j:
                # Initialize counts
                if i not in spair2count:
                    spair2count[i] = {}
                if i not in spair2total:
                    spair2total[i] = {}
                if j not in spair2count:
                    spair2count[j] = {}
                if j not in spair2total:
                    spair2total[j] = {}

                spair2count[i][j] = 0
                spair2total[i][j] = 0
                spair2count[j][i] = 0
                spair2total[j][i] = 0

                # Calculate probabilities with +5 filter
                probs = []
                for resi in segments[i]:
                    for resj in segments[j]:
                        if resi + 5 < resj:  # v1.0 line 489
                            prob = get_prob(prob_matrix, resi, resj)
                            spair2count[i][j] += 1
                            spair2total[i][j] += prob
                            spair2count[j][i] += 1
                            spair2total[j][i] += prob
                            probs.append(prob)

                # Check threshold
                if probs:
                    meanprob = np.mean(probs)
                    if meanprob > 0.64:  # v1.0 param1 (line 176)
                        segment_probs.append([i, j, meanprob])

    # Step 2: Sort by probability descending (v1.0 line 501)
    segment_probs.sort(key=lambda x: x[2], reverse=True)

    # Step 3: Iterative merging with candidate logic (v1.0 lines 502-592)
    segments_V1 = []

    for item in segment_probs:
        segi = item[0]
        segj = item[1]

        if not segments_V1:
            # First pair - create initial cluster
            segments_V1.append(set([segi, segj]))
        else:
            isdone = 0
            candidates = []

            # Find which clusters contain segi or segj
            for counts, segment in enumerate(segments_V1):
                if segi in segment and segj in segment:
                    isdone = 1  # Both already in same cluster
                elif segi in segment:
                    candidates.append(counts)
                elif segj in segment:
                    candidates.append(counts)

            if not isdone:
                if len(candidates) == 2:
                    # Merging would join two existing clusters (v1.0 lines 520-557)
                    c1 = candidates[0]
                    c2 = candidates[1]

                    # Calculate intra-cluster probabilities
                    intra_count1 = 0
                    intra_total1 = 0
                    intra_count2 = 0
                    intra_total2 = 0
                    inter_count = 0
                    inter_total = 0

                    for i in segments_V1[c1]:
                        for j in segments_V1[c1]:
                            if i < j:
                                intra_count1 += spair2count[i][j]
                                intra_total1 += spair2total[i][j]

                    for i in segments_V1[c2]:
                        for j in segments_V1[c2]:
                            if i < j:
                                intra_count2 += spair2count[i][j]
                                intra_total2 += spair2total[i][j]

                    for i in segments_V1[c1]:
                        for j in segments_V1[c2]:
                            inter_count += spair2count[i][j]
                            inter_total += spair2total[i][j]

                    # Decide whether to merge (v1.0 lines 543-557)
                    merge = 0
                    if intra_count1 <= 20 or intra_count2 <= 20:
                        merge = 1
                    else:
                        intra_prob1 = intra_total1 / intra_count1 if intra_count1 > 0 else 0
                        intra_prob2 = intra_total2 / intra_count2 if intra_count2 > 0 else 0
                        inter_prob = inter_total / inter_count if inter_count > 0 else 0
                        if inter_prob * 1.1 >= intra_prob1 or inter_prob * 1.1 >= intra_prob2:
                            merge = 1

                    if merge:
                        # Merge the two clusters
                        new_segments = []
                        new_segment = set()
                        for counts, segment in enumerate(segments_V1):
                            if counts in candidates:
                                new_segment = new_segment.union(segment)
                            else:
                                new_segments.append(segment)
                        new_segments.append(new_segment)
                        segments_V1 = new_segments

                elif len(candidates) == 1:
                    # Add to existing cluster (v1.0 lines 559-588)
                    c0 = candidates[0]

                    # Calculate probabilities
                    intra_count = 0
                    intra_total = 0
                    inter_count = 0
                    inter_total = 0

                    for i in segments_V1[c0]:
                        for j in segments_V1[c0]:
                            if i < j:
                                intra_count += spair2count[i][j]
                                intra_total += spair2total[i][j]

                    if segi in segments_V1[c0]:
                        for k in segments_V1[c0]:
                            if segj != k:
                                inter_count += spair2count[k][segj]
                                inter_total += spair2total[k][segj]
                    elif segj in segments_V1[c0]:
                        for k in segments_V1[c0]:
                            if segi != k:
                                inter_count += spair2count[k][segi]
                                inter_total += spair2total[k][segi]

                    # Decide whether to merge (v1.0 lines 582-587)
                    merge = 0
                    if intra_total <= 20:
                        merge = 1
                    else:
                        intra_prob = intra_total / intra_count if intra_count > 0 else 0
                        inter_prob = inter_total / inter_count if inter_count > 0 else 0
                        if inter_prob * 1.1 >= intra_prob:
                            merge = 1

                    if merge:
                        segments_V1[c0].add(segi)
                        segments_V1[c0].add(segj)

                elif len(candidates) == 0:
                    # Create new cluster (v1.0 line 590)
                    segments_V1.append(set([segi, segj]))

    # Step 4: Convert sets of indices back to lists of residues (v1.0 lines 594-603)
    sorted_segments = []
    for item in segments_V1:
        resids = []
        for segind in item:
            for res in segments[segind]:
                resids.append(res)
        resids.sort()
        if resids:
            sorted_segments.append([resids, np.mean(resids)])

    sorted_segments.sort(key=lambda x: x[1])

    # Return just the residue lists
    return [item[0] for item in sorted_segments]


def fill_gaps(domains: List[List[int]], domain_resids: set) -> List[List[int]]:
    """
    Fill gaps between segments based on original v1.0 logic (lines 540-559).

    Gap filling rules:
    - Always fill gaps <= 10 residues
    - Fill gaps <= 20 residues if <= 10 belong to other domains

    Domain refinement v0 -> v1.
    """
    filled = []

    for domain in domains:
        if not domain:
            continue

        # Split into consecutive segments
        segs = []
        for res in domain:
            if not segs:
                segs.append([res])
            elif res == segs[-1][-1] + 1:
                segs[-1].append(res)
            else:
                segs.append([res])

        # Fill gaps based on v1.0 logic
        if len(segs) > 1:
            newdomain = []
            for counts, seg in enumerate(segs):
                if counts == 0:
                    # First segment - add all residues
                    for residue in seg:
                        newdomain.append(residue)
                else:
                    # Subsequent segments - check gap
                    lastseg = segs[counts - 1]
                    interseg = range(lastseg[-1] + 1, seg[0])

                    count_all = len(interseg)
                    count_other = sum(1 for residue in interseg if residue in domain_resids)
                    count_good = count_all - count_other

                    getit = 0
                    if count_all <= 10:
                        getit = 1
                    elif count_all <= 20 and count_other <= 10:
                        getit = 1

                    if getit:
                        # Fill gap
                        for residue in interseg:
                            newdomain.append(residue)

                    # Add segment
                    for residue in seg:
                        newdomain.append(residue)
            filled.append(newdomain)
        else:
            # Single segment - no gaps to fill
            filled.append(segs[0])

    return filled


def remove_overlaps(domains: List[List[int]]) -> List[List[int]]:
    """
    Remove overlaps between domains.

    v1.0-compatible (lines 594-606): For each domain, remove segments
    where < 10 residues are unique (not in other domains).
    Keep domains with >= 25 total residues.

    Domain refinement v1 -> v2.
    """
    cleaned = []

    for counti, itemi in enumerate(domains):
        domain = itemi

        # Find residues in other domains
        other_resids = set()
        for countj, itemj in enumerate(domains):
            if counti != countj:
                for res in itemj:
                    other_resids.add(res)

        # Split into consecutive segments
        segs = []
        for res in domain:
            if not segs:
                segs.append([res])
            elif res == segs[-1][-1] + 1:
                segs[-1].append(res)
            else:
                segs.append([res])

        # Keep segments with >= 10 unique residues - v1.0 keeps entire segment
        newdomain = []
        for seg in segs:
            unique_in_seg = [resid for resid in seg if resid not in other_resids]
            if len(unique_in_seg) >= 10:
                # v1.0 behavior: keep entire segment, not just unique residues (line 698-702)
                newdomain.extend(seg)

        # Keep domain if >= 25 total residues (v1.0 line 606)
        if len(newdomain) >= 25:
            cleaned.append(newdomain)

    return cleaned


def filter_by_length(domains: List[List[int]], min_length: int = 20) -> List[List[int]]:
    """Filter domains by minimum length."""
    return [d for d in domains if len(d) >= min_length]


def run_step13(prefix: str, working_dir: Path, path_resolver=None) -> bool:
    """
    Run step 13: Parse final domains.

    Args:
        prefix: Structure prefix
        working_dir: Working directory
        path_resolver: PathResolver instance for sharded output directories

    Returns:
        True if successful, False otherwise
    """
    from dpam.core.path_resolver import PathResolver
    resolver = path_resolver or PathResolver(working_dir, sharded=False)

    logger.info(f"Step 13: Parsing domains for {prefix}")

    # Input files
    fasta_file = resolver.step_dir(1) / f'{prefix}.fa'
    diso_file = resolver.step_dir(12) / f'{prefix}.diso'
    pdb_file = resolver.step_dir(1) / f'{prefix}.pdb'
    json_file = resolver.root / f'{prefix}.json'
    gooddomains_file = resolver.step_dir(10) / f'{prefix}.goodDomains'

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

    # Load good domain scores
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

    # Cluster segments using exact v1.0 algorithm
    logger.info("Clustering segments (v1.0 algorithm: prob > 0.64, ratio 1.1)")
    clusters = cluster_segments_v1(segments, prob_matrix)
    logger.info(f"Clustered to {len(clusters)} domains")

    # Domain refinement v0: filter by length
    domains_v0 = filter_by_length(clusters, min_length=20)
    logger.info(f"Domains v0 (>= 20 residues): {len(domains_v0)}")

    # Build set of all domain residues for gap filling
    domain_resids = set()
    for domain in domains_v0:
        for res in domain:
            domain_resids.add(res)

    # Domain refinement v1: fill gaps (<=10 always, <=20 if <=10 in other domains)
    domains_v1 = fill_gaps(domains_v0, domain_resids)
    logger.info(f"Domains v1 (gaps filled): {len(domains_v1)}")

    # Domain refinement v2: remove overlaps (keep segments >=10 unique, domains >=25 total)
    domains_v2 = remove_overlaps(domains_v1)
    logger.info(f"Domains v2 (overlaps removed): {len(domains_v2)}")

    # Final domains (no additional filtering - remove_overlaps already applies >=25 threshold)
    final_domains = domains_v2
    logger.info(f"Final domains: {len(final_domains)}")

    # Write output (two filenames for compatibility)
    step13_dir = resolver.step_dir(13)
    results_dir = resolver.results_dir()
    output_file = step13_dir / f'{prefix}.finalDPAM.domains'
    results_file = results_dir / f'{prefix}.finalDPAM.domains'
    step13_file = step13_dir / f'{prefix}.step13_domains'
    logger.info(f"Writing final domains to {output_file}")

    domain_lines = []
    for i, domain in enumerate(final_domains, 1):
        range_str = residues_to_range(sorted(domain))
        domain_lines.append(f"D{i}\t{range_str}\n")

    # Write .finalDPAM.domains to step dir
    with open(output_file, 'w') as f:
        f.writelines(domain_lines)

    # Write .finalDPAM.domains to results dir
    with open(results_file, 'w') as f:
        f.writelines(domain_lines)

    # Write .step13_domains (for ML pipeline compatibility)
    with open(step13_file, 'w') as f:
        f.writelines(domain_lines)

    logger.info(f"Step 13 complete: {len(final_domains)} domains parsed")

    return True
