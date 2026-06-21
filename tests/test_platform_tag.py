"""Tests for the platform-wheel-tag forcing in ivpm_build.backend.

A CMake project that ships a ctypes-loaded native library has no ``ext_modules``
and would otherwise be tagged ``py3-none-any`` (pure Python). The backend must
force ``py3-none-<platform>`` so the wheel is platform-specific but still
interpreter/ABI agnostic, and so cibuildwheel accepts it.
"""
import os
import sysconfig
import zipfile

import pytest

import setuptools.build_meta as _st

from ivpm_build.backend import _platform_wheel_tag


PYPROJECT = """\
[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.build_meta"

[project]
name = "tagdemo"
version = "0.0.1"

[tool.setuptools]
packages = ["tagdemo"]
package-dir = {"" = "src"}
"""


def _make_project(root):
    (root / "src" / "tagdemo").mkdir(parents=True)
    (root / "src" / "tagdemo" / "__init__.py").write_text("")
    # A staged native-library stand-in: an ordinary package-data file.
    (root / "src" / "tagdemo" / "libtagdemo.so").write_bytes(b"\x7fELF stub")
    (root / "pyproject.toml").write_text(PYPROJECT)
    (root / "pyproject.toml").write_text(
        PYPROJECT + '\n[tool.setuptools.package-data]\ntagdemo = ["*.so"]\n'
    )


def _build(root, wheeldir, force):
    """Build a wheel for the temp project, returning the wheel filename."""
    cwd = os.getcwd()
    os.chdir(root)
    try:
        if force:
            with _platform_wheel_tag():
                return _st.build_wheel(str(wheeldir))
        return _st.build_wheel(str(wheeldir))
    finally:
        os.chdir(cwd)


def test_unforced_build_is_pure(tmp_path):
    """Baseline: without the context manager setuptools tags it py3-none-any."""
    proj = tmp_path / "proj"
    _make_project(proj)
    wheels = tmp_path / "out"
    wheels.mkdir()
    name = _build(proj, wheels, force=False)
    assert name.endswith("-py3-none-any.whl"), name


def test_forced_build_is_platform_specific(tmp_path):
    """With the context manager the wheel is py3-none-<platform>, not -any."""
    proj = tmp_path / "proj"
    _make_project(proj)
    wheels = tmp_path / "out"
    wheels.mkdir()
    name = _build(proj, wheels, force=True)

    assert not name.endswith("-py3-none-any.whl"), name
    assert "-py3-none-" in name, name

    plat = sysconfig.get_platform().replace("-", "_").replace(".", "_")
    assert name.endswith("-py3-none-%s.whl" % plat), (name, plat)

    # The staged native lib must still be inside the wheel.
    with zipfile.ZipFile(wheels / name) as zf:
        assert any(n.endswith("libtagdemo.so") for n in zf.namelist())


def test_patch_is_restored(tmp_path):
    """The patched classes must be returned to their original behaviour."""
    import setuptools.command.bdist_wheel as bw
    from setuptools.dist import Distribution

    before_get_tag = bw.bdist_wheel.get_tag
    before_has_ext = Distribution.has_ext_modules
    with _platform_wheel_tag():
        assert getattr(bw.bdist_wheel, "_ivpm_tag_patched", False)
        assert Distribution.has_ext_modules is not before_has_ext
    assert not getattr(bw.bdist_wheel, "_ivpm_tag_patched", False)
    assert bw.bdist_wheel.get_tag is before_get_tag
    assert Distribution.has_ext_modules is before_has_ext
