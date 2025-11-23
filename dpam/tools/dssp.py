"""
DSSP tool wrapper for secondary structure assignment.
"""

from pathlib import Path
from typing import Optional, Dict
import os

from dpam.tools.base import ExternalTool
from dpam.core.models import SecondaryStructure
from dpam.utils.logging_config import get_logger

logger = get_logger('tools.dssp')


def find_dssp_executable() -> tuple[str, str]:
    """
    Find DSSP executable.

    Search order:
    1. DALI_HOME environment variable (for dsspcmbi)
    2. Standard installation at ~/src/Dali_v5/DaliLite.v5/bin (for dsspcmbi)
    3. System PATH for mkdssp
    4. System PATH for dsspcmbi

    Returns:
        Tuple of (path_to_executable, variant) where variant is 'dsspcmbi' or 'mkdssp'
    """
    # Check DALI_HOME for dsspcmbi
    if 'DALI_HOME' in os.environ:
        dali_home = Path(os.environ['DALI_HOME'])
        dsspcmbi = dali_home / 'bin' / 'dsspcmbi'
        if dsspcmbi.exists():
            logger.debug(f"Found dsspcmbi via DALI_HOME: {dsspcmbi}")
            return str(dsspcmbi), 'dsspcmbi'

    # Check standard installation for dsspcmbi
    home = Path.home()
    default_dsspcmbi = home / 'src' / 'Dali_v5' / 'DaliLite.v5' / 'bin' / 'dsspcmbi'
    if default_dsspcmbi.exists():
        logger.debug(f"Found dsspcmbi at default location: {default_dsspcmbi}")
        return str(default_dsspcmbi), 'dsspcmbi'

    # Check PATH for mkdssp
    import shutil
    mkdssp_result = shutil.which('mkdssp')
    if mkdssp_result:
        logger.debug(f"Found mkdssp in PATH: {mkdssp_result}")
        return mkdssp_result, 'mkdssp'

    # Check PATH for dsspcmbi
    dsspcmbi_result = shutil.which('dsspcmbi')
    if dsspcmbi_result:
        logger.debug(f"Found dsspcmbi in PATH: {dsspcmbi_result}")
        return dsspcmbi_result, 'dsspcmbi'

    # Not found - return mkdssp and let base class handle error
    return 'mkdssp', 'mkdssp'


class DSSP(ExternalTool):
    """
    Wrapper for DSSP secondary structure assignment.

    Supports both mkdssp (modern version) and dsspcmbi (DaliLite version).
    """

    def __init__(self):
        dssp_path, dssp_variant = find_dssp_executable()
        self.variant = dssp_variant
        super().__init__(dssp_path, check_available=True, required=True)
    
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

        Note:
            Supports both mkdssp (modern) and dsspcmbi (DaliLite) variants.
            - mkdssp v4.4+ uses positional arguments and requires explicit
              output format specification for classic DSSP format.
            - dsspcmbi uses simple: dsspcmbi PDB_File DSSP_File
            - Both require absolute paths
        """
        # Convert to absolute paths
        pdb_abs = pdb_file.resolve()
        output_abs = output_file.resolve()

        if self.variant == 'dsspcmbi':
            # dsspcmbi: simple interface with classic format
            cmd = [
                self.executable,
                '-c',  # Classic format
                str(pdb_abs),
                str(output_abs)
            ]
        else:
            # mkdssp: modern interface
            import os
            mmcif_dict = None
            if 'CONDA_PREFIX' in os.environ:
                mmcif_path = Path(os.environ['CONDA_PREFIX']) / 'share' / 'libcifpp' / 'mmcif_pdbx.dic'
                if mmcif_path.exists():
                    mmcif_dict = str(mmcif_path)

            cmd = [
                self.executable,
                '--output-format', 'dssp',
            ]

            if mmcif_dict:
                cmd.extend(['--mmcif-dictionary', mmcif_dict])

            cmd.extend([
                str(pdb_abs),
                str(output_abs)
            ])

        logger.info(f"Running DSSP ({self.variant}) for {pdb_file.name}")
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
