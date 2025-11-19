"""
Step 18: Get Alignment Mappings

Map domain residues to ECOD template residues using original HHsearch and DALI alignments.
This provides the actual residue-to-residue mappings needed for coverage calculations.

Input:
    - step17/{prefix}.confident_predictions: Confident domain-ECOD predictions
    - step5/{prefix}.hhsearch_hits: HHsearch alignments
    - step9/{prefix}.dali_good_hits: DALI alignments
    - ECOD_maps/{ecod_id}.map: PDB→ECOD residue numbering

Output:
    - {prefix}.step18_mappings: Domain predictions with template ranges

Overlap Criteria (stricter than Step 15):
    - Must have ≥33% overlap relative to domain A
    - If yes, must have either:
        - ≥50% overlap relative to A, OR
        - ≥50% overlap relative to B

Algorithm:
    1. Load confident predictions from step 17
    2. For each domain-ECOD prediction:
        a. Find overlapping HHsearch hits
        b. Find overlapping DALI hits
        c. Map aligned residues to ECOD canonical numbering
        d. Convert to range strings
    3. Write mappings (may be 'na' if no alignment found)
"""

from pathlib import Path
from typing import Set, List, Dict, Optional
import logging

from ..utils.ranges import parse_range, format_range
from ..io.parsers import parse_hhsearch_output

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


def load_ecod_map(map_file: Path) -> Dict[int, int]:
    """
    Load ECOD residue numbering map.

    Format: pdb_resid ecod_resid

    Args:
        map_file: ECOD map file path

    Returns:
        Dictionary mapping PDB residue ID to ECOD residue ID
    """
    resmap = {}

    if not map_file.exists():
        logger.warning(f"ECOD map not found: {map_file}")
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


def run_step18(
    prefix: str,
    working_dir: Path,
    data_dir: Path,
    **kwargs
) -> bool:
    """
    Get alignment mappings for confident predictions.

    Args:
        prefix: Structure identifier
        working_dir: Working directory containing input/output
        data_dir: Reference data directory
        **kwargs: Additional arguments (unused)

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Step 18: Getting alignment mappings for {prefix}")

    # Input files
    confident_file = working_dir / f"{prefix}.step17_confident_predictions"
    hhsearch_file = working_dir / f"{prefix}.hhsearch"  # Fixed: use .hhsearch not .hhsearch_hits
    dali_file = working_dir / f"{prefix}_good_hits"  # Fixed: use _good_hits not .dali_good_hits

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

    # Output file
    output_file = working_dir / f"{prefix}.step18_mappings"

    # Load HHsearch hits using proper parser
    hhsearch_alignments = parse_hhsearch_output(hhsearch_file)

    # Convert to format needed by downstream code
    hhsearch_hits = []
    for aln in hhsearch_alignments:
        # Build query and template residue sets from alignment
        query_resids = set(range(aln.query_start, aln.query_end + 1))
        template_resids = list(range(aln.template_start, aln.template_end + 1))

        hhsearch_hits.append({
            'ecod': aln.hit_id,
            'prob': aln.probability / 100.0,  # Convert from percentage
            'query_resids': query_resids,
            'template_resids': template_resids,
            'query_range': f"{aln.query_start}-{aln.query_end}",
            'template_range': f"{aln.template_start}-{aln.template_end}"
        })

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
                ecod_id = parts[2]  # Fixed: ecodkey is column 2, not 1
                zscore = float(parts[4])  # Already in correct format, no need to divide
                query_range = parts[9]
                template_range = parts[10]

                query_resids = set(parse_range(query_range))
                template_resids = list(parse_range(template_range))

                dali_hits.append({
                    'ecod': ecod_id,
                    'zscore': zscore,
                    'query_resids': query_resids,
                    'template_resids': template_resids,
                    'query_range': query_range,
                    'template_range': template_range
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
                    if check_overlap_strict(domain_resids, hit['query_resids']):
                        # Load ECOD map
                        ecod_map = load_ecod_map(ecod_maps_dir / f"{ecod_ref}.map")

                        # Map template residues to ECOD canonical numbering
                        mapped_resids = []
                        for tres in hit['template_resids']:
                            if tres in ecod_map:
                                mapped_resids.append(ecod_map[tres])
                            # If not in map, keep original (for domains without mapping)

                        if mapped_resids:
                            hh_template_range = format_range(mapped_resids)
                        break

            # Find overlapping DALI hit for this ECOD
            dali_template_range = 'na'

            for hit in dali_hits:
                if hit['ecod'] == ecod_ref:
                    if check_overlap_strict(domain_resids, hit['query_resids']):
                        # DALI residues are already in ECOD numbering from step 9
                        dali_template_range = format_range(hit['template_resids'])
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
    hh_mapped = sum(1 for r in results if not r.endswith('na\tna'))
    dali_mapped = sum(1 for r in results if not r.split('\t')[-1] == 'na')
    both_mapped = sum(1 for r in results if 'na\tna' not in r and not r.endswith('\tna'))

    logger.info(f"  HHsearch mapped: {hh_mapped}/{len(results)}")
    logger.info(f"  DALI mapped: {dali_mapped}/{len(results)}")
    logger.info(f"  Both mapped: {both_mapped}/{len(results)}")

    return True
