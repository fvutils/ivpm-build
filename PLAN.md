# `ivpm-build` Implementation, Test, and Documentation Plan

## Overview

This plan describes the full implementation, test suite, Sphinx documentation, and CI/CD
pipeline for the `ivpm-build` package as specified in
`../ivpm/ivpm-build-separation-design.md`.

The goal: a standalone Python package (`ivpm-build`, importable as `ivpm_build`) that:
- Provides a drop-in replacement for `ivpm.setup.setup()` (backward compat)
- Adds a `[tool.ivpm-build]` config parser for `pyproject.toml`
- Exposes a PEP 517 build backend (`ivpm_build.backend`) wrapping `setuptools.build_meta`
- Bundles CMake helpers extracted from `ivpm.setup.build_ext`
- Ships Sphinx documentation published to GitHub Pages
- Releases to PyPI on every push to `main` via GitHub Actions

---

## 1  Repository Layout

```
ivpm-build/
├── .github/
│   └── workflows/
│       └── ci.yml                  # Test → build → publish docs/PyPI
├── PLAN.md                         # This file
├── LICENSE                         # Apache 2.0 (same as ivpm)
├── README.md
├── ivpm.yaml                       # IVPM dependency declaration
├── pyproject.toml                  # PEP 621 project metadata + build config
├── docs/
│   └── source/
│       ├── conf.py
│       ├── index.rst
│       ├── installation.rst
│       ├── migration.rst           # Paths 1, 2, 3 from design doc
│       ├── configuration.rst       # [tool.ivpm-build] reference
│       ├── backend.rst             # PEP 517 backend API
│       ├── cmake.rst               # CMake helper reference
│       └── api/
│           ├── setup.rst           # autodoc ivpm_build.setup
│           ├── config.rst          # autodoc ivpm_build.config
│           ├── backend.rst         # autodoc ivpm_build.backend
│           └── cmake.rst           # autodoc ivpm_build.cmake
├── src/
│   └── ivpm_build/
│       ├── __init__.py
│       ├── _version.py
│       ├── backend.py
│       ├── config.py
│       ├── setup/
│       │   ├── __init__.py         # re-exports setup(), apply_ivpm_setup()
│       │   ├── wrapper.py
│       │   ├── build_ext.py
│       │   ├── install_lib.py
│       │   └── ivpm_data.py
│       └── cmake/
│           ├── __init__.py
│           ├── cmake_builder.py
│           └── skbuild_bridge.py
└── test/
    ├── conftest.py
    ├── unit/
    │   ├── test_ivpm_data.py
    │   ├── test_config.py
    │   └── test_cmake_builder.py
    └── integration/
        ├── test_setup_wrapper.py
        └── test_backend.py
```

---

## 2  `ivpm.yaml`

Mirrors the pattern used by `ivpm` itself.  Only runtime-relevant packages in `default`;
dev tooling (Sphinx, pytest, build) in `default-dev`.

```yaml
# yaml-language-server: $schema=https://fvutils.github.io/ivpm/ivpm.json

package:
  name: ivpm-build

  dep-sets:
  - name: default
    deps:
    - name: ivpm
      src: pypi
    - name: setuptools
      src: pypi
    - name: tomli
      src: pypi     # Python < 3.11 fallback for tomllib

  - name: default-dev
    deps:
    - name: ivpm
      src: pypi
    - name: setuptools
      src: pypi
    - name: tomli
      src: pypi
    - name: pytest
      src: pypi
    - name: pytest-cov
      src: pypi
    - name: build
      src: pypi
    - name: wheel
      src: pypi
    - name: twine
      src: pypi
    - name: Sphinx
      src: pypi
    - name: sphinx-rtd-theme
      src: pypi
    - name: sphinx-argparse
      src: pypi
    - name: myst-parser       # optional: Markdown support in Sphinx
      src: pypi

  env-sets:
    - name: project
      env:
        - name: PYTHONPATH
          value: $IVPM_HOME/src
```

---

## 3  `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.build_meta"

[project]
name = "ivpm-build"
dynamic = ["version"]
description = "Build helpers and PEP 517 backend for IVPM-managed Python extension projects"
license = {file = "LICENSE"}
authors = [
    {name = "Matthew Ballance", email = "matt.ballance@gmail.com"},
]
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "ivpm",
    "setuptools>=64",
    "tomli>=1.2; python_version<'3.11'",
]

