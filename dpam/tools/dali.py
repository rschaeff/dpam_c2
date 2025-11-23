"""
DALI tool wrapper.
"""

from pathlib import Path
from typing import Optional, List, Tuple, Set
import glob
import os

from dpam.tools.base import ExternalTool
from dpam.utils.logging_config import get_logger

logger = get_logger('tools.dali')


def find_dali_executable() -> str:
    """
    Find dali.pl executable.

    Search order:
    1. DALI_HOME environment variable
    2. Standard installation at ~/src/Dali_v5/DaliLite.v5/bin
    3. System PATH

    Returns:
        Path to dali.pl executable
    """
    # Check DALI_HOME
    if 'DALI_HOME' in os.environ:
        dali_home = Path(os.environ['DALI_HOME'])
        dali_pl = dali_home / 'bin' / 'dali.pl'
        if dali_pl.exists():
            logger.debug(f"Found dali.pl via DALI_HOME: {dali_pl}")
            return str(dali_pl)

    # Check standard installation
    home = Path.home()
    default_dali = home / 'src' / 'Dali_v5' / 'DaliLite.v5' / 'bin' / 'dali.pl'
    if default_dali.exists():
        logger.debug(f"Found dali.pl at default location: {default_dali}")
        return str(default_dali)

    # Fall back to PATH
    import shutil
    which_result = shutil.which('dali.pl')
    if which_result:
        logger.debug(f"Found dali.pl in PATH: {which_result}")
        return which_result

    # Not found - return bare name and let base class handle error
    return 'dali.pl'


class DALI(ExternalTool):
    """
    Wrapper for DALI structural alignment tool (dali.pl).
    """

    def __init__(self):
        dali_path = find_dali_executable()
        super().__init__(dali_path, check_available=True, required=True)

    def run(self, **kwargs):
        """Run DALI alignment (delegates to align method)"""
        return self.align(**kwargs)

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
            pdb1: First PDB file (query) - will be converted to absolute path
            pdb2: Second PDB file (template) - will be converted to absolute path
            output_dir: Output directory for DALI files
            dat1_dir: Directory for DAT files (query)
            dat2_dir: Directory for DAT files (template)

        Returns:
            Tuple of (z_score, alignments)
            where alignments is list of (query_resid, template_resid) pairs
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # CRITICAL: DALI requires a DAT subdirectory to exist
        dat_dir = output_dir / 'DAT'
        dat_dir.mkdir(exist_ok=True)

        # Check files exist before running (use absolute paths for checking)
        pdb1_abs = pdb1.resolve()
        pdb2_abs = pdb2.resolve()

        if not pdb1_abs.exists():
            logger.error(f"Query PDB not found: {pdb1_abs}")
            return None, []
        if not pdb2_abs.exists():
            logger.error(f"Template PDB not found: {pdb2_abs}")
            return None, []

        # CRITICAL: Use relative paths from output_dir to avoid DaliLite 80-char path limit
        # DALI will run with cwd=output_dir, so paths must be relative to there
        import os
        output_dir_abs = output_dir.resolve()

        pdb1_rel = Path(os.path.relpath(pdb1_abs, output_dir_abs))
        pdb2_rel = Path(os.path.relpath(pdb2_abs, output_dir_abs))

        cmd = [
            self.executable,
            '--pdbfile1', str(pdb1_rel),
            '--pdbfile2', str(pdb2_rel),
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
        logger.debug(f"  Query: {pdb1_abs}")
        logger.debug(f"  Template: {pdb2_abs}")

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
        z_score = None
        alignments = []

        for line in all_lines:
            words = line.split()

            # Parse Z-score from hit line
            # Format: "   1:  mol2-A  6.2  4.7  120   178   13"
            # Columns: No Chain Z rmsd lali nres %id
            # This line does NOT contain "<=>"
            if len(words) >= 3 and words[0].endswith(':') and '<=>' not in line:
                hit_num = words[0].rstrip(':')
                if hit_num == '1':
                    # First hit - get Z-score from column 2
                    try:
                        z_score = float(words[2])
                        logger.debug(f"Found Z-score: {z_score}")
                    except (ValueError, IndexError):
                        # Not a Z-score line, skip
                        pass

            # Parse structural equivalences
            # Format: "   1: mol1-A mol2-A     2 -  25 <=>    1 -  24  ..."
            # Words: [0]1: [1]mol1-A [2]mol2-A [3]2 [4]- [5]25 [6]<=> [7]1 [8]- [9]24
            elif len(words) >= 10 and words[0].endswith(':') and '<=>' in line:
                try:
                    # Extract ranges
                    arrow_idx = words.index('<=>')

                    # Query range: words[3] and words[5]
                    q_start = int(words[3])
                    q_end = int(words[5])

                    # Template range: words[arrow_idx+1] and words[arrow_idx+3]
                    t_start = int(words[arrow_idx + 1])
                    t_end = int(words[arrow_idx + 3])

                    # Add all aligned pairs in this segment
                    q_len = q_end - q_start + 1
                    t_len = t_end - t_start + 1

                    if q_len == t_len:
                        for i in range(q_len):
                            alignments.append((q_start + i, t_start + i))
                    else:
                        logger.warning(f"Unequal segment lengths: q={q_len}, t={t_len}")
                except (ValueError, IndexError) as e:
                    logger.debug(f"Could not parse alignment segment: {line.strip()} - {e}")
                    pass

        if z_score is not None:
            logger.debug(
                f"Parsed DALI output: z-score={z_score:.2f}, "
                f"aligned={len(alignments)}"
            )
        else:
            logger.debug("No DALI hits found")

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
