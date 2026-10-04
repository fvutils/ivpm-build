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
   * - ``scripts``
     - list of tables
     - ``[]``
     - Built executables to install onto ``PATH`` (see below).

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

``scripts`` entries
-------------------

Ship a CMake-built executable in the wheel's ``<dist>.data/scripts/``
directory.  pip installs it into the environment's scripts directory
(``bin/`` on Linux/macOS, ``Scripts\`` on Windows), so it is on ``PATH`` in
an activated virtual environment.  The file is copied byte for byte and
marked executable; there is no Python launcher.  Applies to ``build_wheel``
only.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Key
     - Description
   * - ``src``
     - Path to the executable, relative to the project root.  Supports
       template variables; use ``{exeext}`` for the platform suffix.
   * - ``optional``
     - ``true`` to skip the entry, with a message, when the file was not
       built (for example on a platform the project does not build it for).
       Default ``false``: a missing file fails the build.

Because pip puts the executable outside the package, it cannot find shared
libraries in the package through a relative RPATH.  Link it statically
against the project's own libraries.

Example::

   [[tool.ivpm-build.scripts]]
   src = "build/bin/mytool{exeext}"
   optional = true

Template variables
------------------

The following variables are expanded in ``src`` and ``name`` fields
(including ``scripts`` entries):

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
   * - ``{exeext}``
     - ``".exe"`` on Windows; ``""`` elsewhere.
