# -*- coding: utf-8 -*-

# The MIT License (MIT)
#
# Copyright (c) 2022, TU Wien
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

import glob

from smos import dist_name as subdist_name
from smos import dist_name, __version__
from collections import OrderedDict

import parse
import os

import numpy as np
from netCDF4 import Dataset, date2num
from datetime import datetime
from smos.grid import ISEA4h9CellGrid
from smos.interface import SMOSImg, SMOSDs



class SMOS_L2_Img(SMOSImg):
    """
    Class for reading one SMOS L2 netcdf image file.

    Parameters
    ----------
    filename: str
        filename of the SMOS nc image file
    mode: str, optional (default: 'r')
        mode of opening the file, only 'r' is implemented at the moment
    parameters : str or list, optional (default: None)
        one or list of parameters to read. We add 'Science_Flagss' if 'read_flags'
        is not None. All parameters are described in docs/varnames.rst. If
        None are passed, all parameters are read.
    flatten: bool, optional (default: False)
        If set then the data is read into 1D arrays. This is used to e.g
        reshuffle the data.
    grid : pygeogrids.CellGrid, optional (default: ISEA4h9CellGrid)
        Grid that the image data is organised on, by default the global ISEA 4h9
        grid is used.
    read_flags : tuple or None, optional (default: (0, 1))
        Filter values to read based on the selected Science_FlagsS.
        Values for locations that are not assigned any of the here passed flags
        are replaces with NaN (by default only the missing-data, i.e. flag=2,
        locations are filtered out). If None is passed, no flags are considered.
    float_fillval : float or None, optional (default: np.Nan)
        Fill Value for masked pixels, this is only applied to float variables.
        Therefore, e.g. mask variables are never filled but use the fill value
        as in the data.
    gpi_name : str, optional. Default is "Grid_Point_ID"
        GPP variable name as it appears in the L2 files
    """

    def __init__(
            self,
            filename,
            mode='r',
            parameters=None,
            flatten=False,
            grid=ISEA4h9CellGrid(),
            read_flags=(0, 1),
            float_fillval=np.nan,
            gpi_name="Grid_Point_ID",
    ):

        super(SMOSImg, self).__init__(filename, mode=mode)

        if parameters is None:
            parameters = []
        if type(parameters) != list:
            parameters = [parameters]

        self.read_flags = read_flags
        self.parameters = parameters
        self.flatten = flatten
        self.gpi_name = gpi_name

        self.grid = grid

        self.image_missing = False
        self.img = None  # to be loaded
        self.glob_attrs = None

        self.float_fillval = float_fillval

    def _read_empty(self):
        """
        Create an empty image for filling missing dates, this is necessary
        for reshuffling as img2ts cannot handle missing days.

        Returns
        -------
        empty_img : dict
            Empty arrays of image size for each object parameter
        """
        self.image_missing = True

        return_img = {}
        return_metadata = {}

        gpis = len(self.grid.activegpis)

        for param in self.parameters:
            data = np.full(gpis, np.nan)
            return_img[param] = data.flatten()
            return_metadata[param] = {'image_missing': 1}

        return return_img, return_metadata

    def _reconstruct_data(self, img_gpis, partial_array) -> np.array:
        """
        Reconstruct the missing grid points in the image and
        assign a NaN value for the parameter

        Parameters
        ----------
        img_gpis : np. Array
            gpis present in the image
        partial_array : np. Array
            values in the image

        Returns
        -------
        reconstructed: np. Array
            original data array with the entire grid shape
        """
        # find what gpis of the global grid are in the file
        gpi_img_mask = np.in1d(self.grid.gpis, img_gpis[:].data)

        # create a global NaN grid and fill with the data
        reconstructed = np.empty(gpi_img_mask.shape)
        reconstructed[:] = partial_array.fill_value
        reconstructed[gpi_img_mask] = partial_array.data

        # apply original mask
        reconstructed = np.ma.masked_where(reconstructed == partial_array.fill_value, reconstructed)
        np.ma.set_fill_value(reconstructed, partial_array.fill_value)

        return reconstructed

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

        if (self.read_flags is not None) and ('Science_Flags' not in parameters):
            parameters.append('Science_Flags')

        for parameter in parameters:
            metadata = {}
            param = ds.variables[parameter]
            data = param[:]

            # fill the missing gpis to reconstruct the entire grid
            data = self._reconstruct_data(ds.variables[self.gpi_name], data,)

            # read long name, FillValue and unit
            for attr in param.ncattrs():
                metadata[attr] = param.getncattr(attr)
            # consistency in data types
            metadata['_FillValue'] = metadata['_FillValue'].astype(data.dtype)

            data.mask = ~np.isfinite(data)
            np.ma.set_fill_value(data, metadata['_FillValue'])

            metadata['image_missing'] = 0

            param_img[parameter] = data
            param_meta[parameter] = metadata

        # filter with the flags (this excludes non-land points as well)
        if self.read_flags is not None:
            flag_mask = ~np.isin(param_img['Science_Flags'], self.read_flags)
        else:
            flag_mask = np.full(param_img[parameters[0]].shape, False)

        for param, data in param_img.items():

            param_img[param].mask = (data.mask | flag_mask)

            if self.float_fillval is not None:
                if issubclass(data.dtype.type, np.floating):
                    param_img[param] = data.filled(fill_value=self.float_fillval)

            # take only the gpis of the grid subset
            gpi_active_mask = np.in1d(self.grid.gpis, self.grid.activegpis)
            param_img[param] = param_img[param].flatten()[gpi_active_mask]

        if ('Science_Flags' in param_img.keys()) and \
                ('Science_Flags' not in self.parameters):
            param_img.pop('Science_Flags')
            param_meta.pop('Science_Flags')

        return param_img, param_meta

    def write(self, image, **kwargs):
        """
        Write the image to a separate output path. E.g. after reading only
        a subset of the parameters, or when reading a spatial subset (with a
        subgrid). If there is already a file, the new image is appended along
        the time dimension.

        Parameters
        ----------
        image : str
            Path to netcdf file to create.
        kwargs
            Additional kwargs are given to netcdf4.Dataset
        """

        if self.img is None:
            raise IOError("No data found for current image, load data first")

        if self.img.timestamp is None:
            raise IOError("No time stamp found for current image.")

        gpis = self.grid.activegpis

        mode = 'w' if not os.path.isfile(image) else 'a'
        ds = Dataset(image, mode=mode, **kwargs)

        ds.set_auto_scale(True)
        ds.set_auto_mask(True)

        units = 'Days since 2000-01-01 00:00:00'

        if mode == 'w':
            ds.createDimension('timestamp', None)  # stack dim
            ds.createDimension('gpi', len(gpis))

            # this is not the obs time, but an image time stamp
            ds.createVariable('timestamp', datatype=np.double, dimensions=('timestamp',),
                              zlib=True, chunksizes=None)
            ds.createVariable('gpi', datatype='float64', dimensions=('gpi',), zlib=True)

            ds.variables['timestamp'].setncatts({'long_name': 'timestamp',
                                                 'units': units})
            ds.variables['gpi'].setncatts({'long_name': 'grid_point_index', 'units': '#',
                                           'valid_range': (1, 9262145)})

            ds.variables['timestamp'][:] = np.array([])
            ds.variables['gpi'] = gpis

            this_global_attrs = \
                OrderedDict([('subset_img_creation_time', str(datetime.now())),
                             ('subset_img_bbox_corners_latlon', str(self.grid.bbox)),
                             ('subset_software', f"{dist_name} | {subdist_name} | {__version__}")])
            glob_attrs = self.glob_attrs
            for k in ['ease_global', 'history', 'creation_time', 'NCO']:
                try:
                    glob_attrs.pop(k)
                except KeyError:
                    continue
            glob_attrs.update(this_global_attrs)
            ds.setncatts(glob_attrs)

        idx = ds.variables['timestamp'].shape[0]
        ds.variables['timestamp'][idx] = date2num(self.img.timestamp, units=units)

        for var, vardata in self.img.data.items():

            if var not in ds.variables.keys():
                ds.createVariable(var, vardata.dtype, dimensions=('timestamp', 'gpi'),
                                  zlib=True, complevel=6)
                ds.variables[var].setncatts(self.img.metadata[var])

            ds.variables[var][-1] = vardata

        ds.close()


