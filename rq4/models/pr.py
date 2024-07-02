import re

import sqlalchemy
from github import Github
from github import PullRequest
from sqlalchemy import Boolean, ForeignKey
from sqlalchemy import Column, String, Integer, ForeignKeyConstraint
from sqlalchemy.orm import Session
from sqlalchemy.orm import relationship

from models import Base
from models.link import Link


class PR(Base):
    """Table representation of PRs used to extract datapoints of updates."""
    __tablename__ = "prs"

    repository = Column(String, ForeignKey("projects.repository"), primary_key=True)
    number = Column(Integer, primary_key=True)
    eligible = Column(Boolean, nullable=False)
    ga = Column(String, nullable=False)
    v_old = Column(String, nullable=False)
    v_new = Column(String, nullable=False)
    update_type = Column(String, nullable=False)

    statically_compatible = Column(Boolean, nullable=True)
    dynamically_compatible = Column(Boolean, nullable=True)
    err = Column(String, nullable=True)

    links = relationship("Link", secondary="pr_links")


class PRLink(Base):
    """Association table for the GitHub links of GAVs in the collected PRs."""
    __tablename__ = "pr_links"
    __table_args__ = (
        ForeignKeyConstraint(["repository", "number"], [PR.repository, PR.number]),
        ForeignKeyConstraint(["ga", "version"], [Link.ga, Link.version]),
    )

    repository = Column(String, primary_key=True)
    number = Column(Integer, primary_key=True)
    ga = Column(String, primary_key=True)
    version = Column(String, primary_key=True)


def pr_exists(repository: str, number: int, session: Session) -> bool:
    return session.query(PR).where(PR.repository == repository, PR.number == number).scalar()


def add_pr(repository: str, pr: PullRequest, session: Session):
    if not pr_exists(repository, pr.number, session):
        ga, v_old, v_new = extract_update_info_from_pr(pr)
        eligible = True if ga and v_old and v_new else False
        update_type = get_bump_update_type(v_old, v_new)
        row = PR(repository=repository, number=pr.number, eligible=eligible, ga=ga, v_old=v_old, v_new=v_new,
                 update_type=update_type)
        session.add(row)
        session.commit()


def get_prs(session: Session):
    return session.query(PR).all()


def get_prs_by_statically_compatible(statically_compatible: bool, session: Session):
    statically_compatible = sqlalchemy.true() if statically_compatible else sqlalchemy.false()
    return session.query(PR).where(PR.statically_compatible == statically_compatible).all()


def get_prs_by_eligible(eligible: bool, session: Session):
    eligible = sqlalchemy.true() if eligible else sqlalchemy.false()
    return session.query(PR).where(PR.eligible == eligible).all()


def get_prs_by_eligible_query(eligible: bool, session: Session):
    eligible = sqlalchemy.true() if eligible else sqlalchemy.false()
    return session.query(PR).where(PR.eligible == eligible)


def get_prs_by_update_type(update_type: str, session: Session):
    return session.query(PR).where(PR.update_type == update_type).all()


def extract_update_info_from_pr(pr: PullRequest) -> (str, str, str):
    """Extracts the groupId, artifactId, old version, and new version from the given pull request's title, assuming
    that the PR title follows the following pattern:  xyzetc bump <group_id>:<artifact_id> from <v_new> to <v_old>."""
    print(pr.title)
    pattern = r".*?bump\s+(.*?)\s+from\s+(.*?)\s+to\s+(.*?)$"

    match = re.match(pattern, pr.title, re.IGNORECASE)

    if match:
        ga, v_old, v_new = match.groups()
        ga, v_old, v_new = ga.strip(), v_old.strip(), v_new.strip()
    else:
        ga, v_old, v_new = "", "", ""

    ga = ga if ":" in ga else ""
    v_new = v_new if " in " not in v_new else v_new.split(" in ")[0]

    print(f"\nThe update of '{pr.title}' is {ga}:{v_old}->{v_new}")

    return ga, v_old, v_new


