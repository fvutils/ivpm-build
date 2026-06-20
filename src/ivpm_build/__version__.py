import os

BASE = "0.2.0"
SUFFIX = ""

__version__ = (BASE, SUFFIX)

# Used by pyproject.toml dynamic versioning. CI rewrites the SUFFIX line during
# the build to append a uniquifying build number (".${GITHUB_RUN_ID}"), so each
# published artifact gets a distinct version.
_pkg_version = BASE + SUFFIX


def get_version():
    """Return the full version string, using git describe when in a source tree."""
    base, suffix = __version__
    version = base + suffix

    src_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    git_dir = os.path.join(src_dir, ".git")

    if os.path.isdir(git_dir):
        try:
            import subprocess
            out = subprocess.check_output(
                ["git", "describe", "--tags", "--dirty", "--always"],
                cwd=src_dir,
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            if out != base:
                return "%s+%s" % (version, out)
        except Exception:
            pass

    return version
