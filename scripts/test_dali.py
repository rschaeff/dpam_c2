#!/usr/bin/env python3
"""
Quick DALI test script.

Tests DALI installation and step 7 implementation.
"""

import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dpam.tools.dali import DALI
from dpam.steps.step07_iterative_dali import run_dali, run_step7
from dpam.utils.logging_config import setup_logging


def test_dali_availability():
    """Test if DALI is available and working."""
    print("=" * 60)
    print("Test 1: DALI Availability")
    print("=" * 60)

    try:
        dali = DALI()
        print(f"✓ DALI executable found: {dali.executable}")

        if dali.check_availability():
            print("✓ DALI is available")
            return True
        else:
            print("✗ DALI not available (check PATH)")
            return False
    except Exception as e:
        print(f"✗ DALI check failed: {e}")
        return False


def test_dali_library_deps():
    """Test if DALI library dependencies are satisfied."""
    print("\n" + "=" * 60)
    print("Test 2: Library Dependencies")
    print("=" * 60)

    import subprocess

    dali = DALI()
    puu_binary = Path(dali.executable).parent / "puu"

    if not puu_binary.exists():
        print(f"✗ puu binary not found: {puu_binary}")
        return False

    print(f"Checking dependencies for: {puu_binary}")

    try:
        result = subprocess.run(
            ["ldd", str(puu_binary)],
            capture_output=True,
            text=True
        )

        print("\nLibraries:")
        for line in result.stdout.splitlines():
            if "not found" in line:
                print(f"  ✗ {line}")
            else:
                print(f"  ✓ {line}")

        if "not found" in result.stdout:
            print("\n✗ Missing libraries detected")
            print("\nTo fix:")
            print("  sudo apt-get install libgfortran3")
            print("  # OR")
            print("  sudo ln -s /usr/lib/x86_64-linux-gnu/libgfortran.so.5 \\")
            print("            /usr/lib/x86_64-linux-gnu/libgfortran.so.3")
            return False
        else:
            print("\n✓ All libraries found")
            return True

    except Exception as e:
        print(f"✗ Library check failed: {e}")
        return False


