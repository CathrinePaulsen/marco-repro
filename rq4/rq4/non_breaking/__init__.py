"""Module responsible for collecting datapoints for the non-breaking changes dataset, and evaluating 'The Tool' on it"""
import argparse
import time
from datetime import datetime, timezone
import pandas as pd

from github import PullRequest, RateLimitExceededException
from sqlalchemy.orm import Session
from pathlib import Path

import rq4.non_breaking.print_logic as p
from core import (get_github_session, get_github_repo_and_tag, PomNotFoundException)
from models import engine
from models.link import get_link, link_exists
from models.pr import (add_pr, get_prs_by_eligible, get_prs_by_statically_compatible,
                       update_rows_with_version_types, add_link)
from models.project import add_project, get_projects_by_dependabot, project_exists
from rq4.non_breaking import utils
from rq6.utils import Result, get_static_result, get_dynamic_result
from server.dynamic import dynamically_compatible
from server.exceptions import MavenNoPomInDirectoryException
from server.template.base_template import BaseTemplate
from server.template.candidate_template import CandidateTemplate

NO_MAVEN = -4
NO_TEST = -3
NO_COMPILE = -2
NO_JAR = -1
COMPATIBLE = 1
INCOMPATIBLE = 0


# Source https://github.com/PyGithub/PyGithub/issues/553
def rate_limited_retry(github):
    def decorator(func):
        def ret(*args, **kwargs):
            for _ in range(3):
                try:
                    return func(*args, **kwargs)
                except RateLimitExceededException:
                    limits = github.get_rate_limit()
                    reset = limits.search.reset.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    seconds = (reset - now).total_seconds()
                    print(f"Rate limit exceeded")
                    print(f"Reset is in {seconds:.3g} seconds.")
                    if seconds > 0.0:
                        print(f"Waiting for {seconds:.3g} seconds...")
                        time.sleep(seconds)
                        print("Done waiting - resume!")
            raise Exception("Failed too many times")
        return ret
    return decorator


def get_query_search_repositories(start_date: str, end_date: str) -> str:
    return f"created:{start_date}..{end_date} language:java stars:>=10"


def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{:02d}:{:02d}:{:02d}".format(int(hours), int(minutes), int(seconds))


def collect_projects():
    """
    Collect GitHub projects we can possibly use to extract update datapoints from their PRs.
    Filters:
        1. recent java (created between Apr 9 2024 and Jan 1 2023)
        2. >= 20 stars
        3. has dependabot updates enabled for maven dependencies
    """
    total_start_time = time.time()
    with Session(engine) as db_session:
        with get_github_session() as github:
            # https://api.github.com/search/repositories?q=created:%3E2021-01-01+language:java+stars:%3E=10
            # Github only returns at most 1000 results to any query, so we need the query up
            queries = [get_query_search_repositories("2023-12-01", "2024-05-01"),   # 871
                       get_query_search_repositories("2023-09-01", "2023-12-01"),   # 785
                       get_query_search_repositories("2023-07-01", "2023-09-01"),   # 733
                       get_query_search_repositories("2023-05-01", "2023-07-01"),   # 786
                       get_query_search_repositories("2023-03-01", "2023-05-01"),   # 865
                       get_query_search_repositories("2023-01-01", "2023-03-01"),   # 898
                       ]
            for idx, query in enumerate(queries):
                start_time = time.time()
                print(f"Running query {idx+1}/{len(queries)}: {query}")
                repos = github.search_repositories(query=query)
                count = 0
                for repo in repos:
                    end_time = time.time()
                    print(f"Elapsed time for query: {format_time(end_time - start_time)} "
                          f"(total: {format_time(end_time - total_start_time)}")
                    limits = github.get_rate_limit()
                    if limits.search.remaining <= 2:
                        print(f"Remaining limit: search={limits.search.remaining}, core={limits.core.remaining}")
                        seconds = (limits.search.reset - datetime.now()).total_seconds()
                        print("Waiting for %d seconds ..." % seconds)
                        time.sleep(seconds)
                        print("Done waiting - resume!")
                    if limits.core.remaining <= 2:
                        print(f"Remaining limit: search={limits.search.remaining}, core={limits.core.remaining}")
                        seconds = (limits.core.reset - datetime.now()).total_seconds()
                        print("Waiting for %d seconds ..." % seconds)
                        time.sleep(seconds)
                        print("Done waiting - resume!")
                    count += 1
                    p.print_progress(count, repos.totalCount)
                    if repo.get_commits().totalCount >= 50:  # Skip projects with less than 50 commits
                        if not project_exists(repo.full_name, db_session):
                            print(f"Found new project {repo.full_name}, adding to db")
                            add_project(repo.full_name, utils.repo_has_maven_dependabot(repo), db_session)

    p.print_stats_total_projects()


