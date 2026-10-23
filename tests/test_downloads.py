"""Downloads and the registry of datasets the Live Chart lacks, with the Live
Chart of Nuclides played by the shipped nuclear data folder (see the served
mode of offline_run.py).
"""

import collections
import re
import shutil

import pandas as pd
import pytest
import yaml

from offline_run import LIVECHART
from test_libraries import PUBLISHED_LINEAGES, nodes
from trial_run import (FLAG, GOLDEN_DIR, REPO_ROOT, assert_library_equal,
                       make_workspace, run_input)

DATASET = 'thorium_series_gamma'
SHIPPED = REPO_ROOT / 'lib' / 'nucl_data'
REGISTRY = REPO_ROOT / 'lib' / 'nonexistent_nucl_data.txt'
RAD_TYPES = ['a', 'bp', 'bm', 'e', 'g', 'x']


def one_dataset_workspace(path):
    """A workspace whose ./inp/one.yaml holds only DATASET of trial.yaml."""
    work = make_workspace(path)
    trial = yaml.safe_load((work / 'inp' / 'trial.yaml')
                           .read_text(encoding='utf-8'))
    trial['active_datasets'] = [DATASET]
    (work / 'inp' / 'one.yaml').write_text(
        yaml.safe_dump(trial, sort_keys=False), encoding='utf-8')
    return work


def read_cached(path):
    return pd.read_csv(path, index_col=0, keep_default_na=False,
                       na_values=[''])


@pytest.fixture(scope='module')
def redownload(tmp_path_factory):
    """DATASET run after removing three nuclides from the nuclear data
    folder; the served Live Chart has them."""
    work = one_dataset_workspace(tmp_path_factory.mktemp('downloads') / 'w')
    removed = ['Pb-212', 'Bi-212', 'Tl-208']
    for rn in removed:
        shutil.rmtree(work / 'lib' / 'nucl_data' / rn)
    run = run_input(work, 'one.yaml', serve_dir=SHIPPED)
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    return run, removed


def test_removed_datasets_are_downloaded_again(redownload):
    run, removed = redownload
    for rn in removed:
        shipped = sorted(p.name for p in (SHIPPED / rn).glob('*.csv'))
        again = sorted(p.name for p in (run.nucl_data / rn).glob('*.csv'))
        assert again == shipped, rn
        for name in shipped:
            pd.testing.assert_frame_equal(
                read_cached(run.nucl_data / rn / name),
                read_cached(SHIPPED / rn / name),
                check_exact=False, rtol=1e-12, atol=0)


def test_downloaded_data_give_the_same_library(redownload):
    run, _ = redownload
    name = f'{DATASET}{FLAG}.csv'
    assert_library_equal(run.figs / name, GOLDEN_DIR / name)
    assert (run.registry.read_text(encoding='utf-8')
            == REGISTRY.read_text(encoding='utf-8'))


def test_downloads_leave_no_temporary_file(redownload):
    run, _ = redownload
    assert not list(run.work_dir.rglob('*.tmp'))


def test_only_the_removed_nuclides_are_asked_for(redownload):
    run, removed = redownload
    asked = {re.search(r'nuclides=(\d+)([a-z]+)', url).groups()
             for url in run.requests}
    assert {f'{sym.capitalize()}-{a}' for a, sym in asked} == set(removed)


def test_each_dataset_is_downloaded_once(redownload):
    run, _ = redownload
    counts = collections.Counter(run.requests)
    assert max(counts.values()) == 1, counts.most_common(3)


