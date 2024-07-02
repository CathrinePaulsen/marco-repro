import os
import pathlib
import subprocess

from server.template import Template

BASE_TEMPLATES_TEST_DIR = pathlib.Path(__file__).parent.parent.parent.resolve() / "test_resources" / "base_templates"
CAND_TEMPLATES_TEST_DIR = pathlib.Path(__file__).parent.parent.parent.resolve() / "test_resources" / "cand_templates"
REPOS_TEST_DIR = pathlib.Path(__file__).parent.parent.parent.resolve() / "test_resources" / "repos"


def cleanup_template(template: Template):
    """Removes the template from test_resources."""
    if os.path.isdir(template.path):
        subprocess.run(['rm', '-rf', template.path])
    else:
        pass


def cleanup_repo(template: Template):
    """Removes the template's repo from test_resources."""
    if os.path.isdir(pathlib.Path.joinpath(REPOS_TEST_DIR, template.repo_name)):
        subprocess.run(['rm', '-rf', pathlib.Path.joinpath(REPOS_TEST_DIR, template.repo_name)])
    else:
        pass
