#!/usr/bin/env python3
"""Test the validation framework file mapping."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validate_against_v1 import convert_protein_id, STEP_FILES

def test_protein_id_conversion():
    """Test protein ID conversion."""
    print("Testing protein ID conversion:")
    print("-" * 60)

    test_cases = [
        ("AF-A0A024R1R8-F1", "A0A024R1R8"),
        ("AF-A0A024RBG1-F1", "A0A024RBG1"),
        ("AF-P12345-F1", "P12345"),
        ("A0A024R1R8", "A0A024R1R8"),  # Already bare
    ]

    for full_id, expected in test_cases:
        result = convert_protein_id(full_id)
        status = "✅" if result == expected else "❌"
        print(f"{status} {full_id:25s} → {result:15s} (expected: {expected})")

    print()


def test_file_mapping():
    """Test file mapping for each step."""
    print("Testing file mapping:")
    print("-" * 60)

    test_protein = "AF-A0A024RBG1-F1"
    v1_prefix = convert_protein_id(test_protein)
    v2_prefix = test_protein

    print(f"Test protein: {test_protein}")
    print(f"v1.0 prefix:  {v1_prefix}")
    print(f"v2.0 prefix:  {v2_prefix}")
    print()

    for step_name, patterns in STEP_FILES.items():
        v1_patterns = patterns['v1']
        v2_patterns = patterns['v2']

        print(f"\n{step_name}:")
        print(f"  v1.0 files ({len(v1_patterns)}):")
        for pattern in v1_patterns:
            filename = pattern.format(v1_prefix=v1_prefix)
            print(f"    - {filename}")

        print(f"  v2.0 files ({len(v2_patterns)}):")
        for pattern in v2_patterns:
            filename = pattern.format(v2_prefix=v2_prefix)
            print(f"    - {filename}")


def test_actual_files():
    """Test that we can find actual v1.0 files."""
    print("\n\nTesting actual file detection:")
    print("-" * 60)

    v1_dir = Path("v1_outputs/AF-A0A024RBG1-F1")
    if not v1_dir.exists():
        print(f"❌ v1.0 directory not found: {v1_dir}")
        return

    print(f"v1.0 directory: {v1_dir}")
    print()

    v1_prefix = "A0A024RBG1"

    for step_name, patterns in STEP_FILES.items():
        v1_patterns = patterns['v1']

        files_found = []
        files_missing = []

        for pattern in v1_patterns:
            filename = pattern.format(v1_prefix=v1_prefix)
            filepath = v1_dir / filename

            if filepath.exists():
                files_found.append(filename)
            else:
                files_missing.append(filename)

        if files_found:
            status = "✅" if not files_missing else "⚠️"
            print(f"{status} {step_name:20s} {len(files_found)}/{len(v1_patterns)} files")
            for f in files_found:
                print(f"     ✓ {f}")
            for f in files_missing:
                print(f"     ✗ {f}")


if __name__ == '__main__':
    test_protein_id_conversion()
    test_file_mapping()
    test_actual_files()
