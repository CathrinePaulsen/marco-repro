"""Collection of shared variables and methods."""
import os
import pathlib
from pathlib import Path

from git import Repo
from github import Repository, Commit

from core import get_github_session
from server.exceptions import GithubRepoDownloadFailedException, GithubRepoNotFoundException

path_to_repos = pathlib.Path(__file__).parent.parent.resolve() / "resources" / "repos"
path_to_test_repos = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "repos"
PATH_TO_JARS = pathlib.Path(__file__).parent.parent.resolve() / "resources" / "jars"
PATH_TO_JAPICMP = (pathlib.Path(__file__).parent.parent.resolve() / "libs" / "japicmp" /
                   "japicmp-0.18.3-jar-with-dependencies.jar")

SERVER_RESOURCES = pathlib.Path(__file__).parent.parent.resolve() / "resources"
COMPATIBILITY_STORE = SERVER_RESOURCES / "compatibilities.json"
BASE_TEMPLATES_DIR = SERVER_RESOURCES / "base_templates"
CAND_TEMPLATES_DIR = SERVER_RESOURCES / "cand_templates"

COMPILE_TIMEOUT = 60
TEST_TIMEOUT = 300


def get_repo(repo_name: str):
    with get_github_session() as session:
        repo = session.get_repo(repo_name)
        if repo is None:
            raise GithubRepoNotFoundException(f"Could not find repo {repo_name} on Github")
        return repo


def download_repo_by_name(repo_name, storage_path=path_to_repos):
    return download_repo(get_repo(repo_name), storage_path=storage_path)


def download_repo_and_return_commit(repo: Repository, storage_path=path_to_repos) -> Commit:
    print(f"Cloning {repo.full_name} into {storage_path}/{repo.full_name}")
    download_path = Path.joinpath(storage_path, repo.full_name)
    if os.path.isdir(download_path):
        return download_path
    try:
        r = Repo.clone_from(f"https://github.com/{repo.full_name}.git", to_path=download_path)
        assert os.path.isdir(download_path)
        print("Success.")
        return r.head.commit
    except Exception:
        raise GithubRepoDownloadFailedException(f"Could not clone repo {repo.full_name}.")


def download_repo(repo: Repository, storage_path=path_to_repos) -> Path:
    print(f"Cloning {repo.full_name} into {storage_path}/{repo.full_name}")
    download_path = Path.joinpath(storage_path, repo.full_name)
    if os.path.isdir(download_path):
        return download_path
    try:
        Repo.clone_from(f"https://github.com/{repo.full_name}.git", to_path=download_path)
        print("Success.")
        assert os.path.isdir(download_path)
        return download_path
    except Exception:
        raise GithubRepoDownloadFailedException(f"Could not clone repo {repo.full_name}.")
