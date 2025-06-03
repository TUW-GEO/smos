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

"""
Module for a command line interface to convert the SMOS image data into a
time series format using the repurpose package
"""

import os
import sys
from datetime import datetime

from repurpose.img2ts import Img2Ts
from smos.smos_l4.interface_l4 import SMOS_L4_Img, SMOS_L4_Ds
from smos.grid import EASE25CellGrid
from smos.reshuffle import firstfile, mkdate, str2bool, parse_args


def reshuffle(input_root, outputpath,
              startdate, enddate,
              imgbuffer=200, **ds_kwargs):
    """
    Reshuffle method applied to SMOS image data.

    Parameters
    ----------
    input_root: string
        input path where smos L4 data was downloaded to (yearly folders)
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
    input_dataset = SMOS_L4_Img(filename=os.path.join(fp, ff),
                            parameters=ds_kwargs['parameters'], flatten=True, read_flags=None,
                            grid=ds_kwargs['grid'], oper=ds_kwargs['oper'] if 'oper' in ds_kwargs else False)
    _, ts_attributes = input_dataset._read_img()
    global_attr = input_dataset.get_global_attrs()

    if ds_kwargs['parameters'] is None:
        ds_kwargs['parameters'] = input_dataset.parameters

    input_dataset = SMOS_L4_Ds(input_root, flatten=True, **ds_kwargs)

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


def main(args):
    """
    Main routine used for command line interface.
    Parameters
    ----------
    args : list of str
        Command line arguments.
    """
    args = parse_args(args)

    input_grid = EASE25CellGrid(bbox=tuple(args.bbox) if args.bbox is not None else None,
                               only_land=args.only_land)

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