Reading images
==============

`L3_SMOS_IC <https://www.catds.fr/Products/Available-products-from-CEC-SM/SMOS-IC>`_
------------------------------------------

After downloading the data you will have a path with subpaths of the format
``YYYY.MM.DD``. Let's call this path ``root_path``. To read 'Soil_Moisture'
data for the descending overpass of a certain date use the following code:

.. code-block:: python

   from smos.smos_ic.interface import SMOSDs
   root_path = os.path.join(os.path.dirname(__file__),
                            'test_data', 'SMOS_IC')
   ds = SMOSDs(root_path, parameters='Soil_Moisture')
   image = ds.read(datetime(2018, 1, 1))
   assert list(image.data.keys()) == ['Soil_Moisture']
   sm_data = image.data['Soil_Moisture]

The returned image is of the type `pygeobase.Image
<http://pygeobase.readthedocs.io/en/latest/api/pygeobase.html#pygeobase.object_base.Image>`_.
Which is only a small wrapper around a dictionary of numpy arrays.

If you only have a single image you can also read the data directly

.. code-block:: python

   from smos.smos_ic.interface import SMOSImg
   fname = os.path.join(os.path.dirname(__file__),
                        'test_data', 'SMOS_IC', '2018',
                        'SM_RE06_MIR_CDF3SA_20180101T000000_20180101T235959_105_001_8.DBL.nc')
   img = SMOSImg(fname, parameters=['Soil_Moisture'])

   image = ds.read()
   assert list(image.data.keys()) == ['Soil_Moisture']
   sm_data = image.data['Soil_Moisture]

