#!/usr/bin/env python3
"""
Analyze DPAM v1.0 step scripts to extract file I/O patterns.

This script reads each v1.0 step script and identifies:
- Input files read
- Output files written
- File naming conventions

Usage:
    python analyze_v1_steps.py v1_scripts/ > v1_file_mapping.txt
"""

import re
import sys
from pathlib import Path
from collections import defaultdict


def extract_file_operations(script_path: Path) -> dict:
    """Extract file read/write operations from a Python script."""

    with open(script_path, 'r') as f:
        content = f.read()

    results = {
        'reads': set(),
        'writes': set(),
        'opens': set(),
        'globs': set(),
    }

    # Pattern 1: open('filename', 'r') or open(f'{prefix}.ext')
    open_patterns = [
        r"open\(['\"]([^'\"]+)['\"],\s*['\"]r['\"]",  # open('file', 'r')
        r"open\(f?['\"]([^'\"]+)['\"]",                # open('file') or open(f'...')
        r"with\s+open\(['\"]([^'\"]+)['\"]",           # with open('file')
    ]

    for pattern in open_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            results['opens'].add(match)

    # Pattern 2: Explicit file operations
    # Example: fw = open(args.protein + '.domains', 'w')
    write_patterns = [
        r"open\([^)]*\+\s*['\"]([^'\"]+)['\"],\s*['\"]w['\"]",  # open(var + '.ext', 'w')
        r"open\([^)]*['\"]\.([a-z_]+)['\"],\s*['\"]w['\"]",     # open(...'.ext', 'w')
    ]

    for pattern in write_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            results['writes'].add(match)

    # Pattern 3: glob patterns
    # Example: glob.glob(f'{protein}*.pdb')
    glob_patterns = [
        r"glob\.glob\(['\"]([^'\"]+)['\"]",
        r"glob\(['\"]([^'\"]+)['\"]",
    ]

    for pattern in glob_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            results['globs'].add(match)

    # Pattern 4: Common file extensions mentioned
    ext_pattern = r'[\'"]\.([a-z_]+)[\'"]'
    extensions = set(re.findall(ext_pattern, content))
    results['extensions'] = extensions

    # Pattern 5: Look for output file definitions
    # Example: output_file = f'{protein}.result'
    output_patterns = [
        r"=\s*[^+]*\+\s*['\"]\.([a-z_]+)['\"]",      # var = something + '.ext'
        r"=\s*f['\"][^'\"]*\.([a-z_]+)['\"]",        # var = f'...ext'
    ]

    for pattern in output_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            results['writes'].add('.' + match)

    return results


def analyze_step_script(script_path: Path) -> dict:
    """Analyze a single step script in detail."""

    step_name = script_path.stem
    file_ops = extract_file_operations(script_path)

    # Read the script to find comments/docstrings about purpose
    with open(script_path, 'r') as f:
        lines = f.readlines()

    # Get first few lines for description
    description = []
    for i, line in enumerate(lines[:20]):
        if line.strip().startswith('#') and i < 10:
            description.append(line.strip('# \n'))

    return {
        'name': step_name,
        'description': ' '.join(description) if description else '',
        'file_ops': file_ops,
        'size': script_path.stat().st_size,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_v1_steps.py <v1_scripts_dir>")
        sys.exit(1)

    scripts_dir = Path(sys.argv[1])

    # Find all step scripts (step1_*.py through step25_*.py)
    step_scripts = sorted(scripts_dir.glob('step*.py'))

    print("=" * 80)
    print("DPAM v1.0 Step Analysis")
    print("=" * 80)
    print()

    # Organize by step number
    steps = defaultdict(list)
    for script in step_scripts:
        # Extract step number
        match = re.match(r'step(\d+)([a-z]?)_', script.name)
        if match:
            step_num = int(match.group(1))
            variant = match.group(2)
            steps[step_num].append((script, variant))

    # Analyze each step
    for step_num in sorted(steps.keys()):
        print(f"\n{'='*80}")
        print(f"STEP {step_num}")
        print('='*80)

        for script_path, variant in steps[step_num]:
            variant_label = f" (variant '{variant}')" if variant else ""
            print(f"\n## {script_path.name}{variant_label}")
            print(f"   Size: {script_path.stat().st_size} bytes")

            analysis = analyze_step_script(script_path)

            if analysis['description']:
                print(f"   Description: {analysis['description'][:100]}")

            file_ops = analysis['file_ops']

            # Print file operations
            if file_ops['writes']:
                print(f"\n   Output files (writes):")
                for ext in sorted(file_ops['writes']):
                    print(f"      • {ext}")

            if file_ops['extensions']:
                print(f"\n   File extensions mentioned:")
                for ext in sorted(file_ops['extensions']):
                    print(f"      • .{ext}")

            if file_ops['opens']:
                print(f"\n   File open operations:")
                for pattern in sorted(file_ops['opens'])[:10]:  # Limit to 10
                    print(f"      • {pattern}")

            if file_ops['globs']:
                print(f"\n   Glob patterns:")
                for pattern in sorted(file_ops['globs']):
                    print(f"      • {pattern}")

    print("\n\n" + "="*80)
    print("File Extension Summary")
    print("="*80)

    # Collect all extensions across all steps
    all_extensions = defaultdict(list)
    for step_num in sorted(steps.keys()):
        for script_path, variant in steps[step_num]:
            analysis = analyze_step_script(script_path)
            for ext in analysis['file_ops']['extensions']:
                all_extensions[ext].append(f"Step {step_num}")

    for ext in sorted(all_extensions.keys()):
        steps_list = ', '.join(sorted(set(all_extensions[ext]))[:5])
        print(f"  .{ext:20s} → {steps_list}")


if __name__ == '__main__':
    main()
