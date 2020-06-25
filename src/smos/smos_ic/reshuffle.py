# -*- coding: utf-8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2019, TU Wien
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

"""
Module for a command line interface to convert the SMOS image data into a
time series format using the repurpose package
"""

import os
import sys
import argparse
from datetime import datetime

from repurpose.img2ts import Img2Ts
from smos.smos_ic.interface import SMOSImg, SMOSDs
from smos.grid import EASE25CellGrid
from netCDF4 import Dataset


def firstfile(input_root):
    '''
    Find the first file and read lat and lon and all variables

    Parameters
    --------
    input_root : str
        Path to the root dir of image files

    Returns
    --------
    firstfile : str
        Path to the first found image file in the input_root
    vars : list
        List of variables in the file
    '''

    for curr, subdirs, files in os.walk(input_root):
        for f in files:
            if len(f) > 0:
                firstfile = os.path.join(input_root, curr, f)
                ds = Dataset(firstfile)
                vars = ds.variables.keys()

                return firstfile, vars

    raise (IOError, 'No netcdf data found under the passed root directory')


def mkdate(datestring):
    """
    Create date string.
    Parameters
    ----------
    datestring : str
        Date string.
    Returns
    -------
    datestr : datetime
        Date string as datetime.
    """
    if len(datestring) == 10:
        return datetime.strptime(datestring, '%Y-%m-%d')
    if len(datestring) == 16:
        return datetime.strptime(datestring, '%Y-%m-%dT%H:%M')


def str2bool(val):
    if val in ['True', 'true', 't', 'T', '1']:
        return True
    else:
        return False


def reshuffle(input_root, outputpath,
              startdate, enddate,
              imgbuffer=200, **ds_kwargs):
    """
    Reshuffle method applied to SMOS image data.

    Parameters
    ----------
    input_root: string
        input path where smos ic data was downloaded to (yearly folders)
    outputpath : string
        Output path.
    startdate : datetime
        Start date.
    enddate : datetime
        End date.
    imgbuffer: int, optional
        How many images to read at once before writing time series.
    ds_kwargs: dict
        Kwargs that are passed to the image datastack class
    """

    ff, file_vars = firstfile(input_root)
    fp, ff = os.path.split(ff)

    if 'grid' not in ds_kwargs.keys():
        ds_kwargs['grid'] = EASE25CellGrid(None)
    if 'parameters' not in ds_kwargs.keys():
        ds_kwargs['parameters'] = None

    # this is only for reading the ts_attrs
    input_dataset = SMOSImg(filename=os.path.join(fp, ff),
                            parameters=ds_kwargs['parameters'], flatten=True, read_flags=None,
                            grid=ds_kwargs['grid'])
    _, ts_attributes = input_dataset._read_img()
    global_attr = input_dataset.get_global_attrs()

    if ds_kwargs['parameters'] is None:
        ds_kwargs['parameters'] = input_dataset.parameters

    input_dataset = SMOSDs(input_root, flatten=True, **ds_kwargs)

    if not os.path.exists(outputpath):
        os.makedirs(outputpath)

    # get time series attributes from first day of data.
    reshuffler = Img2Ts(input_dataset=input_dataset, outputpath=outputpath,
                        startdate=startdate, enddate=enddate,
                        input_grid=ds_kwargs['grid'].cut(),  # drop points that are not subset
                        imgbuffer=imgbuffer, cellsize_lat=5.0,
                        cellsize_lon=5.0, global_attr=global_attr, zlib=True,
                        unlim_chunksize=1000, ts_attributes=ts_attributes)
    reshuffler.calc()


def parse_args(args):
    """
    Parse command line parameters for recursive download.

    Parameters
    ----------
    args : list of str
        Command line parameters as list of strings.
    Returns
    -------
    args : argparse.Namespace
        Command line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Convert SMOS image data to time series format.")
    parser.add_argument("dataset_root",
                        help="Root of local filesystem where the "
                             "data is stored.")

    parser.add_argument("timeseries_root",
                        help="Root of local filesystem where the timeseries "
                             "should be stored.")

    parser.add_argument("start", type=mkdate,
                        help=("Startdate. Either in format YYYY-MM-DD or "
                              "YYYY-MM-DDTHH:MM."))

    parser.add_argument("end", type=mkdate,
                        help=("Enddate. Either in format YYYY-MM-DD or "
                              "YYYY-MM-DDTHH:MM."))

    parser.add_argument("--parameters", metavar="parameters", default=None,
                        nargs="+",
                        help=("Parameters to reshuffle into time series format. "
                              "e.g. Soil_Moisture. If this is not specified, all "
                              "variables in the image file will be reshuffled. "
                              "Default: None"))

    parser.add_argument("--only_good", type=str2bool, default='False',
                        help=("Use only observations with Quality_Flag 0 (GOOD), "
                              "if this is False, also 1-flagged (not recommended) "
                              "ones will be read and reshuffled, 2-flagged (missing)"
                              "values are always masked. Default: False"))

    parser.add_argument("--bbox", type=float, default=None, nargs=4,
                        help=("min_lon min_lat max_lon max_lat. "
                              "Bounding Box (lower left and upper right corner) "
                              "of subset area of global images to reshuffle (WGS84). "
                              "Default: None"))

    parser.add_argument("--imgbuffer", type=int, default=100,
                        help=("How many images to read at once. Bigger "
                              "numbers make the conversion faster but "
                              "consume more memory. Default: 100."))

    args = parser.parse_args(args)

    print(f"Converting SMOS IC data from {args.dataset_root} between "
          f"{args.start.isoformat()} and {args.end.isoformat()} "
          f"into folder {args.timeseries_root}. ")
    print(f"Masking to include only recommended values is "
          f"{'activated' if args.only_good else 'deactivated'}.")
    if args.bbox is not None:
        print(f"Bounding Box used: {str(args.bbox)}")

    return args


def main(args):
    """
    Main routine used for command line interface.
    Parameters
    ----------
    args : list of str
        Command line arguments.
    """
    args = parse_args(args)

    input_grid = EASE25CellGrid(bbox=tuple(args.bbox) if args.bbox is not None else None)

    flags = (0) if args.only_good else (0, 1)

    ds_kwargs = {'read_flags': flags, 'grid': input_grid,
                 'parameters': args.parameters}

    reshuffle(args.dataset_root,
              args.timeseries_root,
              args.start,
              args.end,
              imgbuffer=args.imgbuffer,
              **ds_kwargs)


def run():
    main(sys.argv[1:])
