#!/usr/bin/env python3
from __future__ import annotations

import logging
import os
import sys
from datetime import date
from textwrap import dedent

import fmu.dataio
import fmu.dataio.dataio
from fmu.dataio._models import schemas
from fmu.dataio._models._schema_base import SchemaBase

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
    "sphinx_copybutton",
]

myst_enable_extensions = [
    "substitution",
    "colon_fence",
]


def _myst_substitutions() -> dict[str, SchemaBase]:
    subs = {}
    for s in schemas:
        s.literalinclude = dedent(f"""
            ```{{eval-rst}}
               .. toggle::

                  .. literalinclude:: ../../../{s.PATH}
                     :language: json

            ```
        """)
        if hasattr(s, "CONTRACTUAL"):
            s.contractual = "\n".join([f"- `{item}`" for item in s.CONTRACTUAL])
        subs[f"{s.__name__}"] = s
    return subs


myst_substitutions = _myst_substitutions()
# myst substitutions have objects, causing the cache warning
suppress_warnings = ["config.cache"]

autosummary_generate = True
autosummary_imported_members = True
add_module_names = False

togglebutton_hint = "Expand"

apidoc_module_dir = "../../src/fmu/dataio"
apidoc_output_dir = "apiref"
apidoc_excluded_paths = [
    "case",
    "_models",
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
autodoc_pydantic_model_summary_list_order = "bysource"
autodoc_pydantic_model_member_order = "bysource"
autodoc_default_flags = ["members", "show_inheritance"]
# Mocking ert, rms, pydantic module
autodoc_mock_imports = ["ert", "pydantic", "rmsapi", "_rmsapi", "roxar", "_roxar"]

napoleon_include_special_with_doc = False

# The suffix of source filenames.
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

# The master toctree document.
master_doc = "index"

exclude_patterns = ["_build"]

pygments_style = "sphinx"

# General information about the project.
project = "fmu-dataio"
current_year = date.today().year
# The full version, including alpha/beta/rc tags.
release = fmu.dataio.__version__
# The short version, like 3.0
version = ".".join(release.split(".")[:2])

html_theme = "furo"
html_title = f"{project} {version}"
copyright = f"Equinor {current_year} ({project} release {release})"
# html_logo = "images/logo.png"

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
