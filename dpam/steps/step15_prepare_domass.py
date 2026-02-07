"""
Step 15: Prepare DOMASS Features

Extract 17 machine learning features for each domain-ECOD pair.
Features combine domain properties with HHsearch and DALI evidence.

Input:
    - step13/{prefix}.domains: Parsed domains (step 14 in v1.0)
    - step12/{prefix}.sse: Secondary structure elements
    - step5/{prefix}.hhsearch_hits: HHsearch hits with alignments
    - step9/{prefix}.dali_good_hits: DALI hits with alignments
    - ECOD_maps/{ecod_id}.map: PDB→ECOD residue numbering
    - ecod.latest.domains: ECOD hierarchy (T-groups, H-groups)

Output:
    - {prefix}.step15_features: Features for ML model (17 features + metadata)

Features (17 total):
    1-3:   Domain properties (length, helix_count, strand_count)
    4-6:   HHsearch scores (prob, coverage, rank)
    7-11:  DALI scores (zscore, qscore, ztile, qtile, rank)
    12-13: Consensus metrics (diff, coverage)
    14-17: Metadata (hit names, rotation, translation)

Algorithm:
    1. Count SSE elements per domain
    2. Calculate HHsearch ranks (H-group redundancy)
    3. Load DALI hits with ECOD residue mapping
    4. For each domain:
        a. Find overlapping HHsearch hits (50% threshold)
        b. Find overlapping DALI hits (50% threshold)
        c. Generate features for ECODs found by BOTH methods
        d. Assign default values for single-method ECODs
"""

from pathlib import Path
from typing import Set, Dict, List, Tuple, Optional
import logging
import statistics

from ..utils.ranges import parse_range, format_range

logger = logging.getLogger(__name__)


def check_overlap_permissive(resids_a: Set[int], resids_b: Set[int]) -> bool:
    """
    Check if two residue sets overlap (50% threshold - more permissive than step 18).

    Args:
        resids_a: First residue set
        resids_b: Second residue set

    Returns:
        True if ≥50% overlap relative to either set
    """
    overlap = resids_a & resids_b
    return (len(overlap) >= len(resids_a) * 0.5 or
            len(overlap) >= len(resids_b) * 0.5)


def count_sse_in_domain(
    domain_resids: Set[int],
    resid_to_sse: Dict[int, Tuple[int, str]]
) -> Tuple[int, int]:
    """
    Count helices and strands in domain.

    Args:
        domain_resids: Residues in domain
        resid_to_sse: Mapping of residue → (sse_id, sse_type)

    Returns:
        Tuple of (helix_count, strand_count)
    """
    sse_to_count = {}
    sse_to_type = {}

    for resid in domain_resids:
        if resid in resid_to_sse:
            sse_id, sse_type = resid_to_sse[resid]

            if sse_id not in sse_to_count:
                sse_to_count[sse_id] = 0
                sse_to_type[sse_id] = sse_type

            sse_to_count[sse_id] += 1

    # Count helices with ≥6 residues
    helix_count = sum(
        1 for sse_id, count in sse_to_count.items()
        if sse_to_type[sse_id] == 'H' and count >= 6
    )

    # Count strands with ≥3 residues
    strand_count = sum(
        1 for sse_id, count in sse_to_count.items()
        if sse_to_type[sse_id] == 'E' and count >= 3
    )

    return helix_count, strand_count


