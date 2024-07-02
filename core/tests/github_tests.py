from core import get_github_tag, get_github_session, GitHubTag, get_project_name_from_connection, get_repo_from_parent_scm, get_scm_from_pom_file, get_github_repo_from_scm
from pathlib import Path
from lxml import etree as ET


def test_get_github_tag_from_semver():
    with get_github_session() as session:
        repo = session.get_repo("hibernate/hibernate-orm")
    actual_tag = get_github_tag(repo, "hibernate-orm", "5.6.15.Final")
    expected_tag = GitHubTag("5.6.15", "e924c27e1259b0b5915819e9521d86fcb8164a46")

    assert actual_tag == expected_tag


def test_get_github_tag_exact_lightweight():
    with get_github_session() as session:
        repo = session.get_repo("pawellabaj/auto-record")
    actual_tag = get_github_tag(repo, "auto-record", "v2.0.0")
    expected_tag = GitHubTag("v2.0.0", "22ba56ef647fc12aa4fbacca7698e6ecd8c81256")

    assert actual_tag == expected_tag


def test_get_github_tag_exact_annotated():
    with get_github_session() as session:
        repo = session.get_repo("finos/legend-engine")
    actual_tag = get_github_tag(repo, "legend-engine", "legend-engine-4.37.7")
    expected_tag = GitHubTag("legend-engine-4.37.7", "5827f33703431f309af79219ac8490521a6261b5")

    assert actual_tag == expected_tag


def test_get_github_tag_exact_ex1():
    with get_github_session() as session:
        repo = session.get_repo("bndtools/bnd")
    actual_tag = get_github_tag(repo, "bnd-plugin-parent", "6.3.0")
    expected_tag = GitHubTag("6.3.0", "90e7ecf40a2fbdb7998ef6a3e46d81a91ee054a2")

    assert actual_tag == expected_tag


def test_get_github_tag_inexact_api_returns_none():
    with get_github_session() as session:
        repo = session.get_repo("bndtools/bnd")
    actual_tag = get_github_tag(repo, "bnd-plugin-parent", "5.2.0")
    expected_tag = GitHubTag("5.2.0.REL", "c9791146e2d53925142f1c8d0b9a95547a05e752")

    assert actual_tag == expected_tag


def test_get_project_name_from_connection_github():
    connection = "scm:git:git@github.com:FasterXML/jackson-databind.git"
    actual_name = get_project_name_from_connection(connection)
    expected_name = "FasterXML/jackson-databind"
    assert actual_name == expected_name


def test_get_project_name_from_connection_non_github():
    connection = "scm:git:https://gitbox.apache.org/repos/asf/commons-compress.git"
    actual_name = get_project_name_from_connection(connection)
    expected_name = None
    assert actual_name == expected_name


def test_get_repo_from_parent_scm():
    pom_path = Path(__file__).parent.parent.resolve() / "test_resources" / "tispark-assembly-2.4.1.pom"
    scm, pom = get_scm_from_pom_file(pom_path, "com.pingcap.tispark", "tispark-assembly", "2.4.1")
    with get_github_session() as session:
        repo = get_github_repo_from_scm(scm, session)
        repo_parent = get_repo_from_parent_scm(pom, session)

    assert repo is None
    assert repo_parent.full_name == "pingcap/tispark"


def test_get_github_repo_from_pom():
    pom_path = Path(__file__).parent.parent.resolve() / "test_resources" / "presto-pinot-toolkit-0.266.1.pom"
    scm, pom = get_scm_from_pom_file(pom_path, "com.facebook.presto", "presto-pinot-toolkit", "0.266.1")
    with get_github_session() as session:
        repo = get_github_repo_from_scm(scm, session)
        print(repo)
        repo_parent = get_repo_from_parent_scm(pom, session)
        print(repo_parent)

    # assert repo is None
