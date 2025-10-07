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
    Read ECOD domain numbers from map2ecod.result file.
    
    Args:
        file_path: Path to map2ecod.result
    
    Returns:
        Set of ECOD domain numbers
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
            if words:
                ecod_num = words[0]
                domains.add(ecod_num)
    
    logger.debug(f"Read {len(domains)} domains from map2ecod")
    return domains


def read_domains_from_foldseek(file_path: Path) -> Set[str]:
    """
    Read ECOD domain numbers from foldseek.flt.result file.
    
    Args:
        file_path: Path to foldseek.flt.result
    
    Returns:
        Set of ECOD domain numbers
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
    working_dir: Path
) -> bool:
    """
    Run Step 6: Merge DALI candidates.
    
    Combines unique ECOD domains from:
    - Step 5: HHsearch → ECOD mapping
    - Step 4: Foldseek filtered results
    
    Args:
        prefix: Structure prefix
        working_dir: Working directory
    
    Returns:
        True if successful
    """
    logger.info(f"=== Step 6: Get DALI Candidates for {prefix} ===")
    
    try:
        map_ecod_file = working_dir / f'{prefix}.map2ecod.result'
        foldseek_file = working_dir / f'{prefix}.foldseek.flt.result'
        output_file = working_dir / f'{prefix}_hits4Dali'
        
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
