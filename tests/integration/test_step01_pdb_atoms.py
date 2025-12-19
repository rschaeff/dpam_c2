"""
Integration tests for Step 1 PDB atom name preservation.

Ensures that write_pdb preserves proper atom names (N, CA, C, O, etc.)
so that DSSP and other tools can properly process the files.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from dpam.steps.step01_prepare import run_step1


class TestStep01AtomNames:
    """Test that Step 1 preserves proper atom names in PDB files"""

    @pytest.fixture
    def test_structure(self, tmp_path):
        """Setup test structure file"""
        # Copy a test CIF file to temp directory
        test_cif = Path(__file__).parent.parent / "data" / "test_structure.cif"
        if test_cif.exists():
            work_dir = tmp_path / "work"
            work_dir.mkdir()
            shutil.copy(test_cif, work_dir / "test_structure.cif")
            return work_dir, "test_structure"
        pytest.skip("Test structure not available")

    def test_pdb_has_proper_backbone_atoms(self, test_structure):
        """Test that PDB file contains proper backbone atom names (N, CA, C, O)"""
        work_dir, prefix = test_structure

        # Run Step 1
        success = run_step1(prefix, work_dir)
        assert success, "Step 1 should succeed"

        # Check PDB file
        pdb_file = work_dir / f"{prefix}.pdb"
        assert pdb_file.exists(), "PDB file should be created"

        # Parse PDB and check for proper atom names
        with open(pdb_file) as f:
            lines = f.readlines()

        atom_lines = [l for l in lines if l.startswith("ATOM")]
        assert len(atom_lines) > 0, "PDB should have ATOM records"

        # Extract atom names from columns 13-16
        atom_names = set()
        for line in atom_lines:
            atom_name = line[12:16].strip()
            atom_names.add(atom_name)

        # Check for backbone atoms
        backbone_atoms = {"N", "CA", "C", "O"}
        found_backbone = backbone_atoms.intersection(atom_names)
        assert len(found_backbone) >= 3, \
            f"PDB should have backbone atoms (N, CA, C, O), found: {atom_names}"

    def test_pdb_has_element_symbols(self, test_structure):
        """Test that PDB file has proper element symbols in columns 77-78"""
        work_dir, prefix = test_structure

        # Run Step 1
        success = run_step1(prefix, work_dir)
        assert success, "Step 1 should succeed"

        # Check PDB file
        pdb_file = work_dir / f"{prefix}.pdb"
        with open(pdb_file) as f:
            lines = f.readlines()

        atom_lines = [l for l in lines if l.startswith("ATOM")]

        # Check element symbols (should not all be "C")
        elements = set()
        for line in atom_lines:
            if len(line) >= 78:
                element = line[76:78].strip()
                elements.add(element)

        # Should have at least N, C, O
        essential_elements = {"N", "C", "O"}
        found_elements = essential_elements.intersection(elements)
        assert len(found_elements) >= 2, \
            f"PDB should have proper elements (N, C, O), found: {elements}"

    def test_pdb_atom_names_not_generic(self, test_structure):
        """Test that PDB doesn't use generic atom names like ATOM1, ATOM2"""
        work_dir, prefix = test_structure

        # Run Step 1
        success = run_step1(prefix, work_dir)
        assert success, "Step 1 should succeed"

        # Check PDB file
        pdb_file = work_dir / f"{prefix}.pdb"
        with open(pdb_file) as f:
            content = f.read()

        # Should NOT contain generic ATOM names
        assert "ATOM1" not in content, "PDB should not have generic 'ATOM1' names"
        assert "ATOM2" not in content, "PDB should not have generic 'ATOM2' names"
        assert "ATOM3" not in content, "PDB should not have generic 'ATOM3' names"

    def test_pdb_compatible_with_dssp(self, test_structure):
        """Test that generated PDB can be processed by DSSP"""
        pytest.importorskip("subprocess")
        work_dir, prefix = test_structure

        # Run Step 1
        success = run_step1(prefix, work_dir)
        assert success, "Step 1 should succeed"

        # Try to run DSSP on the PDB
        pdb_file = work_dir / f"{prefix}.pdb"
        dssp_out = work_dir / "test.dssp"

        import subprocess
        import shutil

        # Find DSSP binary
        dssp_cmd = None
        for cmd in ["dsspcmbi", "mkdssp"]:
            if shutil.which(cmd):
                dssp_cmd = cmd
                break

        # Also check DaliLite location
        if dssp_cmd is None:
            dali_dssp = Path.home() / "src/Dali_v5/DaliLite.v5/bin/dsspcmbi"
            if dali_dssp.exists():
                dssp_cmd = str(dali_dssp)

        if dssp_cmd is None:
            pytest.skip("DSSP not available for testing")

        # Run DSSP
        try:
            result = subprocess.run(
                [dssp_cmd, "-c", str(pdb_file), str(dssp_out)],
                capture_output=True,
                text=True,
                timeout=30
            )

            # DSSP should succeed (return code 0) or have acceptable warnings
            # Return code 1 with output is acceptable (just warnings)
            if result.returncode == 1 and dssp_out.exists():
                # Check if output was generated despite warnings
                assert dssp_out.stat().st_size > 0, \
                    "DSSP should generate output even with warnings"
            else:
                assert result.returncode == 0, \
                    f"DSSP should process PDB successfully. Error: {result.stderr}"

            # Verify DSSP output was created and has content
            assert dssp_out.exists(), "DSSP output file should be created"
            assert dssp_out.stat().st_size > 100, \
                "DSSP output should have substantial content"

        except subprocess.TimeoutExpired:
            pytest.fail("DSSP timed out - likely stuck due to malformed PDB")
        except Exception as e:
            pytest.fail(f"DSSP failed: {e}")


