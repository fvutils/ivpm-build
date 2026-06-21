"""PEP 517 build backend for IVPM-managed projects.

Wraps ``setuptools.build_meta`` and injects IVPM configuration parsed from
``[tool.ivpm-build]`` in ``pyproject.toml`` before each hook is invoked.
"""
import contextlib
import importlib
import os
import platform
import shutil
import sys

import setuptools.build_meta as _st

from .config import load_config
from .setup import ivpm_data as _idata
from .setup.ivpm_data import expand_libvars


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


# ---------------------------------------------------------------------------
# extra-data staging
#
# In the pure-pyproject (backend) path there is no setup.py, so the InstallLib
# command that copies ``extra-data`` artifacts into the wheel is never wired in.
# Instead we copy each ``extra-data`` entry into the package's *source* directory
# before delegating to setuptools, so the files are picked up as ordinary package
# data, then remove them afterwards to keep the source tree clean.
# ---------------------------------------------------------------------------

def _load_setuptools_package_dir():
    """Return the ``[tool.setuptools] package-dir`` mapping from pyproject.toml.

    Returns an empty dict when the file or section is absent.
    """
    path = "pyproject.toml"
    if not os.path.isfile(path):
        return {}
    try:
        import tomllib  # Python >= 3.11
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return data.get("tool", {}).get("setuptools", {}).get("package-dir", {}) or {}


def _pkg_src_dir(pkg, package_dir):
    """Resolve a package name to its source directory using setuptools' rules."""
    parts = pkg.split(".")
    if pkg in package_dir:
        return package_dir[pkg].replace("/", os.sep)
    if "" in package_dir:
        return os.path.join(package_dir[""], *parts)
    return os.path.join(*parts)


def _resolve_extra_data_src(src):
    """Expand template vars in *src* and return an existing absolute path or None.

    Tries the default ``{libdir}`` resolution first, then explicit ``lib``/
    ``lib64`` so a single spec works regardless of where CMake placed the lib.
    """
    for cand in (
        expand_libvars(src),
        expand_libvars(src, libdir="lib"),
        expand_libvars(src, libdir="lib64"),
    ):
        p = cand if os.path.isabs(cand) else os.path.join(os.getcwd(), cand)
        if os.path.exists(p):
            return p
    return None


def _stage_extra_data(config):
    """Copy ``extra-data`` artifacts into package source dirs for the wheel build.

    Returns the list of paths created, so the caller can remove them afterwards.
    """
    staged = []
    if not config.extra_data:
        return staged

    package_dir = _load_setuptools_package_dir()

    for spec in config.extra_data:
        src = _resolve_extra_data_src(spec.src)
        if src is None:
            print("ivpm-build: warning: extra-data src not found: %s" % spec.src)
            continue

        pkg_dir = _pkg_src_dir(spec.pkg, package_dir)

        if os.path.isfile(src):
            dst_dir = os.path.join(pkg_dir, spec.dst)
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, os.path.basename(src))
            shutil.copyfile(src, dst)
            staged.append(dst)
            print("ivpm-build: staged %s -> %s" % (src, dst))

            # On Windows ship the import library alongside the DLL.
            if "{dllext}" in spec.src and platform.system() == "Windows":
                link_lib = src.replace(".dll", ".lib")
                if os.path.isfile(link_lib):
                    link_dst = os.path.join(dst_dir, os.path.basename(link_lib))
                    shutil.copyfile(link_lib, link_dst)
                    staged.append(link_dst)
        elif os.path.isdir(src):
            dst = os.path.join(pkg_dir, spec.dst, os.path.basename(src))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            staged.append(dst)
            print("ivpm-build: staged %s/ -> %s/" % (src, dst))

    return staged


def _unstage_extra_data(staged):
    for p in staged:
        try:
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.isfile(p):
                os.remove(p)
        except OSError as e:
            print("ivpm-build: warning: failed to clean staged %s (%s)" % (p, e))


def _run_cmake():
    from .cmake.cmake_builder import CmakeBuilder
    CmakeBuilder(os.getcwd()).run()


# ---------------------------------------------------------------------------
# Platform wheel tagging
#
# A project that ships a CMake-built native library *loaded via ctypes* has no
# Python C-extension (no ``ext_modules``).  setuptools therefore considers it a
# pure-Python project and emits a ``py3-none-any`` wheel -- even though the
# wheel now contains a platform-specific ``.so``/``.dll``/``.dylib``.  Such a
# wheel is wrong (it would install on the wrong OS/arch) and tools like
# ``cibuildwheel`` reject it ("Build failed because a pure Python wheel was
# generated").
#
# Because the library is loaded via ctypes it is *not* tied to a specific
# CPython ABI, so the correct tag is ``py3-none-<platform>`` (e.g.
# ``py3-none-manylinux2014_x86_64`` after auditwheel) -- platform-specific but
# interpreter/ABI agnostic -- NOT ``cp311-cp311-...`` (which would force a
# redundant build per Python version).
#
# There is no setup.py in the pure-pyproject path, so we cannot register a
# ``cmdclass``.  Instead we patch the ``bdist_wheel`` command class in-process
# for the duration of the delegated build.  setuptools.build_meta runs setup()
# in this same process, so the patch takes effect; we restore it afterwards.
# ---------------------------------------------------------------------------

