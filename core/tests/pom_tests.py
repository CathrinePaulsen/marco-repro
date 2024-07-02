import xml.etree.ElementTree as ET
from pathlib import Path

from core import get_version_tag_from_scm_or_pom, namespace, get_github_repo_from_scm, get_github_session

TEST_RESOURCES = Path(__file__).parent.parent.resolve() / "test_resources"


def test_get_version_tag_from_scm_or_pom():
    pom_file = TEST_RESOURCES / "test_pom.xml"
    with open(pom_file, "r") as f:
        root = ET.fromstring(f.read())
    scm = root.find(".//maven:scm", namespaces=namespace)

    actual_version_tag = get_version_tag_from_scm_or_pom(scm, "")
    expected_version_tag = "jackson-databind-2.17.0"

    assert actual_version_tag == expected_version_tag


def test_get_version_tag_from_scm_or_pom_no_tag():
    pom_file = TEST_RESOURCES / "test_pom_no_tag.xml"
    with open(pom_file, "r") as f:
        root = ET.fromstring(f.read())
    scm = root.find(".//maven:scm", namespaces=namespace)

    actual_version_tag = get_version_tag_from_scm_or_pom(scm, "abcd")
    expected_version_tag = "abcd"

    assert actual_version_tag == expected_version_tag


def test_get_github_repo_from_scm():
    pom_file = TEST_RESOURCES / "test_pom.xml"
    with open(pom_file, "r") as f:
        root = ET.fromstring(f.read())
    scm = root.find(".//maven:scm", namespaces=namespace)

    with get_github_session() as session:
        actual_repo = get_github_repo_from_scm(scm, session)

    expected_repo_name = "FasterXML/jackson-databind"

    assert actual_repo.full_name == expected_repo_name


def test_get_github_repo_from_scm_no_github():
    pom_file = TEST_RESOURCES / "test_pom_no_tag.xml"
    with open(pom_file, "r") as f:
        root = ET.fromstring(f.read())
    scm = root.find(".//maven:scm", namespaces=namespace)

    with get_github_session() as session:
        actual_repo = get_github_repo_from_scm(scm, session)

    assert not actual_repo


def test_get_github_repo_from_url_tag():
    pom_file = TEST_RESOURCES / "test_pom_url_only.xml"
    with open(pom_file, "r") as f:
        root = ET.fromstring(f.read())
    scm = root.find(".//maven:scm", namespaces=namespace)

    with get_github_session() as session:
        actual_repo = get_github_repo_from_scm(scm, session)

    assert actual_repo.full_name == "FasterXML/jackson-databind"