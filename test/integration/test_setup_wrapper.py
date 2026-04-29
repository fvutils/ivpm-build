"""Integration tests for ivpm_build.setup (wrapper + apply_ivpm_setup)."""
import sys
import pytest
from unittest.mock import patch, MagicMock
from setuptools import Extension

import ivpm_build.setup.ivpm_data as idata
from ivpm_build.setup import setup, apply_ivpm_setup, BuildExt, InstallLib


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_idata():
    idata._ivpm_extra_data = {}
    idata._ivpm_extdep_data = []
    idata._ivpm_hooks = {}
    idata._ivpm_ext_name_m = {}


# ---------------------------------------------------------------------------
# test_setup_wrapper_basic
# ---------------------------------------------------------------------------

def test_setup_wrapper_basic(tmp_path, monkeypatch):
    """setup() is callable and delegates to setuptools.setup without error."""
    monkeypatch.chdir(tmp_path)
    _reset_idata()

    with patch("ivpm_build.setup.wrapper._setup") as mock_st_setup:
        setup(name="testpkg", version="0.0.1")
        mock_st_setup.assert_called_once()


# ---------------------------------------------------------------------------
# test_apply_ivpm_setup_injects_include_dirs
# ---------------------------------------------------------------------------

def test_apply_ivpm_setup_injects_include_dirs(monkeypatch):
    """apply_ivpm_setup injects mock include dirs into ext.include_dirs."""
    _reset_idata()

    class _FakePkg:
        def getPath(self): return None
        def getIncDirs(self): return ["/fake/include"]
        def getLibDirs(self): return []
        def getLibs(self): return []
        def getDeps(self): return []

    class _FakeRgy:
        def hasPkg(self, n): return n == "mockpkg"
        def getPkg(self, n): return _FakePkg()
        def getPkgs(self): return ["mockpkg"]

    monkeypatch.setattr("ivpm_build.setup.wrapper._PkgInfoRgy_inst", lambda: _FakeRgy())

    ext = Extension("mymod._mymod", sources=[], include_dirs=[])
    apply_ivpm_setup(ext_modules=[ext], ivpm_extdep_pkgs=["mockpkg"])
    assert "/fake/include" in ext.include_dirs


# ---------------------------------------------------------------------------
# test_apply_ivpm_setup_no_ext
# ---------------------------------------------------------------------------

def test_apply_ivpm_setup_no_ext():
    """Calling apply_ivpm_setup with no ext_modules does not raise."""
    _reset_idata()
    apply_ivpm_setup()


# ---------------------------------------------------------------------------
# test_extra_data_stored
# ---------------------------------------------------------------------------

def test_extra_data_stored():
    _reset_idata()
    data = {"mypkg": [("build/lib/foo.so", "share")]}
    apply_ivpm_setup(ivpm_extra_data=data)
    assert idata._ivpm_extra_data == data
    _reset_idata()


# ---------------------------------------------------------------------------
# test_ext_name_map_stored
# ---------------------------------------------------------------------------

def test_ext_name_map_stored():
    _reset_idata()
    name_m = {"mymod._core": "{libpref}core{dllext}"}
    apply_ivpm_setup(ivpm_ext_name_m=name_m)
    assert idata._ivpm_ext_name_m == name_m
    _reset_idata()


# ---------------------------------------------------------------------------
# test_hooks_called
# ---------------------------------------------------------------------------

def test_hooks_called(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _reset_idata()

    pre_called = []
    post_called = []

    hooks = {
        idata.Phase_SetupPre: [lambda ctx: pre_called.append(True)],
        idata.Phase_SetupPost: [lambda ctx: post_called.append(True)],
    }

    with patch("ivpm_build.setup.wrapper._setup"):
        setup(
            name="testpkg",
            version="0.0.1",
            ivpm_hooks=hooks,
        )

    assert pre_called == [True]
    assert post_called == [True]
    _reset_idata()


# ---------------------------------------------------------------------------
# test_cmdclass_injected
# ---------------------------------------------------------------------------

def test_cmdclass_injected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _reset_idata()

    captured = {}

    def fake_setup(**kwargs):
        captured.update(kwargs)

    with patch("ivpm_build.setup.wrapper._setup", side_effect=fake_setup):
        setup(name="testpkg", version="0.0.1")

    assert captured["cmdclass"]["build_ext"] is BuildExt
    assert captured["cmdclass"]["install_lib"] is InstallLib


# ---------------------------------------------------------------------------
# test_cmdclass_not_overridden
# ---------------------------------------------------------------------------

def test_cmdclass_not_overridden(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _reset_idata()

    class UserBuildExt:
        pass

    captured = {}

    def fake_setup(**kwargs):
        captured.update(kwargs)

    with patch("ivpm_build.setup.wrapper._setup", side_effect=fake_setup):
        setup(
            name="testpkg",
            version="0.0.1",
            cmdclass={"build_ext": UserBuildExt},
        )

    assert captured["cmdclass"]["build_ext"] is UserBuildExt
