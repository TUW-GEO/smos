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

import warnings
import numpy as np
from netCDF4 import Dataset
from smos.grid import EASE25CellGrid
from smos.interface import SMOSImg, SMOSDs


def quality_range(read_flags):
    """
    Lower and upper quality threshold from the passed read_flags. Other than
    2 values (e.g. a list of allowed quality values as in older versions) are
    converted to their (min, max) range, with a warning.
    """
    if read_flags is None:
        return None
    flags = np.atleast_1d(read_flags).astype(float)
    if len(flags) != 2:
        rng = (float(np.min(flags)), float(np.max(flags)))
        warnings.warn(f"read_flags is the lower and upper threshold of the "
                      f"quality variable, {read_flags} is interpreted as "
                      f"{rng}.")
        return rng
    if flags[0] > flags[1]:
        raise ValueError(f"Lower quality threshold must be <= upper "
                         f"threshold, got {read_flags}")
    return float(flags[0]), float(flags[1])


class SMOS_L4_Img(SMOSImg):
    """
    Child-class for reading one SMOS L4 CATDS - CESBIO RZSM netcdf image file.

    Parameters
    ----------
    filename: str
        filename of the SMOS nc image file
    mode: str, optional (default: 'r')
        mode of opening the file, only 'r' is implemented at the moment
    parameters : str or list, optional (default: None)
        one or list of parameters to read. We add 'Quality_Flags' if 'read_flags'
        is not None. All parameters are described in docs/varnames.rst.
        If None is passed, all parameters are read.
    flatten: bool, optional (default: False)
        If set then the data is read into 1D arrays. This is used to e.g
        reshuffle the data.
    grid : pygeogrids.CellGrid, optional (default: EASE25CellGrid)
        Grid that the image data is organised on, by default the global EASE25
        grid is used.
    read_flags : tuple or None, optional (default: (0, 1))
        Lower and upper threshold (both included) of the quality variable
        (QUAL for the scientific, Quality for the operational product).
        Values at locations where the quality is outside of this range or
        missing are replaced with NaN. The scientific product has a quality
        index between 0 and 1 (1.0 highest quality, in steps of 0.2), the
        operational product -1 (missing data), 0 (not recommended) and 1 (OK),
        i.e. the default (0, 1) only removes missing data, (1, 1) only keeps
        the best quality. If None is passed, no filtering is applied.
    oper : bool or None, optional (default: None)
        Whether the file is from the SMOS L4 RZSM Scientific (False) or
        Operational (True) product, which differ in the naming and values of
        the quality variable (see docs/varnames.rst). If None is passed, this
        is detected from the file (Quality variable -> operational).
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
                 grid=EASE25CellGrid(bbox=None), read_flags=(0, 1),
                 oper=None, float_fillval=np.nan, empty_template=None):

        super().__init__(filename, mode=mode)

        if parameters is None:
            parameters = []
        if type(parameters) != list:
            parameters = [parameters]

        self.read_flags = quality_range(read_flags)
        self.parameters = parameters
        self.flatten = flatten

        self.oper = oper

        self.grid = grid

        self.image_missing = False
        self.img = None  # to be loaded
        self.glob_attrs = None

        self.float_fillval = float_fillval
        self.empty_template = empty_template


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

            parameters = list(self.parameters)

            if self.oper is None:
                self.oper = 'Quality' in ds.variables

            if not self.oper:
                if (self.read_flags is not None) and ('QUAL' not in parameters):
                    parameters.append('QUAL')
            else:
                if (self.read_flags is not None) and ('Quality' not in parameters):
                    parameters.append('Quality')

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
            qual = np.ma.filled(
                param_img['Quality' if self.oper else 'QUAL'].astype(float),
                np.nan)
            # the quality is stored as float32, allow for rounding errors
            lower, upper = self.read_flags
            flag_mask = ~((qual >= lower - 1e-6) & (qual <= upper + 1e-6))

        else:
            flag_mask = np.full(param_img[parameters[0]].shape, False)

        for param, data in param_img.items():

            param_img[param].mask = (data.mask | flag_mask)

            if self.float_fillval is not None:
                if issubclass(data.dtype.type, np.floating):
                    param_img[param] = data.filled(fill_value=self.float_fillval)

            param_img[param] = param_img[param].flatten()[self.grid.activegpis]

        if not self.oper:
            if ('QUAL' in param_img.keys()) and \
                    ('QUAL' not in self.parameters):
                param_img.pop('QUAL')
                param_meta.pop('QUAL')
        else:
            if ('Quality' in param_img.keys()) and \
                    ('Quality' not in self.parameters):
                param_img.pop('Quality')
                param_meta.pop('Quality')

        return param_img, param_meta


class SMOS_L4_Ds(SMOSDs):
    """
    Class for reading SMOS L4 CATDS - CESBIO RZSM images in nc format. Images are orgnaised in subdirs
    for each year.

    Parameters
    ----------
    data_path : str
        Path to the nc files
    parameters : str or list, optional (default: None)
        one or list of parameters to read. We add quality flags if 'read_flags'
        is not None. All parameters are described in docs/varnames.rst.
        If None is passed, all parameters are read.
    flatten: bool, optional (default: False)
        If set then the data is read into 1D arrays. This is used to e.g
        reshuffle the data.
    grid : pygeogrids.CellGrid, optional (default: EASE25CellGrid)
        Grid that the image data is organised on, by default the global EASE25
        grid is used.
    read_flags : tuple or None, optional (default: (0, 1))
        Lower and upper threshold (both included) of the quality variable
        (QUAL for the scientific, Quality for the operational product).
        Values at locations where the quality is outside of this range or
        missing are replaced with NaN. The scientific product has a quality
        index between 0 and 1 (1.0 highest quality, in steps of 0.2), the
        operational product -1 (missing data), 0 (not recommended) and 1 (OK),
        i.e. the default (0, 1) only removes missing data, (1, 1) only keeps
        the best quality. If None is passed, no filtering is applied.
    oper : bool or None, optional (default: None)
        Whether the file is from the SMOS L4 RZSM Scientific (False) or
        Operational (True) product, which differ in the naming and values of
        the quality variable (see docs/varnames.rst). If None is passed, this
        is detected from the file (Quality variable -> operational).
    float_fillval : float or None, optional (default: np.nan)
        Fill Value for masked pixels, this is only applied to float variables.
        Therefore e.g. mask variables are never filled but use the fill value
        as in the data.
    """

    default_fname_template = "SM_*_MIR_CLF4RD*_{datetime}T000000_{datetime}T235959_*_*_*.DBL.nc"

    def __init__(self, data_path, parameters=None, flatten=False,
                 grid=EASE25CellGrid(bbox=None), filename_templ=None,
                 read_flags=(0, 1), oper=None, float_fillval=np.nan):

        if filename_templ is None:
            filename_templ = self.default_fname_template

        super().__init__(data_path, ioclass=SMOS_L4_Img,
                         parameters=parameters,
                         flatten=flatten,
                         grid=grid,
                         filename_templ=filename_templ,
                         read_flags=read_flags,
                         float_fillval=float_fillval,
                         additional_kws={'oper': oper}
                         )
