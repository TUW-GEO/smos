====
SMOS
====

.. image:: https://travis-ci.org/TUW-GEO/smos.svg?branch=master
    :target: https://travis-ci.org/TUW-GEO/smos

.. image:: https://coveralls.io/repos/github/TUW-GEO/smos/badge.svg?branch=master
    :target: https://coveralls.io/github/TUW-GEO/smos?branch=master

.. image:: https://badge.fury.io/py/smos.svg
    :target: http://badge.fury.io/py/smos

.. image:: https://readthedocs.org/projects/smos/badge/?version=latest
   :target: http://smos.readthedocs.org/


SMOS (Soil Moisture and Ocean Salinity) data readers and time series coverter.

Works great in combination with `pytesmo <https://github.com/TUW-GEO/pytesmo>`_.


Installation
============

Setup of a complete environment with `conda
<http://conda.pydata.org/miniconda.html>`_ can be performed using the following
commands:

.. code-block:: shell

  $ conda create -q -n smos -c conda-forge numpy netcdf4 pyresample scipy pandas
  $ source activate smos
  $ pip install smos

You can also install all needed (conda and pip) dependencies at once using the
following commands after cloning this repository.  This is recommended for
developers of the package.

.. code-block:: shell

  $ git clone https://github.com/TUW-GEO/smos.git --recursive
  $ cd smos
  $ conda create -n smos python=2.7 # or any supported python version
  $ source activate smos
  $ conda update -f environment.yml
  $ python setup.py develop

or you can use the installation script.

.. code-block:: shell

    $ bash install.sh -d --python 3.6 --name smos

Supported Products
==================

- `SMOS IC <https://www.catds.fr/Products/Available-products-from-CEC-SM/SMOS-IC>`_: SMOS INRA-CESBIO (SMOS-IC) 25km


Software Citation
=================


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