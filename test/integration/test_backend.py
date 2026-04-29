"""Integration tests for ivpm_build.backend (PEP 517 hooks)."""
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
