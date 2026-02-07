"""
Step 4: Filter Foldseek Results.

Filters Foldseek hits based on residue coverage to reduce redundancy.
Keeps hits where at least 10 residues have coverage <= 100.
"""

from pathlib import Path
from typing import Dict, List, Set

from dpam.io.readers import read_fasta
from dpam.io.parsers import parse_foldseek_output
from dpam.core.models import FoldseekHit
from dpam.utils.logging_config import get_logger

logger = get_logger('steps.filter_foldseek')


def run_step4(
    prefix: str,
    working_dir: Path,
    path_resolver=None
) -> bool:
    """
    Run Step 4: Filter Foldseek results by coverage.

    Filters hits to reduce redundancy. Processes hits in order of
    increasing e-value, tracking residue coverage. Keeps hits where
    at least 10 residues have coverage <= 100.

    Args:
        prefix: Structure prefix
        working_dir: Working directory
        path_resolver: Optional PathResolver for sharded output directories

    Returns:
        True if successful
    """
    from dpam.core.path_resolver import PathResolver
    resolver = path_resolver or PathResolver(working_dir, sharded=False)

    logger.info(f"=== Step 4: Filter Foldseek Results for {prefix} ===")

    try:
        # Input from step 1
        fasta_file = resolver.step_dir(1) / f'{prefix}.fa'
        # Input from step 3
        foldseek_file = resolver.step_dir(3) / f'{prefix}.foldseek'

        if not fasta_file.exists():
            logger.error(f"FASTA file not found: {fasta_file}")
            return False

        if not foldseek_file.exists():
            logger.error(f"Foldseek file not found: {foldseek_file}")
            return False

        # Read query sequence to get length
        _, query_seq = read_fasta(fasta_file)
        qlen = len(query_seq)
        logger.debug(f"Query length: {qlen} residues")

        # Parse Foldseek hits
        hits = parse_foldseek_output(foldseek_file)
        logger.info(f"Parsed {len(hits)} Foldseek hits")

        # Sort hits by e-value (lower is better)
        hits.sort(key=lambda x: x.evalue)

        # Initialize residue coverage tracker
        qres2count: Dict[int, int] = {res: 0 for res in range(1, qlen + 1)}

        # Filter hits
        filtered_hits: List[FoldseekHit] = []

        for hit in hits:
            # Get residues covered by this hit
            qresids = hit.get_query_residues()

            # Update coverage counts for these residues
            for res in qresids:
                if res in qres2count:
                    qres2count[res] += 1

            # Count "good" residues (coverage <= 100)
            good_res = sum(
                1 for res in qresids
                if res in qres2count and qres2count[res] <= 100
            )

            # Keep hit if it has at least 10 good residues
            if good_res >= 10:
                filtered_hits.append(hit)

        logger.info(
            f"Filtered to {len(filtered_hits)} hits "
            f"({len(hits) - len(filtered_hits)} removed)"
        )

        # Write filtered results to step 4 directory
        output_file = resolver.step_dir(4) / f'{prefix}.foldseek.flt.result'
        with open(output_file, 'w') as f:
            f.write('ecodnum\tevalue\trange\n')
            for hit in filtered_hits:
                f.write(
                    f'{hit.ecod_num}\t{hit.evalue}\t'
                    f'{hit.query_start}-{hit.query_end}\n'
                )

        logger.info(f"Step 4 completed successfully for {prefix}")
        return True

    except Exception as e:
        logger.error(f"Step 4 failed for {prefix}: {e}")
        logger.exception("Exception details:")
        return False
