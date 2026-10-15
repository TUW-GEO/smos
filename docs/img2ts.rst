Conversion to time series format
================================

For a lot of applications it is favorable to convert the image based format into
a format which is optimized for fast time series retrieval. This is what we
often need for e.g. validation studies. This can be done by stacking the images
into a netCDF file and choosing the correct chunk sizes or a lot of other
methods. We have chosen to do it in the following way:

- Store the time series in netCDF4 in the Climate and Forecast convention
  `Orthogonal multidimensional array representation
  <http://cfconventions.org/cf-conventions/v1.6.0/cf-conventions.html#_orthogonal_multidimensional_array_representation>`_
  (SMOS IC, L3, L4) or `Indexed ragged array representation
  <http://cfconventions.org/cf-conventions/v1.6.0/cf-conventions.html#_indexed_ragged_array_representation>`_
  (SMOS L2, as the number of observations differs between locations).
- Store the time series in 5x5 degree cells. This means there will be 2448 cell
  files for global data and a file called ``grid.nc``, which contains the information about which grid point is stored in which file.
  This allows us to read a whole 5x5 degree area into memory and iterate over the time series quickly.

  .. image:: 5x5_cell_partitioning.png
     :target: _images/5x5_cell_partitioning.png

Conversion to time series is performed by the `repurpose package
<https://github.com/TUW-GEO/repurpose>`_ in the background. For custom settings
or other options see the `repurpose documentation
<http://repurpose.readthedocs.io/en/latest/>`_ .

The following command line programs are available (see ``--help`` of each
command for all options):

=============  =====================  ===================================
Product        Convert images         Append new images to time series
=============  =====================  ===================================
SMOS L2        ``smos l2 reshuffle``  ``smos l2 update_ts``
SMOS IC        ``smos ic reshuffle``  \-
SMOS L3        ``smos l3 reshuffle``  ``smos l3 update_ts``
SMOS L4 RZSM   ``smos l4 reshuffle``  \-
=============  =====================  ===================================

Grid point indices (gpis) in the time series are the same as in the global
image grid, also if only a spatial subset (``--bbox``) or only land points
(``--only_land``) are converted.

SMOS IC
-------

SMOS IC images of one overpass (``ASC`` or ``DES`` folder) are converted with
the ``smos ic reshuffle`` program, e.g.

.. code-block:: shell

   smos ic reshuffle /path/to/smos_ic/ASC /path/to/ts/smos_ic_asc -s 2011-01-01 -e 2011-12-31 --parameters Soil_Moisture,Scene_Flags,RMSE,Days,UTC_Seconds --bbox -11 34 43 71

which converts Soil_Moisture, Scene_Flags and RMSE values over Europe from
January 1st to December 31st 2011 and stores the time series in the folder
``/path/to/ts/smos_ic_asc``. The observation time variables (Days and
UTC_Seconds) are needed to read the time series with the actual observation
time as index (see `Reading time series`_).

Options for ``smos ic reshuffle``:

- **--startdate (-s)** / **--enddate (-e)** : First and last day to convert
  (YYYY-MM-DD). Default: first and last available image.
- **--parameters (-v)** : Parameters to convert (comma-separated). Default:
  all parameters in the first image file.
- **--bbox** : min_lon min_lat max_lon max_lat. Bounding box (lower left and
  upper right corner) of the area to convert (WGS84). Default: global.
- **--only_land** : Only convert land points.
- **--imgbuffer (-b)** : The number of images that are read into memory before
  converting them into time series. Bigger numbers make the conversion faster
  but consume more memory. Default: 100.

SMOS L4 RZSM
------------

SMOS L4 images (scientific or operational product, detected from the files)
are converted with ``smos l4 reshuffle``, which has the same options as
``smos ic reshuffle`` and additionally ``--quality_range LOWER UPPER`` (``-q``)
to only keep observations where the quality variable is within this range
(see the SMOS L4 section in the image reading docs). The default ``0 1`` only removes missing data,
e.g. ``-q 0.8 1`` keeps observations with a quality index of at least 0.8:

