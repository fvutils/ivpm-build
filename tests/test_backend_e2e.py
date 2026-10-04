"""End-to-end test of the backend's no-extension CMake wheel build.

Exercises the full path cibuildwheel relies on: CMake configure/build/install
-> extra-data staging into the package -> platform-tagged wheel. The native
library is loaded via ctypes (no Python C-extension), so the resulting wheel
must be ``py3-none-<platform>`` and contain the built shared library.
"""
import os
import shutil
import sysconfig
import zipfile

import pytest

import ivpm_build.backend as backend


pytestmark = pytest.mark.skipif(
    shutil.which("cmake") is None or shutil.which("ninja") is None,
    reason="cmake and ninja are required for the end-to-end backend test",
)


CMAKELISTS = """\
cmake_minimum_required(VERSION 3.16)
project(demo C)
add_library(demo SHARED demo.c)
install(TARGETS demo LIBRARY DESTINATION lib RUNTIME DESTINATION lib)
"""

DEMO_C = "int demo_answer(void) { return 42; }\n"

PYPROJECT = """\
[build-system]
requires = ["setuptools>=64"]
build-backend = "ivpm_build.backend"

[project]
name = "demo"
version = "0.0.1"

[tool.setuptools]
packages = ["demo"]
package-dir = {"" = "src"}

[tool.setuptools.package-data]
demo = ["*.so", "*.dylib", "*.dll"]

[tool.ivpm-build]
cmake = true

[[tool.ivpm-build.extra-data]]
pkg = "demo"
src = "build/{libdir}/{libpref}demo{dllext}"
dst = ""
"""


def _make_project(root):
    (root / "src" / "demo").mkdir(parents=True)
    (root / "src" / "demo" / "__init__.py").write_text("")
    (root / "CMakeLists.txt").write_text(CMAKELISTS)
    (root / "demo.c").write_text(DEMO_C)
    (root / "pyproject.toml").write_text(PYPROJECT)


def test_build_wheel_is_platform_tagged_and_contains_lib(tmp_path):
    proj = tmp_path / "proj"
    _make_project(proj)
    wheels = tmp_path / "out"
    wheels.mkdir()

    cwd = os.getcwd()
    os.chdir(proj)
    try:
        name = backend.build_wheel(str(wheels))
    finally:
        os.chdir(cwd)

    # Platform-specific, interpreter/ABI agnostic tag.
    assert not name.endswith("-py3-none-any.whl"), name
    plat = sysconfig.get_platform().replace("-", "_").replace(".", "_")
    assert name.endswith("-py3-none-%s.whl" % plat), (name, plat)

    # The CMake-built shared library was staged at the package root (not
    # relocated under <name>.data/purelib/).
    with zipfile.ZipFile(wheels / name) as zf:
        members = zf.namelist()
    assert any(
        n.startswith("demo/") and n.endswith((".so", ".dylib", ".dll"))
        for n in members
    ), members
    assert not any(".data/purelib/" in n for n in members), members

    # Staging must be cleaned from the source tree afterwards.
    leftover = list((proj / "src" / "demo").glob("*.so"))
    assert leftover == [], leftover


def test_installed_wheel_has_lib_next_to_package(tmp_path):
    """A real install must drop the library right next to the package __init__,
    where a ctypes loader (Path(__file__).parent) expects it."""
    import subprocess
    import sys
    import venv

    proj = tmp_path / "proj"
    _make_project(proj)
    wheels = tmp_path / "out"
    wheels.mkdir()

    cwd = os.getcwd()
    os.chdir(proj)
    try:
        name = backend.build_wheel(str(wheels))
    finally:
        os.chdir(cwd)

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    py = env_dir / "bin" / "python"
    subprocess.run([str(py), "-m", "pip", "install", "-q",
                    str(wheels / name)], check=True)

    site = subprocess.run(
        [str(py), "-c",
         "import demo, os; print(os.path.dirname(demo.__file__))"],
        check=True, capture_output=True, text=True).stdout.strip()
    libs = [f for f in os.listdir(site)
            if f.endswith((".so", ".dylib", ".dll"))]
    assert libs, "no native lib next to demo/__init__.py in %s" % site


# ---------------------------------------------------------------------------
# [[tool.ivpm-build.scripts]]: a CMake-built executable installed onto PATH
# ---------------------------------------------------------------------------

SCRIPT_CMAKELISTS = CMAKELISTS + """\
add_executable(hello hello.c)
set_target_properties(hello PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
"""

HELLO_C = """\
#include <stdio.h>
int main(void) { printf("hello from a wheel\\n"); return 0; }
"""

SCRIPTS_TOML = """
[[tool.ivpm-build.scripts]]
src = "build/bin/hello{exeext}"

[[tool.ivpm-build.scripts]]
src = "build/bin/not-built{exeext}"
optional = true
"""


def _make_script_project(root):
    _make_project(root)
    (root / "CMakeLists.txt").write_text(SCRIPT_CMAKELISTS)
    (root / "hello.c").write_text(HELLO_C)
    with open(root / "pyproject.toml", "a") as fh:
        fh.write(SCRIPTS_TOML)


def _build(proj, wheels):
    cwd = os.getcwd()
    os.chdir(proj)
    try:
        return backend.build_wheel(str(wheels))
    finally:
        os.chdir(cwd)


def test_scripts_land_in_wheel_data_scripts(tmp_path):
    proj = tmp_path / "proj"
    _make_script_project(proj)
    wheels = tmp_path / "out"
    wheels.mkdir()
    name = _build(proj, wheels)

    exe = "hello.exe" if os.name == "nt" else "hello"
    member = "demo-0.0.1.data/scripts/" + exe
    with zipfile.ZipFile(wheels / name) as zf:
        members = zf.namelist()
        assert member in members, members
        record = zf.read("demo-0.0.1.dist-info/RECORD").decode()
        info = zf.getinfo(member)
        # Copied byte for byte, not rewritten as a text script.
        built = (proj / "build" / "bin" / exe).read_bytes()
        assert zf.read(member) == built
    assert member + "," in record
    if os.name == "posix":
        assert (info.external_attr >> 16) & 0o111, oct(info.external_attr >> 16)
    # The optional, unbuilt entry is skipped rather than failing the build.
    assert not any("not-built" in n for n in members), members


def test_missing_required_script_fails(tmp_path):
    proj = tmp_path / "proj"
    _make_script_project(proj)
    with open(proj / "pyproject.toml", "a") as fh:
        fh.write('\n[[tool.ivpm-build.scripts]]\nsrc = "build/bin/absent"\n')
    wheels = tmp_path / "out"
    wheels.mkdir()
    with pytest.raises(FileNotFoundError, match="absent"):
        _build(proj, wheels)


@pytest.mark.skipif(os.name != "posix", reason="POSIX venv layout")
def test_installed_script_runs_from_path(tmp_path):
    import subprocess
    import venv

    proj = tmp_path / "proj"
    _make_script_project(proj)
    wheels = tmp_path / "out"
    wheels.mkdir()
    name = _build(proj, wheels)

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    subprocess.run([str(env_dir / "bin" / "python"), "-m", "pip", "install",
                    "-q", str(wheels / name)], check=True)
    out = subprocess.run([str(env_dir / "bin" / "hello")], check=True,
                         capture_output=True, text=True).stdout
    assert out.strip() == "hello from a wheel"
