Reading converted time series data
----------------------------------

For reading the data the ``smos_repurpose`` command produces the class
``SMOSTs`` can be used. Optional arguments that are passed to the parent class
(``OrthoMultiTs``, as defined in `pynetcf.time_series <https://github.com/TUW-GEO/pynetCF/blob/master/pynetcf/time_series.py>`_)
can be passed as well:

.. code-block:: python

    from smos.smos_ic.interface import SMOSTs
    ds = SMOSTs(ts_path, parameters=['Soil_Moisture','RMSE'],
                ioclass_kws={'read_bulk': True})
    # read_ts takes either lon, lat coordinates or a grid point indices.
    # and returns a pandas.DataFrame
    ts = ds.read_ts(45, 15) # (lon, lat)


Bulk reading speeds up reading multiple points from a cell file by storing the
file in memory for subsequent calls.