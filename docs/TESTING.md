# DPAM Testing Guide

## Overview

DPAM v2.0 includes a comprehensive test suite covering:
- **Dependency validation** - External tools and reference data
- **Unit tests** - Pure Python functions (fast, isolated)
- **Integration tests** - Full step execution with real tools
- **End-to-end tests** - Complete pipeline validation

## Quick Start

### Install Test Dependencies

```bash
# Install package with development dependencies
pip install -e ".[dev]"
```

This installs:
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting
- `black` - Code formatter
- `mypy` - Type checker
- `flake8` - Linter

### Download Test Fixtures

```bash
cd tests/fixtures
./download_test_data.sh
cd ../..
```

Downloads minimal test structure (~100 residues) from AlphaFold DB.

### Run Tests

```bash
# Quick check (unit tests only, <10 seconds)
pytest -m unit

# Dependency check (verify tools available)
pytest tests/test_dependencies.py

# All tests
pytest

# With coverage
pytest --cov=dpam --cov-report=html
```

## Test Organization

### Directory Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── test_dependencies.py           # Tool availability
├── unit/                          # Fast unit tests
│   ├── test_utils.py             # Range parsing, amino acids
│   └── test_probability_funcs.py # Step 13 probabilities
├── integration/                   # Step integration tests
│   ├── test_step01_prepare.py
│   ├── test_step13_parse_domains.py
│   └── [steps 2-12 to be added]
└── fixtures/                      # Test data
    ├── download_test_data.sh
    └── test_structure.*
```

### Test Categories

#### 1. Dependency Tests

**File:** `tests/test_dependencies.py`

**Purpose:** Verify environment is set up correctly

**Checks:**
- External tools (hhsearch, foldseek, dali.pl, mkdssp)
- Python dependencies (numpy, gemmi)
- DPAM modules import correctly
- Reference data available (optional)

**Run:**
```bash
pytest tests/test_dependencies.py -v
```

**Expected output:**
```
test_hhsearch_available PASSED
test_foldseek_available PASSED
test_dali_available PASSED
test_dssp_available PASSED
test_numpy_available PASSED
test_gemmi_available PASSED
...
```

**If tools missing:**
- Tests will FAIL with clear error messages
- Install missing tools or skip integration tests

---

#### 2. Unit Tests

**Directory:** `tests/unit/`

**Marker:** `@pytest.mark.unit`

**Purpose:** Test pure functions without external dependencies

**Coverage:**
- Range parsing (`range_to_residues`, `residues_to_range`)
- Amino acid conversions (`three_to_one`, `one_to_three`)
- Probability functions (exact threshold testing)

**Run:**
```bash
pytest -m unit -v
```

**Characteristics:**
- ✅ Fast (<10 seconds)
- ✅ No external tools required
- ✅ No test fixtures required
- ✅ High code coverage (>90%)

**Example tests:**
- `test_range_to_residues_simple`: "10-15" → {10, 11, 12, 13, 14, 15}
- `test_residues_to_range_with_gaps`: [10, 11, 15, 16] → "10-11,15-16"
- `test_get_PDB_prob`: Distance thresholds exact match with v1.0

---

#### 3. Integration Tests

**Directory:** `tests/integration/`

**Markers:** `@pytest.mark.integration`

**Purpose:** Test full step execution with real tools

**Coverage:**
- Step 1 (Prepare): Input validation and preparation
- Step 13 (Parse Domains): Complete domain parsing
- [Steps 2-12: To be added]

**Run:**
```bash
# All integration tests
pytest -m integration

# Specific step
pytest tests/integration/test_step01_prepare.py -v
```

**Requirements:**
- External tools installed
- Test fixtures downloaded
- Temporary working directory (auto-created)

**Characteristics:**
- ⏱️  Slower (~5-10 minutes total)
- 🔧 Requires external tools
- 📁 Requires test fixtures
- ✅ Tests real execution

---

## Test Markers

Pytest markers enable selective test execution:

```python
@pytest.mark.unit                  # Fast unit test
@pytest.mark.integration           # Integration test
@pytest.mark.slow                  # Slow test (>1 minute)
@pytest.mark.requires_hhsearch     # Requires HHsearch
@pytest.mark.requires_foldseek     # Requires Foldseek
@pytest.mark.requires_dali         # Requires DALI
@pytest.mark.requires_dssp         # Requires DSSP
@pytest.mark.requires_ecod         # Requires ECOD data
```

### Usage

```bash
# Only unit tests
pytest -m unit

# Only tests requiring hhsearch
pytest -m requires_hhsearch

# Exclude slow tests
pytest -m "not slow"

# Integration but not slow
pytest -m "integration and not slow"
```

## Fixtures

### Shared Fixtures (conftest.py)

**`test_data_dir`**: Path to test fixtures directory

**`test_prefix`**: Test structure prefix ("test_structure")

**`working_dir`**: Temporary directory (auto-cleaned)

**`reference_data`**: Loaded ECOD data (auto-skip if unavailable)

**`setup_test_files`**: Copies test files to working directory

**Tool availability fixtures:**
- `hhsearch_available`: Skip if hhsearch not found
- `foldseek_available`: Skip if foldseek not found
- `dali_available`: Skip if dali not found
- `dssp_available`: Skip if dssp not found

### Usage in Tests

```python
def test_my_function(working_dir, test_prefix):
    # working_dir is temporary, auto-cleaned
    # test_prefix is "test_structure"
    output_file = working_dir / f"{test_prefix}.output"
    ...
```

## Coverage

### Generate Report

```bash
# Terminal output
pytest --cov=dpam

