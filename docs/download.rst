Downloading data
================

All command line programs of this package are available via the ``smos``
command, with a group of commands for each product: ``smos l2``, ``smos ic``,
``smos l3`` and ``smos l4``, e.g. ``smos l3 download``. Use ``--help`` to see
all commands and options, e.g. ``smos --help`` or ``smos l3 download --help``.
There is no download program for SMOS L4 RZSM.

The download programs use `lftp <https://lftp.yar.ru/>`_ in the background,
which must be installed on your system (e.g. ``apt-get install lftp``).
Files that already exist locally are not downloaded again. After each
download a file ``overview.yml`` is written to the local data root. It contains
the first and last locally available day and is used to update an existing
record (do not change this file manually).

`L3_SMOS_IC <https://www.catds.fr/Products/Available-products-from-CEC-SM/SMOS-IC>`_
------------------------------------------------------------------------------------

SMOS IC data is distributed via the CATDS server at
https://data.catds.fr/cecsm/Land_products/L3_SMOS_IC_Soil_Moisture/.
No account is required. Note that SMOS IC is a scientific (not an operational)
product, i.e. the record on the server is only extended when a new version is
released.

To download all available data for both overpasses (ASC and DES) use

.. code-block:: shell

   smos ic download /path/to/smos_ic

Data for each orbit is stored in a separate subfolder with the same structure as
on the server, e.g. ``/path/to/smos_ic/ASC/2018/SM_RE06_MIR_CDF3SA_20180101T000000_20180101T235959_106_001_8.DBL.nc``.
The orbit folder (e.g. ``/path/to/smos_ic/ASC``) is the ``root_path`` used when
reading images (see below).

Options for ``smos ic download``:

- **--startdate (-s)** : First day to download (YYYY-MM-DD). Default: first
  available day of the product (2010-01-12).
- **--enddate (-e)** : Last day to download (YYYY-MM-DD). Default: last
  available day on the server.
- **--orbits (-o)** : Comma-separated list of overpasses to download, ASC
  and/or DES. Default: ASC,DES

To later download new files (that don't exist locally yet) for an existing
record, use

.. code-block:: shell

   smos ic update_img /path/to/smos_ic

The same functionality is available in python via the
``smos.smos_ic.download.SmosIcHttp`` class:

.. code-block:: python

   from smos.smos_ic.download import SmosIcHttp

   http = SmosIcHttp('/path/to/smos_ic', orbits=['ASC'])
   http.sync_period('2018-01-01', '2018-01-31')

`L2_SMOS <https://earth.esa.int/eogateway/catalog/smos-science-products>`_
--------------------------------------------------------------------------

SMOS L2 data is downloaded from the ESA SMOS dissemination FTP server, which
requires an EO Sign In account (https://eoiam-idp.eo.esa.int). Ideally store your
credentials in the file ``$HOME/.smosapirc`` as

.. code-block:: text

   DISSEO_USERNAME=xxxx
   DISSEO_PASSWORD=xxxx

and then use

.. code-block:: shell

   smos l2 download /path/to/smos_l2 --startdate 2022-01-01
   smos l2 update_img /path/to/smos_l2

See ``smos l2 download --help`` for all options.

`L3_SMOS <https://www.catds.fr/Products/Available-products-from-CPDC/L3-Land-products>`_
----------------------------------------------------------------------------------------

SMOS L3 soil moisture data is distributed by CATDS via the FTP server
``ftp.ifremer.fr``. The public CATDS account (``ext-catds-cpdc``) is used by
default, no registration is required. The following products are available,
each for ascending (6 am) and descending (6 pm) overpasses:

=========  ===================================================  ====================
Product    Description                                          Images
=========  ===================================================  ====================
CLF3S      Daily soil moisture (default)                        daily
CLF31      Daily retrieval, all retrieved variables             daily
CLF33      3-day aggregate                                      daily (running)
CLF3E      3-day aggregate dielectric constant (no SM)          daily (running)
CLF3D      10-day aggregate (median, min, max)                  1st, 11th, 21st
CLF3M      Monthly aggregate                                    1st of month
=========  ===================================================  ====================

On the server, data is split into processing campaigns, currently the
reprocessed (``RE07``, 2010-2021) and operational (``OPER``, since 2021)
campaign. By default, all campaigns found on the server are downloaded into the
same local folder (RE07 and OPER overlap for a few days in 2021 and contain the
same soil moisture values there; the reader uses the file with the highest
version, i.e. the operational one, in this case). A future reprocessing (e.g.
``RE08``) is found and downloaded in the same way. To download e.g. the daily
SM product for both overpasses use

.. code-block:: shell

   smos l3 download /path/to/smos_l3 --product CLF3S --startdate 2020-01-01

This creates one folder per product and overpass with the same structure as on
the server, e.g. ``/path/to/smos_l3/MIR_CLF3SA/2020/001/`` for daily products
(year and day of year) and ``/path/to/smos_l3/MIR_CLF3DA/2020/01/`` for all
other products (year and month). The downloaded ``.tgz`` archives are kept (so
that they are not downloaded again) and extracted next to them.

Options for ``smos l3 download`` (see ``smos l3 download --help``):

- **--product (-p)** : One of the products above. Default: CLF3S
- **--startdate (-s)** / **--enddate (-e)** : Period to download (by start
  date of the files). Default: full period.
- **--orbits (-o)** : ASC and/or DES (comma-separated). Default: ASC,DES
- **--campaigns (-c)** : e.g. RE07 and/or OPER (comma-separated). Default: all
  campaigns on the server

To later download new files for an existing record, use

.. code-block:: shell

   smos l3 update_img /path/to/smos_l3 --product CLF3S

This checks all campaigns on the server. If a campaign is not part of the local
record yet (e.g. after a new reprocessing was published), it is downloaded for
the whole period of the local record.

In python, use ``smos.smos_l3.download.SmosL3Ftp``:

.. code-block:: python

   from smos.smos_l3.download import SmosL3Ftp

   ftp = SmosL3Ftp('/path/to/smos_l3', product='CLF3S', orbits=['ASC'])
   ftp.sync_period('2021-06-01', '2021-06-30')
