import os
import pathlib
import subprocess
from pathlib import Path
from typing import Optional

from github import Repository

from core import get_github_session
from server.config import CAND_TEMPLATES_DIR, COMPILE_TIMEOUT
from server.exceptions import (GithubRepoNotFoundException, MavenCompileFailedException,
                               MavenNoPomInDirectoryException, CandidateMavenCompileTimeout,
                               MavenResolutionFailedException)
from server.template import Template


class CandidateTemplate(Template):
    """Class responsible for the creation of candidate templates containing classes and generated-sources."""
    def __init__(self, g: str, a: str, v: str, repo_storage_path="", pom_path="", repo_name="", tag_name="",
                 commit_sha=""):
        super().__init__(g, a, v, repo_storage_path=repo_storage_path, pom_path=pom_path, repo_name=repo_name,
                         tag_name=tag_name, commit_sha=commit_sha)

    def template_exists(self) -> bool:
        if os.path.isfile(self.path / "pom.xml") and os.path.isdir(pathlib.Path.joinpath(self.target_path, "classes")):
            return True
        return False

    def get_base_dir(self) -> Path:
        return CAND_TEMPLATES_DIR

    def get_preexisting_github_metadata(self) -> Optional[Repository]:
        if os.path.isdir(pathlib.Path.joinpath(self.target_path, "classes")):
            if os.path.isfile(pathlib.Path.joinpath(self.path, "_metadata.json")):
                self.load_metadata()
                with get_github_session() as session:
                    repo = session.get_repo(self.repo_name)
                    if repo is None:
                        raise GithubRepoNotFoundException(f"Could not find repo {self.repo_name} on Github")
                    return repo
        return None

    def prepare_template(self):
        # Compile test classes and sources of the base and move them to temp/target/
        old_dir = os.getcwd()
        os.chdir(self.repo_path)
        subprocess.run(["git", "checkout", "-f", self.commit_sha])
        try:
            out = subprocess.run(["mvn", "clean", "test-compile", "-Dspotbugs.skip=true", "-Dspotless.check.skip=true", "-Dspotless.apply.skip=true"],
                                 stdout=subprocess.PIPE, universal_newlines=True, timeout=COMPILE_TIMEOUT)
            if "there is no POM in this directory" in out.stdout:
                os.chdir(old_dir)
                raise MavenNoPomInDirectoryException(f"Found no POM for candidate {self.gav}")
            elif "Could not resolve dependencies" in out.stdout:
                os.chdir(old_dir)
                raise MavenResolutionFailedException(f"Failed to resolve dependencies for candidate {self.gav}")
            elif "Compilation failure" in out.stdout or "Fatal error compiling" in out.stdout:
                os.chdir(old_dir)
                raise MavenCompileFailedException(f"Failed to compile for candidate {self.gav}")
            elif "BUILD FAILURE" in out.stdout:
                os.chdir(old_dir)
                raise MavenCompileFailedException(f"Failed to compile for base {self.gav}")
        except subprocess.TimeoutExpired:
            os.chdir(old_dir)
            raise CandidateMavenCompileTimeout(f"mvn clean test-compile lasted more than {COMPILE_TIMEOUT}s")

        classes_path = pathlib.Path.joinpath(self.repo_path).resolve() / "target" / "classes"
        if not os.path.isdir(classes_path):
            os.chdir(old_dir)
            raise MavenCompileFailedException(f"Failed to compile {self.gav}")

        try:
            subprocess.run(["mv", "target/generated-sources", self.target_path])
        except Exception:
            pass
        subprocess.run(["mv", "target/classes", self.target_path])
        subprocess.run(["cp", "pom.xml", self.path])
        os.chdir(old_dir)
