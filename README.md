# SMOS

[![CI/CD](https://github.com/TUW-GEO/smos/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/TUW-GEO/smos/actions/workflows/ci.yml)
[![Coverage](https://coveralls.io/repos/github/TUW-GEO/smos/badge.svg?branch=master)](https://coveralls.io/github/TUW-GEO/smos?branch=master)
[![PyPI](https://badge.fury.io/py/smos.svg)](https://badge.fury.io/py/smos)
[![Documentation](https://readthedocs.org/projects/smos/badge/?version=latest)](https://smos.readthedocs.io/en/latest/)
[![DOI](https://zenodo.org/badge/167011732.svg)](https://zenodo.org/badge/latestdoi/167011732)

Download, readers and time series conversion for SMOS (Soil Moisture and
Ocean Salinity) soil moisture data. Works great in combination with
[pytesmo](https://github.com/TUW-GEO/pytesmo).

The full documentation is available at
[smos.readthedocs.io](https://smos.readthedocs.io/en/latest/). To cite this
package, follow the Zenodo (DOI) badge above and export the citation there.

## Supported products

| Product | Description | Download | Command group |
|---|---|---|---|
| [SMOS L2](https://earth.esa.int/eogateway/catalog/smos-science-products) | ESA L2 soil moisture swaths (MIR_SMUDP2) | ESA FTP (EO Sign In account) | `smos l2` |
| [SMOS IC](https://www.catds.fr/Products/Available-products-from-CEC-SM/SMOS-IC) | INRAE-CESBIO SMOS-IC (CDF3S), 25 km | CATDS (no account) | `smos ic` |
| [SMOS L3](https://www.catds.fr/Products/Available-products-from-CPDC/L3-Land-products) | CATDS L3 soil moisture (CLF3S, CLF31, CLF33, CLF3E, CLF3D, CLF3M), 25 km | CATDS FTP (public account) | `smos l3` |
| [SMOS L4 RZSM](https://www.catds.fr/Products/Available-products-from-CEC-SM/L4-Land-research-products) | CATDS-CESBIO root zone soil moisture, 25 km | not included | `smos l4` |

## Installation

All dependencies are available via pip (Python >= 3.11):

```shell
pip install smos
```

The download programs use [lftp](https://lftp.yar.ru/), which must be
installed on your system (e.g. `apt-get install lftp`). The package can also
be installed into an existing conda environment, e.g. if you prefer installing
compiled dependencies such as netCDF4 or pyresample from conda-forge first.

## Quickstart

All command line programs are available via `smos <product> <command>`, see
`smos --help` and e.g. `smos l3 download --help`. As an example, download 10
days of SMOS L3 daily soil moisture (ascending overpasses):

```shell
smos l3 download ./smos_l3 --product CLF3S --orbits ASC -s 2024-01-01 -e 2024-01-10
```

and convert the images over Europe into time series (5x5 degree cell files):

```shell
smos l3 reshuffle ./smos_l3/MIR_CLF3SA ./smos_l3_ts --parameters Soil_Moisture,Mean_Acq_Time_Days,Mean_Acq_Time_Seconds --bbox -11 34 43 71
```

Read an image and a time series in python:

```python
from datetime import datetime
from smos.smos_l3.interface_l3 import SMOS_L3_Ds, SMOSL3Ts

ds = SMOS_L3_Ds('./smos_l3/MIR_CLF3SA', parameters='Soil_Moisture')
image = ds.read(datetime(2024, 1, 5))
sm = image.data['Soil_Moisture']  # global 2D array (584 x 1388)

ts = SMOSL3Ts('./smos_l3_ts', index_add_time=True).read(16.37, 48.21)  # lon, lat
print(ts['Soil_Moisture'])
```

To keep the data up to date, download all images that are new since the last
downloaded day (until today) and append them to the time series with

```shell
smos l3 update_img ./smos_l3 --product CLF3S --orbits ASC
smos l3 update_ts ./smos_l3/MIR_CLF3SA ./smos_l3_ts
```

The other products work the same way, see the
[documentation](https://smos.readthedocs.io/en/latest/) for details.

## Docker image

For each release, a Docker image with the package and `lftp` is published to
the GitHub container registry:

```shell
docker run --rm -v /path/to/data:/data ghcr.io/tuw-geo/smos:latest smos l3 update_img /data/smos_l3
```

The container runs as a non-root user (uid 1000), pass e.g.
`--user $(id -u):$(id -g)` to access mounted data as your own user. To build
the image locally from the checked out version, run `docker build -t smos .`.

## Development

Clone the repository including the test data submodule (requires
[git lfs](https://git-lfs.com/)) and install the package in editable mode with
the test dependencies:

```shell
git clone --recurse-submodules git@github.com:TUW-GEO/smos.git
cd smos
pip install -e ".[testing]"
pytest
```

## Contribute

We are happy if you want to contribute. Please raise an issue explaining what
is missing or if you find a bug. We will also gladly accept pull requests
against our master branch for new features or bug fixes:

- Fork the smos repository and create a feature branch from master.
- Add your feature or fix, including tests (we use pytest) and documentation
  (numpy style docstrings, docs pages, `CHANGELOG.rst`).
- Format your code with `yapf` (settings in `pyproject.toml`).
- Submit a pull request to our master branch.

See [AGENTS.md](https://github.com/TUW-GEO/smos/blob/master/AGENTS.md) for more detailed development guidelines.
