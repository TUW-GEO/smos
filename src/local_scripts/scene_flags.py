# -*- coding: utf-8 -*-

'''
Module description
'''
# TODO # (+) 

# NOTES # -

from smos.smos_ic.interface import SMOSTs

path = r"R:\Datapool_processed\SMOS\L3_SMOS_IC_Soil_Moisture\smos_asc_ts"

ds = SMOSTs(path)

ts = ds.read(80., 53.)

ts.loc['2017-02-09', 'Scene_flags']