[project.optional-dependencies]
cmake  = ["scikit-build-core"]
dev    = [
    "pytest", "pytest-cov", "build", "wheel", "twine",
    "Sphinx", "sphinx-rtd-theme", "sphinx-argparse", "myst-parser",
]

[project.urls]
Homepage      = "https://github.com/fvutils/ivpm-build"
Documentation = "https://fvutils.github.io/ivpm-build"
Repository    = "https://github.com/fvutils/ivpm-build"

[tool.setuptools.dynamic]
version = {attr = "ivpm_build._version._pkg_version"}

[tool.setuptools.packages.find]
where = ["src"]
```

---

## 4  Source Implementation

### 4.1  `src/ivpm_build/_version.py`

Standard single-source versioning matching the `ivpm` pattern:

```python
_pkg_version = "0.1.0"
SUFFIX = ""
version = _pkg_version + SUFFIX
```

### 4.2  `src/ivpm_build/__init__.py`

```python
from ._version import version as __version__
```

### 4.3  `src/ivpm_build/setup/ivpm_data.py`  *(ported, no logic change)*

Direct copy of `ivpm/src/ivpm/setup/ivpm_data.py`.
Update all internal import paths from `ivpm.setup` → `ivpm_build.setup`.
No functional changes.

Key exports:
- Phase constants: `Phase_SetupPre`, `Phase_SetupPost`, `Phase_BuildPre`, `Phase_BuildPost`
- Getters: `get_hooks()`, `get_ivpm_extra_data()`, `get_ivpm_extdep_data()`, `get_ivpm_ext_name_m()`
- Path expansion: `expand_libvars()`, `expand()`

### 4.4  `src/ivpm_build/setup/build_ext.py`  *(ported + refactored)*

Copy of `ivpm/src/ivpm/setup/build_ext.py` with:
1. Import paths updated: `ivpm.setup.ivpm_data` → `ivpm_build.setup.ivpm_data`
2. CMake logic (`build_cmake`, `build_ninja`, `build_make`, `install_ninja`, `install_make`)
   **extracted** into `ivpm_build.cmake.cmake_builder.CmakeBuilder` and called from here
   via `CmakeBuilder(proj_dir).build()`.  This decouples cmake logic from the setuptools command.
3. The `distutils.file_util.copy_file` import replaced with `shutil.copy2` (distutils deprecated).

### 4.5  `src/ivpm_build/setup/install_lib.py`  *(ported)*

Copy of `ivpm/src/ivpm/setup/install_lib.py` with:
1. Import paths updated.
2. The `from ivpm import setup as ivpms` import removed (no longer needed).

### 4.6  `src/ivpm_build/setup/wrapper.py`  *(ported + new helper)*

Copy of `ivpm/src/ivpm/setup/wrapper.py` with:
1. Import paths updated.
2. New public function `apply_ivpm_setup(ext_modules, ivpm_extdep_pkgs=None, ...)` added.
   This is the **Path 2** helper that patches extension descriptors in-place without
   replacing `setup()`:

```python
def apply_ivpm_setup(
    ext_modules=None,
    ivpm_extdep_pkgs=None,
    ivpm_extra_data=None,
    ivpm_extdep_data=None,
    ivpm_hooks=None,
    ivpm_ext_name_m=None,
):
    """Inject IVPM-managed dependency paths into extension descriptors and
    store extra-data/hook configuration without replacing setuptools.setup().
    Call this before calling setuptools.setup() directly."""
    ...
```

### 4.7  `src/ivpm_build/setup/__init__.py`

```python
from .wrapper import setup, apply_ivpm_setup
from .build_ext import BuildExt
from .install_lib import InstallLib
from . import ivpm_data
```

### 4.8  `src/ivpm_build/config.py`  *(new)*

Reads `[tool.ivpm-build]` from `pyproject.toml`.

```python
@dataclass
class ExtraDataSpec:
    pkg: str
    src: str
    dst: str

@dataclass
class ExtNameMapEntry:
    module: str
    name: str

@dataclass
class IvpmBuildConfig:
    cmake: bool = False
    ivpm_dep_pkgs: list[str] = field(default_factory=list)
    extra_data: list[ExtraDataSpec] = field(default_factory=list)
    ext_name_map: list[ExtNameMapEntry] = field(default_factory=list)

