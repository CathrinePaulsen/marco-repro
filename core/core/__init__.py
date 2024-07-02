import os
import re
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from github import Auth, Github, Repository, UnknownObjectException
from lxml import etree as ET

HTTP_headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Cookie': 'MVN_SESSION=eyJhbGciOiJIUzI1NiJ9.eyJkYXRhIjp7InVpZCI6IjliNGIyMzYwLTdlNDUtMTFlZS1hMzU3LWYxZWZiNzI5MWY5MiJ9LCJleHAiOjE3Mzc1NDYyMDgsIm5iZiI6MTcwNjAxMDIwOCwiaWF0IjoxNzA2MDEwMjA4fQ.n82-3CPLYOOlZWlf2-UCkbpHXPchcB3Bzh2ZtirLe8k; __cf_bm=.TnN1ieTPgClHmnj1fQ.CjS7XeThFuv1TobLvWmeI3g-1706010208-1-Ab4wLRgNWN956sIBuhKfCTzUSe2rG7tWKgN/EfnlgHvl8J5XYT5aV1TckXMb1MZn38VpbLiUId4YW6NcrC5HzM0=; cf_clearance=ckfujQhgwVXFPcqOmQHmn2sNsnZ3tksdgkPiH5QWDWE-1706010208-1-AZzCzxxjn8rzeH5CKHradUhz8Am+Ii0KPnybJs2KYuf0icvCYedNGdDdz0R+jyxhqJc7TZx0leXvfEHrpfsGfng='}
namespace = {'maven': 'http://maven.apache.org/POM/4.0.0'}


class MavenMetadataNotFound(Exception):
    """Raised when maven-metadata.xml cannot be found in a Maven repository."""
    pass


class PomNotFoundException(Exception):
    """Raised when the pom could not be found."""


class GitHubTag:
    """
    Class representing a GitHub tag, storing the tag's name and commit sha.
    """
    def __init__(self, tag_name: str, commit_sha: str, exact_match=False):
        self.name = tag_name
        self.commit = commit_sha
        self.exact_match = exact_match

    def __eq__(self, other):
        """
        Two tags are equal if both their names and commit shas are the same.
        """
        if self.name == other.name and self.commit == other.commit:
            return True
        return False

    def __repr__(self):
        return f"GitHubTag(name={self.name}, commit={self.commit})"


class GAV:
    def __init__(self, group_id: str, artifact_id: str, version: str, scope="", packaging="", classifier=""):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.packaging = packaging
        self.classifier = classifier
        self.version = version
        self.scope = scope

    def __repr__(self):
        scope_str = "" if not self.scope else f":{self.scope}"
        packaging_str = "" if not self.packaging else f":{self.packaging}"
        classifier_str = "" if not self.classifier else f":{self.classifier}"
        return f"{self.group_id}:{self.artifact_id}{packaging_str}{classifier_str}:{self.version}{scope_str}"

    def __eq__(self, other):
        if isinstance(other, GAV):
            if self.group_id == other.group_id and self.artifact_id == other.artifact_id:
                if self.packaging == other.packaging and self.scope == other.scope:
                    return self.version == other.version and self.classifier == other.classifier
        return False


def dependencies_are_equal(x: ET.Element, y: ET.Element, except_version=False):
    if get_text_of_child(x, "groupId") == get_text_of_child(y, "groupId"):
        if get_text_of_child(x, "artifactId") == get_text_of_child(y, "artifactId"):
            if except_version:
                return True if get_text_of_child(x, "version") != get_text_of_child(y, "version") else False
            if get_text_of_child(x, "version") == get_text_of_child(y, "version"):
                return True
    return False


def get_text_of_child(element: ET.Element, child_tag: str) -> str:
    child = element.find(f".//maven:{child_tag}", namespaces=namespace)
    return child.text if child is not None else ""


def scrape_available_versions(g: str, a: str, use_remote=False) -> list[str]:
    # Returns all available versions of GA from Maven Central as a sorted list, most recent first
    if use_remote:
        base_url = "http://127.0.0.1:5000/maven"
    else:
        base_url = "https://repo1.maven.org/maven2"
    query = f"{base_url}/{g.replace('.', '/')}/{a}/"
    response = requests.get(query, headers=HTTP_headers)
    versions = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all <a> tags with href attributes ending with "/"
        version_tags = soup.find_all('a', href=re.compile(r'^[^./][^/]*\/$'))

        # Extract version numbers from the href attributes
        versions = [tag['href'].rstrip('/') for tag in version_tags]
        versions.reverse()  # So newest are listed first

    return versions


