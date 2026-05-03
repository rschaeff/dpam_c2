"""
Unit tests for parser functions.

Tests parsing of external tool outputs (HHsearch, Foldseek, DALI, DSSP).
"""

import pytest
from pathlib import Path
from unittest.mock import patch
from dpam.io.parsers import (
    parse_hhsearch_output,
    parse_foldseek_output,
    parse_dssp_output
)
from dpam.tools.dali import DALI, _DALI_ALIGN_RE


@pytest.mark.unit
class TestHHSearchParser:
    """Tests for HHsearch output parser."""

    def test_parse_basic_hit(self, tmp_path):
        """Test parsing a basic HHsearch hit."""
        hhsearch_file = tmp_path / "test.hhsearch"
        content = """Query test_structure

>2rsp_A
Probab=99.82  E-value=2.1e-25  Score=125.50  Aligned_cols=50  Identities=48%  Similarity=1.234  Sum_probs=45.6

Q test_structure    10 MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQL   59 (75)
Q Consensus        10 mqifvktltgktitlevepsdtienvkakiqdkegippdqqrlifagkql   59 (75)
T Consensus        15 mqifvktltgktitlevepsdtienvkakiqdkegippdqqrlifagkql   64 (124)
T 2rsp_A           15 MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQL   64 (124)
"""
        hhsearch_file.write_text(content)

        alignments = parse_hhsearch_output(hhsearch_file)

        assert len(alignments) == 1
        hit = alignments[0]
        assert hit.hit_id == "2rsp_A"
        assert hit.probability == 99.82
        assert hit.evalue == "2.1e-25"
        assert hit.score == "125.50"
        assert hit.aligned_cols == "50"
        assert hit.query_start == 10
        assert hit.query_end == 59
        assert hit.template_start == 15
        assert hit.template_end == 64

    def test_parse_multiple_hits(self, tmp_path):
        """Test parsing multiple HHsearch hits."""
        hhsearch_file = tmp_path / "test.hhsearch"
        content = """Query test_structure

>2rsp_A
Probab=99.82  E-value=2.1e-25  Score=125.50  Aligned_cols=50  Identities=48%  Similarity=1.234  Sum_probs=45.6

Q test_structure    10 MQIFVK   15 (75)
T 2rsp_A           15 MQIFVK   20 (124)

>2pma_A
Probab=98.54  E-value=8.5e-15  Score=95.30  Aligned_cols=45  Identities=42%  Similarity=1.123  Sum_probs=42.1

Q test_structure    15 KTLTGK   20 (75)
T 2pma_A           20 KTLTGK   25 (141)
"""
        hhsearch_file.write_text(content)

        alignments = parse_hhsearch_output(hhsearch_file)

        assert len(alignments) == 2
        assert alignments[0].hit_id == "2rsp_A"
        assert alignments[1].hit_id == "2pma_A"
        assert alignments[0].probability == 99.82
        assert alignments[1].probability == 98.54

    def test_parse_no_hits(self, tmp_path):
        """Test parsing HHsearch output with no hits."""
        hhsearch_file = tmp_path / "test.hhsearch"
        content = """Query test_structure
Match_columns 75
"""
        hhsearch_file.write_text(content)

        alignments = parse_hhsearch_output(hhsearch_file)

        assert len(alignments) == 0

    def test_parse_multiline_alignment(self, tmp_path):
        """Test parsing HHsearch hit with multiline alignment."""
        hhsearch_file = tmp_path / "test.hhsearch"
        content = """Query test_structure

>2rsp_A
Probab=99.82  E-value=2.1e-25  Score=125.50  Aligned_cols=100  Identities=48%  Similarity=1.234  Sum_probs=90.0

Q test_structure    10 MQIFVKTLTGKTITLEVEPSD   30 (75)
Q Consensus        10 mqifvktltgktitlevepsd   30 (75)
T Consensus        15 mqifvktltgktitlevepsd   35 (124)
T 2rsp_A           15 MQIFVKTLTGKTITLEVEPSD   35 (124)

Q test_structure    31 TIENVKAKIQDKEGIPPDQQR   51 (75)
Q Consensus        31 tienvkakiqdkegippdqqr   51 (75)
T Consensus        36 tienvkakiqdkegippdqqr   56 (124)
T 2rsp_A           36 TIENVKAKIQDKEGIPPDQQR   56 (124)
"""
        hhsearch_file.write_text(content)

        alignments = parse_hhsearch_output(hhsearch_file)

        assert len(alignments) == 1
        hit = alignments[0]
        assert hit.query_start == 10
        assert hit.query_end == 51
        assert hit.template_start == 15
        assert hit.template_end == 56


