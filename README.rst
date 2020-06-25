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
conda dependencies:

.. code-block:: shell

  $ conda install -c conda-forge netcdf4 pyresample
  $ pip install smos

Setup of a complete environment with `conda
<http://conda.pydata.org/miniconda.html>`_ can be performed using the following
commands:

You can also install all needed (conda and pip) dependencies at once using the
following commands after cloning this repository.  This is recommended for
developers of the package.

.. code-block:: shell

  $ git clone https://github.com/TUW-GEO/smos.git --recursive
  $ cd smos
  $ conda create -n smos python=3.6 # or any supported python version
  $ source activate smos
  $ conda update -f environment.yml
  $ python setup.py develop

or you can use the installation script with/without the develop flag (``-d``),
which will call ``python setup.py develop``, resp ``python setup.py install``.

.. code-block:: shell

    $ bash install.sh -d --python 3.6 --name smos

Supported Products
==================

Currently the following products are supported, additional products can be
added.

- `SMOS IC <https://www.catds.fr/Products/Available-products-from-CEC-SM/SMOS-IC>`_: SMOS INRA-CESBIO (SMOS-IC) 25km

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
