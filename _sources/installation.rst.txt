Installation
============

From PyPI
---------

.. code-block:: bash

   pip install ivpm-build

How it fits into a native-extension project
--------------------------------------------

A typical project using ``ivpm-build`` has this structure:

* A C/C++ library built with **CMake** (outputs ``.so`` / ``.dll`` / ``.dylib``).
* One or more **Cython** ``.pyx`` files that wrap the native library.
* One or more **IVPM-managed** native packages (e.g. ``debug-mgr``,
  ``ciostream``) whose headers and libraries must be on the compiler's include
  and link paths.

``ivpm-build`` wires these pieces together:

1. ``CmakeBuilder`` drives the CMake configure → build → install cycle.
2. ``BuildExt`` (a custom ``build_ext`` command) queries the IVPM package
   registry (``PkgInfoRgy``) to inject include dirs, library dirs, and Cython
   ``.pxd`` search paths from every package listed in ``ivpm_extdep_pkgs``.
3. ``InstallLib`` copies the built native shared library into the installed
   Python package so the wheel is self-contained.

Relationship to ``ivpm``
------------------------

``ivpm`` is the full dependency-management tool.  ``ivpm-build`` is a
lightweight build-time companion that:

* is listed in ``[build-system].requires`` in ``pyproject.toml`` so it is
  available during ``pip install`` / ``python -m build``, and
* calls into ``ivpm``\'s package registry at build time to resolve paths for
  IVPM-managed native dependencies.

``ivpm`` itself is therefore also required at build time (for ``PkgInfoRgy``
queries) and must be listed alongside ``ivpm-build`` in
``[build-system].requires``.
