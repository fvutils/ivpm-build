Installation
============

From PyPI
---------

.. code-block:: bash

   pip install ivpm-build

With optional CMake support (pulls in ``scikit-build-core``):

.. code-block:: bash

   pip install ivpm-build[cmake]

Relationship to ``ivpm``
------------------------

``ivpm-build`` is a build-time companion for projects that are managed by
`ivpm <https://github.com/fvutils/ivpm>`_.  It extracts the
``ivpm.setup`` build helpers into a lightweight package that only needs to be
present when building — not when running — the project.

Runtime code that queries the IVPM package registry (``PkgInfoRgy``) still
requires ``ivpm`` itself.
