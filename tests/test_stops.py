"""How a run ends when its input is wrong.

A deliberate stop shows a warning block whose last line is "Terminating."
and exits with status 1, without a traceback and without touching the
nuclear data folder. Mistakes that concern one dataset only (a name not
defined, an empty dataset, a library left empty) are warnings: the run
goes on with the other datasets and exits with status 0.
"""

import re

import pytest
import yaml

from trial_run import (GOLDEN_DIR, assert_library_equal, file_digests,
                       make_workspace, read_library, run_input)

THORIUM = {'scout': {'radionuclides': {'recursive': ['Th-232']}}}


def write_input(work, name, content):
    """Write ./inp/<name>: a dict as YAML, or a str as it is."""
    text = (content if isinstance(content, str)
            else yaml.safe_dump(content, sort_keys=False))
    (work / 'inp' / name).write_text(text, encoding='utf-8')


def thorium_with(**radionuclides):
    """THORIUM with the given scout > radionuclides settings."""
    rns = dict(THORIUM['scout']['radionuclides'], **radionuclides)
    return {'active_datasets': ['thorium'],
            'thorium': {'scout': {'radionuclides': rns}}}


def cutoff(**cutoffs):
    return thorium_with(cutoffs=cutoffs)


STOPS = {
    'missing input file': (None, ['could not be located']),
    'not valid YAML': ('active_datasets: [unclosed\n',
                       ['could not be parsed']),
    'empty input file': ('', ['[active_datasets] has no element.']),
    'no active_datasets': ({'thorium': THORIUM},
                           ['[active_datasets] has no element.']),
    'empty active_datasets': ({'active_datasets': [], 'thorium': THORIUM},
                              ['[active_datasets] has no element.']),
    'unknown radiation': (thorium_with(spectrum_radiation='gammas'),
                          ['has been set to be [gammas]',
                           'It must be one of [alpha, gamma, beta minus]']),
    'non-numeric cutoff': (cutoff(energy=[0, 'lots']),
                           ['[scout > radionuclides > cutoffs > energy]'
                            ' must be a pair of numbers']),
    'reversed cutoff': (cutoff(energy=[2e3, 1e2]),
                        ['The lower limit of [scout > radionuclides >'
                         ' cutoffs > energy] exceeds its upper limit']),
    'negative key-line count': (cutoff(priority_number_max=-1),
                                ['priority_number_max] must be a whole'
                                 ' number of 0 or more', '[-1]']),
    'unknown sort key': (dict(thorium_with(), thorium=dict(
        THORIUM, io={'cols_sort': {'toggle': True, 'by': 'colour'}})),
        ['[io > cols_sort > by] is [colour]', 'for a gamma library',
         'radionuclide']),
}


def assert_stopped(run, phrases):
    out = run.stdout + run.stderr
    assert run.returncode == 1, out[-3000:]
    assert 'Traceback' not in run.stderr, run.stderr[-3000:]
    lines = run.stdout.rstrip().splitlines()
    assert lines[-2] == 'Terminating.', lines[-6:]
    assert set(lines[-1]) == {'*'}  # The closing border of the warning
    for phrase in phrases:
        assert phrase in run.stdout, (phrase, run.stdout[-2000:])


@pytest.mark.parametrize('case', STOPS)
def test_wrong_input_stops_cleanly(tmp_path, repo_root, case):
    content, phrases = STOPS[case]
    work = make_workspace(tmp_path / 'w')
    if content is not None:
        write_input(work, 'case.yaml', content)
    run = run_input(work, 'case.yaml')
    assert_stopped(run, phrases)
    assert (file_digests(work / 'lib')
            == file_digests(repo_root / 'lib'))
    assert not list(work.glob('figs/*.csv'))


def test_network_down_stops_cleanly(tmp_path):
    """K-40 is not in the shipped nuclear data folder."""
    work = make_workspace(tmp_path / 'w')
    write_input(work, 'case.yaml', {
        'active_datasets': ['potassium'],
        'potassium': {'scout': {'radionuclides': {'recursive': ['K-40']}}}})
    run = run_input(work, 'case.yaml', network='down')
    assert_stopped(run, ['Could not reach the Live Chart of Nuclides',
                         'do not have Internet access'])
    assert not (work / 'lib' / 'nucl_data' / 'K-40').exists()


def test_network_timeout_stops_cleanly(tmp_path):
    work = make_workspace(tmp_path / 'w')
    write_input(work, 'case.yaml', {
        'active_datasets': ['potassium'],
        'potassium': {'scout': {'radionuclides': {'recursive': ['K-40']}}}})
    run = run_input(work, 'case.yaml', network='timeout')
    assert_stopped(run, ['Could not reach the Live Chart of Nuclides'
                         ' server (no answer within 60 s)'])


