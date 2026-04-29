"""CMake configure / build / install driver.

Extracted from ivpm.setup.BuildExt.build_cmake() so it can be used
independently of the setuptools command hierarchy.
"""
import os
import platform
import subprocess
import sys


class CmakeBuilder:
    """Drives a CMake configure + build + install cycle."""

    def __init__(
        self,
        proj_dir: str,
        build_dir: str = None,
        debug: bool = False,
        cmake_build_tool: str = None,
    ):
        self.proj_dir = proj_dir
        self.build_dir = build_dir or os.path.join(proj_dir, "build")
        self.debug = debug
        if cmake_build_tool is None:
            cmake_build_tool = os.environ.get("CMAKE_BUILD_TOOL", "Ninja")
        self.cmake_build_tool = cmake_build_tool

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def configure(self, extra_args: list = None) -> None:
        """Run cmake configure step."""
        supported = ("Ninja", "Unix Makefiles")
        if self.cmake_build_tool not in supported:
            raise ValueError(
                "cmake_build_tool %r not supported; choose one of %s"
                % (self.cmake_build_tool, supported)
            )

        if not os.path.isdir(self.build_dir):
            os.makedirs(self.build_dir)

        build_type = "-DCMAKE_BUILD_TYPE=Debug" if self.debug else "-DCMAKE_BUILD_TYPE=Release"

        packages_dir = self._find_packages_dir()

        env = self._build_env()

        config_cmd = [
            "cmake",
            self.proj_dir,
            "-G%s" % self.cmake_build_tool,
            build_type,
            "-DPACKAGES_DIR=%s" % packages_dir,
            "-DCMAKE_INSTALL_PREFIX=%s" % self.build_dir,
        ]

        if platform.system() == "Darwin":
            config_cmd.append("-DCMAKE_OSX_ARCHITECTURES='x86_64;arm64'")

        if extra_args:
            config_cmd.extend(extra_args)

        print("cmake config command: %s" % str(config_cmd))
        result = subprocess.run(config_cmd, cwd=self.build_dir, env=env)
        if result.returncode != 0:
            raise RuntimeError("cmake configure failed (returncode=%d)" % result.returncode)

    def build(self) -> None:
        """Run the build step (ninja or make)."""
        env = self._build_env()
        if self.cmake_build_tool == "Ninja":
            self._run_ninja(self.build_dir, env)
        else:
            self._run_make(self.build_dir, env)

    def install(self) -> None:
        """Run the install step."""
        env = self._build_env()
        if self.cmake_build_tool == "Ninja":
            self._run_ninja_install(self.build_dir, env)
        else:
            self._run_make_install(self.build_dir, env)

    def run(self, extra_cmake_args: list = None) -> None:
        """Configure, build, and install in sequence."""
        self.configure(extra_cmake_args)
        self.build()
        self.install()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_packages_dir(self) -> str:
        if os.path.isdir(os.path.join(self.proj_dir, "packages")):
            return os.path.join(self.proj_dir, "packages")
        elif os.path.isdir(os.path.dirname(self.proj_dir)):
            return os.path.dirname(self.proj_dir)
        else:
            raise RuntimeError(
                "Cannot locate packages directory relative to proj_dir=%s" % self.proj_dir
            )

    def _build_env(self) -> dict:
        env = os.environ.copy()
        python_bindir = os.path.dirname(sys.executable)
        if "PATH" in env:
            env["PATH"] = python_bindir + os.pathsep + env["PATH"]
        else:
            env["PATH"] = python_bindir
        env.pop("PYTHONPATH", None)
        return env

    def _run_ninja(self, build_dir, env):
        result = subprocess.run(
            ["ninja", "-j", "%d" % os.cpu_count()],
            cwd=build_dir,
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError("ninja build failed (returncode=%d)" % result.returncode)

    def _run_ninja_install(self, build_dir, env):
        result = subprocess.run(
            ["ninja", "-j", "%d" % os.cpu_count(), "install"],
            cwd=build_dir,
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError("ninja install failed (returncode=%d)" % result.returncode)

    def _run_make(self, build_dir, env):
        result = subprocess.run(
            ["make", "-j%d" % os.cpu_count()],
            cwd=build_dir,
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError("make build failed (returncode=%d)" % result.returncode)

    def _run_make_install(self, build_dir, env):
        result = subprocess.run(
            ["make", "-j%d" % os.cpu_count(), "install"],
            cwd=build_dir,
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError("make install failed (returncode=%d)" % result.returncode)
