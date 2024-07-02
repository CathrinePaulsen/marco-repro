import os
import subprocess
from pathlib import Path

import pandas as pd
import requests
from github import Repository

from core import (get_project_name_from_connection, get_github_repo_and_tag,
                  PomNotFoundException, HTTP_headers)
from rq6.utils import Result


def extract_value(line):
    return line.split('=')[1].strip()


class ReproducibleCentralInfo:
    """
    Class to store the info obstained from a dependency's reproducible central buildspec file.
    """
    def __init__(self, group_id: str, artifact_id: str, version: str, repo: str, tag: str):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version
        self.repo = repo
        self.tag = tag


def parse_buildspec(path_to_buildspec: Path) -> ReproducibleCentralInfo | None:
    """
    :param path_to_buildspec: absolute path to a dependency's buildspec file
    :return: a ReproducibleCentralInfo object containing the info extracted from the buildspec file
    """
    with open(path_to_buildspec) as f:
        group_id, artifact_id, version, git_repo, git_tag = None, None, None, None, None
        for line in f.readlines():
            if line.startswith('groupId='):
                group_id = extract_value(line)
            elif line.startswith('artifactId='):
                artifact_id = extract_value(line)
            elif line.startswith('version='):
                version = extract_value(line)
            elif line.startswith('gitRepo='):
                git_repo = extract_value(line)
                if git_repo:
                    if "sed s" in git_repo:
                        print(git_repo)
                        input(path_to_buildspec)
                    git_repo = git_repo.replace("${artifactId}", artifact_id)
                if git_repo.endswith(".git"):
                    git_repo = git_repo[:-4]
            elif line.startswith('gitTag='):
                git_tag = extract_value(line)
                git_tag = git_tag.replace("^", "")
                git_tag = git_tag.replace("${version}", version)
                git_tag = git_tag.replace("{version}", version)
                git_tag = git_tag.replace("$version", version)
                git_tag = git_tag.replace("${artifactId}", artifact_id)
                git_tag = git_tag.replace("{artifactId}", artifact_id)
                git_tag = git_tag.replace("$artifactId", artifact_id)

    if not group_id or not artifact_id or not version:
        return None
    git_repo_name = get_project_name_from_connection(git_repo)
    return ReproducibleCentralInfo(group_id, artifact_id, version, git_repo_name, git_tag)


def has_tests(repo: Repository, commit_sha: str) -> bool:
    """
    Slow approach: actually run the tests...
    Alternative (current code): look for files that match: Test*.java, *Test.java, *Tests.java, *TestCase.java
    :param repo: the GitHub repository to evaluate
    :return: True if the given repo has tests, False otherwise
    """

    tree = repo.get_git_tree(commit_sha, recursive=True)
    for obj in tree.tree:
        end = obj.path.split("/")[-1]
        if end.endswith(".java"):
            filename = end.split(".")[0]
            if filename.endswith("Test") or filename.endswith("Tests") or filename.endswith("TestCase") or filename.startswith("Test"):
                print(f"Found test ({obj.path}) for {repo.full_name}")
                return True

    print(f"Found no tests for {repo.full_name}. WAITING FOR INPUT TO CONTINUE")
    return False


def get_buildspec_files(path_to_rc: Path) -> list[str]:
    """
    Returns a list of all .buildspec files contained in the local Reproducible Central repository
    :param path_to_rc: absolute path to the content directory in the reproducible central repository
    :return: list of .buildspec filenames (paths starting with "./", relative to reproducible-central/content)
    """
    os.chdir(path_to_rc)
    output = subprocess.run(["find", ".", "-name", "*.buildspec"], stdout=subprocess.PIPE, universal_newlines=True)
    items = output.stdout.split("\n")
    return [x for x in items if x.endswith(".buildspec")]