def load_config(pyproject_path: str = "pyproject.toml") -> IvpmBuildConfig:
    """Parse [tool.ivpm-build] section from pyproject.toml.
    Returns default IvpmBuildConfig if the section is absent."""
    ...
```

Uses `tomllib` (Python ≥ 3.11) or `tomli` (Python < 3.11) with a compatibility shim:

```python
try:
    import tomllib
except ImportError:
    import tomli as tomllib
```

### 4.9  `src/ivpm_build/cmake/cmake_builder.py`  *(extracted from build_ext)*

```python
class CmakeBuilder:
    """Drives a CMake configure + build + install cycle.

    Extracted from ivpm.setup.BuildExt.build_cmake() so it can be used
    independently of the setuptools command hierarchy.
    """

    def __init__(self, proj_dir: str, build_dir: str | None = None,
                 debug: bool = False, cmake_build_tool: str | None = None):
        self.proj_dir = proj_dir
        self.build_dir = build_dir or os.path.join(proj_dir, "build")
        self.debug = debug
        self.cmake_build_tool = cmake_build_tool or os.environ.get(
            "CMAKE_BUILD_TOOL", "Ninja")

    def configure(self, extra_args: list[str] | None = None) -> None: ...
    def build(self) -> None: ...
    def install(self) -> None: ...
    def run(self, extra_cmake_args: list[str] | None = None) -> None:
        """Configure, build, and install in sequence."""
        self.configure(extra_cmake_args)
        self.build()
        self.install()
```

Key implementation notes:
- Supports `Ninja` and `Unix Makefiles` (as today).
- `packages_dir` discovery logic preserved from original.
- `PYTHONPATH` isolation preserved.
- Platform-specific flags (Darwin universal binary, Windows) preserved.

### 4.10  `src/ivpm_build/cmake/skbuild_bridge.py`  *(aspirational, stubbed)*

```python
try:
    from scikit_build_core.build import BuildHookInterface as _BHI  # type: ignore
    _SKBUILD_AVAILABLE = True
except ImportError:
    _BHI = object
    _SKBUILD_AVAILABLE = False

class IVPMHook(_BHI):
    """scikit-build-core build hook that injects IVPM include/lib paths."""

    def initialize(self, version, build_data):
        if not _SKBUILD_AVAILABLE:
            raise RuntimeError("scikit-build-core is required for IVPMHook")
        build_data["cmake_args"].extend(collect_cmake_args())

def collect_cmake_args(dep_pkgs: list[str] | None = None) -> list[str]:
    """Return a list of -DCMAKE_PREFIX_PATH=... args from IVPM pkg_info registry."""
    ...
```

### 4.11  `src/ivpm_build/cmake/__init__.py`

```python
from .cmake_builder import CmakeBuilder
```

### 4.12  `src/ivpm_build/backend.py`  *(new — PEP 517 backend)*

Wraps `setuptools.build_meta` and injects IVPM config before each PEP 517 call.

```python
import setuptools.build_meta as _st

from .config import load_config
from .setup import ivpm_data as _idata

def _apply_ivpm_config(config=None):
    if config is None:
        config = load_config()
    if config.extra_data:
        _idata._ivpm_extra_data = {
            spec.pkg: [(spec.src, spec.dst)] for spec in config.extra_data
        }
    if config.ext_name_map:
        _idata._ivpm_ext_name_m = {
            e.module: e.name for e in config.ext_name_map
        }

def get_requires_for_build_wheel(config_settings=None):
    config = load_config()
    base = _st.get_requires_for_build_wheel(config_settings)
    if config.cmake:
        base = list(base) + ["ninja; sys_platform != 'win32'"]
    return base

def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    return _st.prepare_metadata_for_build_wheel(metadata_directory, config_settings)

def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    config = load_config()
    _apply_ivpm_config(config)
    if config.cmake:
        import os
        from .cmake.cmake_builder import CmakeBuilder
        CmakeBuilder(os.getcwd()).run()
    return _st.build_wheel(wheel_directory, config_settings, metadata_directory)

def build_sdist(sdist_directory, config_settings=None):
    return _st.build_sdist(sdist_directory, config_settings)

def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    config = load_config()
    _apply_ivpm_config(config)
    return _st.build_editable(wheel_directory, config_settings, metadata_directory)

def get_requires_for_build_editable(config_settings=None):
    return _st.get_requires_for_build_editable(config_settings)