@pytest.mark.unit
class TestFoldseekParser:
    """Tests for Foldseek output parser."""

    def test_parse_basic_hit(self, tmp_path):
        """Test parsing a basic Foldseek hit."""
        foldseek_file = tmp_path / "test.foldseek"
        content = """test_structure\te6qdnA1.1\t0.950\t100\t1\t0\t10\t50\t15\t55\t1.2e-10\t100.5
"""
        foldseek_file.write_text(content)

        hits = parse_foldseek_output(foldseek_file)

        assert len(hits) == 1
        hit = hits[0]
        assert hit.ecod_num == "e6qdnA1"
        assert hit.evalue == 1.2e-10
        assert hit.query_start == 10
        assert hit.query_end == 50

    def test_parse_multiple_hits(self, tmp_path):
        """Test parsing multiple Foldseek hits."""
        foldseek_file = tmp_path / "test.foldseek"
        content = """test_structure\te6qdnA1.1\t0.950\t100\t1\t0\t10\t50\t15\t55\t1.2e-10\t100.5
test_structure\te5jb7A1.1\t0.920\t95\t2\t1\t15\t60\t20\t65\t2.5e-09\t95.3
test_structure\te4hkrA1.1\t0.880\t90\t3\t0\t25\t70\t30\t75\t5.1e-08\t88.7
"""
        foldseek_file.write_text(content)

        hits = parse_foldseek_output(foldseek_file)

        assert len(hits) == 3
        assert hits[0].ecod_num == "e6qdnA1"
        assert hits[1].ecod_num == "e5jb7A1"
        assert hits[2].ecod_num == "e4hkrA1"
        assert hits[0].evalue == 1.2e-10
        assert hits[1].evalue == 2.5e-09

    def test_parse_removes_version_suffix(self, tmp_path):
        """Test that domain version suffixes are removed."""
        foldseek_file = tmp_path / "test.foldseek"
        content = """test_structure\te6qdnA1.2\t0.950\t100\t1\t0\t10\t50\t15\t55\t1.2e-10\t100.5
"""
        foldseek_file.write_text(content)

        hits = parse_foldseek_output(foldseek_file)

        assert hits[0].ecod_num == "e6qdnA1"

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty Foldseek output."""
        foldseek_file = tmp_path / "test.foldseek"
        foldseek_file.write_text("")

        hits = parse_foldseek_output(foldseek_file)

        assert len(hits) == 0

    def test_parse_malformed_line(self, tmp_path):
        """Test parsing with malformed lines (too few fields)."""
        foldseek_file = tmp_path / "test.foldseek"
        content = """test_structure\te6qdnA1.1\t0.950
test_structure\te5jb7A1.1\t0.920\t95\t2\t1\t15\t60\t20\t65\t2.5e-09\t95.3
"""
        foldseek_file.write_text(content)

        hits = parse_foldseek_output(foldseek_file)

        # Should skip malformed line and parse good one
        assert len(hits) == 1
        assert hits[0].ecod_num == "e5jb7A1"


# DALI parser tests commented out - parser has different signature
# @pytest.mark.unit
# class TestDALIParser:
#     """Tests for DALI output parser."""
#     pass


# DSSP parser tests commented out - complex format needs actual implementation
# @pytest.mark.unit
# class TestDSSPParser:
#     """Tests for DSSP output parser."""
#     pass


@pytest.mark.unit
class TestParserEdgeCases:
    """Test edge cases for all parsers."""

    def test_parse_with_special_characters_in_id(self, tmp_path):
        """Test parsing with special characters in IDs."""
        foldseek_file = tmp_path / "test.foldseek"
        content = """test_structure\te6qdn-A1.1\t0.950\t100\t1\t0\t10\t50\t15\t55\t1.2e-10\t100.5
