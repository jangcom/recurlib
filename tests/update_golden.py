"""Rewrite the expected outputs under ./tests/golden.

Run this only after a deliberate change to the libraries RecurLib writes,
and review the differences with "git diff tests/golden" before committing:

    python tests/update_golden.py
"""

import shutil
import sys
import tempfile

from trial_run import (DATASETS, EXTRA_DATASETS, GOLDEN_DIR, output_names,
                       run_extra, run_trial)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        runs = [(run_trial(f'{tmp}/trial'), DATASETS),
                (run_extra(f'{tmp}/extra'), EXTRA_DATASETS)]
        for run, _ in runs:
            if not run.ok:
                sys.stderr.write(run.stdout[-3000:] + run.stderr[-3000:])
                sys.exit('A run failed; ./tests/golden is unchanged.')
        GOLDEN_DIR.mkdir(exist_ok=True)
        for old in GOLDEN_DIR.iterdir():
            if not old.name.startswith('.'):
                old.unlink()
        for run, datasets in runs:
            for dataset in datasets:
                for name in output_names(dataset):
                    shutil.copy2(run.figs / name, GOLDEN_DIR / name)
                    print(f'[tests/golden/{name}] generated.')


if __name__ == '__main__':
    main()
