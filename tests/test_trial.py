"""End-to-end run of the sample input ./inp/trial.yaml, offline: how the run
ends, what it reads and writes, and the messages it prints. Its libraries
are compared with the expected outputs in test_golden.py.
"""

import re

import pytest

from trial_run import DATASETS, FLAG, file_digests


def test_run_finishes(trial):
    assert trial.returncode == 0
    assert re.search(r'^Elapsed real time: \[\d+\.\d s\]$', trial.stdout,
                     re.MULTILINE)
    assert 'Program execution error' not in trial.stdout
    assert 'Traceback' not in trial.stderr


def test_run_needs_no_network(trial):
    """The shipped nuclear data folder and registry cover the sample
    input: no query is made."""
    assert trial.requests == []


def test_run_leaves_nuclear_data_unchanged(trial, repo_root):
    """A run from a complete cache neither adds nor rewrites a file."""
    assert (file_digests(trial.nucl_data)
            == file_digests(repo_root / 'lib' / 'nucl_data'))
    assert (trial.registry.read_text(encoding='utf-8')
            == (repo_root / 'lib' / 'nonexistent_nucl_data.txt')
            .read_text(encoding='utf-8'))


def test_no_deprecation_from_recurlib(trial):
    """Deprecations raised for RecurLib's own calls announce a break in a
    coming release of a library."""
    lines = [ln for ln in trial.stderr.splitlines()
             if re.search(r'(Deprecation|PendingDeprecation|Future)Warning',
                          ln)
             and re.search(r'recurlib\.py|modules[/\\]', ln)]
    assert not lines, '\n'.join(lines)


def test_messages_name_each_dataset_in_order(trial):
    """The lines a graphical interface follows a run by: each dataset,
    then the decay chain of each of its recursive progenitors."""
    steps = re.findall(r'^(Working on|Searching the decay chain of) '
                       r'\[(.+)\]\.\.\.$', trial.stdout, re.MULTILINE)
    expected = []
    for dataset, progenitors in DATASETS.items():
        expected.append(('Working on', dataset))
        expected += [('Searching the decay chain of', p) for p in progenitors]
    assert steps == expected


def test_finished_run_has_no_stop_line(trial):
    assert not re.search(r'^Terminating\.$', trial.stdout, re.MULTILINE)


@pytest.mark.parametrize('dataset', DATASETS)
def test_expected_files_per_dataset(trial, dataset):
    bname = dataset + FLAG
    figs = {f'{bname}.csv', f'{bname}_levels.yaml', f'{bname}_echo.yaml'}
    figs |= {f'{bname}_{p}_lineage.yaml' for p in DATASETS[dataset]}
    for name in figs:
        assert (trial.figs / name).is_file(), name
    assert len(list(trial.figs.glob(f'{bname}_nrg*_rn_*.png'))) == 1
    for tpl in ['gexp_01_master', 'gexp_02_group']:
        assert (trial.exports / f'recurlib_{bname}_{tpl}.xml').is_file()


def test_each_file_is_announced(trial):
    """Every output file is named on a "[<path>] generated." line."""
    announced = re.findall(r'^\[(.+)\] generated\.$', trial.stdout,
                           re.MULTILINE)
    written = sorted(['./figs/' + p.name for p in trial.figs.iterdir()]
                     + ['./exports/' + p.name for p in trial.exports.iterdir()])
    assert sorted(announced) == written
