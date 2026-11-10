"""Public documentation; importing the CLI parser performs no remote operations."""

import sys
from pathlib import Path

from jupyhop import __version__

sys.path.insert(0, str(Path(__file__).parent / "_ext"))

project = "JupyHop"
copyright = "JupyHop contributors"
version = release = __version__
language = "en"
extensions = ["myst_parser", "sphinx_copybutton", "sphinx.ext.githubpages", "jupyhop_cli"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
nitpicky = True
myst_heading_anchors = 4
myst_enable_extensions = ["colon_fence"]

html_theme = "pydata_sphinx_theme"
html_title = "JupyHop"
templates_path = ["_templates"]
html_theme_options = {
    "github_url": "https://github.com/uibcdf/jupyhop",
    "show_toc_level": 2,
}
html_context = {
    "github_user": "uibcdf",
    "github_repo": "jupyhop",
    "github_version": "main",
    "doc_path": "docs",
}
html_baseurl = "https://www.uibcdf.org/jupyhop/"
html_show_sourcelink = False
html_copy_source = False
html_static_path = ["_static"]
html_css_files = ["jupyhop.css"]

copybutton_prompt_text = r"\$ |>>> |\.\.\. "
copybutton_prompt_is_regexp = True
linkcheck_timeout = 20
linkcheck_retries = 2
