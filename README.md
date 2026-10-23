[![Static Badge](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.11081346-%233F3FD4)](https://zenodo.org/doi/10.5281/zenodo.11081346)
[![Static Badge](https://img.shields.io/badge/GitHub_Pages-https%3A%2F%2Fjangcom.github.io%2Frecurlib%2F-crimson)](https://jangcom.github.io/recurlib/)
[![Static Badge](https://img.shields.io/badge/Paper-https%3A%2F%2Fdoi.org%2F10.1103%2FPhysRevResearch.6.043208-%23189ab4)](https://doi.org/10.1103/PhysRevResearch.6.043208)

---

# NAME

RecurLib: A recursion-based radionuclide library generator

# DESCRIPTION

RecurLib generates radionuclide identification libraries for alpha-particle or gamma-ray spectrometry. Nuclear data are retrieved from the Evaluated Nuclear Structure Data File [[1](#references)] via the web application programming interface of the Live Chart of Nuclides [[2](#references)] requiring one-time Internet connection for newly encountered radionuclides.

*Keep it simple*: **All you need to do is specify progenitor radionuclides in a user input file**. RecurLib will then compute every feasible progeny and collect all the associated nuclear data on your behalf.

*But remain customizable*:
- Consult the initialization file `./inp/ini_recurlib.yaml` (`python recurlib.py --show-ini` prints its path), where you can find every setting of the data coverage and visualization of radionuclide libraries. To change a setting, copy it, together with its parent keys, into a dataset of the user input file; settings shared by every dataset of the file go under its `template` key, and those shared by several user input files can be collected in a custom initialization file passed with `--ini`.
- Create a Jinja template to obtain cross-platform library files that can be imported into commercial spectral analysis software.

# INSTALLATION

Run the Python script `recurlib.py` with the list of Python libraries in [PYTHON REQUIREMENTS](#python-requirements) installed.

The required libraries can be installed at once with either pip or conda:

    pip install -r requirements.txt

    conda install -c conda-forge --file requirements.txt

## PYTHON REQUIREMENTS

- The versions of Python libraries listed below are those that have been confirmed to work properly with RecurLib. Try these versions if you encounter a library-related program crash.
- For convenience, these versions are pinned in `requirements-tested.txt`; with Python 3.11, run `pip install -r requirements-tested.txt` or `conda install -c conda-forge --file requirements-tested.txt` to install them.

| Python library | Version | Use                               |
|----------------|---------|-----------------------------------|
| python         | 3.11.9  | To run RecurLib                   |
| pyyaml         | 6.0.1   | User input parsing                |
| jinja2         | 3.1.3   | Cross-platform data exchange      |
| matplotlib     | 3.8.4   | Data visualization                |
| pandas         | 2.2.1   | Data restructuring and management |

## OPTIONAL DEPENDENCIES

- Tabulated below are optional Python libraries and third-party software used for Excel writing or figure rendering purposes; install them on a per-need basis.
- Use of the specified versions is recommended, but not required.

| Python library/software                    | Version | Use                                       |
|--------------------------------------------|---------|-------------------------------------------|
| openpyxl (v3.0.10) or xlsxwriter (v3.1.1)  | -       | A Pandas dependency for Excel writing     |
| [Inkscape](https://inkscape.org)           | 1.3     | .emf rendering                            |
| [Ghostscript](https://www.ghostscript.com) | 10.02.1 | .pdf file size reduction and reversioning |
| [pdfcrop](https://ctan.org/pkg/pdfcrop)    | 1.38    | .pdf margin cropping                      |

## TESTS

The test suite under `tests/` runs RecurLib without Internet access on the sample input `./inp/trial.yaml` and on a test-only input, `tests/inp/extra.yaml`, using the nuclear data shipped in `./lib/nucl_data`. It compares the libraries, lineages and energy levels with the expected outputs under `tests/golden`, and checks independently that the lineages reproduce those published in the paper (see [SEE ALSO](#see-also)), that every line lies within the cutoffs, that the key lines are the most probable lines of each radionuclide, and that the Gamma Explorer exports hold the libraries. It also checks downloads and the registry of unavailable datasets against a stand-in for the Live Chart of Nuclides served from the shipped nuclear data. To run it from a clone of the repository:

    pip install -r requirements.txt pytest

    pytest

The same suite runs on GitHub Actions for every push and pull request, on Linux, macOS, and Windows, with the latest releases of the libraries and with the versions pinned in `requirements-tested.txt`.

After a deliberate change to the libraries RecurLib writes, rewrite the expected outputs with `python tests/update_golden.py` and review the differences (`git diff tests/golden`) before committing.

# SYNOPSIS

    python recurlib.py [file]
                       [--ini=file] [--echo] [--show-ini]

> On macOS and Linux without an activated conda or virtual environment, use `python3` instead of `python`.

> The paths in the initialization and user input files (e.g. `./lib/nucl_data` and `./figs`) are relative to the working directory; run RecurLib from the repository root, or use absolute paths. The default initialization file, `ini_recurlib.yaml` in the `inp` directory next to `recurlib.py`, is found regardless of the working directory; earlier versions read `./inp/ini_recurlib.yaml` of the working directory, which can now be passed with `--ini`.

# OPTIONS

    file
        A user input file (.yaml).

    --ini=file
        A custom initialization file (.yaml), deeply merged over the default
        one in the inp directory next to recurlib.py. It only needs to hold
        the settings that differ from the default ones, under the template
        key; a complete initialization file of earlier versions also works.

    --echo (default: False)
        Print the content of the initialization and user input files on the shell.

    --show-ini (default: False)
        Print the path of the default initialization file and exit.

# EXIT STATUS

    0   Every active dataset was processed. A dataset that cannot be processed
        (e.g. not defined in the user input file, or empty) is skipped with a
        warning, as is a library left without lines by the cutoffs.

    1   RecurLib stopped: a warning ending with the line "Terminating." says
        why (e.g. a missing input file, a misspelled radiation, invalid
        cutoffs, settings that cannot be merged over the default ones, or
        no access to the Live Chart of Nuclides).

# EXAMPLES

## Running RecurLib

`python recurlib.py ./inp/trial.yaml`

`python recurlib.py ./inp/trial.yaml --echo > trial.log`

## User input (.yaml) snippets

**An alpha-particle library for the thorium (4n) series**
```
thorium_series_alpha:
  scout:
    radionuclides:
      recursive:
        - Th-232  # Thorium (4n) series
      spectrum_radiation: alpha
  plot:
    xticks:
      lim:
        - 2e3  # Unit: keV
        - 9e3
    xlabel:
      label: Alpha-particle energy (keV)
    title:
      label: Thorium series ($4n$)
```

**A gamma-ray library for a mixture of uranium (4n+2) and actinium (4n+3) series and potassium-40**
```
mixture_gamma:
  scout:
    radionuclides:
      recursive:
        - U-238  # Uranium (4n+2) series
        - U-235  # Actinium (4n+3) series
        - K-40  # Potassium-40
      exclusion:
        - Pa-234  # Negligibly small quantity
      spectrum_radiation: gamma
  plot:
    xticks:
      lim:
        - 0
        - 2e3
    xlabel:
      label: Photon energy (keV)
    title:
      label: Uranium ($4n+2$) and actinium series ($4n+3$), and $^{40}$K
```

**A template shared by every dataset of the file**
```
template:  # Overridable at each active dataset
  scout:
    radionuclides:
      cutoffs:
        emission_probability:
          - 1e-1  # Unit: %
          - 1e2

active_datasets:
  - thorium_series_alpha
  - mixture_gamma

thorium_series_alpha:
  # As above
mixture_gamma:
  # As above
```

> `template` and `active_datasets` are not allowed as dataset names, in any letter case or as a word of one (e.g. `thorium template`).

# CAVEATS

> Radionuclides unknown to RecurLib trigger Internet connection to the [Live Chart of Nuclides](https://www-nds.iaea.org/relnsd/vcharthtml/VChartHTML.html) to download the required nuclear datasets. Once accessed, these datasets are stored to the local drive (to the library directory specified at the initialization file) and reused in the subsequent runs.

For the reason above, RecurLib can be used in offline environments only if all the pertinent nuclear datasets have been fetched from the Live Chart of Nuclides.

# REFERENCES

[1] [ENSDF](https://www.nndc.bnl.gov/ensdf/), maintained by the National Nuclear Data Center of the Brookhaven National Laboratory.

[2] [Live Chart of Nuclides](https://www-nds.iaea.org/relnsd/vcharthtml/VChartHTML.html), developed and maintained by the Nuclear Data Section of the International Atomic Energy Agency.

# SEE ALSO

[RecurLib in a paper: _Phys. Rev. Res._ **6** (2024) 043208](https://doi.org/10.1103/PhysRevResearch.6.043208)

# AUTHOR

Jaewoong Jang <jang[at]ric.u-tokyo.ac.jp>

# COPYRIGHT

Copyright (c) 2024-2026 Jaewoong Jang

# LICENSE

This software is available under the permissive MIT license; the license information is found in 'LICENSE'.
