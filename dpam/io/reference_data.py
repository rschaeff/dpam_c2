"""
Load ECOD reference database files.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dpam.core.models import ReferenceData
from dpam.utils.logging_config import get_logger

logger = get_logger('io.reference_data')


def load_ecod_lengths(data_dir: Path) -> Dict[str, Tuple[str, int]]:
    """
    Load ECOD_length file.
    
    Format: ecod_num ecod_key length
    Example: 000000003 e2rspA1 124
    
    Returns:
        Dict mapping ecod_num -> (ecod_key, length)
    """
    file_path = data_dir / 'ECOD_length'
    logger.debug(f"Loading ECOD lengths from {file_path}")
    
    ecod_lengths = {}
    with open(file_path, 'r') as f:
        for line in f:
            words = line.split()
            if len(words) >= 3:
                ecod_num = words[0]
                ecod_key = words[1]
                length = int(words[2])
                ecod_lengths[ecod_num] = (ecod_key, length)
    
    logger.info(f"Loaded {len(ecod_lengths)} ECOD domain lengths")
    return ecod_lengths


def load_ecod_norms(data_dir: Path) -> Dict[str, float]:
    """
    Load ECOD_norms file.
    
    Format: ecod_num norm_value
    Example: 000423727 27.3
    
    Returns:
        Dict mapping ecod_num -> norm_value
    """
    file_path = data_dir / 'ECOD_norms'
    logger.debug(f"Loading ECOD norms from {file_path}")
    
    ecod_norms = {}
    with open(file_path, 'r') as f:
        for line in f:
            words = line.split()
            if len(words) >= 2:
                ecod_num = words[0]
                norm_value = float(words[1])
                ecod_norms[ecod_num] = norm_value
    
    logger.info(f"Loaded {len(ecod_norms)} ECOD norms")
    return ecod_norms


def load_ecod_pdbmap(data_dir: Path) -> Dict[str, Tuple[str, str, List[int]]]:
    """
    Load ECOD_pdbmap file.
    
    Format: ecod_num pdb_id chain:ranges
    Example: 000000003 2rsp A:1-124
    
    Returns:
        Dict mapping pdb_chain -> (ecod_num, chain_id, residue_list)
    """
    file_path = data_dir / 'ECOD_pdbmap'
    logger.debug(f"Loading ECOD PDB map from {file_path}")
    
    pdb_map = {}
    with open(file_path, 'r') as f:
        for line in f:
            words = line.split()
            if len(words) >= 3:
                ecod_num = words[0]
                pdb_id = words[1]
                segments = words[2].split(',')
                
                # Parse segments
                chain_ids = set()
                residues = []
                
                for segment in segments:
                    chain_id = segment.split(':')[0]
                    chain_ids.add(chain_id)
                    
                    range_part = segment.split(':')[1]
                    if '-' in range_part:
                        start, end = map(int, range_part.split('-'))
                        residues.extend(range(start, end + 1))
                    else:
                        residues.append(int(range_part))
                
                # Only single-chain domains
                if len(chain_ids) == 1:
                    chain_id = list(chain_ids)[0]
                    pdb_chain = f"{pdb_id.upper()}_{chain_id}"
                    pdb_map[pdb_chain] = (ecod_num, chain_id, residues)
    
    logger.info(f"Loaded {len(pdb_map)} PDB chain mappings")
    return pdb_map


def load_ecod_domains_file(data_dir: Path) -> Dict[str, Tuple[str, str]]:
    """
    Load ecod.latest.domains file.
    
    Format: Tab-separated with ecod_num, ecod_id, and family info
    
    Returns:
        Dict mapping ecod_num -> (ecod_id, family)
    """
    file_path = data_dir / 'ecod.latest.domains'
    logger.debug(f"Loading ECOD domains file from {file_path}")
    
    ecod_metadata = {}
    with open(file_path, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            
            words = line.rstrip('\n').split('\t')
            if len(words) >= 4:
                ecod_num = words[0]
                ecod_id = words[1]
                # Family is first two levels of architecture (e.g., "1.1" from "1.1.2.3")
                family = '.'.join(words[3].split('.')[:2])
                ecod_metadata[ecod_num] = (ecod_id, family)
    
    logger.info(f"Loaded {len(ecod_metadata)} ECOD domain metadata entries")
    return ecod_metadata


def load_ecod_weights(
    data_dir: Path,
    ecod_num: str
) -> Optional[Dict[int, float]]:
    """
    Load position weights for specific ECOD domain.
    
    Format: position ... ... weight
    
    Returns:
        Dict mapping position -> weight, or None if file doesn't exist
    """
    file_path = data_dir / 'ecod_weights' / f'{ecod_num}.weight'
    
    if not file_path.exists():
        return None
    
    weights = {}
    total_weight = 0.0
    
    with open(file_path, 'r') as f:
        for line in f:
            words = line.split()
            if len(words) >= 4:
                position = int(words[0])
                weight = float(words[3])
                weights[position] = weight
                total_weight += weight
    
    return weights


def load_ecod_domain_info(
    data_dir: Path,
    ecod_num: str
) -> Optional[Tuple[List[float], List[float]]]:
    """
    Load z-scores and q-scores for specific ECOD domain.
    
    Format: ... zscore qscore
    
    Returns:
        Tuple of (zscores, qscores), or None if file doesn't exist
    """
    file_path = data_dir / 'ecod_domain_info' / f'{ecod_num}.info'
    
    if not file_path.exists():
        return None
    
    zscores = []
    qscores = []
    
    with open(file_path, 'r') as f:
        for line in f:
            words = line.split()
            if len(words) >= 3:
                zscores.append(float(words[1]))
                qscores.append(float(words[2]))
    
    return zscores, qscores


def load_ecod_data(data_dir: Path) -> ReferenceData:
    """
    Load all ECOD reference data.
    
    Args:
        data_dir: Directory containing ECOD files
    
    Returns:
        ReferenceData object with all loaded data
    """
    logger.info(f"Loading ECOD reference data from {data_dir}")
    
    ecod_lengths = load_ecod_lengths(data_dir)
    ecod_norms = load_ecod_norms(data_dir)
    ecod_pdbmap = load_ecod_pdbmap(data_dir)
    ecod_metadata = load_ecod_domains_file(data_dir)
    
    # Note: ecod_weights and ecod_domain_info are loaded on-demand
    # since there are potentially millions of files
    
    return ReferenceData(
        ecod_lengths=ecod_lengths,
        ecod_norms=ecod_norms,
        ecod_pdbmap=ecod_pdbmap,
        ecod_domain_info={},  # Loaded on demand
        ecod_weights={},  # Loaded on demand
        ecod_metadata=ecod_metadata
    )
