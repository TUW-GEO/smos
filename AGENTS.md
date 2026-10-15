# AGENTS.md

Guidance for coding agents working on the `smos` package (TU Wien, TUW-GEO):
readers, downloaders and image-to-time-series conversion for SMOS soil
moisture products.

## Products and code layout

| Product | Package | Download | Reader | Time series |
|---|---|---|---|---|
| SMOS L2 (ESA swaths, MIR_SMUDP2) | `smos/smos_l2` | `download.py` (ESA FTP, EO account) | via `qa4sm_preprocessing.level2.smos.SMOSL2Reader` | `reshuffle.py` (IndexedRagged, read with `pynetcf.time_series.GriddedNcIndexedRaggedTs`) |
| SMOS IC (CATDS, CDF3S) | `smos/smos_ic` | `download.py` (`SmosIcHttp`, https, no account) | `interface_ic.py` | `reshuffle_ic.py` (OrthoMulti, read with `smos.interface.SMOSTs`) |
| SMOS L3 (CATDS, CLF3S/31/33/3E/3D/3M) | `smos/smos_l3` | `download.py` (`SmosL3Ftp`, public CATDS FTP account as default) | `interface_l3.py` | `reshuffle.py` (`SMOSL3Ts`) |
| SMOS L4 RZSM (CATDS, CLF4RD, SCIE/OPER) | `smos/smos_l4` | none | `interface_l4.py` | `reshuffle_l4.py` (`SMOSTs`) |

Shared code:
- `src/smos/interface.py`: `SMOSImg` / `SMOSDs` base classes (image reading,
  typed empty images, writing subsets), `LatestVersionMixin`, `SMOSTs`.
- `src/smos/grid.py`: `EASE25CellGrid` (EASE2 25 km, 584 x 1388, 5° cells)
  with `bbox` and `only_land` options. Used by IC, L3, L4 (L2 has its own
  grid from qa4sm_preprocessing).
- `src/smos/reshuffle.py`: argparse helpers (`parse_args`, `firstfile`) used by
  the IC / L4 python `main()` functions.
- `src/smos/misc.py`: `overview.yml` helpers, first/last image date.
- `src/smos/cli.py`: the `smos` command.

## Command line

One entry point, `smos`, with a click group per product (`smos --help`):
- `smos l2` / `smos l3`: `download`, `update_img`, `reshuffle`, `update_ts`
- `smos ic`: `download`, `update_img`, `reshuffle`
- `smos l4`: `reshuffle` (no downloader)

Each group lives in `smos_<product>/cli.py`. `smos_l2` is kept as a
deprecated entry point (it was released). When adding a command, register it in
the product group, keep options consistent with the other groups
(`-s/-e` dates defaulting to the first/last image, `--parameters` comma
separated, `--bbox` 4 floats, `--only_land` flag, `--imgbuffer`), and add it to
`tests/test_cli.py` and `docs/img2ts.rst` / `docs/download.rst`.

Downloads use `lftp` (system program). `download` writes an `overview.yml`
(first/last day, for L3 also the campaigns) that `update_img` relies on, same
for time series (`update_ts`).

## Project policies

- **Python versions**: support the latest Python release and a few versions
  before it. When a new Python version is released, add it to the CI matrix
  (`.github/workflows/ci.yml`) and the classifiers, fix what breaks, and drop
  versions that have reached end of life (update `requires-python`, the
  classifiers, the CI matrix, README, `.readthedocs.yml` and the Python version
  of the Dockerfile together). CI should always test the oldest and the newest
  supported version; Docker and Read the Docs use the newest one (Read the
  Docs may lag behind, use the newest version it offers).
- **No sensitive information in the repository or git history**: no
  passwords, tokens, API keys, personal credentials or private URLs in code,
  tests, docs, notebooks, CI files or commit messages. Credentials are read
  from the environment or user config files (e.g. ESA EO account for SMOS L2 in
  `$HOME/.smosapirc`), CI secrets are only referenced via `${{ secrets.* }}`.
  Tests use dummy values. The only exception is the public CATDS FTP account
  for SMOS L3 (`ext-catds-cpdc`), which CATDS publishes on its website. If a
  secret was committed, removing it in a new commit is not enough: tell the
  maintainer (the secret must be revoked and the history rewritten).