def load_ecod_map(map_file: Path) -> Dict[int, int]:
    """
    Load ECOD residue numbering map.

    Args:
        map_file: ECOD map file path

    Returns:
        Dictionary mapping PDB residue ID to ECOD residue ID
    """
    resmap = {}

    if not map_file.exists():
        return resmap

    with open(map_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    pdb_resid = int(parts[0])
                    ecod_resid = int(parts[1])
                    resmap[pdb_resid] = ecod_resid
                except ValueError:
                    continue

    return resmap


def run_step15(
    prefix: str,
    working_dir: Path,
    data_dir: Path,
    path_resolver=None,
    **kwargs
) -> bool:
    """
    Prepare DOMASS features for ML model.

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

    logger.info(f"Step 15: Preparing DOMASS features for {prefix}")

    # Input files
    domains_file = resolver.step_dir(13) / f"{prefix}.step13_domains"
    sse_file = resolver.step_dir(11) / f"{prefix}.sse"
    gooddomains_file = resolver.step_dir(10) / f"{prefix}.goodDomains"  # Contains both HHsearch and DALI
    good_hits_file = resolver.step_dir(8) / f"{prefix}_good_hits"  # DALI hits with scores

    # Check inputs
    if not domains_file.exists():
        logger.info(f"No domains found for {prefix}")
        return True

    for required_file in [sse_file, gooddomains_file, good_hits_file]:
        if not required_file.exists():
            logger.error(f"Required file not found: {required_file}")
            return False

    # Reference data
    ecod_maps_dir = data_dir / "ECOD_maps"
    ecod_domains_file = data_dir / "ecod.latest.domains"

    if not ecod_maps_dir.exists():
        logger.error(f"ECOD maps directory not found: {ecod_maps_dir}")
        return False

    if not ecod_domains_file.exists():
        logger.error(f"ECOD domains file not found: {ecod_domains_file}")
        return False

    # Load ECOD hierarchy (T-groups, H-groups)
    ecod_to_tgroup = {}
    ecod_to_hgroup = {}

    with open(ecod_domains_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue

            parts = line.strip().split()
            if len(parts) >= 4:
                ecod_id = parts[1]  # Column 1 is ECOD ID (e.g., e1r6wA1), column 0 is UID
                full_group = parts[3]
                group_parts = full_group.split('.')

                if len(group_parts) >= 3:
                    tgroup = '.'.join(group_parts[:3])
                    hgroup = '.'.join(group_parts[:2])
                    ecod_to_tgroup[ecod_id] = tgroup
                    ecod_to_hgroup[ecod_id] = hgroup

    logger.debug(f"Loaded {len(ecod_to_tgroup)} ECOD T-groups")

    # Load SSE data
    resid_to_sse = {}

    with open(sse_file, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 4:
                try:
                    resid = int(parts[0])
                    sse_id_str = parts[2]

                    if sse_id_str == 'na':
                        continue

                    sse_id = int(sse_id_str)
                    sse_type = parts[3]

                    resid_to_sse[resid] = (sse_id, sse_type)

                except (ValueError, IndexError):
                    continue

    # Load domains
    domains = []

    with open(domains_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue

            parts = line.strip().split('\t')
            if len(parts) >= 2:
                domain_name = parts[0]
                domain_range = parts[1]
                domain_resids = set(parse_range(domain_range))

                helix_count, strand_count = count_sse_in_domain(
                    domain_resids,
                    resid_to_sse
                )

                domains.append({
                    'name': domain_name,
                    'range': domain_range,
                    'resids': domain_resids,
                    'length': len(domain_resids),
                    'helix_count': helix_count,
                    'strand_count': strand_count
                })

    logger.debug(f"Loaded {len(domains)} domains")

    # Load HHsearch hits from goodDomains (sequence entries)
    qres_to_hgroups = {}  # Track which H-groups cover each query residue
    hhsearch_hits = []

    with open(gooddomains_file, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 11:  # Need at least 11 columns after step10 fix
                continue

            # Only process sequence (HHsearch) hits
            if parts[0] != 'sequence':
                continue

            try:
                ecod_uid = parts[2]
                ecod_id = parts[3]

                if ecod_id not in ecod_to_hgroup:
                    continue

                hgroup = ecod_to_hgroup[ecod_id]
                prob = float(parts[5]) / 100.0  # Already percentage (100.0 = 1.0)
                coverage = float(parts[6])
                # After step10 fix: cols 8=query_range, 9=template_range (ECOD numbering), 10=filtered_query
                template_range = parts[9]  # ECOD template residue numbering
                query_range = parts[10]    # Filtered query range

                query_resids = parse_range(query_range)
                template_resids = list(parse_range(template_range))

                # Track H-groups covering each residue
                for qres in query_resids:
                    if qres not in qres_to_hgroups:
                        qres_to_hgroups[qres] = set()
                    qres_to_hgroups[qres].add(hgroup)

                # Calculate rank (average number of H-groups per residue)
                ranks = [len(qres_to_hgroups[qres]) for qres in query_resids]
                rank = statistics.mean(ranks) / 10.0 if ranks else 0.0

                hhsearch_hits.append({
                    'ecod': ecod_id,
                    'hit_name': ecod_uid,
                    'prob': prob,
                    'coverage': coverage,
                    'rank': rank,
                    'query_resids': set(query_resids),
                    'template_resids': template_resids
                })

            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping malformed goodDomains line: {e}")
                continue

    max_hh_rank = max((hit['rank'] for hit in hhsearch_hits), default=10.0)
    if max_hh_rank < 10.0:
        max_hh_rank = 10.0

    logger.debug(f"Loaded {len(hhsearch_hits)} HHsearch hits")

    # Load DALI hits from _good_hits with ECOD residue mapping
    dali_hits = []

    with open(good_hits_file, 'r') as f:
        for line in f:
            # Skip header
            if line.startswith('hitname'):
                continue

            parts = line.strip().split('\t')
            if len(parts) < 11:
                continue

            try:
                hit_name = parts[0]
                ecod_uid = parts[1]
                ecod_id = parts[2]

                # Load ECOD map
                ecod_map = load_ecod_map(ecod_maps_dir / f"{ecod_id}.map")

                # V1.0 normalizes z-score and rank by dividing by 10
                # This matches the training data used for the DOMASS model
                zscore = float(parts[4]) / 10.0
                qscore = float(parts[5])
                ztile = float(parts[6])
                qtile = float(parts[7])
                rank = float(parts[8]) / 10.0
                query_range = parts[9]
                template_range = parts[10]

                query_resids = parse_range(query_range)
                raw_template_resids = parse_range(template_range)

                # Map template residues to ECOD canonical numbering
                mapped_template_resids = []
                for tres in raw_template_resids:
                    if tres in ecod_map:
                        mapped_template_resids.append(ecod_map[tres])

                dali_hits.append({
                    'ecod': ecod_id,
                    'hit_name': hit_name,
                    'zscore': zscore,
                    'qscore': qscore,
                    'ztile': ztile,
                    'qtile': qtile,
                    'rank': rank,
                    'query_resids': set(query_resids),
                    'template_resids': mapped_template_resids,
                    'rot1': 'na',  # Not in our pipeline
                    'rot2': 'na',
                    'rot3': 'na',
                    'trans': 'na'
                })

            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping malformed DALI line: {e}")
                continue

    max_dali_rank = max((hit['rank'] for hit in dali_hits), default=10.0)
    if max_dali_rank < 10.0:
        max_dali_rank = 10.0

    logger.debug(f"Loaded {len(dali_hits)} DALI hits")

    # Generate features for each domain
    output_file = resolver.step_dir(15) / f"{prefix}.step15_features"
    feature_count = 0

    with open(output_file, 'w') as f:
        # Write header
        f.write("domID\tdomRange\ttgroup\tecodid\tdomLen\tHelix_num\tStrand_num\t"
                "HHprob\tHHcov\tHHrank\tDzscore\tDqscore\tDztile\tDqtile\tDrank\t"
                "Cdiff\tCcov\tHHname\tDname\tDrot1\tDrot2\tDrot3\tDtrans\n")

        for domain in domains:
            domain_name = domain['name']
            domain_range = domain['range']
            domain_resids = domain['resids']
            domain_length = domain['length']
            helix_count = domain['helix_count']
            strand_count = domain['strand_count']

            # Find overlapping HHsearch hits
            hh_overlaps = {}
            for hit in hhsearch_hits:
                if check_overlap_permissive(domain_resids, hit['query_resids']):
                    ecod = hit['ecod']
                    # Keep best hit per ECOD (highest probability)
                    if ecod not in hh_overlaps or hit['prob'] > hh_overlaps[ecod]['prob']:
                        hh_overlaps[ecod] = hit

            # Find overlapping DALI hits
            dali_overlaps = {}
            for hit in dali_hits:
                if check_overlap_permissive(domain_resids, hit['query_resids']):
                    ecod = hit['ecod']
                    # Keep best hit per ECOD (highest z-score)
                    if ecod not in dali_overlaps or hit['zscore'] > dali_overlaps[ecod]['zscore']:
                        dali_overlaps[ecod] = hit

            # Generate features for ECODs found by BOTH methods
            both_ecods = set(hh_overlaps.keys()) & set(dali_overlaps.keys())

            for ecod in both_ecods:
                if ecod not in ecod_to_tgroup:
                    continue

                tgroup = ecod_to_tgroup[ecod]
                hh = hh_overlaps[ecod]
                dali = dali_overlaps[ecod]

                # Calculate consensus metrics
                common_qres = hh['query_resids'] & dali['query_resids']
                consensus_cov = len(common_qres) / domain_length if domain_length > 0 else 0

                # Build residue mappings (fixed: don't mutate set during iteration)
                hh_query_list = list(hh['query_resids'])
                hh_map = {hh_query_list[i]: hh['template_resids'][i]
                         for i in range(min(len(hh_query_list), len(hh['template_resids'])))}

                dali_query_list = list(dali['query_resids'])
                dali_map = {dali_query_list[i]: dali['template_resids'][i]
                           for i in range(min(len(dali_query_list), len(dali['template_resids'])))}

                # Calculate template position differences
                consensus_diffs = []
                for qres in common_qres:
                    if qres in hh_map and qres in dali_map:
                        diff = abs(hh_map[qres] - dali_map[qres])
                        consensus_diffs.append(diff)

                consensus_diff = statistics.mean(consensus_diffs) if consensus_diffs else -1

                # Write feature row
                f.write(f"{domain_name}\t{domain_range}\t{tgroup}\t{ecod}\t"
                       f"{domain_length}\t{helix_count}\t{strand_count}\t"
                       f"{hh['prob']:.3f}\t{hh['coverage']:.3f}\t{hh['rank']:.2f}\t"
                       f"{dali['zscore']:.3f}\t{dali['qscore']:.3f}\t"
                       f"{dali['ztile']:.3f}\t{dali['qtile']:.3f}\t{dali['rank']:.2f}\t"
                       f"{consensus_diff:.2f}\t{consensus_cov:.3f}\t"
                       f"{hh['hit_name']}\t{dali['hit_name']}\t"
                       f"{dali['rot1']}\t{dali['rot2']}\t{dali['rot3']}\t{dali['trans']}\n")

                feature_count += 1

            # Handle HHsearch-only hits
            hh_only = set(hh_overlaps.keys()) - set(dali_overlaps.keys())
            for ecod in hh_only:
                if ecod not in ecod_to_tgroup:
                    continue

                tgroup = ecod_to_tgroup[ecod]
                hh = hh_overlaps[ecod]

                f.write(f"{domain_name}\t{domain_range}\t{tgroup}\t{ecod}\t"
                       f"{domain_length}\t{helix_count}\t{strand_count}\t"
                       f"{hh['prob']:.3f}\t{hh['coverage']:.3f}\t{hh['rank']:.2f}\t"
                       f"0.000\t0.000\t10.000\t10.000\t{max_dali_rank:.2f}\t"
                       f"-1.00\t0.000\t"
                       f"{hh['hit_name']}\tna\tna\tna\tna\tna\n")

                feature_count += 1

            # Handle DALI-only hits
            dali_only = set(dali_overlaps.keys()) - set(hh_overlaps.keys())
            for ecod in dali_only:
                if ecod not in ecod_to_tgroup:
                    continue

                tgroup = ecod_to_tgroup[ecod]
                dali = dali_overlaps[ecod]

                f.write(f"{domain_name}\t{domain_range}\t{tgroup}\t{ecod}\t"
                       f"{domain_length}\t{helix_count}\t{strand_count}\t"
                       f"0.000\t0.000\t{max_hh_rank:.2f}\t"
                       f"{dali['zscore']:.3f}\t{dali['qscore']:.3f}\t"
                       f"{dali['ztile']:.3f}\t{dali['qtile']:.3f}\t{dali['rank']:.2f}\t"
                       f"-1.00\t0.000\t"
                       f"na\t{dali['hit_name']}\t"
                       f"{dali['rot1']}\t{dali['rot2']}\t{dali['rot3']}\t{dali['trans']}\n")

                feature_count += 1

    logger.info(f"Step 15 complete: {feature_count} feature rows generated")

    return True
