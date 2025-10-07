"""
DSSP tool wrapper for secondary structure assignment.
"""

from pathlib import Path
from typing import Optional, Dict

from dpam.tools.base import ExternalTool
from dpam.core.models import SecondaryStructure
from dpam.utils.logging_config import get_logger

logger = get_logger('tools.dssp')


class DSSP(ExternalTool):
    """
    Wrapper for mkdssp (DSSP secondary structure assignment).
    """
    
    def __init__(self):
        super().__init__('mkdssp', check_available=True, required=True)
    
    def run(
        self,
        pdb_file: Path,
        output_file: Path,
        working_dir: Optional[Path] = None
    ) -> None:
        """
        Run DSSP on PDB file.
        
        Args:
            pdb_file: Input PDB file
            output_file: Output DSSP file
            working_dir: Working directory
        """
        cmd = [
            self.executable,
            '-i', str(pdb_file),
            '-o', str(output_file)
        ]
        
        logger.info(f"Running DSSP for {pdb_file.name}")
        self._execute(cmd, cwd=working_dir, capture_output=True)
        logger.info(f"DSSP completed: {output_file}")
    
    def run_and_parse(
        self,
        pdb_file: Path,
        sequence: str,
        working_dir: Optional[Path] = None
    ) -> Dict[int, SecondaryStructure]:
        """
        Run DSSP and parse results.
        
        Args:
            pdb_file: Input PDB file
            sequence: Protein sequence for validation
            working_dir: Working directory
        
        Returns:
            Dict mapping residue_id -> SecondaryStructure
        """
        dssp_file = pdb_file.with_suffix('.dssp')
        
        # Run DSSP
        self.run(pdb_file, dssp_file, working_dir)
        
        # Parse results
        from dpam.io.parsers import parse_dssp_output
        sse_dict = parse_dssp_output(dssp_file, sequence)
        
        # Clean up DSSP file
        if dssp_file.exists():
            dssp_file.unlink()
        
        return sse_dict
