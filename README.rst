====
SMOS
====
.. image:: https://github.com/TUW-GEO/smos/workflows/Automated%20Tests/badge.svg?branch=master&event=push
   :target: https://github.com/TUW-GEO/smos/actions

.. image:: https://coveralls.io/repos/github/TUW-GEO/smos/badge.svg?branch=master
    :target: https://coveralls.io/github/TUW-GEO/smos?branch=master

.. image:: https://badge.fury.io/py/smos.svg
    :target: http://badge.fury.io/py/smos

.. image:: https://readthedocs.org/projects/smos/badge/?version=latest
   :target: http://smos.readthedocs.org/

.. image:: https://zenodo.org/badge/167011732.svg
   :target: https://zenodo.org/badge/latestdoi/167011732
   

SMOS (Soil Moisture and Ocean Salinity) data readers and time series converter.

Works great in combination with `pytesmo <https://github.com/TUW-GEO/pytesmo>`_.


Documentation & Software Citation
=================================
To see the latest full documentation click on the docs badge at the top.

To cite this package follow the Zenodo badge at the top and export the citation there.
Be aware that this badge links to the latest package version. Additional information
on DOI versioning can be found here: http://help.zenodo.org/#versioning

Installation
============

Before installing this package via pip, please install the necessary
`conda <http://conda.pydata.org/miniconda.html>`_ dependencies:

.. code::

    $ conda install -c conda-forge netcdf4 pyresample


Then

.. code::

    $ pip install smos

should work.

Example installation script
---------------------------

The following script will install miniconda and setup the environment on a UNIX
like system. Miniconda will be installed into ``$HOME/miniconda``.

.. code::

   wget https://repo.continuum.io/miniconda/Miniconda-latest-Linux-x86_64.sh -O miniconda.sh
   bash miniconda.sh -b -p $HOME/miniconda
   export PATH="$HOME/miniconda/bin:$PATH"
   git clone git@github.com:TUW-GEO/smos.git smos
   cd smos
   conda env create -f environment.yml
   source activate smos

This script adds ``$HOME/miniconda/bin`` temporarily to the ``PATH`` to do this
permanently add ``export PATH="$HOME/miniconda/bin:$PATH"`` to your ``.bashrc``
or ``.zshrc``

The second to last line in the example activates the ``smos`` environment.

After that you should be able to run:

.. code::

    pytest

to run the test suite.


Supported Products
==================

Currently the following products are supported, additional products can be
added.

- `SMOS IC <https://www.catds.fr/Products/Available-products-from-CEC-SM/SMOS-IC>`_: SMOS INRA-CESBIO (SMOS-IC) 25km
- `SMOS L4 RZSM <https://www.catds.fr/Products/Available-products-from-CEC-SM/L4-Land-research-products>`_: SMOS CATDS-CESBIO (SMOS L4 RZSM) 25km

Contribute
==========

We are happy if you want to contribute. Please raise an issue explaining what
is missing or if you find a bug. We will also gladly accept pull requests
against our master branch for new features or bug fixes.


Guidelines
----------

If you want to contribute please follow these steps:

- Fork the smos repository to your account
- make a new feature branch from the smos master branch
- Add your feature
- please include tests for your contributions in one of the test directories
  We use py.test so a simple function called test_my_feature is enough
- submit a pull request to our master branch
