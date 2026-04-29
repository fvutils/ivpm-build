# ivpm-build

Build helpers and PEP 517 backend for [IVPM](https://github.com/fvutils/ivpm)-managed Python extension projects.

`ivpm-build` is a standalone package that extracts the build infrastructure
from `ivpm` so projects can use it without depending on the full IVPM tool chain
at build time.

## Features

- Drop-in replacement for `ivpm.setup.setup()` (backward compatible)
- `[tool.ivpm-build]` config section in `pyproject.toml`
- PEP 517 build backend wrapping `setuptools.build_meta`
- CMake helpers (`CmakeBuilder`) decoupled from the setuptools command hierarchy
- Optional `scikit-build-core` bridge (`IVPMHook`)

## Installation

```bash
pip install ivpm-build
```

With CMake support:

```bash
pip install ivpm-build[cmake]
```

## Quick Start

### Path 1 — Legacy `setup.py` (one-line change)

```python
# Before
from ivpm.setup import setup
# After
from ivpm_build.setup import setup
```

### Path 2 — Hybrid `pyproject.toml` + `setup.py`

Add to `pyproject.toml`:

```toml
[build-system]
requires = ["ivpm-build", "setuptools>=64"]
build-backend = "setuptools.build_meta"

[tool.ivpm-build]
ivpm-dep-pkgs = ["mypkg"]
```

In `setup.py`:

```python
from setuptools import setup
from setuptools import Extension
from ivpm_build.setup import apply_ivpm_setup

ext = Extension("mymod._mymod", sources=["src/mymod.cpp"])
apply_ivpm_setup(ext_modules=[ext], ivpm_extdep_pkgs=["mypkg"])
setup(name="mymod", ext_modules=[ext])
```

### Path 3 — Pure `pyproject.toml`

```toml
[build-system]
requires = ["ivpm-build", "setuptools>=64"]
build-backend = "ivpm_build.backend"

[tool.ivpm-build]
cmake = true
ivpm-dep-pkgs = ["mypkg"]
```

## Documentation

Full documentation is published at https://fvutils.github.io/ivpm-build

## License

Apache 2.0 — see [LICENSE](LICENSE)
