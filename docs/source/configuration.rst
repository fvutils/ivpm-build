``[tool.ivpm-build]`` Configuration Reference
=============================================

``ivpm-build`` reads its configuration from the ``[tool.ivpm-build]``
section of ``pyproject.toml``.  All keys are optional; the defaults are safe
and backward-compatible.

.. list-table::
   :header-rows: 1
   :widths: 20 15 10 55

   * - Key
     - Type
     - Default
     - Description
   * - ``cmake``
     - bool
     - ``false``
     - When ``true``, run a CMake configure + build + install cycle before
       building the wheel.
   * - ``ivpm-dep-pkgs``
     - list[str]
     - ``[]``
     - IVPM package names whose include / library directories should be
       injected into C/C++ extension descriptors.
   * - ``extra-data``
     - list of tables
     - ``[]``
     - File or directory copy specifications (see below).
   * - ``ext-name-map``
     - list of tables
     - ``[]``
     - Extension module rename specifications (see below).

``extra-data`` entries
----------------------

Each entry is a TOML table with the following keys:

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Key
     - Description
   * - ``pkg``
     - Destination Python package name (e.g. ``"myproject"``).
   * - ``src``
     - Source path, relative to the project root.  Supports template
       variables (see below).
   * - ``dst``
     - Destination sub-directory inside the package
       (e.g. ``"share"``).

Example::

   [[tool.ivpm-build.extra-data]]
   pkg = "myproject"
   src = "build/{libdir}/{libpref}mylib{dllext}"
   dst = "share"

``ext-name-map`` entries
------------------------

Rename an extension module's output file after it is built.  Useful when
CMake produces a shared library with a different naming convention than
``setuptools`` expects.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Key
     - Description
   * - ``module``
     - Fully-qualified extension module name (e.g. ``"myproject._core"``).
   * - ``name``
     - Target filename.  Supports template variables.

Example::

   [[tool.ivpm-build.ext-name-map]]
   module = "myproject._core"
   name = "{libpref}core{dllext}"

Template variables
------------------

The following variables are expanded in ``src`` and ``name`` fields:

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Variable
     - Expansion
   * - ``{libdir}``
     - ``"lib64"`` if ``build/lib64`` exists, otherwise ``"lib"``.
   * - ``{libpref}``
     - ``"lib"`` on Linux/macOS; ``""`` on Windows.
   * - ``{dllpref}``
     - Same as ``{libpref}``.
   * - ``{dllext}``
     - ``".so"`` (Linux), ``".dylib"`` (macOS), ``".dll"`` (Windows).
