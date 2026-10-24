# Changelog

All notable changes to RecurLib are documented in this file, newest first.

## v1.1.0 (2026-10-23)

User input files written for v1.0.x work unchanged; see "Changed" for the settings whose defaults have changed, the exit status, and the registry file.

### Added

- A `template` key of the user input file: the settings shared by every dataset of the file, merged over the initialization file and under each dataset. `template` and `active_datasets` are not allowed as dataset names.
- `--ini` now takes a custom initialization file holding only the settings that differ from the default ones, deeply merged over the default `./inp/ini_recurlib.yaml`; a complete initialization file of earlier versions also works. `--show-ini` prints the path of the default initialization file.
- `scout > radionuclides > cutoffs > priority_number_xrays` (default `False`): whether X-rays can be flagged as priority radiation data points (key lines).
- A line `Searching the decay chain of [<progenitor>]...` before each decay chain search, for the progress of a run to be followed.
- A test suite under `tests/`, run offline using the shipped nuclear data files (see TESTS in the README), and a GitHub Actions workflow running it on Linux, macOS, and Windows.
- `dev/benchmark.py`, which times the datasets of `./inp/trial.yaml`.

### Changed

- Every deliberate stop of RecurLib ends with the line `Terminating.` and the exit status 1; a run completing every active dataset exits with 0. A dataset that cannot be processed (not defined, empty, repeated, or named by a reserved word) and a radionuclide library left without data points are skipped with a warning.
- The default initialization file is read from the `inp` directory next to `recurlib.py` regardless of the working directory. `./inp/ini_recurlib.yaml` of the working directory is no longer read; a run names such a file if it differs from the default one.
- X-rays are no longer flagged as priority radiation data points unless `priority_number_xrays` is `True`: they are emitted from the atomic shells of daughters, shared by other radionuclides, and overlapped with gamma rays. Ties in emission probability are broken by the uncertainties of emission probability and then energy, so that priority numbers no longer depend on the platform.
- Beta-particle libraries are no longer exported to Gamma Explorer, whose libraries hold peak energies; the export of such a library wrote empty peaks.
- Gamma-cascade and energy-level datasets unavailable in the ENSDF are now registered in `./lib/nonexistent_nucl_data.txt`, and the pairs listed there are compared exactly. **The registry file of this version is not to be used with earlier versions**, which compare the pairs as substrings.
- A nuclear dataset is downloaded once, instead of twice, with a timeout of 60 s. Nuclear data files and the registry are written via temporary files, so that an interrupted run leaves no truncated file.
- Output directories are created without a prompt, including missing parent directories.
- Gamma cascades are traversed once per energy level and gamma data file; runs on cached nuclear data are 5-9 times faster. Unknown (NaN) energy levels are no longer listed in the level report files.
- The spectrum radiation ignores letter cases and blanks (e.g. `Gamma`), and a dataset may hold static radionuclides alone.

### Fixed

- A dataset without recursive progenitors crashed with `UnboundLocalError`.
- A spectrum radiation written in capitals (e.g. `Gamma`) crashed with `KeyError`.
- A limit of an annotation window written in scientific notation (e.g. `1e-1`) crashed the plotting with `TypeError`.
- A program path written as `exe` (earlier versions) was ignored once merged with the `exes` list of the default initialization file; it is now tried first.
- The flattened energy levels of Pb-209 were sorted incorrectly because of NaN entries.

## v1.0.3 (2026-10-08)

- The User-Agent of the requests to the Live Chart of Nuclides is set to `Livechart/1.0`, as requests without one are rejected by the server (#27).
- The bundled executable has been removed, and `requirements.txt` and `requirements-tested.txt` have been added (#29).

## v1.0.2 (2026-03-26)

- Inkscape, Ghostscript, and pdfcrop are searched for across platforms (#24, #25).
- Column keys for beta-particle libraries have been added (#19).
- Bug fixes (#22).

## v1.0.1 (2024-10-28)

- Error messages for Internet unavailability, naming the responsible side (server or client), have been added.

## v1.0.0 (2024-05-22)

- RecurLib first published.