def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    return _st.prepare_metadata_for_build_editable(metadata_directory, config_settings)
```

---

## 5  Test Plan

### 5.1  Test Infrastructure

- Test runner: `pytest`
- Test layout: `test/unit/` (no external deps) + `test/integration/` (require
  `setuptools`, `build`, may invoke subprocesses)
- `conftest.py`: shared fixtures (temp directories, mock `pyproject.toml` generator,
  mock `PkgInfoRgy`)

### 5.2  Unit Tests

#### `test/unit/test_ivpm_data.py`

| Test | What it validates |
|---|---|
| `test_expand_libvars_linux` | `expand_libvars("{libpref}foo{dllext}")` → `"libfoo.so"` on Linux |
| `test_expand_libvars_darwin` | → `"libfoo.dylib"` on Darwin |
| `test_expand_libvars_windows` | → `"foo.dll"` on Windows |
| `test_expand_libvars_libdir_auto` | Auto-detects `lib` vs `lib64` |
| `test_expand_libvars_libdir_explicit` | Explicit `libdir` param used |
| `test_hooks_empty` | `get_hooks("setup.pre")` returns `[]` when no hooks set |
| `test_hooks_registered` | Hooks round-trip through `_ivpm_hooks` dict |
| `test_get_ivpm_extra_data` | Returns current module-global dict |
| `test_get_ivpm_extdep_data` | Returns current module-global list |
| `test_get_ivpm_ext_name_m` | Returns current module-global dict |

#### `test/unit/test_config.py`

| Test | What it validates |
|---|---|
| `test_load_config_empty_file` | Missing `[tool.ivpm-build]` → default `IvpmBuildConfig` |
| `test_load_config_cmake_true` | `cmake = true` → `config.cmake is True` |
| `test_load_config_extra_data` | `[[tool.ivpm-build.extra-data]]` parsed into `ExtraDataSpec` list |
| `test_load_config_ext_name_map` | `[[tool.ivpm-build.ext-name-map]]` parsed into `ExtNameMapEntry` list |
| `test_load_config_ivpm_dep_pkgs` | `ivpm-dep-pkgs = [...]` parsed into `list[str]` |
| `test_load_config_combined` | All fields together parse correctly |
| `test_load_config_missing_file` | Non-existent `pyproject.toml` → default config (no exception) |
| `test_load_config_invalid_toml` | Malformed TOML → raises `ValueError` |

#### `test/unit/test_cmake_builder.py`

| Test | What it validates |
|---|---|
| `test_cmake_builder_defaults` | Default `build_dir`, `cmake_build_tool` from env |
| `test_cmake_build_tool_env` | `CMAKE_BUILD_TOOL=Unix Makefiles` env picked up |
| `test_cmake_build_tool_unsupported` | Unsupported tool → `ValueError` on `configure()` |
| `test_configure_args_linux` | Linux: correct `cmake` invocation flags |
| `test_configure_args_darwin` | Darwin: `-DCMAKE_OSX_ARCHITECTURES='x86_64;arm64'` present |
| `test_configure_args_windows` | Windows: no extra arch flags |
| `test_run_calls_sequence` | `CmakeBuilder.run()` calls configure → build → install in order (mock subprocess) |
| `test_cmake_failure_raises` | Non-zero returncode → `RuntimeError` |

### 5.3  Integration Tests

#### `test/integration/test_setup_wrapper.py`

Uses a temporary directory with a minimal `setup.py`-style project.

| Test | What it validates |
|---|---|
| `test_setup_wrapper_basic` | `from ivpm_build.setup import setup` callable without error on a trivial project |
| `test_apply_ivpm_setup_injects_include_dirs` | `apply_ivpm_setup(ext_modules=[ext], ivpm_extdep_pkgs=["mockpkg"])` injects mock include dirs into `ext.include_dirs` |
| `test_apply_ivpm_setup_no_ext` | Calling with no `ext_modules` does not raise |
| `test_extra_data_stored` | `ivpm_extra_data` kwarg populates `ivpm_data._ivpm_extra_data` |
| `test_ext_name_map_stored` | `ivpm_ext_name_m` kwarg populates `ivpm_data._ivpm_ext_name_m` |
| `test_hooks_called` | Pre/post hooks registered via `ivpm_hooks` kwarg are invoked |
| `test_cmdclass_injected` | `BuildExt` and `InstallLib` appear in `cmdclass` when not overridden |
| `test_cmdclass_not_overridden` | User-supplied `build_ext` not replaced |

#### `test/integration/test_backend.py`

| Test | What it validates |
|---|---|
| `test_get_requires_no_cmake` | Returns setuptools base requires only |
| `test_get_requires_cmake` | Adds `ninja` on non-Windows |
| `test_apply_ivpm_config_extra_data` | `_apply_ivpm_config` populates `ivpm_data._ivpm_extra_data` |
| `test_apply_ivpm_config_ext_name_map` | Populates `ivpm_data._ivpm_ext_name_m` |
| `test_build_wheel_delegates_to_setuptools` | `build_wheel()` calls `_st.build_wheel` (monkeypatched) |
| `test_build_sdist_delegates` | `build_sdist()` delegates cleanly |
| `test_build_editable_delegates` | `build_editable()` delegates cleanly |
| `test_backend_pep517_surface` | Module exposes all required PEP 517 hooks |

### 5.4  Running Tests

```bash
# From repo root (after bootstrap / ivpm install)
./packages/python/bin/python3 -m pytest test/ -v --tb=short
```

Coverage target: ≥ 85% on `src/ivpm_build/` (excluding `cmake/skbuild_bridge.py`).

---

## 6  Sphinx Documentation Plan

### 6.1  `docs/source/conf.py`

```python
import os, sys
sys.path.insert(0, os.path.abspath("../../src"))

