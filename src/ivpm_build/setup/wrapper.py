"""Ported from ivpm.setup.wrapper with updated imports and new apply_ivpm_setup()."""
import importlib
import os
import platform
import sys

from setuptools import setup as _setup

import ivpm_build.setup.ivpm_data as idata
from ivpm_build.setup.build_ext import BuildExt
from ivpm_build.setup.install_lib import InstallLib


def _PkgInfoRgy_inst():
    """Thin wrapper around PkgInfoRgy.inst() to allow monkeypatching in tests."""
    from ivpm.pkg_info.pkg_info_rgy import PkgInfoRgy
    return PkgInfoRgy.inst()


def setup(*args, **kwargs):
    print("IVPM setup: %s" % kwargs.get("name", "<unknown>"))

    if "-DDEBUG" in sys.argv:
        sys.argv.remove("-DDEBUG")

    if "ivpm_extra_data" in kwargs:
        idata._ivpm_extra_data = kwargs.pop("ivpm_extra_data")

    if "ivpm_extdep_data" in kwargs:
        idata._ivpm_extdep_data = kwargs.pop("ivpm_extdep_data")

    if "ivpm_hooks" in kwargs:
        idata._ivpm_hooks = kwargs.pop("ivpm_hooks")

    if "ivpm_ext_name_m" in kwargs:
        idata._ivpm_ext_name_m = kwargs.pop("ivpm_ext_name_m")

    # Update extension flags based on common requirements
    if "ext_modules" in kwargs:
        for m in kwargs["ext_modules"]:
            if hasattr(m, "language") and m.language == "c++":
                print("C++ extension")
                if platform.system() == "Darwin":
                    if not hasattr(m, "extra_compile_args"):
                        setattr(m, "extra_compile_args", [])
                    m.extra_compile_args.append("-std=c++17")

    if "ivpm_extdep_pkgs" in kwargs:
        include_dirs = []
        library_dirs = []
        libraries = []
        paths = []
        for dep in kwargs.pop("ivpm_extdep_pkgs"):
            processed = set()
            _collect_extdeps(dep, processed, include_dirs, library_dirs, libraries, paths)

        print("paths: %s" % str(paths), flush=True)
        print("include_dirs: %s" % str(include_dirs), flush=True)

        if "ext_modules" in kwargs:
            for m in kwargs["ext_modules"]:
                print("Applying extension updates to: %s" % m.name)
                _apply_extdeps(m, include_dirs, library_dirs, libraries)
                print("Final settings for %s:" % m.name)
                print("   incdirs: %s" % str(m.include_dirs))
        else:
            print("Note: no extension libraries")

    if "cmdclass" in kwargs:
        cmdclass = kwargs["cmdclass"]
    else:
        cmdclass = {}
        kwargs["cmdclass"] = cmdclass

    if "build_ext" in cmdclass:
        print("Warning: build_ext is overridden")
    else:
        cmdclass["build_ext"] = BuildExt

    if "install_lib" in cmdclass:
        print("Warning: install_lib is overridden")
    else:
        cmdclass["install_lib"] = InstallLib

    print("ivpm_build.setup.setup")
    if "ext_modules" in kwargs:
        for ext in kwargs["ext_modules"]:
            if hasattr(ext, "package_deps"):
                print("package_deps")

    for hook in idata.get_hooks(idata.Phase_SetupPre):
        hook(None)

    _setup(*args, **kwargs)

    for hook in idata.get_hooks(idata.Phase_SetupPost):
        hook(None)


def apply_ivpm_setup(
    ext_modules=None,
    ivpm_extdep_pkgs=None,
    ivpm_extra_data=None,
    ivpm_extdep_data=None,
    ivpm_hooks=None,
    ivpm_ext_name_m=None,
):
    """Inject IVPM-managed dependency paths into extension descriptors and
    store extra-data/hook configuration without replacing setuptools.setup().
    Call this before calling setuptools.setup() directly."""

    if ivpm_extra_data is not None:
        idata._ivpm_extra_data = ivpm_extra_data

    if ivpm_extdep_data is not None:
        idata._ivpm_extdep_data = ivpm_extdep_data

    if ivpm_hooks is not None:
        idata._ivpm_hooks = ivpm_hooks

    if ivpm_ext_name_m is not None:
        idata._ivpm_ext_name_m = ivpm_ext_name_m

    if ivpm_extdep_pkgs and ext_modules:
        include_dirs = []
        library_dirs = []
        libraries = []
        paths = []
        for dep in ivpm_extdep_pkgs:
            processed = set()
            _collect_extdeps(dep, processed, include_dirs, library_dirs, libraries, paths)

        for m in ext_modules:
            print("Applying extension updates to: %s" % m.name)
            _apply_extdeps(m, include_dirs, library_dirs, libraries)


def _collect_extdeps(dep, processed, include_dirs, library_dirs, libraries, paths):
    if dep in processed:
        return
    processed.add(dep)

    rgy = _PkgInfoRgy_inst()

    for pkg in rgy.getPkgs():
        print("Package: %s" % pkg, flush=True)

    if rgy.hasPkg(dep):
        print("Package %s is an IVPM package" % dep)
        pkg = rgy.getPkg(dep)

        path = pkg.getPath()
        if path is not None and path not in paths:
            paths.append(path)

        for incdir in pkg.getIncDirs():
            if incdir not in include_dirs:
                include_dirs.append(incdir)

        for libdir in pkg.getLibDirs():
            if libdir not in library_dirs:
                library_dirs.append(libdir)

        for lib in pkg.getLibs():
            if lib not in libraries:
                libraries.append(lib)

        for sub_dep in pkg.getDeps():
            _collect_extdeps(sub_dep, processed, include_dirs, library_dirs, libraries, paths)
    else:
        print("TODO: %s is not an IVPM package" % str(dep))
        try:
            mod = importlib.import_module(dep)
            pkg_path = mod.__file__

            if pkg_path is not None:
                if os.path.isfile(pkg_path):
                    pkg_dir = os.path.dirname(pkg_path)
                else:
                    pkg_dir = pkg_path
                print("pkg_path: %s ; pkg_dir: %s" % (pkg_path, pkg_dir))
                if pkg_dir not in include_dirs:
                    include_dirs.append(pkg_dir)
            else:
                print("Package %s does not have a non-null module path" % dep)
        except ImportError as e:
            print("Failed to import dependency %s (%s)" % (dep, str(e)))


def _apply_extdeps(m, include_dirs, library_dirs, libraries):
    for incdir in include_dirs:
        if incdir not in m.include_dirs:
            print("Add incdir %s" % incdir)
            m.include_dirs.append(incdir)
    for libdir in library_dirs:
        if libdir not in m.library_dirs:
            m.library_dirs.append(libdir)
