"""Unit tests for ivpm_build.cmake.cmake_builder.CmakeBuilder."""
import os
import subprocess
import pytest
from unittest.mock import patch, MagicMock, call

from ivpm_build.cmake.cmake_builder import CmakeBuilder


# ---------------------------------------------------------------------------
# Construction / defaults
# ---------------------------------------------------------------------------

def test_cmake_builder_defaults(tmp_path):
    cb = CmakeBuilder(str(tmp_path))
    assert cb.proj_dir == str(tmp_path)
    assert cb.build_dir == os.path.join(str(tmp_path), "build")
    assert cb.debug is False
    assert cb.cmake_build_tool in ("Ninja", "Unix Makefiles", os.environ.get("CMAKE_BUILD_TOOL", "Ninja"))


def test_cmake_build_tool_env(tmp_path, monkeypatch):
    monkeypatch.setenv("CMAKE_BUILD_TOOL", "Unix Makefiles")
    cb = CmakeBuilder(str(tmp_path))
    assert cb.cmake_build_tool == "Unix Makefiles"


def test_cmake_build_tool_explicit(tmp_path):
    cb = CmakeBuilder(str(tmp_path), cmake_build_tool="Unix Makefiles")
    assert cb.cmake_build_tool == "Unix Makefiles"


def test_cmake_build_tool_unsupported(tmp_path, monkeypatch):
    # Create a fake packages dir so configure() doesn't fail on path discovery
    (tmp_path / "packages").mkdir()
    cb = CmakeBuilder(str(tmp_path), cmake_build_tool="BadTool")
    with pytest.raises(ValueError, match="not supported"):
        cb.configure()


# ---------------------------------------------------------------------------
# run() calls configure → build → install in order (mock subprocess)
# ---------------------------------------------------------------------------

def test_run_calls_sequence(tmp_path):
    (tmp_path / "packages").mkdir()
    cb = CmakeBuilder(str(tmp_path))
    order = []

    with patch.object(cb, "configure", side_effect=lambda *a, **kw: order.append("configure")):
        with patch.object(cb, "build", side_effect=lambda: order.append("build")):
            with patch.object(cb, "install", side_effect=lambda: order.append("install")):
                cb.run()

    assert order == ["configure", "build", "install"]


# ---------------------------------------------------------------------------
# cmake failure raises RuntimeError
# ---------------------------------------------------------------------------

def test_cmake_failure_raises(tmp_path, monkeypatch):
    (tmp_path / "packages").mkdir()
    cb = CmakeBuilder(str(tmp_path))

    failed = MagicMock()
    failed.returncode = 1

    with patch("subprocess.run", return_value=failed):
        with pytest.raises(RuntimeError, match="cmake configure failed"):
            cb.configure()


def test_build_failure_raises(tmp_path, monkeypatch):
    (tmp_path / "packages").mkdir()
    cb = CmakeBuilder(str(tmp_path))
    ok = MagicMock(returncode=0)
    fail = MagicMock(returncode=1)

    # configure passes, build fails
    with patch("subprocess.run", side_effect=[ok, fail]):
        cb.configure()
        with pytest.raises(RuntimeError, match="ninja build failed"):
            cb.build()


# ---------------------------------------------------------------------------
# platform-specific configure args
# ---------------------------------------------------------------------------

def test_configure_args_darwin(tmp_path, monkeypatch):
    import platform as _platform
    monkeypatch.setattr(_platform, "system", lambda: "Darwin")
    (tmp_path / "packages").mkdir()

    captured_cmd = []

    def fake_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fake_run):
        cb = CmakeBuilder(str(tmp_path), cmake_build_tool="Ninja")
        cb.configure()

    assert any("x86_64;arm64" in arg for arg in captured_cmd)


def test_configure_args_linux(tmp_path, monkeypatch):
    import platform as _platform
    monkeypatch.setattr(_platform, "system", lambda: "Linux")
    (tmp_path / "packages").mkdir()

    captured_cmd = []

    def fake_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fake_run):
        cb = CmakeBuilder(str(tmp_path), cmake_build_tool="Ninja")
        cb.configure()

    assert not any("OSX" in arg for arg in captured_cmd)


def test_configure_args_windows(tmp_path, monkeypatch):
    import platform as _platform
    monkeypatch.setattr(_platform, "system", lambda: "Windows")
    (tmp_path / "packages").mkdir()

    captured_cmd = []

    def fake_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fake_run):
        cb = CmakeBuilder(str(tmp_path), cmake_build_tool="Ninja")
        cb.configure()

    assert not any("OSX" in arg for arg in captured_cmd)
