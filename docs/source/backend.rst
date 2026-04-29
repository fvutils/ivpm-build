PEP 517 Build Backend (``ivpm_build.backend``)
===============================================

``ivpm_build.backend`` is a PEP 517 / PEP 660 compliant build backend that
wraps ``setuptools.build_meta`` and injects IVPM configuration before each
hook is invoked.

Activating the backend
-----------------------

Add the following to ``pyproject.toml``:

.. code-block:: toml

   [build-system]
   requires = ["ivpm-build", "setuptools>=64"]
   build-backend = "ivpm_build.backend"

When to use this backend vs. the ``setup.py`` wrapper
------------------------------------------------------

* **Use the backend** (Path 3) when you want a pure-``pyproject.toml``
  project with no ``setup.py``.  The backend handles CMake invocation,
  IVPM path injection, and extra-data copying automatically.

* **Use** ``apply_ivpm_setup()`` (Path 2) when you need fine-grained
  control over extension descriptors in a ``setup.py`` while still
  benefiting from ``pyproject.toml`` metadata.

* **Use** ``from ivpm_build.setup import setup`` (Path 1) for a zero-change
  migration from ``ivpm.setup.setup``.

What the backend does
---------------------

1. Loads ``[tool.ivpm-build]`` from ``pyproject.toml``.
2. Populates ``ivpm_data._ivpm_extra_data`` and
   ``ivpm_data._ivpm_ext_name_m`` from the config.
3. If ``cmake = true``, invokes :class:`~ivpm_build.cmake.CmakeBuilder`
   before delegating to ``setuptools.build_meta.build_wheel()``.
4. Delegates all remaining PEP 517 hooks unchanged to
   ``setuptools.build_meta``.

Exposed hooks
-------------

All required PEP 517 hooks are exposed:

* ``get_requires_for_build_wheel``
* ``prepare_metadata_for_build_wheel``
* ``build_wheel``
* ``build_sdist``
* ``build_editable``
* ``get_requires_for_build_editable``
* ``prepare_metadata_for_build_editable``
