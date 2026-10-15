Variable naming for different versions of SMOS
====================================================
 
This is a full list of all available variables in each image. These parameters
can be passed to the repurpose routine to create time series.

* L3 SMOS IC (v106)

Note: Version 105 files additionally contained the variables ``Quality_Flag``
(0: data OK, 1: data not recommended, 2: missing data) and ``Processing_Flags``
(1: RMSE > 12 K), but no ``Skin_Temperature_ECMWF``.

+--------------------------+------------------------------------------------------+-----------------------+
| Parameter                | Long Name                                            | Units                 |
+==========================+======================================================+=======================+
| Days                     | Number of Days since 1/1/2000                        |                       |
+--------------------------+------------------------------------------------------+-----------------------+
| RMSE                     | RMSE TBmeas. TB modeled                              |                       |
+--------------------------+------------------------------------------------------+-----------------------+
| Scene_Flags              | Scene Flags (bits: 1 moderate topo, 2 strong topo,   |                       |
|                          | 4 polluted scene, 8 frozen scene)                    |                       |
+--------------------------+------------------------------------------------------+-----------------------+
| Skin_Temperature_ECMWF   | ECMWF Skin Temperature                               | Kelvin                |
+--------------------------+------------------------------------------------------+-----------------------+
| Soil_Moisture            | Soil Moisture                                        | m :sup:`3` m :sup:`-3`|
+--------------------------+------------------------------------------------------+-----------------------+
| Soil_Moisture_StdError   | Soil Moisture standard error                         | m :sup:`3` m :sup:`-3`|
+--------------------------+------------------------------------------------------+-----------------------+
| Soil_Temperature_Level1  | ECMWF Soil Temperature at surface level 1            | Kelvin                |
+--------------------------+------------------------------------------------------+-----------------------+
| UTC_Microseconds         | Microseconds                                         | micros.               |
+--------------------------+------------------------------------------------------+-----------------------+
| UTC_Seconds              | Number of Seconds                                    | s                     |
+--------------------------+------------------------------------------------------+-----------------------+

* L3 SMOS SM daily (CLF3S)

Other L3 products (CLF31, CLF33, CLF3E, CLF3D, CLF3M) contain different
variables, see the CATDS product documentation. Variables with a third dimension
are split by the reader (suffix ``_re``/``_im`` or ``_med``/``_min``/``_max``).

+----------------------------+------------------------------------------------------+-----------------------+
| Parameter                  | Long Name                                            | Units                 |
+============================+======================================================+=======================+
| Mean_Acq_Time_Days         | Day of mean acquisition time (since 2000-01-01)      | d                     |
+----------------------------+------------------------------------------------------+-----------------------+
| Mean_Acq_Time_Seconds      | Seconds of mean acquisition time (of the day)        | s                     |
+----------------------------+------------------------------------------------------+-----------------------+
| Soil_Moisture              | Retrieved soil moisture value                        | m :sup:`3` m :sup:`-3`|
+----------------------------+------------------------------------------------------+-----------------------+
| Soil_Moisture_Dqx          | DQX of retrieved soil moisture value                 | m :sup:`3` m :sup:`-3`|
+----------------------------+------------------------------------------------------+-----------------------+
| Optical_Thickness_Nad      | Nadir optical thickness of vegetation layer          | neper                 |
+----------------------------+------------------------------------------------------+-----------------------+
| Optical_Thickness_Nad_Dqx  | DQX of Optical_Thickness_Nad                         | neper                 |
+----------------------------+------------------------------------------------------+-----------------------+
| Chi_2                      | Retrieval fit quality index                          |                       |
+----------------------------+------------------------------------------------------+-----------------------+
| Chi_2_P                    | X2 high value acceptability probability              |                       |
+----------------------------+------------------------------------------------------+-----------------------+
| Number_Degrees_Freedom     | Number of degrees of freedom                         |                       |
+----------------------------+------------------------------------------------------+-----------------------+
| M_Ava                      | Number of TB measurements available                  |                       |
+----------------------------+------------------------------------------------------+-----------------------+
| Ratio_RFI                  | RFI probability counted over the three orbits        |                       |
+----------------------------+------------------------------------------------------+-----------------------+
| Science_Flags              | Science Flags                                        |                       |
+----------------------------+------------------------------------------------------+-----------------------+
| Mean_FM0_FNO               | Mean cover fraction for FNO                          | %                     |
+----------------------------+------------------------------------------------------+-----------------------+
| Mean_FM0_FFO               | Mean cover fraction for FFO                          | %                     |
+----------------------------+------------------------------------------------------+-----------------------+
| Rfi_Prob                   | Probability to have RFI (from current file)          |                       |
+----------------------------+------------------------------------------------------+-----------------------+

* L4 SMOS RZSM SM_SCIE_MIR_CLF4RD

+--------------------------+------------------------------------------------------+-----------------------+
| Parameter                | Long Name                                            | Units                 |
+==========================+======================================================+=======================+
| QUAL                     | Quality index 1.0 highest quality                    |                       |
+--------------------------+------------------------------------------------------+-----------------------+
| RZSM                     | Root Zone Soil Moisture                              | m3/m3                 |
+--------------------------+------------------------------------------------------+-----------------------+

* L4 SMOS RZSM SM_OPER_MIR_CLF4RD

+--------------------------+------------------------------------------------------+-----------------------+
| Parameter                | Long Name                                            | Units                 |
+==========================+======================================================+=======================+
| Quality                  | -1: missing data, 0: data not recommended, 1: data OK|                       |
+--------------------------+------------------------------------------------------+-----------------------+

Note that the ``long_name`` attribute of ``Quality`` in the operational files
("0: data OK, 1: data not recommended, 2: missing data") does not match the
values in the files (-1, 0, 1). The meaning above is consistent with the
scientific product (the share of values with ``Quality`` = 1 matches the share
of ``QUAL`` = 1).
| RZSM                     | Retrieved Root Zone Soil Moisture                    | m3/m3                 |
+--------------------------+------------------------------------------------------+-----------------------+

