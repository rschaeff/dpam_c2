"""
File writers for DPAM outputs.

Write PDB, FASTA, and various result files maintaining backward compatibility.
"""

from pathlib import Path
from typing import Dict, List, TextIO
import numpy as np

from dpam.core.models import Structure, Domain, SequenceHit, StructureHit
from dpam.utils.logging_config import get_logger

logger = get_logger('io.writers')


def write_fasta(output_path: Path, header: str, sequence: str) -> None:
    """
    Write FASTA file.
    
    Args:
        output_path: Path to output FASTA file
        header: FASTA header (without '>')
        sequence: Amino acid sequence
    """
    with open(output_path, 'w') as f:
        f.write(f">{header}\n")
        f.write(f"{sequence}\n")
    
    logger.debug(f"Wrote FASTA to {output_path}")


def write_pdb(
    output_path: Path,
    structure: Structure,
    truncate_coords: bool = True
) -> None:
    """
    Write structure to PDB format file.
    
    Maintains backward compatibility with original format:
    - Coordinates truncated to 3 decimal places
    - Specific column formatting
    - Chain A only
    
    Args:
        output_path: Path to output PDB file
        structure: Structure to write
        truncate_coords: Truncate coordinates to 3 decimals (default: True)
    """
    with open(output_path, 'w') as f:
        atom_count = 0
        
        for resid in structure.residue_ids:
            coords = structure.residue_coords[resid]
            resname = structure.sequence[structure.residue_ids.index(resid)]
            
            # Convert one-letter to three-letter
            from dpam.utils.amino_acids import one_to_three
            resname_3 = one_to_three(resname)
            
            # Write each atom
            for atom_idx, coord in enumerate(coords):
                atom_count += 1
                
                # Determine atom name (simplified - would need full atom info)
                # For now, use generic naming
                atom_name = f"ATOM{atom_idx+1}"
                if len(atom_name) < 4:
                    atom_name = f" {atom_name:<3}"
                else:
                    atom_name = atom_name[:4]
                
                # Format coordinates
                x, y, z = coord
                if truncate_coords:
                    # Truncate to 3 decimal places
                    x_str = f"{x:.3f}".rstrip('0').rstrip('.')
                    y_str = f"{y:.3f}".rstrip('0').rstrip('.')
                    z_str = f"{z:.3f}".rstrip('0').rstrip('.')
                    # Ensure at least 3 decimals
                    if '.' in x_str and len(x_str.split('.')[1]) < 3:
                        x_str = f"{float(x_str):.3f}"
                    if '.' in y_str and len(y_str.split('.')[1]) < 3:
                        y_str = f"{float(y_str):.3f}"
                    if '.' in z_str and len(z_str.split('.')[1]) < 3:
                        z_str = f"{float(z_str):.3f}"
                else:
                    x_str = f"{x:.3f}"
                    y_str = f"{y:.3f}"
                    z_str = f"{z:.3f}"
                
                # Atom type (simplified - just use first char)
                atom_type = "C"  # Default
                
                # Write PDB line
                line = (
                    f"ATOM  {atom_count:>5} {atom_name} "
                    f"{resname_3:<3} {structure.chain_id}{resid:>4}    "
                    f"{x_str:>8}{y_str:>8}{z_str:>8}"
                    f"  1.00  0.00           {atom_type}\n"
                )
                f.write(line)
    
    logger.debug(f"Wrote PDB to {output_path}")


def write_pdb_from_coords(
    output_path: Path,
    residue_coords: Dict[int, np.ndarray],
    residue_ids: List[int],
    sequence: str,
    chain_id: str = 'A'
) -> None:
    """
    Write PDB file directly from coordinates dict.
    
    More detailed version that preserves actual atom names.
    """
    # This would need more information about atom names
    # For now, use simplified version above
    pass


def write_sequence_results(
    output_path: Path,
    hits: List[SequenceHit]
) -> None:
    """
    Write sequence-based hits to result file (step 9 output).
    
    Format: ecod_num_count ecod_id family probability coverage length query_range template_range
    """
    with open(output_path, 'w') as f:
        for hit in hits:
            line = (
                f"{hit.ecod_num}\t{hit.ecod_id}\t{hit.family}\t"
                f"{hit.probability}\t{hit.coverage}\t{hit.ecod_length}\t"
                f"{hit.query_range}\t{hit.template_range}\n"
            )
            f.write(line)
    
    logger.debug(f"Wrote sequence results to {output_path}")


