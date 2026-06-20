"""Integration tests for ivpm_build.backend (PEP 517 hooks)."""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

import ivpm_build.backend as backend
import ivpm_build.setup.ivpm_data as idata
from ivpm_build.config import IvpmBuildConfig, ExtraDataSpec, ExtNameMapEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_idata():
    idata._ivpm_extra_data = {}
    idata._ivpm_extdep_data = []
    idata._ivpm_hooks = {}
    idata._ivpm_ext_name_m = {}


# ---------------------------------------------------------------------------
# PEP 517 surface
# ---------------------------------------------------------------------------

def test_backend_pep517_surface():
    required = [
        "get_requires_for_build_wheel",
        "prepare_metadata_for_build_wheel",
        "build_wheel",
        "build_sdist",
        "build_editable",
        "get_requires_for_build_editable",
        "prepare_metadata_for_build_editable",
    ]
    for name in required:
        assert hasattr(backend, name), "missing PEP 517 hook: %s" % name


# ---------------------------------------------------------------------------
# get_requires_for_build_wheel
# ---------------------------------------------------------------------------

def test_get_requires_no_cmake(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = IvpmBuildConfig(cmake=False)

    with patch("ivpm_build.backend.load_config", return_value=cfg):
        with patch("ivpm_build.backend._st.get_requires_for_build_wheel", return_value=["setuptools"]):
            result = backend.get_requires_for_build_wheel()

    assert "ninja" not in result
    assert "setuptools" in result


def test_get_requires_cmake_non_windows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = IvpmBuildConfig(cmake=True)

    with patch("ivpm_build.backend.load_config", return_value=cfg):
        with patch("ivpm_build.backend._st.get_requires_for_build_wheel", return_value=[]):
            with patch.object(sys, "platform", "linux"):
                result = backend.get_requires_for_build_wheel()

    assert "ninja" in result


def test_get_requires_cmake_windows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = IvpmBuildConfig(cmake=True)

    with patch("ivpm_build.backend.load_config", return_value=cfg):
        with patch("ivpm_build.backend._st.get_requires_for_build_wheel", return_value=[]):
            with patch.object(sys, "platform", "win32"):
                result = backend.get_requires_for_build_wheel()

    assert "ninja" not in result


# ---------------------------------------------------------------------------
# _apply_ivpm_config
# ---------------------------------------------------------------------------

def test_apply_ivpm_config_extra_data():
    _reset_idata()
    cfg = IvpmBuildConfig(
        extra_data=[ExtraDataSpec(pkg="mypkg", src="build/foo.so", dst="share")]
    )
    backend._apply_ivpm_config(cfg)
    assert "mypkg" in idata._ivpm_extra_data
    assert idata._ivpm_extra_data["mypkg"] == [("build/foo.so", "share")]
    _reset_idata()


def test_apply_ivpm_config_ext_name_map():
    _reset_idata()
    cfg = IvpmBuildConfig(
        ext_name_map=[ExtNameMapEntry(module="mod._core", name="libcore.so")]
    )
    backend._apply_ivpm_config(cfg)
    assert idata._ivpm_ext_name_m == {"mod._core": "libcore.so"}
    _reset_idata()


# ---------------------------------------------------------------------------
# build_wheel / build_sdist / build_editable delegates
# ---------------------------------------------------------------------------

def test_build_wheel_delegates_to_setuptools(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = IvpmBuildConfig(cmake=False)

    with patch("ivpm_build.backend.load_config", return_value=cfg):
        with patch("ivpm_build.backend._st.build_wheel", return_value="wheel.whl") as mock_bw:
            result = backend.build_wheel(str(tmp_path))

    mock_bw.assert_called_once()
    assert result == "wheel.whl"


def test_build_sdist_delegates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with patch("ivpm_build.backend._st.build_sdist", return_value="pkg.tar.gz") as mock_bs:
        result = backend.build_sdist(str(tmp_path))

    mock_bs.assert_called_once()
    assert result == "pkg.tar.gz"


def test_build_editable_delegates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = IvpmBuildConfig(cmake=False)

    with patch("ivpm_build.backend.load_config", return_value=cfg):
        with patch("ivpm_build.backend._st.build_editable", return_value="editable.whl") as mock_be:
            result = backend.build_editable(str(tmp_path))

    mock_be.assert_called_once()
    assert result == "editable.whl"


# ---------------------------------------------------------------------------
# B2: editable build runs CMake when cmake=true
# ---------------------------------------------------------------------------

def test_build_editable_runs_cmake(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = IvpmBuildConfig(cmake=True)

    with patch("ivpm_build.backend.load_config", return_value=cfg):
        with patch("ivpm_build.backend._run_cmake") as mock_cmake:
            with patch("ivpm_build.backend._st.build_editable", return_value="editable.whl"):
                backend.build_editable(str(tmp_path))

    mock_cmake.assert_called_once()


def test_build_wheel_runs_cmake_then_stages(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = IvpmBuildConfig(cmake=True)
    order = []

    with patch("ivpm_build.backend.load_config", return_value=cfg):
        with patch("ivpm_build.backend._run_cmake", side_effect=lambda: order.append("cmake")):
            with patch("ivpm_build.backend._stage_extra_data",
                       side_effect=lambda c: order.append("stage") or []) as mock_stage:
                with patch("ivpm_build.backend._st.build_wheel",
                           side_effect=lambda *a, **k: order.append("build") or "w.whl"):
                    result = backend.build_wheel(str(tmp_path))

    assert result == "w.whl"
    assert order == ["cmake", "stage", "build"]
    mock_stage.assert_called_once()


def test_get_requires_editable_cmake_adds_ninja(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = IvpmBuildConfig(cmake=True)

    with patch("ivpm_build.backend.load_config", return_value=cfg):
        with patch("ivpm_build.backend._st.get_requires_for_build_editable", return_value=[]):
            with patch.object(sys, "platform", "linux"):
                result = backend.get_requires_for_build_editable()

    assert "ninja" in result


# ---------------------------------------------------------------------------
# B1: extra-data staging into package source dir
# ---------------------------------------------------------------------------

def test_stage_extra_data_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # produce a fake built library under build/lib
    libdir = tmp_path / "build" / "lib"
    libdir.mkdir(parents=True)
    (libdir / "libfoo.so").write_text("ELF")
    # pyproject with src-layout package-dir
    (tmp_path / "pyproject.toml").write_text(
        "[tool.setuptools]\npackage-dir = {\"\" = \"src\"}\n"
    )
    (tmp_path / "src" / "foo").mkdir(parents=True)

    cfg = IvpmBuildConfig(
        extra_data=[ExtraDataSpec(pkg="foo", src="build/{libdir}/{libpref}foo{dllext}", dst="")]
    )
    staged = backend._stage_extra_data(cfg)

    dst = tmp_path / "src" / "foo" / "libfoo.so"
    assert dst.is_file()
    assert len(staged) == 1

    backend._unstage_extra_data(staged)
    assert not dst.exists()


def test_stage_extra_data_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inc = tmp_path / "build" / "include" / "foo"
    inc.mkdir(parents=True)
    (inc / "foo.h").write_text("#pragma once")
    (tmp_path / "pyproject.toml").write_text(
        "[tool.setuptools]\npackage-dir = {\"\" = \"src\"}\n"
    )
    (tmp_path / "src" / "foo").mkdir(parents=True)

    cfg = IvpmBuildConfig(
        extra_data=[ExtraDataSpec(pkg="foo", src="build/include/foo", dst="share/include")]
    )
    staged = backend._stage_extra_data(cfg)

    dst = tmp_path / "src" / "foo" / "share" / "include" / "foo" / "foo.h"
    assert dst.is_file()

    backend._unstage_extra_data(staged)
    assert not (tmp_path / "src" / "foo" / "share" / "include" / "foo").exists()


def test_stage_extra_data_missing_src_warns(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cfg = IvpmBuildConfig(
        extra_data=[ExtraDataSpec(pkg="foo", src="build/{libdir}/{libpref}nope{dllext}", dst="")]
    )
    staged = backend._stage_extra_data(cfg)
    assert staged == []
    assert "not found" in capsys.readouterr().out


def test_pkg_src_dir_resolution():
    assert backend._pkg_src_dir("foo", {"": "src"}) == os.path.join("src", "foo")
    assert backend._pkg_src_dir("foo.bar", {"": "src"}) == os.path.join("src", "foo", "bar")
    assert backend._pkg_src_dir("foo", {"foo": "python/foo"}) == os.path.join("python", "foo")
    assert backend._pkg_src_dir("foo", {}) == "foo"
