# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Make the package importable without installing it
sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------

project = "niimblue.py"
copyright = "2026, Wiktor Pyk"
author = "Wiktor Pyk"
release = "0.1.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",        # Google / NumPy docstring styles
    "sphinx.ext.viewcode",        # [source] links
    "sphinx.ext.intersphinx",     # cross-links to Python stdlib docs
    "sphinx_autodoc_typehints",   # move type hints into description
]

autosummary_generate = True
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_param = True
napoleon_use_rtype = True

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "special-members": "__init__, __enter__, __exit__",
}

# Always document __init__ params in the class docstring
autoclass_content = "both"

# Prevent duplicate object warnings from autodoc
suppress_warnings = [
    "toc.not_included",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
    "pillow": ("https://pillow.readthedocs.io/en/stable/", None),
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "navigation_depth": 4,
    "titles_only": False,
}

# Suppress warnings about duplicate object descriptions
suppress_warnings = [
    "toc.not_included",  # Examples in code blocks shouldn't trigger this
]