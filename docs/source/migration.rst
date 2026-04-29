Migrating from ``ivpm.setup``
=============================

Projects that previously used ``from ivpm.setup import setup`` can migrate to
``ivpm_build`` with minimal changes.  Three integration paths are available,
depending on how much you want to modernise your project's build system.

All three paths preserve the same core behaviour: ``BuildExt`` injects include
and library paths from IVPM-managed dependencies, ``InstallLib`` packages native
shared libraries into the wheel, and the IVPM package registry is queried at
build time to resolve dependency paths.

----

Path 1 — Legacy ``setup.py`` (one-line change)
-----------------------------------------------

The simplest migration: change a single import line.  Everything else stays
the same.

**Before**

.. code-block:: python

   from ivpm.setup import setup

**After**

.. code-block:: python

   from ivpm_build.setup import setup

``ivpm_build.setup.setup()`` is a drop-in replacement that accepts the same
keyword arguments (``ivpm_extdep_pkgs``, ``ivpm_extra_data``,
``ivpm_ext_name_m``, ``ivpm_hooks``, etc.) and injects ``BuildExt`` /
``InstallLib`` into the ``cmdclass`` dict just as the original did.

----

Path 2 — Hybrid ``pyproject.toml`` + ``setup.py``
--------------------------------------------------

Keep a ``setup.py`` for extension configuration but express package metadata
in ``pyproject.toml`` and use ``apply_ivpm_setup()`` instead of wrapping
``setup()``.

``pyproject.toml`` — **before** (no ``[build-system]`` table):

.. code-block:: toml

   [project]
   name = "myproject"
   ...

``pyproject.toml`` — **after**:

.. code-block:: toml

   [build-system]
   requires = ["ivpm-build", "setuptools>=64"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "myproject"
   ...

   [tool.ivpm-build]
   ivpm-dep-pkgs = ["mypkg"]

``setup.py`` — **before**:

.. code-block:: python

   from ivpm.setup import setup
   from setuptools import Extension

   setup(
       name="myproject",
       ext_modules=[Extension("myproject._core", sources=["src/core.cpp"])],
       ivpm_extdep_pkgs=["mypkg"],
   )

``setup.py`` — **after**:

.. code-block:: python

   from setuptools import setup, Extension
   from ivpm_build.setup import apply_ivpm_setup

   ext = Extension("myproject._core", sources=["src/core.cpp"])
   apply_ivpm_setup(ext_modules=[ext], ivpm_extdep_pkgs=["mypkg"])
   setup(name="myproject", ext_modules=[ext])

----

Path 3 — Pure ``pyproject.toml``
---------------------------------

Eliminate ``setup.py`` entirely.  Use ``ivpm_build.backend`` as the PEP 517
build backend.

**Before** (has a ``setup.py``):

.. code-block:: python

   # setup.py
   from ivpm.setup import setup
   ...

**After** — ``pyproject.toml`` only:

.. code-block:: toml

   [build-system]
   requires = ["ivpm-build", "setuptools>=64"]
   build-backend = "ivpm_build.backend"

   [project]
   name = "myproject"
   ...

   [tool.ivpm-build]
   cmake = true
   ivpm-dep-pkgs = ["mypkg"]

   [[tool.ivpm-build.extra-data]]
   pkg = "myproject"
   src = "build/{libdir}/{libpref}mycore{dllext}"
   dst = "share"

Delete ``setup.py``.  The backend will configure CMake, call
``CmakeBuilder``, inject IVPM paths, and delegate wheel/sdist building to
``setuptools.build_meta``.
