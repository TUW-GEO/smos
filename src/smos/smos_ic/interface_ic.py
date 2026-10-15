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

import numpy as np
from netCDF4 import Dataset
from smos.grid import EASE25CellGrid
from smos.interface import SMOSImg, SMOSDs, LatestVersionMixin


class SMOS_IC_Img(SMOSImg):
    """
    Class for reading one SMOS IC netcdf image file.

    Note: Since product version 106 (v2.0), SMOS IC files do not contain the
    'Quality_Flag' and 'Processing_Flags' variables anymore. Observations
    that were flagged as not recommended in previous versions (e.g. frozen,
    polluted or strong topography scenes) are already removed from the
    data. Therefore, no flag based filtering is applied when reading.

    Parameters
    ----------
    filename: str
        filename of the SMOS nc image file
    mode: str, optional (default: 'r')
        mode of opening the file, only 'r' is implemented at the moment
    parameters : str or list, optional (default: None)
        one or list of parameters to read. All parameters are described in
        docs/varnames.rst. If None are passed, all parameters are read.
    flatten: bool, optional (default: False)
        If set then the data is read into 1D arrays. This is used to e.g
        reshuffle the data.
    grid : pygeogrids.CellGrid, optional (default: EASE25CellGrid)
        Grid that the image data is organised on, by default the global EASE25
        grid is used.
    float_fillval : float or None, optional (default: np.nan)
        Fill Value for masked pixels, this is only applied to float variables.
        Therefore e.g. mask variables are never filled but use the fill value
        as in the data.
    empty_template : dict, optional (default: None)
        Variable name -> (dtype, fill value), as returned by
        `variable_template`. Used to create empty images (if the file is
        missing) with the correct data types (see `SMOSImg`).
    """

    def __init__(self, filename, mode='r', parameters=None, flatten=False,
                 grid=EASE25CellGrid(bbox=None), float_fillval=np.nan,
                 empty_template=None):

        super().__init__(filename, mode=mode, parameters=parameters,
                         flatten=flatten, grid=grid, read_flags=None,
                         float_fillval=float_fillval,
                         empty_template=empty_template)

    def _read_img(self) -> (dict, dict):
        # Read a netcdf image and metadata

        with Dataset(self.filename) as ds:
            self.glob_attrs = ds.__dict__

            param_img = {}
            param_meta = {}

            if len(self.parameters) == 0:
                # all data vars, exclude coord vars
                self.parameters = [k for k in ds.variables.keys() if
                                   ds.variables[k].ndim != 1]

            missing = [p for p in self.parameters if p not in ds.variables]
            if len(missing) > 0:
                available = [k for k in ds.variables.keys()
                             if ds.variables[k].ndim != 1]
                raise ValueError(f"Parameter(s) {missing} not found in "
                                 f"{self.filename}. Available: {available}")

            for parameter in self.parameters:
                metadata = {}
                param = ds.variables[parameter]
                data = param[:]

                # read long name, FillValue and unit
                for attr in param.ncattrs():
                    metadata[attr] = param.getncattr(attr)

                # keep the _FillValue mask (int vars) and mask NaNs (float vars)
                data = np.ma.masked_array(data, mask=np.ma.getmaskarray(data) | ~np.isfinite(data))
                np.ma.set_fill_value(data, metadata['_FillValue'])

                metadata['image_missing'] = 0

                if self.float_fillval is not None:
                    if issubclass(data.dtype.type, np.floating):
                        data = data.filled(fill_value=self.float_fillval)

                param_img[parameter] = data.flatten()[self.grid.activegpis]
                param_meta[parameter] = metadata

        return param_img, param_meta


class SMOS_IC_Ds(LatestVersionMixin, SMOSDs):
    """
    Class for reading SMOS IC images in nc format. Images are orgnaised in subdirs
    for each year.

    Parameters
    ----------
    data_path : str
        Path to the nc files
    parameter : str or list, optional (default: None)
        one or list of parameters to read, see SMOS documentation
        for more information (default: 'Soil_Moisture').
    flatten: bool, optional (default: False)
        If set then the data is read into 1D arrays. This is used to e.g
        reshuffle the data.
    grid : pygeogrids.CellGrid, optional (default: EASE25CellGrid)
        Grid that the image data is organised on, by default the global EASE25
        grid is used.
    filename_templ: str, optional (default: None)
        Template for the file names to read. `{datetime}` is replaced by the
        date of the image and `{version}` by the passed version. By default,
        we use `default_fname_template`, which matches all versions, file
        counters and (operational or reprocessed) brightness temperature
        campaigns.
    version: int or str, optional (default: None)
        SMOS IC product version (e.g. 106) to read. If None is passed, any
        version is accepted. If multiple files are found for a date, the one
        with the highest version (and file counter) is used.
    float_fillval : float or None, optional (default: np.nan)
        Fill Value for masked pixels, this is only applied to float variables.
        Therefore e.g. mask variables are never filled but use the fill value
        as in the data.
    """

    default_fname_template = \
        "SM_*_MIR_CDF3S*_{datetime}T000000_{datetime}T235959_{version}_*_8.DBL.nc"

    def __init__(self, data_path, parameters=None, flatten=False,
                 grid=EASE25CellGrid(bbox=None), filename_templ=None,
                 version=None, float_fillval=np.nan):

        if filename_templ is None:
            filename_templ = self.default_fname_template

        filename_templ = filename_templ.replace(
            '{version}', '*' if version is None else f"{int(version):03}")

        super().__init__(data_path, ioclass=SMOS_IC_Img,
                         parameters=parameters,
                         flatten=flatten,
                         grid=grid,
                         filename_templ=filename_templ,
                         read_flags=None,
                         float_fillval=float_fillval
                         )
        # no quality flags in SMOS IC, not passed to the image class
        self.ioclass_kws.pop('read_flags')
