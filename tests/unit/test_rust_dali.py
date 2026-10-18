"""
Rust DALI backend must fail loudly when the `dali` module cannot be imported.

Previously RustDALI logged an error and returned empty results, so step 7
wrote empty hit files and a .done marker for every protein.
"""

import sys

import pytest

from dpam.tools.dali import RustDALI
from dpam.steps.step07_iterative_dali import run_step7


@pytest.fixture
def no_dali(monkeypatch):
    # A None entry in sys.modules makes `import dali` raise ImportError
    monkeypatch.setitem(sys.modules, 'dali', None)


def test_rustdali_raises_without_module(no_dali):
    with pytest.raises(ImportError, match=sys.executable):
        RustDALI()


def test_step7_fails_without_module(no_dali, monkeypatch, tmp_path):
    monkeypatch.setenv('DPAM_DALI_BACKEND', 'rust')
    monkeypatch.delenv('DPAM_DALI_RUST_BATCH', raising=False)
    prefix, edomain = 'query', 'e000000001'
    work = tmp_path / 'work'   # flat layout (PathResolver sharded=False)
    data = tmp_path / 'data'
    work.mkdir()
    (data / 'ECOD70').mkdir(parents=True)
    (work / f'{prefix}.pdb').write_text('END\n')
    (data / 'ECOD70' / f'{edomain}.pdb').write_text('END\n')
    (work / f'{prefix}_hits4Dali').write_text(edomain + '\n')

    assert run_step7(prefix, work, data, cpus=1) is False
    assert not (work / f'{prefix}.iterativeDali.done').exists()
    assert not (work / f'{prefix}_iterativdDali_hits').exists()
