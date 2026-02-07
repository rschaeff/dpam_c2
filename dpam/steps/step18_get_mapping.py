"""
Step 18: Get Alignment Mappings

Map domain residues to ECOD template residues using original HHsearch and DALI alignments.
This provides the actual residue-to-residue mappings needed for coverage calculations.

Input:
    - {prefix}.step17_confident_predictions: Confident domain-ECOD predictions
    - {prefix}.map2ecod.result: HHsearch alignments (from step 5)
    - {prefix}_good_hits: DALI alignments (from step 9)
    - ECOD_maps/{ecod_id}.map: PDB→ECOD residue numbering

Output:
    - {prefix}.step18_mappings: Domain predictions with template ranges

CRITICAL: Template residue filtering
    For merge candidate detection (step 19), we need to know which template
    residues correspond to THIS domain's query residues (not the entire alignment).

    Example: If DALI aligns query 1-500 to template 1-300, but domain D1 only
    covers query 1-200, we should only report template residues that align to
    the query residues 1-200.

Overlap Criteria (stricter than Step 15):
    - Must have ≥33% overlap relative to domain A
    - If yes, must have either:
        - ≥50% overlap relative to A, OR
        - ≥50% overlap relative to B

Algorithm:
    1. Load confident predictions from step 17
    2. For each domain-ECOD prediction:
        a. Find overlapping HHsearch hits from map2ecod.result
        b. Find overlapping DALI hits from _good_hits
        c. Filter to only template residues where query aligns to domain
        d. Map HHsearch template residues to ECOD canonical numbering
        e. Convert to range strings
    3. Write mappings (may be 'na' if no alignment found)
"""

from pathlib import Path
from typing import Set, List, Dict, Optional, Tuple
import logging

from ..utils.ranges import parse_range, format_range, range_to_residues_list

logger = logging.getLogger(__name__)


def check_overlap_strict(resids_a: Set[int], resids_b: Set[int]) -> bool:
    """
    Check if two residue sets overlap significantly (stricter than step 15).

    Rules:
    - Must have ≥33% overlap relative to A
    - If yes, must have either:
      - ≥50% overlap relative to A, OR
      - ≥50% overlap relative to B

    Args:
        resids_a: First residue set (domain)
        resids_b: Second residue set (hit)

    Returns:
        True if overlap criteria met, False otherwise
    """
    overlap = resids_a & resids_b

    if len(overlap) >= len(resids_a) * 0.33:
        if len(overlap) >= len(resids_a) * 0.5 or len(overlap) >= len(resids_b) * 0.5:
            return True

    return False


