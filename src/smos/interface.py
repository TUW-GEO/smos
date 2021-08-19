# -*- coding: utf-8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2021, TU Wien
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import numpy as np
import pandas as pd
from netCDF4 import num2date

from pynetcf.time_series import GriddedNcOrthoMultiTs
from pygeogrids.netcdf import load_grid


class SMOSTs(GriddedNcOrthoMultiTs):

    _t0_vars = {'sec': 'UTC_Seconds', 'days': 'Days'}
    _t0_unit = 'days since 2000-01-01'

    def __init__(self, ts_path, grid_path=None, index_add_time=False,
                 drop_missing=True, **kwargs):
        """
        Class for reading SMOS time series after reshuffling images.
        Missing images are represented in time series as lines where all
        variables are NaN.

        Parameters
        ----------
        ts_path : str
            Directory where the netcdf time series files are stored
        grid_path : str, optional (default: None)
            Path to grid file, that is used to organize the location of time
            series to read. If None is passed, grid.nc is searched for in the
            ts_path.
        index_add_time : bool, optional (default: False)
            Add overpass time stamps to the data frame index. This needs the
            'Days' and 'UTC_Seconds' variable available in the time series files.
        drop_missing : bool, optional (default: True)
            Drop Lines in TS where ALL variables are missing.

        Optional keyword arguments that are passed to the Gridded Base:
        ------------------------------------------------------------------------
            parameters : list, optional (default: None)
                Specific variable names to read, if None are selected, all are read.
            offsets : dict, optional (default:None)
                Offsets (values) that are added to the parameters (keys)
            scale_factors : dict, optional (default:None)
                Offset (value) that the parameters (key) is multiplied with
            ioclass_kws: dict
                Optional keyword arguments to pass to OrthoMultiTs class:
                ----------------------------------------------------------------
                    read_bulk : boolean, optional (default:False)
                        if set to True the data of all locations is read into memory,
                        and subsequent calls to read_ts read from the cache and not from disk
                        this makes reading complete files faster#
                    read_dates : boolean, optional (default:False)
                        if false dates will not be read automatically but only on specific
                        request useable for bulk reading because currently the netCDF
                        num2date routine is very slow for big datasets
                    autofill : bool, (default: True)
                        Fill missing values with nans
        """

        if grid_path is None:
            grid_path = os.path.join(ts_path, "grid.nc")

        self.drop_missing = drop_missing
        grid = load_grid(grid_path)
        super(SMOSTs, self).__init__(ts_path, grid, **kwargs)

        self.index_add_time = index_add_time
        if (self.parameters is not None) and self.index_add_time:
            for v in self._t0_vars.values():
                self.parameters.append(v)

    def _to_datetime(self, df:pd.DataFrame) -> pd.DataFrame:
        # convert Days and UTC_Seconds to actual datetimes
        units = self._t0_unit

        df['_date'] = df.index.values

        if (self._t0_vars['days'] not in df.columns) or \
            (self._t0_vars['sec'] not in df.columns):
            raise KeyError(f"Could not find {self._t0_vars['days']} or {self._t0_vars['sec']} "
                           f"in reshuffled data.")


        # days + (seconds / seconds per day)
        num = df[self._t0_vars['days']].dropna() + (df[self._t0_vars['sec']].dropna() / 86400.)
        if len(num) == 0:
            df.loc[num.index, '_datetime_UTC'] = []
        else:
            df.loc[num.index, '_datetime_UTC'] = \
                pd.DatetimeIndex(num2date(num.values, units=units,
                        calendar='standard', only_use_cftime_datetimes=False))

        df = df.set_index('_datetime_UTC')
        df = df[df.index.notnull()]
        return df

    def read(self, *args, **kwargs):
        """
        Read time series by grid point index, or by lonlat. Convert columns to
        ints if possible (if there are no Nans in it).

        Parameters
        ----------
        lon: float
            Location longitude
        lat : float
            Location latitude
        .. OR
        gpi : int
            Grid point Index

        Returns
        -------
        df : pd.DataFrame
            Time Series data at the selected location
        """

        ts = super(SMOSTs, self).read(*args, **kwargs)

        if self.drop_missing:
            ts = ts.dropna(how='all')

        for col in ts:  # convert to ints, if possible
            if (not np.isnan(ts[col]).any()) and \
                    (np.all(np.mod(ts[col].values, 1) == 0.)):
                ts[col] = ts[col].astype(int)

        if self.index_add_time:
            ts = self._to_datetime(ts)

        return ts
