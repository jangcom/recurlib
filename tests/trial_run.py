"""Run RecurLib offline in a scratch folder, and compare its outputs with the
expected ones under ./tests/golden.

Used by conftest.py, update_golden.py and the tests.
"""

import hashlib
import math
import os
import pathlib
import shutil
import subprocess
import sys
from dataclasses import dataclass

import pandas as pd
import yaml

TESTS_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
GOLDEN_DIR = TESTS_DIR / 'golden'
CORE = REPO_ROOT / 'recurlib.py'
LAUNCHER = TESTS_DIR / 'offline_run.py'

# The datasets of ./inp/trial.yaml and their recursive progenitors
DATASETS = {
    'thorium_series_alpha': ['Th-232'],
    'thorium_series_gamma': ['Th-232'],
    'neptunium_series_alpha': ['Np-237'],
    'neptunium_series_gamma': ['Np-237'],
    'uranium_series_alpha': ['U-238'],
    'uranium_series_gamma': ['U-238'],
    'actinium_series_alpha': ['U-235'],
    'actinium_series_gamma': ['U-235'],
}
# The datasets of ./tests/inp/extra.yaml, a test-only input for settings
# that ./inp/trial.yaml does not use
EXTRA_DATASETS = {
    'tight_cutoffs': ['Th-232'],
    'beta_minus': ['Th-232'],
    'static_and_isomer': ['Th-232'],
    'mixture_gamma': ['U-238', 'U-235', 'Th-232'],
    'xray_key_lines': ['Th-232'],
}
EXTRA_INPUT = TESTS_DIR / 'inp' / 'extra.yaml'
ALL_DATASETS = {**DATASETS, **EXTRA_DATASETS}
# The session fixture (conftest.py) whose run holds each dataset
FIXTURE = {**{ds: 'trial' for ds in DATASETS},
           **{ds: 'extra' for ds in EXTRA_DATASETS}}
FLAG = '_lib'  # io > out > flag of the shipped initialization file


@dataclass
class Run:
    """The scratch folder of a run and what the run printed."""
    work_dir: pathlib.Path
    returncode: int
    stdout: str
    stderr: str
    requests: list

    @property
    def figs(self):
        return self.work_dir / 'figs'

    @property
    def exports(self):
        return self.work_dir / 'exports'

    @property
    def nucl_data(self):
        return self.work_dir / 'lib' / 'nucl_data'

    @property
    def registry(self):
        return self.work_dir / 'lib' / 'nonexistent_nucl_data.txt'

    @property
    def ok(self):
        return (self.returncode == 0
                and 'Elapsed real time: [' in self.stdout)


def make_workspace(work_dir, inputs=()):
    """Copy what a run reads into work_dir, as the repository lays it out.

    The nuclear data folder and the registry are copies, so that a run
    cannot change the repository's. inputs: further input files to copy
    into ./inp next to ./inp/trial.yaml.
    """
    work_dir = pathlib.Path(work_dir).resolve()
    shutil.copytree(REPO_ROOT / 'lib', work_dir / 'lib')
    (work_dir / 'inp').mkdir()
    for path in [REPO_ROOT / 'inp' / 'ini_recurlib.yaml',
                 REPO_ROOT / 'inp' / 'trial.yaml', *inputs]:
        shutil.copy2(path, work_dir / 'inp' / pathlib.Path(path).name)
    # In the shipped layout the figures go to the report folder, which
    # RecurLib creates; creating both here keeps "[./figs] generated." and
    # "[./exports] generated." out of the messages.
    (work_dir / 'figs').mkdir()
    (work_dir / 'exports').mkdir()
    return work_dir