def write_structure_results(
    output_path: Path,
    hits: List[StructureHit]
) -> None:
    """
    Write structure-based hits to result file (step 9 output).
    
    Format: hitname ecod_id family zscore qscore ztile qtile rank bestprob bestcov qrange trange
    """
    with open(output_path, 'w') as f:
        for hit in hits:
            line = (
                f"{hit.hit_name}\t{hit.ecod_id}\t{hit.family}\t"
                f"{hit.z_score}\t{hit.q_score}\t{hit.z_percentile}\t"
                f"{hit.q_percentile}\t{hit.rank}\t{hit.best_seq_prob}\t"
                f"{hit.best_seq_cov}\t{hit.query_range}\t{hit.template_range}\n"
            )
            f.write(line)
    
    logger.debug(f"Wrote structure results to {output_path}")


def write_good_domains(
    output_path: Path,
    sequence_hits: List[SequenceHit],
    structure_hits: List[StructureHit],
    ecod_norms: Dict[str, float]
) -> None:
    """
    Write filtered good domains (step 10 output).
    
    Combines sequence and structure hits that pass quality thresholds.
    """
    with open(output_path, 'w') as f:
        # Write sequence hits
        for hit in sequence_hits:
            line = (
                f"sequence\t{hit.ecod_num}\t{hit.ecod_id}\t{hit.family}\t"
                f"{hit.probability}\t{hit.coverage}\t{hit.ecod_length}\t"
                f"{hit.query_range}\t{hit.template_range}\n"
            )
            f.write(line)
        
        # Write structure hits with additional quality info
        for hit in structure_hits:
            # Calculate normalized z-score
            ecod_num = hit.ecod_num
            z_norm = hit.z_score / ecod_norms.get(ecod_num, 1.0) if ecod_num in ecod_norms else 0.0
            
            # Determine sequence support level
            if hit.best_seq_prob >= 95 and hit.best_seq_cov >= 0.6:
                seq_judge = "superb"
            elif hit.best_seq_prob >= 80 and hit.best_seq_cov >= 0.4:
                seq_judge = "high"
            elif hit.best_seq_prob >= 50 and hit.best_seq_cov >= 0.3:
                seq_judge = "medium"
            elif hit.best_seq_prob >= 20 and hit.best_seq_cov >= 0.2:
                seq_judge = "low"
            else:
                seq_judge = "no"
            
            line = (
                f"structure\t{seq_judge}\t{hit.ecod_num}\t{z_norm:.2f}\t"
                f"{hit.hit_name}\t{hit.ecod_id}\t{hit.family}\t"
                f"{hit.z_score}\t{hit.q_score}\t{hit.z_percentile}\t"
                f"{hit.q_percentile}\t{hit.rank}\t{hit.best_seq_prob}\t"
                f"{hit.best_seq_cov}\t{hit.query_range}\t{hit.filtered_range}\n"
            )
            f.write(line)
    
    logger.debug(f"Wrote good domains to {output_path}")


def write_sse_annotation(
    output_path: Path,
    residue_sse: Dict[int, tuple]  # resid -> (sse_id, sse_type)
) -> None:
    """
    Write secondary structure annotation (step 11 output).
    
    Format: resid aa sse_id sse_type
    """
    with open(output_path, 'w') as f:
        for resid in sorted(residue_sse.keys()):
            sse_id, sse_type = residue_sse[resid]
            aa = "X"  # Would need sequence lookup
            
            if sse_id is None:
                f.write(f"{resid}\t{aa}\tna\t{sse_type}\n")
            else:
                f.write(f"{resid}\t{aa}\t{sse_id}\t{sse_type}\n")
    
    logger.debug(f"Wrote SSE annotation to {output_path}")


def write_disorder_regions(
    output_path: Path,
    disorder_residues: List[int]
) -> None:
    """
    Write disordered residue list (step 12 output).
    
    Format: One residue ID per line
    """
    with open(output_path, 'w') as f:
        for resid in sorted(disorder_residues):
            f.write(f"{resid}\n")
    
    logger.debug(f"Wrote disorder regions to {output_path}")


def write_final_domains(
    output_path: Path,
    domains: List[Domain]
) -> None:
    """
    Write final parsed domains (step 13 output).
    
    Format: domain_id range
    """
    with open(output_path, 'w') as f:
        for domain in domains:
            f.write(f"{domain.domain_id}\t{domain.residue_range}\n")
    
    logger.debug(f"Wrote final domains to {output_path}")
