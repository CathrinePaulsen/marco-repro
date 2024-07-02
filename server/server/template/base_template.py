import os
import pathlib
import subprocess
from pathlib import Path
from typing import Optional

from github import Repository

from core import get_github_session
from server.config import BASE_TEMPLATES_DIR, COMPILE_TIMEOUT, TEST_TIMEOUT
from server.exceptions import (GithubRepoNotFoundException, MavenSurefireTestFailedException,
                               MavenNoPomInDirectoryException, BaseMavenCompileTimeout, BaseMavenTestTimeout,
                               MavenCompileFailedException, MavenResolutionFailedException)
from server.template import Template
from server.test_failure import at_least_one_passing_test


class BaseTemplate(Template):
    """Class responsible for the creation of candidate templates containing test-classes and generated-test-sources."""
    def __init__(self, g: str, a: str, v: str, repo_storage_path="", pom_path="", repo_name="", tag_name="",
                 commit_sha=""):
        print(f"BaseTemplate constructor got repo_name={repo_name}")
        super().__init__(g, a, v, repo_storage_path=repo_storage_path, pom_path=pom_path, repo_name=repo_name,
                         tag_name=tag_name, commit_sha=commit_sha)

    def template_exists(self) -> bool:
        if os.path.isdir(pathlib.Path.joinpath(self.target_path, "surefire-reports_BASE")) and \
                os.path.isdir(pathlib.Path.joinpath(self.target_path, "test-classes")):
            return True
        return False

    def get_base_dir(self) -> Path:
        return BASE_TEMPLATES_DIR

    def get_preexisting_github_metadata(self) -> Optional[Repository]:
        if os.path.isdir(pathlib.Path.joinpath(self.target_path, "test-classes")):
            if os.path.isdir(pathlib.Path.joinpath(self.target_path, "surefire-reports_BASE")):  # TODO: remove
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
        print("Running mvn clean test-compile...")
        try:
            out = subprocess.run(["mvn", "clean", "test-compile", "-Dspotbugs.skip=true",
                                  "-Dspotless.check.skip=true", "-Dspotless.apply.skip=true"],
                                 stdout=subprocess.PIPE, universal_newlines=True, timeout=COMPILE_TIMEOUT)
            if "there is no POM in this directory" in out.stdout:
                os.chdir(old_dir)
                raise MavenNoPomInDirectoryException(f"Found no POM for base {self.gav}")
            elif "Could not resolve dependencies" in out.stdout:
                os.chdir(old_dir)
                raise MavenResolutionFailedException(f"Failed to resolve dependencies for base {self.gav}")
            elif "Compilation failure" in out.stdout or "Fatal error compiling" in out.stdout:
                os.chdir(old_dir)
                raise MavenCompileFailedException(f"Failed to compile for base {self.gav}")
            elif "BUILD FAILURE" in out.stdout:
                os.chdir(old_dir)
                raise MavenCompileFailedException(f"Failed to compile for base {self.gav}")
        except subprocess.TimeoutExpired:
            os.chdir(old_dir)
            raise BaseMavenCompileTimeout(f"mvn clean compile lasted more than {COMPILE_TIMEOUT}s")

        try:
            out = subprocess.run(["mvn", "surefire:test"],
                                 stdout=subprocess.PIPE, universal_newlines=True, timeout=TEST_TIMEOUT)
            if "No tests to run" in out.stdout or "Tests are skipped" in out.stdout:
                os.chdir(old_dir)
                raise MavenSurefireTestFailedException(f"Found no running tests for base {self.gav}")
        except subprocess.TimeoutExpired:
            os.chdir(old_dir)
            raise BaseMavenTestTimeout(f"mvn surefire:test lasted more than {TEST_TIMEOUT}s")
        print("Done.")

        surefire_path = pathlib.Path.joinpath(self.repo_path).resolve() / "target" / "surefire-reports"
        if not at_least_one_passing_test(surefire_path):
            os.chdir(old_dir)
            raise MavenSurefireTestFailedException(f"Found no running tests for base {self.gav}")
        try:
            subprocess.run(["mv", "target/generated-test-sources", self.target_path])
        except Exception:
            pass
        subprocess.run(["mv", "target/test-classes", self.target_path])
        subprocess.run(["mv", "target/surefire-reports", pathlib.Path.joinpath(self.target_path,
                                                                               "surefire-reports_BASE")])
        subprocess.run(["cp", "pom.xml", self.path])
        os.chdir(old_dir)
