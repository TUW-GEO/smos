Write (subset) images
=====================

To write down an image to a new file (e.g. after filtering certain parameters or
to create spatial subset files) you can use the functions ``SMOS_IC_Img.write``. This
will create a new netcdf file with the content of the current image at a selected location.

.. code-block:: python

   from smos.smos_ic.interface_ic import SMOS_IC_Img
   from smos.grid import EASE25CellGrid
   import matplotlib.pyplot as plt
   from datetime import datetime
   import os
   # path to the cloned test data repository, see section "Test data"
   testdata_path = '/path/to/smos-test-data'

   fname = os.path.join(testdata_path, 'L3_SMOS_IC', 'ASC', '2018',
                        'SM_RE06_MIR_CDF3SA_20180101T000000_20180101T235959_106_001_8.DBL.nc')

   # bbox_order : (min_lon, min_lat, max_lon, max_lat)
   subgrid_eu = EASE25CellGrid(bbox=(-11., 34., 43., 71.))

   img = SMOS_IC_Img(fname, parameters=['Soil_Moisture', 'Scene_Flags', 'Days', 'UTC_Seconds'],
                       grid=subgrid_eu)

   img.read(datetime(2018,1,1))

   img.write('/tmp/smos_write/subset_image.nc')

Finally, you can also write down multiple files using the write function from
``SMOS_IC_Ds``. You can either create single files per time stamp (like the original data is)
or netcdf stacks. This example will do both (note that days when no data is loaded are
also skipped when writing the subset).

.. code-block:: python

   from smos.smos_ic.interface_ic import SMOS_IC_Ds
   from smos.grid import EASE25CellGrid
   import matplotlib.pyplot as plt
   from datetime import datetime
   import os
   # path to the cloned test data repository, see section "Test data"
   testdata_path = '/path/to/smos-test-data'

   path = os.path.join(testdata_path, 'L3_SMOS_IC', 'ASC')

   # bbox_order : (min_lon, min_lat, max_lon, max_lat)
   subgrid_eu = EASE25CellGrid(bbox=(-11., 34., 43., 71.))

   ds = SMOS_IC_Ds(path, parameters=['Soil_Moisture', 'Scene_Flags', 'Days', 'UTC_Seconds'],
                    grid=subgrid_eu)

   # write data as single files
   ds.write_multiple('/tmp/smos_write/single', start_date=datetime(2018,1,1), end_date=datetime(2018,1,3),
                     stackfile=None)

   # write data as a stack
   ds.write_multiple('/tmp/smos_write/stack', stackfile='stack.nc', start_date=datetime(2018,1,1),
                     end_date=datetime(2018,1,3))