def get_update_type(old: str, new: str) -> str:
    """Given two version strings, returns whether the update is major, minor, patch, or other."""
    # TODO: may be best to just use the same method that BUMP uses for consistency?
    parts_old = old.split(".")
    parts_new = new.split(".")

    while len(parts_old) < 3:
        parts_old.append("0")
    while len(parts_new) < 3:
        parts_new.append("0")

    if parts_old[0] != parts_new[0]:
        return "major"
    if parts_old[1] != parts_new[1]:
        return "minor"
    if parts_old[2] != parts_new[2]:
        return "patch"
    return "other"


def update_rows_with_update_info(github_session: Github, db_session: Session):
    """For all rows in PRs, extract the ga, v_old, v_new."""
    prs = get_prs(db_session)
    for pr in prs:
        repo = github_session.get_repo(pr.repository)
        p = repo.get_pull(pr.number)
        ga, v_old, v_new = extract_update_info_from_pr(p)
        pr.ga = ga
        pr.v_old = v_old
        pr.v_new = v_new
        db_session.commit()


def update_rows_with_version_types(db_session: Session, use_bump=False):
    prs = get_prs(db_session)
    total = len(prs)
    count = 0
    for pr in prs:
        count += 1
        if use_bump:
            update_type = get_bump_update_type(pr.v_old, pr.v_new)
        else:
            update_type = get_update_type(pr.v_old, pr.v_new)
        pr.update_type = update_type
        db_session.commit()
        print(f"PROGRESS {count}/{total} ({int(count/total*100)}%)")


def get_bump_semver_version(string: str) -> str:
    """
    Returns full semver if there is semver match (with or without patch), otherwise returns empty string.
    The patterns are based on the ones used by the BUMP benchmark to keep the datapoints comparable:
    https://github.com/chains-project/bump/blob/f0a2c231fbad0863c4e8b5a3009dbb18c08be1b0/src/main/java/miner/BreakingUpdate.java#L37
    """
    pattern = r'^\d+\.\d+\.\d+$'
    match = re.search(pattern, string)
    if match:
        return match.group()
    return ""


def get_bump_update_type(old: str, new: str) -> str:
    """
    Given two version strings, returns whether the update is major, minor, patch, or other according to the
    same methodology used by the BUMP benchmark:
    https://github.com/chains-project/bump/blob/f0a2c231fbad0863c4e8b5a3009dbb18c08be1b0/src/main/java/miner/BreakingUpdate.java#L244
    """
    semver_old = get_bump_semver_version(old)
    semver_new = get_bump_semver_version(new)
    if not semver_old or semver_new:
        return "other"

    parts_old = old.split(".")
    parts_new = new.split(".")

    if parts_old[0] != parts_new[0]:
        return "major"
    if parts_old[1] != parts_new[1]:
        return "minor"

    return "patch"


def add_link(pr: PR, version: str, link, session: Session, err=None):
    """Adds a link to the db."""
    # Commenting this out since I think it's the reason why the pr.links relationship does not return the same
    # amount of links as when querying the Links table directly.
    # exists = session.query(Links).where(Links.ga == pr.ga, Links.version == version).scalar()
    # if not exists:
    #     return

    if link[0] is None:
        err = "NO_GITHUB" if not err else err
    if link[1] is None:
        err = "NO_TAG" if not err else err

    tag_name = None if link[1] is None else link[1].name
    tag_commit = None if link[1] is None else link[1].commit
    repository = None if link[0] is None else link[0].full_name

    link = Link(ga=pr.ga, version=version, repository=repository, tag_name=tag_name, tag_commit=tag_commit, err=err)
    pr_link = PRLink(repository=pr.repository, number=pr.number, ga=link.ga, version=link.version)

    session.merge(link)
    session.merge(pr_link)
    session.commit()
