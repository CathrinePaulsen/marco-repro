from typing import Optional

from github import Repository, UnknownObjectException, PullRequest, ContentFile, PaginatedList, Github


def repo_has_file(repo: Repository, filepath: str) -> bool:
    """Returns True if the repo contains the exact file, otherwise False."""
    try:
        return True if repo.get_contents(filepath) else False
    except UnknownObjectException:
        return False


def get_file(repo: Repository, filepath: str) -> Optional[ContentFile]:
    """Retrieves the ContentFile with the given filepath if it exists, otherwise None."""
    try:
        file = repo.get_contents(filepath)
        return file[0] if isinstance(file, list) else file
    except UnknownObjectException:
        return None


def repo_has_pom(repo: Repository) -> bool:
    """Returns True if the repo contains a pom file in its root directory, otherwise False."""
    return repo_has_file(repo, "pom.xml")


def repo_has_maven_dependabot(repo: Repository) -> bool:
    """Returns True if the repo has dependabot updates enabled for Maven, otherwise False."""
    dependabot_config = get_file(repo, ".github/dependabot.yml")
    if not dependabot_config:
        return False
    dependabot_content = dependabot_config.decoded_content.decode("utf-8")
    if 'package-ecosystem: "maven"' in dependabot_content or "package-ecosystem: 'maven'" in dependabot_content:
        has_maven = True
    else:
        has_maven = False
    return has_maven


def get_dependabot_prs_of_repo(repo: Repository, session: Github) -> list[PullRequest]:
    """Generator used for looping over the given repo's pull requests if they fulfill the following criteria:
        1. The PR is a merged dependabot update
        2. there is only one commit, which is to a pom file"""
    query = f"type:pr is:merged author:dependabot[bot] repo:{repo.full_name}"
    pr_issues = session.search_issues(query=query)
    for issue in pr_issues:
        pr = repo.get_pull(issue.number)
        if pr_updates_pom(pr) and pr_has_one_commit(pr):
            print(f"[VALID] {repo.full_name}/pull/{pr.number}")
            yield pr
        else:
            print(f"[SKIP] {repo.full_name}/pull/{pr.number}")


def pr_opened_by_dependabot(pr: PullRequest) -> bool:
    """Returns True if the given pull request was opened by dependabot, otherwise False."""
    return pr.user.login == "dependabot[bot]"


def pr_updates_pom(pr: PullRequest) -> bool:
    """Returns True if the given pull request updates a pom file, otherwise False."""
    if pr.changed_files == 1:
        file = pr.get_files()[0]
        return file.filename.endswith("pom.xml")
    return False


def pr_has_one_commit(pr: PullRequest) -> bool:
    """Returns True if the given pull request only contains one commit, otherwise False."""
    return True if pr.commits == 1 else False


@DeprecationWarning
def merged_dependabot_prs(repo: Repository):
    """Generator used for looping over the given repo's pull requests if they fulfill the following criteria:
        1. The PR is a merged dependabot update
        2. there is only one commit, which is to a pom file"""
    closed_prs = repo.get_pulls(state="closed", sort="created", direction="desc")
    for pr in closed_prs:
        if pr_updates_pom(pr) and pr_opened_by_dependabot(pr) and pr.is_merged() and pr_has_one_commit(pr):
            print(f"[VALID] {repo.full_name}/pull/{pr.number}")
            yield pr
        else:
            print(f"[SKIP] {repo.full_name}/pull/{pr.number}")