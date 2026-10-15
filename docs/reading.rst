Reading images
==============

`L3_SMOS_IC <https://www.catds.fr/Products/Available-products-from-CEC-SM/SMOS-IC>`_
------------------------------------------------------------------------------------

After downloading the data (see above) you will have a directory for each
orbit (``ASC``, ``DES``) with subpaths of the format ``YYYY``. Let's call the
orbit directory ``root_path``. To read 'Soil_Moisture' data for a certain
date use the following code:

.. code-block:: python

   from smos.smos_ic.interface_ic import SMOS_IC_Ds
   import matplotlib.pyplot as plt
   from datetime import datetime
   import os
   # path to the cloned test data repository, see section "Test data"
   testdata_path = '/path/to/smos-test-data'


   root_path = os.path.join(testdata_path, 'L3_SMOS_IC', 'ASC')
   ds = SMOS_IC_Ds(root_path, parameters='Soil_Moisture')
   image = ds.read(datetime(2018, 1, 1))
   assert list(image.data.keys()) == ['Soil_Moisture']
   sm_data = image.data['Soil_Moisture']

   plt.imshow(sm_data)
   plt.show()

The returned image is of the type `pygeobase.Image
<http://pygeobase.readthedocs.io/en/latest/api/pygeobase.html#pygeobase.object_base.Image>`_.
Which is only a small wrapper around a dictionary of numpy arrays.

By default, files of all product versions are found. If there are multiple
files for the same day (e.g. after downloading a new version into an existing
folder), the one with the highest version (and file counter) is read. Pass
e.g. ``version=106`` to ``SMOS_IC_Ds`` to only read files of a certain version.

.. note::

   Since product version 106 (v2.0, the version currently distributed by
   CATDS), SMOS IC files no longer contain the ``Quality_Flag`` and
   ``Processing_Flags`` variables. Observations that were flagged as "not
   recommended" in v105 (strong topography, polluted or frozen scenes) are
   already removed from the Soil Moisture data. Only moderate topography
   (``Scene_Flags`` = 1) and observations with high RMSE are kept, these can
   be filtered with the ``Scene_Flags`` and ``RMSE`` variables if needed.
   The ``read_flags`` option is therefore not available for SMOS IC anymore.

If you only have a single image you can also read the data directly by specifying
the file. Here we read all variables from the file.

.. code-block:: python

   from smos.smos_ic.interface_ic import SMOS_IC_Img
   import matplotlib.pyplot as plt
   from datetime import datetime
   import os
   # path to the cloned test data repository, see section "Test data"
   testdata_path = '/path/to/smos-test-data'

   fname = os.path.join(testdata_path, 'L3_SMOS_IC', 'ASC', '2018',
                        'SM_RE06_MIR_CDF3SA_20180101T000000_20180101T235959_106_001_8.DBL.nc')
   img = SMOS_IC_Img(fname)

   image = img.read(datetime(2018,1,1))
   sm_data = image.data['Soil_Moisture']

   plt.imshow(sm_data)
   plt.show()


You can also limit the reading to certain variables or a spatial subset by
defining a bounding box area.
In the following example, we read SMOS IC Soil Moisture and some other
variables over Europe only.

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

   imgdata = img.read(datetime(2018,1,1))

   plt.imshow(imgdata.data['Soil_Moisture'])
   plt.show()

`L4_SMOS_RZSM <https://www.catds.fr/Products/Available-products-from-CEC-SM/L4-Land-research-products>`_
-------------------------------------------------------------------------------------------------------------

SMOS L4 root zone soil moisture images (stored in yearly subfolders) are on the
same EASE2 25 km grid and are read in the same way:

.. code-block:: python

   import os
   from datetime import datetime
   from smos.smos_l4.interface_l4 import SMOS_L4_Ds
   # path to the cloned test data repository, see section "Test data"
   testdata_path = '/path/to/smos-test-data'

   ds = SMOS_L4_Ds(os.path.join(testdata_path, 'L4_SMOS_RZSM', 'SCIE'),
                   parameters=['RZSM', 'QUAL'])
   image = ds.read(datetime(2018, 1, 1))
   rzsm = image.data['RZSM']

``read_flags`` is the lower and upper threshold (both included) of the quality
variable, values with a quality outside of this range are masked. The
scientific product (``SM_SCIE_MIR_CLF4RD`` files) has a quality index ``QUAL``
between 0 and 1 (1 is the highest quality), the operational product
(``SM_OPER_MIR_CLF4RD`` files) a ``Quality`` flag (-1 = missing,
0 = not recommended, 1 = OK). The product is detected from the file. The
default ``read_flags=(0, 1)`` only masks missing data, e.g.
``read_flags=(0.8, 1)`` only keeps values with a quality index of at least
0.8, ``read_flags=(1, 1)`` only the best quality. Pass ``read_flags=None`` to
read all values without filtering. See the variable names section for all
variables.

`L3_SMOS <https://www.catds.fr/Products/Available-products-from-CPDC/L3-Land-products>`_
----------------------------------------------------------------------------------------

All SMOS L3 products are on the same EASE2 25 km grid as SMOS IC. To read data
for one product and overpass, pass the corresponding folder created by the
download program (the product and overpass are derived from the folder name):

.. code-block:: python

   import os
   from datetime import datetime
   from smos.smos_l3.interface_l3 import SMOS_L3_Ds
   from smos.grid import EASE25CellGrid

   # path to the downloaded data or extracted test data, see section "Test data"
   path = '/path/to/smos_l3/MIR_CLF3SA'

   ds = SMOS_L3_Ds(path, parameters=['Soil_Moisture', 'Science_Flags'],
                   grid=EASE25CellGrid(bbox=(-11., 34., 43., 71.)))
   image = ds.read(datetime(2021, 6, 7))
   sm_data = image.data['Soil_Moisture']  # (113, 208) array over Europe

If files of multiple campaigns or versions exist for a date (e.g. RE07 and
OPER), the one with the highest version (here OPER) is used, pass e.g. ``version=338`` to
read a specific version. Variables with a third dimension are split into
separate variables, i.e. ``Soil_Moisture_med``, ``Soil_Moisture_min`` and
``Soil_Moisture_max`` for the 10-day product (CLF3D) and ``Dielect_Const_re``,
``Dielect_Const_im`` for the real and imaginary part of the dielectric constant.
Passing the variable name without suffix (e.g. ``Soil_Moisture``) reads all
elements.

The image time stamps depend on the product: every day for the daily and 3-day
products (3-day files are named by their first day), the 1st, 11th and 21st of
each month for the 10-day product and the 1st of each month for the monthly
product (see ``SMOS_L3_Ds.tstamps_for_daterange``).
