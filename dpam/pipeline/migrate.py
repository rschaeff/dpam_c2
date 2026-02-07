"""
Migrate flat DPAM working directories to sharded layout.

Moves per-protein intermediate files from a flat working directory into
per-step subdirectories as defined by PathResolver.STEP_DIRS.
"""

import shutil
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from dpam.core.path_resolver import PathResolver, STEP_DIRS
from dpam.utils.logging_config import get_logger

logger = get_logger('migrate')

# (suffix, step_number) ordered longest-suffix-first to avoid ambiguity.
# Each suffix is matched against "{prefix}{suffix}" filenames.
SUFFIX_TO_STEP: list = [
    # Step 4 — must match before shorter .foldseek
    ('.foldseek.flt.result', 4),
    # Step 3 — .foldseek.log before .foldseek
    ('.foldseek.log', 3),
    ('.foldseek', 3),
    # Step 5
    ('.map2ecod.result', 5),
    # Step 2 (HHsearch outputs)
    ('.a3m.ss', 2),
    ('.a3m', 2),
    ('.hmm', 2),
    ('.hhm', 2),
    ('.hhsearch', 2),
    ('.hhmake.log', 2),
    ('.hhblits.log', 2),
    ('.hhr', 2),
    # Step 6
    ('_hits4Dali', 6),
    # Step 7
    ('_iterativdDali_hits', 7),
    ('.iterativeDali.done', 7),
    # Step 8
    ('_good_hits', 8),
    # Step 9
    ('_sequence.result', 9),
    ('_structure.result', 9),
    # Step 10
    ('.goodDomains', 10),
    # Step 11
    ('.sse', 11),
    # Step 12
    ('.diso', 12),
    # Step 13
    ('.step13_domains', 13),
    # Step 15
    ('.step15_features', 15),
    # Step 16
    ('.step16_predictions', 16),
    # Step 17
    ('.step17_confident_predictions', 17),
    # Step 18
    ('.step18_mappings', 18),
    # Step 19
    ('.step19_merge_candidates', 19),
    ('.step19_merge_info', 19),
    # Step 21
    ('.step21_comparisons', 21),
    # Step 22
    ('.step22_merged_domains', 22),
    # Step 23
    ('.step23_predictions', 23),
]

# Files that stay in root (never moved)
ROOT_SUFFIXES = {'.cif', '.json'}


def discover_proteins(working_dir: Path) -> Set[str]:
    """Find protein prefixes from state files and .fa files in root.

    Scans for:
      - .{prefix}.dpam_state.json  (hidden state files)
      - {prefix}.fa                (FASTA files from step 1)
    """
    prefixes: Set[str] = set()
    for p in working_dir.iterdir():
        if not p.is_file():
            continue
        name = p.name
        # State files: .AF-P12345-F1.dpam_state.json
        if name.startswith('.') and name.endswith('.dpam_state.json'):
            prefix = name[1:].replace('.dpam_state.json', '')
            prefixes.add(prefix)
        # FASTA files: AF-P12345-F1.fa
        elif name.endswith('.fa'):
            prefixes.add(name[:-3])  # strip .fa
    return prefixes


def classify_file(
    filename: str,
    known_prefixes: Set[str],
) -> Optional[Tuple[int, str]]:
    """Classify a file by suffix to its originating step.

    Returns:
        (step_number, 'move') for regular files
        (1, 'move') for .fa files
        (1, 'copy') for .pdb files
        (-1, 'dual') for .finalDPAM.domains (copy to step13 + results)
        None if not a pipeline file or should stay in root
    """
    # .finalDPAM.domains — dual copy to step13 + results
    for prefix in known_prefixes:
        if filename == f'{prefix}.finalDPAM.domains':
            return (-1, 'dual')

    # .fa → move to step01_prepare
    for prefix in known_prefixes:
        if filename == f'{prefix}.fa':
            return (1, 'move')

    # .pdb → copy to step01_prepare (keep original in root)
    for prefix in known_prefixes:
        if filename == f'{prefix}.pdb':
            return (1, 'copy')

    # Root files — skip
    for suffix in ROOT_SUFFIXES:
        for prefix in known_prefixes:
            if filename == f'{prefix}{suffix}':
                return None

    # Hidden state files and batch state — skip
    if filename.endswith('.dpam_state.json') or filename == '_batch_state.json':
        return None

    # Suffix table match
    for suffix, step in SUFFIX_TO_STEP:
        for prefix in known_prefixes:
            if filename == f'{prefix}{suffix}':
                return (step, 'move')

    return None


