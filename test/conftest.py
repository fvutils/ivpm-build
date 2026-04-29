"""Shared test fixtures for ivpm-build tests."""
import os
import sys
import pytest


@pytest.fixture
def tmp_pyproject(tmp_path):
    """Return a helper that writes a pyproject.toml into *tmp_path* and
    returns its path."""

    def _make(content: str) -> str:
        p = tmp_path / "pyproject.toml"
        p.write_text(content)
        return str(p)

    return _make


@pytest.fixture
def mock_pkg_info_rgy(monkeypatch):
    """Return a factory that injects a fake PkgInfoRgy into ivpm_build.setup.wrapper."""

    class _FakePkg:
        def __init__(self, inc=(), lib=(), libs=(), deps=(), path=None):
            self._inc = list(inc)
            self._lib = list(lib)
            self._libs = list(libs)
            self._deps = list(deps)
            self._path = path

        def getPath(self):
            return self._path

        def getIncDirs(self):
            return self._inc

        def getLibDirs(self):
            return self._lib

        def getLibs(self):
            return self._libs

        def getDeps(self):
            return self._deps

    class _FakeRgy:
        def __init__(self, pkgs):
            self._pkgs = pkgs  # dict name -> _FakePkg

        def hasPkg(self, name):
            return name in self._pkgs

        def getPkg(self, name):
            return self._pkgs[name]

        def getPkgs(self):
            return list(self._pkgs.keys())

    class _Factory:
        def __call__(self, pkgs):
            rgy = _FakeRgy(pkgs)
            monkeypatch.setattr(
                "ivpm_build.setup.wrapper._PkgInfoRgy_inst",
                lambda: rgy,
            )
            return rgy

        def make_pkg(self, **kwargs):
            return _FakePkg(**kwargs)

    return _Factory()
