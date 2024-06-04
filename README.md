[![Static Badge](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.11081346-%233F3FD4)](https://zenodo.org/doi/10.5281/zenodo.11081346)
[![Static Badge](https://img.shields.io/badge/GitHub_Pages-https%3A%2F%2Fjangcom.github.io%2Frecurlib%2F-crimson)](https://jangcom.github.io/recurlib/)

---

# NAME

RecurLib: A recursion-based radionuclide library generator

# DESCRIPTION

RecurLib generates radionuclide identification libraries for alpha-particle or gamma-ray spectrometry. Nuclear data are retrieved from the Evaluated Nuclear Structure Data File [[l](#references)] via the web application programming interface of the Live Chart of Nuclides [[2](#references)] requiring one-time Internet connection for newly encountered radionuclides.

*Keep it simple*: **All you need to do is specify progenitor radionuclides in a user input file**. RecurLib will then compute every feasible progeny and collect all the associated nuclear data on your behalf.

*But remain customizable*:
- Edit the initialization file `./inp/ini_recurlib.yaml` where you can tailor the data coverage and visualization settings of radionuclide libraries in great detail.
- Create a Jinja template to obtain cross-platform library files that can be imported into commercial spectral analysis software.

# INSTALLATION

**Option 1: No installation required**

Use the enclosed executable `recurlib.exe`.

**Option 2: Full-fledged implementation**

Run the Python script `recurlib.py` with the list of Python libraries in [PYTHON REQUIREMENTS](#python-requirements) installed.

# SYNOPSIS

**Executable**

    recurlib.exe [file]
                 [--ini=file] [--echo]

**Python (full-fledged)**

    python recurlib.py [file]
                       [--ini=file] [--echo]

# OPTIONS

    file
        A user input file (.yaml).

    --ini=file (default: ./inp/ini_recurlib.yaml)
        An initialization file (.yaml).

    --echo (default: False)
        Print the content of the initialization and user input files on the shell.

# EXAMPLES

## Running RecurLib

`recurlib.exe ./inp/trial.yaml`

`recurlib.exe ./inp/trial.yaml --echo > trial.log`

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

## PYTHON REQUIREMENTS

- The versions of Python libraries listed below are those that have been confirmed to work properly with RecurLib. Try these versions if you encounter a library-related program crash.
- pip-installed Matplotlib uses OpenBLAS NumPy, which may be more suitable for bundling purposes.

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

# CAVEATS

> Radionuclides unknown to RecurLib trigger Internet connection to the [Live Chart of Nuclides](https://www-nds.iaea.org/relnsd/vcharthtml/VChartHTML.html) to download the required nuclear datasets. Once accessed, these datasets are stored to the local drive (to the library directory specified at the initialization file) and reused in the subsequent runs.

For the reason above, RecurLib can be used in offline environments only if all the pertinent nuclear datasets have been fetched from the Live Chart of Nuclides.

# REFERENCES

[1] [ENSDF](https://www.nndc.bnl.gov/ensdf/), maintained by the National Nuclear Data Center of the Brookhaven National Laboratory.

[2] [Live Chart of Nuclides](https://www-nds.iaea.org/relnsd/vcharthtml/VChartHTML.html), developed and maintained by the Nuclear Data Section of the International Atomic Energy Agency.

# AUTHOR

Jaewoong Jang <jang[at]ric.u-tokyo.ac.jp>

# COPYRIGHT

Copyright (c) 2024 Jaewoong Jang

# LICENSE

This software is available under the permissive MIT license; the license information is found in 'LICENSE'.
