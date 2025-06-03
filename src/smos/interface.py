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
import warnings
import numpy as np
import pandas as pd

from pynetcf.time_series import GriddedNcOrthoMultiTs
from pygeogrids.netcdf import load_grid

from pygeobase.io_base import ImageBase, MultiTemporalImageBase
from pygeobase.object_base import Image
from datetime import timedelta, datetime
from netCDF4 import Dataset, date2num, num2date
from smos.grid import EASE25CellGrid
from smos import dist_name as subdist_name
from smos import dist_name, __version__
from collections import OrderedDict


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


class SMOSImg(ImageBase):
    """
    Class for reading one SMOS netcdf image file.

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

    def get_global_attrs(self, exclude=('history', 'NCO', 'netcdf_version_id', 'contact',
                                        'institution', 'creation_time')):
        return {k: v for k, v in self.glob_attrs.items() if k not in exclude}

    def _read_empty(self) -> (dict, dict):
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

        try:
            rows, cols = self.grid.subset_shape
        except AttributeError:
            rows, cols = self.grid.shape
        except ValueError:
            # Flat grid case
            rows = self.grid.subset_shape
            cols = None
        
        # Create shape based on grid type
        shape = rows if cols is None else (rows, cols)

        for param in self.parameters: 
            data = np.full(shape, np.nan)
            return_img[param] = data.flatten()
            return_metadata[param] = {'image_missing': 1}

        return return_img, return_metadata


    def _read_img(self) -> (dict, dict):
        raise NotImplementedError


    def read(self, timestamp):
        """
        Read a single SMOS image, if it exists, otherwise fill an empty image

        Parameters
        --------
        timestamp : datetime
            Time stamp for the image to read.
        """

        if timestamp is None:
            raise ValueError("No time stamp passed")

        try:
            return_img, return_metadata = self._read_img()
        except IOError:
            warnings.warn('Error loading image for {}, '
                          'generating empty image instead'.format(timestamp.date()))
            return_img, return_metadata = self._read_empty()

        if self.flatten:
            self.img = Image(self.grid.activearrlon, self.grid.activearrlat,
                             return_img, return_metadata, timestamp)

        else:
            try:
                shape = self.grid.subset_shape
            except AttributeError:
                shape = self.grid.shape

            rows, cols = shape
            for key in return_img:
                return_img[key] = np.flipud(return_img[key].reshape(rows, cols))

            self.img = Image(self.grid.activearrlon.reshape(rows, cols),
                             np.flipud(self.grid.activearrlat.reshape(rows, cols)),
                             return_img,
                             return_metadata,
                             timestamp)
        return self.img

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

        lons = np.unique(self.img.lon.flatten())
        lats = np.flipud(np.unique(self.img.lat.flatten()))

        mode = 'w' if not os.path.isfile(image) else 'a'
        ds = Dataset(image, mode=mode, **kwargs)

        ds.set_auto_scale(True)
        ds.set_auto_mask(True)

        units = 'Days since 2000-01-01 00:00:00'

        if mode == 'w':
            ds.createDimension('timestamp', None)  # stack dim
            ds.createDimension('lat', len(lats))
            ds.createDimension('lon', len(lons))

            # this is not the obs time, but an image time stamp
            ds.createVariable('timestamp', datatype=np.double, dimensions=('timestamp',),
                              zlib=True, chunksizes=None)
            ds.createVariable('lat', datatype='float64', dimensions=('lat',), zlib=True)
            ds.createVariable('lon', datatype='float64', dimensions=('lon',), zlib=True)

            ds.variables['timestamp'].setncatts({'long_name': 'timestamp',
                                                'units': units})
            ds.variables['lat'].setncatts({'long_name': 'latitude', 'units': 'Degrees_North',
                                           'valid_range': (-90, 90)})
            ds.variables['lon'].setncatts({'long_name': 'longitude', 'units': 'Degrees_East',
                                           'valid_range': (-180, 180)})

            ds.variables['lon'][:] = lons
            ds.variables['lat'][:] = lats
            ds.variables['timestamp'][:] = np.array([])

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
                ds.createVariable(var, vardata.dtype, dimensions=('timestamp', 'lat', 'lon'),
                                  zlib=True, complevel=6)
                ds.variables[var].setncatts(self.img.metadata[var])

            ds.variables[var][-1] = vardata

        ds.close()

    def read_masked_data(self, **kwargs):
        raise NotImplementedError

    def flush(self):
        pass

    def close(self):
        pass


class SMOSDs(MultiTemporalImageBase):
    """
    Class for reading SMOS images in nc format. Images are orgnaised in subdirs
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


    def __init__(self, data_path, ioclass, parameters=None, flatten=False,
                 grid=EASE25CellGrid(bbox=None), filename_templ=None,
                 read_flags=(0, 1), float_fillval=np.nan, additional_kws=None):

        ioclass_kws = {'parameters': parameters,
                       'flatten': flatten,
                       'grid': grid,
                       'read_flags': read_flags,
                       'float_fillval': float_fillval}

        if additional_kws:
            ioclass_kws.update(additional_kws)

        sub_path = ['%Y']

        super().__init__(data_path,
                         ioclass=ioclass,
                         fname_templ=filename_templ,
                         datetime_format="%Y%m%d",
                         subpath_templ=sub_path,
                         exact_templ=False,
                         ioclass_kws=ioclass_kws)

    def _assemble_img(self, timestamp, mask=False, **kwargs):
        img = None
        try:
            filepath = self._build_filename(timestamp)
        except IOError:
            filepath = None

        if self._open(filepath):
            kwargs['timestamp'] = timestamp
            if mask is False:
                img = self.fid.read(**kwargs)
            else:
                img = self.fid.read_masked_data(**kwargs)

        return img

    def read(self, timestamp, **kwargs):
        return self._assemble_img(timestamp, **kwargs)

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
            self.read(t, **kwargs)
            if self.fid.image_missing:
                continue
            if stackfile is None:
                subdir = os.path.join(root_path, str(t.year))
                if not os.path.exists(subdir): os.makedirs(subdir)
                filepath = os.path.join(subdir, os.path.basename(self.fid.filename))
            else:
                filepath = os.path.join(root_path, stackfile)
            print(f"{'Write' if not stackfile else 'Stack'} image for {str(t)}...")
            self.fid.write(filepath)

    def tstamps_for_daterange(self, start_date, end_date):
        """
        return timestamps for daterange,
        Parameters
        ----------
        start_date: datetime.datetime
            start of date range
        end_date: datetime.datetime
            end of date range
        Returns
        -------
        timestamps : list
            list of datetime objects of each available image between
            start_date and end_date
        """
        img_offsets = np.array([timedelta(hours=0)])

        timestamps = []
        diff = end_date - start_date
        for i in range(diff.days + 1):
            daily_dates = start_date + timedelta(days=i) + img_offsets
            timestamps.extend(daily_dates.tolist())

        return timestamps
