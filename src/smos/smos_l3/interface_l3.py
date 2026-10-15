# -*- coding: utf-8 -*-
"""
Readers for SMOS L3 SM (CATDS) images and the time series created from them.

All L3 products are provided on the global EASE2 25 km grid (same as SMOS IC).
Variables with an additional third dimension (e.g. the real and imaginary
part of the dielectric constant, or median, min and max values in the 10-day
product) are split into separate variables, e.g. Soil_Moisture_med,
Soil_Moisture_min and Soil_Moisture_max.
"""

import os
import re
from datetime import datetime, timedelta
import numpy as np
from netCDF4 import Dataset
from smos.grid import EASE25CellGrid
from smos.interface import SMOSImg, SMOSDs, SMOSTs, LatestVersionMixin
from smos.smos_l3.download import L3_PRODUCTS

# Names for the elements of known third dimensions in the L3 files
_dim_suffixes = {
    'd_reim': ('re', 'im'),
    'med_min_max': ('med', 'min', 'max'),
}

# Attributes that don't apply anymore after reading (data is unpacked)
_drop_attrs = ('scale_factor', 'add_offset')


def _split_suffix(name):
    # Base name of a variable with a suffix for the third dimension
    # (e.g. Soil_Moisture_med -> Soil_Moisture), None for other variables
    base, _, suffix = name.rpartition('_')
    known = [s for suffixes in _dim_suffixes.values() for s in suffixes]
    return base if (suffix in known or suffix.isdigit()) and base else None


class SMOS_L3_Img(SMOSImg):
    """
    Class for reading one SMOS L3 netcdf image file.

    Parameters
    ----------
    filename: str
        filename of the SMOS L3 .DBL.nc image file
    mode: str, optional (default: 'r')
        mode of opening the file, only 'r' is implemented at the moment
    parameters : str or list, optional (default: None)
        one or list of parameters to read. If None are passed, all
        variables on the (lat, lon) grid are read. Variables with a third
        dimension can be passed either with suffix (e.g. 'Soil_Moisture_med')
        or without (e.g. 'Soil_Moisture'), then all elements are read.
    flatten: bool, optional (default: False)
        If set then the data is read into 1D arrays. This is used to e.g
        reshuffle the data.
    grid : pygeogrids.CellGrid, optional (default: EASE25CellGrid)
        Grid that the image data is organised on, by default the global EASE25
        grid is used.
    float_fillval : float or None, optional (default: np.nan)
        Fill Value for masked pixels, this is only applied to float variables.
        Therefore e.g. flag variables are never filled but use the fill value
        as in the data.
    empty_template : dict, optional (default: None)
        Variable name -> (dtype, fill value), as returned by
        `variable_template`. Used to create empty images (if the file is
        missing) with the correct data types (see `SMOSImg`).
    """

    def __init__(self,
                 filename,
                 mode='r',
                 parameters=None,
                 flatten=False,
                 grid=EASE25CellGrid(bbox=None),
                 float_fillval=np.nan,
                 empty_template=None):

        super().__init__(
            filename,
            mode=mode,
            parameters=parameters,
            flatten=flatten,
            grid=grid,
            read_flags=None,
            float_fillval=float_fillval,
            empty_template=empty_template)

    @staticmethod
    def available_variables(ds) -> dict:
        """
        All variables on the (lat, lon) grid in the passed (open) netcdf file.

        Returns
        -------
        variables: dict
            Variable name (as returned by the reader) -> (name in file, index
            in third dimension or None)
        """
        variables = {}
        for name, var in ds.variables.items():
            if var.dimensions[:2] != ('lat', 'lon'):
                continue
            if var.ndim == 2:
                variables[name] = (name, None)
            elif var.ndim == 3:
                dim = var.dimensions[2]
                suffixes = _dim_suffixes.get(
                    dim, [str(i) for i in range(len(ds.dimensions[dim]))])
                for i, suffix in enumerate(suffixes):
                    variables[f"{name}_{suffix}"] = (name, i)
        return variables

    def _expand_parameters(self, available) -> list:
        # Resolve the selected parameters to the names returned by the
        # reader, i.e. add suffixes for variables with a third dimension.
        # available is a list of all variable names (with suffix)
        if len(self.parameters) == 0:
            return list(available)
        parameters = []
        for p in self.parameters:
            if p in available:
                parameters.append(p)
            else:
                expanded = [
                    k for k in available
                    if _split_suffix(k) == p and k not in self.parameters
                ]
                if len(expanded) == 0:
                    raise ValueError(
                        f"Parameter {p} not found in {self.filename}. "
                        f"Available: {list(available)}")
                parameters += expanded
        return parameters

    def _read_empty(self) -> (dict, dict):
        # Empty image, with the data types from the template (if available)
        if self.empty_template is not None:
            self.parameters = self._expand_parameters(
                list(self.empty_template.keys()))
        return super()._read_empty()

    def _read_img(self) -> (dict, dict):
        # Read a netcdf image and metadata
        ds = Dataset(self.filename)
        self.glob_attrs = ds.__dict__

        available = self.available_variables(ds)

        try:
            parameters = self._expand_parameters(list(available.keys()))
        except ValueError:
            ds.close()
            raise
        self.parameters = parameters

        param_img = {}
        param_meta = {}

        for parameter in parameters:
            name, idx = available[parameter]
            var = ds.variables[name]
            data = var[:] if idx is None else var[:, :, idx]

            metadata = {
                attr: var.getncattr(attr)
                for attr in var.ncattrs()
                if attr not in _drop_attrs
            }
            if idx is not None and 'long_name' in metadata:
                metadata['long_name'] = \
                    f"{metadata['long_name']} ({parameter.split('_')[-1]})"

            # keep the _FillValue mask (int vars) and mask NaNs (float vars)
            data = np.ma.masked_array(
                data, mask=np.ma.getmaskarray(data) | ~np.isfinite(data))

            if issubclass(data.dtype.type, np.floating):
                # packed values are unpacked to float, original fill value
                # does not apply anymore
                metadata.pop('_FillValue', None)
                if self.float_fillval is not None:
                    data = data.filled(fill_value=self.float_fillval)

            metadata['image_missing'] = 0

            param_img[parameter] = data.flatten()[self.grid.activegpis]
            param_meta[parameter] = metadata

        ds.close()

        return param_img, param_meta


