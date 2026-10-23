"""Initialization files and the template of a user input file.

The settings of a dataset are layered, each over the one before:
(1) the default initialization file, ./inp/ini_recurlib.yaml next to
    recurlib.py, found regardless of the working directory;
(2) a custom initialization file passed with --ini, holding only the
    settings that differ (a complete one of earlier versions also works);
(3) the template key of the user input file;
(4) the dataset.
"""

import re
import subprocess
import sys

import pytest
import yaml

from trial_run import (CORE, FLAG, GOLDEN_DIR, REPO_ROOT, TESTS_DIR,
                       assert_library_equal, make_workspace, read_library,
                       read_yaml, run_input)
from test_stops import assert_stopped, write_input

THORIUM = {'scout': {'radionuclides': {'recursive': ['Th-232']}}}


def trial_subset(work, datasets):
    """./inp/trial.yaml reduced to the given datasets, as ./inp/sub.yaml."""
    trial = yaml.safe_load((work / 'inp' / 'trial.yaml')
                           .read_text(encoding='utf-8'))
    trial['active_datasets'] = list(datasets)
    write_input(work, 'sub.yaml', trial)


def cutoffs(run, dataset):
    """The scout > radionuclides > cutoffs of a dataset, as the run echoed
    them."""
    return read_yaml(run.figs / f'{dataset}{FLAG}_echo.yaml')[
        'scout']['radionuclides']['cutoffs']


def test_default_ini_is_found_next_to_recurlib(tmp_path):
    work = make_workspace(tmp_path / 'w')
    (work / 'inp' / 'ini_recurlib.yaml').unlink()
    trial_subset(work, ['thorium_series_gamma'])
    run = run_input(work, 'sub.yaml')
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    name = f'thorium_series_gamma{FLAG}.csv'
    assert_library_equal(run.figs / name, GOLDEN_DIR / name)


def test_local_ini_of_the_working_directory_is_not_read(tmp_path):
    """Earlier versions read ./inp/ini_recurlib.yaml of the working
    directory; one that differs from the default is now named in a warning
    and left unread."""
    work = make_workspace(tmp_path / 'w')
    local = work / 'inp' / 'ini_recurlib.yaml'
    local.write_text(local.read_text(encoding='utf-8').replace(
        'flag: _lib', 'flag: _local'), encoding='utf-8')
    trial_subset(work, ['thorium_series_gamma'])
    run = run_input(work, 'sub.yaml')
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    assert ('Warning: [./inp/ini_recurlib.yaml] of the working directory is'
            ' not read') in run.stdout
    assert (run.figs / f'thorium_series_gamma{FLAG}.csv').is_file()
    assert not list(run.figs.glob('*_local*'))


def test_partial_custom_ini(tmp_path):
    """A custom initialization file holding one setting changes that
    setting only."""
    work = make_workspace(tmp_path / 'w')
    write_input(work, 'custom.yaml', {'template': {'io': {'out': {'flag': '_x'}}}})
    trial_subset(work, ['thorium_series_gamma'])
    run = run_input(work, 'sub.yaml', args=['--ini=./inp/custom.yaml'])
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    assert_library_equal(run.figs / 'thorium_series_gamma_x.csv',
                         GOLDEN_DIR / f'thorium_series_gamma{FLAG}.csv')
    assert not list(run.figs.glob(f'*{FLAG}*'))


def test_complete_ini_of_earlier_versions(tmp_path):
    """The initialization file of RecurLib 1.0.0, given with --ini, gives
    the same libraries: the settings added since come from the default."""
    work = make_workspace(tmp_path / 'w',
                          inputs=[TESTS_DIR / 'inp' /
                                  'ini_recurlib_v1.0.0.yaml'])
    trial_subset(work, ['thorium_series_alpha', 'uranium_series_gamma'])
    run = run_input(work, 'sub.yaml',
                    args=['--ini=./inp/ini_recurlib_v1.0.0.yaml'])
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    for dataset in ['thorium_series_alpha', 'uranium_series_gamma']:
        name = f'{dataset}{FLAG}.csv'
        assert_library_equal(run.figs / name, GOLDEN_DIR / name)


