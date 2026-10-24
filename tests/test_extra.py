"""The test-only input ./tests/inp/extra.yaml, related to the trial run.

Each of its datasets changes one thing against a dataset of
./inp/trial.yaml (the cutoffs, the static and exclusion groups, several
recursive progenitors), so its library must be that dataset's library
changed in exactly that way.
"""

from trial_run import FLAG, EXTRA_DATASETS, read_library, read_yaml

RN = 'Radionuclide'
NRG = 'Radiation energy (keV)'
EP = 'Emission probability (%)'
HL = 'Half-life (s)'


def library(run, dataset):
    return read_library(run.figs / f'{dataset}{FLAG}.csv')


def lines(df):
    """The (nuclide, energy, emission probability) of each line."""
    return set(zip(df[RN], df[NRG].round(9), df[EP].round(9)))


def within(df, column, limits):
    lo, hi = (float(x) for x in limits)
    return df[(df[column] >= lo) & (df[column] <= hi)]


def test_extra_run_needs_no_network(extra):
    assert extra.requests == []
    assert all(f'Working on [{ds}]...' in extra.stdout
               for ds in EXTRA_DATASETS)


def test_tight_cutoffs_keep_exactly_the_lines_within_them(trial, extra):
    cut = read_yaml(extra.figs / f'tight_cutoffs{FLAG}_echo.yaml')[
        'scout']['radionuclides']['cutoffs']
    wide = library(trial, 'thorium_series_gamma')
    kept = within(within(within(wide, NRG, cut['energy']),
                         EP, cut['emission_probability']),
                  HL, cut['half_life_sec'])
    tight = library(extra, 'tight_cutoffs')
    assert 0 < len(tight) < len(wide)
    assert lines(tight) == lines(kept)


def test_each_tight_cutoff_binds(trial, extra):
    """Each bound of tight_cutoffs, alone, removes at least one line that
    the other five keep, so that the relation above tests all six."""
    cut = read_yaml(extra.figs / f'tight_cutoffs{FLAG}_echo.yaml')[
        'scout']['radionuclides']['cutoffs']
    wide = library(trial, 'thorium_series_gamma')
    bounds = {NRG: cut['energy'], EP: cut['emission_probability'],
              HL: cut['half_life_sec']}
    for column, (lo, hi) in bounds.items():
        others = wide
        for other, limits in bounds.items():
            if other != column:
                others = within(others, other, limits)
        assert (others[column] < float(lo)).any(), (column, 'lower')
        assert (others[column] > float(hi)).any(), (column, 'upper')


def test_mixture_is_the_union_of_its_series(trial, extra):
    """./inp/uatk.yaml without K-40: the uranium, actinium and thorium
    series together, Pa-234 excluded, within the mixture's cutoffs."""
    cut = read_yaml(extra.figs / f'mixture_gamma{FLAG}_echo.yaml')[
        'scout']['radionuclides']['cutoffs']
    series = [library(trial, ds) for ds in ['uranium_series_gamma',
                                            'actinium_series_gamma',
                                            'thorium_series_gamma']]
    union = set()
    for df in series:
        union |= lines(within(within(df, NRG, cut['energy']),
                              EP, cut['emission_probability']))
    assert lines(library(extra, 'mixture_gamma')) == union


def test_static_and_excluded_nuclides(trial, extra):
    """Static nuclides bring their own lines but not their progeny's; an
    excluded progeny of the recursive chain leaves the rest of it as is.

    The static isomer Pa-234m;73.92 also brings the ground state Pa-234
    (6.70 h), which its own gamma cascade reaches; the expected outputs
    under ./tests/golden record that.
    """
    mixed = library(extra, 'static_and_isomer')
    thorium = library(trial, 'thorium_series_gamma')
    uranium = library(trial, 'uranium_series_gamma')
    statics = {'Pa-234m', 'Pa-234', 'Ra-226'}
    assert (lines(mixed[~mixed[RN].isin(statics)])
            == lines(thorium[thorium[RN] != 'Tl-208']))
    for rn in ['Pa-234m', 'Ra-226']:
        assert lines(mixed[mixed[RN] == rn]) == lines(uranium[uranium[RN]
                                                              == rn])
    # Ra-226's progeny are not followed
    assert not set(mixed[RN]) & {'Rn-222', 'Pb-214', 'Bi-214', 'Pb-210'}
    assert set(mixed.loc[mixed[RN] == 'Pa-234', 'Decay mode']) == {'B-'}


def test_xray_key_lines_change_only_the_priority_numbers(trial, extra):
    """Allowing X-rays as key lines changes no line, only priority
    numbers."""
    default = library(trial, 'thorium_series_gamma')
    allowed = library(extra, 'xray_key_lines')
    keep = [c for c in default.columns if c != 'Priority number']
    assert allowed[keep].equals(default[keep])
    assert not allowed['Priority number'].equals(default['Priority number'])
