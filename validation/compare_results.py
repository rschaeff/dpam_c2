#!/usr/bin/env python3
"""
Compare DPAM v2.0 results against v1.0 SwissProt reference.

Compares domain counts, ranges, T-group assignments, and quality labels.
"""

import sys
from pathlib import Path
from collections import defaultdict
import difflib


def parse_range(range_str: str) -> set:
    """Parse range string into set of residues."""
    residues = set()
    if not range_str or range_str == 'na':
        return residues

    for segment in range_str.split(','):
        if '-' in segment:
            start, end = segment.split('-')
            residues.update(range(int(start), int(end) + 1))
        else:
            residues.add(int(segment))

    return residues


def load_v1_reference(ref_file: Path) -> dict:
    """Load v1.0 reference results."""
    proteins = defaultdict(list)

    with open(ref_file) as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 13:
                protein_id = parts[0]
                proteins[protein_id].append({
                    'domain': parts[1],
                    'range': parts[2],
                    'ecod_num': parts[3],
                    'ecod_key': parts[4],
                    'tgroup': parts[5],
                    'dpam_prob': parts[6],
                    'judge': parts[10],
                    'residues': parse_range(parts[2])
                })

    return proteins


def load_v2_results(working_dir: Path, protein_id: str) -> list:
    """Load v2.0 results for a protein."""
    prefix = f"AF-{protein_id}"
    protein_dir = working_dir / protein_id

    # Try final output file (step 24)
    final_file = protein_dir / f"{prefix}.final_domains"
    if not final_file.exists():
        # Try step 23
        final_file = protein_dir / f"{prefix}.step23_predictions"

    if not final_file.exists():
        # Try step 13 (domain parsing without ML)
        final_file = protein_dir / f"{prefix}.finalDPAM.domains"

    if not final_file.exists():
        return None

    domains = []
    with open(final_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split('\t')
            if len(parts) >= 2:  # At minimum need domain name and range
                domains.append({
                    'domain': parts[0],
                    'range': parts[1],
                    'tgroup': parts[2] if len(parts) > 2 else 'unknown',
                    'ecod': parts[3] if len(parts) > 3 else 'unknown',
                    'residues': parse_range(parts[1])
                })

    return domains if domains else None


def compare_domains(v1_domains: list, v2_domains: list, protein_id: str):
    """Compare v1 and v2 domain assignments."""
    print(f"\n{'='*70}")
    print(f"Protein: {protein_id}")
    print(f"{'='*70}")

    if not v2_domains:
        print("❌ No v2.0 results found")
        return {'status': 'missing', 'protein': protein_id}

    # Basic counts
    v1_count = len(v1_domains)
    v2_count = len(v2_domains)

    print(f"\nDomain count: v1.0={v1_count}, v2.0={v2_count}", end="")
    if v1_count == v2_count:
        print(" ✓")
    else:
        print(f" ✗ (diff: {v2_count - v1_count:+d})")

    # Compare T-group assignments
    v1_tgroups = set(d['tgroup'] for d in v1_domains)
    v2_tgroups = set(d['tgroup'] for d in v2_domains)

    print(f"\nT-groups:")
    print(f"  v1.0: {sorted(v1_tgroups)}")
    print(f"  v2.0: {sorted(v2_tgroups)}")

    tgroup_match = v1_tgroups == v2_tgroups
    if tgroup_match:
        print("  ✓ T-groups match")
    else:
        missing = v1_tgroups - v2_tgroups
        extra = v2_tgroups - v1_tgroups
        if missing:
            print(f"  Missing in v2.0: {sorted(missing)}")
        if extra:
            print(f"  Extra in v2.0: {sorted(extra)}")

    # Compare residue coverage
    v1_residues = set()
    for d in v1_domains:
        v1_residues.update(d['residues'])

    v2_residues = set()
    for d in v2_domains:
        v2_residues.update(d['residues'])

    overlap = v1_residues & v2_residues
    coverage_v1 = len(overlap) / len(v1_residues) if v1_residues else 0
    coverage_v2 = len(overlap) / len(v2_residues) if v2_residues else 0

    print(f"\nResidue coverage:")
    print(f"  v1.0 residues: {len(v1_residues)}")
    print(f"  v2.0 residues: {len(v2_residues)}")
    print(f"  Overlap: {len(overlap)} ({100*coverage_v1:.1f}% of v1.0, {100*coverage_v2:.1f}% of v2.0)")

    # Detailed domain comparison
    print(f"\nDetailed comparison:")
    print(f"  {'v1.0 Domain':<15} {'v1.0 Range':<25} {'v1.0 T-group':<12} {'Judge':<15}")
    print(f"  {'-'*67}")

    for d in v1_domains:
        print(f"  {d['domain']:<15} {d['range']:<25} {d['tgroup']:<12} {d['judge']:<15}")

    print(f"\n  {'v2.0 Domain':<15} {'v2.0 Range':<25} {'v2.0 T-group':<12}")
    print(f"  {'-'*52}")

    for d in v2_domains:
        print(f"  {d['domain']:<15} {d['range']:<25} {d['tgroup']:<12}")

    # Overall assessment
    score = 0
    if v1_count == v2_count:
        score += 33
    if tgroup_match:
        score += 33
    if coverage_v1 >= 0.9 and coverage_v2 >= 0.9:
        score += 34

    print(f"\nOverall match score: {score}/100")

    return {
        'status': 'compared',
        'protein': protein_id,
        'domain_count_match': v1_count == v2_count,
        'tgroup_match': tgroup_match,
        'coverage_v1': coverage_v1,
        'coverage_v2': coverage_v2,
        'score': score
    }


def main():
    # Paths
    ref_file = Path("/home/rschaeff/dev/dpam_c2/validation/v1_reference/swissprot_reference.tsv")
    working_dir = Path("/home/rschaeff/dev/dpam_c2/validation/working")
    protein_list = Path("/tmp/test_proteins.txt")

    if not ref_file.exists():
        print(f"Error: Reference file not found: {ref_file}")
        return 1

    if not working_dir.exists():
        print(f"Error: Working directory not found: {working_dir}")
        return 1

    # Load v1.0 reference
    v1_ref = load_v1_reference(ref_file)
    print(f"Loaded v1.0 reference for {len(v1_ref)} proteins")

    # Read protein list
    with open(protein_list) as f:
        protein_ids = [line.strip() for line in f if line.strip()]

    # Compare each protein
    results = []

    for protein_id in protein_ids:
        v1_domains = v1_ref.get(protein_id, [])
        v2_domains = load_v2_results(working_dir, protein_id)

        result = compare_domains(v1_domains, v2_domains, protein_id)
        results.append(result)

    # Summary
    print(f"\n{'='*70}")
    print("VALIDATION SUMMARY")
    print(f"{'='*70}")

    total = len(results)
    compared = sum(1 for r in results if r['status'] == 'compared')
    missing = sum(1 for r in results if r['status'] == 'missing')

    print(f"Total proteins: {total}")
    print(f"Compared: {compared}")
    print(f"Missing v2.0 results: {missing}")

    if compared > 0:
        domain_matches = sum(1 for r in results if r.get('domain_count_match', False))
        tgroup_matches = sum(1 for r in results if r.get('tgroup_match', False))
        avg_score = sum(r.get('score', 0) for r in results if r['status'] == 'compared') / compared

        print(f"\nDomain count matches: {domain_matches}/{compared} ({100*domain_matches/compared:.1f}%)")
        print(f"T-group matches: {tgroup_matches}/{compared} ({100*tgroup_matches/compared:.1f}%)")
        print(f"Average match score: {avg_score:.1f}/100")

    return 0


if __name__ == "__main__":
    sys.exit(main())
