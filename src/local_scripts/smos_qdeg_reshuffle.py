# -*- coding: utf-8 -*-

"""
Module description
"""
# TODO:
#   (+) 
#---------
# NOTES:
#   -


from smos.smos_ic.reshuffle import reshuffle
from datetime import datetime
from smecv_grid import SMECV_Grid_v052

path = r"R:\Projects\CCIplus_Soil_Moisture\07_data\processed\smos_ic_resampled_quarter\ASC"
outpath = r"C:\Users\wpreimes\AppData\Local\Temp\tmpndff5tpg"
grid = SMECV_Grid_v052(None)
reshuffle(path, outputpath=outpath, startdate=datetime(2018,12,1), enddate=datetime(2019,1,31),
          parameters=['sm_resampled'], img_kwargs={'grid':grid, 'read_flags':(0)})