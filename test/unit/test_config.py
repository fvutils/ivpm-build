"""Unit tests for ivpm_build.config."""
import os
import pytest

from ivpm_build.config import (
    IvpmBuildConfig,
    ExtraDataSpec,
    ExtNameMapEntry,
    load_config,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write(tmp_path, content):
    p = tmp_path / "pyproject.toml"
    p.write_text(content)
    return str(p)


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_load_config_missing_file(tmp_path):
    cfg = load_config(str(tmp_path / "nonexistent.toml"))
    assert cfg == IvpmBuildConfig()


def test_load_config_empty_file(tmp_path):
    p = _write(tmp_path, "[project]\nname='foo'\n")
    cfg = load_config(p)
    assert cfg == IvpmBuildConfig()


def test_load_config_cmake_true(tmp_path):
    p = _write(tmp_path, "[tool.ivpm-build]\ncmake = true\n")
    cfg = load_config(p)
    assert cfg.cmake is True


def test_load_config_cmake_false_default(tmp_path):
    p = _write(tmp_path, "[tool.ivpm-build]\n")
    cfg = load_config(p)
    assert cfg.cmake is False


def test_load_config_ivpm_dep_pkgs(tmp_path):
    p = _write(tmp_path, '[tool.ivpm-build]\nivpm-dep-pkgs = ["pkg_a", "pkg_b"]\n')
    cfg = load_config(p)
    assert cfg.ivpm_dep_pkgs == ["pkg_a", "pkg_b"]


def test_load_config_extra_data(tmp_path):
    content = """
[tool.ivpm-build]
[[tool.ivpm-build.extra-data]]
pkg = "mypkg"
src = "build/lib/foo.so"
dst = "share"
"""
    p = _write(tmp_path, content)
    cfg = load_config(p)
    assert len(cfg.extra_data) == 1
    assert cfg.extra_data[0] == ExtraDataSpec(pkg="mypkg", src="build/lib/foo.so", dst="share")


def test_load_config_ext_name_map(tmp_path):
    content = """
[tool.ivpm-build]
[[tool.ivpm-build.ext-name-map]]
module = "mymod._core"
name = "{libpref}core{dllext}"
"""
    p = _write(tmp_path, content)
    cfg = load_config(p)
    assert len(cfg.ext_name_map) == 1
    assert cfg.ext_name_map[0] == ExtNameMapEntry(module="mymod._core", name="{libpref}core{dllext}")


def test_load_config_combined(tmp_path):
    content = """
[tool.ivpm-build]
cmake = true
ivpm-dep-pkgs = ["dep1"]

[[tool.ivpm-build.extra-data]]
pkg = "mypkg"
src = "src"
dst = "dst"

[[tool.ivpm-build.ext-name-map]]
module = "mod"
name = "libmod.so"
"""
    p = _write(tmp_path, content)
    cfg = load_config(p)
    assert cfg.cmake is True
    assert cfg.ivpm_dep_pkgs == ["dep1"]
    assert len(cfg.extra_data) == 1
    assert len(cfg.ext_name_map) == 1


def test_load_config_invalid_toml(tmp_path):
    p = _write(tmp_path, "this is: not [valid toml\n")
    with pytest.raises(ValueError, match="Failed to parse"):
        load_config(str(p))
