"""Command-line entry point for ivpm-build.

The ``build`` subcommand drives the CMake configure/build/install cycle in the
current project. For projects that ship a standalone native library (loaded via
ctypes) rather than a Python extension module, this is the in-place dev-rebuild
equivalent of ``python setup.py build_ext --inplace``::

    PYTHONPATH=<ivpm-build>/src python -m ivpm_build build [--debug]

After it runs, the freshly built library is in ``<proj>/build`` and an editable
install can load it from there.
"""
import argparse
import os
import sys

from .cmake.cmake_builder import CmakeBuilder


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m ivpm_build")
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser(
        "build",
        help="Run the CMake configure/build/install cycle for the project",
    )
    b.add_argument(
        "--debug",
        action="store_true",
        help="Configure with CMAKE_BUILD_TYPE=Debug",
    )
    b.add_argument(
        "--proj-dir",
        default=os.getcwd(),
        help="Project directory containing CMakeLists.txt (default: cwd)",
    )

    args = parser.parse_args(argv)

    if args.cmd == "build":
        proj_dir = os.path.abspath(args.proj_dir)
        if not os.path.isfile(os.path.join(proj_dir, "CMakeLists.txt")):
            parser.error("no CMakeLists.txt found in %s" % proj_dir)
        CmakeBuilder(proj_dir, debug=args.debug).run()
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
