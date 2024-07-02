import os
import pathlib
from unittest.mock import patch

from tests.template import BASE_TEMPLATES_TEST_DIR, REPOS_TEST_DIR, cleanup_template, cleanup_repo

from server.template.base_template import BaseTemplate


def test_always_passes():
    assert True


def test_base_template_creation():
    g, a, v = ["gTest", "aTest", "vTest"]
    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.template.base_template.BaseTemplate.get_github_metadata'), \
            patch('server.template.download_repo'), \
            patch('server.template.base_template.BaseTemplate.prepare_template'):
        template = BaseTemplate(g, a, v)

    assert os.path.isdir(pathlib.Path.joinpath(BASE_TEMPLATES_TEST_DIR, f"{g}:{a}:{v}"))

    cleanup_template(template)


def test_base_template_github_metadata():
    g, a, v = ["com.fasterxml.jackson.core", "jackson-databind", "2.15.0"]
    template_path = pathlib.Path.joinpath(BASE_TEMPLATES_TEST_DIR, f"{g}:{a}:{v}")
    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.template.download_repo'), \
            patch('server.template.base_template.BaseTemplate.prepare_template'):
        template = BaseTemplate(g, a, v)

    assert template.repo_name == "FasterXML/jackson-databind"
    assert template.tag_name == "jackson-databind-2.15.0"
    assert template.commit_sha == "30e5c71f2269e21988ba729371d989b55683a5f1"
    assert os.path.isdir(template_path)
    assert os.path.isfile(pathlib.Path.joinpath(template_path, "_metadata.json"))

    cleanup_template(template)



def test_base_template_repo_download():
    g, a, v = ["com.fasterxml.jackson.core", "jackson-databind", "2.16.0"]
    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR), \
            patch('server.template.base_template.BaseTemplate.prepare_template'):
        template = BaseTemplate(g, a, v)

    assert template.repo_name == "FasterXML/jackson-databind"
    assert template.tag_name == "jackson-databind-2.16.0"
    assert template.commit_sha == "74621b01e69396160cc48b023aa0e85f38964c0f"
    assert os.path.isdir(pathlib.Path.joinpath(BASE_TEMPLATES_TEST_DIR, f"{g}:{a}:{v}"))

    cleanup_repo(template)
    cleanup_template(template)


def test_base_template_prepare_template():
    g, a, v = ["com.fasterxml.jackson.core", "jackson-databind", "2.16.0"]
    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        template = BaseTemplate(g, a, v)

    test_classes_path = pathlib.Path.joinpath(template.target_path, "test-classes")
    test_sources_path = pathlib.Path.joinpath(template.target_path, "generated-test-sources")
    surefire_path = pathlib.Path.joinpath(template.target_path, "surefire-reports_BASE")

    assert os.path.isdir(test_classes_path)
    assert os.path.isdir(test_sources_path)
    assert os.path.isdir(surefire_path)

    cleanup_repo(template)
    cleanup_template(template)