project = "ivpm-build"
copyright = "2024, Matthew Ballance"
author = "Matthew Ballance"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_rtd_theme",
]

html_theme = "sphinx_rtd_theme"
```

### 6.2  Documentation Pages

#### `index.rst`
- Title, brief description, TOC linking all pages.

#### `installation.rst`
- Install from PyPI: `pip install ivpm-build`
- Optional extras: `pip install ivpm-build[cmake]`
- Relationship to `ivpm`

#### `migration.rst`
**"Migrating from `ivpm.setup`"** — covers all three integration paths from the design doc:

- **Path 1 (Legacy `setup.py`)** — change one import line; zero other changes
- **Path 2 (Hybrid `pyproject.toml` + `setup.py`)** — add `[build-system]` table,
  add `[tool.ivpm-build]` config, slim down `setup.py` to use `apply_ivpm_setup()`
- **Path 3 (Pure `pyproject.toml`)** — set `build-backend = "ivpm_build.backend"`,
  eliminate `setup.py` entirely

Each path includes a before/after code block.

#### `configuration.rst`
**`[tool.ivpm-build]` Reference** — documents every key:

| Key | Type | Default | Description |
|---|---|---|---|
| `cmake` | bool | `false` | Run CMake before building |
| `ivpm-dep-pkgs` | list[str] | `[]` | IVPM pkg names to query for include/lib dirs |
| `extra-data` | list of tables | `[]` | `{pkg, src, dst}` file/dir copy specs |
| `ext-name-map` | list of tables | `[]` | `{module, name}` rename specs |

Documents `{libdir}`, `{libpref}`, `{dllpref}`, `{dllext}` template variables.

#### `backend.rst`
Narrative description of `ivpm_build.backend` as a PEP 517 build backend.
How it relates to `setuptools.build_meta`.
When to use it vs. the legacy `setup.py` wrapper.

#### `cmake.rst`
CMake integration reference:
- How `CmakeBuilder` is invoked
- `CMAKE_BUILD_TOOL` environment variable
- `DEBUG` flag
- `PACKAGES_DIR` convention
- Platform notes (macOS universal binary, Windows)
- Optional `scikit-build-core` bridge (`IVPMHook`)

#### `api/` — Auto-generated API reference
Use `sphinx.ext.autodoc` with `:members:`, `:undoc-members:`, `:show-inheritance:`
for each submodule.

---

## 7  CI/CD: `.github/workflows/ci.yml`

```yaml
name: CI
on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  ci-linux:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Bootstrap IVPM
      run: |
        pip install ivpm
        python -m ivpm update --py-only

    - name: Install dev dependencies
      run: |
        ./packages/python/bin/python3 -m pip install -e ".[dev]"

    - name: Run Tests
      run: |
        ./packages/python/bin/python3 -m pytest test/ -v --tb=short \
          --cov=src/ivpm_build --cov-report=term-missing

    - name: Build Package
      run: |
        rm -rf dist/
        # Stamp version with CI run number (matches ivpm pattern)
        sed -i -e "s/^SUFFIX = \"\"$/SUFFIX = \".${GITHUB_RUN_ID}\"/" \
          src/ivpm_build/_version.py
        ./packages/python/bin/python3 -m build .

    - name: Build Docs
      run: |
        ./packages/python/bin/python3 -m pip install \
          sphinx sphinx-rtd-theme sphinx-argparse myst-parser
        ./packages/python/bin/sphinx-build -M html ./docs/source build
        touch build/html/.nojekyll

    - name: Publish to PyPI
      if: ${{ startsWith(github.ref, 'refs/heads/main') }}
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        user: __token__
        password: ${{ secrets.PYPI_API_TOKEN }}

    - name: Publish Docs
      if: ${{ startsWith(github.ref, 'refs/heads/main') }}
      uses: JamesIves/github-pages-deploy-action@4.1.7
      with:
        branch: gh-pages
        folder: build/html
