"""The comparison helpers of trial_run.py: what they forgive and what they
must not."""

import pandas as pd
import pytest

from trial_run import GOLDEN_DIR, assert_library_equal, canonical_levels

GOLDEN = GOLDEN_DIR / 'actinium_series_alpha_lib.csv'


def edited(tmp_path, edit):
    df = pd.read_csv(GOLDEN, keep_default_na=False, na_values=[''])
    edit(df)
    path = tmp_path / GOLDEN.name
    df.to_csv(path, index=False)
    return path


def ra223(df, energy):
    return (df['Radionuclide'] == 'Ra-223') & (
        (df['Radiation energy (keV)'] - energy).abs() < 1e-9)


def test_golden_holds_the_ra223_tie():
    """The tie is broken by the energy uncertainty, 0.4 keV against
    0.9 keV, the emission-probability uncertainties being equal."""
    df = pd.read_csv(GOLDEN)
    tied = df[ra223(df, 5539.8) | ra223(df, 5747.0)]
    assert tied['Emission probability (%)'].nunique() == 1
    assert tied['Uncertainty of emission probability (%)'].nunique() == 1
    keyed = tied.set_index('Radiation energy (keV)')['Priority number']
    assert keyed[5747.0] == 3 and keyed[5539.8] == 0


def test_tied_key_lines_may_not_trade_places(tmp_path):
    """Ra-223 at 5539.8 and 5747.0 keV have the same emission probability;
    RecurLib breaks the tie by the uncertainties, so trading their priority
    numbers is a change."""
    def swap(df):
        a, b = ra223(df, 5539.8), ra223(df, 5747.0)
        df.loc[a, 'Priority number'], df.loc[b, 'Priority number'] = (
            df.loc[b, 'Priority number'].values,
            df.loc[a, 'Priority number'].values)
    with pytest.raises(AssertionError):
        assert_library_equal(edited(tmp_path, swap), GOLDEN)


def test_other_key_line_changes_fail(tmp_path):
    def promote(df):
        df.loc[ra223(df, 5747.0), 'Priority number'] = 0
        df.loc[ra223(df, 5433.6), 'Priority number'] = 3
    with pytest.raises(AssertionError):
        assert_library_equal(edited(tmp_path, promote), GOLDEN)


def test_value_changes_fail(tmp_path):
    def nudge(df):
        df.loc[ra223(df, 5747.0), 'Emission probability (%)'] = 8.9000001
    with pytest.raises(AssertionError):
        assert_library_equal(edited(tmp_path, nudge), GOLDEN)


def test_level_sets_ignore_order_but_limits_keep_it():
    a = {'energy_levels_flattened': [2.0, float('nan'), 1.0],
         'self': {'B-': {'energy_levels': [[0.0, 0.1], [73.9, 73.95]]}}}
    b = {'energy_levels_flattened': [float('nan'), 1.0, 2.0],
         'self': {'B-': {'energy_levels': [[0.0, 0.1], [73.9, 73.95]]}}}
    assert canonical_levels(a) == canonical_levels(b)
    b['self']['B-']['energy_levels'][1] = [73.95, 73.9]
    assert canonical_levels(a) != canonical_levels(b)
