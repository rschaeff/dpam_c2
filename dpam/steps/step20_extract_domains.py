"""
Step 20: Extract Domain PDB Files

Extract PDB files for domains involved in merge candidates (from Step 19).
This creates individual PDB files needed for structural comparison in Step 21.

Input:
    - step19/{prefix}.result: Merge candidate pairs
    - {prefix}.pdb: Structure file with coordinates

Output:
    - step20/{prefix}_{domain}.pdb: Individual PDB files per merge candidate domain

Algorithm:
    1. Collect all domains from merge pairs
    2. Parse residue ranges for each domain
    3. Extract ATOM lines for each domain's residues
    4. Write individual PDB files
"""

from pathlib import Path
from typing import Set, List, Tuple
import logging

from ..utils.ranges import parse_range

logger = logging.getLogger(__name__)


def extract_domain_pdb(
    input_pdb: Path,
    output_pdb: Path,
    residues: Set[int]
) -> None:
    """
    Extract PDB file containing only specified residues.

    Args:
        input_pdb: Input structure file
        output_pdb: Output PDB file
        residues: Set of residue IDs to extract
    """
    output_pdb.parent.mkdir(parents=True, exist_ok=True)

    with open(input_pdb, 'r') as fin, open(output_pdb, 'w') as fout:
        for line in fin:
            if line.startswith('ATOM'):
                # PDB format: residue ID at columns 23-26 (0-indexed: 22-26)
                try:
                    resid = int(line[22:26].strip())
                    if resid in residues:
                        fout.write(line)
                except (ValueError, IndexError):
                    # Skip malformed lines
                    continue


def run_step20(
    prefix: str,
    working_dir: Path,
    **kwargs
) -> bool:
    """
    Extract PDB files for merge candidate domains.

    Args:
        prefix: Structure identifier
        working_dir: Working directory containing input/output
        **kwargs: Additional arguments (unused)

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Step 20: Extracting domain PDBs for {prefix}")

    # Input files
    merge_file = working_dir / f"{prefix}.step19_merge_candidates"
    input_pdb = working_dir / f"{prefix}.pdb"

    # Check if merge candidates exist
    if not merge_file.exists():
        logger.info(f"No merge candidates found for {prefix}")
        return True

    if not input_pdb.exists():
        logger.error(f"Structure file not found: {input_pdb}")
        return False

    # Output directory
    output_dir = working_dir / "step20"
    output_dir.mkdir(exist_ok=True)

    # Parse merge candidates
    domains_to_extract: List[Tuple[str, str, Set[int]]] = []
    seen_domains: Set[str] = set()

    with open(merge_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue

            parts = line.strip().split('\t')
            if len(parts) < 4:
                continue

            domain1, range1, domain2, range2 = parts[:4]

            # Add domain1 if not seen
            if domain1 not in seen_domains:
                resids1 = set(parse_range(range1))
                domains_to_extract.append((prefix, domain1, resids1))
                seen_domains.add(domain1)

            # Add domain2 if not seen
            if domain2 not in seen_domains:
                resids2 = set(parse_range(range2))
                domains_to_extract.append((prefix, domain2, resids2))
                seen_domains.add(domain2)

    if not domains_to_extract:
        logger.info(f"No domains to extract for {prefix}")
        return True

    logger.info(f"Extracting {len(domains_to_extract)} domain PDB files")

    # Extract each domain
    for prot, domain, residues in domains_to_extract:
        output_pdb = output_dir / f"{prot}_{domain}.pdb"

        try:
            extract_domain_pdb(input_pdb, output_pdb, residues)
            logger.debug(f"Extracted {domain}: {len(residues)} residues → {output_pdb.name}")
        except Exception as e:
            logger.error(f"Failed to extract {domain}: {e}")
            return False

    logger.info(f"Step 20 complete: {len(domains_to_extract)} PDB files extracted")
    return True
