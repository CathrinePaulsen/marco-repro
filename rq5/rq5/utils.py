import os
import re
import shutil
import subprocess
from pathlib import Path

import requests
from lxml import etree as ET

from core import HTTP_headers, namespace, GAV
from rq5.models.project import Project
from server.config import path_to_repos


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_latest_version(g: str, a: str, use_remote=False) -> str:
    return get_special_version(g, a, tag="latest", use_remote=use_remote)


def get_release_version(g: str, a: str, use_remote=False) -> str:
    return get_special_version(g, a, tag="release", use_remote=use_remote)


def get_special_version(g: str, a: str, tag: str, use_remote=False) -> str:
    if tag != "latest" and tag != "release":
        raise ValueError("The value of the argument 'tag' must be either 'release' or 'latest'.")

    if use_remote:
        base_url = "http://127.0.0.1:5000/maven"
    else:
        base_url = "https://repo1.maven.org/maven2"
    query = f"{base_url}/{g.replace('.', '/')}/{a}/maven-metadata.xml"
    response = requests.get(query, headers=HTTP_headers)
    query = f"https://repo1.maven.org/maven2/{g}/eclipse-collections/maven-metadata.xml"

    if response.headers["Content-Type"] != "text/xml":
        return tag.upper()

    root = ET.fromstring(response.content)
    special_version = root.find('versioning', namespace).find(tag, namespace)
    if special_version is not None and special_version.text is not None:
        return special_version.text
    else:
        return tag.upper()


def get_dependencies(repository_name: str, commit_sha: str, from_command: str, original=False, save_as=None, repos_path=path_to_repos) -> list[GAV]:
    if from_command != "dependency:list" and from_command != "dependency:tree":
        raise ValueError("The from_command argument must be either 'dependency:list' or 'dependency:tree'")

    # dependency:list will only give resolved GAVs
    # dependency:tree will list all declared deps (direct and transitive), and may therefore contain duplicates
    out = get_dependency_command_output(repository_name, commit_sha, from_command, original=original, save_as=save_as,
                                        repos_path=repos_path)
    gavs = parse_dependency_command_output(out.stdout, from_command)
    for gav in gavs:
        if gav.version == "RELEASE":
            gav.version = get_release_version(gav.group_id, gav.artifact_id)
        elif gav.version == "LATEST":
            gav.version = get_latest_version(gav.group_id, gav.artifact_id)

    return gavs


def parse_dependency_command_output(out: str, from_command: str):
    # Regular expression pattern to match GAVs
    if from_command == "dependency:list":
        pattern = r'    (\S+)'
    elif from_command == "dependency:tree":
        pattern = r'(?:(?!\()\S*:){4,5}\S*'
    else:
        raise ValueError("The from_command argument must be either 'dependency:list' or 'dependency:tree'")

    gav_matches = re.findall(pattern, out)
    gavs = []
    for gav_match in gav_matches:
        gav_match = gav_match.strip().split(":")
        assert len(gav_match) == 5 or len(gav_match) == 6
        if len(gav_match) == 5:
            gavs.append(GAV(group_id=gav_match[0], artifact_id=gav_match[1], packaging=gav_match[2],
                            version=gav_match[3], scope=gav_match[4]))
        if len(gav_match) == 6:
            gavs.append(GAV(group_id=gav_match[0], artifact_id=gav_match[1], packaging=gav_match[2],
                            classifier=gav_match[3], version=gav_match[4], scope=gav_match[5]))
    return gavs


def get_dependency_command_output(repository_name: str, commit_sha: str, from_command: str,
                                  repos_path=path_to_repos, save_as=None, original=False) -> subprocess.CompletedProcess:
    original_command = []
    save_to_command = []
    if original:
        if Path.is_file(repos_path / repository_name / "original_pom.xml"):
            original_command = ["-f", "original_pom.xml"]
    if save_as:
        save_to_command = ["-l", save_as]

    if from_command == "dependency:list":
        commands = ["mvn", "dependency:list"] + original_command + ["-DincludeScope=runtime", "-DincludeTypes=jar"]
    elif from_command == "dependency:tree":
        commands = (["mvn", "dependency:tree"] + original_command +
                    ["-Dverbose", "-Dscope=runtime", "-DincludeTypes=jar"])
    else:
        raise ValueError("The from_command argument must be either 'dependency:list' or 'dependency:tree'")

    repo_path = repos_path / repository_name
    assert Path.is_dir(repo_path)
    old_dir = os.getcwd()
    os.chdir(repo_path)
    if save_as:
        subprocess.run(commands + save_to_command)
    out = subprocess.run(commands, stdout=subprocess.PIPE, universal_newlines=True)
    os.chdir(old_dir)
    return out


def pom_has_tag(tag: str, pom: ET.Element) -> bool:
    tag = pom.find(f".//maven:{tag}", namespace)
    return True if tag is not None else False


def pom_has_compile_or_runtime_dependencies(pom: ET.Element) -> bool:
    dependencies_tag = pom.find(".//maven:dependencies", namespace)
    management_tag = pom.find(".//maven:dependencyManagement", namespace)

    dependencies = []
    if dependencies_tag is not None:
        dependencies += dependencies_tag.findall("maven:dependency", namespace)
    if management_tag is not None:
        dependencies += management_tag.findall("maven:dependency", namespace)

    for dep in dependencies:
        scope = dep.find("maven:scope", namespace)
        scope = "compile" if scope is None else scope.text
        if scope == "compile" or scope == "runtime":
            return True


def checkout_sha(project: Project):
    old_dir = os.getcwd()
    os.chdir(path_to_repos / project.repository)
    subprocess.run(["git", "checkout", "-f", project.sha.strip()]).check_returncode()
    os.chdir(old_dir)


def backup_pom(path_to_original: Path, path_to_backup: Path):
    if not Path.is_file(path_to_backup):  # Do not overwrite backup if it exists
        assert Path.is_file(path_to_original)
        shutil.copy(path_to_original, path_to_backup)
        assert Path.is_file(path_to_backup)
