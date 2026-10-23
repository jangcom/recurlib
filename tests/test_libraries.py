"""Properties of the libraries of ./inp/trial.yaml and ./tests/inp/extra.yaml,
checked independently of the expected outputs under ./tests/golden: the
decay chains published in Phys. Rev. Research 6, 043208 (2024), the merged
settings, the cutoffs, the radiation and priority numbers, nuclear isomers
and exclusions, and the Gamma Explorer exports.
"""

import copy
import math
import re
import xml.etree.ElementTree as ET

import pandas as pd
import pytest

from trial_run import (ALL_DATASETS, EXTRA_INPUT, FIXTURE, FLAG, REPO_ROOT,
                       read_library, read_yaml)

#
# The lineages of Supplemental Figs. 5-8 of the paper
#
_TL205 = {'Pb-209': {'Bi-209': {'Tl-205': {}}}}
_BI213 = {'Tl-209': _TL205, 'Po-213': _TL205}
_PB210 = {'Hg-206': {'Tl-206': {'Pb-206': {}}},
          'Bi-210': {'Tl-206': {'Pb-206': {}}, 'Po-210': {'Pb-206': {}}}}
_PO215 = {'Pb-211': {'Bi-211': {'Tl-207': {'Pb-207': {}},
                                'Po-211': {'Pb-207': {}}}}}
_RA223 = {'Rn-219': {'Po-215': _PO215}}
PUBLISHED_LINEAGES = {
    'Th-232': {'Th-232': {'Ra-228': {'Ac-228': {'Th-228': {'Ra-224': {
        'Rn-220': {'Po-216': {'Pb-212': {'Bi-212': {
            'Tl-208': {'Pb-208': {}}, 'Po-212': {'Pb-208': {}}}}}}}}}}}},
    'Np-237': {'Np-237': {'Pa-233': {'U-233': {'Th-229': {'Ra-225': {
        'Rn-221': {'Po-217': {'Pb-213': {'Bi-213': _BI213}},
                   'Fr-221': {'At-217': {'Bi-213': _BI213}}},
        'Ac-225': {'Fr-221': {'At-217': {'Bi-213': _BI213}}}}}}}}},
    'U-238': {'U-238': {'Th-234': {'Pa-234': {'U-234': {'Th-230': {
        'Ra-226': {'Rn-222': {'Po-218': {'Pb-214': {'Bi-214': {
            'Tl-210': {'Pb-210': _PB210},
            'Po-214': {'Pb-210': _PB210}}}}}}}}}}}},
    'U-235': {'U-235': {'Th-231': {'Pa-231': {'Ac-227': {
        'Fr-223': {'At-219': {'Bi-215': {'Po-215': _PO215}},
                   'Ra-223': _RA223},
        'Th-227': {'Ra-223': _RA223}}}}}},
}


def nodes(tree):
    out = set()
    for k, v in tree.items():
        out.add(k)
        out |= nodes(v)
    return out


def base_name(name):
    """'Pa-234m;73.92' -> 'Pa-234'; 'Pa-234m' -> 'Pa-234'."""
    return re.match(r'^([A-Z][a-z]?-\d+)', name).group(1)


@pytest.fixture(params=list(ALL_DATASETS))
def case(request):
    """(dataset, run) for each dataset of the two inputs."""
    return request.param, request.getfixturevalue(FIXTURE[request.param])


def settings(run, dataset):
    """The effective settings of a dataset, as the run echoed them."""
    return read_yaml(run.figs / f'{dataset}{FLAG}_echo.yaml')


def library(run, dataset):
    return read_library(run.figs / f'{dataset}{FLAG}.csv')


def is_beta(s):
    return s['scout']['radionuclides']['spectrum_radiation'] == 'beta minus'


def col(s, key):
    """The library column of a key of io > cols; for a beta-minus library,
    energy and emission probability are those RecurLib cuts and ranks by:
    the maximum energy and the beta emission probability."""
    if is_beta(s):
        key = {'energy': 'energy_bm_max',
               'emission_probability': 'emission_probability_bm'}.get(key,
                                                                      key)
    return s['io']['cols'][key]['nucl_data_new']


def test_lineages_reproduce_the_paper(case):
    dataset, run = case
    for prog in ALL_DATASETS[dataset]:
        got = read_yaml(run.figs / f'{dataset}{FLAG}_{prog}_lineage.yaml')
        assert got == PUBLISHED_LINEAGES[prog]


