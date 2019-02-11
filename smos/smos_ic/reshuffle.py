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
from smos.smos_ic.grid import EASE25CellGrid
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

    raise(IOError, 'No netcdf data found under the passed root directory')

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
              parameters=None, img_kwargs={},
              imgbuffer=50):
    """
    Reshuffle method applied to SMOS image data.
    Parameters
    ----------
    input_root: string
        input path where gldas data was downloaded
    outputpath : string
        Output path.
    startdate : datetime
        Start date.
    enddate : datetime
        End date.
    parameters: list
        parameters to read and convert
    img_kwargs: dict
        Kwargs that are passed to the image class
    imgbuffer: int, optional
        How many images to read at once before writing time series.
    """

    ff, file_vars = firstfile(input_root)
    fp, ff = os.path.split(ff)

    grid = EASE25CellGrid()

    if parameters is None:
        parameters = [p for p in file_vars if p not in ['lat', 'lon', 'time']]

    # this is only for reading the ts_attrs
    input_dataset = SMOSImg(os.path.join(fp, ff), parameters, grid=grid, flatten=True, **img_kwargs)
    data = input_dataset.read()
    ts_attributes = data.metadata
    ts_attributes = None # todo: fails for Quality_Flags

    input_dataset = SMOSDs(input_root, parameters, grid=grid, flatten=True,
                           **img_kwargs)

    if not os.path.exists(outputpath):
        os.makedirs(outputpath)

    global_attr = {'product': 'SMOS_IC'}

    # get time series attributes from first day of data.


    reshuffler = Img2Ts(input_dataset=input_dataset, outputpath=outputpath,
                        startdate=startdate, enddate=enddate, input_grid=grid,
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
                        help='Root of local filesystem where the '
                             'data is stored.')

    parser.add_argument("timeseries_root",
                        help='Root of local filesystem where the timeseries '
                             'should be stored.')

    parser.add_argument("start", type=mkdate,
                        help=("Startdate. Either in format YYYY-MM-DD or "
                              "YYYY-MM-DDTHH:MM."))

    parser.add_argument("end", type=mkdate,
                        help=("Enddate. Either in format YYYY-MM-DD or "
                              "YYYY-MM-DDTHH:MM."))

    parser.add_argument("--parameters", metavar="parameters", default=None,
                        nargs="+",
                        help=("Parameters to reshuffle into time series format. "
                              "e.g. Soil_Moisture if this is not specified, all "
                              "variables in the image file will be reshuffled"))

    parser.add_argument("--only_good", type=bool, default=True,
                        help=("Read only 0-flagged (GOOD) observations, "
                              "if this is False, also 1-flagged (not recommended) "
                              "ones will be read and reshuffled"))


    parser.add_argument("--imgbuffer", type=int, default=50,
                        help=("How many images to read at once. Bigger "
                              "numbers make the conversion faster but "
                              "consume more memory."))

    args = parser.parse_args(args)
    # set defaults that can not be handled by argparse

    print("Converting data from {} to"
          " {} into folder {}.".format(args.start.isoformat(),
                                      args.end.isoformat(),
                                      args.timeseries_root))

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

    reshuffle(args.dataset_root,
              args.timeseries_root,
              args.start,
              args.end,
              args.parameters,
              img_kwargs={'only_good': args.only_good},
              imgbuffer=args.imgbuffer)



def run():
    main(sys.argv[1:])

if __name__ == '__main__':
    '''    
    main([ds_root, ts_root, '2018-01-01', '2018-01-05', '--parameters', 'Soil_Moisture',
          'Days', 'Processing_Flags', 'Quality_Flag', 'RMSE', 'Scene_Flags', 'Soil_Moisture',
          'Soil_Moisture_StdError', 'Soil_Temperature_Level1', 'UTC_Microseconds', 'UTC_Seconds',
          '--only_good', False])
    '''