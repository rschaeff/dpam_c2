"""
Regression tests for the gated adjacency merge in step19 (MERGE_FRAGMENT_DEFICIENCY.md).

Guards two things at once:
  1. The FIX: an orphan fragment embedded in an ECOD-hitless domain must now be proposed
     for merge (previously invisible -> survived to final output as a 25aa "domain").
  2. The SAFEGUARD: the adjacency rule must NOT re-introduce merging of dissimilar H/T
     groups (the reason the adjacency rule was originally forgone), and must NOT absorb
     small-but-real domains (e.g. Zn-fingers).

The acceptance criterion mirrors the fold-aware QC gate used on the resplit campaign
(analysis/tier_a_run/qc_gate.py): a domain is a FRAGMENT only if it is smaller than ANY
curated ECOD domain of its own T-group AND < 0.5x that fold's median.
"""
import pytest

from dpam.steps.step19_get_merge_candidates import (
    is_fragment, ht_compatible, is_adjacent, h_group, run_step19,
)

# Curated size profiles (t_id -> n, min, p05, median), as loaded from ECOD_tgroup_sizes.
TG = {
    "109.4.1": dict(n=651, min=103.0, p05=176.0, med=282.0),   # ARM repeat
    "5.1.4":   dict(n=185, min=180.0, p05=316.0, med=348.0),   # 7-bladed propeller
    "101.1.1": dict(n=233, min=29.0,  p05=47.0,  med=73.0),    # small-domain fold (Zn-finger-like)
    "2002.1.1": dict(n=400, min=150.0, p05=200.0, med=319.0),  # TIM barrel
}


class TestFragmentGate:
    """Gate 1: fold-aware size floor."""

    def test_arm_sliver_is_fragment(self):
        # 25aa piece assigned to ARM (curated median 282) -> unambiguous fragment
        assert is_fragment(25, "109.4.1", TG)

    def test_propeller_blade_is_fragment(self):
        # a single 30aa blade of a 7-bladed propeller is not a domain
        assert is_fragment(30, "5.1.4", TG)

    def test_small_but_real_domain_is_protected(self):
        # SAFEGUARD: a 35aa domain in a fold whose curated min is 29 is REAL, not a fragment.
        # A flat size floor would wrongly absorb this (the Zn-finger class).
        assert not is_fragment(35, "101.1.1", TG)

    def test_full_size_domain_never_a_fragment(self):
        assert not is_fragment(282, "109.4.1", TG)
        assert not is_fragment(319, "2002.1.1", TG)

    def test_below_absolute_floor_is_always_fragment(self):
        assert is_fragment(12, "101.1.1", TG)   # below ABS_MIN_DOMAIN regardless of fold

    def test_uncalibrated_tgroup_falls_back_to_absolute_floor(self):
        # unknown/low-n T-group: do not guess -> only the absolute floor applies
        assert not is_fragment(60, "9999.9.9", TG)
        assert is_fragment(10, "9999.9.9", TG)


class TestHTCompatibilityGate:
    """Gate 2: the safeguard the template-sharing rule used to provide."""

    def test_same_hgroup_allowed(self):
        assert ht_compatible("109.4.1", "109.4.2")   # same H-group 109.4

    def test_different_hgroup_forbidden(self):
        # SAFEGUARD: a TIM barrel must never be fused into an ARM repeat by adjacency
        assert not ht_compatible("2002.1.1", "109.4.1")

    def test_unassigned_side_allowed(self):
        # the D7/D8 case: acceptor has no ECOD hit -> permitted
        assert ht_compatible("109.4.1", "")
        assert ht_compatible("", "109.4.1")

    def test_h_group_parsing(self):
        assert h_group("109.4.1") == "109.4"
        assert h_group("") == ""


