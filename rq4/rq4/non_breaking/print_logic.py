"""Module responsible for all custom print logic."""
import sqlalchemy
from sqlalchemy.orm import Session, Query

from models import engine
from models.link import get_link
from models.pr import PR, get_prs_by_eligible_query, get_prs_by_statically_compatible
from models.project import get_projects_by_dependabot
from rq6.utils import Result


def print_progress(n_processed: int, n_to_process: int, info=""):
    print(f"=> {info} PROGRESS: processed {n_processed}/{n_to_process} ({int(n_processed / n_to_process * 100)}%)")


def print_type_distribution(dist: dict):
    print(f"    Update types: major={dist['major']}, minor={dist['minor']}, patch={dist['patch']}, other={dist['other']}\n")


def print_stats_info(info: str, dist: dict):
    print(f"{info}: {dist['total']}")
    print_type_distribution(dist)


def print_stats_total_projects():
    with Session(engine) as session:
        n_total_projects = len(get_projects_by_dependabot(True, session))
    print(f"Total projects: {n_total_projects}")


def get_update_distribution(query: Query):
    distribution = {'total': len(query.all())}
    for update_type in ['major', 'minor', 'patch', 'other']:
        distribution[update_type] = len(query.where(PR.update_type == update_type).all())
    return distribution


def print_stats_prs():
    with Session(engine) as session:
        prs = get_update_distribution(session.query(PR))
        eligible_prs = get_update_distribution(get_prs_by_eligible_query(True, session))
    print_stats_info("Total PRs evaluated", prs)
    print_stats_info("Total eligible PRs", eligible_prs)


def print_stats_static():
    with Session(engine) as session:
        static_pass = get_update_distribution(session.query(PR).where(PR.statically_compatible == sqlalchemy.true()))
        static_fail = get_update_distribution(session.query(PR).where(PR.statically_compatible == sqlalchemy.false(), PR.err == sqlalchemy.null()))
        no_jar = get_update_distribution(session.query(PR).where(PR.err == Result.NO_JAR))

    print_stats_info("Static pass", static_pass)
    print_stats_info("Static fail", static_fail)
    print_stats_info("Static inconclusive due to NO_JAR", no_jar)


def print_stats_dynamic():
    with Session(engine) as session:
        passing = get_update_distribution(session.query(PR).where(PR.dynamically_compatible == sqlalchemy.true()))
        failing = get_update_distribution(session.query(PR).where(PR.dynamically_compatible == sqlalchemy.false(), PR.err == sqlalchemy.null()))
        no_maven = get_update_distribution(session.query(PR).where(PR.err == Result.NO_MAVEN))
        no_compile = get_update_distribution(session.query(PR).where(PR.err == Result.NO_COMPILE))
        no_test = get_update_distribution(session.query(PR).where(PR.err == Result.NO_TEST))
        no_resolve = get_update_distribution(session.query(PR).where(PR.err == Result.NO_RESOLVE))

    print_stats_info("Dynamic pass", passing)
    print_stats_info("Dynamic fail", failing)
    print_stats_info("Dynamic inconclusive due to NO_MAVEN", no_maven)
    print_stats_info("Dynamic inconclusive due to NO_COMPILE", no_compile)
    print_stats_info("Dynamic inconclusive due to NO_TEST", no_test)
    print_stats_info("Dynamic inconclusive due to NO_RESOLVE", no_resolve)


def print_stats_links():
    with Session(engine) as session:
        n_link_success = 0
        n_success_major, n_success_minor, n_success_patch = (0, 0, 0)
        n_link_no_github = 0
        n_github_major, n_github_minor, n_github_patch = (0, 0, 0)
        n_link_no_tag = 0
        n_tag_major, n_tag_minor, n_tag_patch = (0, 0, 0)

        for pr in get_prs_by_statically_compatible(True, session):
            row_old = get_link(pr.ga, pr.v_old, session)
            row_new = get_link(pr.ga, pr.v_new, session)
            if not row_old.err and not row_new.err:
                n_link_success += 1
                n_success_major = n_success_major + 1 if pr.update_type == "major" else n_success_major
                n_success_minor = n_success_minor + 1 if pr.update_type == "minor" else n_success_minor
                n_success_patch = n_success_patch + 1 if pr.update_type == "patch" else n_success_patch

            elif row_old.err == Result.NO_GITHUB_LINK and row_new.err == Result.NO_GITHUB_LINK:
                n_link_no_github += 1
                n_github_major = n_github_major + 1 if pr.update_type == "major" else n_github_major
                n_github_minor = n_github_minor + 1 if pr.update_type == "minor" else n_github_minor
                n_github_patch = n_github_patch + 1 if pr.update_type == "patch" else n_github_patch

            elif row_old.err == Result.NO_GITHUB_TAG and row_new.err == Result.NO_GITHUB_TAG:
                n_link_no_tag += 1
                n_tag_major = n_tag_major + 1 if pr.update_type == "major" else n_tag_major
                n_tag_minor = n_tag_minor + 1 if pr.update_type == "minor" else n_tag_minor
                n_tag_patch = n_tag_patch + 1 if pr.update_type == "patch" else n_tag_patch

    print(f"link success: {n_link_success}")
    print(f"    Update types: major={n_success_major}, minor={n_success_minor}, patch={n_success_patch}")
    print(f"\nlink NO_GITHUB_LINK: {n_link_no_github}")
    print(f"    Update types: major={n_github_major}, minor={n_github_minor}, patch={n_github_patch}")
    print(f"\nlink NO_GITHUB_TAG: {n_link_no_tag}")
    print(f"    Update types: major={n_tag_major}, minor={n_tag_minor}, patch={n_tag_patch}")