.. code-block:: shell

   smos l4 reshuffle /path/to/smos_l4 /path/to/ts/smos_l4 -s 2018-01-01 -e 2018-12-31 --parameters RZSM,QUAL --only_land -q 0.8 1

SMOS IC and L4 time series are read with ``smos.interface.SMOSTs`` (see
`Reading time series`_ below).

SMOS L2
-------

SMOS L2 swath files are converted with ``smos l2 reshuffle``. By default, the
variables Soil_Moisture, Science_Flags, Confidence_Flags, Chi_2_P, RFI_Prob,
N_RFI_X, N_RFI_Y and M_AVA0 are converted (``--variables`` to change this),
the acquisition time and an overpass flag are always added.

.. code-block:: shell

   smos l2 reshuffle /path/to/smos_l2 /path/to/ts/smos_l2 -s 2022-01-01 -e 2022-12-31

New swath files (e.g. after ``smos l2 update_img``) are appended to the existing
time series via

.. code-block:: shell

   smos l2 update_ts /path/to/smos_l2 /path/to/ts/smos_l2

The time series can be read with ``pynetcf.time_series.GriddedNcIndexedRaggedTs``:

.. code-block:: python

   import os
   from pygeogrids.netcdf import load_grid
   from pynetcf.time_series import GriddedNcIndexedRaggedTs

   ts_path = '/path/to/ts/smos_l2'
   reader = GriddedNcIndexedRaggedTs(ts_path,
                                     grid=load_grid(os.path.join(ts_path, 'grid.nc')))
   ts = reader.read(-70.696, 50.629)  # lon, lat
   reader.close()

SMOS L3
-------

SMOS L3 images of one product and overpass are converted with the
``smos l3 reshuffle`` program, e.g.

.. code-block:: shell

   smos l3 reshuffle /path/to/smos_l3/MIR_CLF3SA /path/to/ts/MIR_CLF3SA -s 2021-01-01 -e 2021-12-31 --parameters Soil_Moisture,Science_Flags,Mean_Acq_Time_Days,Mean_Acq_Time_Seconds --bbox -11 34 43 71

If no parameters are passed, all variables are converted. The settings are
stored in the file ``overview.yml`` in the time series directory. New images
(e.g. after ``smos l3 update_img``) can then be appended to the existing time
series (with the same settings) via

.. code-block:: shell

   smos l3 update_ts /path/to/smos_l3/MIR_CLF3SA /path/to/ts/MIR_CLF3SA

The time series can be read with ``smos.smos_l3.interface_l3.SMOSL3Ts``.
With ``index_add_time=True`` the actual observation time (from the
``Mean_Acq_Time_Days`` and ``Mean_Acq_Time_Seconds`` variables) is used as index:

.. code-block:: python

   from smos.smos_l3.interface_l3 import SMOSL3Ts

   ds = SMOSL3Ts('/path/to/ts/MIR_CLF3SA', index_add_time=True)
   ts = ds.read(15.0, 48.0)  # lon, lat

The same functionality is available via ``smos.smos_l3.reshuffle.img2ts`` and
``smos.smos_l3.reshuffle.extend_ts``.

Reading time series
-------------------

SMOS IC and L4 time series are read with ``smos.interface.SMOSTs``. Optional
arguments are passed to the parent class (``OrthoMultiTs``, as defined in
`pynetcf.time_series <https://github.com/TUW-GEO/pynetCF/blob/master/pynetcf/time_series.py>`_).
With ``index_add_time=True`` the observation time (from the ``Days`` and
``UTC_Seconds`` variables of SMOS IC) is used as index:

.. code-block:: python

   from smos.interface import SMOSTs

   ds = SMOSTs('/path/to/ts/smos_ic_asc', ioclass_kws={'read_bulk': True},
               index_add_time=True)
   # read takes either lon, lat coordinates or a grid point index
   # and returns a pandas.DataFrame
   ts = ds.read(20.36, 47.68)  # (lon, lat)
   ds.close()

Bulk reading speeds up iterative reading of multiple (adjacent) points from a cell
file by storing the file in memory for subsequent calls.
