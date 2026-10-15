Test data
=========

A small set of sample files for each supported product is available in a
separate repository. These are the files used in the automated tests, and you
can also use them to try out the examples in this documentation without
downloading the full data records first. The test data is *not* part of the
``smos`` package installed via pip.

The repository contains:

- ``L3_SMOS_IC/ASC/2018`` and ``L3_SMOS_IC/DES/2018``: SMOS IC (v106) images for
  2018-01-01 (ASC, DES) and 2018-01-03 (ASC only). There is intentionally no
  file for 2018-01-02, to show how missing days are handled.
- ``L2_SMOS/2022/01/<DD>``: SMOS L2 swath files for 2022-01-01 to 2022-01-03.
- ``L4_SMOS_RZSM/SCIE`` and ``L4_SMOS_RZSM/OPER``: SMOS L4 RZSM images.
- ``L3_SMOS/MIR_<product><A|D>``: SMOS L3 archives (``.tgz``, as on the server)
  for all L3 products. ``MIR_CLF3SA`` contains 2021-06-06 (both the RE07 and
  OPER file), 2021-06-07 and 2021-06-09 (2021-06-08 is intentionally missing),
  ``MIR_CLF3SD`` contains 2021-06-06. For all other products there is one
  ascending file starting on 2025-01-01. Extract the archives before reading
  them, e.g. with ``smos.smos_l3.download.extract_archives('/path/to/smos-test-data/L3_SMOS')``.

Download
--------

The netCDF files are stored with `Git LFS <https://git-lfs.com/>`_, so make sure
it is installed (e.g. ``apt-get install git-lfs`` or
``conda install -c conda-forge git-lfs``, then run ``git lfs install`` once).
Without Git LFS you only get small text pointer files instead of the actual
data.

To only get the test data (about 200 MB), clone the repository directly:

.. code-block:: shell

   git clone https://git.geo.tuwien.ac.at/public_projects/rs/rs_testdata/smos-test-data.git

If you work on the ``smos`` code itself, the test data is included as a
submodule in ``tests/smos-test-data``. Clone the package repository with

.. code-block:: shell

   git clone --recurse-submodules https://github.com/TUW-GEO/smos.git

or, in an existing clone, run ``git submodule update --init``.

Usage
-----

In the examples in this documentation, ``testdata_path`` is the path to
the cloned test data folder, e.g.

.. code-block:: python

   import os
   from datetime import datetime
   from smos.smos_ic.interface_ic import SMOS_IC_Ds

   testdata_path = '/path/to/smos-test-data'

   ds = SMOS_IC_Ds(os.path.join(testdata_path, 'L3_SMOS_IC', 'ASC'),
                   parameters=['Soil_Moisture'])
   image = ds.read(datetime(2018, 1, 1))
   print(image.data['Soil_Moisture'].shape)  # (584, 1388)

The time series conversion described below also works with the test data,
e.g. to convert the SMOS IC sample images over Europe:

.. code-block:: shell

   smos ic reshuffle /path/to/smos-test-data/L3_SMOS_IC/ASC /tmp/smos_ic_ts --parameters Soil_Moisture --bbox -11 34 43 71