def update_pr_version_types(use_bump=False):
    with Session(engine) as session:
        update_rows_with_version_types(session, use_bump=use_bump)
    p.print_stats_prs()


def collect_prs():
    """
    Collect PRs from GitHub projects we can possibly use to extract update datapoints from.
    Filters:
        1. PR changes pom file, is merged, is made by dependabot, and has one commit
        2. [PINNED] The change is in <dependency> or <dependencyManagement> section
        3. Can easily extract GA and versions from PR title
    """
    with Session(engine) as db:
        with get_github_session() as github:
            projects = get_projects_by_dependabot(True, db)
            total_projects = len(projects)
            print(f"Evaluating {total_projects} projects")
            count_projects = 0
            for project in projects:
                repo = github.get_repo(project.repository)
                for pr in utils.get_dependabot_prs_of_repo(repo, github):
                    add_pr(repo.full_name, pr, db)
                count_projects += 1
                p.print_progress(count_projects, total_projects, info="Project")

    p.print_stats_prs()


def evaluate_static_compatibility(override=False):
    """
    Evaluates static compatibility for all eligible PRs.
    Updates the eligible rows with the static compatibility result.
    """
    with Session(engine) as session:
        prs = get_prs_by_eligible(True, session)
        n_to_process = len(prs)
        n_processed = 0
        for pr in prs:
            if override or pr.statically_compatible is None:
                g, a, = pr.ga.split(":")
                static_result = get_static_result(g, a, pr.v_old, pr.v_new)
                if static_result == Result.NO_JAR:
                    pr.statically_compatible = False
                    pr.err = Result.NO_JAR
                else:
                    pr.statically_compatible = False if static_result == Result.STATICALLY_INCOMPATIBLE else True
                    pr.err = None if pr.err == "no_jar" or pr.err == "NO_JAR" else pr.err
                session.commit()
            n_processed += 1
            p.print_progress(n_processed, n_to_process, info="Static")
    p.print_stats_static()


# def get_static_result(ga: str, v_base: str, v_cand: str) -> Result:
#     """
#     Returns the result of the static compatibility check. The return options are:
#          0: the v_base and v_cand are statically incompatible.
#          1: the v_base and v_cand are statically compatible.
#         -1: static compatibility could not be determined because the jars could not be fetched from Maven Central.
#     """
#     print(f"\nEvaluating static compatibility on {ga} between base {v_base} and candidate {v_cand}")
#     g, a = ga.split(":")
#     try:
#         compatible = statically_compatible(g, a, v_base, v_cand)
#         compatibility_result = Result.STATICALLY_COMPATIBLE if compatible else Result.STATICALLY_INCOMPATIBLE
#     except (BaseJarNotFoundException, CandidateJarNotFoundException) as e:
#         print(e)
#         print(f"Found no jar for base or candidate.")
#         compatibility_result = Result.NO_JAR
#
#     return compatibility_result


def evaluate_dynamic_compatibility(override=False):
    """
    Evaluates dynamic compatibility for PRs that are statically compatible and we know their GitHub links.
    Updates the eligible rows with the dynamic compatibility result.
    """
    START_FROM = 533
    with Session(engine) as session:
        prs = []
        for pr in get_prs_by_statically_compatible(True, session):
            link_old = get_link(pr.ga, pr.v_old, session)
            link_new = get_link(pr.ga, pr.v_new, session)
            if link_old and link_new:
                if not link_old.err and not link_new.err:
                    prs.append(pr)
                elif link_old.err:
                    print(f"updating pr.err={link_old.err}")
                    pr.err = link_old.err
                elif link_new.err:
                    print(f"updating pr.err={link_new.err}")
                    pr.err = link_new.err
                session.commit()
            # link_old, link_new = sort_links(pr)
            # if link_old and link_new:
            #     if not link_old.err and not link_new.err:
            #         prs.append(pr)
        input("finished updating errors")
        n_to_process = len(prs)
        n_processed = 0
        updates = set()
        for pr in prs:
            update = f"{pr.ga}:{pr.v_old}->{pr.v_new}"
            updates.add(update)

        input(f"I found {n_to_process} PRs, {len(updates)} unique updates")
        for pr in prs:
            n_processed += 1
            if n_processed <= START_FROM:
                print(f"Skipping {n_processed}")
                continue
            if not override:
                if pr.dynamically_compatible is not None:
                    continue
            link_old = get_link(pr.ga, pr.v_old, session)
            link_new = get_link(pr.ga, pr.v_new, session)
            g, a = pr.ga.split(":")
            dynamic_result = get_dynamic_result(g, a, pr.v_old, pr.v_new)
            if dynamic_result == Result.COMPATIBLE:
                pr.dynamically_compatible = True
                pr.err = None
            elif dynamic_result == Result.DYNAMICALLY_INCOMPATIBLE:
                pr.dynamically_compatible = False
            elif dynamic_result == Result.NO_MAVEN:
                pr.dynamically_compatible = False
                pr.err = Result.NO_MAVEN
            elif dynamic_result == Result.NO_TEST:
                pr.dynamically_compatible = False
                pr.err = Result.NO_TEST
            elif dynamic_result == Result.NO_COMPILE:
                pr.dynamically_compatible = False
                pr.err = Result.NO_COMPILE
            elif dynamic_result == Result.NO_RESOLVE:
                pr.dynamically_compatible = False
                pr.err = Result.NO_RESOLVE
            elif dynamic_result == Result.NO_GITHUB_TAG:
                pr.dynamically_compatible = False
                pr.err = Result.NO_GITHUB_TAG
            elif dynamic_result == Result.NO_GITHUB_LINK:
                pr.dynamically_compatible = False
                pr.err = Result.NO_GITHUB_LINK
            session.commit()

            p.print_progress(n_processed, n_to_process, info="Dynamic")

    p.print_stats_dynamic()