class TestAdjacencyGate:
    """Gate 3: embedding / sequence proximity."""

    def test_embedded_fragment_is_adjacent(self):
        # the real case: D8 (1511-1535) sits inside D7 (1196-1510, 1536-1560)
        frag = set(range(1511, 1536))
        host = set(range(1196, 1511)) | set(range(1536, 1561))
        assert is_adjacent(frag, host)

    def test_distant_domains_not_adjacent(self):
        # D8 vs a domain ~1000 residues away -> must NOT be adjacent
        assert not is_adjacent(set(range(1511, 1536)), set(range(1, 71)))


class TestStep19Integration:
    """End-to-end on a fixture reproducing the K7MVJ7 defect + both safeguard cases."""

    @pytest.fixture
    def workdir(self, tmp_path):
        prefix = "AF-TEST-F1"
        # step13: D1 host (no ECOD hit), D2 fragment embedded in D1,
        #         D3 full TIM-barrel adjacent to D2 (different H-group -> must not merge),
        #         D4 small-but-real Zn-finger-like domain adjacent to D3 (must not be absorbed)
        (tmp_path / f"{prefix}.step13_domains").write_text(
            "D1\t100-400,451-500\n"     # host, ECOD-hitless
            "D2\t401-450\n"             # 50aa... make it a true fragment below ARM floor
            "D3\t501-820\n"             # 320aa TIM barrel (full size, different H-group)
            "D4\t821-860\n"             # 40aa 101.1.1 domain (small but REAL)
        )
        # step18: only D2, D3, D4 have ECOD hits. D1 has none (that is the bug's trigger).
        hdr = "domain\trange\tecod\ttgroup\tprob\tquality\thh_range\tdali_range\n"
        (tmp_path / f"{prefix}.step18_mappings").write_text(
            hdr
            + "D2\t401-450\te1armA1\t109.4.1\t0.90\tgood\t1-50\tna\n"
            + "D3\t501-820\te1timA1\t2002.1.1\t0.99\tgood\t1-320\tna\n"
            + "D4\t821-860\te1zncA1\t101.1.1\t0.95\tgood\t1-40\tna\n"
        )
        return tmp_path, prefix

    def _adjacency_pairs(self, tmp_path, prefix):
        info = tmp_path / f"{prefix}.step19_merge_info"
        if not info.exists():
            return []
        return [l.split('\t')[0] for l in info.read_text().splitlines() if "ADJACENCY" in l]

    def test_embedded_fragment_now_proposed(self, workdir, tmp_path_factory):
        tmp_path, prefix = workdir
        data_dir = tmp_path_factory.mktemp("data")
        (data_dir / "ECOD_length").write_text(
            "0\te1armA1\t282\n0\te1timA1\t319\n0\te1zncA1\t73\n"
        )
        (data_dir / "ECOD_tgroup_sizes").write_text(
            "109.4.1\t651\t103\t176\t282\n"
            "2002.1.1\t400\t150\t200\t319\n"
            "101.1.1\t233\t29\t47\t73\n"
        )
        assert run_step19(prefix, tmp_path, data_dir) is True

        pairs = self._adjacency_pairs(tmp_path, prefix)

        # THE FIX: the fragment D2 must now be proposed against its ECOD-hitless host D1.
        assert any(set(p.split(',')) == {"D2", "D1"} for p in pairs), \
            f"embedded fragment D2 was not proposed against its host D1; got {pairs}"

        # SAFEGUARD 1: D2 (ARM, 109.4) must NOT be proposed against D3 (TIM barrel, 2002.1)
        assert not any(set(p.split(',')) == {"D2", "D3"} for p in pairs), \
            "adjacency merged across dissimilar H-groups (109.4 vs 2002.1)"

        # SAFEGUARD 2: D4 is small (40aa) but AT/ABOVE its fold's curated min (29) -> it is a
        # real domain and must never be absorbed by adjacency.
        assert not any("D4" in p.split(',') for p in pairs), \
            "a small-but-real domain (Zn-finger class) was absorbed by the adjacency pass"
