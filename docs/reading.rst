Reading images
==============

`L3_SMOS_IC <https://www.catds.fr/Products/Available-products-from-CEC-SM/SMOS-IC>`_
------------------------------------------

After downloading the data you will have a directory with subpaths of the format
``YYYY``. Let's call this path ``root_path``. To read 'Soil_Moisture'
data for a certain date use the following code:

.. code-block:: python

   from smos.smos_ic.interface import SMOSDs
   import matplotlib.pyplot as plt
   from datetime import datetime
   import os
   # make sure to clone testdata submodule from https://github.com/TUW-GEO/smos
   from smos import testdata_path


   root_path = os.path.join(testdata_path, 'L3_SMOS_IC', 'ASC')
   ds = SMOSDs(root_path, parameters='Soil_Moisture')
   image = ds.read(datetime(2018, 1, 1))
   assert list(image.data.keys()) == ['Soil_Moisture']
   sm_data = image.data['Soil_Moisture']

   plt.imshow(sm_data)
   plt.show()

The returned image is of the type `pygeobase.Image
<http://pygeobase.readthedocs.io/en/latest/api/pygeobase.html#pygeobase.object_base.Image>`_.
Which is only a small wrapper around a dictionary of numpy arrays.

If you only have a single image you can also read the data directly by specifying
the file. Here we ignore any "Quality_Flag" values and simply read all data from file.

.. code-block:: python

   from smos.smos_ic.interface import SMOSImg
   import matplotlib.pyplot as plt
   from datetime import datetime
   import os
   # make sure to clone testdata submodule from https://github.com/TUW-GEO/smos
   from smos import testdata_path

   fname = os.path.join(testdata_path, 'L3_SMOS_IC', 'ASC', '2018',
                        'SM_RE06_MIR_CDF3SA_20180101T000000_20180101T235959_105_001_8.DBL.nc')
   img = SMOSImg(fname, read_flags=None)

   image = img.read(datetime(2018,1,1))
   sm_data = image.data['Soil_Moisture']

   plt.imshow(sm_data)
   plt.show()


You can also limit the reading to certain variables or a spatial subset by
defining a bounding box area.
In the following example, we read SMOS IC Soil Moisture over Europe only,
and mask the data based on the "Quality_Flag" variable, to only include 0-flagged
(i.e. "good") values.

.. code-block:: python

   from smos.smos_ic.interface import SMOSImg
   from smos.grid import EASE25CellGrid
   import matplotlib.pyplot as plt
   from datetime import datetime
   import os
   # make sure to clone testdata submodule from https://github.com/TUW-GEO/smos
   from smos import testdata_path

   fname = os.path.join(testdata_path, 'L3_SMOS_IC', 'ASC', '2018',
                        'SM_RE06_MIR_CDF3SA_20180101T000000_20180101T235959_105_001_8.DBL.nc')

   # bbox_order : (min_lon, min_lat, max_lon, max_lat)
   subgrid_eu = EASE25CellGrid(bbox=(-11., 34., 43., 71.))

   img = SMOSImg(fname, parameters=['Soil_Moisture', 'Quality_Flag', 'Days', 'UTC_Seconds'],
                 read_flags=(0,), grid=subgrid_eu)

   imgdata = img.read(datetime(2018,1,1))

   plt.imshow(imgdata.data['Soil_Moisture'])
   plt.show()
