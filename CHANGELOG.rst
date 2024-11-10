=========
Changelog
=========

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