- **Docstrings** follow the numpy convention (`Parameters`, `Returns`,
  `Raises`, ... sections with `name : type` lines) for all public modules,
  classes, functions and methods.
- **Code style**: format code with `yapf` (`yapf -i <files>`), configured in
  `[tool.yapf]` of `pyproject.toml` (based on the `yapf` style, 4 spaces
  indentation, 79 characters line limit; don't add a separate `.style.yapf` or
  `setup.cfg` section). Only reformat files/lines you change, to keep diffs
  reviewable; flake8 (`.flake8`) must not report new issues.
- **Everything is tested and documented**: every new feature, option and bug
  fix comes with tests (a bug fix with a test that fails without the fix) and
  with documentation (docstrings, the relevant `docs/*.rst` page, CLI `--help`
  texts and `CHANGELOG.rst`).
- **Keep the package scaffolding up to date**: the project was created with
  PyScaffold. Packaging, CI, docs config and the other meta files should
  follow current versions of PyScaffold and the PyPA standards (e.g. when a new
  PyScaffold version is released, compare its template with this repository
  and adopt the changes). Note that the package metadata currently lives in
  `pyproject.toml` (PEP 621) instead of PyScaffold's `setup.cfg`; keep that
  unless a newer PyScaffold template does it differently.

## Environment and tests

- All dependencies from pip (`pyproject.toml`, PEP 621, setuptools_scm
  version). No setup.cfg/setup.py anymore.
- Dev install: `pip install -e .[testing]` (docs: `.[docs]`).
- Run tests: `pytest` (addopts add coverage; use `--no-cov -W ignore -q` for
  quick runs). The full suite takes ~6 min, mostly reshuffling tests.