def get_available_versions(g: str, a: str, use_remote=False, max_num=None) -> list[str]:
    """Given a GA, returns all the available versions from Maven Central or remote if max_num is not specified"""
    # Returns all available versions of GA from Maven Central as a sorted list, most recent first
    if use_remote:
        base_url = "http://127.0.0.1:5000/maven"
    else:
        base_url = "https://repo1.maven.org/maven2"
    query = f"{base_url}/{g.replace('.', '/')}/{a}/maven-metadata.xml"
    response = requests.get(query, headers=HTTP_headers)

    if response.headers["Content-Type"] != "text/xml":
        raise MavenMetadataNotFound(f"Could not find maven-metadata.xml for {g}:{a} from {query}.")

    root = ET.fromstring(response.content)
    versions = root.find('versioning', namespace).find("versions", namespace).findall("version")

    version_list = [version.text for version in versions]
    version_list.reverse()  # Reverse the list so that the newest versions are listed first

    return version_list[:max_num] if max_num else version_list


def get_github_token(filename: str = "github_api.token") -> str:
    try:
        with open(os.path.join(os.path.dirname(__file__), filename)) as f:
            return f.readline()
    except FileNotFoundError as e:
        print('No Github API token found.')
        raise e


def get_github_session():
    access_token = get_github_token()
    auth = Auth.Token(access_token)

    return Github(auth=auth)


def get_pom(groupId: str, artifactId: str, version: str) -> requests.Response:
    """Given a GAV coordinate, request its POM from Maven Central and return the http response."""
    groupId = groupId.replace(".", "/")
    pom_link = f"https://repo1.maven.org/maven2/{groupId}/{artifactId}/{version}/{artifactId}-{version}.pom"
    print(f"Downloading pom from {pom_link}")
    return requests.get(pom_link, headers=HTTP_headers)


def get_project_name_from_connection(connection: str) -> str | None:
    """
    :param connection: String content obtained from the POM's SCM connection tag
    :return: return the name (<OWNER>/<REPO>) of the given GitHub connection, None if connection is not GitHub
    """
    github_path = connection.replace(".git", "").split("github.com")[-1][1:] if "github.com" in connection else None
    if github_path:
        paths = github_path.split("/")
        return "/".join(paths[:2])
    else:
        return None


def get_candidate_tag_names(artifact_id: str, version: str) -> list[str]:
    """
    Returns a list of likely tag based on the following commonly observed patterns:
        <VERSION>, <ARTIFACT_ID>-<VERSION>, v<VERSION>, r<VERSION>,
        <MAJ.MIM.PAT>, <ARTIFACT_ID>-<MAJ.MIM.PAT>, v<MAJ.MIM.PAT>, r<MAJ.MIM.PAT>
    Also checks if dots in version has been replaced by underscores, as is the case for
        https://github.com/eclipse-aspectj/aspectj/tags
    :param artifact_id: Artifact ID of the dependency
    :param version: version of the dependency
    :return: a list of potential tag names
    """
    patterns = [f"{version}", f"{artifact_id}-{version}", f"v{version}", f"r{version}"]

    semver = extract_semver(str(version))
    semver_underscores = version.replace(".", "_")
    if semver:
        patterns += [f"{semver}", f"{artifact_id}-{semver}", f"v{semver}", f"r{semver}"]
    if semver_underscores:
        patterns += [f"{semver_underscores}", f"{artifact_id}-{semver_underscores}", f"v{semver_underscores}",
                     f"r{semver_underscores}"]

    return patterns


def get_scm_from_pom(pom_response: requests.Response, g: str, a: str, v: str):
    if pom_response.headers["Content-Type"] != "text/xml":
        print(f"Skipping, resource is not in XML format")
        raise PomNotFoundException(f"Could not find the pom of: {g}:{a}:{v}")
    root = ET.fromstring(pom_response.content)
    return root.find(".//maven:scm", namespaces={'maven': 'http://maven.apache.org/POM/4.0.0'}), root


