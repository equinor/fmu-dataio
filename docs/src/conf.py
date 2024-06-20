#!/usr/bin/env python3

import logging
import os
import sys
from datetime import date

import fmu.dataio
import fmu.dataio.dataio

sys.path.insert(0, os.path.abspath("../../src/fmu"))
sys.path.insert(1, os.path.abspath("../ext"))


class PydanticAutodocFilter(logging.Filter):
    """A logging filter to suppress warnings about duplicate object descriptions when
    generating Pydantic model documentation. These warnings are a result of generating a
    new nested model document wherever one occurs, even if this Pydantic model is used
    in multiple places."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "duplicate object description" not in record.getMessage()


logging.getLogger("sphinx").addFilter(PydanticAutodocFilter())


# -- General configuration ---------------------------------------------

# The full version, including alpha/beta/rc tags.
release = fmu.dataio.__version__

extensions = [
    "myst_parser",
    "pydantic_autosummary",
    "sphinx.ext.autodoc",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx_togglebutton",
    "sphinxcontrib.apidoc",
    "sphinxcontrib.autodoc_pydantic",
]

autosummary_generate = True
autosummary_imported_members = True
add_module_names = False

togglebutton_hint = "Expand"

apidoc_module_dir = "../../src/fmu/dataio"
apidoc_output_dir = "apiref"
apidoc_excluded_paths = [
    "case",
    "datastructure",
    "hook_implementations",
    "providers",
    "scripts",
    "tests",
    "types",
    "version",
]
apidoc_separate_modules = True
apidoc_module_first = True
apidoc_extra_args = ["-H", "API reference for fmu.dataio"]

autoclass_content = "class"
# Sort members by input order in classes
autodoc_member_order = "bysource"
autodoc_default_flags = ["members", "show_inheritance"]
# Mocking ert, rms, pydantic module
autodoc_mock_imports = ["ert", "pydantic", "rmsapi", "_rmsapi", "roxar", "_roxar"]

napoleon_include_special_with_doc = False

# The suffix of source filenames.
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "fmu.dataio"
current_year = date.today().year
copyright = f"Equinor {current_year} (fmu-dataio release {release})"


exclude_patterns = ["_build"]

pygments_style = "sphinx"

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "style_nav_header_background": "#C0C0C0",
    "navigation_depth": -1,
    "collapse_navigation": False,
    "titles_only": True,
}


# html_logo = "images/xtgeo-logo.png"

# The name of an image file (within the static path) to use as favicon
# of the docs.  This file should be a Windows icon file (.ico) being
# 16x16 or 32x32 pixels large.
# html_favicon = None


# If not '', a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
# html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
# html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names
# to template names.
# html_additional_pages = {}

# If false, no module index is generated.
# html_domain_indices = True

# If false, no index is generated.
# html_use_index = True

# If true, the index is split into individual pages for each letter.
# html_split_index = False

# If true, links to the reST sources are added to the pages.
# html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer.
# Default is True.
# html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer.
# Default is True.
# html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages
# will contain a <link> tag referring to it.  The value of this option
# must be the base URL from which the finished HTML is served.
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = "dataio"