def get_dynamic_result2(ga: str, v_base: str, v_cand: str, link_old, link_new) -> int:
    """
    Returns the result of the dynamic compatibility check. The return options are:
         0: the v_base and v_cand are dynamically incompatible.
         1: the v_base and v_cand are dynamically compatible.
        -2: dynamic compatibility check could not be run because the repository did not compile.
        -3: dynamic compatibility check could not be run because there were no tests.
        -4: dynamic compatibility check could not be run because the pom file was not found in the repository.
    """
    print(f"\nEvaluating dynamic compatibility on {ga} between base {v_base} and candidate {v_cand} using:")
    print(f"     repo: {link_old.repository}, tag_old: {link_old.tag_name}, tag_new: {link_new.tag_name}")
    g, a = ga.split(":")

    # Prepare templates
    try:
        print(f"Creating base template for {g}:{a}:{v_base}")
        base_template = BaseTemplate(g, a, v_base, repo_name=link_old.repository, tag_name=link_old.tag_name, commit_sha=link_old.tag_commit)
    except MavenNoPomInDirectoryException as e:
        print(e)
        # input("????????????")
        return NO_MAVEN
    except Exception as e:
        print(e)
        c_or_t = input("-- EXCEPTION while generating base template. Compile error (c), no tests (t)? ")
        if c_or_t == "c":
            print("Adding datapoint to no compile dataset")
            return NO_COMPILE
        if c_or_t == "t":
            print("Adding datapoint to no test dataset")
            return NO_TEST
        else:
            print("Aborting.")
            exit(0)

    try:
        print(f"Creating candidate template for {g}:{a}:{v_cand}")
        cand_template = CandidateTemplate(g, a, v_cand, repo_name=link_new.repository, tag_name=link_new.tag_name, commit_sha=link_new.tag_commit)
    except Exception as e:
        print(e)
        c_or_t = input("-- EXCEPTION while generating candidate template. Compile error (c) or no maven (m)? ")
        if c_or_t == "c":
            print("Adding datapoint to no compile dataset")
            return NO_COMPILE
        if c_or_t == "m":
            print("Adding datapoint to no maven dataset")
            return NO_MAVEN
        else:
            print("Aborting.")
            exit(0)

    print(f"Running dynamic check on base {g}:{a}:{v_base} ,   candidate v {v_cand}")
    return COMPATIBLE if dynamically_compatible(base_template, v_cand) else INCOMPATIBLE


def collect_links(override=False, statically_compatible_only=True):
    """Collects the links of each statically compatible PR, and stores them in the db."""
    with Session(engine) as session:
        if statically_compatible_only:
            prs = get_prs_by_statically_compatible(True, session)
        else:
            prs = get_prs_by_eligible(True, session)
        n_to_process = len(prs)
        n_processed = 0

        for pr in prs:
            collect_link(pr, pr.v_old, session, override=override)
            collect_link(pr, pr.v_new, session, override=override)
            n_processed += 1
            p.print_progress(n_processed, n_to_process, info="Link")

    p.print_stats_links()


