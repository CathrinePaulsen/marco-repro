from pathlib import Path

from git import Commit
from github import GithubException
from sqlalchemy.orm import Session

from core import get_github_session
from rq12.models import engine, Project
from server.config import download_repo_and_return_commit
from server.exceptions import GithubRepoDownloadFailedException


def add_to_db(repo_name: str, commit: Commit, session: Session) -> None:
    dep = Project(
        name=repo_name, commit=str(commit)
    )
    session.add(dep)
    session.commit()


def collect_projects():
    repos_path = Path(__file__).parent.parent.resolve() / "resources" / "repos"
    with Session(engine) as db:
        with get_github_session() as g:
            # Get Java repos created since 01/01/2023 with at least 10 stars
            repos = g.search_repositories(query="created:>2023-01-01 language:java stars:>=10")
            count = 0
            until = repos.totalCount

            for repo in repos:
                count += 1
                # if repo.get_commits().totalCount < 50:  # Skip projects with less than 50 commits
                #     print(f"[SKIPPING] Repo has less than 50 commits {count}/{until}")
                #     continue
                try:
                    repo.get_contents("pom.xml")

                    # Check if repo is already in db
                    with Session(engine) as session:
                        q = session.query(Project.name).filter(Project.name == repo.full_name)
                        repo_in_db = session.query(q.exists()).scalar()

                    # If repo is not already in db, collect it
                    if not repo_in_db:
                        commit = download_repo_and_return_commit(repo, storage_path=repos_path)
                        if commit:  # Commit is only returned if the download was successful
                            add_to_db(repo.full_name, commit, db)
                            print(f"Downloaded repo {count}/{until}")
                    else:
                        print("Repo already collected.")
                except (GithubException, GithubRepoDownloadFailedException):
                    print(f"Could not clone {repo.full_name} or has no pom.xml file in root directory.")
                    pass