def load_ecod_map(map_file: Path) -> Tuple[Set[int], Dict[int, int]]:
    """
    Load ECOD residue numbering map.

    Format: ecod_resid pdb_resid

    Args:
        map_file: ECOD map file path

    Returns:
        Tuple of (set of ECOD residues, dict mapping ECOD to PDB residue IDs)
    """
    ecod_resids = set()
    ecod_to_pdb = {}

    if not map_file.exists():
        logger.warning(f"ECOD map not found: {map_file}")
        return ecod_resids, ecod_to_pdb

    with open(map_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    ecod_resid = int(parts[1])  # ECOD resid in column 1
                    pdb_resid = int(parts[0])   # PDB resid in column 0
                    ecod_resids.add(ecod_resid)
                    ecod_to_pdb[ecod_resid] = pdb_resid
                except ValueError:
                    continue

    return ecod_resids, ecod_to_pdb


def run_step18(
    prefix: str,
    working_dir: Path,
    data_dir: Path,
    path_resolver=None,
    **kwargs
) -> bool:
    """
    Get alignment mappings for confident predictions.

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

    logger.info(f"Step 18: Getting alignment mappings for {prefix}")

    # Input files
    confident_file = resolver.step_dir(17) / f"{prefix}.step17_confident_predictions"
    hhsearch_file = resolver.step_dir(5) / f"{prefix}.map2ecod.result"  # Step 5 output
    dali_file = resolver.step_dir(8) / f"{prefix}_good_hits"  # Step 9 output

    # Check inputs
    if not confident_file.exists():
        logger.info(f"No confident predictions found for {prefix}")
        return True

    if not hhsearch_file.exists():
        logger.error(f"HHsearch hits not found: {hhsearch_file}")
        return False

    if not dali_file.exists():
        logger.error(f"DALI hits not found: {dali_file}")
        return False

    # ECOD maps directory
    ecod_maps_dir = data_dir / "ECOD_maps"
    if not ecod_maps_dir.exists():
        logger.error(f"ECOD maps directory not found: {ecod_maps_dir}")
        return False

    # Load ECOD ID to UID mapping from ECOD_length file
    # Format: uid \t ecod_id \t length
    ecod_id_to_uid = {}
    ecod_length_file = data_dir / "ECOD_length"
    if ecod_length_file.exists():
        with open(ecod_length_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    uid = parts[0]
                    ecod_id = parts[1]
                    ecod_id_to_uid[ecod_id] = uid
        logger.debug(f"Loaded {len(ecod_id_to_uid)} ECOD ID to UID mappings")
    else:
        logger.warning(f"ECOD_length file not found: {ecod_length_file}")

    # Output file
    output_file = resolver.step_dir(18) / f"{prefix}.step18_mappings"

    # Load HHsearch hits from map2ecod.result
    # Format: uid  ecod_domain_id  hh_prob  ...  query_range  template_range  ...
    hhsearch_hits = []

    with open(hhsearch_file, 'r') as f:
        for i, line in enumerate(f):
            if i == 0:  # Skip header
                continue

            parts = line.strip().split('\t')
            if len(parts) < 13:
                continue

            try:
                ecod_id = parts[1]  # ecod_domain_id
                hh_prob = float(parts[2]) / 100.0  # Convert from percentage
                query_range = parts[11]  # query_range column
                template_range = parts[12]  # template_range column

                # Get position-correspondent lists
                query_resids = range_to_residues_list(query_range)
                template_resids = range_to_residues_list(template_range)

                if len(query_resids) != len(template_resids):
                    logger.warning(f"HHsearch Q/T length mismatch for {ecod_id}: "
                                   f"{len(query_resids)} vs {len(template_resids)}")
                    continue

                hhsearch_hits.append({
                    'ecod': ecod_id,
                    'prob': hh_prob,
                    'query_resids': query_resids,
                    'template_resids': template_resids,
                    'query_resids_set': set(query_resids)
                })
            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping malformed HHsearch line: {e}")
                continue

    logger.debug(f"Loaded {len(hhsearch_hits)} HHsearch hits")

    # Load DALI hits
    dali_hits = []

    with open(dali_file, 'r') as f:
        for i, line in enumerate(f):
            if i == 0 or line.startswith('#'):
                continue  # Skip header

            parts = line.strip().split('\t')
            if len(parts) < 11:
                continue

            try:
                ecod_id = parts[2]  # ecodkey column
                zscore = float(parts[4])
                query_range = parts[9]  # qrange column
                template_range = parts[10]  # erange column

                # Get position-correspondent lists
                query_resids = range_to_residues_list(query_range)
                template_resids = range_to_residues_list(template_range)

                if len(query_resids) != len(template_resids):
                    logger.warning(f"DALI Q/T length mismatch for {ecod_id}: "
                                   f"{len(query_resids)} vs {len(template_resids)}")
                    continue

                dali_hits.append({
                    'ecod': ecod_id,
                    'zscore': zscore,
                    'query_resids': query_resids,
                    'template_resids': template_resids,
                    'query_resids_set': set(query_resids)
                })
            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping malformed DALI line: {e}")
                continue

    logger.debug(f"Loaded {len(dali_hits)} DALI hits")

    # Process confident predictions
    results = []

    with open(confident_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue

            parts = line.strip().split('\t')
            if len(parts) < 6:
                continue

            domain_name = parts[0]
            domain_range = parts[1]
            tgroup = parts[2]
            ecod_ref = parts[3]
            dpam_prob = parts[4]
            quality = parts[5]

            domain_resids = set(parse_range(domain_range))

            # Find overlapping HHsearch hit for this ECOD
            hh_template_range = 'na'

            for hit in hhsearch_hits:
                if hit['ecod'] == ecod_ref:
                    if check_overlap_strict(domain_resids, hit['query_resids_set']):
                        # Load ECOD map using UID
                        uid = ecod_id_to_uid.get(ecod_ref)
                        if not uid:
                            logger.debug(f"No UID found for {ecod_ref}")
                            continue
                        ecod_resids, ecod_to_pdb = load_ecod_map(
                            ecod_maps_dir / f"{uid}.map"
                        )

                        # Filter template residues to only those where
                        # the query residue falls within THIS domain
                        filtered_template_resids = []
                        for i in range(len(hit['query_resids'])):
                            qres = hit['query_resids'][i]
                            tres = hit['template_resids'][i]
                            # Only include if query residue is in this domain
                            # and template residue maps to ECOD
                            if qres in domain_resids and tres in ecod_resids:
                                # Map to ECOD canonical numbering
                                filtered_template_resids.append(ecod_to_pdb[tres])

                        if filtered_template_resids:
                            hh_template_range = format_range(filtered_template_resids)
                        break

            # Find overlapping DALI hit for this ECOD
            dali_template_range = 'na'

            for hit in dali_hits:
                if hit['ecod'] == ecod_ref:
                    if check_overlap_strict(domain_resids, hit['query_resids_set']):
                        # Filter template residues to only those where
                        # the query residue falls within THIS domain
                        # DALI residues are already in ECOD numbering from step 9
                        filtered_template_resids = []
                        for i in range(len(hit['query_resids'])):
                            qres = hit['query_resids'][i]
                            tres = hit['template_resids'][i]
                            # Only include if query residue is in this domain
                            if qres in domain_resids:
                                filtered_template_resids.append(tres)

                        if filtered_template_resids:
                            dali_template_range = format_range(filtered_template_resids)
                        break

            results.append(
                f"{domain_name}\t{domain_range}\t{ecod_ref}\t{tgroup}\t"
                f"{dpam_prob}\t{quality}\t{hh_template_range}\t{dali_template_range}"
            )

    # Write results
    with open(output_file, 'w') as f:
        f.write("# domain\tdomain_range\tecod_id\ttgroup\tdpam_prob\tquality\t"
                "hh_template_range\tdali_template_range\n")
        for result in results:
            f.write(result + '\n')

    logger.info(f"Step 18 complete: {len(results)} mappings generated")

    # Summary statistics
    hh_mapped = sum(1 for r in results if r.split('\t')[6] != 'na')
    dali_mapped = sum(1 for r in results if r.split('\t')[7] != 'na')
    both_mapped = sum(1 for r in results
                      if r.split('\t')[6] != 'na' and r.split('\t')[7] != 'na')

    logger.info(f"  HHsearch mapped: {hh_mapped}/{len(results)}")
    logger.info(f"  DALI mapped: {dali_mapped}/{len(results)}")
    logger.info(f"  Both mapped: {both_mapped}/{len(results)}")

    return True
