"""
DALI tool wrapper.
"""

from pathlib import Path
from typing import Optional, List, Tuple, Set
import glob
import os
import re

# DALI alignment line format:
#   "   1: mol1-A mol2-A     2 -  25 <=>    1 -  24   (...)"      3-digit
#   "   1: mol1-A mol2-A  1014 -1044 <=>    2 -  32   (...)"      4-digit (dash attaches to end)
#   "   1: mol1-A mol2-A 12345-67890 <=> 12345-67890   (...)"     5-digit (no spaces)
# Splitting on whitespace is unreliable because DALI uses fixed-width formatting
# that swallows spaces when residue numbers grow. Use regex on the original line
# to extract the four residue indices regardless of internal spacing.
_DALI_ALIGN_RE = re.compile(
    r':\s+\S+\s+\S+\s+(\d+)\s*-\s*(\d+)\s+<=>\s+(\d+)\s*-\s*(\d+)'
)

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
    ) -> Tuple[Optional[float], List[Tuple[int, int]], List[str], List[str]]:
        """
        Run DALI alignment between two structures.

        Args:
            pdb1: First PDB file (query) - will be converted to absolute path
            pdb2: Second PDB file (template) - will be converted to absolute path
            output_dir: Output directory for DALI files
            dat1_dir: Directory for DAT files (query)
            dat2_dir: Directory for DAT files (template)

        Returns:
            Tuple of (z_score, alignments, rotation_rows, translation_vals)
            where alignments is list of (query_resid, template_resid) pairs,
            rotation_rows is list of 3 tab-separated rotation value strings,
            translation_vals is list of 3 translation value strings
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
        z_score, alignments, rotation_rows, translation_vals = self._parse_dali_output(output_dir)

        return z_score, alignments, rotation_rows, translation_vals
    
    def _parse_dali_output(
        self,
        output_dir: Path
    ) -> Tuple[Optional[float], List[Tuple[int, int]], List[str], List[str]]:
        """
        Parse DALI output files.

        Args:
            output_dir: Directory containing DALI output

        Returns:
            Tuple of (z_score, alignments, rotation_rows, translation_vals)
            - rotation_rows: list of 3 tab-separated strings like "val1\tval2\tval3"
            - translation_vals: list of 3 translation values as strings
        """
        # Find mol*.txt files
        mol_files = list(output_dir.glob('mol*.txt'))

        if not mol_files:
            logger.debug("No DALI output files found")
            return None, [], [], []

        # Read all mol files
        all_lines = []
        for mol_file in mol_files:
            with open(mol_file, 'r') as f:
                all_lines.extend(f.readlines())

        # Parse alignment
        z_score = None
        alignments = []
        matrix_lines = []  # Raw -matrix lines
        getit = True  # Only parse first hit (matches v1.0)

        for line in all_lines:
            words = line.split()

            if not getit:
                break

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
                elif hit_num == '2':
                    # Second hit - stop parsing (matches v1.0 behavior)
                    getit = False

            # Parse structural equivalences. See _DALI_ALIGN_RE comment for why
            # token-position parsing is unreliable here.
            elif len(words) >= 4 and words[0].endswith(':') and '<=>' in line:
                m = _DALI_ALIGN_RE.search(line)
                if m:
                    q_start, q_end, t_start, t_end = (int(g) for g in m.groups())
                    q_len = q_end - q_start + 1
                    t_len = t_end - t_start + 1
                    if q_len == t_len:
                        for i in range(q_len):
                            alignments.append((q_start + i, t_start + i))
                    else:
                        logger.warning(f"Unequal segment lengths: q={q_len}, t={t_len}")
                else:
                    logger.debug(f"Could not parse alignment segment: {line.strip()}")

            # Parse rotation/translation matrix
            # Format: -matrix  "mol1-A mol2-A  U(1,.)  rot1 rot2 rot3  trans"
            # After splitting: words[4:7] = rotation, words[7] = translation (with trailing ")
            elif len(words) >= 8 and words[0] == "-matrix":
                matrix_lines.append(line)

        # Extract rotation and translation from -matrix lines
        rotation_rows = []
        translation_vals = []

        for mat_line in matrix_lines:
            # Strip trailing newline and closing quote
            stripped = mat_line.rstrip()
            if stripped.endswith('"'):
                stripped = stripped[:-1]
            mat_words = stripped.split()
            if len(mat_words) >= 8:
                # words[4:7] = 3 rotation values, words[7] = translation value
                rotation_rows.append('\t'.join(mat_words[4:7]))
                translation_vals.append(mat_words[7])

        if z_score is not None:
            logger.debug(
                f"Parsed DALI output: z-score={z_score:.2f}, "
                f"aligned={len(alignments)}, "
                f"rot_rows={len(rotation_rows)}"
            )
        else:
            logger.debug("No DALI hits found")

        return z_score, alignments, rotation_rows, translation_vals


class RustDALI:
    """
    Rust-based DALI structural alignment.

    Drop-in replacement for DALI class. Key differences:
    - No subprocess: calls Rust library directly via PyO3
    - Alignments use 1-based sequential numbering (same as Fortran .dat convention)
    - When template .dat file is available, uses it directly (bypasses Rust DSSP,
      eliminates DSSP divergence vs Fortran dsspcmbi)
    """

    def __init__(self, dat_dir: Optional[Path] = None):
        """
        Args:
            dat_dir: Optional directory containing pre-computed .dat files.
                     When set, template .dat files are looked up here before
                     falling back to PDB import. Use Fortran-generated .dat
                     files to eliminate DSSP divergence.
        """
        self.dat_dir = Path(dat_dir) if dat_dir else None

    def align(
        self,
        pdb1: Path,
        pdb2: Path,
        output_dir: Path,
        dat1_dir: Optional[Path] = None,
        dat2_dir: Optional[Path] = None,
    ) -> Tuple[Optional[float], List[Tuple[int, int]], List[str], List[str]]:
        """
        Run DALI alignment between two structures using Rust backend.

        If a pre-computed .dat file exists for the template (in self.dat_dir
        or dat2_dir), it is used directly, bypassing Rust DSSP computation.

        Returns same signature as DALI.align():
            (z_score, alignments, rotation_rows, translation_vals)
        """
        try:
            import dali as dali_rust
        except ImportError:
            logger.error("Rust dali module not available")
            return None, [], [], []

        pdb1_abs = str(Path(pdb1).resolve())
        pdb2_abs = str(Path(pdb2).resolve())

        # Look for pre-computed .dat file for template (bypasses Rust DSSP)
        template_dat = None
        template_stem = Path(pdb2).stem
        for search_dir in [self.dat_dir, dat2_dir]:
            if search_dir is not None:
                candidate = Path(search_dir) / f'{template_stem}.dat'
                if candidate.exists():
                    template_dat = str(candidate.resolve())
                    break

        try:
            result = dali_rust.align_pdb(
                pdb1_abs, pdb2_abs,
                query_chain="", template_chain="",
                query_code="mol1", template_code="mol2",
                template_dat=template_dat,
            )
        except Exception as e:
            logger.warning(f"Rust DALI alignment failed: {e}")
            return None, [], [], []

        if result is None:
            return None, [], [], []

        # Format rotation rows as tab-separated strings (matches Fortran output)
        rotation_rows = [
            '\t'.join(f'{v:.6f}' for v in row) for row in result.rotation
        ]
        # Format translation values as strings
        translation_vals = [f'{v:.6f}' for v in result.translation]

        return result.zscore, result.alignments, rotation_rows, translation_vals

    def iterative_search(
        self,
        query_pdb: Path,
        template_pdb: Path,
        template_dat_path: Optional[str] = None,
        min_aligned: int = 20,
        min_zscore: float = 2.0,
        gap_tolerance: int = 5,
        max_rounds: int = 10,
    ) -> List[Tuple[float, int, int, List[Tuple[int, int]], List[str], List[str]]]:
        """
        Run full iterative DALI in Rust (single FFI call for the entire loop).

        Imports query and template into a temporary ProteinStore, runs
        iterative_search natively in Rust (search → mask → repeat), and
        maps alignment indices back to PDB residue IDs.

        Args:
            query_pdb: Path to query PDB file
            template_pdb: Path to template PDB file
            template_dat_path: Optional pre-computed .dat file for the template.
                If None and self.dat_dir is set, looks up by template PDB stem.
            min_aligned: Minimum aligned residues per hit (default 20)
            min_zscore: Z-score threshold (default 2.0)
            gap_tolerance: Gap bridging for masking (default 5)
            max_rounds: Maximum iteration rounds (default 10)

        Returns:
            List of (z_score, n_aligned, qlen, alignments, rotation_rows, translation_vals)
            where alignments are (query_pdb_resid, template_sequential_idx) pairs.
        """
        try:
            import dali as dali_rust
        except ImportError:
            logger.error("Rust dali module not available")
            return []

        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            store = dali_rust.ProteinStore(tmpdir)

            # Import query PDB
            # Note: import_pdb may append chain to code (e.g. "q" → "qA"),
            # so we use the returned code for all subsequent operations.
            try:
                q = dali_rust.import_pdb(str(Path(query_pdb).resolve()), "", "q")
                store.add_protein(q)
                query_code = q.code
            except Exception as e:
                logger.warning(f"Failed to import query PDB: {e}")
                return []

            # Resolve template .dat (check self.dat_dir if not explicitly provided)
            if template_dat_path is None and self.dat_dir is not None:
                candidate = self.dat_dir / f'{Path(template_pdb).stem}.dat'
                if candidate.exists():
                    template_dat_path = str(candidate.resolve())

            # Import template: prefer .dat if available.
            # When .dat exists, symlink into store dir — avoids parsing
            # + rewriting the .dat file on every call.  The ECOD70 library
            # is invariant across queries, so this is pure overhead.
            try:
                if template_dat_path:
                    template_code = Path(template_dat_path).stem
                    link_path = os.path.join(tmpdir, f'{template_code}.dat')
                    os.symlink(os.path.realpath(template_dat_path), link_path)
                else:
                    t = dali_rust.import_pdb(
                        str(Path(template_pdb).resolve()), "", "t"
                    )
                    store.add_protein(t)
                    template_code = t.code
            except Exception as e:
                logger.warning(f"Failed to import template: {e}")
                return []

            # Run iterative search.
            # skip_wolf=False: WOLF path is robust to DSSP divergence in
            # PDB-imported queries; PARSI alone fails for Rust-imported
            # queries due to secondary structure assignment differences.
            hits = dali_rust.iterative_search(
                query_code, [template_code], store,
                min_aligned=min_aligned,
                min_zscore=min_zscore,
                gap_tolerance=gap_tolerance,
                max_rounds=max_rounds,
                skip_wolf=False,
            )

            results = []
            for hit in hits:
                # Determine which query protein was used this round.
                # Round 0 uses the original, round N uses "{query_code}_r{N-1}".
                if hit.round == 0:
                    q_code = query_code
                else:
                    q_code = f"{query_code}_r{hit.round - 1}"

                try:
                    q_prot = store.get_protein(q_code)
                except Exception:
                    break

                qlen = q_prot.nres

                # Map query sequential indices to PDB residue IDs
                alignments_pdb = []
                for q_idx, t_idx in hit.alignments:
                    actual_qresid = q_prot.resid_map[q_idx - 1]
                    alignments_pdb.append((actual_qresid, t_idx))

                # Format rotation/translation as tab-separated strings
                rotation_rows = [
                    '\t'.join(f'{v:.6f}' for v in row) for row in hit.rotation
                ]
                translation_vals = [f'{v:.6f}' for v in hit.translation]

                results.append((
                    hit.zscore,
                    len(hit.alignments),
                    qlen,
                    alignments_pdb,
                    rotation_rows,
                    translation_vals,
                ))

            return results


    def batch_search(
        self,
        query_pdb: Path,
        template_codes: List[str],
        pdb_dir: Optional[Path] = None,
        min_aligned: int = 20,
        min_zscore: float = 2.0,
        gap_tolerance: int = 5,
        max_rounds: int = 10,
    ) -> List[Tuple[str, float, int, int, List[Tuple[int, int]], List[str], List[str]]]:
        """
        Iterative one-to-many domain detection (single FFI call).

        Searches query against ALL template_codes simultaneously,
        finding the globally best match per masking round.  Exploits
        ECOD70 library invariance: template .dat files are resolved
        once, query is imported once, WOLF grid and PARSI cache are
        built once.

        Template .dat resolution order for each code:
          1. self.dat_dir/{code}.dat  (pre-generated, symlinked)
          2. pdb_dir/{code}.pdb       (auto-generated via Rust import_pdb)
          3. skipped

        Args:
            query_pdb: Path to query PDB file
            template_codes: ECOD70 domain codes
            pdb_dir: Directory containing template PDB files ({code}.pdb).
                Used to auto-generate .dat for templates missing from dat_dir.
            min_aligned: Minimum aligned residues per hit
            min_zscore: Z-score threshold
            gap_tolerance: Gap bridging for masking
            max_rounds: Maximum masking rounds

        Returns:
            List of (template_code, z_score, n_aligned, qlen,
                     alignments, rotation_rows, translation_vals)
            where alignments are (query_pdb_resid, template_1based) pairs.
        """
        try:
            import dali as dali_rust
        except ImportError:
            logger.error("Rust dali module not available")
            return []

        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            store = dali_rust.ProteinStore(tmpdir)

            # Import query PDB
            try:
                q = dali_rust.import_pdb(str(Path(query_pdb).resolve()), "", "q")
                store.add_protein(q)
                query_code = q.code
            except Exception as e:
                logger.warning(f"batch_search: failed to import query: {e}")
                return []

            # Resolve template .dat files: symlink if pre-computed,
            # auto-generate from PDB otherwise.
            # The .dat format truncates codes to 5 chars, so we maintain
            # a reverse map from truncated internal code → original name.
            valid_codes = []
            code_map = {}  # internal_code → original_code
            n_symlinked = 0
            n_generated = 0
            for code in template_codes:
                # Try pre-computed .dat first
                if self.dat_dir is not None:
                    dat_path = self.dat_dir / f'{code}.dat'
                    if dat_path.exists():
                        link_path = os.path.join(tmpdir, f'{code}.dat')
                        try:
                            os.symlink(os.path.realpath(str(dat_path)), link_path)
                            valid_codes.append(code)
                            code_map[code] = code
                            n_symlinked += 1
                            continue
                        except OSError:
                            pass

                # Fall back to PDB import (code may be truncated to 5 chars)
                if pdb_dir is not None:
                    pdb_path = Path(pdb_dir) / f'{code}.pdb'
                    if pdb_path.exists():
                        try:
                            t = dali_rust.import_pdb(str(pdb_path.resolve()), "", code)
                            store.add_protein(t)
                            valid_codes.append(t.code)
                            code_map[t.code] = code  # t.code may be truncated
                            n_generated += 1
                            # Write back to dat_dir for future reuse
                            if self.dat_dir is not None:
                                cache_path = self.dat_dir / f'{code}.dat'
                                if not cache_path.exists():
                                    try:
                                        dali_rust.write_dat(t, str(cache_path))
                                    except Exception:
                                        pass
                            continue
                        except Exception as e:
                            logger.debug(f"batch_search: import failed for {code}: {e}")

                logger.debug(f"batch_search: no .dat or .pdb for {code}, skipping")

            logger.info(
                f"batch_search: {len(valid_codes)}/{len(template_codes)} templates "
                f"({n_symlinked} .dat, {n_generated} imported)"
            )

            if not valid_codes:
                return []

            # Single iterative search across all templates.
            # WOLF grid + PARSI cache built once for the query.
            hits = dali_rust.iterative_search(
                query_code, valid_codes, store,
                min_aligned=min_aligned,
                min_zscore=min_zscore,
                gap_tolerance=gap_tolerance,
                max_rounds=max_rounds,
                skip_wolf=False,
            )

            results = []
            for hit in hits:
                if hit.round == 0:
                    q_code = query_code
                else:
                    q_code = f"{query_code}_r{hit.round - 1}"

                try:
                    q_prot = store.get_protein(q_code)
                except Exception:
                    break

                qlen = q_prot.nres

                alignments_pdb = []
                for q_idx, t_idx in hit.alignments:
                    actual_qresid = q_prot.resid_map[q_idx - 1]
                    alignments_pdb.append((actual_qresid, t_idx))

                rotation_rows = [
                    '\t'.join(f'{v:.6f}' for v in row) for row in hit.rotation
                ]
                translation_vals = [f'{v:.6f}' for v in hit.translation]

                # Restore original code (undo .dat 5-char truncation)
                original_code = code_map.get(hit.cd2, hit.cd2)

                results.append((
                    original_code,
                    hit.zscore,
                    len(hit.alignments),
                    qlen,
                    alignments_pdb,
                    rotation_rows,
                    translation_vals,
                ))

            return results


def generate_dat_files(
    pdb_dir: Path,
    dat_dir: Path,
    chain: str = "",
    use_fortran: bool = False,
    dali_home: Optional[str] = None,
) -> int:
    """
    Pre-generate .dat files from PDB files.

    Converts all .pdb files in pdb_dir to .dat format, storing results
    in dat_dir. When use_fortran=True, runs Fortran DaliLite to generate
    .dat files (guaranteeing Fortran-compatible DSSP). Otherwise uses
    Rust import_pdb (faster but may have DSSP divergence).

    Args:
        pdb_dir: Directory containing .pdb files
        dat_dir: Output directory for .dat files
        chain: Chain ID to extract (empty string = first chain)
        use_fortran: If True, use Fortran DaliLite for .dat generation
        dali_home: Path to DaliLite installation (for Fortran mode)

    Returns:
        Number of .dat files generated
    """
    import subprocess

    dat_dir = Path(dat_dir)
    dat_dir.mkdir(parents=True, exist_ok=True)
    pdb_files = sorted(Path(pdb_dir).glob('*.pdb'))
    count = 0

    for pdb_file in pdb_files:
        code = pdb_file.stem
        dat_file = dat_dir / f'{code}.dat'
        if dat_file.exists():
            continue

        if use_fortran:
            # Use Fortran DaliLite import to generate .dat
            dali_bin = Path(dali_home or find_dali_executable()).parent
            import_bin = dali_bin / 'import.pl'
            if not import_bin.exists():
                logger.warning(f"Fortran import.pl not found at {import_bin}")
                continue
            try:
                tmp = dat_dir / f'.tmp_{code}'
                tmp.mkdir(exist_ok=True)
                subprocess.run(
                    [str(import_bin), '--pdbfile', str(pdb_file.resolve()),
                     '--dat', str(tmp)],
                    cwd=str(tmp), capture_output=True, timeout=30
                )
                # import.pl writes mol1A.dat or similar — find and rename
                generated = list(tmp.glob('*.dat'))
                if generated:
                    import shutil
                    shutil.copy(str(generated[0]), str(dat_file))
                    count += 1
                import shutil
                shutil.rmtree(tmp, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Fortran import failed for {code}: {e}")
        else:
            # Use Rust import
            try:
                import dali as dali_rust
                protein = dali_rust.import_pdb(str(pdb_file.resolve()), chain, code)
                protein.write_dat(str(dat_file))
                count += 1
            except Exception as e:
                logger.warning(f"Rust import failed for {code}: {e}")

    logger.info(f"Generated {count} .dat files in {dat_dir}")
    return count


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
        z_score, alignments, _, _ = dali.align(
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