def _merge(base, over):
    """base deep-updated by over: dicts merge, anything else replaces."""
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


# Names RecurLib adds under io > out for the files of a dataset
DERIVED_OUT_KEYS = {
    'echo_bname', 'echo_fname_full', 'export_bname', 'fig_bname',
    'lev_bname', 'lev_fname_full', 'lineage_bname', 'lineage_fname',
    'lineage_fname_full', 'rpt_bname'}


def test_settings_are_the_template_merged_with_the_dataset(case):
    """The echoed settings equal the initialization file's template deep-
    updated by the dataset, with the recursive and static lists normalised
    (empty entries dropped, isomer suffix and energy level removed; the
    exclusion list is kept as written) and the output names added."""
    dataset, run = case
    ini = read_yaml(REPO_ROOT / 'inp' / 'ini_recurlib.yaml')['template']
    inp = (REPO_ROOT / 'inp' / 'trial.yaml' if FIXTURE[dataset] == 'trial'
           else EXTRA_INPUT)
    want = _merge(ini, read_yaml(inp)[dataset])
    rns = want['scout']['radionuclides']
    for group in ['recursive', 'static']:
        rns[group] = [base_name(n) for n in rns[group] if n]
    got = settings(run, dataset)
    out = got['io']['out']
    assert DERIVED_OUT_KEYS <= set(out)
    bname = dataset + want['io']['out']['flag']
    assert out['rpt_bname'] == out['fig_bname'] == bname
    assert out['export_bname'] == 'recurlib_' + bname
    for key in DERIVED_OUT_KEYS:
        out.pop(key)
    assert got == want


def test_library_holds_only_chain_members(case):
    """Every nuclide is a member of a recursive progenitor's chain or a
    static radionuclide, and none is excluded."""
    dataset, run = case
    s = settings(run, dataset)
    rns = s['scout']['radionuclides']
    members = {base_name(n) for n in rns['static']}
    for prog in ALL_DATASETS[dataset]:
        members |= nodes(PUBLISHED_LINEAGES[prog])
    labels = set(library(run, dataset)[col(s, 'radionuclide')])
    assert {base_name(lb) for lb in labels} <= members
    assert not labels & set(rns['exclusion'])


def test_lines_lie_within_the_cutoffs(case):
    dataset, run = case
    s = settings(run, dataset)
    cut = s['scout']['radionuclides']['cutoffs']
    df = library(run, dataset)
    assert len(df) > 0
    for key, cutoff in [('energy', 'energy'),
                        ('emission_probability', 'emission_probability'),
                        ('half_life_sec', 'half_life_sec')]:
        lo, hi = (float(x) for x in cut[cutoff])
        values = df[col(s, key)]
        assert values.notna().all(), key
        assert ((values >= lo) & (values <= hi)).all(), key


def test_radiation_numbers_count_up_per_nuclide(case):
    dataset, run = case
    s = settings(run, dataset)
    df = library(run, dataset)
    for label, rows in df.groupby(col(s, 'radionuclide'), sort=False):
        assert list(rows[col(s, 'radiation_number')]) == list(
            range(1, len(rows) + 1)), label


def test_key_lines_are_the_most_probable(case):
    """Per nuclide (an isomer apart), the lines within the key-line energy
    window ranked by emission probability: 1, 2, ... up to the maximum;
    every other line 0. Ties may rank either way."""
    dataset, run = case
    s = settings(run, dataset)
    cut = s['scout']['radionuclides']['cutoffs']
    lo, hi = (float(x) for x in cut['priority_number_energy'])
    n_max = int(cut['priority_number_max'])
    c_nrg, c_ep = col(s, 'energy'), col(s, 'emission_probability')
    c_key = col(s, 'priority_number')
    df = library(run, dataset)
    for label, rows in df.groupby(col(s, 'radionuclide'), sort=False):
        inside = rows[(rows[c_nrg] >= lo) & (rows[c_nrg] <= hi)]
        n = min(n_max, len(inside))
        assert (rows.loc[~rows.index.isin(inside.index), c_key] == 0).all()
        keyed = inside[inside[c_key] > 0].sort_values(c_key)
        assert list(keyed[c_key]) == list(range(1, n + 1)), label
        eps = list(keyed[c_ep])
        assert eps == sorted(eps, reverse=True), label
        others = inside.loc[inside[c_key] == 0, c_ep]
        if n and len(others):
            assert others.max() <= eps[-1], label


