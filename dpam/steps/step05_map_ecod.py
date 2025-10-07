"""
Step 5: Map HHsearch Hits to ECOD Domains.

Maps PDB chains from HHsearch results to ECOD domain definitions,
calculating coverage metrics and filtering by quality thresholds.
"""

from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass

from dpam.core.models import ReferenceData, HHSearchAlignment
from dpam.io.parsers import parse_hhsearch_output
from dpam.utils.ranges import residues_to_range
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.map_ecod')


@dataclass
class ECODMapping:
    """Mapping of HHsearch hit to ECOD domain"""
    ecod_num: str
    ecod_id: str
    hh_prob: float
    hh_eval: str
    hh_score: str
    aligned_cols: str
    identities: str
    similarity: str
    sum_probs: str
    coverage: float
    ungapped_coverage: float
    query_range: str
    template_range: str
    template_seqid_range: str


def map_pdb_to_ecod(
    hit_id: str,
    alignment: HHSearchAlignment,
    ecod_pdbmap: Dict[str, Tuple[str, str, List[int]]],
    ecod_lengths: Dict[str, Tuple[str, int]],
    min_aligned: int = 10
) -> List[ECODMapping]:
    """
    Map a single HHsearch hit to ECOD domain(s).
    
    Args:
        hit_id: PDB chain ID (e.g., "2RSP_A")
        alignment: HHsearch alignment
        ecod_pdbmap: PDB chain to ECOD mapping
        ecod_lengths: ECOD domain lengths
        min_aligned: Minimum aligned residues to keep
    
    Returns:
        List of ECOD mappings for this hit
    """
    # Check if this PDB chain maps to ECOD
    if hit_id not in ecod_pdbmap:
        return []
    
    ecod_num, chain_id, pdb_residues = ecod_pdbmap[hit_id]
    
    # Build PDB residue to ECOD position mapping
    pdb_to_ecod_pos = {}
    for i, pdb_res in enumerate(pdb_residues):
        pdb_to_ecod_pos[pdb_res] = i + 1  # 1-indexed
    
    # Parse alignment to get aligned PDB residues
    qseq = alignment.query_seq
    hseq = alignment.template_seq
    
    if len(qseq) != len(hseq):
        logger.warning(f"Alignment length mismatch for {hit_id}")
        return []
    
    # Walk through alignment
    query_pos = alignment.query_start - 1
    template_pos = alignment.template_start - 1
    
    aligned_query = []
    aligned_template_pdb = []
    aligned_template_ecod = []
    
    for i in range(len(qseq)):
        if qseq[i] != '-':
            query_pos += 1
        if hseq[i] != '-':
            template_pos += 1
        
        # Both aligned (no gap)
        if qseq[i] != '-' and hseq[i] != '-':
            # Check if template position maps to ECOD
            if template_pos in pdb_to_ecod_pos:
                ecod_pos = pdb_to_ecod_pos[template_pos]
                aligned_query.append(query_pos)
                aligned_template_pdb.append(template_pos)
                aligned_template_ecod.append(ecod_pos)
    
    # Filter by minimum aligned residues
    if len(aligned_query) < min_aligned or len(aligned_template_ecod) < min_aligned:
        return []
    
    # Get ECOD metadata
    if ecod_num not in ecod_lengths:
        logger.warning(f"ECOD {ecod_num} not in lengths database")
        return []
    
    ecod_id, ecod_length = ecod_lengths[ecod_num]
    
    # Calculate coverage metrics
    coverage = round(len(aligned_template_ecod) / ecod_length, 3)
    
    # Ungapped coverage: span of aligned region
    ungapped_span = max(aligned_template_ecod) - min(aligned_template_ecod) + 1
    ungapped_coverage = round(ungapped_span / ecod_length, 3)
    
    # Format ranges
    query_range = residues_to_range(aligned_query, chain_id='')
    template_ecod_range = residues_to_range(aligned_template_ecod, chain_id='')
    template_pdb_range = residues_to_range(aligned_template_pdb, chain_id=chain_id)
    
    # Create mapping
    mapping = ECODMapping(
        ecod_num=ecod_num,
        ecod_id=ecod_id,
        hh_prob=alignment.probability,
        hh_eval=alignment.evalue,
        hh_score=alignment.score,
        aligned_cols=alignment.aligned_cols,
        identities=alignment.identities,
        similarity=alignment.similarity,
        sum_probs=alignment.sum_probs,
        coverage=coverage,
        ungapped_coverage=ungapped_coverage,
        query_range=query_range,
        template_range=template_ecod_range,
        template_seqid_range=template_pdb_range
    )
    
    return [mapping]


def run_step5(
    prefix: str,
    working_dir: Path,
    reference_data: ReferenceData
) -> bool:
    """
    Run Step 5: Map HHsearch hits to ECOD domains.
    
    Args:
        prefix: Structure prefix
        working_dir: Working directory
        reference_data: ECOD reference data
    
    Returns:
        True if successful
    """
    logger.info(f"=== Step 5: Map to ECOD for {prefix} ===")
    
    try:
        hhsearch_file = working_dir / f'{prefix}.hhsearch'
        output_file = working_dir / f'{prefix}.map2ecod.result'
        
        # Check input
        if not hhsearch_file.exists():
            logger.error(f"HHsearch file not found: {hhsearch_file}")
            return False
        
        # Parse HHsearch output
        logger.info("Parsing HHsearch alignments")
        alignments = parse_hhsearch_output(hhsearch_file)
        logger.info(f"Found {len(alignments)} HHsearch hits")
        
        # Map to ECOD
        all_mappings = []
        
        for alignment in alignments:
            hit_id = alignment.hit_id
            
            # Map this hit to ECOD domain(s)
            mappings = map_pdb_to_ecod(
                hit_id=hit_id,
                alignment=alignment,
                ecod_pdbmap=reference_data.ecod_pdbmap,
                ecod_lengths=reference_data.ecod_lengths,
                min_aligned=10
            )
            
            all_mappings.extend(mappings)
        
        logger.info(f"Mapped {len(all_mappings)} ECOD domains")
        
        # Write results
        with open(output_file, 'w') as f:
            # Header
            f.write('\t'.join([
                'uid',
                'ecod_domain_id',
                'hh_prob',
                'hh_eval',
                'hh_score',
                'aligned_cols',
                'idents',
                'similarities',
                'sum_probs',
                'coverage',
                'ungapped_coverage',
                'query_range',
                'template_range',
                'template_seqid_range'
            ]) + '\n')
            
            # Data rows
            for mapping in all_mappings:
                f.write('\t'.join([
                    mapping.ecod_num,
                    mapping.ecod_id,
                    str(mapping.hh_prob),
                    str(mapping.hh_eval),
                    str(mapping.hh_score),
                    str(mapping.aligned_cols),
                    str(mapping.identities),
                    str(mapping.similarity),
                    str(mapping.sum_probs),
                    str(mapping.coverage),
                    str(mapping.ungapped_coverage),
                    mapping.query_range,
                    mapping.template_range,
                    mapping.template_seqid_range
                ]) + '\n')
        
        logger.info(f"Step 5 completed successfully for {prefix}")
        logger.info(f"Output: {output_file}")
        return True
    
    except Exception as e:
        logger.error(f"Step 5 failed for {prefix}: {e}", exc_info=True)
        return False