def test_dali_single_alignment():
    """Test DALI with single alignment."""
    print("\n" + "=" * 60)
    print("Test 3: Single DALI Alignment")
    print("=" * 60)

    # Test files
    test_dir = Path("test_run")
    query_pdb = test_dir / "AF-Q976I1-F1.pdb"
    template_pdb = Path("/home/rschaeff_1/data/dpam_reference/ecod_data/ECOD70/000001438.pdb")
    output_dir = test_dir / "test_dali_single"

    # Check files exist
    if not query_pdb.exists():
        print(f"✗ Query PDB not found: {query_pdb}")
        return False

    if not template_pdb.exists():
        print(f"✗ Template PDB not found: {template_pdb}")
        print("  (Adjust path to your ECOD70 directory)")
        return False

    print(f"Query: {query_pdb}")
    print(f"Template: {template_pdb}")
    print(f"Output: {output_dir}")

    try:
        dali = DALI()
        z_score, alignments = dali.align(
            query_pdb,
            template_pdb,
            output_dir
        )

        if z_score is not None:
            print(f"\n✓ DALI alignment successful")
            print(f"  Z-score: {z_score:.2f}")
            print(f"  Aligned residues: {len(alignments)}")

            if len(alignments) > 0:
                print(f"  First alignment: {alignments[0]}")
                print(f"  Last alignment: {alignments[-1]}")

            return True
        else:
            print(f"\n✗ DALI alignment failed (no output)")
            print(f"  Check log: {output_dir}/log")
            return False

    except Exception as e:
        print(f"\n✗ DALI alignment failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_step7_single_domain():
    """Test step 7 with single ECOD domain."""
    print("\n" + "=" * 60)
    print("Test 4: Step 7 Single Domain")
    print("=" * 60)

    test_dir = Path("test_run")
    data_dir = Path("/home/rschaeff_1/data/dpam_reference/ecod_data")

    args = (
        'AF-Q976I1-F1',
        '000001438',
        test_dir,
        data_dir
    )

    print(f"Running DALI for domain: 000001438")

    try:
        result = run_dali(args)

        if result:
            print(f"\n✓ Step 7 single domain successful")

            # Check output file
            output_file = test_dir / "iterativeDali_AF-Q976I1-F1/AF-Q976I1-F1_000001438_hits"
            if output_file.exists():
                size = output_file.stat().st_size
                print(f"  Output file: {output_file}")
                print(f"  Size: {size} bytes")

                if size > 0:
                    with open(output_file, 'r') as f:
                        lines = f.readlines()
                    print(f"  Lines: {len(lines)}")
                    print(f"  First line: {lines[0].strip()}")
                    return True
                else:
                    print(f"  ✗ Output file is empty")
                    return False
            else:
                print(f"  ✗ Output file not created")
                return False
        else:
            print(f"\n✗ Step 7 single domain failed")
            return False

    except Exception as e:
        print(f"\n✗ Step 7 single domain failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_step7_full():
    """Test full step 7 with multiple domains (slow)."""
    print("\n" + "=" * 60)
    print("Test 5: Step 7 Full Run (2 CPUs, ~30-60 min)")
    print("=" * 60)

    response = input("Run full step 7 test? This will take 30-60 minutes (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("Skipped")
        return None

    test_dir = Path("test_run")
    data_dir = Path("/home/rschaeff_1/data/dpam_reference/ecod_data")

    # Clean previous run
    import shutil
    iterative_dir = test_dir / "iterativeDali_AF-Q976I1-F1"
    if iterative_dir.exists():
        print(f"Removing old output: {iterative_dir}")
        shutil.rmtree(iterative_dir)

    done_file = test_dir / "AF-Q976I1-F1.iterativeDali.done"
    if done_file.exists():
        done_file.unlink()

    output_file = test_dir / "AF-Q976I1-F1_iterativdDali_hits"
    if output_file.exists():
        output_file.unlink()

    print(f"\nRunning step 7 for AF-Q976I1-F1...")
    print(f"Working dir: {test_dir}")
    print(f"Data dir: {data_dir}")

    try:
        success = run_step7(
            'AF-Q976I1-F1',
            test_dir,
            data_dir,
            cpus=2
        )

        if success:
            print(f"\n✓ Step 7 completed successfully")

            if output_file.exists():
                size = output_file.stat().st_size
                with open(output_file, 'r') as f:
                    lines = f.readlines()

                print(f"  Output file: {output_file}")
                print(f"  Size: {size:,} bytes")
                print(f"  Lines: {len(lines):,}")

                # Count hits
                hits = [l for l in lines if l.startswith('>')]
                print(f"  Hit count: {len(hits)}")

                if len(hits) > 0:
                    print(f"  First hit: {hits[0].strip()}")
                    return True
                else:
                    print(f"  ✗ No hits found")
                    return False
            else:
                print(f"  ✗ Output file not created")
                return False
        else:
            print(f"\n✗ Step 7 failed")
            return False

    except Exception as e:
        print(f"\n✗ Step 7 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    setup_logging(json_format=False)

    # Reduce verbosity for cleaner output
    logging.getLogger('tools.dali').setLevel(logging.WARNING)
    logging.getLogger('steps.iterative_dali').setLevel(logging.WARNING)

    print("\n" + "=" * 60)
    print("DALI Test Suite")
    print("=" * 60)

    results = {}

    # Test 1: Availability
    results['availability'] = test_dali_availability()

    # Test 2: Library dependencies
    results['libraries'] = test_dali_library_deps()

    # Only continue if basic tests pass
    if results['availability'] and results['libraries']:
        # Test 3: Single alignment
        results['single_alignment'] = test_dali_single_alignment()

        if results['single_alignment']:
            # Test 4: Single domain
            results['single_domain'] = test_step7_single_domain()

            # Test 5: Full run (optional)
            full_result = test_step7_full()
            if full_result is not None:
                results['full_run'] = full_result
    else:
        print("\n⚠️  Skipping further tests due to failures")

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:20s}: {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("\nDALI is working correctly. You can now:")
        print("  1. Run full pipeline: dpam run AF-Q976I1-F1 --working-dir test_run ...")
        print("  2. Generate v1.0 reference: ./scripts/generate_v1_reference.sh")
        print("  3. Create validation tests: pytest tests/validation/")
    else:
        print("✗ Some tests failed")
        print("\nNext steps:")
        if not results.get('libraries', True):
            print("  1. Fix library dependencies (see Test 2 output)")
        print("  2. Check logs for errors")
        print("  3. See docs/DALI_TROUBLESHOOTING.md for help")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
