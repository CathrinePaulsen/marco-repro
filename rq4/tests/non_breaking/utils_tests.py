from core import get_github_session
from rq4.non_breaking import utils


def test_repo_has_pom_true():
    with get_github_session() as session:
        r = session.get_repo("FasterXML/jackson-databind")
    assert utils.repo_has_pom(r)


def test_repo_has_pom_false_1():
    with get_github_session() as session:
        r = session.get_repo("spring-projects/spring-boot")
    assert not utils.repo_has_pom(r)


def test_repo_has_pom_false_2():
    with get_github_session() as session:
        r = session.get_repo("Stirling-Tools/Stirling-PDF")
    assert not utils.repo_has_pom(r)


# TODO: slow?
# def test_yield_merged_prs():
#     with get_github_session() as session:
#         r = session.get_repo("spring-projects/spring-boot")
#
#     count = 0
#     for pr in utils.merged_dependabot_prs(r):
#         if count >= 8:
#             break
#         count += 1
#         assert pr.is_merged


def test_dependabot_pr_true():
    with get_github_session() as session:
        r = session.get_repo("spring-projects/spring-boot")

    p = r.get_pull(40106)
    assert p.title == "Bump gradle/wrapper-validation-action from 2.1.1 to 2.1.2"
    assert utils.pr_opened_by_dependabot(p)


def test_dependabot_pr_false():
    with get_github_session() as session:
        r = session.get_repo("spring-projects/spring-boot")

    p = r.get_pull(40172)
    assert p.title == "Fix broken AnsiOutput.detectIfAnsiCapable on JDK22"
    assert not utils.pr_opened_by_dependabot(p)


def test_repo_has_maven_dependabot_true():
    with get_github_session() as session:
        r = session.get_repo("netplex/json-smart-v2")

    assert utils.repo_has_maven_dependabot(r)


def test_get_dependabot_prs_of_repo():
    with get_github_session() as session:
        repo = session.get_repo("netplex/json-smart-v2")
        count = 0
        for _ in utils.get_dependabot_prs_of_repo(repo, session):
            count += 1
    assert count == 70


def test_repo_has_maven_dependabot_no_maven_1():
    with get_github_session() as session:
        r = session.get_repo("FasterXML/jackson-databind")

    assert not utils.repo_has_maven_dependabot(r)


def test_repo_has_maven_dependabot_no_maven_2():
    with get_github_session() as session:
        r = session.get_repo("Stirling-Tools/Stirling-PDF")

    assert not utils.repo_has_maven_dependabot(r)


def test_repo_has_maven_dependabot_no_config():
    with get_github_session() as session:
        r = session.get_repo("gunnarmorling/1brc")

    assert not utils.repo_has_maven_dependabot(r)


def test_pr_updates_pom_true():
    with get_github_session() as session:
        r = session.get_repo("KouShenhai/KCloud-Platform-Alibaba")
    pr = r.get_pull(1084)
    assert utils.pr_updates_pom(pr)


def test_pr_has_one_commit_true():
    with get_github_session() as session:
        r = session.get_repo("OpenFeign/querydsl")
    pr = r.get_pull(138)
    assert utils.pr_has_one_commit(pr)


def test_pr_has_one_commit_false():
    with get_github_session() as session:
        r = session.get_repo("KouShenhai/KCloud-Platform-Alibaba")
    pr = r.get_pull(1084)
    assert not utils.pr_has_one_commit(pr)
