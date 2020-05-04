# Configuration file for the Sphinx documentation app.

# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from datetime import datetime

from kikuchipy import release as kp_release

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append("../")

# Project information
project = "kikuchipy"
copyright = "2019-" + str(datetime.now().year) + ", " + kp_release.author + "."
author = kp_release.author
version = kp_release.version
release = kp_release.version

master_doc = "index"

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    #    "sphinx.ext.viewcode",
    "sphinx.ext.linkcode",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
]

# Create links to references within kikuchipy's documentation to these packages.
intersphinx_mapping = {
    "dask": ("https://docs.dask.org/en/latest", None),
    "hyperspy": ("http://hyperspy.org/hyperspy-doc/current", None),
    "matplotlib": ("https://matplotlib.org", None),
    "numpy": ("https://docs.scipy.org/doc/numpy", None),
    "python": ("https://docs.python.org/3", None),
    "pyxem": ("https://pyxem.github.io/pyxem-website/docstring", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/reference", None),
    "skimage": ("https://scikit-image.org/docs/stable", None),
    "sklearn": ("https://scikit-learn.org/stable", None),
    "h5py": ("http://docs.h5py.org/en/stable/", None),
}

# Add any paths that contain templates here, relative to this directory.
templates_path = [
    "_templates",
]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files. This image also affects
# html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
]

# The theme to use for HTML and HTML Help pages.  See the documentation for a
# list of builtin themes.
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files, so
# a file named "default.css" will overwrite the builtin "default.css".
html_static_path = [
    "_static",
]
html_css_files = [
    "style.css",
]

# Syntax highlighting
# solarized-dark, solarized-light
# default, friendly, colorful, sphinx
pygments_style = "friendly"

# Logo
cmap = "plasma"  # viridis, magma, inferno, plasma
html_logo = f"_static/icon/{cmap}_logo.svg"
html_favicon = f"_static/icon/{cmap}_favicon.png"

# Read the Docs theme options
html_theme_options = {
    "prev_next_buttons_location": None,
}


def linkcode_resolve(domain, info):
    if domain != "py":
        return None
    if not info["module"]:
        return None
    filename = info["module"].replace(".", "/")
    return "https://github.com/kikuchipy/kikuchipy/tree/master/%s.py" % filename