def test_missing_output_folders_are_created_without_asking(tmp_path):
    """Nested folders for the tables, figures and exports that do not
    exist yet are created, with no question on the shell (whose input is
    empty here)."""
    work = make_workspace(tmp_path / 'w')
    write_input(work, 'case.yaml', dict(thorium_with(), thorium=dict(
        THORIUM, io={'out': {'rpt_path': './out/tables',
                             'fig_path': './out/figures/png',
                             'export_path': './out/exports'}})))
    run = run_input(work, 'case.yaml')
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    for folder in ['out/tables', 'out/figures/png', 'out/exports']:
        assert '[./' + folder + '] generated.' in run.stdout
    assert (work / 'out' / 'tables' / 'thorium_lib.csv').is_file()
    assert list((work / 'out' / 'figures' / 'png').glob('*.png'))
    assert list((work / 'out' / 'exports').glob('*.xml'))


def test_unreadable_nuclear_data_file_stops_cleanly(tmp_path):
    work = make_workspace(tmp_path / 'w')
    (work / 'lib' / 'nucl_data' / 'Th-232' / 'Th-232_a.csv').write_text('')
    write_input(work, 'case.yaml', thorium_with())
    run = run_input(work, 'case.yaml')
    assert_stopped(run, ['Th-232_a.csv] could not be loaded correctly'])


#
# Warnings: the run goes on
#
WARNED = {
    'active_datasets': [None, 'nowhere', 'empty_one', 'listy',
                        'active_datasets', 'nothing_named',
                        'nothing_within', 'static_only',
                        'thorium_series_gamma'],
    'empty_one': None,
    'listy': [1, 2],
    'nothing_named': {'scout': {'radionuclides': {'recursive': [],
                                                  'static': []}}},
    'nothing_within': {'scout': {'radionuclides': {
        'recursive': ['Th-232'],
        'cutoffs': {'emission_probability': [99.9, 100]}}}},
    'static_only': {'scout': {'radionuclides': {'recursive': None,
                                                'static': ['Ra-226']}}},
}


@pytest.fixture(scope='module')
def warned(tmp_path_factory, repo_root):
    """One run of WARNED; its last dataset is trial.yaml's
    thorium_series_gamma with the radiation written ' Gamma '."""
    work = make_workspace(tmp_path_factory.mktemp('stops') / 'w')
    trial = yaml.safe_load((repo_root / 'inp' / 'trial.yaml')
                           .read_text(encoding='utf-8'))
    content = dict(WARNED, thorium_series_gamma=trial[
        'thorium_series_gamma'])
    content['thorium_series_gamma']['scout']['radionuclides'][
        'spectrum_radiation'] = ' Gamma '
    write_input(work, 'warned.yaml', content)
    run = run_input(work, 'warned.yaml')
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    return run


def test_warnings_do_not_stop_the_run(warned):
    assert warned.returncode == 0
    assert 'Traceback' not in warned.stderr
    assert not re.search(r'^Terminating\.$', warned.stdout, re.MULTILINE)
    worked = re.findall(r'^Working on \[(.+)\]\.\.\.$', warned.stdout,
                        re.MULTILINE)
    assert worked == ['nothing_named', 'nothing_within', 'static_only',
                      'thorium_series_gamma']


@pytest.mark.parametrize('phrase', [
    'A null element name [None]; skipping.',
    '[nowhere] not in [./inp/warned.yaml]; skipping.',
    'The dataset [empty_one] is empty; skipping.',
    'The dataset [listy] is not a set of settings',
    '[active_datasets] is not allowed as an element name',
    'The radionuclide library of [nothing_named] is empty, as no'
    ' radionuclide has been designated under [recursive] or [static]',
    'The radionuclide library of [nothing_within] is empty, as no data'
    ' point lies within the cutoffs'])
def test_each_skip_is_named(warned, phrase):
    assert phrase in warned.stdout


def test_empty_libraries_are_not_written(warned):
    for dataset in ['nothing_named', 'nothing_within']:
        assert not (warned.figs / f'{dataset}_lib.csv').exists()
        assert not list(warned.figs.glob(f'{dataset}_lib_nrg*'))
        assert not list(warned.exports.glob(f'recurlib_{dataset}_lib_*'))


def test_static_only_dataset(warned):
    """A dataset of static radionuclides alone, with no recursive group,
    holds their lines: Ra-226's, as in the uranium series."""
    static = read_library(warned.figs / 'static_only_lib.csv')
    uranium = read_library(GOLDEN_DIR / 'uranium_series_gamma_lib.csv')
    assert set(static['Radionuclide']) == {'Ra-226'}
    ra = uranium[uranium['Radionuclide'] == 'Ra-226']
    assert (sorted(static['Radiation energy (keV)'])
            == sorted(ra['Radiation energy (keV)']))


def test_radiation_name_ignores_case_and_blanks(warned):
    assert_library_equal(warned.figs / 'thorium_series_gamma_lib.csv',
                         GOLDEN_DIR / 'thorium_series_gamma_lib.csv')
