# ivpm-build

Build tooling for Python packages that wrap native C/C++ extensions, with
[IVPM](https://github.com/fvutils/ivpm) integration for cross-package
dependency resolution.

`ivpm-build` handles the full native-extension build pipeline:

1. **CMake build** — configure, build, and install native code via `CmakeBuilder`
2. **Python extension compile** — Cython/C++ extension compilation via a
   `BuildExt` command that injects include and library paths from IVPM-managed
   dependencies
3. **Shared-library packaging** — `InstallLib` copies native `.so`/`.dll`/`.dylib`
   files into the wheel alongside the Python extension module
4. **IVPM dependency resolution** — queries the IVPM package registry
   (`PkgInfoRgy`) to obtain include dirs, library dirs, and Cython `.pxd` files
   from other IVPM-managed native packages listed in `ivpm.yaml`

## When to use `ivpm-build`

Use `ivpm-build` when your Python package:

- wraps a C/C++ library built with CMake, **and/or**
- exposes a Cython extension that links against native libraries from other
  IVPM-managed packages (e.g. `debug-mgr`, `ciostream`, `antlr4-runtime`)

## Installation

```bash
pip install ivpm-build
```

## Quick Start

### `pyproject.toml` (recommended)

```toml
[build-system]
requires = ["setuptools>=64", "wheel", "cython", "ivpm-build", "ivpm"]
build-backend = "setuptools.build_meta"
```

### `setup.py`

```python
from ivpm_build.setup import setup   # replaces ivpm.setup.setup
from setuptools import Extension

ext = Extension("mypkg._core", sources=["python/core.pyx"], language="c++")

setup(
    name="mypkg",
    ext_modules=[ext],
    ivpm_extdep_pkgs=["debug-mgr", "ciostream"],   # IVPM deps → include/lib paths
    ivpm_extra_data={
        "mypkg": [
            ("build/{libdir}/{libpref}mypkg{dllext}", ""),  # bundle native lib
        ]
    },
)
```

`BuildExt` (injected by `setup()`) automatically resolves include directories,
library directories, and Cython `.pxd` search paths from each package listed in
`ivpm_extdep_pkgs` via the IVPM registry.

### CMake-only build

```python
from ivpm_build.cmake import CmakeBuilder

builder = CmakeBuilder(proj_dir="/path/to/project")
builder.run()   # cmake configure → build → install
```

## Integration paths

| Path | When to use |
|---|---|
| **Path 1** — swap `from ivpm.setup import setup` → `from ivpm_build.setup import setup` | Existing `setup.py` project, zero-change migration |
| **Path 2** — `apply_ivpm_setup()` in `setup.py` + `pyproject.toml` metadata | Fine-grained control over extension descriptors |
| **Path 3** — pure `pyproject.toml` with `build-backend = "ivpm_build.backend"` | New projects or full modernisation |

See the [migration guide](https://fvutils.github.io/ivpm-build/migration.html)
for step-by-step instructions.

## Documentation

Full documentation: https://fvutils.github.io/ivpm-build

## License

Apache 2.0 — see [LICENSE](LICENSE)