class TestAtomNameFormatting:
    """Test atom name formatting rules"""

    def test_atom_name_padding(self):
        """Test that atom names are properly padded according to PDB format"""
        from dpam.io.writers import write_pdb
        from dpam.core.models import Structure
        import numpy as np

        # Create a minimal structure
        structure = Structure(
            prefix="test",
            sequence="A",
            residue_coords={1: np.array([[0.0, 0.0, 0.0]])},
            residue_ids=[1],
            chain_id='A',
            atom_names={1: ["CA"]},
            atom_elements={1: ["C"]}
        )

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as f:
            temp_pdb = Path(f.name)

        try:
            write_pdb(temp_pdb, structure)

            # Read and check formatting
            with open(temp_pdb) as f:
                line = f.readline()

            # Atom name should be in columns 13-16
            atom_name_field = line[12:16]
            # For 2-char names like "CA", should be " CA "
            assert atom_name_field == " CA ", \
                f"Atom name 'CA' should be ' CA ' but got '{atom_name_field}'"

        finally:
            if temp_pdb.exists():
                temp_pdb.unlink()

    def test_backbone_atoms_present(self):
        """Test that all backbone atoms are written"""
        from dpam.io.writers import write_pdb
        from dpam.core.models import Structure
        import numpy as np

        # Create structure with backbone atoms
        structure = Structure(
            prefix="test",
            sequence="A",
            residue_coords={1: np.array([
                [0.0, 0.0, 0.0],  # N
                [1.0, 0.0, 0.0],  # CA
                [2.0, 0.0, 0.0],  # C
                [3.0, 0.0, 0.0]   # O
            ])},
            residue_ids=[1],
            chain_id='A',
            atom_names={1: ["N", "CA", "C", "O"]},
            atom_elements={1: ["N", "C", "C", "O"]}
        )

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as f:
            temp_pdb = Path(f.name)

        try:
            write_pdb(temp_pdb, structure)

            # Read and verify all atoms present
            with open(temp_pdb) as f:
                lines = f.readlines()

            assert len(lines) == 4, "Should have 4 ATOM lines"

            # Check each atom
            atoms_found = []
            for line in lines:
                atom_name = line[12:16].strip()
                atoms_found.append(atom_name)

            assert atoms_found == ["N", "CA", "C", "O"], \
                f"Should have backbone atoms in order, got: {atoms_found}"

        finally:
            if temp_pdb.exists():
                temp_pdb.unlink()
