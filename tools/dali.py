"""
DALI tool wrapper.
"""

from pathlib import Path
from typing import Optional, List, Tuple, Set
import glob

from dpam.tools.base import ExternalTool
from dpam.utils.logging_config import get_logger

logger = get_logger('tools.dali')


class DALI(ExternalTool):
    """
    Wrapper for DALI structural alignment tool (dali.pl).
    """
    
    def __init__(self):
        super().__init__('dali.pl', check_available=True, required=True)
    
    def align(
        self,
        pdb1: Path,
        pdb2: Path,
        output_dir: Path,
        dat1_dir: Optional[Path] = None,
        dat2_dir: Optional[Path] = None
    ) -> Tuple[Optional[float], List[Tuple[int, int]]]:
        """
        Run DALI alignment between two structures.
        
        Args:
            pdb1: First PDB file (query)
            pdb2: Second PDB file (template)
            output_dir: Output directory for DALI files
            dat1_dir: Directory for DAT files (query)
            dat2_dir: Directory for DAT files (template)
        
        Returns:
            Tuple of (z_score, alignments)
            where alignments is list of (query_resid, template_resid) pairs
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.executable,
            '--pdbfile1', str(pdb1),
            '--pdbfile2', str(pdb2),
            '--outfmt', 'summary,alignments,transrot'
        ]
        
        if dat1_dir:
            cmd.extend(['--dat1', str(dat1_dir)])
        else:
            cmd.extend(['--dat1', './'])
        
        if dat2_dir:
            cmd.extend(['--dat2', str(dat2_dir)])
        else:
            cmd.extend(['--dat2', './'])
        
        log_file = output_dir / 'log'
        
        logger.debug(f"Running DALI alignment: {pdb1.name} vs {pdb2.name}")
        
        try:
            self._execute(cmd, cwd=output_dir, log_file=log_file, check=False)
        except Exception as e:
            logger.warning(f"DALI execution had issues: {e}")
        
        # Parse output files
        z_score, alignments = self._parse_dali_output(output_dir)
        
        return z_score, alignments
    
    def _parse_dali_output(
        self,
        output_dir: Path
    ) -> Tuple[Optional[float], List[Tuple[int, int]]]:
        """
        Parse DALI output files.
        
        Args:
            output_dir: Directory containing DALI output
        
        Returns:
            Tuple of (z_score, alignments)
        """
        # Find mol*.txt files
        mol_files = list(output_dir.glob('mol*.txt'))
        
        if not mol_files:
            logger.debug("No DALI output files found")
            return None, []
        
        # Read all mol files
        all_lines = []
        for mol_file in mol_files:
            with open(mol_file, 'r') as f:
                all_lines.extend(f.readlines())
        
        # Parse alignment
        z_score = 0.0
        query_ali = ""
        subject_ali = ""
        in_alignment = True
        
        for line in all_lines:
            words = line.split()
            
            if len(words) >= 2:
                if words[0] == 'Query':
                    query_ali += words[1]
                elif words[0] == 'Sbjct':
                    subject_ali += words[1]
                elif words[0] == 'No' and words[1] == '1:':
                    # Parse z-score
                    for word in words:
                        if '=' in word:
                            key, value = word.split('=')
                            if key == 'Z-score':
                                z_parts = value.split('.')
                                if len(z_parts) >= 2:
                                    z_score = float(f"{z_parts[0]}.{z_parts[1]}")
                elif words[0] == 'No' and words[1] == '2:':
                    # Stop at second hit
                    in_alignment = False
        
        # Parse alignment into residue pairs
        alignments = []
        q_pos = 0
        s_pos = 0
        
        for i in range(len(query_ali)):
            if query_ali[i] != '-':
                q_pos += 1
            if subject_ali[i] != '-':
                s_pos += 1
            
            if query_ali[i] != '-' and subject_ali[i] != '-':
                if query_ali[i].isupper() and subject_ali[i].isupper():
                    alignments.append((q_pos, s_pos))
        
        logger.debug(
            f"Parsed DALI output: z-score={z_score:.2f}, "
            f"aligned={len(alignments)}"
        )
        
        return z_score, alignments


def run_iterative_dali(
    query_pdb: Path,
    template_pdb: Path,
    template_ecod: str,
    data_dir: Path,
    output_dir: Path
) -> List[Tuple[str, float, int, int, int, List[Tuple[int, int]]]]:
    """
    Run iterative DALI alignment.
    
    Repeatedly align query against template, removing matched regions.
    
    Args:
        query_pdb: Query PDB file
        template_pdb: Template PDB file (from ECOD70)
        template_ecod: ECOD domain number
        data_dir: Data directory containing ECOD70
        output_dir: Output directory
    
    Returns:
        List of (hit_name, z_score, n_match, q_len, t_len, alignments)
    """
    logger.info(f"Starting iterative DALI for {template_ecod}")
    
    dali = DALI()
    
    # Create working directories
    tmp_dir = output_dir / f'tmp_{query_pdb.stem}_{template_ecod}'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    output_tmp_dir = tmp_dir / 'output_tmp'
    output_tmp_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy query PDB to tmp directory
    import shutil
    work_pdb = tmp_dir / f'{query_pdb.stem}_{template_ecod}.pdb'
    shutil.copy(query_pdb, work_pdb)
    
    # Get template PDB from ECOD70
    template_path = data_dir / 'ECOD70' / f'{template_ecod}.pdb'
    
    if not template_path.exists():
        logger.warning(f"Template not found: {template_path}")
        return []
    
    # Read query residues
    with open(work_pdb, 'r') as f:
        query_resids = set()
        for line in f:
            if line.startswith('ATOM'):
                resid = int(line[22:26])
                query_resids.add(resid)
    
    all_query_resids = set(query_resids)
    
    hits = []
    iteration = 0
    
    while True:
        iteration += 1
        
        # Run DALI
        z_score, alignments = dali.align(
            work_pdb,
            template_path,
            output_tmp_dir,
            dat1_dir=output_tmp_dir,
            dat2_dir=output_tmp_dir
        )
        
        if z_score is None or len(alignments) < 20:
            logger.debug(f"No significant alignment in iteration {iteration}")
            break
        
        # Extract aligned residues
        query_resids_list = sorted(query_resids)
        aligned_query = [query_resids_list[q-1] for q, t in alignments]
        aligned_template = [t for q, t in alignments]
        
        # Convert to actual residue IDs
        actual_alignments = list(zip(aligned_query, aligned_template))
        
        # Record hit
        hit_name = f'{template_ecod}_{iteration}'
        q_len = len(query_resids)
        t_len = 0  # Would need to read from template
        
        hits.append((
            hit_name,
            z_score,
            len(alignments),
            q_len,
            t_len,
            actual_alignments
        ))
        
        logger.debug(
            f"Iteration {iteration}: z={z_score:.2f}, "
            f"aligned={len(alignments)}"
        )
        
        # Remove aligned regions from query
        from dpam.utils.ranges import residues_to_range, range_to_residues
        aligned_query_set = set(aligned_query)
        
        # Get range with gap tolerance
        aligned_range = residues_to_range(sorted(aligned_query), gap_tolerance=5)
        aligned_with_gaps = range_to_residues(aligned_range)
        
        remaining = query_resids - aligned_with_gaps
        
        if len(remaining) < 20:
            logger.debug("Insufficient residues remaining")
            break
        
        # Write new PDB with remaining residues
        with open(query_pdb, 'r') as fin:
            with open(work_pdb, 'w') as fout:
                for line in fin:
                    if line.startswith('ATOM'):
                        resid = int(line[22:26])
                        if resid in remaining:
                            fout.write(line)
        
        query_resids = remaining
        
        # Clean output directory
        for f in output_tmp_dir.glob('*'):
            if f.is_file():
                f.unlink()
    
    # Clean up
    shutil.rmtree(tmp_dir)
    
    logger.info(f"Iterative DALI completed: {len(hits)} hits")
    return hits
