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

# --- Gated adjacency merge (fragment absorption) -----------------------------------------
# Template-sharing alone cannot rescue an orphan fragment: a domain with NO ECOD hit is
# invisible to the template pass, so a fragment embedded inside such a domain is never even
# proposed (see MERGE_FRAGMENT_DEFICIENCY.md). We add adjacency-based candidates, but GATED,
# so we do not re-introduce the dissimilar-H/T merging the adjacency rule was forgone to avoid.
#
# A pair is proposed by adjacency ONLY if ALL hold:
#   1. one side is a FRAGMENT: shorter than any curated ECOD domain of its own T-group AND
#      < 0.5x that fold's median (or below ABS_MIN_DOMAIN). Full-size domains are never
#      absorbable; small-but-real domains (e.g. Zn-fingers, whose T-group min is ~29) are not
#      fragments and are therefore protected.
#   2. H/T COMPATIBLE: same H-group, or one side has no confident assignment. Two confidently
#      assigned domains of DIFFERENT H-groups are never proposed.
#   3. within ADJ_GAP_MAX residues, or embedded inside the acceptor's sequence span.
# step21's connectivity test still validates every proposed pair.

ABS_MIN_DOMAIN = 30      # no curated ECOD domain is smaller than this
ADJ_GAP_MAX = 50         # residues; fragment must sit this close to its acceptor
MIN_CURATED_N = 3        # need >=3 curated examples to trust a T-group's floor


def h_group(tgroup: str) -> str:
    """H-group (X.H) of a T-group id (X.H.T)."""
    return ".".join(tgroup.split(".")[:2]) if tgroup else ""


def load_tgroup_sizes(data_dir: Path) -> Dict[str, dict]:
    """Curated ECOD domain-size stats per T-group: t_id, n, min_len, p05, median."""
    sizes: Dict[str, dict] = {}
    f = data_dir / "ECOD_tgroup_sizes"
    if not f.exists():
        logger.warning(f"ECOD_tgroup_sizes not found in {data_dir}; "
                       "adjacency merge falls back to the absolute size floor only")
        return sizes
    with open(f, 'r') as fh:
        for line in fh:
            p = line.strip().split('\t')
            if len(p) < 5:
                continue
            try:
                sizes[p[0]] = dict(n=int(p[1]), min=float(p[2]),
                                   p05=float(p[3]), med=float(p[4]))
            except ValueError:
                continue
    logger.debug(f"Loaded curated size profiles for {len(sizes)} T-groups")
    return sizes


def is_fragment(length: int, tgroup: str, tg_sizes: Dict[str, dict]) -> bool:
    """Fold-aware fragment test (gate condition 1)."""
    if length < ABS_MIN_DOMAIN:
        return True
    c = tg_sizes.get(tgroup)
    if not tgroup or c is None or c["n"] < MIN_CURATED_N:
        return False          # cannot fold-calibrate -> not a fragment (absolute floor only)
    return length < c["min"] and length < 0.5 * c["med"]


def ht_compatible(tg_a: str, tg_b: str) -> bool:
    """Gate condition 2: same H-group, or at least one side unassigned."""
    if not tg_a or not tg_b:
        return True
    return h_group(tg_a) == h_group(tg_b)


def is_adjacent(resids_a: Set[int], resids_b: Set[int]) -> bool:
    """Gate condition 3: embedded in the acceptor's span, or within ADJ_GAP_MAX residues."""
    if not resids_a or not resids_b:
        return False
    lo_a, hi_a = min(resids_a), max(resids_a)
    lo_b, hi_b = min(resids_b), max(resids_b)
    # embedded: the fragment lies inside the acceptor's sequence span (e.g. fills a gap in it)
    if lo_b <= lo_a and hi_a <= hi_b:
        return True
    gap = min(abs(a - b) for a in (lo_a, hi_a) for b in (lo_b, hi_b))
    return gap <= ADJ_GAP_MAX