def run_input(work_dir, input_name, serve_dir=None, network=None,
              timeout=1800):
    """Run "python recurlib.py ./inp/<input_name>" in a workspace made by
    make_workspace(), offline, served from serve_dir, or with the network
    'down' or answering with a 'timeout' (see offline_run)."""
    work_dir = pathlib.Path(work_dir).resolve()
    request_log = work_dir / 'requests.log'
    env = dict(os.environ)
    env.update({
        'MPLBACKEND': 'Agg',
        'PYTHONIOENCODING': 'utf-8',
        'RECURLIB_TEST_REQUEST_LOG': str(request_log),
    })
    env.pop('RECURLIB_TEST_SERVE_DIR', None)
    env.pop('RECURLIB_TEST_NETWORK', None)
    if serve_dir:
        env['RECURLIB_TEST_SERVE_DIR'] = str(serve_dir)
    if network:
        env['RECURLIB_TEST_NETWORK'] = network
    # -W default: show every warning once on stderr, where the tests look
    # for deprecations raised by RecurLib's own calls.
    proc = subprocess.run(
        [sys.executable, '-W', 'default', str(LAUNCHER), str(CORE),
         f'./inp/{input_name}'],
        cwd=work_dir, env=env, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=timeout)
    requests = (request_log.read_text(encoding='utf-8').splitlines()
                if request_log.exists() else [])
    request_log.unlink(missing_ok=True)
    return Run(work_dir, proc.returncode, proc.stdout, proc.stderr, requests)


def run_trial(work_dir):
    """Run "python recurlib.py ./inp/trial.yaml" offline in work_dir."""
    return run_input(make_workspace(work_dir), 'trial.yaml')


def run_extra(work_dir):
    """Run the test-only input ./tests/inp/extra.yaml offline in work_dir."""
    return run_input(make_workspace(work_dir, inputs=[EXTRA_INPUT]),
                     EXTRA_INPUT.name)


def file_digests(folder):
    """{relative path: SHA-256} of the files under folder."""
    folder = pathlib.Path(folder)
    return {p.relative_to(folder).as_posix():
            hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*')
            if p.is_file() and not p.name.startswith('.')}


def output_names(dataset):
    """The base names of the files compared with ./tests/golden."""
    bname = dataset + FLAG
    names = [f'{bname}.csv', f'{bname}_levels.yaml']
    names += [f'{bname}_{prog}_lineage.yaml'
              for prog in ALL_DATASETS[dataset]]
    return names


#
# Comparisons
#
def read_library(path):
    """A library as written: empty fields are NaN, any other text is kept."""
    return pd.read_csv(path, keep_default_na=False, na_values=[''])


def assert_library_equal(actual_csv, expected_csv):
    """Same columns, rows, texts and types; numbers equal to 12 significant
    digits.

    The tolerance absorbs the last-digit differences that float parsing and
    formatting show across versions of pandas.
    """
    actual = read_library(actual_csv)
    expected = read_library(expected_csv)
    pd.testing.assert_frame_equal(actual, expected, check_exact=False,
                                  rtol=1e-12, atol=0)


def read_yaml(path):
    with open(path, encoding='utf-8') as fh:
        return yaml.safe_load(fh)


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _number(x):
    return 'nan' if math.isnan(x) else float(f'{x:.9g}')


# Lists of energy levels that RecurLib uses as sets (membership only)
SET_KEYS = {'energy_levels', 'energy_levels_flattened',
            'energy_levels_isomer', 'feasible_energies'}


def canonical_levels(node, key=None):
    """A form of a levels file that ignores the order of the energy levels
    that RecurLib uses as sets.

    Such lists become their sorted values (to 9 significant digits) plus
    the count of NaN entries. Their order, notably that of NaN entries among
    the levels reached by gamma cascades, varies between versions of pandas
    and NumPy: RecurLib collects the levels with a new NaN per missing
    value, and sorting a list that holds NaN depends on where they fall.
    Every other list keeps its order, e.g. the [lower, upper] limits of a
    level.
    """
    if isinstance(node, dict):
        return {k: canonical_levels(v, k) for k, v in node.items()}
    if isinstance(node, list):
        if key in SET_KEYS and node and all(_is_number(x) for x in node):
            nans = sum(1 for x in node if math.isnan(x))
            values = sorted(_number(x) for x in node if not math.isnan(x))
            return {'numbers': values, 'nan_count': nans}
        return [canonical_levels(x) for x in node]
    if _is_number(node):
        return _number(node)
    return node
