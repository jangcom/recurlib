"""Time RecurLib on the datasets of ./inp/trial.yaml, offline.

Each dataset runs on its own, repeatedly, in a scratch copy of the nuclear
data folder, through the offline launcher of the tests (no network access).
The times are those RecurLib prints ("Elapsed real time"), as mean and
sample standard deviation:

    python dev/benchmark.py [--repeat N] [dataset ...]
"""

import argparse
import os
import pathlib
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tempfile

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
LAUNCHER = REPO_ROOT / 'tests' / 'offline_run.py'
CORE = REPO_ROOT / 'recurlib.py'


def main():
    trial = yaml.safe_load((REPO_ROOT / 'inp' / 'trial.yaml')
                           .read_text(encoding='utf-8'))
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('datasets', nargs='*',
                        default=trial['active_datasets'])
    parser.add_argument('--repeat', type=int, default=4)
    args = parser.parse_args()

    print(f'Python {platform.python_version()}, {platform.platform()}, '
          f'{platform.processor() or platform.machine()}')
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        shutil.copytree(REPO_ROOT / 'lib', work / 'lib')
        (work / 'inp').mkdir()
        shutil.copy2(REPO_ROOT / 'inp' / 'ini_recurlib.yaml', work / 'inp')
        (work / 'figs').mkdir()
        (work / 'exports').mkdir()
        for ds in args.datasets:
            one = dict(trial, active_datasets=[ds])
            inp = work / 'inp' / f'{ds}.yaml'
            inp.write_text(yaml.safe_dump(one, sort_keys=False),
                           encoding='utf-8')
            times = []
            for _ in range(args.repeat):
                proc = subprocess.run(
                    [sys.executable, str(LAUNCHER), str(CORE),
                     f'./inp/{ds}.yaml'],
                    cwd=work, stdin=subprocess.DEVNULL, capture_output=True,
                    text=True, encoding='utf-8',
                    env={**os.environ, 'MPLBACKEND': 'Agg'})
                m = re.search(r'Elapsed real time: \[(\d+\.\d) s\]',
                              proc.stdout)
                if proc.returncode or not m:
                    sys.exit(f'{ds} failed:\n{proc.stdout[-2000:]}'
                             f'{proc.stderr[-2000:]}')
                times.append(float(m.group(1)))
            sd = statistics.stdev(times) if len(times) > 1 else 0.0
            print(f'{ds:24s} {statistics.mean(times):6.1f} +/- {sd:4.1f} s '
                  f'(n = {len(times)})')


if __name__ == '__main__':
    main()
