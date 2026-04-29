ivpm-build
==========

**ivpm-build** is build tooling for Python packages that wrap native C/C++
extensions.  It handles the full pipeline — CMake-based native builds, Python
extension (Cython/C++) compilation, shared-library packaging — and integrates
with `IVPM <https://github.com/fvutils/ivpm>`_ to resolve include paths,
library paths, and Cython ``.pxd`` files from other IVPM-managed native
packages declared in ``ivpm.yaml``.

Use ``ivpm-build`` when your Python package wraps a C/C++ library built with
CMake, or exposes a Cython extension that links against native libraries from
other IVPM-managed packages.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   installation
   cmake
   migration
   configuration
   backend
   api/setup
   api/config
   api/backend
   api/cmake

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
