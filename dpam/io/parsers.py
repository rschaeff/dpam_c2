"""
Parsers for external tool outputs.

Parse HHsearch, Foldseek, DALI, and DSSP output files.
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional
import re

from dpam.core.models import (
    HHSearchAlignment,
    FoldseekHit,
    DALIAlignment,
    SecondaryStructure
)
from dpam.utils.logging_config import get_logger

logger = get_logger('io.parsers')


def parse_hhsearch_output(hhsearch_file: Path) -> List[HHSearchAlignment]:
    """
    Parse HHsearch output file.
    
    Args:
        hhsearch_file: Path to .hhsearch file
    
    Returns:
        List of HHSearchAlignment objects
    """
    logger.debug(f"Parsing HHsearch output: {hhsearch_file}")
    
    with open(hhsearch_file, 'r') as f:
        content = f.read()
    
    # Split by hits (each hit starts with ">")
    hits = content.split('\n>')[1:]  # Skip header
    
    alignments = []
    
    for hit in hits:
        lines = hit.split('\n')
        
        # Initialize variables
        hit_id = ""
        probability = 0.0
        evalue = "0"
        score = "0"
        aligned_cols = "0"
        identities = "0"
        similarity = "0"
        sum_probs = "0"
        
        query_start = 0
        query_end = 0
        query_seq = ""
        template_start = 0
        template_end = 0
        template_seq = ""
        
        # Parse header line
        for line in lines:
            if len(line) >= 6 and line[:6] == 'Probab':
                words = line.split()
                for word in words:
                    if '=' in word:
                        key, value = word.split('=', 1)
                        if key == 'Probab':
                            probability = float(value)
                        elif key == 'E-value':
                            evalue = value
                        elif key == 'Score':
                            score = value
                        elif key == 'Aligned_cols':
                            aligned_cols = value
                        elif key == 'Identities':
                            identities = value
                        elif key == 'Similarity':
                            similarity = value
                        elif key == 'Sum_probs':
                            sum_probs = value
            
            elif line.startswith('Q '):
                words = line.split()
                if len(words) >= 5 and words[1] not in ['ss_pred', 'Consensus']:
                    query_seq += words[3]
                    if query_start == 0:
                        query_start = int(words[2])
                    query_end = int(words[4])
            
            elif line.startswith('T '):
                words = line.split()
                if len(words) >= 5 and words[1] not in ['Consensus', 'ss_dssp', 'ss_pred']:
                    if not hit_id:
                        hit_id = words[1]
                    template_seq += words[3]
                    if template_start == 0:
                        template_start = int(words[2])
                    template_end = int(words[4])
        
        if hit_id and query_seq:
            alignments.append(HHSearchAlignment(
                hit_id=hit_id,
                probability=probability,
                evalue=evalue,
                score=score,
                aligned_cols=aligned_cols,
                identities=identities,
                similarity=similarity,
                sum_probs=sum_probs,
                query_start=query_start,
                query_end=query_end,
                query_seq=query_seq,
                template_start=template_start,
                template_end=template_end,
                template_seq=template_seq
            ))
    
    logger.debug(f"Parsed {len(alignments)} HHsearch hits")
    return alignments


def parse_foldseek_output(foldseek_file: Path) -> List[FoldseekHit]:
    """
    Parse Foldseek output file.
    
    Format: query target ... qstart qend ... evalue ...
    
    Args:
        foldseek_file: Path to .foldseek file
    
    Returns:
        List of FoldseekHit objects
    """
    logger.debug(f"Parsing Foldseek output: {foldseek_file}")
    
    hits = []
    
    with open(foldseek_file, 'r') as f:
        for line in f:
            words = line.split()
            if len(words) >= 11:
                ecod_num = words[1].split('.')[0]
                query_start = int(words[6])
                query_end = int(words[7])
                evalue = float(words[10])
                
                hits.append(FoldseekHit(
                    ecod_num=ecod_num,
                    evalue=evalue,
                    query_start=query_start,
                    query_end=query_end
                ))
    
    logger.debug(f"Parsed {len(hits)} Foldseek hits")
    return hits


def parse_dali_hits_file(dali_hits_file: Path) -> List[DALIAlignment]:
    """
    Parse iterative DALI hits file.
    
    Format:
    >hit_name z_score n_aligned q_len t_len
    query_resid template_resid
    ...
    
    Args:
        dali_hits_file: Path to DALI hits file
    
    Returns:
        List of DALIAlignment objects
    """
    logger.debug(f"Parsing DALI hits: {dali_hits_file}")
    
    alignments = []
    
    current_hit = None
    current_alignments = []
    
    with open(dali_hits_file, 'r') as f:
        for line in f:
            if line.startswith('>'):
                # Save previous hit
                if current_hit:
                    alignments.append(DALIAlignment(
                        hit_name=current_hit['name'],
                        ecod_num=current_hit['ecod_num'],
                        z_score=current_hit['z_score'],
                        n_aligned=current_hit['n_aligned'],
                        query_length=current_hit['q_len'],
                        template_length=current_hit['t_len'],
                        alignments=current_alignments
                    ))
                
                # Parse new hit header
                words = line[1:].split()
                hit_name = words[0]
                ecod_num = hit_name.split('_')[0]
                z_score = float(words[1])
                n_aligned = int(words[2])
                q_len = int(words[3])
                t_len = int(words[4])
                
                current_hit = {
                    'name': hit_name,
                    'ecod_num': ecod_num,
                    'z_score': z_score,
                    'n_aligned': n_aligned,
                    'q_len': q_len,
                    't_len': t_len
                }
                current_alignments = []
            
            else:
                # Parse alignment line
                words = line.split()
                if len(words) >= 2:
                    query_resid = int(words[0])
                    template_resid = int(words[1])
                    current_alignments.append((query_resid, template_resid))
        
        # Save last hit
        if current_hit:
            alignments.append(DALIAlignment(
                hit_name=current_hit['name'],
                ecod_num=current_hit['ecod_num'],
                z_score=current_hit['z_score'],
                n_aligned=current_hit['n_aligned'],
                query_length=current_hit['q_len'],
                template_length=current_hit['t_len'],
                alignments=current_alignments
            ))
    
    logger.debug(f"Parsed {len(alignments)} DALI alignments")
    return alignments


def parse_dssp_output(
    dssp_file: Path,
    sequence: str
) -> Dict[int, SecondaryStructure]:
    """
    Parse DSSP output file.
    
    Args:
        dssp_file: Path to .dssp file
        sequence: Protein sequence for validation
    
    Returns:
        Dict mapping residue_id -> SecondaryStructure
    """
    logger.debug(f"Parsing DSSP output: {dssp_file}")
    
    with open(dssp_file, 'r') as f:
        lines = f.readlines()
    
    # Find start of residue records
    start_parsing = False
    dssp_result = ""
    resids = []
    
    for line in lines:
        words = line.split()
        
        if len(words) > 3:
            if words[0] == '#' and words[1] == 'RESIDUE':
                start_parsing = True
                continue
            
            if start_parsing:
                try:
                    resid = int(line[5:10])
                except ValueError:
                    continue
                
                resids.append(resid)
                
                # Get secondary structure prediction
                pred = line[16]
                if pred == 'E' or pred == 'B':
                    newpred = 'E'  # Strand
                elif pred == 'G' or pred == 'H' or pred == 'I':
                    newpred = 'H'  # Helix
                else:
                    newpred = '-'  # Coil
                
                dssp_result += newpred
    
    # Validate length
    if len(resids) != len(sequence):
        logger.warning(
            f"DSSP length mismatch: {len(resids)} residues vs {len(sequence)} sequence"
        )
    
    # Parse into SSE segments
    res2sse = {}
    dssp_segs = dssp_result.split('--')
    posi = 0
    sse_id = 0
    
    for dssp_seg in dssp_segs:
        # Check if this is a valid SSE (3+ strands or 6+ helices)
        is_sse = (dssp_seg.count('E') >= 3 or dssp_seg.count('H') >= 6)
        
        if is_sse:
            sse_id += 1
        
        for char in dssp_seg:
            if posi < len(resids):
                resid = resids[posi]
                aa = sequence[posi] if posi < len(sequence) else 'X'
                
                if char != '-' and is_sse:
                    res2sse[resid] = SecondaryStructure(
                        residue_id=resid,
                        amino_acid=aa,
                        sse_id=sse_id,
                        sse_type=char
                    )
                else:
                    res2sse[resid] = SecondaryStructure(
                        residue_id=resid,
                        amino_acid=aa,
                        sse_id=None,
                        sse_type='C' if char == '-' else char
                    )
                
                posi += 1
        
        posi += 2  # Skip the '--' delimiter
    
    logger.debug(f"Parsed SSE for {len(res2sse)} residues, {sse_id} SSEs")
    return res2sse


def parse_good_domains_file(
    good_domains_file: Path
) -> Tuple[List[Tuple], List[Tuple]]:
    """
    Parse goodDomains file.
    
    Returns:
        Tuple of (sequence_hits, structure_hits)
    """
    logger.debug(f"Parsing good domains: {good_domains_file}")
    
    sequence_hits = []
    structure_hits = []
    
    with open(good_domains_file, 'r') as f:
        for line in f:
            words = line.split()
            
            if words[0] == 'sequence':
                # Parse sequence hit
                sequence_hits.append(tuple(words[1:]))
            
            elif words[0] == 'structure':
                # Parse structure hit
                structure_hits.append(tuple(words[1:]))
    
    logger.debug(
        f"Parsed {len(sequence_hits)} sequence hits, "
        f"{len(structure_hits)} structure hits"
    )
    
    return sequence_hits, structure_hits
