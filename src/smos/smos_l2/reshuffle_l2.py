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
Module for a command line interface to convert the SMOS L2 image data into a
time series format using the repurpose package
"""
import logging
import os
import sys
from datetime import datetime

import numpy as np
from repurpose.img2ts import Img2Ts, Img2TsError
from smos.smos_l2.interface_l2 import SMOS_L2_Img, SMOS_L2_Ds
from smos.grid import ISEA4h9CellGrid
from smos.reshuffle import firstfile, mkdate, str2bool, parse_args
import repurpose.resample as resamp


class Img2TSs_SMOSL2(Img2Ts):
    """ Adaptation of read_bulk method for SMOS L2"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def img_bulk(self):
        """
        Adaptation of img2ts.Img2Ts.img_bulk for SMOS L2
        with sub-daily timestamps
        """
        img_dict = {}
        datetimes = []
        jd_list = []
        # set start of current imgbulk to startdate
        bulkstart = self.startdate
        # image counter
        read_images = 0

        dates = self.imgin.tstamps_for_daterange(self.startdate,
                                                 self.enddate)
        for date in dates:
            # Adaptation for subtimes
            subtimes = self.imgin._find_subtimes(date)

            for subt in subtimes:
                try:
                    (input_img, metadata,
                     image_datetime, lon,
                     lat, time_arr) = self.imgin.read(subt, **self.input_kwargs)
                except IOError as e:
                    msg = "I/O error({0}): {1}".format(e.errno,
                                                       e.strerror)
                    logging.log(logging.INFO, msg)
                    continue
                read_images += 1
                logging.log(logging.INFO, "read" + image_datetime.isoformat())
                if self.resample:

                    if time_arr is not None:
                        input_img['jd'] = time_arr
                    input_img = resamp.resample_to_grid(input_img, lon, lat,
                                                        self.target_grid.activearrlon,
                                                        self.target_grid.activearrlat,
                                                        methods=self.r_methods,
                                                        weight_funcs=self.r_weightf,
                                                        min_neighbours=self.r_min_n,
                                                        search_rad=self.r_radius,
                                                        neighbours=self.r_neigh,
                                                        fill_values=self.r_fill_values)
                    time_arr = input_img.pop('jd')
                if time_arr is None:
                    self.time_var = None

                else:
                    self.time_var = 'jd'
                if time_arr is not None:
                    # if time_var is not None means that each observation of the
                    # image has its own observation time
                    # this means that the resulting time series is not
                    # regularly spaced in time
                    if self.orthogonal is None:
                        self.orthogonal = False
                    if self.orthogonal:
                        raise Img2TsError("Images can not switch between a fixed image "
                                          "timestamp and individual timestamps for each observation")
                    jd_list.append(time_arr)
                if time_arr is None:
                    if self.orthogonal is None:
                        self.orthogonal = True
                    if not self.orthogonal:
                        raise Img2TsError(
                            "Images can not switch between a fixed image "
                            "timestamp and individual timestamps for each observation")

                for key in input_img:
                    if key not in img_dict.keys():
                        img_dict[key] = []
                    img_dict[key].append(input_img[key])

                datetimes.append(image_datetime)

                if read_images >= self.imgbuffer - 1:
                    img_stack_dict = {}
                    if len(jd_list) != 0:
                        jd_stack = np.ma.vstack(jd_list)
                        jd_list = None
                    else:
                        jd_stack = None
                    for key in img_dict:
                        img_stack_dict[key] = np.vstack(img_dict[key])
                        img_dict[key] = None
                    datetimestack = np.array(datetimes)
                    img_dict = {}
                    datetimes = []
                    jd_list = []
                    yield (img_stack_dict, bulkstart, self.currentdate,
                           datetimestack, jd_stack)
                    # reset image counter
                    read_images = 0

        if len(datetimes) > 0:
            img_stack_dict = {}
            if len(jd_list) != 0:
                jd_stack = np.ma.vstack(jd_list)
            else:
                jd_stack = None
            for key in img_dict:
                img_stack_dict[key] = np.vstack(img_dict[key])
                img_dict[key] = None
            datetimestack = np.array(datetimes)
            yield (img_stack_dict, bulkstart, self.currentdate, datetimestack,
                   jd_stack)


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
        ds_kwargs['grid'] = ISEA4h9CellGrid()
    if 'parameters' not in ds_kwargs.keys():
        ds_kwargs['parameters'] = None

    # this is only for reading the ts_attrs
    input_dataset = SMOS_L2_Img(
        filename=os.path.join(fp, ff),
        parameters=ds_kwargs['parameters'],
        flatten=True,
        read_flags=None,
        grid=ds_kwargs['grid']
    )
    _, ts_attributes = input_dataset._read_img()
    global_attr = input_dataset.get_global_attrs()

    if ds_kwargs['parameters'] is None:
        ds_kwargs['parameters'] = input_dataset.parameters

    input_dataset = SMOS_L2_Ds(input_root, flatten=True, **ds_kwargs)

    if not os.path.exists(outputpath):
        os.makedirs(outputpath)

    # get time series attributes from first day of data.
    reshuffler = Img2TSs_SMOSL2(
        input_dataset=input_dataset, outputpath=outputpath,
        startdate=startdate, enddate=enddate,
        input_grid=ds_kwargs['grid'].cut(),
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

    input_grid = ISEA4h9CellGrid()

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


if __name__ == "__main__":
    run()
