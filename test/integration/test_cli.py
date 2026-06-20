"""Tests for the ``python -m ivpm_build`` CLI (B3)."""
import pytest
from unittest.mock import patch

from ivpm_build.__main__ import main


def test_cli_build_invokes_cmake(tmp_path, monkeypatch):
    (tmp_path / "CMakeLists.txt").write_text("project(x)")
    monkeypatch.chdir(tmp_path)

    with patch("ivpm_build.__main__.CmakeBuilder") as MockCB:
        rc = main(["build"])

    assert rc == 0
    MockCB.assert_called_once()
    _, kwargs = MockCB.call_args
    assert kwargs.get("debug") is False
    MockCB.return_value.run.assert_called_once()


def test_cli_build_debug_flag(tmp_path, monkeypatch):
    (tmp_path / "CMakeLists.txt").write_text("project(x)")
    monkeypatch.chdir(tmp_path)

    with patch("ivpm_build.__main__.CmakeBuilder") as MockCB:
        main(["build", "--debug"])

    _, kwargs = MockCB.call_args
    assert kwargs.get("debug") is True


def test_cli_build_requires_cmakelists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        main(["build"])


def test_cli_requires_subcommand():
    with pytest.raises(SystemExit):
        main([])
