"""PEP 517 build backend for IVPM-managed projects.

Wraps ``setuptools.build_meta`` and injects IVPM configuration parsed from
``[tool.ivpm-build]`` in ``pyproject.toml`` before each hook is invoked.
"""
import os
import sys

import setuptools.build_meta as _st

from .config import load_config
from .setup import ivpm_data as _idata


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
        from .cmake.cmake_builder import CmakeBuilder
        CmakeBuilder(os.getcwd()).run()
    return _st.build_wheel(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory, config_settings=None):
    return _st.build_sdist(sdist_directory, config_settings)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    config = load_config()
    _apply_ivpm_config(config)
    return _st.build_editable(wheel_directory, config_settings, metadata_directory)


def get_requires_for_build_editable(config_settings=None):
    return _st.get_requires_for_build_editable(config_settings)


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    return _st.prepare_metadata_for_build_editable(metadata_directory, config_settings)
