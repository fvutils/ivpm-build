"""Parser for the [tool.ivpm-build] section of pyproject.toml."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

try:
    import tomllib  # Python >= 3.11
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError as exc:
        raise ImportError(
            "tomli is required on Python < 3.11: pip install tomli"
        ) from exc


@dataclass
class ExtraDataSpec:
    pkg: str
    src: str
    dst: str


@dataclass
class ExtNameMapEntry:
    module: str
    name: str


@dataclass
class IvpmBuildConfig:
    cmake: bool = False
    ivpm_dep_pkgs: List[str] = field(default_factory=list)
    extra_data: List[ExtraDataSpec] = field(default_factory=list)
    ext_name_map: List[ExtNameMapEntry] = field(default_factory=list)


def load_config(pyproject_path: str = "pyproject.toml") -> IvpmBuildConfig:
    """Parse [tool.ivpm-build] section from *pyproject_path*.

    Returns a default :class:`IvpmBuildConfig` if the file does not exist or
    if the section is absent.  Raises :class:`ValueError` on malformed TOML.
    """
    if not os.path.isfile(pyproject_path):
        return IvpmBuildConfig()

    try:
        with open(pyproject_path, "rb") as fh:
            data = tomllib.load(fh)
    except Exception as exc:
        raise ValueError("Failed to parse %s: %s" % (pyproject_path, exc)) from exc

    section = data.get("tool", {}).get("ivpm-build", {})
    if not section:
        return IvpmBuildConfig()

    cmake = bool(section.get("cmake", False))
    ivpm_dep_pkgs = list(section.get("ivpm-dep-pkgs", []))

    extra_data = [
        ExtraDataSpec(
            pkg=entry["pkg"],
            src=entry["src"],
            dst=entry["dst"],
        )
        for entry in section.get("extra-data", [])
    ]

    ext_name_map = [
        ExtNameMapEntry(
            module=entry["module"],
            name=entry["name"],
        )
        for entry in section.get("ext-name-map", [])
    ]

    return IvpmBuildConfig(
        cmake=cmake,
        ivpm_dep_pkgs=ivpm_dep_pkgs,
        extra_data=extra_data,
        ext_name_map=ext_name_map,
    )