class SMOS_L3_Ds(LatestVersionMixin, SMOSDs):
    """
    Class for reading SMOS L3 images of one product and orbit, as downloaded
    with `smos.smos_l3.download.SmosL3Ftp`, i.e. organised in
    <data_path>/<YYYY>/<DOY or MM>/ folders.

    If files from multiple campaigns are available for a date (e.g. RE07 and
    OPER), the one with the highest version (and file counter) is used.

    Parameters
    ----------
    data_path : str
        Path to the product folder, e.g. /path/to/MIR_CLF3SA
    product: str, optional (default: None)
        L3 product, e.g. 'CLF3S'. If None is passed, the product is derived
        from the name of the data_path folder.
    orbit: str, optional (default: None)
        'A' (ascending) or 'D' (descending). If None is passed, the orbit is
        derived from the name of the data_path folder.
    parameters : str or list, optional (default: None)
        one or list of parameters to read. See `SMOS_L3_Img`.
    flatten: bool, optional (default: False)
        If set then the data is read into 1D arrays. This is used to e.g
        reshuffle the data.
    grid : pygeogrids.CellGrid, optional (default: EASE25CellGrid)
        Grid that the image data is organised on, by default the global EASE25
        grid is used.
    version: int or str, optional (default: None)
        Product version (e.g. 339) to read. If None is passed, any
        version is accepted (the latest one is used if there are multiple).
    float_fillval : float or None, optional (default: np.nan)
        Fill Value for masked pixels, this is only applied to float variables.
    """

    def __init__(self,
                 data_path,
                 product=None,
                 orbit=None,
                 parameters=None,
                 flatten=False,
                 grid=EASE25CellGrid(bbox=None),
                 version=None,
                 float_fillval=np.nan):

        if (product is None) or (orbit is None):
            m = re.match(r"^MIR_(CLF3.)([AD])$",
                         os.path.basename(os.path.normpath(data_path)))
            if m is None:
                raise ValueError(
                    f"Could not derive product and orbit from {data_path}. "
                    f"Pass them explicitly or use the folder structure from "
                    f"the download (e.g. MIR_CLF3SA).")
            product = m.group(1) if product is None else product
            orbit = m.group(2) if orbit is None else orbit

        self.product = product.upper().replace('MIR_', '')
        if self.product not in L3_PRODUCTS:
            raise ValueError(f"Unknown product {product}, choose from "
                             f"{list(L3_PRODUCTS.keys())}")
        self.orbit = orbit.upper()[0]
        folder_type, self.temp_res = L3_PRODUCTS[self.product]

        version = '*' if version is None else f"{int(version):03}"
        filename_templ = (f"SM_*_MIR_{self.product}{self.orbit}_"
                          f"{{datetime}}T000000_*_{version}_*_*.DBL.nc")

        super().__init__(
            data_path,
            ioclass=SMOS_L3_Img,
            parameters=parameters,
            flatten=flatten,
            grid=grid,
            filename_templ=filename_templ,
            read_flags=None,
            float_fillval=float_fillval,
            subpath_templ=('%Y', '%j' if folder_type == 'doy' else '%m'))
        # no quality flags in SMOS L3, not passed to the image class
        self.ioclass_kws.pop('read_flags')

    def _first_file(self, data_path):
        # Find the first image file of this product and orbit in data_path
        pattern = re.compile(
            rf"^SM_.*_MIR_{self.product}{self.orbit}_.*\.DBL\.nc$")
        for root, dirs, files in os.walk(data_path):
            dirs.sort()
            for f in sorted(files):
                if pattern.match(f):
                    return os.path.join(root, f)
        return None

    def tstamps_for_daterange(self, start_date, end_date):
        """
        Image time stamps between start_date and end_date, depending on the
        temporal resolution of the product: every day for daily (and 3-day
        running) products, the 1st, 11th and 21st of each month for the
        10-day product and the 1st of each month for the monthly product.

        Parameters
        ----------
        start_date: datetime
            start of date range
        end_date: datetime
            end of date range

        Returns
        -------
        timestamps : list
            list of datetime objects of each image between start_date and
            end_date
        """
        start = datetime(start_date.year, start_date.month, start_date.day)
        days = []
        d = start
        while d <= end_date:
            days.append(d)
            d += timedelta(days=1)

        if self.temp_res == 'dekad':
            days = [d for d in days if d.day in (1, 11, 21)]
        elif self.temp_res == 'monthly':
            days = [d for d in days if d.day == 1]

        return days


class SMOSL3Ts(SMOSTs):
    """
    Class for reading SMOS L3 time series after reshuffling images.
    Same as `smos.interface.SMOSTs`, but uses the L3 variables
    'Mean_Acq_Time_Days' and 'Mean_Acq_Time_Seconds' to add the observation
    time to the index (if index_add_time=True).
    """

    _t0_vars = {'sec': 'Mean_Acq_Time_Seconds', 'days': 'Mean_Acq_Time_Days'}
    _t0_unit = 'days since 2000-01-01'
