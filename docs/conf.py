exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", ".venv", "venv"]
html_css_files = ["literals.css"]
extensions = ["sphinx_rtd_theme"]
templates_path = ["_templates"]

html_context = {
    "display_github": True,
    "github_user": "AAA3A-AAA3A",
    "github_repo": "AAA3A-cogs",
    "github_version": "main/docs/",
}

master_doc = "index"
html_theme = "furo"
source_suffix = ".rst"
master_doc = "index"
exclude_patterns = []
add_function_parentheses = True

project = "AAA3A-cogs"
copyright = "2022 | AAA3A"
html_logo = "image_cog-creators-logo.png"