def test_lines_come_from_the_ground_state_or_the_isomer(case):
    """In these chains every line of a nuclide comes from its ground state
    (parent energy level 0), and every line of an isomer label from one
    excited level: Pa-234m at 73.92 keV, the only isomer they hold."""
    dataset, run = case
    s = settings(run, dataset)
    df = library(run, dataset)
    labels = df[col(s, 'radionuclide')]
    levels = df[col(s, 'energy_level')]
    assert (levels[~labels.str.endswith('m')] == 0).all()
    isomers = df[labels.str.endswith('m')]
    assert set(isomers[col(s, 'radionuclide')]) <= {'Pa-234m'}
    assert ((isomers[col(s, 'energy_level')] - 73.92).abs() < 1e-9).all()


@pytest.mark.parametrize('dataset', ['uranium_series_gamma', 'mixture_gamma'])
def test_isomer_stays_when_its_ground_state_is_excluded(request, dataset):
    """Pa-234 is excluded; its isomer Pa-234m, reached at 73.92 keV by the
    beta decay of Th-234, stays (the exclusion follows isomer labelling)."""
    run = request.getfixturevalue(FIXTURE[dataset])
    s = settings(run, dataset)
    assert s['scout']['radionuclides']['exclusion'] == ['Pa-234']
    df = library(run, dataset)
    labels = df[col(s, 'radionuclide')]
    assert 'Pa-234' not in set(labels)
    pa = df[labels == 'Pa-234m']
    assert len(pa) > 0
    assert ((pa[col(s, 'half_life')] - 1.159).abs() < 1e-9).all()
    assert set(pa[col(s, 'half_life_unit')]) == {'m'}
    assert set(pa[col(s, 'decay_mode')]) <= {'B-', 'IT'}


def _children(root, tag):
    return [{c.tag: (c.text or '') for c in el} for el in root.findall(tag)]


@pytest.fixture(params=[
    pytest.param(ds, marks=pytest.mark.xfail(
        strict=True, reason='Known bug: for a beta-minus library, '
        'get_context stores the energies under energy_bm_max and '
        'emission_probability_bm, while the templates read energy and '
        'emission_probability, so every peak is written empty'))
    if ds == 'beta_minus' else ds
    for ds in ALL_DATASETS])
def export_case(request):
    return request.param, request.getfixturevalue(FIXTURE[request.param])


def test_gamma_explorer_exports_hold_the_library(export_case):
    dataset, run = export_case
    s = settings(run, dataset)
    df = library(run, dataset)
    c_rn = col(s, 'radionuclide')
    bname = f'recurlib_{dataset}{FLAG}'
    master = ET.parse(run.exports / f'{bname}_gexp_01_master.xml').getroot()
    group = ET.parse(run.exports / f'{bname}_gexp_02_group.xml').getroot()

    source = _children(master, 'nuc_核データ出典')
    assert len(source) == 1
    assert len(source[0]['Code']) <= 28 + len('-mst')
    nuclides = _children(master, 'nuc_核種')
    assert [n['IsoName'] for n in nuclides] == list(df[c_rn].unique())
    names = {n['IsoCode']: n['IsoName'] for n in nuclides}

    peaks = _children(master, 'nuc_核種ピーク')
    assert len(peaks) == len(df)
    got = sorted((names[p['IsoCode']], int(p['PeakNo']), float(p['Energy']),
                  float(p['Abundance']), int(p['Priority'])) for p in peaks)
    want = sorted(zip(df[c_rn], df[col(s, 'radiation_number')],
                      df[col(s, 'energy')], df[col(s, 'emission_probability')],
                      df[col(s, 'priority_number')]))
    for g, w in zip(got, want):
        assert g[:2] == w[:2] and g[4] == w[4]
        assert math.isclose(g[2], w[2], rel_tol=1e-12)
        assert math.isclose(g[3], w[3], rel_tol=1e-12)

    assert len(_children(group, 'nuc_対象核種_List')) == len(nuclides)
    group_peaks = _children(group, 'nuc_対象核種_Pks')
    assert len(group_peaks) == len(df)
    assert (sum(int(p['Priority']) > 0 for p in group_peaks)
            == int((df[col(s, 'priority_number')] > 0).sum()))
