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
from netCDF4 import Dataset, date2num, num2date
from smos.grid import EASE25CellGrid
from smos.interface import SMOSImg, SMOSDs


class SMOS_IC_Img(SMOSImg):
    """
    Class for reading one SMOS IC netcdf image file.

    Parameters
    ----------
    filename: str
        filename of the SMOS nc image file
    mode: str, optional (default: 'r')
        mode of opening the file, only 'r' is implemented at the moment
    parameters : str or list, optional (default: None)
        one or list of parameters to read. We add 'Quality_Flags' if 'read_flags'
        is not None. All parameters are described in docs/varnames.rst. If
        None are passed, all parameters are read.
    flatten: bool, optional (default: False)
        If set then the data is read into 1D arrays. This is used to e.g
        reshuffle the data.
    grid : pygeogrids.CellGrid, optional (default: EASE25CellGrid)
        Grid that the image data is organised on, by default the global EASE25
        grid is used.
    read_flags : tuple or None, optional (default: (0, 1))
        Filter values to read based on the selected QUALITY_FLAGS.
        Values for locations that are not assigned any of the here passed flags
        are replaces with NaN (by default only the missing-data, i.e. flag=2,
        locations are filtered out). If None is passed, no flags are considered.
    float_fillval : float or None, optional (default: np.nan)
        Fill Value for masked pixels, this is only applied to float variables.
        Therefore e.g. mask variables are never filled but use the fill value
        as in the data.
    """

    def __init__(self, filename, mode='r', parameters=None, flatten=False,
                 grid=EASE25CellGrid(bbox=None), read_flags=(0, 1), float_fillval=np.nan):

        super(SMOSImg, self).__init__(filename, mode=mode)

        if parameters is None:
            parameters = []
        if type(parameters) != list:
            parameters = [parameters]

        self.read_flags = read_flags
        self.parameters = parameters
        self.flatten = flatten

        self.grid = grid

        self.image_missing = False
        self.img = None  # to be loaded
        self.glob_attrs = None

        self.float_fillval = float_fillval


    def _read_img(self) -> (dict, dict):
        # Read a netcdf image and metadata

        ds = Dataset(self.filename)
        self.glob_attrs = ds.__dict__

        param_img = {}
        param_meta = {}

        if len(self.parameters) == 0:
            # all data vars, exclude coord vars
            self.parameters = [k for k in ds.variables.keys() if
                               ds.variables[k].ndim != 1]

        parameters = list(self.parameters)

        if (self.read_flags is not None) and ('Quality_Flag' not in parameters):
            parameters.append('Quality_Flag')

        for parameter in parameters:
            metadata = {}
            param = ds.variables[parameter]
            data = param[:]

            # read long name, FillValue and unit
            for attr in param.ncattrs():
                metadata[attr] = param.getncattr(attr)

            data.mask = ~np.isfinite(data)
            np.ma.set_fill_value(data, metadata['_FillValue'])

            metadata['image_missing'] = 0

            param_img[parameter] = data
            param_meta[parameter] = metadata

        # filter with the flags (this excludes non-land points as well)
        if self.read_flags is not None:
            flag_mask = ~np.isin(param_img['Quality_Flag'], self.read_flags)
        else:
            flag_mask = np.full(param_img[parameters[0]].shape, False)

        for param, data in param_img.items():

            param_img[param].mask = (data.mask | flag_mask)

            if self.float_fillval is not None:
                if issubclass(data.dtype.type, np.floating):
                    param_img[param] = data.filled(fill_value=self.float_fillval)

            param_img[param] = param_img[param].flatten()[self.grid.activegpis]

        if ('Quality_Flag' in param_img.keys()) and \
                ('Quality_Flag' not in self.parameters):
            param_img.pop('Quality_Flag')
            param_meta.pop('Quality_Flag')

        return param_img, param_meta


class SMOS_IC_Ds(SMOSDs):
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
    read_flags : tuple or None, optional (default: (0, 1))
        Filter values to read based on the selected QUALITY_FLAGS.
        Values for locations that are not assigned any of the here passed flags
        are replaces with NaN (by default only the missing-data, i.e. flag=2,
        locations are filtered out).
    float_fillval : float or None, optional (default: np.nan)
        Fill Value for masked pixels, this is only applied to float variables.
        Therefore e.g. mask variables are never filled but use the fill value
        as in the data.
    """

    default_fname_template = "SM_RE06_MIR_CDF3S*_{datetime}T000000_{datetime}T235959_105_*_8.DBL.nc"

    def __init__(self, data_path, parameters=None, flatten=False,
                 grid=EASE25CellGrid(bbox=None), filename_templ=None,
                 read_flags=(0, 1), float_fillval=np.nan):

        if filename_templ is None:
            filename_templ = self.default_fname_template

        super().__init__(data_path, ioclass=SMOS_IC_Img,
                         parameters=parameters,
                         flatten=flatten,
                         grid=grid,
                         filename_templ=filename_templ,
                         read_flags=read_flags,
                         float_fillval=float_fillval
                         )