def get_scm_from_pom_file(pomfile: Path, g: str, a: str, v: str):
    if not Path.is_file(pomfile):
        raise PomNotFoundException(f"Could not find the pom of: {g}:{a}:{v}")
    root = ET.parse(pomfile)
    return root.find(".//maven:scm", namespaces={'maven': 'http://maven.apache.org/POM/4.0.0'}), root


def get_repo_from_parent_scm(pom: ET.Element, session: Github) -> Repository:
    if pom is not None:
        parent_tag = pom.find(".//maven:parent", namespace)
        if parent_tag is not None:
            parent_group_id = get_text_of_child(parent_tag, "groupId")
            parent_artifact_id = get_text_of_child(parent_tag, "artifactId")
            parent_version = get_text_of_child(parent_tag, "version")
            if (parent_group_id, parent_artifact_id, parent_version) != (None, None, None):
                parent_pom = get_pom(parent_group_id, parent_artifact_id, parent_version)
                try:
                    parent_scm, _ = get_scm_from_pom(parent_pom, parent_group_id, parent_artifact_id,
                                                  parent_version)
                    return get_github_repo_from_scm(parent_scm, session)
                except Exception:
                    pass
    return None


def get_github_repo_from_scm(scm: ET.Element, github_session: Github) -> Repository:
    """Given an SCM element and Github session, return the Github repo via SCM. Return None if not found."""
    if scm is None:
        return None

    # Get scm:connection tag
    connection = scm.find("maven:connection", namespaces=namespace)
    if connection is None or connection.text is None:
        print("No <connection> tag inside <scm>. Checking for <developerConnection> tag")
        connection = scm.find("maven:developerConnection", namespaces=namespace)
        if connection is None or connection.text is None:
            print("No <connection> or <developerConnection> tag inside <scm>. Checking for <url> tag.")
            connection = scm.find("maven:url", namespaces=namespace)
            if connection is None or connection.text is None:
                print("No <connection> or <developerConnection> tag inside <scm>. Skipping project.")
                return None

    # Get github author/project (project_name) string via connection tag
    project_name = get_project_name_from_connection(connection.text)
    if not project_name:
        print("No github connection. Skipping project.")
        return None

    # Get Github repo from SCM connection
    try:
        print(f"Getting repo from Github with name {project_name}")
        github_repo = github_session.get_repo(project_name)
        return github_repo
    except UnknownObjectException:
        print("Could not find repo via scm; scm is possibly broken. Skipping project.")
        return None


def get_version_tag_from_scm_or_pom(scm: ET.Element, pom_version: str) -> str:
    """
    Given an <scm> element, returns the tag version provided by <tag> if it contains a specific element.
    If <tag> is missing, or contains versions like "HEAD" or "${version}" then the GAV version is returned.
    :param scm: ElementTree of the <scm> element obtained from the POM
    :param pom_version: version given by Maven GAV
    :return: return the tag version provided by <scm><tag></tag></scm> if present, otherwise returns the GAV version.
    """
    # Get <tag> tag if available
    tag = scm.find("maven:tag", namespaces=namespace) if scm is not None else None
    if tag is not None and tag.text != "HEAD" and "${" not in tag.text:
        version_tag = tag.text
    else:
        print("No <tag> present, or tag is HEAD, or tag is using variable replacement. Using POM version.")
        version_tag = pom_version

    return version_tag


def extract_semver(string: str) -> str:
    print(f"Extracting semver from: {string}")
    pattern = r'\d+\.\d+\.\d+'
    match = re.search(pattern, string)
    return match.group() if match else ""


