CMake Integration
=================

``ivpm-build`` ships a ``CmakeBuilder`` class that drives a CMake
configure → build → install cycle.  In a typical native-extension project,
``CmakeBuilder`` is called *before* the Cython/C++ extension is compiled so
that the CMake-installed headers and the native shared library are in place when
``BuildExt`` runs.

What gets built
---------------

A CMake project managed by ``ivpm-build`` typically produces:

* A native shared library (e.g. ``libmypkg.so``) that the Python extension
  links against.
* Public headers installed to ``build/include/``, which ``BuildExt`` adds to
  the compiler's include path.
* Generated Cython source files (e.g. from ANTLR4 grammars) that ``BuildExt``
  then compiles.

``PACKAGES_DIR`` and IVPM dependency layout
--------------------------------------------

``CmakeBuilder`` resolves the packages directory automatically:

1. If ``<proj_dir>/packages/`` exists → ``PACKAGES_DIR=<proj_dir>/packages``.
2. Otherwise → ``PACKAGES_DIR=<parent of proj_dir>``.

The resolved path is passed to CMake as ``-DPACKAGES_DIR=...``.  CMake
``find_package`` / ``find_library`` calls in the project's ``CMakeLists.txt``
can use ``PACKAGES_DIR`` to locate headers and libraries from other
IVPM-managed packages (e.g. ``debug-mgr``, ``ciostream``, ``antlr4-runtime``).

Basic usage
-----------

.. code-block:: python

   from ivpm_build.cmake import CmakeBuilder

   builder = CmakeBuilder(proj_dir="/path/to/project")
   builder.run()   # configure, build, install

Or step by step:

.. code-block:: python

   builder = CmakeBuilder(proj_dir, cmake_build_tool="Unix Makefiles", debug=True)
   builder.configure(extra_args=["-DSOME_FLAG=ON"])
   builder.build()
   builder.install()

``CMAKE_BUILD_TOOL`` environment variable
-----------------------------------------

The build tool (generator) can be overridden at runtime:

.. code-block:: bash

    CMAKE_BUILD_TOOL="Unix Makefiles" python -m build

Supported values: ``"Ninja"`` (default), ``"Unix Makefiles"``.

``DEBUG`` flag
--------------

Pass ``debug=True`` to ``CmakeBuilder`` or set the environment variable
``DEBUG=1`` (or ``y`` / ``Y``) to build with
``-DCMAKE_BUILD_TYPE=Debug``.

Platform notes
--------------

* **macOS** — ``-DCMAKE_OSX_ARCHITECTURES='x86_64;arm64'`` is added
  automatically for universal binary support.
* **Windows** — no extra architecture flags are added.

Optional ``scikit-build-core`` bridge (``IVPMHook``)
----------------------------------------------------

If ``scikit-build-core`` is installed, ``IVPMHook`` can inject IVPM prefix
paths into CMake:

.. code-block:: toml

   # pyproject.toml
   [tool.scikit-build.hooks]
   build = "ivpm_build.cmake.skbuild_bridge:IVPMHook"

.. note::
   The ``scikit-build-core`` bridge is currently a stub pending finalisation
   of the hook API.  It is safe to import when ``scikit-build-core`` is not
   installed.