"""
        foldseek_file.write_text(content)

        hits = parse_foldseek_output(foldseek_file)

        assert len(hits) == 1
        assert hits[0].ecod_num == "e6qdn-A1"

    def test_parse_with_very_small_evalue(self, tmp_path):
        """Test parsing with very small e-values."""
        foldseek_file = tmp_path / "test.foldseek"
        content = """test_structure\te6qdnA1.1\t0.950\t100\t1\t0\t10\t50\t15\t55\t1e-100\t100.5
"""
        foldseek_file.write_text(content)

        hits = parse_foldseek_output(foldseek_file)

        assert hits[0].evalue == 1e-100

    def test_parse_with_large_coordinates(self, tmp_path):
        """Test parsing with large residue coordinates."""
        foldseek_file = tmp_path / "test.foldseek"
        content = """test_structure\te6qdnA1.1\t0.950\t100\t1\t0\t1000\t2000\t1500\t2500\t1.2e-10\t100.5
"""
        foldseek_file.write_text(content)

        hits = parse_foldseek_output(foldseek_file)

        assert hits[0].query_start == 1000
        assert hits[0].query_end == 2000


@pytest.mark.unit
class TestDALIAlignmentRegex:
    """
    Direct regex tests for DALI alignment lines.

    Regression coverage for the 4-digit residue parsing bug: DaliLite's
    fixed-width formatting eats spaces around the dash when residue indices
    grow past 999 (e.g. ``1014 -1044`` instead of ``1014 - 1044``).
    """

    @pytest.mark.parametrize("line,expected", [
        # 3-digit: 5 tokens between mol2-A and <=>
        (
            "   1: mol1-A mol2-A     2 -  25 <=>    1 -  24   "
            "(ALA   2  - LEU  25  <=> ALA   1  - LEU  24 )",
            (2, 25, 1, 24),
        ),
        # 4-digit query, 2-digit template — INSR D10 vs PKinase template
        (
            "   1: mol1-A mol2-A  1014 -1044 <=>    2 -  32   "
            "(ASP 1014  - ASP 1044  <=> ASP   12  - GLY   42 )",
            (1014, 1044, 2, 32),
        ),
        # Mixed: 4-digit query, 3-digit template
        (
            "   1: mol1-A mol2-A  1198 -1294 <=>  165 - 261",
            (1198, 1294, 165, 261),
        ),
        # 5-digit: dash with no spaces at all on either side
        (
            "   1: mol1-A mol2-A 12345-67890 <=> 12345-67890",
            (12345, 67890, 12345, 67890),
        ),
        # 4-digit on both sides
        (
            "   2: mol1-A mol2-A  1014 -1044 <=>  2014 -2044",
            (1014, 1044, 2014, 2044),
        ),
    ])
    def test_residue_widths(self, line, expected):
        m = _DALI_ALIGN_RE.search(line)
        assert m is not None, f"regex failed to match: {line!r}"
        assert tuple(int(g) for g in m.groups()) == expected

    def test_header_line_does_not_match(self):
        """Z-score summary line must not be parsed as an alignment segment."""
        header = "   1:  mol2-A 29.4  2.4  248   274   41"
        assert _DALI_ALIGN_RE.search(header) is None

    def test_matrix_line_does_not_match(self):
        """Translation/rotation matrix line must not be parsed as alignment."""
        matrix = ('-matrix  "mol1-A mol2-A  U(1,.)   '
                  '0.838773 -0.413254  0.354514          -22.411917"')
        assert _DALI_ALIGN_RE.search(matrix) is None


@pytest.mark.unit
class TestDALIParseOutput:
    """
    End-to-end tests for DALI._parse_dali_output against synthetic mol*.txt
    files. Covers the file-level contract: which fields are returned, when
    None is returned, and that the matrix block is parsed independently of
    the alignment block.
    """

    def _dali_obj(self):
        # Bypass executable-availability check; we only exercise the parser.
        with patch.object(DALI, '__init__', lambda self: None):
            d = DALI()
        return d

    def _write(self, output_dir: Path, content: str):
        (output_dir / "mol1A.txt").write_text(content)

    def test_parses_3digit_alignment(self, tmp_path):
        content = (
            "# Job: test\n"
            "# Query: mol1A\n"
            "# No:  Chain   Z    rmsd lali nres  %id\n"
            "   1:  mol2-A  6.2  4.7  24    50   13\n"
            "\n"
            "# Structural equivalences\n"
            "   1: mol1-A mol2-A     2 -  25 <=>    1 -  24\n"
            "\n"
            "# Translation-rotation matrices\n"
            '-matrix  "mol1-A mol2-A  U(1,.)   1.0 0.0 0.0          0.0"\n'
            '-matrix  "mol1-A mol2-A  U(2,.)   0.0 1.0 0.0          0.0"\n'
            '-matrix  "mol1-A mol2-A  U(3,.)   0.0 0.0 1.0          0.0"\n'
        )
        self._write(tmp_path, content)
        z, alignments, rot, trans = self._dali_obj()._parse_dali_output(tmp_path)
        assert z == 6.2
        assert len(alignments) == 24
        assert alignments[0] == (2, 1)
        assert alignments[-1] == (25, 24)
        assert len(rot) == 3
        assert len(trans) == 3

    def test_parses_4digit_alignment_regression(self, tmp_path):
        """
        INSR D10 (kinase) regression: query residues 1014-1294 against an
        ECOD PKinase template. With the old token-position parser, every
        alignment segment silently raised ValueError and ``alignments`` came
        back empty — step 7 then dropped the hit and the kinase domain was
        lost from the final output.
        """
        content = (
            "# Job: test\n"
            "# Query: mol1A\n"
            "# No:  Chain   Z    rmsd lali nres  %id\n"
            "   1:  mol2-A 29.4  2.4  248   274   41\n"
            "\n"
            "# Structural equivalences\n"
            "   1: mol1-A mol2-A  1014 -1044 <=>    2 -  32\n"
            "   1: mol1-A mol2-A  1051 -1063 <=>   33 -  45\n"
            "   1: mol1-A mol2-A  1198 -1294 <=>  165 - 261\n"
            "\n"
            "# Translation-rotation matrices\n"
            '-matrix  "mol1-A mol2-A  U(1,.)   0.838773 -0.413254  0.354514          -22.411917"\n'
            '-matrix  "mol1-A mol2-A  U(2,.)  -0.428382 -0.098983  0.898160            9.990059"\n'
            '-matrix  "mol1-A mol2-A  U(3,.)  -0.336077 -0.905220 -0.260055          -17.584805"\n'
        )
        self._write(tmp_path, content)
        z, alignments, rot, trans = self._dali_obj()._parse_dali_output(tmp_path)

        assert z == 29.4
        # 31 + 13 + 97 = 141 residues across the three segments
        assert len(alignments) == 31 + 13 + 97
        # Segment boundaries
        assert (1014, 2) in alignments
        assert (1044, 32) in alignments
        assert (1294, 261) in alignments
        # n_aligned must clear step-7's ≥20-residue gate
        assert len(alignments) >= 20

        assert rot == [
            "0.838773\t-0.413254\t0.354514",
            "-0.428382\t-0.098983\t0.898160",
            "-0.336077\t-0.905220\t-0.260055",
        ]
        assert trans == ["-22.411917", "9.990059", "-17.584805"]

    def test_only_first_hit_parsed(self, tmp_path):
        """v1.0 behavior: stop parsing at the second hit summary line."""
        content = (
            "   1:  mol2-A  6.2  4.7  24    50   13\n"
            "   1: mol1-A mol2-A     2 -  25 <=>    1 -  24\n"
            "   2:  mol3-A  5.0  5.5  20    50   10\n"
            "   2: mol1-A mol3-A    50 -  70 <=>   10 -  30\n"
        )
        self._write(tmp_path, content)
        z, alignments, _, _ = self._dali_obj()._parse_dali_output(tmp_path)
        assert z == 6.2
        # Alignments from hit #2 must not appear
        for q, t in alignments:
            assert q <= 25

    def test_no_mol_files_returns_none(self, tmp_path):
        z, alignments, rot, trans = self._dali_obj()._parse_dali_output(tmp_path)
        assert z is None
        assert alignments == []
        assert rot == []
        assert trans == []

    def test_no_hits_in_mol_file(self, tmp_path):
        """File present but contains no parseable hit (DALI ran but found nothing)."""
        self._write(tmp_path, "# Job: test\n# Query: mol1A\n")
        z, alignments, rot, trans = self._dali_obj()._parse_dali_output(tmp_path)
        assert z is None
        assert alignments == []
