"""
Step 11: Secondary Structure Elements (SSE)

Assigns secondary structure using DSSP:
1. Run mkdssp on PDB file
2. Parse DSSP output
3. Identify SSE segments (3+ strands or 6+ helices)
4. Write SSE assignments

Input:
    {prefix}.pdb - Structure file
    {prefix}.fa - Sequence file (for validation)

Output:
    {prefix}.sse - SSE assignments per residue

Author: DPAM v2.0
"""

from pathlib import Path

from dpam.tools.dssp import DSSP
from dpam.io.readers import read_fasta
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.step11')


def run_step11(
    prefix: str,
    working_dir: Path
) -> bool:
    """
    Run step 11: Assign secondary structure elements.

    Args:
        prefix: Structure prefix
        working_dir: Working directory

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Step 11: Assigning secondary structure for {prefix}")

    # Input files
    pdb_file = working_dir / f'{prefix}.pdb'
    fasta_file = working_dir / f'{prefix}.fa'

    if not pdb_file.exists():
        logger.error(f"PDB file not found: {pdb_file}")
        return False

    if not fasta_file.exists():
        logger.error(f"FASTA file not found: {fasta_file}")
        return False

    # Read sequence
    _, sequence = read_fasta(fasta_file)
    logger.info(f"Sequence length: {len(sequence)}")

    # Run DSSP and parse
    logger.info("Running DSSP")
    dssp = DSSP()

    try:
        sse_dict = dssp.run_and_parse(pdb_file, sequence, working_dir)
        logger.info(f"DSSP completed: {len(sse_dict)} residues assigned")
    except Exception as e:
        logger.error(f"DSSP failed: {e}")
        return False

    # Validate
    if len(sse_dict) != len(sequence):
        logger.error(
            f"Length mismatch: {len(sse_dict)} DSSP residues vs "
            f"{len(sequence)} sequence residues"
        )
        return False

    # Write SSE file
    output_file = working_dir / f'{prefix}.sse'
    logger.info(f"Writing SSE assignments to {output_file}")

    with open(output_file, 'w') as f:
        for resid in sorted(sse_dict.keys()):
            sse = sse_dict[resid]

            # Format: resid\taa\tsse_id\tsse_type
            # sse_id: SSE number or 'na' if not in SSE
            # sse_type: H (helix), E (strand), C (coil)
            sse_id_str = str(sse.sse_id) if sse.sse_id is not None else 'na'

            f.write(
                f"{sse.residue_id}\t"
                f"{sse.amino_acid}\t"
                f"{sse_id_str}\t"
                f"{sse.sse_type}\n"
            )

    # Count SSEs
    num_sses = len(set(
        sse.sse_id for sse in sse_dict.values()
        if sse.sse_id is not None
    ))

    logger.info(f"Step 11 complete: {num_sses} SSEs identified, {len(sse_dict)} residues")

    return True