def load_all_domains(domains_file: Path) -> Dict[str, str]:
    """ALL step13 domains, including those with NO ECOD hit (invisible to the template pass)."""
    out: Dict[str, str] = {}
    if not domains_file.exists():
        return out
    with open(domains_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                out[parts[0]] = parts[1]
    return out


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
    path_resolver=None,
    **kwargs
) -> bool:
    """
    Identify merge candidate domain pairs.

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

    logger.info(f"Step 19: Getting merge candidates for {prefix}")

    # Input file
    mappings_file = resolver.step_dir(18) / f"{prefix}.step18_mappings"

    if not mappings_file.exists():
        logger.info(f"No mappings found for {prefix}")
        return True

    # Reference data
    ecod_length_file = data_dir / "ECOD_length"
    weights_dir = data_dir / "posi_weights"

    if not ecod_length_file.exists():
        logger.error(f"ECOD length file not found: {ecod_length_file}")
        return False

    # ALL step13 domains — including those with NO ECOD hit. The template pass below only ever
    # sees domains present in step18_mappings, so an ECOD-hitless domain is invisible to it and
    # a fragment embedded inside such a domain can never be proposed. The adjacency pass needs
    # the full domain set.
    all_domains = load_all_domains(resolver.step_dir(13) / f"{prefix}.step13_domains")
    tg_sizes = load_tgroup_sizes(data_dir)

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

                # Get template residues using V1 logic:
                # Use DALI only if it covers >50% of HHsearch residues
                hh_resids = set(parse_range(hh_template_range)) if hh_template_range != 'na' else set()
                dali_resids = set(parse_range(dali_template_range)) if dali_template_range != 'na' else set()

                if len(dali_resids) > len(hh_resids) * 0.5:
                    template_resids = dali_resids
                else:
                    template_resids = hh_resids

                if not template_resids:
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
                # Note: original uses > not >= for the threshold check
                if not (prob1 + 0.1 > domain_to_best_prob[domain1] and
                        prob2 + 0.1 > domain_to_best_prob[domain2]):
                    continue

                # Template regions must cover different areas (< 25% overlap)
                common = tres1 & tres2

                # V1 logic: Skip only if BOTH have high overlap (AND, not OR)
                # This is more permissive - allows merge if EITHER has low overlap
                if (len(common) >= 0.25 * len(tres1) and
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
        # Original uses > for prob check and ratio check
        against1 = set()
        if domain1 in domain_to_hits:
            for hit in domain_to_hits[domain1]:
                if (hit['prob'] + 0.1 > domain_to_best_prob[domain1] and
                    hit['coverage'] > 0.5 and
                    hit['ecod'] not in supporting_ecods):
                    against1.add(hit['ecod'])

        # Count ECODs opposing merge for domain2
        against2 = set()
        if domain2 in domain_to_hits:
            for hit in domain_to_hits[domain2]:
                if (hit['prob'] + 0.1 > domain_to_best_prob[domain2] and
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

    # ---------------------------------------------------------------------------------
    # GATED ADJACENCY PASS — rescue orphan fragments the template pass cannot see.
    # Gates: (1) fold-aware fragment size, (2) H/T compatibility, (3) adjacency/embedding.
    # step21 still validates connectivity for every pair proposed here.
    # ---------------------------------------------------------------------------------
    # Best (highest-prob) T-group per domain; domains with no ECOD hit stay unassigned ("").
    domain_to_tgroup: Dict[str, str] = {}
    for domain, hits in domain_to_hits.items():
        best = max(hits, key=lambda h: h['prob'])
        domain_to_tgroup[domain] = best['tgroup'] or ""

    domain_resids = {d: set(parse_range(r)) for d, r in all_domains.items()}
    existing_pairs = {tuple(sorted(m.split('\t')[0::2])) for m in validated_merges}

    n_adj = 0
    for frag, frag_res in domain_resids.items():
        frag_len = len(frag_res)
        frag_tg = domain_to_tgroup.get(frag, "")

        # Gate 1: only a fragment (below its own fold's curated floor) may be absorbed.
        if not is_fragment(frag_len, frag_tg, tg_sizes):
            continue

        for acc, acc_res in domain_resids.items():
            if acc == frag:
                continue
            acc_tg = domain_to_tgroup.get(acc, "")

            # Never absorb a fragment into another fragment.
            if is_fragment(len(acc_res), acc_tg, tg_sizes):
                continue
            # Gate 2: H/T compatibility — this is the safeguard the template rule provided.
            if not ht_compatible(frag_tg, acc_tg):
                continue
            # Gate 3: adjacency / embedding.
            if not is_adjacent(frag_res, acc_res):
                continue

            pair = tuple(sorted([frag, acc]))
            if pair in existing_pairs:
                continue
            existing_pairs.add(pair)

            validated_merges.append(
                f"{frag}\t{all_domains[frag]}\t{acc}\t{all_domains[acc]}"
            )
            merge_info.append(f"{frag},{acc}\tADJACENCY(frag={frag_len}aa,"
                              f"tg={frag_tg or 'NA'}->{acc_tg or 'NA'})")
            n_adj += 1

    if n_adj:
        logger.info(f"Step 19: {n_adj} additional merge candidates from gated adjacency pass")

    # Write results
    output_file = resolver.step_dir(19) / f"{prefix}.step19_merge_candidates"
    info_file = resolver.step_dir(19) / f"{prefix}.step19_merge_info"

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