class SMOS_L2_Ds(SMOSDs):
    """
    Class for reading SMOS L2 images in nc format. Images are orgnaised in subdirs
    for each year.

    Methods have been adapted to account for the fact that the files are relative to
    individual satellite tracks (i.e, multiple files for a single day)

    Parameters
    ----------
    data_path : str
        Path to the nc files
    parameters : str or list, optional (default: None)
        one or list of parameters to read, see SMOS documentation
        for more information (default: 'Soil_Moisture').
    flatten: bool, optional (default: True)
        If set then the data is read into 1D arrays. This is used to e.g
        reshuffle the data.
    grid : pygeogrids.CellGrid, optional (default: EASE25CellGrid)
        Grid that the image data is organised on, by default the global EASE25
        grid is used.
    read_flags : tuple or None, optional (default: (0, 1))
        Filter values to read based on the selected Science_Flags.
        Values for locations that are not assigned any of the here passed flags
        are replaces with NaN (by default only the missing-data, i.e. flag=2,
        locations are filtered out).
    float_fillval : float or None, optional (default: np.nan)
        Fill Value for masked pixels, this is only applied to float variables.
        Therefore e.g. mask variables are never filled but use the fill value
        as in the data.
    sub_path : str or list, optional. Default is '%Y'
        path to the files stored in the subfolders. If listed, each subforlder
        is a different element, e.g. ['%Y', '%m']
    filename_templ : str, default is None
    subtime_filename_templ : str, default is None
    """
    # Used to find all the subtime files
    default_fname_template = "SM_REPR_MIR_SMUDP2_{datetime}T*_700_100_1.nc"

    # parse settings
    datetimestart = 'datetimestart'
    timestart = 'timestart'
    datetimeend = 'datetimeend'
    timeend = 'timeend'
    # Used to get the time information from the files found in the index
    parse_fname_template = f"SM_REPR_MIR_SMUDP2_{{datetimestart}}T{{timestart}}_{{datetimeend}}T{{timeend}}_700_100_1.nc"

    # Used to find a specific subtime file
    default_subtime_fname_template = f"SM_REPR_MIR_SMUDP2_{{datetimestart}}T{{timestart}}*_700_100_1.nc"

    def __init__(
            self, data_path,
            parameters=None,
            flatten=True,
            grid=ISEA4h9CellGrid(),
            filename_templ=None,
            subtime_filename_templ=None,
            read_flags=(0, 1),
            float_fillval=np.nan,
            custom_templ=None,
    ):
        if read_flags is not None:
            raise NotImplementedError(
                "Code should at the moment only be used for reshuffling"
            )

        if filename_templ is None:
            filename_templ = self.default_fname_template

        self.custom_templ = custom_templ
        self.subtime_filename_templ = subtime_filename_templ

        super().__init__(data_path, ioclass=SMOS_L2_Img,
                         parameters=parameters,
                         flatten=flatten,
                         grid=grid,
                         filename_templ=filename_templ,
                         read_flags=read_flags,
                         float_fillval=float_fillval,
                         sub_path=['%Y', '%m', '%d'],
                         )

    def _search_files(self, timestamp, custom_templ=None, str_param=None,
                      custom_datetime_format=None):
        """
        Adapted from io_base.MultiTemporalImageBase._search_files
        for having sub daily timestamps
        """
        # Meaning we are looking for all subtimes matching a specific date,
        # e.g. datetime.datetime(2016, 1, 1, 0, 0) -> timestamp.time().strftime('%H%M') == '0000'
        if timestamp.time().strftime('%H%M') == '0000':
            if custom_templ is not None:
                fname_templ = custom_templ
            else:
                fname_templ = self.fname_templ

            if custom_datetime_format is not None:
                dFormat = {self.dtime_placeholder: custom_datetime_format}
            else:
                dFormat = {self.dtime_placeholder: self.datetime_format}

            fname_templ = fname_templ.format(**dFormat)

            if str_param is not None:
                fname_templ = fname_templ.format(**str_param)

        # Meaning we are looking for a specific subtime file,
        # e.g. datetime.datetime(2016, 1, 1, 12, 25, 43) -> timestamp.time().strftime('%H%M') == '122543'
        else:
            if self.subtime_filename_templ is not None:
                fname_templ = self.subtime_filename_templ
            else:
                fname_templ = self.default_subtime_fname_template

            # create a template with date and time specification
            dFormat = {self.datetimestart: '%Y%m%d', self.timestart: '%H%M%S'}
            fname_templ = fname_templ.format(**dFormat)

            if str_param is not None:
                fname_templ = fname_templ.format(**str_param)

        sub_path = ''
        if self.subpath_templ is not None:
            for s in self.subpath_templ:
                sub_path = os.path.join(sub_path, timestamp.strftime(s))

        search_file = os.path.join(self.path, sub_path,
                                   timestamp.strftime(fname_templ))
        if self.exact_templ:
            return [search_file]
        else:
            filename = glob.glob(search_file)

        if not filename:
            filename = []

        return filename

    def _parse_fname(self, fname):
        # get the parse result dictionary based on self.parse_fname_template
        return parse.parse(self.parse_fname_template,
                           os.path.basename(fname),)

    def _find_subtimes(self, timestamp):
        filenames = self._search_files(timestamp)
        # filenames = self._sort_subtimes(filenames)

        if len(filenames) == 0:
            raise IOError("No file found for {:}".format(timestamp.ctime()))

        subtimes = []
        for file in filenames:
            parsed = self._parse_fname(os.path.basename(file))
            subtime = datetime.strptime(
                parsed[self.datetimestart] + parsed[self.timestart],
                "%Y%m%d%H%M%S"
            )
            subtimes.append(subtime)

        return sorted(subtimes)

    def write_multiple(self, root_path, start_date, end_date, stackfile='stack.nc',
                       **kwargs):
        """
        Create multiple netcdf files or a netcdf stack in the passed directoy for
        a range of time stamps. Note that stacking gets slower when the stack gets larger.
        Empty images (if no original data can be loaded) are excluded here as
        well.

        Parameters
        ----------
        root : str
            Directory where the files / the stack are/is stored
        start_date : datetime
            Start date of images to write down
        end_date
            Last date of images to write down
        stackfile : str, optional (default: 'stack.nc')
            Name of the stack file to create in root_path. If no name is passed
            we create single images instead of a stack with the same name as
            the original images (faster).
        kwargs:
            kwargs that are passed to the image reading function
        """
        timestamps = self.tstamps_for_daterange(start_date, end_date)
        for t in timestamps:
            subtimes = self._find_subtimes(t)
            kwargs['timestamp'] = t

            for subt in subtimes:
                self.read(subt, **kwargs)
                if self.fid.image_missing:
                    continue
                if stackfile is None:
                    subdir = os.path.join(root_path, str(subt.year))
                    if not os.path.exists(subdir): os.makedirs(subdir)
                    filepath = os.path.join(subdir, os.path.basename(self.fid.filename))
                else:
                    filepath = os.path.join(root_path, stackfile)
                print(f"{'Write' if not stackfile else 'Stack'} image for {str(subt)}...")
                self.fid.write(filepath)
