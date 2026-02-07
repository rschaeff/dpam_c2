"""
Step 6: Get DALI Candidates.

Merges domain candidates from HHsearch mapping (step 5) and
Foldseek filtering (step 4) into a unified list for DALI alignment.
"""

from pathlib import Path
from typing import Set

from dpam.utils.logging_config import get_logger

logger = get_logger('steps.dali_candidates')


def read_domains_from_map_ecod(file_path: Path) -> Set[str]:
    """
    Read ECOD domain UIDs from map2ecod.result file.

    Reads the uid column (first column) to get numeric ECOD IDs
    like '001822778' that correspond to PDB filenames in ECOD70/.

    Args:
        file_path: Path to map2ecod.result

    Returns:
        Set of ECOD UIDs (e.g., '001822778')
    """
    domains = set()

    if not file_path.exists():
        logger.warning(f"Map2ecod file not found: {file_path}")
        return domains

    with open(file_path, 'r') as f:
        for i, line in enumerate(f):
            if i == 0:  # Skip header
                continue

            words = line.split()
            if len(words) >= 1:
                uid = words[0]  # First column: uid (numeric ECOD ID)
                domains.add(uid)

    logger.debug(f"Read {len(domains)} domains from map2ecod")
    return domains


def read_domains_from_foldseek(file_path: Path) -> Set[str]:
    """
    Read ECOD domain IDs from foldseek.flt.result file.

    Args:
        file_path: Path to foldseek.flt.result

    Returns:
        Set of ECOD domain IDs (e.g., 'e2rspA1')
    """
    domains = set()
    
    if not file_path.exists():
        logger.warning(f"Foldseek filtered file not found: {file_path}")
        return domains
    
    with open(file_path, 'r') as f:
        for i, line in enumerate(f):
            if i == 0:  # Skip header
                continue
            
            words = line.split()
            if words:
                ecod_num = words[0]
                domains.add(ecod_num)
    
    logger.debug(f"Read {len(domains)} domains from foldseek")
    return domains


def run_step6(
    prefix: str,
    working_dir: Path,
    path_resolver=None
) -> bool:
    """
    Run Step 6: Merge DALI candidates.

    Combines unique ECOD domains from:
    - Step 5: HHsearch -> ECOD mapping
    - Step 4: Foldseek filtered results

    Args:
        prefix: Structure prefix
        working_dir: Working directory
        path_resolver: Optional PathResolver for sharded output directories

    Returns:
        True if successful
    """
    from dpam.core.path_resolver import PathResolver
    resolver = path_resolver or PathResolver(working_dir, sharded=False)

    logger.info(f"=== Step 6: Get DALI Candidates for {prefix} ===")

    try:
        # Input from step 5
        map_ecod_file = resolver.step_dir(5) / f'{prefix}.map2ecod.result'
        # Input from step 4
        foldseek_file = resolver.step_dir(4) / f'{prefix}.foldseek.flt.result'
        # Output to step 6 directory
        output_file = resolver.step_dir(6) / f'{prefix}_hits4Dali'
        
        # Read domains from both sources
        domains_from_hhsearch = read_domains_from_map_ecod(map_ecod_file)
        domains_from_foldseek = read_domains_from_foldseek(foldseek_file)
        
        # Merge (union)
        all_domains = domains_from_hhsearch | domains_from_foldseek
        
        if not all_domains:
            logger.warning(f"No DALI candidates found for {prefix}")
            # Still create empty file for pipeline consistency
            with open(output_file, 'w') as f:
                pass
            return True
        
        logger.info(
            f"Merged candidates: {len(domains_from_hhsearch)} from HHsearch + "
            f"{len(domains_from_foldseek)} from Foldseek = "
            f"{len(all_domains)} unique domains"
        )
        
        # Write candidates (sorted for reproducibility)
        with open(output_file, 'w') as f:
            for domain in sorted(all_domains):
                f.write(f"{domain}\n")
        
        logger.info(f"Step 6 completed successfully for {prefix}")
        logger.info(f"Output: {output_file} ({len(all_domains)} candidates)")
        return True
    
    except Exception as e:
        logger.error(f"Step 6 failed for {prefix}: {e}", exc_info=True)
        return False
