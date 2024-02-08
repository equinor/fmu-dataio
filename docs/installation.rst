.. highlight:: shell

============
Installation
============

From pip
--------

For a selection of platforms (Linux/Windows/MacOS; all 64bit) and Python versions:

.. code-block:: console

   $ pip install fmu-dataio


Stable release in Equinor
-------------------------

Within Equinor, the stable release is pre-installed, so all you have
to do is:

.. code-block:: python

   from fmu import dataio


From github
------------

.. code-block:: console

   $ pip install git+https://github.com/equinor/fmu-dataio


From downloaded sources
-----------------------

The sources for FMU-dataio can be downloaded from the `Equinor Github repo`_.

You can either clone the public repository:

.. code-block:: console

   $ git clone git@github.com:equinor/fmu-dataio

For required python packages, see the pyproject.toml file in the root folder.

Once you have a copy of the source, and you have a `virtual environment`_,
then always run tests (run first compile and install with ``pip install .``):

.. code-block:: console

   $ pytest

Next you can install it with:

.. code-block:: console

   $ pip install .


.. _Equinor Github repo: https://github.com/equinor/fmu-dataio
.. _virtual environment: http://docs.python-guide.org/en/latest/dev/virtualenvs/
