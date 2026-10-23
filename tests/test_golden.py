"""The libraries, lineages and energy levels of ./inp/trial.yaml and
./tests/inp/extra.yaml compared with the expected outputs under
./tests/golden. After a deliberate change to them, rewrite those with
tests/update_golden.py and review the differences.
"""

import pytest

from trial_run import (ALL_DATASETS, FIXTURE, FLAG, GOLDEN_DIR,
                       assert_library_equal, canonical_levels, output_names,
                       read_yaml)


@pytest.fixture(params=list(ALL_DATASETS))
def case(request):
    """(dataset, run) for each dataset of the two inputs."""
    return request.param, request.getfixturevalue(FIXTURE[request.param])


def test_library_matches_golden(case):
    dataset, run = case
    name = f'{dataset}{FLAG}.csv'
    assert_library_equal(run.figs / name, GOLDEN_DIR / name)


def test_lineages_match_golden(case):
    dataset, run = case
    for prog in ALL_DATASETS[dataset]:
        name = f'{dataset}{FLAG}_{prog}_lineage.yaml'
        assert read_yaml(run.figs / name) == read_yaml(GOLDEN_DIR / name)


def test_levels_match_golden(case):
    dataset, run = case
    name = f'{dataset}{FLAG}_levels.yaml'
    assert (canonical_levels(read_yaml(run.figs / name))
            == canonical_levels(read_yaml(GOLDEN_DIR / name)))


def test_golden_is_complete():
    expected = {n for ds in ALL_DATASETS for n in output_names(ds)}
    assert {p.name for p in GOLDEN_DIR.iterdir()
            if not p.name.startswith('.')} == expected