```

**Required repository secrets:**
- `PYPI_API_TOKEN` — API token from PyPI project settings

---

## 8  Implementation Phases and Order

### Phase A — Scaffold (do first)

1. Create `pyproject.toml`, `ivpm.yaml`, `LICENSE`, `README.md`
2. Create `src/ivpm_build/__init__.py` + `_version.py`
3. Create empty `test/conftest.py`
4. Create `.github/workflows/ci.yml` (test + build only; publish gated on `main`)
5. Verify CI runs and passes with no source yet (trivially)

### Phase B — Port `ivpm.setup` (backward compat, no new features)

6. Port `ivpm_data.py` (update import paths; no logic change)
7. Port `install_lib.py` (update imports; remove obsolete `from ivpm import setup` line)
8. Extract CMake logic from `build_ext.py` → `cmake/cmake_builder.py`
9. Port `build_ext.py` (update imports; delegate cmake to `CmakeBuilder`)
10. Port `wrapper.py` (update imports; add `apply_ivpm_setup()`)
11. Create `setup/__init__.py`
12. Write unit tests for `ivpm_data` (Phase 5.2)
13. Write unit tests for `cmake_builder` (Phase 5.2)
14. Write integration tests for `setup_wrapper` (Phase 5.3)
15. All tests green

### Phase C — Config Parser

16. Implement `config.py` with `load_config()` / `IvpmBuildConfig`
17. Write unit tests for `config.py` (Phase 5.2)
18. All tests green

### Phase D — PEP 517 Backend

19. Implement `backend.py` wrapping `setuptools.build_meta`
20. Wire `config.py` into `backend.py`
21. Write integration tests for `backend.py` (Phase 5.3)
22. All tests green

### Phase E — Documentation

23. Create `docs/source/conf.py`
24. Write `installation.rst`, `migration.rst`, `configuration.rst`,
    `backend.rst`, `cmake.rst`
25. Write `api/*.rst` autodoc stubs
26. Build docs locally: `sphinx-build -M html docs/source build`
27. Verify no warnings

### Phase F — scikit-build bridge (stub)

28. Implement `cmake/skbuild_bridge.py` stub with `IVPMHook` and `collect_cmake_args()`
29. Guard with `try/except ImportError` for `scikit-build-core`

### Phase G — Final Polish and Release

30. Verify all tests pass, coverage ≥ 85%
31. Tag `v0.1.0` on `main` → CI publishes to PyPI + GitHub Pages
32. Confirm package installable: `pip install ivpm-build`
33. Smoke test Path 1 import: `python -c "from ivpm_build.setup import setup; print('ok')"`

---

## 9  Open Questions / Deferred Items

- **`distutils` deprecation**: `distutils.file_util.copy_file` used in existing `build_ext.py`
  is deprecated in Python 3.12+. Replace with `shutil.copy2` in the ported version.
- **Thread safety of `ivpm_data` globals**: the module-global pattern is preserved here
  for backward compatibility.  A context-object refactor is deferred to a later version.
- **`scikit-build-core` bridge maturity**: `skbuild_bridge.py` is shipped as a stub;
  full functionality deferred until scikit-build-core hook API is finalized.
- **Windows CI**: the existing CMake code has Windows-specific paths; a Windows runner
  job should be added to the CI matrix in a follow-up PR.
- **`importlib_metadata` on Python < 3.10**: `PkgInfoRgy` in `ivpm` uses this as a
  fallback; `ivpm-build` delegates to `ivpm` for registry queries, so this is not
  an `ivpm-build` concern.
