# -*- coding: utf-8 -*-

'''
Module description
'''
# TODO # (+) 

# NOTES # -

from smos.smos_ic.reshuffle import main

ds_root = r'R:\Datapool_raw\SMOS\datasets\L3_SMOS_IC_Soil_Moisture\ASC'
ts_root = r'C:\Temp\SMOS_TS\ASC'
main([ds_root, ts_root, '2017-01-01', '2017-02-28', '--parameters', 'Soil_Moisture',
      'Days', 'Processing_Flags', 'Quality_Flag', 'RMSE', 'Scene_Flags', 'Soil_Moisture',
      'Soil_Moisture_StdError', 'Soil_Temperature_Level1', 'UTC_Microseconds', 'UTC_Seconds',
      '--only_good', False, 'imgbuffer', 500])
