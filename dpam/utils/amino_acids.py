"""
Amino acid mapping and utility functions.
"""

from typing import Dict

# Three-letter to one-letter amino acid code mapping
THREE_TO_ONE: Dict[str, str] = {
    "ALA": "A",
    "CYS": "C",
    "ASP": "D",
    "GLU": "E",
    "PHE": "F",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LYS": "K",
    "LEU": "L",
    "MET": "M",
    "MSE": "M",  # Selenomethionine -> Methionine
    "ASN": "N",
    "PRO": "P",
    "GLN": "Q",
    "ARG": "R",
    "SER": "S",
    "THR": "T",
    "VAL": "V",
    "TRP": "W",
    "TYR": "Y",
}

# One-letter to three-letter mapping
ONE_TO_THREE: Dict[str, str] = {v: k for k, v in THREE_TO_ONE.items() if k != "MSE"}


def three_to_one(three_letter: str) -> str:
    """
    Convert three-letter amino acid code to one-letter.
    
    Args:
        three_letter: Three-letter code (e.g., "ALA")
    
    Returns:
        One-letter code (e.g., "A"), or "X" if unknown
    """
    return THREE_TO_ONE.get(three_letter.upper(), "X")


def one_to_three(one_letter: str) -> str:
    """
    Convert one-letter amino acid code to three-letter.
    
    Args:
        one_letter: One-letter code (e.g., "A")
    
    Returns:
        Three-letter code (e.g., "ALA"), or "UNK" if unknown
    """
    return ONE_TO_THREE.get(one_letter.upper(), "UNK")