# Candidate locations of the bdist_wheel command class, newest first.
#   setuptools >= 70.1 vendors it at setuptools.command.bdist_wheel
#   older setuptools delegates to the standalone ``wheel`` package
_BDIST_WHEEL_MODULES = (
    "setuptools.command.bdist_wheel",
    "wheel.bdist_wheel",
)


@contextlib.contextmanager
def _platform_wheel_tag():
    """Force an impure, ABI-agnostic ``py3-none-<platform>`` wheel tag.

    Two things have to change versus a default setuptools build of an
    extension-less project:

    1. The distribution must be treated as carrying platform binaries so the
       package is installed into *platlib* -- otherwise the wheel root (platlib)
       and the installed files (purelib) disagree and setuptools relocates the
       package under ``<name>.data/purelib/``.  We do this by making
       ``Distribution.has_ext_modules()`` report ``True`` for the build, which
       also flips ``bdist_wheel.root_is_pure`` to ``False`` automatically.

    2. The wheel tag must be ``py3-none-<plat>`` (interpreter/ABI agnostic),
       because the native library is loaded via ctypes and is not bound to a
       CPython ABI.  A project that genuinely ships a C-extension keeps its
       original ``cpXX-<abi>-<plat>`` tag.

    The genuine ``has_ext_modules`` answer is recorded per-distribution as
    ``_ivpm_real_ext`` so the tag logic can tell the two cases apart.
    """
    from setuptools.dist import Distribution

    patched = []

    # (1) platlib placement -- also makes root_is_pure False for free.
    orig_has_ext = Distribution.has_ext_modules

    def has_ext_modules(self, _orig=orig_has_ext):
        if not hasattr(self, "_ivpm_real_ext"):
            self._ivpm_real_ext = bool(_orig(self))
        return True

    Distribution.has_ext_modules = has_ext_modules

    # (2) interpreter/ABI-agnostic tag, unless there is a real C-extension.
    for mod_name in _BDIST_WHEEL_MODULES:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        cls = getattr(mod, "bdist_wheel", None)
        if cls is None or getattr(cls, "_ivpm_tag_patched", False):
            continue

        orig_get_tag = cls.get_tag

        def get_tag(self, _orig=orig_get_tag):
            impl, abi, plat = _orig(self)
            if getattr(self.distribution, "_ivpm_real_ext", False):
                return impl, abi, plat
            return "py3", "none", plat

        cls.get_tag = get_tag
        cls._ivpm_tag_patched = True
        patched.append((cls, orig_get_tag))
        # The first importable module in priority order is the canonical
        # bdist_wheel command; patching further (legacy) copies is unnecessary
        # and would emit deprecation warnings.
        break

    try:
        yield
    finally:
        Distribution.has_ext_modules = orig_has_ext
        for cls, orig_get_tag in patched:
            cls.get_tag = orig_get_tag
            del cls._ivpm_tag_patched


# ---------------------------------------------------------------------------
# PEP 517 hooks
# ---------------------------------------------------------------------------

def get_requires_for_build_wheel(config_settings=None):
    config = load_config()
    base = list(_st.get_requires_for_build_wheel(config_settings))
    if config.cmake and sys.platform != "win32":
        base.append("ninja")
    return base


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    return _st.prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    config = load_config()
    _apply_ivpm_config(config)
    if config.cmake:
        _run_cmake()
    staged = _stage_extra_data(config)
    try:
        # When CMake produced native artifacts, force a platform-specific wheel
        # tag so the wheel is not mistagged as pure-Python (py3-none-any).
        if config.cmake:
            with _platform_wheel_tag():
                return _st.build_wheel(
                    wheel_directory, config_settings, metadata_directory)
        return _st.build_wheel(wheel_directory, config_settings, metadata_directory)
    finally:
        _unstage_extra_data(staged)


def build_sdist(sdist_directory, config_settings=None):
    return _st.build_sdist(sdist_directory, config_settings)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    config = load_config()
    _apply_ivpm_config(config)
    if config.cmake:
        _run_cmake()
    return _st.build_editable(wheel_directory, config_settings, metadata_directory)


def get_requires_for_build_editable(config_settings=None):
    config = load_config()
    base = list(_st.get_requires_for_build_editable(config_settings))
    if config.cmake and sys.platform != "win32":
        base.append("ninja")
    return base


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    return _st.prepare_metadata_for_build_editable(metadata_directory, config_settings)
