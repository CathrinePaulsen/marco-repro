from core import get_github_session
from server.repo_utils import repo_compiles, repo_has_tests
from server.config import download_repo


def test_repo_compiles():
    with get_github_session() as session:
        repo = session.get_repo("0x727/BypassPro")
    download_path = download_repo(repo)
    assert repo_compiles(download_path)


def test_repo_has_tests_false_no_tests():
    with get_github_session() as session:
        repo = session.get_repo("0x727/BypassPro")
    download_path = download_repo(repo)
    assert not repo_has_tests(download_path)


def test_repo_has_tests_false_no_running_tests():
    with get_github_session() as session:
        repo = session.get_repo("jar-analyzer/jar-analyzer")
    download_path = download_repo(repo)
    assert not repo_has_tests(download_path)


def test_repo_has_tests_false_no_passing_tests():
    with get_github_session() as session:
        repo = session.get_repo("edw2023/DBMastermind-Suite")
    download_path = download_repo(repo)
    assert not repo_has_tests(download_path)