def test_layers_override_in_order(tmp_path):
    """Default < --ini < template of the user input file < dataset."""
    work = make_workspace(tmp_path / 'w')
    write_input(work, 'custom.yaml', {'template': {'scout': {'radionuclides': {
        'cutoffs': {'emission_probability': [1e-2, 1e3],
                    'priority_number_max': 2}}}}})
    write_input(work, 'layers.yaml', {
        'template': {'scout': {'radionuclides': {
            'cutoffs': {'energy': [0, 2e3], 'priority_number_max': 4}}}},
        'active_datasets': ['own', 'shared'],
        'own': {'scout': {'radionuclides': {
            'recursive': ['Th-232'],
            'cutoffs': {'emission_probability': [1, 1e3],
                        'priority_number_max': 3}}}},
        'shared': THORIUM,
    })
    run = run_input(work, 'layers.yaml', args=['--ini=./inp/custom.yaml'])
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    own, shared = cutoffs(run, 'own'), cutoffs(run, 'shared')
    assert own['emission_probability'] == [1, 1e3]  # The dataset
    assert shared['emission_probability'] == [1e-2, 1e3]  # --ini
    assert own['energy'] == shared['energy'] == [0, 2e3]  # The template
    assert own['priority_number_max'] == 3  # The dataset over the template
    assert shared['priority_number_max'] == 4  # The template over --ini
    assert own['half_life_sec'] == [0.0, '1.433e99']  # The default


def test_template_lists_are_not_shared_between_datasets(tmp_path):
    """RecurLib rewrites the radionuclide lists of a dataset in place
    (Pa-234m;73.92 -> Pa-234); each dataset needs its own copy of the
    template, or the second one would lose the isomer level."""
    work = make_workspace(tmp_path / 'w')
    write_input(work, 'shared.yaml', {
        'template': {'scout': {'radionuclides': {
            'recursive': [], 'static': ['Pa-234m;73.92']}}},
        'active_datasets': ['first', 'second'],
        'first': {'plot': {'title': {'label': 'First'}}},
        'second': {'plot': {'title': {'label': 'Second'}}},
    })
    run = run_input(work, 'shared.yaml')
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    first = read_library(run.figs / f'first{FLAG}.csv')
    second = read_library(run.figs / f'second{FLAG}.csv')
    assert 'Pa-234m' in set(first['Radionuclide'])
    assert first.equals(second)


def test_reserved_and_repeated_dataset_names(tmp_path):
    work = make_workspace(tmp_path / 'w')
    write_input(work, 'names.yaml', {
        'template': {'scout': {'radionuclides': {'recursive': ['Th-232']}}},
        'active_datasets': ['template', 'Template', 'thorium', 'thorium'],
        'Template': THORIUM,
        'thorium': {'plot': {'title': {'label': 'Thorium'}}},
    })
    run = run_input(work, 'names.yaml')
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    assert run.stdout.count('Warning: [template] is not allowed as an'
                            ' element name under [active_datasets]') == 2
    assert ('Warning: [thorium] is listed more than once under'
            ' [active_datasets]; skipping.') in run.stdout
    assert re.findall(r'^Working on \[(.+)\]\.\.\.$', run.stdout,
                      re.MULTILINE) == ['thorium']


@pytest.mark.parametrize('custom', ['# Nothing to change\n', 'template:\n',
                                    'template: {}\n'])
def test_custom_ini_without_settings_keeps_the_defaults(tmp_path, custom):
    work = make_workspace(tmp_path / 'w')
    write_input(work, 'empty.yaml', custom)
    trial_subset(work, ['thorium_series_gamma'])
    run = run_input(work, 'sub.yaml', args=['--ini=./inp/empty.yaml'])
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    name = f'thorium_series_gamma{FLAG}.csv'
    assert_library_equal(run.figs / name, GOLDEN_DIR / name)


def test_custom_ini_settings_outside_template_are_named(tmp_path):
    """A setting written without the template key above it is not read;
    the run says so."""
    work = make_workspace(tmp_path / 'w')
    write_input(work, 'custom.yaml', {'io': {'out': {'flag': '_x'}}})
    trial_subset(work, ['thorium_series_gamma'])
    run = run_input(work, 'sub.yaml', args=['--ini=./inp/custom.yaml'])
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    assert ('Warning: [io] of the custom initialization file'
            ' [./inp/custom.yaml] is not under [template]; ignored.') \
        in run.stdout
    assert (run.figs / f'thorium_series_gamma{FLAG}.csv').is_file()


@pytest.mark.parametrize('template', [None, {}])
def test_template_without_settings_changes_nothing(tmp_path, template):
    work = make_workspace(tmp_path / 'w')
    trial = yaml.safe_load((work / 'inp' / 'trial.yaml')
                           .read_text(encoding='utf-8'))
    trial['active_datasets'] = ['thorium_series_gamma']
    trial['template'] = template
    write_input(work, 'sub.yaml', trial)
    run = run_input(work, 'sub.yaml')
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    name = f'thorium_series_gamma{FLAG}.csv'
    assert_library_equal(run.figs / name, GOLDEN_DIR / name)


