"""Unit tests for ivpm_build.setup.ivpm_data."""
import os
import platform
import sys
import pytest

import ivpm_build.setup.ivpm_data as idata


# ---------------------------------------------------------------------------
# expand_libvars
# ---------------------------------------------------------------------------

def test_expand_libvars_linux(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    result = idata.expand_libvars("{libpref}foo{dllext}", libdir="lib")
    assert result == "libfoo.so"


def test_expand_libvars_darwin(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    result = idata.expand_libvars("{libpref}foo{dllext}", libdir="lib")
    assert result == "libfoo.dylib"


def test_expand_libvars_windows(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    result = idata.expand_libvars("{libpref}foo{dllext}", libdir="lib")
    assert result == "foo.dll"


def test_expand_libvars_libdir_auto_lib(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    # No build/lib64 dir → should use "lib"
    result = idata.expand_libvars("{libdir}/foo", )
    assert result == "lib/foo"


def test_expand_libvars_libdir_auto_lib64(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "build" / "lib64").mkdir(parents=True)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    result = idata.expand_libvars("{libdir}/foo")
    assert result == "lib64/foo"


def test_expand_libvars_libdir_explicit(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    result = idata.expand_libvars("{libdir}/foo", libdir="mylib")
    assert result == "mylib/foo"


# ---------------------------------------------------------------------------
# hooks
# ---------------------------------------------------------------------------

def test_hooks_empty():
    idata._ivpm_hooks = {}
    result = idata.get_hooks("setup.pre")
    assert result == []


def test_hooks_registered():
    called = []

    def my_hook(ctx):
        called.append(ctx)

    idata._ivpm_hooks = {idata.Phase_SetupPre: [my_hook]}
    hooks = idata.get_hooks(idata.Phase_SetupPre)
    assert hooks == [my_hook]
    hooks[0]("ctx")
    assert called == ["ctx"]

    # Clean up
    idata._ivpm_hooks = {}


# ---------------------------------------------------------------------------
# get_* accessors
# ---------------------------------------------------------------------------

def test_get_ivpm_extra_data():
    idata._ivpm_extra_data = {"mypkg": [("src", "dst")]}
    result = idata.get_ivpm_extra_data()
    assert result == {"mypkg": [("src", "dst")]}
    idata._ivpm_extra_data = {}


def test_get_ivpm_extdep_data():
    idata._ivpm_extdep_data = [("a", "b")]
    result = idata.get_ivpm_extdep_data()
    assert result == [("a", "b")]
    idata._ivpm_extdep_data = []


def test_get_ivpm_ext_name_m():
    idata._ivpm_ext_name_m = {"mod": "name"}
    result = idata.get_ivpm_ext_name_m()
    assert result == {"mod": "name"}
    idata._ivpm_ext_name_m = {}
