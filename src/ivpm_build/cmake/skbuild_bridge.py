"""Optional scikit-build-core bridge.

This module is a stub that will be completed once the scikit-build-core hook
API is finalised.  It is safe to import even when scikit-build-core is absent.
"""
try:
    from scikit_build_core.build import BuildHookInterface as _BHI  # type: ignore
    _SKBUILD_AVAILABLE = True
except ImportError:
    _BHI = object  # type: ignore[misc,assignment]
    _SKBUILD_AVAILABLE = False


def collect_cmake_args(dep_pkgs: list = None) -> list:
    """Return a list of ``-DCMAKE_PREFIX_PATH=...`` args from the IVPM
    pkg_info registry for *dep_pkgs* (defaults to all registered packages)."""
    from ivpm.pkg_info.pkg_info_rgy import PkgInfoRgy

    rgy = PkgInfoRgy.inst()
    prefix_paths = []

    pkgs_to_query = dep_pkgs if dep_pkgs is not None else rgy.getPkgs()
    for name in pkgs_to_query:
        if rgy.hasPkg(name):
            pkg = rgy.getPkg(name)
            path = pkg.getPath()
            if path and path not in prefix_paths:
                prefix_paths.append(path)

    if prefix_paths:
        return ["-DCMAKE_PREFIX_PATH=%s" % ";".join(prefix_paths)]
    return []


class IVPMHook(_BHI):
    """scikit-build-core build hook that injects IVPM include/lib paths."""

    def initialize(self, version, build_data):
        if not _SKBUILD_AVAILABLE:
            raise RuntimeError(
                "scikit-build-core is required for IVPMHook; "
                "install ivpm-build[cmake]"
            )
        build_data["cmake_args"].extend(collect_cmake_args())