def test_registry_is_rebuilt_from_scratch(tmp_path):
    """Without a registry, a run asks for every nuclide-radiation pair
    of the chain that the nuclear data folder lacks, and records each
    "no dataset" answer: sorted, once each."""
    work = one_dataset_workspace(tmp_path / 'w')
    (work / 'lib' / 'nonexistent_nucl_data.txt').unlink()
    run = run_input(work, 'one.yaml', serve_dir=SHIPPED)
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]

    members = nodes(PUBLISHED_LINEAGES['Th-232'])
    lacking = {f'{rn}_{rt}' for rn in members
               for rt in RAD_TYPES + ['gammas', 'levels']
               if not (SHIPPED / rn / f'{rn}_{rt}.csv').is_file()}
    rebuilt = run.registry.read_text(encoding='utf-8').splitlines()
    assert rebuilt == sorted(set(rebuilt))
    assert set(rebuilt) == lacking
    shipped = REGISTRY.read_text(encoding='utf-8').splitlines()
    assert set(rebuilt) == {p for p in shipped
                            if p.rsplit('_', 1)[0] in members}
    for pair in lacking:
        rn, rt = pair.rsplit('_', 1)
        m = re.match(r'([A-Z][a-z]?)-(\d+)$', rn)
        lc = f'{m.group(2)}{m.group(1).lower()}'
        url = (f'{LIVECHART}fields={rt}&nuclides={lc}'
               if rt in ('gammas', 'levels') else
               f'{LIVECHART}fields=decay_rads&nuclides={lc}&rad_types={rt}')
        assert url in run.requests, pair


def test_missing_gamma_cascades_are_registered(tmp_path):
    """The Live Chart has no gamma cascades of Rn-221 (neptunium series).
    Without that line in the registry, a run asks once and records the
    answer; the next run asks nothing."""
    work = make_workspace(tmp_path / 'w')
    registry = work / 'lib' / 'nonexistent_nucl_data.txt'
    lines = registry.read_text(encoding='utf-8').splitlines()
    assert 'Rn-221_gammas' in lines
    registry.write_text(''.join(f'{x}\n' for x in lines
                                if x != 'Rn-221_gammas'), encoding='utf-8')
    trial = yaml.safe_load((work / 'inp' / 'trial.yaml')
                           .read_text(encoding='utf-8'))
    trial['active_datasets'] = ['neptunium_series_alpha']
    (work / 'inp' / 'np.yaml').write_text(
        yaml.safe_dump(trial, sort_keys=False), encoding='utf-8')
    first = run_input(work, 'np.yaml', serve_dir=SHIPPED)
    assert first.ok, first.stdout[-3000:] + first.stderr[-3000:]
    assert first.requests == [f'{LIVECHART}fields=gammas&nuclides=221rn']
    assert (registry.read_text(encoding='utf-8')
            == REGISTRY.read_text(encoding='utf-8'))
    second = run_input(work, 'np.yaml')  # Offline: any query fails
    assert second.ok, second.stdout[-3000:] + second.stderr[-3000:]
    assert second.requests == []


def test_registry_lines_match_exactly(tmp_path):
    """The registry line Rn-221_gammas (no gamma cascades) must not hide the
    gamma rays of Rn-221 (Rn-221_g): with Rn-221_g.csv removed from the
    nuclear data folder, the run downloads it again and the library is the
    same."""
    work = make_workspace(tmp_path / 'w')
    (work / 'lib' / 'nucl_data' / 'Rn-221' / 'Rn-221_g.csv').unlink()
    trial = yaml.safe_load((work / 'inp' / 'trial.yaml')
                           .read_text(encoding='utf-8'))
    trial['active_datasets'] = ['neptunium_series_gamma']
    (work / 'inp' / 'np.yaml').write_text(
        yaml.safe_dump(trial, sort_keys=False), encoding='utf-8')
    run = run_input(work, 'np.yaml', serve_dir=SHIPPED)
    assert run.ok, run.stdout[-3000:] + run.stderr[-3000:]
    assert run.requests == [f'{LIVECHART}fields=decay_rads&nuclides=221rn'
                            '&rad_types=g']
    name = f'neptunium_series_gamma{FLAG}.csv'
    assert_library_equal(run.figs / name, GOLDEN_DIR / name)
