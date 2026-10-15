=========
Changelog
=========

Unreleased changes in master branch
===================================


v0.5
====
New features
------------
- Support for the SMOS L3 soil moisture products of CATDS (CLF3S, CLF31, CLF33,
  CLF3E, CLF3D, CLF3M; ascending and descending): download from the CATDS FTP
  server, image reader (``smos.smos_l3.interface_l3``) and conversion to / update
  of time series. The processing campaigns (OPER, RE07, future reprocessings)
  are read from the server; ``update_img`` also downloads a new campaign for
  the whole period of the local record.
- Download of SMOS IC data from the CATDS server (no account required).
- Support for SMOS IC v106 (v2.0) data. If there are multiple files for a date
  (versions, campaigns, file counters), the latest one is used for SMOS IC and
  L3 (``version`` option to read a specific version).
- New command line program ``smos`` with a group of commands for each product:
  ``smos l2``, ``smos ic``, ``smos l3`` (``download``, ``update_img``,
  ``reshuffle``, ``update_ts``) and ``smos l4`` (``reshuffle``). This replaces
  the documented ``smos_repurpose`` program, which was never installed.
  ``smos_l2`` is kept for backwards compatibility.
- SMOS L4: the scientific / operational product is detected from the file,
  operational files can now be converted to time series.

Changes
-------
- SMOS L4: ``read_flags`` is now the lower and upper threshold of the quality
  variable (``QUAL`` / ``Quality``), default ``(0, 1)`` (only missing data is
  masked). ``smos l4 reshuffle`` has a ``--quality_range`` option,
  ``--only_good`` of ``smos.smos_l4.reshuffle_l4.main`` keeps only the best
  quality (1).
- SMOS IC: the ``read_flags`` option was removed, v106 files have no
  ``Quality_Flag`` (not recommended observations are already removed).
  ``--only_good`` is ignored with a warning.
- Removed the notebooks to create land masked grid files for SMOS IC and L3
  (``mask_and_flatten_gridfile.ipynb``), use the ``only_land`` option instead.
- Empty images (for missing dates) have the same data types as the actual
  images for SMOS IC, L3 and L4 (integer variables are masked).
- The output folder is created when writing (subset) images.

Bug fixes
---------
- ``EASE25CellGrid(only_land=True)``: land points keep their global grid
  point indices. Previously, the readers of SMOS IC and L4 read the values of
  the wrong pixels for land-only grids, i.e. SMOS L4 time series created with
  ``--only_land`` (without ``--bbox``) in v0.4 contain data of wrong locations
  and must be re-created.
- SMOS L4 quality filtering: the allowed quality values were compared exactly
  with the float32 ``QUAL`` index, so the reader dropped all values with
  ``QUAL`` < 1 and the conversion to time series only kept ``QUAL`` = 0 or 1
  (``--only_good`` kept ``QUAL`` = 0, the lowest quality). SMOS L4 time series
  created with older versions miss these observations and should be
  re-created.
- Missing images could lead to wrong values in time series of integer
  variables (e.g. SMOS IC ``Days`` = -2147483648, ``Scene_Flags`` = 0 instead
  of missing values) or float instead of integer variables.
- SMOS IC: the ``--only_land`` option of the conversion to time series was
  ignored.
- SMOS L2 download: the lftp option ``--no-perms`` was passed with unicode
  dashes.
- Finding the first image file for the SMOS IC / L4 conversion failed for
  relative paths or other (non-netCDF) files in the image folder.
- Keep the _FillValue mask of integer variables when reading SMOS IC images.
- SMOS L3: damaged or incomplete archives (e.g. after an interrupted download)
  no longer stop the extraction of all other archives, and no partially
  extracted files are left.

Packaging, CI and documentation
-------------------------------
- Package configuration moved from setup.cfg / setup.py to pyproject.toml,
  all dependencies are installed from pip (``pip install smos``), added
  missing dependencies (click, tqdm, pyyaml). The conda ``environment.yml`` and
  ``tox.ini`` were removed.
- Supported Python versions are 3.11 to 3.14 (dropped 3.10, which reaches its
  end of life in October 2026). Python 3.15 is tested in CI, but not all
  dependencies provide wheels for it yet.
- Test data (git submodule) is not included in the source distribution.
  SMOS IC test data was updated to v106, SMOS L3 test data was added.
- CI uses pip instead of conda, tests on Linux and Windows, builds the
  documentation and the Docker image. Updated all GitHub Actions, added
  Dependabot for them.
- Docker image based on python-slim (instead of micromamba / alpine), runs as
  a non-root user.
- Documentation: new pages for data download and test data, all examples
  are checked against the test data, added SMOS L3 and L4 reading and time
  series examples. Updated the Read the Docs configuration.
- README converted to Markdown (``README.md``) with a quickstart guide.
- All subpackages are regular packages (with ``__init__.py``).
- Added ``AGENTS.md`` with guidelines for contributions by coding agents.

v0.4
====
- pass only_land bool to SMOSL2Reader in qa4sm-preprocessing
- add only_land option to L4 grid creation and reshuffling
- Add Grid_Point_Mask_USGS.nc to be used for masking (Geo2d mask)
- Add ipynb scripts to convert regular global grid.nc to flat land masked grid.nc for smos ic and smos l3

v0.3.2
======
- Fixed a bug that led to failing SMOS L2 downloads

v0.3.1
======
- Changed the default variables reshuffled for SMOS L2 and added option to select variables

v0.3.0
======
- Add support for SMOS L4 RZSM product (`PR #11 <https://github.com/TUW-GEO/smos/pull/11>`_)
- Update pyscaffold to v4, Replace Travis CI with GithubActions (`PR #11 <https://github.com/TUW-GEO/smos/pull/11>`_)
- Add support for SMOS L2 product
- Add scripts for operational data updates of SMOS L2 (download and time series extension)

v0.2
====
- Add option read data for spatial subsets
- Add option to add time stamps to time series index
- Add function to write images/stacks down
- Add function to reshuffle by bounding box
- Update docs and travis, automatic pypi deployment
- Update tests
- By default also reshuffle if Scene_Flag is 2
- Switch to pyscaffold 3 package structure
- Drop support for python 2

v0.1
====
- First version of L3 SMOS IC image and TS reader
- Include time series reshuffling
- Include tests and CI
- Basic documentation
