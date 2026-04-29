import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

project = "ivpm-build"
copyright = "2024, Matthew Ballance"
author = "Matthew Ballance"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_rtd_theme",
]

html_theme = "sphinx_rtd_theme"
html_static_path = []

# autodoc settings
autodoc_member_order = "bysource"