- Test data is a git submodule with Git LFS: `tests/smos-test-data`
  (https://git.geo.tuwien.ac.at/public_projects/rs/rs_testdata/smos-test-data.git).
  Run `git submodule update --init` and make sure `git lfs` is installed,
  otherwise netCDF files are LFS pointer files and tests fail with odd netCDF
  errors. Contents are described in `docs/testdata.rst`; L3 data is stored as
  `.tgz` archives (extracted in `tests/smos_l3/conftest.py`, fixture `l3_root`).
- Changes to test data are committed in the submodule repo first, then the
  submodule pointer here.
- Tests that need the network or lftp mock `exec` / `list` of the downloader
  classes (see `tests/smos_l3/test_l3_download.py` `_fake_server`). Do not add
  tests that download data.
- CI: `.github/workflows/ci.yml`, ubuntu + windows, oldest and newest
  supported Python version (currently 3.11 and 3.14), pip only. A new Python
  release is first added as `experimental` job (allowed to fail) until all
  dependencies provide wheels for it (check e.g. with the Docker build, the
  slim image has no compilers), then it becomes the newest supported version.
  Keep code Windows compatible (`os.path.join` for local paths,
  `PurePosixPath` for server paths).

## Repository files

- `pyproject.toml`: all package metadata, dependencies (extras `testing` and
  `docs`), entry points, pytest, setuptools_scm and yapf settings. There is no
  setup.cfg, setup.py, tox.ini, conda `environment.yml` or
  `docs/requirements.txt` anymore; don't re-add them.
- `MANIFEST.in`: needed. setuptools_scm adds all git tracked files to the
  sdist, including the test data submodule (~40 MB); `MANIFEST.in` prunes it.
- `.github/workflows/ci.yml`: tests (Linux, Windows), docs build, Docker build,
  coverage (Coveralls), and on `v*` tags of TUW-GEO publishing to PyPI and of
  the Docker image to ghcr.io. `.github/dependabot.yml` keeps the actions up
  to date.
- `Dockerfile` / `.dockerignore`: two stage build (wheel built with git for
  the setuptools_scm version, installed into `python:<version>-slim` with
  lftp), runs as non-root user `smos`.
- `.readthedocs.yml`: installs the package with the `docs` extra; `docs/conf.py`
  runs sphinx-apidoc for the API reference (`docs/api`, git-ignored).
- `README.md` (Markdown, also the PyPI description): overview, installation
  and a quickstart; the docs include it via myst-parser
  (`docs/index.rst`). Keep the quickstart commands working, use absolute
  links (relative links don't resolve in the docs).
- Every (sub)package in `src/smos` has an `__init__.py` (regular packages, no
  implicit namespace packages); add one for new subpackages.
- `CHANGELOG.rst`: unreleased changes are grouped in "New features",
  "Changes", "Bug fixes" and "Packaging, CI and documentation"; mention
  changes that affect existing data or user code explicitly.

## Conventions

- Line endings: the repo uses `core.autocrlf=true`; many existing files are
  CRLF in the working tree, new files are LF. When editing, preserve the
  existing line endings of a file (don't convert whole files).
- Match the surrounding code style (see Project policies for docstrings,
  yapf and flake8).
- Every user-visible change gets an entry in `CHANGELOG.rst` under
  "Unreleased changes in master branch".
- Docs (`docs/*.rst`, built with sphinx, all pages are also included in
  `index.rst`): code examples must run against the test data
  (`testdata_path = '/path/to/smos-test-data'` placeholder). After changing
  docs, execute the code blocks and build with
  `python -m sphinx -b html -q docs <outdir>`; it should produce no warnings.
- `src/local_scripts/` is git-ignored and holds personal analysis scripts, not
  package code.

## Important behaviour (don't break)

- **Grid point indices are global.** `EASE25CellGrid(only_land=True)` and
  `bbox` subsets are `subset`s of the global grid; gpis are never renumbered.
  Readers select image pixels with `grid.activegpis` from the flattened global
  image, so renumbering would read wrong pixels. Reading gpi X from a land-only
  or a global time series must give the same data (tests:
  `*_land_same_gpis`).
- **Multiple files per date**: `LatestVersionMixin` picks the file with the
  highest `<version>_<counter>` (file names end with
  `_<version>_<counter>_<site>.DBL.nc`). IC and L3 accept a `version=` to pin
  one version. File name templates use `SM_*_` so any campaign matches.
- **L3 campaigns are not hard-coded**: `SmosL3Ftp` lists the campaign folders
  on the server (`OPER`, `RE<nn>`, sorted with OPER last). `smos l3 update_img`
  downloads a campaign that isn't in the local `overview.yml` for the whole
  local period. All campaigns share one local folder per product/orbit
  (`MIR_<product><A|D>/<YYYY>/<DOY|MM>/`).
- **Empty images keep data types**: `SMOSDs` builds an `empty_template`
  (dtype, fill value per variable) from the first file; missing dates produce
  float NaN / masked integer arrays of the same types. Otherwise `Img2Ts`
  writes wrong values (e.g. -2147483648) or float types into the time series.
  New image classes must accept and pass on `empty_template`.
- **L4 quality filter**: `read_flags=(lower, upper)` is an inclusive range on
  `QUAL` (SCIE, 0-1 in steps of 0.2, float32) or `Quality` (OPER, -1 missing,
  0 not recommended, 1 OK). Default `(0, 1)` only removes missing data. Never
  compare float32 quality values with `==`/`np.isin`. SCIE vs OPER is detected
  from the file (`oper=None`). The `long_name` of OPER `Quality` in the files
  is wrong (see `docs/varnames.rst`).
- **SMOS IC v106** has no `Quality_Flag` (data is pre-screened), so IC has no
  `read_flags`; `--only_good` is ignored with a warning.
- **L3 specifics**: variables with a third dimension are split
  (`_med/_min/_max` for CLF3D, `_re/_im` for dielectric constant); image time
  stamps depend on the product (daily, dekads 1/11/21, monthly), see
  `SMOS_L3_Ds.tstamps_for_daterange`. Files are stored south-up, the reader
  returns north-up 2D images.

## Before finishing a change

1. Run the relevant tests (and the full suite for changes in `interface.py`,
   `grid.py` or `reshuffle.py`).
2. New code is tested; if a bug is fixed, add a test that fails without the
   fix.
3. Numpy docstrings, yapf formatting of the changed code.
4. Update docs and `CHANGELOG.rst`; run the affected doc examples.
5. Check the diff for credentials or other sensitive information.
6. Don't commit or push unless asked; the test data submodule needs its own
   commit/push first.
