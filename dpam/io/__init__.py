"""
Input/Output module for DPAM.

Handles reading and writing of structure files, FASTA files,
tool outputs, and reference data.
"""

from dpam.io.readers import (
    read_fasta,
    read_structure_from_cif,
    read_structure_from_pdb,
    extract_sequence_from_cif,
    read_pae_matrix,
)

from dpam.io.writers import (
    write_fasta,
    write_pdb,
    write_sequence_results,
    write_structure_results,
    write_good_domains,
    write_sse_annotation,
    write_disorder_regions,
    write_final_domains,
)

from dpam.io.parsers import (
    parse_hhsearch_output,
    parse_foldseek_output,
    parse_dali_hits_file,
    parse_dssp_output,
    parse_good_domains_file,
)

from dpam.io.reference_data import (
    load_ecod_data,
    load_ecod_lengths,
    load_ecod_norms,
    load_ecod_pdbmap,
    load_ecod_domains_file,
    load_ecod_weights,
    load_ecod_domain_info,
)

__all__ = [
    # Readers
    "read_fasta",
    "read_structure_from_cif",
    "read_structure_from_pdb",
    "extract_sequence_from_cif",
    "read_pae_matrix",
    # Writers
    "write_fasta",
    "write_pdb",
    "write_sequence_results",
    "write_structure_results",
    "write_good_domains",
    "write_sse_annotation",
    "write_disorder_regions",
    "write_final_domains",
    # Parsers
    "parse_hhsearch_output",
    "parse_foldseek_output",
    "parse_dali_hits_file",
    "parse_dssp_output",
    "parse_good_domains_file",
    # Reference data
    "load_ecod_data",
    "load_ecod_lengths",
    "load_ecod_norms",
    "load_ecod_pdbmap",
    "load_ecod_domains_file",
    "load_ecod_weights",
    "load_ecod_domain_info",
]