# HTML report
pytest --cov=dpam --cov-report=html
open htmlcov/index.html
```

### Coverage Goals

| Module | Target | Current |
|--------|--------|---------|
| utils/ | >90% | ~90% |
| core/ | >85% | ~80% |
| io/ | >80% | ~70% |
| steps/ | >75% | ~60% |
| **Overall** | **>80%** | **~75%** |

### Improving Coverage

```bash
# Show missing lines
pytest --cov=dpam --cov-report=term-missing

# Focus on specific module
pytest --cov=dpam.utils tests/unit/test_utils.py --cov-report=term-missing
```

## Writing New Tests

### Unit Test Template

```python
# tests/unit/test_mymodule.py
import pytest
from dpam.mymodule import my_function

@pytest.mark.unit
class TestMyFunction:
    """Tests for my_function."""

    def test_basic_case(self):
        """Test basic functionality."""
        result = my_function("input")
        assert result == "expected"

    def test_edge_case(self):
        """Test edge case."""
        result = my_function("")
        assert result == ""

    def test_invalid_input(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            my_function(None)
```

### Integration Test Template

```python
# tests/integration/test_step99_mystep.py
import pytest
from dpam.steps.step99_mystep import run_step99

@pytest.mark.integration
@pytest.mark.requires_mytool
class TestStep99:
    """Integration tests for step 99."""

    def test_basic_execution(self, test_prefix, working_dir, mytool_available):
        """Test basic step execution."""
        success = run_step99(test_prefix, working_dir)
        assert success, "Step should succeed"

        # Verify outputs
        output_file = working_dir / f"{test_prefix}.output"
        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_output_format(self, test_prefix, working_dir, mytool_available):
        """Test output file format."""
        run_step99(test_prefix, working_dir)

        output_file = working_dir / f"{test_prefix}.output"
        with open(output_file) as f:
            lines = f.readlines()

        # Validate format
        for line in lines:
            parts = line.strip().split('\t')
            assert len(parts) == 3  # Expected columns
```

## Debugging Tests

### Run Single Test

```bash
# By file
pytest tests/unit/test_utils.py

# By class
pytest tests/unit/test_utils.py::TestRangeParsing

# By function
pytest tests/unit/test_utils.py::TestRangeParsing::test_range_to_residues_simple
```

### Verbose Output

```bash
# Show test names
pytest -v

# Show print statements
pytest -s

# Full traceback
pytest --tb=long
```

### Drop into Debugger

```bash
# On failure
pytest --pdb

# On error
pytest --pdb --pdbcls=IPython.terminal.debugger:Pdb
```

### Filter by Name

```bash
# Tests with "range" in name
pytest -k range

# Tests with "probability" in name
pytest -k probability

# Exclude specific tests
pytest -k "not slow"
```

## Continuous Integration

### Local Pre-commit

```bash
# Before committing
pytest -m unit                    # Quick check
pytest -m "not slow"              # Full check (skip long tests)
```

### GitHub Actions (Planned)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -e ".[dev]"
      - run: pytest -m unit
      - run: pytest --cov=dpam --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Troubleshooting

### Tests Skipped

**Issue:** "X tests skipped"

**Common reasons:**
- Tool not available → Install tool or skip integration tests
- Fixtures not found → Run `tests/fixtures/download_test_data.sh`
- ECOD data not found → Set `DPAM_TEST_DATA_DIR` or skip

**Check:**
```bash
pytest -v -rs  # Show skip reasons
```

### Import Errors

**Issue:** `ModuleNotFoundError: No module named 'dpam'`

**Solution:**
```bash
pip install -e .
```

### Test Failures

**Debug steps:**
1. Run with verbose: `pytest -vv tests/test_file.py::test_name`
2. Check test data: `ls -la tests/fixtures/`
3. Check tools: `which hhsearch foldseek dali.pl mkdssp`
4. Check imports: `python -c "import dpam; print(dpam.__file__)"`

## Performance

### Current Benchmarks

| Test Suite | Tests | Time | Notes |
|------------|-------|------|-------|
| Dependencies | ~30 | <5s | Tool checks |
| Unit tests | ~60 | <10s | Pure Python |
| Integration (1+13) | ~20 | ~2min | With fixtures |
| **Total** | **~110** | **~2min** | Fast feedback |

### Expected Times (Full Suite)

| Test Suite | Tests | Time |
|------------|-------|------|
| All unit tests | ~60 | <10s |
| Integration (13 steps) | ~100 | ~10min |
| Full pipeline | ~5 | ~20min |
| **Total** | **~165** | **~30min** |

## Best Practices

### Do's

✅ Write unit tests for all utility functions
✅ Test boundary conditions and edge cases
✅ Use descriptive test names
✅ Test error handling (invalid inputs)
✅ Keep tests independent (no shared state)
✅ Use fixtures for common setup
✅ Mark tests appropriately (unit/integration/slow)

### Don'ts

❌ Don't test implementation details
❌ Don't write tests that depend on order
❌ Don't use hardcoded paths (use fixtures)
❌ Don't skip cleanup (use tmp_path)
❌ Don't test external tools (test our wrappers)

## Summary

✅ **Minimal test suite implemented**
- Dependency validation (30 tests)
- Unit tests for critical utilities (60 tests)
- Integration tests for steps 1 and 13 (20 tests)
- ~110 tests total, ~2 minute runtime

✅ **Infrastructure complete**
- Pytest configuration
- Shared fixtures
- Test markers
- Coverage reporting
- Documentation

✅ **Ready to extend**
- Template for new tests
- CI/CD integration ready
- Clear structure for steps 2-12

**Next steps:**
1. `pip install -e ".[dev]"`
2. `cd tests/fixtures && ./download_test_data.sh`
3. `pytest -m unit`
4. Add integration tests for remaining steps as needed
