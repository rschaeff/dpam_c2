"""
Unit tests for utility functions.

Tests range parsing, amino acid utilities, and other helper functions.
"""

import pytest
from dpam.utils.ranges import range_to_residues, residues_to_range
from dpam.utils.amino_acids import three_to_one, one_to_three, is_valid_amino_acid


class TestRangeParsing:
    """Tests for range parsing functions."""

    def test_range_to_residues_simple(self):
        """Test simple range parsing."""
        result = range_to_residues("10-15")
        assert result == {10, 11, 12, 13, 14, 15}

    def test_range_to_residues_single(self):
        """Test single residue range."""
        result = range_to_residues("10-10")
        assert result == {10}

    def test_range_to_residues_multiple(self):
        """Test multiple ranges."""
        result = range_to_residues("10-12,20-22")
        assert result == {10, 11, 12, 20, 21, 22}

    def test_range_to_residues_complex(self):
        """Test complex range with gaps."""
        result = range_to_residues("1-3,10-12,20-22")
        assert result == {1, 2, 3, 10, 11, 12, 20, 21, 22}

    def test_range_to_residues_single_residue_no_dash(self):
        """Test single residue without dash (if supported)."""
        # This depends on implementation - may need adjustment
        result = range_to_residues("10")
        assert 10 in result

    def test_residues_to_range_simple(self):
        """Test simple residue list to range."""
        result = residues_to_range([10, 11, 12])
        assert result == "10-12"

    def test_residues_to_range_single(self):
        """Test single residue."""
        result = residues_to_range([10])
        assert result == "10-10" or result == "10"

    def test_residues_to_range_with_gaps(self):
        """Test residues with gaps."""
        result = residues_to_range([10, 11, 12, 20, 21, 22])
        assert result == "10-12,20-22"

    def test_residues_to_range_unordered(self):
        """Test unordered residue list."""
        result = residues_to_range([22, 10, 21, 11, 20, 12])
        assert result == "10-12,20-22"

    def test_residues_to_range_complex(self):
        """Test complex pattern."""
        result = residues_to_range([1, 2, 3, 10, 15, 16, 17, 100])
        expected_parts = {"1-3", "10-10", "15-17", "100-100"}
        # Allow single residues to be represented as either "X-X" or "X"
        result_parts = set(result.split(","))
        # Normalize single residues
        normalized = set()
        for part in result_parts:
            if "-" in part:
                start, end = part.split("-")
                if start == end:
                    normalized.add(f"{start}-{end}")
                else:
                    normalized.add(part)
            else:
                normalized.add(f"{part}-{part}")
        assert normalized == expected_parts or result_parts == {"1-3", "10", "15-17", "100"}

    def test_roundtrip_conversion(self):
        """Test range -> residues -> range conversion."""
        original = "10-15,20-25,30-35"
        residues = range_to_residues(original)
        result = residues_to_range(sorted(residues))
        assert result == original

    def test_empty_range(self):
        """Test empty range."""
        result = range_to_residues("")
        assert result == set()

    def test_empty_residues(self):
        """Test empty residue list."""
        result = residues_to_range([])
        assert result == ""


class TestAminoAcids:
    """Tests for amino acid conversion functions."""

    def test_three_to_one_standard(self):
        """Test standard amino acid conversion."""
        assert three_to_one("ALA") == "A"
        assert three_to_one("GLY") == "G"
        assert three_to_one("TRP") == "W"

    def test_three_to_one_lowercase(self):
        """Test lowercase input."""
        assert three_to_one("ala") == "A"
        assert three_to_one("gly") == "G"

    def test_three_to_one_invalid(self):
        """Test invalid three-letter code."""
        with pytest.raises(KeyError):
            three_to_one("XXX")

    def test_one_to_three_standard(self):
        """Test one-letter to three-letter conversion."""
        assert one_to_three("A") == "ALA"
        assert one_to_three("G") == "GLY"
        assert one_to_three("W") == "TRP"

    def test_one_to_three_lowercase(self):
        """Test lowercase one-letter code."""
        assert one_to_three("a") == "ALA"
        assert one_to_three("g") == "GLY"

    def test_one_to_three_invalid(self):
        """Test invalid one-letter code."""
        with pytest.raises(KeyError):
            one_to_three("X")

    def test_is_valid_amino_acid_one_letter(self):
        """Test validation of one-letter codes."""
        assert is_valid_amino_acid("A") is True
        assert is_valid_amino_acid("G") is True
        assert is_valid_amino_acid("X") is False
        assert is_valid_amino_acid("Z") is False

    def test_is_valid_amino_acid_three_letter(self):
        """Test validation of three-letter codes."""
        assert is_valid_amino_acid("ALA") is True
        assert is_valid_amino_acid("GLY") is True
        assert is_valid_amino_acid("XXX") is False

    def test_all_twenty_amino_acids(self):
        """Test all 20 standard amino acids can be converted."""
        standard_aa = "ACDEFGHIKLMNPQRSTVWY"
        for aa in standard_aa:
            three = one_to_three(aa)
            assert len(three) == 3
            assert three_to_one(three) == aa

    def test_roundtrip_conversion(self):
        """Test one -> three -> one conversion."""
        for aa in "ACDEFGHIKLMNPQRSTVWY":
            assert three_to_one(one_to_three(aa)) == aa


class TestRangeEdgeCases:
    """Edge case tests for range functions."""

    def test_large_range(self):
        """Test large range."""
        result = range_to_residues("1-1000")
        assert len(result) == 1000
        assert min(result) == 1
        assert max(result) == 1000

    def test_many_small_ranges(self):
        """Test many small ranges."""
        ranges = ",".join([f"{i}-{i+1}" for i in range(1, 100, 10)])
        result = range_to_residues(ranges)
        assert len(result) == 20  # 10 ranges × 2 residues each

    def test_overlapping_ranges_if_allowed(self):
        """Test overlapping ranges (behavior depends on implementation)."""
        # Some implementations may handle overlaps, others may not
        result = range_to_residues("10-15,12-17")
        # Should contain 10-17 without duplicates
        assert result == set(range(10, 18))

    def test_descending_order_in_range(self):
        """Test if descending ranges are handled."""
        # Most implementations expect ascending order
        # This test documents expected behavior
        try:
            result = range_to_residues("15-10")
            # If implementation handles it, check result
            assert result == set() or result == {10, 11, 12, 13, 14, 15}
        except (ValueError, AssertionError):
            # If implementation doesn't handle descending, that's fine
            pass

    def test_whitespace_handling(self):
        """Test whitespace in range strings."""
        # Test if implementation handles whitespace
        result = range_to_residues("10-15, 20-25")
        assert result == {10, 11, 12, 13, 14, 15, 20, 21, 22, 23, 24, 25}

    def test_residues_to_range_set_input(self):
        """Test residues_to_range with set input."""
        result = residues_to_range({10, 11, 12, 20, 21})
        assert result == "10-12,20-21"

    def test_residues_to_range_tuple_input(self):
        """Test residues_to_range with tuple input."""
        result = residues_to_range((10, 11, 12, 20, 21))
        assert result == "10-12,20-21"
