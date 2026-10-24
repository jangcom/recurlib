"""RecurLib imported as a module, the way MIRI uses it.

MIRI keeps copies of recurlib.py and ./modules/*.py in a package named
"modules" and calls Recurlib(), set_radiat(), set_cols(), get_rnlib() and
get_context(); recurlib.py binds its helper modules for exactly that import
name. These calls must keep working and give the library the CLI writes.
"""

import json
import os
import shutil
import subprocess
import sys

from trial_run import (GOLDEN_DIR, REPO_ROOT, TESTS_DIR,
                       assert_library_equal, make_workspace)

DATASET = 'thorium_series_gamma'

CHILD = r'''
import copy, json, sys
sys.path.insert(0, sys.argv[1])  # the folder holding the package "modules"
sys.path.insert(1, sys.argv[2])  # ./tests, for the offline launcher
import offline_run
offline_run.install()  # No network from here on
from modules import mytoolkit as mt
from modules import inpout
from modules import recurlib

io = inpout.InpOut()
ini = io.read_yaml('./inp/ini_recurlib.yaml')
yml = io.read_yaml('./inp/trial.yaml')
ds = sys.argv[3]
a = mt.merge(copy.deepcopy(ini['template']), yml[ds])
# The output names as MIRI sets them before calling get_rnlib()
for key in ['lineage_bname', 'lev_bname', 'echo_bname']:
    a['io']['out'][key] = ds
a['io']['out']['export_bname'] = 'recurlib_' + ds
for key in ['rpt_bname', 'fig_bname']:
    a['io']['out'][key] = ds + a['io']['out']['flag']

rcl = recurlib.Recurlib()
rcl.set_radiat(a['scout']['radionuclides']['spectrum_radiation'])
rcl.set_cols(a['io']['cols'])
df = rcl.get_rnlib(a)
df.to_csv('api_library.csv')
context = rcl.get_context(ds, df, is_verbose=False)
with open('api_context.json', 'w', encoding='utf-8') as fh:
    json.dump({'rnlib_info': context['rnlib_info'],
               'nuclides': list(context['rns']),
               'radiations': sum(len(v['radiats'])
                                 for v in context['rns'].values())},
              fh, default=str)
'''


def test_miri_style_import_gives_the_cli_library(tmp_path):
    work = make_workspace(tmp_path / 'work')
    package = tmp_path / 'pkg' / 'modules'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text('', encoding='utf-8')
    shutil.copy2(REPO_ROOT / 'recurlib.py', package)
    for py in (REPO_ROOT / 'modules').glob('*.py'):
        shutil.copy2(py, package)

    env = dict(os.environ, MPLBACKEND='Agg', PYTHONIOENCODING='utf-8')
    proc = subprocess.run(
        [sys.executable, '-c', CHILD, str(tmp_path / 'pkg'), str(TESTS_DIR),
         DATASET],
        cwd=work, env=env, stdin=subprocess.DEVNULL, capture_output=True,
        text=True, encoding='utf-8', timeout=900)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]

    assert_library_equal(work / 'api_library.csv',
                         GOLDEN_DIR / f'{DATASET}_lib.csv')
    with open(work / 'api_context.json', encoding='utf-8') as fh:
        context = json.load(fh)
    import pandas as pd
    golden = pd.read_csv(GOLDEN_DIR / f'{DATASET}_lib.csv')
    assert context['nuclides'] == list(golden['Radionuclide'].unique())
    assert context['radiations'] == len(golden)
    assert len(context['rnlib_info']['code_master']) <= 28 + len('-mst')
    # get_rnlib() wrote the lineage under MIRI's name, without the flag
    assert (work / 'figs' / f'{DATASET}_Th-232_lineage.yaml').is_file()