def create_raw():
    WRITE_TO = Path(__file__).parent.resolve() / "rq3_raw.csv"
    rows = []

    try:
        BUILDSPEC_PATH = Path(__file__).parent.parent.parent.parent.resolve() / "reproducible-central" / "content"
        buildspec_files = get_buildspec_files(BUILDSPEC_PATH)
        n_total = len(buildspec_files)

        for i, filename in enumerate(buildspec_files):
            print(f"\nPROGRESS {i+1}/{n_total} ({int((i+1)/n_total*100)}%)")
            print(f"Processing {Path.joinpath(BUILDSPEC_PATH, filename[2:])}")

            gt = parse_buildspec(Path.joinpath(BUILDSPEC_PATH, filename[2:]))  # ground truth info
            if not gt:
                print(f"Skipping malformed datapoint: {Path.joinpath(BUILDSPEC_PATH, filename[2:])}")
                continue
            print("groupId:", gt.group_id)
            print("artifactId:", gt.artifact_id)
            print("version:", gt.version)
            print("gitRepoName:", gt.repo)
            print("gitTag:", gt.tag)

            row = {
                'ga': f"{gt.group_id}:{gt.artifact_id}",
                'version': gt.version,
                'groundtruth_repo': gt.repo,
                'groundtruth_tag': gt.tag,
                'repo': None,
                'tag': None,
                'commit': None,
                'exact_match': None,
                'has_tests': None,
                'has_tests_jar': None,
                'err': None,
            }
            print(f"Row={row}")
            rows.append(row)

    except KeyboardInterrupt as e:
        print(e)
        pass

    # print("Converting result list to df...")
    # df = pd.DataFrame(rows)
    # print(f"Writing df to {WRITE_TO}...")
    # df.to_csv(WRITE_TO, index=False)
    # print(f"Done.")


def process_tests_jars(override=False):
    READ_FROM = Path(__file__).parent.resolve() / "rq3_results.csv"
    WRITE_TO = Path(__file__).parent.resolve() / "rq3_results.csv"

    df = pd.read_csv(READ_FROM)

    total = len(df)
    count = 0

    try:
        for index, row in df.iterrows():
            count += 1
            print(f"\nPROGRESS {count}/{total} ({int(count/total*100)}%)")

            if not override:
                if not pd.isnull(row['has_tests_jar']):
                    print(f"\nSKIPPING {count}/{total} ({int(count/total*100)}%)")
                    continue

            g, a = row['ga'].split(":")
            version = row['version']
            base_url = "https://repo1.maven.org/maven2"
            query = f"{base_url}/{g.replace('.', '/')}/{a}/{version}/{a}-{version}-tests.jar"
            response = requests.get(query, headers=HTTP_headers)
            has_tests_jar = True if response.status_code == 200 else False
            print(f"has_tests_jar={has_tests_jar}")

            df.at[index, 'has_tests_jar'] = has_tests_jar

    except KeyboardInterrupt as e:
        print(e)
        pass

    print(f"Writing df to {WRITE_TO}...")
    df.to_csv(WRITE_TO, index=False)
    print(f"Done.")


def process_linking(override=False):
    READ_FROM = Path(__file__).parent.resolve() / "rq3_results.csv"  # "rq3_raw.csv" to redo from scratch
    WRITE_TO = Path(__file__).parent.resolve() / "rq3_results.csv"

    df = pd.read_csv(READ_FROM)

    total = len(df)
    count = 0

    try:
        # Iterate through the DataFrame row by row
        for index, row in df.iterrows():
            count += 1
            print(f"\nPROGRESS {count}/{total} ({int((count)/total*100)}%)")
            ga = row['ga']
            g, a = ga.split(":")
            version = row['version']
            print(f"Processing {ga}:{version}")
            if not override:
                if not pd.isnull(row['repo']) or not pd.isnull(row['err']):
                    print(f"\nSKIPPING {count}/{total} ({int((count)/total*100)}%)")
                    continue

            repo, repo_name, tag, tag_name, tag_commit, exact_match, repo_has_tests, err = None, None, None, None, None, None, None, None
            try:
                repo, tag = get_github_repo_and_tag(g, a, version)
                if repo is None:
                    err = Result.NO_GITHUB_LINK
                elif tag is None:
                    repo_name = repo.full_name
                    err = Result.NO_GITHUB_TAG
                else:
                    repo_name = repo.full_name
                    tag_name = tag.name
                    tag_commit = tag.commit
                    exact_match = tag.exact_match
                    repo_has_tests = has_tests(repo, tag.commit)
            except PomNotFoundException as e:
                print(e)
                err = Result.NO_POM

            df.at[index, 'repo'] = repo_name
            df.at[index, 'tag'] = tag_name
            df.at[index, 'tag'] = tag_name
            df.at[index, 'commit'] = tag_commit
            df.at[index, 'exact_match'] = exact_match
            df.at[index, 'has_tests'] = repo_has_tests
            df.at[index, 'err'] = err

    except KeyboardInterrupt as e:
        print(e)
        pass

    print(f"Writing df to {WRITE_TO}...")
    df.to_csv(WRITE_TO, index=False)
    print(f"Done.")
