"""
Step 1: Structure Preparation and Validation.

Extracts sequences from CIF/PDB files and creates standardized PDB format.
Combines functionality of step1_get_AFDB_seqs.py and step1_get_AFDB_pdbs.py
"""

from pathlib import Path
from typing import Tuple, Optional
import subprocess

from dpam.io.readers import (
    read_fasta,
    extract_sequence_from_cif,
    read_structure_from_cif,
    read_structure_from_pdb
)
from dpam.io.writers import write_fasta, write_pdb
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.prepare')


class StructurePreparationError(Exception):
    """Raised when structure preparation fails"""
    pass


def extract_sequence(
    prefix: str,
    working_dir: Path
) -> bool:
    """
    Extract sequence from structure file.
    
    Replicates step1_get_AFDB_seqs.py
    
    Args:
        prefix: Structure prefix
        working_dir: Working directory
    
    Returns:
        True if successful
    
    Raises:
        StructurePreparationError: If extraction fails
    """
    logger.info(f"Extracting sequence for {prefix}")
    
    cif_file = working_dir / f'{prefix}.cif'
    pdb_file = working_dir / f'{prefix}.pdb'
    fasta_file = working_dir / f'{prefix}.fa'
    
    # Check if FASTA already exists
    if fasta_file.exists():
        logger.debug(f"FASTA already exists: {fasta_file}")
        return True
    
    # Try CIF first
    if cif_file.exists():
        try:
            sequence = extract_sequence_from_cif(cif_file, chain_id='A')
            write_fasta(fasta_file, prefix, sequence)
            logger.info(f"Extracted sequence from CIF: {len(sequence)} residues")
            return True
        except Exception as e:
            logger.error(f"Failed to extract from CIF: {e}")
            raise StructurePreparationError(f"CIF extraction failed: {e}")
    
    # Try PDB with external tool
    elif pdb_file.exists():
        try:
            # Use pdb2fasta if available
            result = subprocess.run(
                ['pdb2fasta', str(pdb_file)],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output and fix header
            lines = result.stdout.strip().split('\n')
            if lines and lines[0].startswith('>'):
                header = lines[0].split(':')[0]
                sequence = ''.join(lines[1:])
                write_fasta(fasta_file, prefix, sequence)
                logger.info(f"Extracted sequence from PDB: {len(sequence)} residues")
                return True
            else:
                raise StructurePreparationError("Invalid pdb2fasta output")
        
        except subprocess.CalledProcessError as e:
            logger.error(f"pdb2fasta failed: {e}")
            raise StructurePreparationError(f"PDB extraction failed: {e}")
        except FileNotFoundError:
            logger.error("pdb2fasta not found in PATH")
            raise StructurePreparationError("pdb2fasta not available")
    
    else:
        raise StructurePreparationError("No structure file found (.cif or .pdb)")


def standardize_structure(
    prefix: str,
    working_dir: Path
) -> bool:
    """
    Create standardized PDB file with validation.
    
    Replicates step1_get_AFDB_pdbs.py
    
    Args:
        prefix: Structure prefix
        working_dir: Working directory
    
    Returns:
        True if successful
    
    Raises:
        StructurePreparationError: If standardization fails
    """
    logger.info(f"Standardizing structure for {prefix}")
    
    cif_file = working_dir / f'{prefix}.cif'
    pdb_file = working_dir / f'{prefix}.pdb'
    fasta_file = working_dir / f'{prefix}.fa'
    
    # Read FASTA sequence (ground truth)
    if not fasta_file.exists():
        raise StructurePreparationError("FASTA file not found")
    
    header, reference_seq = read_fasta(fasta_file)
    
    # Branch 1: CIF + FASTA
    if cif_file.exists() and fasta_file.exists():
        try:
            structure = read_structure_from_cif(cif_file, chain_id='A')
            
            # Validate sequence match
            if structure.sequence != reference_seq:
                # Check with gaps
                structure_seq_with_gaps = ""
                for i, ref_aa in enumerate(reference_seq):
                    resid = i + 1
                    if resid in structure.residue_coords:
                        idx = structure.residue_ids.index(resid)
                        structure_seq_with_gaps += structure.sequence[idx]
                    else:
                        structure_seq_with_gaps += "-"
                
                if structure_seq_with_gaps != reference_seq:
                    error_msg = f"Sequence mismatch for {prefix}"
                    logger.error(error_msg)
                    raise StructurePreparationError(error_msg)
            
            # Write standardized PDB
            write_pdb(pdb_file, structure, truncate_coords=True)
            logger.info(f"Standardized CIF to PDB: {len(structure.residue_ids)} residues")
            return True
        
        except Exception as e:
            logger.error(f"CIF standardization failed: {e}")
            raise StructurePreparationError(f"CIF processing failed: {e}")
    
    # Branch 2: PDB + FASTA (validation only)
    elif pdb_file.exists() and fasta_file.exists():
        try:
            structure = read_structure_from_pdb(pdb_file, chain_id='A')
            
            # Validate sequence
            if structure.sequence != reference_seq:
                error_msg = f"PDB sequence mismatch for {prefix}"
                logger.error(error_msg)
                raise StructurePreparationError(error_msg)
            
            # Rewrite PDB (standardizes format)
            write_pdb(pdb_file, structure, truncate_coords=True)
            logger.info(f"Validated and standardized PDB: {len(structure.residue_ids)} residues")
            return True
        
        except Exception as e:
            logger.error(f"PDB validation failed: {e}")
            raise StructurePreparationError(f"PDB processing failed: {e}")
    
    else:
        raise StructurePreparationError("Required files not found")


def run_step1(
    prefix: str,
    working_dir: Path
) -> bool:
    """
    Run complete Step 1: preparation and validation.
    
    Args:
        prefix: Structure prefix
        working_dir: Working directory
    
    Returns:
        True if successful
    """
    logger.info(f"=== Step 1: Structure Preparation for {prefix} ===")
    
    try:
        # Extract sequence
        extract_sequence(prefix, working_dir)
        
        # Standardize structure
        standardize_structure(prefix, working_dir)
        
        logger.info(f"Step 1 completed successfully for {prefix}")
        return True
    
    except StructurePreparationError as e:
        logger.error(f"Step 1 failed for {prefix}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in Step 1 for {prefix}: {e}")
        return False