def collect_link(pr: PullRequest, v: str, session: Session, override=False):
    """Collect and store the link for a specific GAV."""
    assert v == pr.v_old or v == pr.v_new
    if not override:
        if link_exists(pr.ga, v, session):
            return

    g, a = pr.ga.split(":")
    try:
        link = get_github_repo_and_tag(g, a, str(v))
        add_link(pr, v, link, session)
    except PomNotFoundException as e:
        print(e)
        add_link(pr, v, (None, None), session, err="NO_POM")


def sort_links(pr):
    """Sorts the links of the PR so that it returns a tuple of (old_link, new_link)."""
    if len(pr.links) == 2:
        if pr.links[0].version == pr.v_old:
            link_old = pr.links[0]
            link_new = pr.links[1]
        else:
            link_old = pr.links[1]
            link_new = pr.links[0]
        return link_old, link_new
    return None, None


def generate_csv():
    WRITE_TO = Path(__file__).parent.resolve() / "rq4_non_breaking_results.csv"
    rows = []
    with Session(engine) as session:
        prs = get_prs_by_eligible(True, session)
        count = 0
        total = len(prs)
        for pr in prs:
            count += 1
            print(f"PROGRESS {count}/{total} ({int(count/total*100)}%)")
            row = {
                'repository': pr.repository,
                'pr': pr.number,
                'ga': pr.ga,
                'v_old': pr.v_old,
                'v_new': pr.v_new,
                'update_type': pr.update_type,
                'statically_compatible': pr.statically_compatible,
                'dynamically_compatible': pr.dynamically_compatible,
                'err': pr.err
            }
            rows.append(row)
    print("Converting list to df...")
    df = pd.DataFrame(rows)
    print(f"Writing df to {WRITE_TO}...")
    df.to_csv(WRITE_TO, index=False)


def update_link_errors():
    with Session(engine) as session:
        prs = get_prs_by_statically_compatible(True, session)
        count = 0
        total = len(prs)
        for pr in prs:
            count += 1
            print(f"PROGRESS {count}/{total} ({int(count/total*100)}%)")
            old_link = get_link(pr.ga, pr.v_old, session)
            new_link = get_link(pr.ga, pr.v_old, session)
            assert old_link is not None and new_link is not None
            if old_link.err is not None:
                print(f"Setting pr.err=old_link.err={old_link.err}")
                pr.err = old_link.err
            elif new_link.err is not None:
                print(f"Setting pr.err=new_link.err={new_link.err}")
                pr.err = new_link.err
            session.commit()




def confirm(step: str):
    input(f"[NON-BREAKING DATASET] Running data collection step {step}. Press any key to begin.")


def main():
    parser = argparse.ArgumentParser(description='Script that collects the datapoints for the non-breaking dataset '
                                                 'used to evaluate RQ4.')
    parser.add_argument('-s', '--step', choices=['projects', 'prs', 'static', 'links', 'dynamic',
                                                 'update_pr_version_types', 'generate_csv', 'update_link_errors'],
                        help='Specify which collection step in the data collection pipeline you would like to run. '
                             'Options (in logical order): projects, prs, static, links, dynamic.', required=True)
    parser.add_argument('--stats_only', action='store_true',
                        help='Enable stats-only mode, use this if you only want to print the statistics associated '
                             'with a particular collection step.')
    parser.add_argument('--override', action='store_true',
                        help='Enable override, use this if you only want re-run a collection step and override/delete '
                             'previous results.')

    args = parser.parse_args()
    collection_step = args.step
    stats_only = args.stats_only
    override = args.override

    if collection_step == 'projects':
        if stats_only:
            p.print_stats_total_projects()
        else:
            confirm(collection_step)
            collect_projects()

    elif collection_step == 'prs':
        if stats_only:
            p.print_stats_prs()
        else:
            confirm(collection_step)
            collect_prs()

    elif collection_step == 'links':
        if stats_only:
            p.print_stats_links()
        else:
            confirm(collection_step)
            collect_links(override=override)

    elif collection_step == 'static':
        if stats_only:
            p.print_stats_static()
        else:
            confirm(collection_step)
            evaluate_static_compatibility(override=override)

    elif collection_step == 'dynamic':
        if stats_only:
            p.print_stats_dynamic()
        else:
            confirm(collection_step)
            evaluate_dynamic_compatibility(override=override)

    elif collection_step == 'update_pr_version_types':
        if stats_only:
            p.print_stats_prs()
        else:
            confirm(collection_step)
            update_pr_version_types()
    elif collection_step == 'generate_csv':
        confirm(collection_step)
        generate_csv()
    elif collection_step == 'update_link_errors':
        confirm(collection_step)
        update_link_errors()
