import numpy as np
from datetime import datetime
from smos_l4.interface import SMOSL4Img, SMOSL4Ds
from matplotlib import pyplot as plt

def TCDR():

    path = r"D:\DATA\SMOS_L4_RZSM\Raw\MIR_CLF4RD\2020\SM_SCIE_MIR_CLF4RD_20200212T000000_20200212T235959_301_001_9.DBL.nc"

    ds = SMOSL4Img(path, flatten=False, read_flags=None, oper=False)
    date = datetime(2020, 2, 10)
    smos_img = ds.read(date)

print("Bazinga!")

def ICDR():

    oper_path = r"D:\DATA\SMOS_L4_RZSM\Raw\MIR_CLFRD_OPER\2020\SM_OPER_MIR_CLF4RD_20200131T000000_20200131T235959_300_001_9.DBL.nc"

    ds = SMOSL4Img(oper_path, flatten=False, read_flags=None, oper=True)
    date = datetime(2020, 1, 13)
    smos_img = ds.read(date)

    plt.imshow(smos_img['RZSM'])

print("Bazinga!")

def MULTI_TCDR():

    path = r"D:\DATA\SMOS_L4_RZSM\Raw\MIR_CLF4RD"

    ds = SMOSL4Ds(path, flatten=False, oper=False)
    start_date = datetime(2015, 8, 1)
    end_date = datetime(2015, 8, 10)
    for date in SMOSL4Ds.tstamps_for_daterange(ds, start_date=start_date, end_date=end_date):
        smos_img = ds.read(date)
        plt.imshow(smos_img['RZSM'])
        plt.imshow(smos_img['QUAL'])

def MULTI_ICDR():

    path = r"D:\DATA\SMOS_L4_RZSM\Raw\MIR_CLF4RD_OPER"
    ds = SMOSL4Ds(path, flatten=False, oper=True)
    start_date = datetime(2020, 8, 1)
    end_date = datetime(2020, 8, 10)
    for date in SMOSL4Ds.tstamps_for_daterange(ds, start_date=start_date, end_date=end_date):

        smos_img = ds.read(date)
        plt.imshow(smos_img['RZSM'])
        plt.imshow(smos_img['Quality'])

print("Bazinga!")

