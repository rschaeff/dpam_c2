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


def test_fortran_report_rounds_z_and_inverts_superposition():
    from dpam.tools.dali import _fortran_report

    # 90 degrees about z; dali_cl's (R, t) is the inverse of DaliLite's
    rot = [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
    z, rows, trans = _fortran_report(4.238896, rot, [1.0, 2.0, 3.0])

    assert z == 4.2
    assert rows == ['0.000000\t1.000000\t0.000000',
                    '-1.000000\t0.000000\t0.000000',
                    '0.000000\t0.000000\t1.000000']
    assert trans == ['-2.000000', '1.000000', '-3.000000']


class _FakeHit:
    zscore = 5.04
    qlen = 30
    rotation = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    translation = [0.0, 0.0, 0.0]
    alignments = [(i, i) for i in range(1, 21)]
    query_resids = list(range(1, 21))


def _fake_dali(log, raise_in_search=False):
    """Stand-in for the dali_cl module; records the template code searched."""
    class Protein:
        code = 't'

    class Store:
        def __init__(self, path):
            pass

        def add_protein(self, protein):
            pass

    def iterative_search_pdb(query, templates, store, **kwargs):
        with open(log, 'a') as f:
            f.write(templates[0] + '\n')
        if raise_in_search:
            raise RuntimeError('boom')
        return [_FakeHit()]

    import types
    return types.SimpleNamespace(
        ProteinStore=Store,
        import_pdb=lambda path, chain, code: Protein(),
        iterative_search_pdb=iterative_search_pdb,
    )


@pytest.fixture
def rust_step7(monkeypatch, tmp_path):
    monkeypatch.setenv('DPAM_DALI_BACKEND', 'rust')
    monkeypatch.delenv('DPAM_DALI_RUST_BATCH', raising=False)
    prefix, edomain = 'query', 'e000000001'
    work = tmp_path / 'work'
    data = tmp_path / 'data'
    work.mkdir()
    (data / 'ECOD70').mkdir(parents=True)
    (work / f'{prefix}.pdb').write_text('END\n')
    (data / 'ECOD70' / f'{edomain}.pdb').write_text('END\n')
    (work / f'{prefix}_hits4Dali').write_text(edomain + '\n')
    log = tmp_path / 'searched'

    def install(**kwargs):
        # Pool workers are forked, so they see this module too
        monkeypatch.setitem(sys.modules, 'dali', _fake_dali(log, **kwargs))

    return prefix, edomain, work, data, log, install


def test_step7_search_error_is_not_no_hits(rust_step7):
    prefix, _, work, data, _, install = rust_step7
    install(raise_in_search=True)

    assert run_step7(prefix, work, data, cpus=1) is False
    assert not (work / f'{prefix}.iterativeDali.done').exists()


def test_step7_discards_stale_partial_hits(rust_step7):
    prefix, edomain, work, data, _, install = rust_step7
    install()
    stale = work / f'iterativeDali_{prefix}'
    stale.mkdir()
    (stale / f'{prefix}_{edomain}_hits').write_text('>stale_1\t9.9\t20\t30\t0\n')

    assert run_step7(prefix, work, data, cpus=1) is True
    hits = (work / f'{prefix}_iterativdDali_hits').read_text()
    assert 'stale' not in hits
    assert hits.count('>') == 1
    assert hits.startswith(f'>{edomain}_1\t5.0\t20\t30\t0\n')


def test_step7_uses_ecod70_dat_by_default(rust_step7):
    prefix, edomain, work, data, log, install = rust_step7
    install()
    (data / 'ECOD70_dat').mkdir()
    (data / 'ECOD70_dat' / f'{edomain}.dat').write_text('')

    assert run_step7(prefix, work, data, cpus=1) is True
    # .dat symlinked under its own stem rather than imported (code 't')
    assert log.read_text().split() == [edomain]
