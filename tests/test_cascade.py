"""The traversal of gamma cascades (Recurlib.get_nrg_lev_end) on small
cascades, against the recursion of RecurLib 1.0, which it reproduces without
walking a cascade twice."""

import math
import os
import sys

import pandas as pd
import pytest

from trial_run import REPO_ROOT

os.environ.setdefault('MPLBACKEND', 'Agg')
sys.path.insert(0, str(REPO_ROOT))
import recurlib  # noqa: E402
from modules import inpout, mytoolkit  # noqa: E402

# The helper modules recurlib.py binds when run as a script or imported as
# modules.recurlib
recurlib.mt = mytoolkit
recurlib.io = inpout.InpOut()


def gammas(rows):
    """A gamma-cascade DF of (start level, its uncertainty, end level), with
    the start-level windows as set_gams() adds them."""
    df = pd.DataFrame(rows, columns=['start_level_energy', 'unc_sle',
                                     'end_level_energy'])
    df['sle_llim'] = df['start_level_energy'] - df['unc_sle']
    df['sle_ulim'] = df['start_level_energy'] + df['unc_sle']
    return df


def recursion_of_v1(df, start):
    """The tally of RecurLib 1.0 (no reuse, no cycle guard), with duplicates
    removed in the order of first identification and NaN left out, as
    set_gams() then used it."""
    def tally(nrg):
        hit = (df['sle_llim'] <= nrg) & (df['sle_ulim'] >= nrg)
        ends = df.loc[hit, 'end_level_energy'].to_list()
        out = []
        for ele in ends:
            out += tally(ele)
        return out + ends
    return list(dict.fromkeys(x for x in tally(start) if not math.isnan(x)))


@pytest.fixture
def rcl():
    return recurlib.Recurlib()


# 300 keV decays to 200 and 100 keV, 200 to 100 keV, 100 to 0 keV, and
# 250 keV (another start) to 200 keV; 150 keV has an unknown end level.
BRANCHED = gammas([
    (300.0, 0.1, 200.0), (300.0, 0.1, 100.0), (200.0, 0.1, 100.0),
    (100.0, 0.1, 0.0), (250.0, 0.1, 200.0), (150.0, 0.1, float('nan')),
])


@pytest.mark.parametrize('start', [300.0, 250.0, 200.0, 100.0, 0.0, 150.0])
def test_same_levels_in_the_same_order_as_v1(rcl, start):
    assert (rcl.get_nrg_lev_end(BRANCHED, start)
            == recursion_of_v1(BRANCHED, start))


def test_levels_within_the_start_level_uncertainty(rcl):
    assert rcl.get_nrg_lev_end(BRANCHED, 300.05) == [0.0, 100.0, 200.0]
    assert rcl.get_nrg_lev_end(BRANCHED, 300.2) == []


def test_unknown_uncertainty_never_matches(rcl):
    df = gammas([(100.0, float('nan'), 0.0)])
    assert rcl.get_nrg_lev_end(df, 100.0) == []


def test_unknown_end_levels_are_not_tallied(rcl):
    assert rcl.get_nrg_lev_end(BRANCHED, 150.0) == []


def test_reuse_gives_the_same_levels(rcl):
    memo = {}
    first = [rcl.get_nrg_lev_end(BRANCHED, s, memo=memo)
             for s in [250.0, 300.0]]
    assert 200.0 in memo  # Reached from 250 keV, reused from 300 keV
    again = [rcl.get_nrg_lev_end(BRANCHED, s, memo=memo)
             for s in [250.0, 300.0]]
    assert first == again == [recursion_of_v1(BRANCHED, 250.0),
                              recursion_of_v1(BRANCHED, 300.0)]


def test_unknown_start_level_adds_nothing(rcl):
    memo = {}
    assert rcl.get_nrg_lev_end(BRANCHED, float('nan'), memo=memo) == []
    assert memo == {}


def test_visiting_is_left_empty(rcl):
    visiting = set()
    rcl.get_nrg_lev_end(BRANCHED, 300.0, visiting=visiting)
    assert visiting == set()


def test_a_cycle_ends(rcl):
    """100 -> 50 -> 100 keV made RecurLib 1.0 recurse without end; it now
    stops, and the levels reached on a cut path are not memoized."""
    df = gammas([(100.0, 0.1, 50.0), (50.0, 0.1, 100.0), (50.0, 0.1, 0.0)])
    memo = {}
    assert set(rcl.get_nrg_lev_end(df, 100.0, memo=memo)) == {0.0, 50.0,
                                                              100.0}
    assert 50.0 not in memo
    assert set(rcl.get_nrg_lev_end(df, 50.0, memo=memo)) == {0.0, 50.0,
                                                             100.0}


def test_overlapping_windows_end(rcl):
    """Transitions that all go downward can still loop through overlapping
    start-level windows: 99.8 keV lies within 100.0 +/- 0.5 keV."""
    df = gammas([(100.0, 0.5, 99.8), (99.8, 0.1, 0.0)])
    assert set(rcl.get_nrg_lev_end(df, 100.0)) == {0.0, 99.8}


def write_gammas(folder, rn, rows):
    """A gamma-cascade file of rn as the Live Chart of Nuclides gives it."""
    (folder / rn).mkdir(parents=True)
    pd.DataFrame(rows, columns=['start_level_energy', 'unc_sle',
                                'end_level_energy']).to_csv(
        folder / rn / f'{rn}_gammas.csv')


def test_cascades_are_kept_per_gamma_data_file(rcl, tmp_path):
    """Two radionuclides, or one radionuclide in two nuclear data folders,
    with the same start level but different gamma data, keep their own
    cascades: the memo of one file is not used for another."""
    first, second = tmp_path / 'first', tmp_path / 'second'
    write_gammas(first, 'Xx-1', [(300.0, 0.1, 100.0), (100.0, 0.1, 0.0)])
    write_gammas(first, 'Yy-1', [(300.0, 0.1, 200.0)])
    write_gammas(second, 'Xx-1', [(300.0, 0.1, 50.0)])
    reached = {}
    for folder, rn in [(first, 'Xx-1'), (first, 'Yy-1'), (second, 'Xx-1')]:
        rcl.levs = {rn: {'from_Pp-1': {'energy_levels': [300.0]}}}
        rcl.set_gams(rn, str(folder))
        reached[(folder.name, rn)] = rcl.levs[rn]['from_gamma_cascade'][
            'energy_levels']
    assert reached == {('first', 'Xx-1'): [0.0, 100.0],
                       ('first', 'Yy-1'): [200.0],
                       ('second', 'Xx-1'): [50.0]}