def get_github_tag(repo: Repository, artifact_id: str, version: str, max_num_tags=100) -> GitHubTag | None:
    """
    Given a GitHub repository, its Maven artifact ID and version, return the likely GitHub tag based on exact
    matching of commonly used tag versioning patterns and inexact string match if no exact match can be found.
    :param repo: The GitHub repository
    :param artifact_id: Artifact ID of the repository's corresponding Maven GAV
    :param version: version of the repository's corresponding Maven GAV
    :param max_num_tags: The max number of tags that will be checked for inexact string match
    :return: GitHubTag if a tag was found, None otherwise
    """
    # First get tag by exact match
    for candidate in get_candidate_tag_names(artifact_id, version):
        tag = get_github_tag_by_name(repo, candidate)
        if tag:
            print(f"Found tag by exact match: {tag.name}")
            return tag

    # If there is no exact match, get the shortest inexact match through loop
    tag_candidates = []
    # If there are too many tags, only match with the N latest ones
    print(f"Could not find tag by exact match, performing inexact match...")
    repo_tags = repo.get_tags()
    if repo_tags.totalCount > max_num_tags:
        repo_tags = repo_tags[:max_num_tags]

    version_underscores = version.replace(".", "_")
    for tag in repo_tags:
        if version in tag.name or version_underscores in tag.name:
            tag_candidates.append(tag)

    print(tag_candidates)

    if len(tag_candidates) == 0:
        print("Could not find tag for project")
        return None
    if len(tag_candidates) == 1:
        chosen_tag = tag_candidates[0]
        print(f"Found commit {chosen_tag.commit.sha} for tag {chosen_tag.name}")
        return GitHubTag(chosen_tag.name, chosen_tag.commit.sha, exact_match=False)
    # If there is more than one tag match, select the closest match which will be the shortest match
    if len(tag_candidates) > 1:
        chosen_tag = min(tag_candidates, key=lambda x: len(x.name))
        return GitHubTag(chosen_tag.name, chosen_tag.commit.sha, exact_match=False)


def get_github_tag_by_name(repo: Repository, tag_name: str) -> GitHubTag | None:
    """
    GitHub tags are either lightweight or annotated, and their commit sha is fetched differently.
      * Any tag can be fetched by name from: api.github.com/repos/<OWNER>/<REPO>/git/refs/tags/<TAG_NAME>
      * The sha of the returned json ref object (ref.object.sha) is the commit sha for lightweight tags, but the tag sha
        for annotated tags.
      * The commit sha for an annotated tag can be found via ref.object.sha from the json ref returned from:
         api.github.com/repos/<OWNER>/<REPO>/git/tags/<TAG_SHA>
    :param repo: The GitHub repository
    :param tag_name: name of the tag to look for in the repository
    :return: a GitHubTag if a tag was found, None otherwise
    """
    # Get tag
    try:
        print(f"Looking for: api.github.com/repos/{repo.full_name}/git/refs/tags/{tag_name}")
        ref = repo.get_git_ref(f"tags/{tag_name}")  # Returns GitRef(None) when the api returns a list
    except UnknownObjectException:
        return None  # return None if not found

    try:
        object_type = ref.object.type
    except AttributeError:
        return None  # return None if the response is malformed

    # If tag is lightweight the given sha is the commit sha, so we can directly return it
    if object_type == "commit":
        return GitHubTag(tag_name, ref.object.sha, exact_match=True)

    # If the tag is annotated the given sha is the tag sha, so the commit sha must be fetched via the tag sha
    if object_type == "tag":
        tag_sha = ref.object.sha
        return GitHubTag(tag_name, repo.get_git_tag(tag_sha).object.sha, exact_match=True)

    return None  # shouldn't really happen unless response is malformed somehow


def get_github_repo_and_tag(g: str, a: str, v: str,
                            repo_name=None, pom_path=None) -> tuple[Optional[Repository], Optional[GitHubTag]]:
    """Given a GAV, returns the tuple (Repository, GitHubTag) via pom analysis."""
    pom = get_pom(g, a, v)
    pom_element = None
    try:
        scm, pom_element = get_scm_from_pom(pom, g, a, v)
    except PomNotFoundException as e:
        print(e)
        if pom_path:
            print(f"Looking for POM using the provided path {pom_path}")
            try:
                scm, pom_element = get_scm_from_pom_file(pom_path, g, a, v)
            except PomNotFoundException as e:
                print(e)
                raise PomNotFoundException(f"Could not find POM from pomfile {pom_path}")
            try:
                pom_element = ET.parse(pom_path)
            except Exception:
                pass
        else:
            raise e

    with get_github_session() as session:
        if repo_name:
            print(f"Using provided repo_name={repo_name}")
            repo = session.get_repo(repo_name)
        else:
            repo = get_github_repo_from_scm(scm, session)
        if repo is None and pom_element is not None:
            repo = get_repo_from_parent_scm(pom_element, session)

    if not repo:
        return None, None

    tag_version = get_version_tag_from_scm_or_pom(scm, v)
    tag = get_github_tag(repo, a, tag_version)
    if not tag:
        # If no commit was found using the version provided by <tag>, try matching with the version provided by pom
        tag = get_github_tag(repo, a, v)

    return repo, tag