STOPS = {
    'template not a mapping': (
        None, {'template': ['Th-232'], 'active_datasets': ['t'],
               't': THORIUM},
        ['[template] must be a set of settings (key: value pairs).']),
    'template key without a value': (
        None, {'template': {'io': None}, 'active_datasets': ['t'],
               't': THORIUM},
        ['[template] cannot be merged', '[io] has no value.']),
    'template mapping over a list': (
        None, {'template': {'scout': {'radionuclides': {'cutoffs': {
            'energy': {'lo': 0}}}}}, 'active_datasets': ['t'],
            't': THORIUM},
        ['[scout > radionuclides > cutoffs > energy] must not be a set'
         ' of settings']),
    'dataset key without a value': (
        None, {'active_datasets': ['t'],
               't': dict(THORIUM, plot=None)},
        ['[t] cannot be merged', '[plot] has no value.']),
    'dataset list over a mapping': (
        None, {'active_datasets': ['t'],
               't': dict(THORIUM, io=['csv'])},
        ['[io] must be a set of settings (key: value pairs).']),
    'custom ini not a mapping': (
        ['Th-232'], {'active_datasets': ['t'], 't': THORIUM},
        ['must hold its settings under the [template] key.']),
    'custom ini key without a value': (
        {'template': {'plot': None}},
        {'active_datasets': ['t'], 't': THORIUM},
        ['cannot be merged over the default one', '[plot] has no value.']),
}


@pytest.mark.parametrize('case', STOPS)
def test_unmergeable_settings_stop_cleanly(tmp_path, case):
    ini, user, phrases = STOPS[case]
    work = make_workspace(tmp_path / 'w')
    write_input(work, 'case.yaml', user)
    args = []
    if ini is not None:
        write_input(work, 'custom.yaml', ini)
        args = ['--ini=./inp/custom.yaml']
    run = run_input(work, 'case.yaml', args=args)
    assert_stopped(run, phrases)


def test_show_ini_prints_the_default_path():
    proc = subprocess.run([sys.executable, str(CORE), '--show-ini'],
                          capture_output=True, text=True, encoding='utf-8',
                          stdin=subprocess.DEVNULL)
    assert proc.returncode == 0
    assert proc.stdout.strip() == str((REPO_ROOT / 'inp'
                                       / 'ini_recurlib.yaml').resolve())


def test_read_argv_as_miri_calls_it(monkeypatch):
    """Without is_show_ini, the file argument stays required, as for the
    downstream program MIRI, which calls read_argv with keywords only."""
    sys.path.insert(0, str(REPO_ROOT))
    from modules import inpout
    io = inpout.InpOut()
    monkeypatch.setattr(sys, 'argv', ['miri.py', 'f.yaml'])
    args = io.read_argv(desc='', ini_dflt='./inp/ini_miri.yaml')
    assert (args.file, args.ini, args.is_echo) == ('f.yaml',
                                                   './inp/ini_miri.yaml',
                                                   False)
    assert not hasattr(args, 'is_show_ini')
    monkeypatch.setattr(sys, 'argv', ['miri.py'])
    with pytest.raises(SystemExit) as e:
        io.read_argv(desc='', ini_dflt='./inp/ini_miri.yaml')
    assert e.value.code == 2
    monkeypatch.setattr(sys, 'argv', ['recurlib.py'])
    with pytest.raises(SystemExit) as e:
        io.read_argv(desc='', ini_dflt='x.yaml', is_show_ini=True)
    assert e.value.code == 2


def test_get_exes_tries_an_old_exe_first(monkeypatch):
    """A program path written as 'exe' (earlier versions) survives a merge
    with the default 'exes' list, and is tried first."""
    sys.path.insert(0, str(REPO_ROOT))
    from modules import painter
    creator = painter.Painter()
    monkeypatch.setenv('RECURLIB_TEST_DIR', '/opt')
    assert creator.get_exes({'exe': '$RECURLIB_TEST_DIR/gs',
                             'exes': ['/usr/bin/gs']}) == ['/opt/gs',
                                                           '/usr/bin/gs']
    assert creator.get_exes({'exes': ['a', 'b']}) == ['a', 'b']
    assert creator.get_exes({}) == []
