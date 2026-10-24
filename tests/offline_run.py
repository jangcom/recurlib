"""Run recurlib.py as a script with no network access.

Usage: python offline_run.py <path to recurlib.py> [recurlib.py arguments]

Modes, chosen by the environment:

- Offline (default). Any query means that the nuclear data folder lacks a
  file the run needs, or that the registry of datasets the Live Chart lacks
  does not list it: the query raises OfflineError, which RecurLib does not
  catch, and the run stops.
- Served. If RECURLIB_TEST_SERVE_DIR names a nuclear data folder, every
  query is answered from it as the Live Chart would: the dataset without the
  index column RecurLib adds on saving, or "0" if the folder lacks it.
- Network down or slow. If RECURLIB_TEST_NETWORK is "down", every query
  fails as it does without Internet access (urllib.error.URLError); if it is
  "timeout", as it does when the server does not answer (TimeoutError).

In every mode a query without a timeout raises OfflineError: RecurLib must
never wait for the network without limit.

Every query is appended to the file named by RECURLIB_TEST_REQUEST_LOG, if
set. Importing this module changes nothing; install() does.
"""

import io
import os
import re
import runpy
import socket
import sys
import urllib.error
import urllib.request

LIVECHART = 'https://nds.iaea.org/relnsd/v1/data?'


class OfflineError(RuntimeError):
    """A network access that the offline run cannot answer."""


class Response(io.BytesIO):
    """A minimal HTTP response, enough for RecurLib and pandas."""
    headers = {}


def _log(url):
    path = os.environ.get('RECURLIB_TEST_REQUEST_LOG')
    if path:
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(url + '\n')


def served_file(serve_dir, url):
    """The file of serve_dir that answers url, or None."""
    query = dict(kv.split('=', 1) for kv in url[len(LIVECHART):].split('&'))
    m = re.fullmatch(r'(\d+)([a-z]+)', query['nuclides'])  # e.g. 228ac
    rn = f'{m.group(2).capitalize()}-{m.group(1)}'  # Ac-228
    if query['fields'] == 'decay_rads':
        name = f'{rn}_{query["rad_types"]}.csv'
    else:
        name = f'{rn}_{query["fields"]}.csv'
    path = os.path.join(serve_dir, rn, name)
    return path if os.path.isfile(path) else None


def fake_urlopen(req, *args, **kwargs):
    url = getattr(req, 'full_url', req)
    _log(url)
    if kwargs.get('timeout') is None and len(args) < 2:
        raise OfflineError(f'A query without a timeout: {url}')
    network = os.environ.get('RECURLIB_TEST_NETWORK')
    if network == 'down':
        raise urllib.error.URLError('Network is unreachable')
    if network == 'timeout':
        raise TimeoutError('The read operation timed out')
    serve_dir = os.environ.get('RECURLIB_TEST_SERVE_DIR')
    if serve_dir and url.startswith(LIVECHART):
        path = served_file(serve_dir, url)
        if path is None:
            return Response(b'0\n')
        import pandas as pd
        df = pd.read_csv(path, index_col=0)  # The index RecurLib added
        return Response(df.to_csv(index=False).encode('utf-8'))
    raise OfflineError(f'Network access in an offline run: {url}')


def install():
    """Route RecurLib's queries to fake_urlopen and block other sockets."""
    connect = socket.socket.connect

    def blocked_connect(self, *args, **kwargs):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            raise OfflineError('Socket connection in an offline run')
        return connect(self, *args, **kwargs)

    urllib.request.urlopen = fake_urlopen
    socket.socket.connect = blocked_connect


def main():
    install()
    core = os.path.abspath(sys.argv[1])
    sys.argv = [core] + sys.argv[2:]
    # As for "python recurlib.py": the script's folder comes first on the
    # path, so that its "from modules import ..." finds RecurLib's modules.
    sys.path.insert(0, os.path.dirname(core))
    runpy.run_path(core, run_name='__main__')


if __name__ == '__main__':
    main()
