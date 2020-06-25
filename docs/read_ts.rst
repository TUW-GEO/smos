Reading converted time series data
----------------------------------

For reading the data the ``smos_repurpose`` command produces the class
``SMOSTs`` can be used. Optional arguments that are passed to the parent class
(``OrthoMultiTs``, as defined in `pynetcf.time_series <https://github.com/TUW-GEO/pynetCF/blob/master/pynetcf/time_series.py>`_)
can be passed as well:

.. code-block:: python

    from smos.smos_ic.interface import SMOSTs
    ds = SMOSTs('/path/to/ts', parameters=['Soil_Moisture','RMSE'],
                ioclass_kws={'read_bulk': True}, index_add_time=True)
    # read_ts takes either lon, lat coordinates or a grid point indices.
    # and returns a pandas.DataFrame
    ts = ds.read_ts(45, 15) # (lon, lat)

    >> ts
                         Soil_Moisture       RMSE  UTC_Seconds  Days      _date
    _datetime_UTC
    2010-01-16 15:19:28       0.076049   9.918421        55168  3668 2010-01-16
    2010-02-11 15:07:07       0.082200   6.816125        54427  3694 2010-02-11
    2010-03-01 15:06:33       0.111931   5.149402        54393  3712 2010-03-01
        ...                     ...                 ...                 ...

Bulk reading speeds up iterative reading of multiple (adjacent) points from a cell
file by storing the file in memory for subsequent calls.