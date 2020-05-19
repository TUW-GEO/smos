# -*- coding: utf-8 -*-

"""
Module description
"""
# TODO:
#   (+) 
#---------
# NOTES:
#   -


from smecv_grid import SMECV_Grid_v052
from smos.smos_ic.interface import SMOSImg
import matplotlib .pyplot as plt


# read one of the original files, also read the non-good values
smos_img = r"R:\Datapool_raw\SMOS\datasets\L3_SMOS_IC_Soil_Moisture\ASC\2014\SM_RE06_MIR_CDF3SA_20140107T000000_20140107T235959_105_001_8.DBL.nc"
reader = SMOSImg(filename=smos_img, read_flags=(0,1), parameters=['Soil_Moisture'])
image = reader.read()

fig1, ax1 = plt.subplots()
ax1.imshow(image.data['Soil_Moisture'])



# read one of the original files, only read the good values
smos_img = r"R:\Datapool_raw\SMOS\datasets\L3_SMOS_IC_Soil_Moisture\ASC\2014\SM_RE06_MIR_CDF3SA_20140107T000000_20140107T235959_105_001_8.DBL.nc"
reader = SMOSImg(filename=smos_img, read_flags=(0), parameters=['Soil_Moisture'])
image = reader.read()

fig2, ax2 = plt.subplots()
ax2.imshow(image['Soil_Moisture'])


# read one of the resampled files
grid = SMECV_Grid_v052(None)
smos_img = r"R:\Projects\CCIplus_Soil_Moisture\07_data\processed\smos_ic_resampled_quarter\ASC\2016\SMOS_IC_CCI_GRID_20160103T000000.nc"
reader = SMOSImg(filename=smos_img, read_flags=None, grid=grid, parameters=['smos_sm_resampled'])
image = reader.read()
fig3, ax3 = plt.subplots()
ax3.imshow(image['smos_sm_resampled'])


##############################################################################
# reshuffle the resampled files
from smos.smos_ic.reshuffle import reshuffle
from datetime import datetime
import tempfile
from pygeogrids.grids import BasicGrid

input_root = r"R:\Projects\CCIplus_Soil_Moisture\07_data\processed\smos_ic_resampled_quarter\ASC"
outputpath = tempfile.mkdtemp()
startdate, enddate = datetime(2017,12,1), datetime(2018,1,31)
gpis, lons, lats, cells = SMECV_Grid_v052(None).get_grid_points()
cci_grid = BasicGrid(lons.filled(), lats.filled(), gpis.filled()).to_cell_grid(5.)

ds_kwargs = {'grid':cci_grid, 'read_flags': None,
            'filename_templ':'SMOS_IC_CCI_GRID_{datetime}T000000.nc'}
reshuffle(input_root, outputpath,
              startdate, enddate, parameters=['smos_sm_resampled'],
              ds_kwargs=ds_kwargs,
              imgbuffer=50)

# read the time series
from smos.smos_ic.interface import SMOSTs
ds = SMOSTs(outputpath)
time_series = ds.read(-72,-4.821).dropna()
print(time_series)
