"""Shared fixtures: run ./inp/trial.yaml and the test-only input
./tests/inp/extra.yaml once each, offline, in scratch folders.

The two runs take about a minute and a half; every test of the session
reads their outputs.
"""

import pytest

from trial_run import REPO_ROOT, run_extra, run_trial


def _checked(run, name):
    if not run.ok:
        pytest.fail(f'The {name} run failed:\n' + run.stdout[-3000:]
                    + run.stderr[-3000:], pytrace=False)
    return run


@pytest.fixture(scope='session')
def repo_root():
    return REPO_ROOT


@pytest.fixture(scope='session')
def trial(tmp_path_factory):
    """The scratch folder and printed output of the offline trial run."""
    return _checked(run_trial(tmp_path_factory.mktemp('recurlib') / 'trial'),
                    'trial')


@pytest.fixture(scope='session')
def extra(tmp_path_factory):
    """The scratch folder and printed output of the offline run of
    ./tests/inp/extra.yaml."""
    return _checked(run_extra(tmp_path_factory.mktemp('recurlib') / 'extra'),
                    'extra')
