import os
import subprocess
from pathlib import Path

from server.test_failure import at_least_one_passing_test
from server.config import COMPILE_TIMEOUT, TEST_TIMEOUT


def get_sha_of_repo_head(repo_path: Path) -> str:
    assert Path.is_dir(repo_path)
    old_dir = os.getcwd()
    os.chdir(repo_path)
    out = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], stdout=subprocess.PIPE, universal_newlines=True)
    os.chdir(old_dir)
    sha = out.stdout
    return sha


def repo_has_tests(repo_path: Path) -> bool:
    print(f"Checking runnable tests for {repo_path}")
    return run_repo_tests(repo_path)


def run_repo_tests(repo_path: Path) -> bool:
    assert Path.is_dir(repo_path)
    assert Path.is_dir(repo_path / "target")
    old_dir = os.getcwd()
    os.chdir(repo_path)
    try:
        subprocess.run(["mvn", "surefire:test"], timeout=TEST_TIMEOUT)
        has_tests = at_least_one_passing_test(repo_path / "target" / "surefire-reports")
    except subprocess.TimeoutExpired:
        has_tests = False
    os.chdir(old_dir)
    return has_tests


def repo_compiles(repo_path: Path) -> bool:
    return compile_repo(repo_path)


def compile_only_repo(repo_path: Path, log_name="compile.log") -> bool:
    assert Path.is_dir(repo_path)
    log_path = repo_path / log_name
    compiles = False
    old_dir = os.getcwd()
    os.chdir(repo_path)
    try:
        subprocess.run(["mvn", "clean", "test-compile", "-Dspotbugs.skip=true", "-Dspotless.check.skip=True", "-Dspotless.apply.skip=True", "-l", log_path], timeout=COMPILE_TIMEOUT)
        if Path.is_file(log_path):
            with open(log_path, 'r') as f:
                compiles = "BUILD SUCCESS" in f.read()
    except subprocess.TimeoutExpired:
        pass
    os.chdir(old_dir)
    return compiles


def compile_repo(repo_path: Path, use_pom="pom.xml", save_as=None) -> bool:
    print(f"Compiling repo {repo_path}, save log as {save_as}")
    assert Path.is_dir(repo_path)
    old_dir = os.getcwd()
    os.chdir(repo_path)
    pom_path = repo_path / use_pom
    save_as_command = ["-l", repo_path / save_as] if save_as else []
    try:
        out = subprocess.run(["mvn", "clean", "test-compile", "-Dspotbugs.skip=true",
                              "-Dspotless.check.skip=True", "-Dspotless.apply.skip=True", "-f", pom_path] + save_as_command,
                             stdout=subprocess.PIPE, universal_newlines=True, timeout=COMPILE_TIMEOUT)
        if not save_as:
            compiles = "[INFO] BUILD SUCCESS" in out.stdout
        else:
            with open(repo_path / save_as, 'r') as f:
                compiles = "[INFO] BUILD SUCCESS" in f.read()
    except subprocess.TimeoutExpired:
        compiles = False
    os.chdir(old_dir)
    return compiles
# mvn clean install -DskipTests -Dspotbugs.skip=True -f original_pom.xml -l original_build.log