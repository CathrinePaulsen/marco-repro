import json
import os
import pathlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from github import Repository

from core import (get_github_session, PomNotFoundException,
                  get_github_repo_and_tag)
from server.config import download_repo
from server.exceptions import GithubRepoNotFoundException, GithubTagNotFoundException


class Template(ABC):
    """Abstract class for BaseTemplate and CandidateTemplate."""

    @abstractmethod
    def __init__(self, g: str, a: str, v: str, repo_storage_path="", pom_path="", repo_name="", tag_name="", commit_sha=""):
        self.group_id = g
        self.artifact_id = a
        self.version = v
        self.gav = f"{g}:{a}:{v}"
        self.repo_name = repo_name
        self.tag_name = tag_name
        self.commit_sha = commit_sha

        self.base_dir: Path = self.get_base_dir()

        self.path: Path = self.get_or_create_template_dir()
        self.pom_path = self.path / "pom.xml"
        self.target_path: Path = pathlib.Path.joinpath(self.path, "target")
        assert os.path.isdir(self.path)
        assert os.path.isdir(self.target_path)

        if self.repo_name:
            with get_github_session() as session:
                repo: Repository = session.get_repo(repo_name)
            if self.tag_name and self.commit_sha:
                self.store_metadata(self.repo_name, self.tag_name, self.commit_sha)
            else:
                # get tag_name and commit_sha from repo
                self.get_github_metadata(repo_name=self.repo_name)
        else:  # Get repo from pom
            # Sets repo_name, tag_name, commit_sha, and returns Repository
            repo: Repository = self.get_github_metadata(pom_path=pom_path)

        if not self.template_exists():
            if repo_storage_path:
                self.repo_path: Path = download_repo(repo, storage_path=repo_storage_path)  # Downloads repo (unless it exists) and returns its path
            else:
                self.repo_path: Path = download_repo(repo)  # Downloads repo (unless it exists) and returns its path
            module_path = self.repo_path / self.artifact_id
            if Path.is_dir(module_path):
                self.repo_path = module_path
                print(f"Found module path, repo_path={self.repo_path}")
            self.prepare_template()  # Generate test files and move them into the template

    @abstractmethod
    def template_exists(self) -> bool:
        pass

    @abstractmethod
    def get_base_dir(self) -> Path:
        pass

    @abstractmethod
    def get_preexisting_github_metadata(self) -> Optional[Repository]:
        pass

    @abstractmethod
    def prepare_template(self):
        pass

    def get_or_create_template_dir(self) -> Path:
        """Creates <base_dir>/gav/target/ if it does not already exist and returns the path to <base_dir>/gav"""
        old_dir = os.getcwd()
        gav = f"{self.group_id}:{self.artifact_id}:{self.version}"
        template_path = pathlib.Path.joinpath(self.base_dir, gav)

        # If the template already exists, simply return the path
        if os.path.isdir(template_path):
            return template_path

        # Otherwise, create the template and return the path
        os.chdir(self.base_dir)
        os.mkdir(gav)
        os.chdir(template_path)
        os.mkdir("target")
        os.chdir(old_dir)

        return template_path

    def load_metadata(self):
        metadata = read_template_metadata(self.path)
        self.repo_name = metadata['repo_name']
        self.tag_name = metadata['tag_name']
        self.commit_sha = metadata['commit_sha']

    def store_metadata(self, repo_name: str, tag_name: str, commit_sha: str):
        self.repo_name = repo_name
        self.tag_name = tag_name
        self.commit_sha = commit_sha
        write_template_metadata(repo_name, tag_name, commit_sha, self.path)

    def get_github_metadata(self, repo_name=None, pom_path=None) -> Repository:
        # If template already exists, load metadata and return
        preexisting_repo = self.get_preexisting_github_metadata()
        if preexisting_repo:
            return preexisting_repo

        # Otherwise, get Github metadata via pom
        try:
            repo, tag = get_github_repo_and_tag(self.group_id, self.artifact_id, self.version,
                                                repo_name=repo_name, pom_path=pom_path)
        except PomNotFoundException as e:
            raise e

        if repo is None:
            raise GithubRepoNotFoundException(f"Could not find Github repo via scm of: "
                                              f"{self.group_id}:{self.artifact_id}:{self.version}")

        if tag is None:
            raise GithubTagNotFoundException(f"Could not find Github tag of "
                                             f"{self.group_id}:{self.artifact_id}:{self.version} "
                                             f"from repo {repo.full_name}")

        self.store_metadata(repo.full_name, tag.name, tag.commit)
        return repo


def read_template_metadata(path: Path):
    filepath = pathlib.Path.joinpath(path, "_metadata.json")
    assert os.path.isfile(filepath)
    with open(filepath, 'r') as f:
        return json.load(f)


def write_template_metadata(repo_name: str, tag_name: str, commit_sha: str, path: Path):
    metadata = {
        'repo_name': repo_name, 'tag_name': tag_name, 'commit_sha': commit_sha
    }
    with open(pathlib.Path.joinpath(path, "_metadata.json"), 'w') as f:
        json.dump(metadata, f, indent=4)

