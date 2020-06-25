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
- Store the time series in 5x5 degree cells. This means there will be 2448 cell
  files for global data and a file called ``grid.nc``, which contains the information about which grid point is stored in which file.
  This allows us to read a whole 5x5 degree area into memory and iterate over the time series quickly.

  .. image:: 5x5_cell_partitioning.png
     :target: _images/5x5_cell_partitioning.png

This conversion can be performed using the ``smos_repurpose`` command line
program. An example would be:

.. code-block:: shell

   smos_repurpose /smos_ic_img_data /timeseries/data 2011-01-01 2011-01-02 --parameters Soil_Moisture --bbox -11 34 43 71

Which would take Soil_Moisture values from SMOS IC images stored in ``/image_data`` from January 1st
2011 to January 2nd 2011 and store the values as time series in the folder ``/timeseries/data``.

Keywords that can be used in ``smos_repurpose``:

- **-h (--help)** : Shows the help text for the reshuffle function
- **--parameters** : Parameters to reshuffle into time series format. e.g.
  Soil_Moisture. If this is not specified, all parameters in the first detected image
  file will be reshuffled. Default: None.
- **--only_good** : Read only 0-flagged (GOOD) observations (by Quality_Flag),
  if this is set to False, also 1-flagged (not recommended) ones will be read and reshuffled,
  2-flagged (missing) values are always excluded. Excluded values are replaced by NaNs.
  Default: False.
- **--bbox** : min_lon min_lat max_lon max_lat. Bounding Box (lower left and upper
  right corner) of subset area of global images to reshuffle (WGS84). Default: None.
- **--imgbuffer** : The number of images that are read into memory before converting
  them into time series. Bigger numbers make the conversion faster but consume more memory.
  Default: 100.


Conversion to time series is performed by the `repurpose package
<https://github.com/TUW-GEO/repurpose>`_ in the background. For custom settings
or other options see the `repurpose documentation
<http://repurpose.readthedocs.io/en/latest/>`_ .
