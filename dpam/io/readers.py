"""
Structure file readers using Gemmi library.

Replaces pdbx with modern Gemmi for CIF and PDB parsing.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

try:
    import gemmi
except ImportError:
    raise ImportError(
        "Gemmi library required. Install with: pip install gemmi --break-system-packages"
    )

from dpam.core.models import Structure
from dpam.utils.amino_acids import three_to_one
from dpam.utils.logging_config import get_logger

logger = get_logger('io.readers')


def read_fasta(fasta_path: Path) -> Tuple[str, str]:
    """
    Read FASTA file.
    
    Args:
        fasta_path: Path to FASTA file
    
    Returns:
        Tuple of (header, sequence)
    """
    with open(fasta_path, 'r') as f:
        lines = f.readlines()
    
    header = ""
    sequence = ""
    
    for line in lines:
        line = line.strip()
        if line.startswith('>'):
            header = line[1:]
        else:
            sequence += line
    
    return header, sequence


def read_structure_from_cif(
    cif_path: Path,
    chain_id: str = 'A',
    model_num: Optional[int] = None
) -> Structure:
    """
    Read structure from mmCIF file using Gemmi.
    
    Args:
        cif_path: Path to CIF file
        chain_id: Chain to extract (default: 'A')
        model_num: Specific model number (None = use first/best)
    
    Returns:
        Structure object
    """
    logger.debug(f"Reading CIF file: {cif_path}")
    
    # Read structure
    structure = gemmi.read_structure(str(cif_path))
    
    # Get appropriate model
    if model_num is not None:
        model = structure[model_num]
    else:
        # Use first model if only one, else lowest numbered
        if len(structure) == 1:
            model = structure[0]
        else:
            model_numbers = [m.name for m in structure]
            try:
                min_model_idx = min(range(len(model_numbers)), 
                                  key=lambda i: int(model_numbers[i]))
                model = structure[min_model_idx]
            except ValueError:
                model = structure[0]
    
    # Extract chain
    try:
        chain = model[chain_id]
    except KeyError:
        raise ValueError(f"Chain {chain_id} not found in structure")
    
    # Extract residues and coordinates
    residue_coords = {}
    residue_ids = []
    sequence_parts = []
    
    # Track alternate locations
    resid_to_altloc = {}
    
    for residue in chain:
        resid = residue.seqid.num
        resname = residue.name

        # Skip HETATM records (only process ATOM records)
        if residue.het_flag == 'H':
            continue
        
        # Get amino acid
        aa = three_to_one(resname)
        
        # Handle alternate locations - take first encountered
        has_altloc = any(atom.altloc != '\0' for atom in residue)
        
        if has_altloc:
            if resid not in resid_to_altloc:
                # Record first altloc for this residue
                first_altloc = next(
                    atom.altloc for atom in residue 
                    if atom.altloc != '\0'
                )
                resid_to_altloc[resid] = first_altloc
        
        # Collect atom coordinates (skip hydrogens)
        coords = []
        for atom in residue:
            if atom.is_hydrogen():
                continue

            # Filter by alternate location
            if has_altloc:
                if atom.altloc == '\0' or atom.altloc == resid_to_altloc[resid]:
                    coords.append([atom.pos.x, atom.pos.y, atom.pos.z])
            else:
                coords.append([atom.pos.x, atom.pos.y, atom.pos.z])
        
        if coords:
            residue_coords[resid] = np.array(coords)
            if resid not in residue_ids:
                residue_ids.append(resid)
                sequence_parts.append(aa)
    
    sequence = ''.join(sequence_parts)
    prefix = cif_path.stem
    
    logger.debug(f"Extracted {len(residue_ids)} residues from chain {chain_id}")
    
    return Structure(
        prefix=prefix,
        sequence=sequence,
        residue_coords=residue_coords,
        residue_ids=residue_ids,
        chain_id=chain_id
    )


def read_structure_from_pdb(
    pdb_path: Path,
    chain_id: str = 'A'
) -> Structure:
    """
    Read structure from PDB file using Gemmi.
    
    Args:
        pdb_path: Path to PDB file
        chain_id: Chain to extract (default: 'A')
    
    Returns:
        Structure object
    """
    logger.debug(f"Reading PDB file: {pdb_path}")
    
    structure = gemmi.read_structure(str(pdb_path))
    model = structure[0]
    
    try:
        chain = model[chain_id]
    except KeyError:
        raise ValueError(f"Chain {chain_id} not found in structure")
    
    residue_coords = {}
    residue_ids = []
    sequence_parts = []
    
    for residue in chain:
        resid = residue.seqid.num
        resname = residue.name

        # Skip HETATM records
        if residue.het_flag == 'H':
            continue
        
        aa = three_to_one(resname)
        
        coords = []
        for atom in residue:
            if not atom.is_hydrogen():
                coords.append([atom.pos.x, atom.pos.y, atom.pos.z])
        
        if coords:
            residue_coords[resid] = np.array(coords)
            if resid not in residue_ids:
                residue_ids.append(resid)
                sequence_parts.append(aa)
    
    sequence = ''.join(sequence_parts)
    prefix = pdb_path.stem
    
    return Structure(
        prefix=prefix,
        sequence=sequence,
        residue_coords=residue_coords,
        residue_ids=residue_ids,
        chain_id=chain_id
    )


def extract_sequence_from_cif(cif_path: Path, chain_id: str = 'A') -> str:
    """
    Extract canonical sequence from CIF file (handles modified residues).
    
    This replicates the logic from step1_get_AFDB_seqs.py
    
    Args:
        cif_path: Path to CIF file
        chain_id: Chain to extract
    
    Returns:
        Sequence string
    """
    logger.debug(f"Extracting sequence from CIF: {cif_path}")
    
    doc = gemmi.cif.read_file(str(cif_path))
    block = doc.sole_block()
    
    # Parse modified residue mappings
    modinfo = {}
    if block.find_loop('_pdbx_struct_mod_residue.label_asym_id'):
        mod_table = block.find('_pdbx_struct_mod_residue.')
        for row in mod_table:
            chain = row.str(0)  # label_asym_id
            position = row.str(1)  # label_seq_id
            mod_resname = row.str(3)  # label_comp_id  
            parent_resname = row.str(2)  # parent_comp_id
            
            if chain not in modinfo:
                modinfo[chain] = {}
            modinfo[chain][position] = (mod_resname, parent_resname)
    
    # Extract sequence from pdbx_poly_seq_scheme
    sequence = []
    
    if block.find_loop('_pdbx_poly_seq_scheme.entity_id'):
        seq_table = block.find('_pdbx_poly_seq_scheme.')
        
        for row in seq_table:
            chain = row.str(1)  # asym_id
            if chain != chain_id:
                continue
            
            resname = row.str(2)  # mon_id
            position = row.str(3)  # seq_id
            
            # Try direct conversion
            aa = three_to_one(resname)
            
            # If unknown, check modified residue mapping
            if aa == 'X' and chain in modinfo and position in modinfo[chain]:
                mod_name, parent_name = modinfo[chain][position]
                if resname == mod_name:
                    aa = three_to_one(parent_name)
            
            sequence.append(aa)
    
    return ''.join(sequence)


def read_pae_matrix(json_path: Path) -> 'PAEMatrix':
    """
    Read PAE matrix from AlphaFold JSON file.
    
    Args:
        json_path: Path to JSON confidence file
    
    Returns:
        PAEMatrix object
    """
    import json
    from dpam.core.models import PAEMatrix
    
    logger.debug(f"Reading PAE from: {json_path}")
    
    with open(json_path, 'r') as f:
        # AlphaFold JSON has format [{ ... }]
        text = f.read()
        if text.startswith('['):
            text = text[1:-1]
        data = json.loads(text)
    
    return PAEMatrix.from_json(data)