def migrate_flat_to_sharded(
    working_dir: Path,
    dry_run: bool = False,
) -> Dict[str, int]:
    """Migrate a flat working directory to sharded layout.

    Args:
        working_dir: Path to the working directory
        dry_run: If True, print actions without modifying files

    Returns:
        Dict with counts: {moved, copied, skipped, errors, renamed}
    """
    working_dir = Path(working_dir)
    if not working_dir.is_dir():
        raise FileNotFoundError(f"Working directory not found: {working_dir}")

    # Abort if already sharded
    if PathResolver.detect_layout(working_dir):
        print(f"Directory already uses sharded layout (step01_prepare/ exists)")
        print(f"Nothing to do.")
        return {'moved': 0, 'copied': 0, 'skipped': 0, 'errors': 0, 'renamed': 0}

    # Discover proteins
    proteins = discover_proteins(working_dir)
    if not proteins:
        print(f"No proteins found in {working_dir}")
        print(f"Expected .dpam_state.json or .fa files.")
        return {'moved': 0, 'copied': 0, 'skipped': 0, 'errors': 0, 'renamed': 0}

    print(f"Found {len(proteins)} proteins: {', '.join(sorted(proteins))}")

    resolver = PathResolver(working_dir, sharded=True)
    counts = {'moved': 0, 'copied': 0, 'skipped': 0, 'errors': 0, 'renamed': 0}

    # Phase 1: Rename existing step directories (step20/ → step20_extract/, etc.)
    dir_renames = [
        ('step20', STEP_DIRS[20]),   # step20 → step20_extract
        ('step24', STEP_DIRS[24]),   # step24 → step24_integrate
    ]
    for old_name, new_name in dir_renames:
        old_dir = working_dir / old_name
        new_dir = working_dir / new_name
        if old_dir.is_dir() and not new_dir.exists():
            if dry_run:
                print(f"  RENAME {old_name}/ → {new_name}/")
            else:
                old_dir.rename(new_dir)
                logger.info(f"Renamed {old_name}/ → {new_name}/")
            counts['renamed'] += 1

    # Phase 2: Move batch-related directories
    batch_dirs = ['_foldseek_batch', '_dali_template_cache']
    for dirname in batch_dirs:
        src = working_dir / dirname
        if src.is_dir():
            if dry_run:
                dst = working_dir / '_batch' / dirname
                print(f"  MOVE {dirname}/ → _batch/{dirname}/")
            else:
                batch_dir = resolver.batch_dir()
                dst = batch_dir / dirname
                if not dst.exists():
                    shutil.move(str(src), str(dst))
                    logger.info(f"Moved {dirname}/ → _batch/{dirname}/")
            counts['moved'] += 1

    # Helper: get step directory name without creating it
    def _step_dir_name(step_num: int) -> str:
        return STEP_DIRS.get(step_num, '')

    # Phase 3: Classify and move/copy individual files
    files = sorted(f for f in working_dir.iterdir() if f.is_file() and not f.name.startswith('.'))
    for filepath in files:
        result = classify_file(filepath.name, proteins)

        if result is None:
            continue  # Not a pipeline file or stays in root

        step, action = result

        try:
            if action == 'move':
                if dry_run:
                    print(f"  MOVE {filepath.name} → {_step_dir_name(step)}/")
                else:
                    dest_dir = resolver.step_dir(step)
                    dest = dest_dir / filepath.name
                    if dest.exists():
                        counts['skipped'] += 1
                        continue
                    shutil.move(str(filepath), str(dest))
                counts['moved'] += 1

            elif action == 'copy':
                if dry_run:
                    print(f"  COPY {filepath.name} → {_step_dir_name(step)}/")
                else:
                    dest_dir = resolver.step_dir(step)
                    dest = dest_dir / filepath.name
                    if dest.exists():
                        counts['skipped'] += 1
                        continue
                    shutil.copy2(str(filepath), str(dest))
                counts['copied'] += 1

            elif action == 'dual':
                # .finalDPAM.domains → copy to step13 + results, remove original
                if dry_run:
                    print(f"  COPY {filepath.name} → {_step_dir_name(13)}/")
                    print(f"  COPY {filepath.name} → results/")
                    print(f"  REMOVE {filepath.name} (original)")
                    counts['moved'] += 1
                else:
                    dest_step13 = resolver.step_dir(13) / filepath.name
                    dest_results = resolver.results_dir() / filepath.name
                    for dest in [dest_step13, dest_results]:
                        if not dest.exists():
                            shutil.copy2(str(filepath), str(dest))
                    if dest_step13.exists() and dest_results.exists():
                        filepath.unlink()
                        counts['moved'] += 1
                    else:
                        counts['errors'] += 1

        except OSError as e:
            logger.error(f"Error processing {filepath.name}: {e}")
            counts['errors'] += 1

    # Summary
    print(f"\nMigration {'(dry run) ' if dry_run else ''}summary:")
    print(f"  Moved:   {counts['moved']}")
    print(f"  Copied:  {counts['copied']}")
    print(f"  Renamed: {counts['renamed']}")
    print(f"  Skipped: {counts['skipped']}")
    print(f"  Errors:  {counts['errors']}")

    if not dry_run and counts['errors'] == 0:
        # Verify sharded layout is now detectable
        if PathResolver.detect_layout(working_dir):
            print(f"\nMigration complete. Directory now uses sharded layout.")
        else:
            print(f"\nWarning: step01_prepare/ not created (no .fa files found).")
            print(f"Layout may not be detected as sharded until step 1 runs.")

    return counts
