import argparse
import glob
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from pprint import pprint

import pandas as pd
from lxml import etree as ET
from sqlalchemy.orm import Session
import sqlalchemy

import core.dependency_tree as dt
from client import expand_and_replace
from core import get_github_session
from core.dependency_tree import TreeComparator
from rq4.non_breaking import get_query_search_repositories, format_time
from rq4.non_breaking.print_logic import print_progress
from rq4.non_breaking.utils import repo_has_pom, get_file
from rq5 import utils
from rq5.models import engine, set_up_db
from rq5.models.compatibility import add_compatibility, get_compatibilities_of_base
from rq5.models.dependency import (add_dependency, get_dependencies, update_dependency_err,
                                   update_dependency_evaluated_with_date, get_dependencies_that_are_processed)
from rq5.models.project import add_project, project_exists, get_projects_that_compile_and_has_tests
from server import find_compatibility_results
from server import repo_utils, save_compatibility_store
from server.config import download_repo_by_name, path_to_repos, COMPATIBILITY_STORE
from server.exceptions import (MavenSurefireTestFailedException, MavenNoPomInDirectoryException,
                               GithubRepoNotFoundException, BaseMavenTestTimeout, BaseMavenCompileTimeout,
                               GithubTagNotFoundException, MavenResolutionFailedException, MavenCompileFailedException)
from core import MavenMetadataNotFound

LOCAL_M2 = Path("/home/cathrine/.m2/repository")


def create_dep_tree(repo_name: str, save_log_as: str, save_tree_as: str, pom_file=None) -> bool:
    print(f"Creating dep tree for {repo_name}, save log as {save_log_as}, save tree as {save_tree_as}")
    old_dir = os.getcwd()
    repo_path = path_to_repos / repo_name
    read_from_commands = ["-f", repo_path / pom_file] if pom_file else []
    save_log_as_commands = ["-l", repo_path / save_log_as]
    os.chdir(repo_path)
    commands = (["mvn", "dependency:tree"] + read_from_commands +
                ["-Dverbose", "-Dscope=runtime", "-DincludeTypes=jar", f"-DoutputFile={save_tree_as}"] + save_log_as_commands)
    subprocess.run(commands)
    assert Path.is_file(repo_path / save_log_as)
    with open(repo_path / save_log_as, 'r') as f:
        resolves = False if "Could not resolve dependencies" in f.read() else True
    os.chdir(old_dir)
    return resolves


def extract_library_jars(recompute=False, path_to_libraries=LOCAL_M2):
    with Session(engine) as db:
        libraries = get_dependencies(db)
        count = 0
        total = len(libraries)
        for library in libraries:
            path_to_library = (path_to_libraries / library.group_id.replace(".", "/")
                               / library.artifact_id / library.version)
            path_to_classes = path_to_library / 'target' / 'classes'

            if recompute:
                shutil.rmtree(path_to_classes)
            if Path.is_dir(path_to_classes) and not recompute:
                count += 1
                print(f"== PROGRESS {int(count/total*100)}% ({count}/{total}) - {path_to_library}")
                continue

            path_to_jar = path_to_library / f"{library.artifact_id}-{library.version}.jar"
            print(f"Extracting jar {path_to_jar}")

            if not Path.is_file(path_to_jar):
                print(f"Did not find jar with name {path_to_jar.name}")
                try:
                    path_to_jar = Path(glob.glob(f"{path_to_library}/*.jar")[0])
                    print(f"Using jar file {path_to_jar.name}")
                except IndexError:
                    endpoint = f"https://repo1.maven.org/maven2/{library.group_id.replace('.','/')}/{library.artifact_id}/{library.version}/{library.artifact_id}-{library.version}.jar"
                    print(f"endpoint={endpoint}")
                    out = subprocess.run(["curl", "-f", "-o", path_to_jar, endpoint])
                    if out.returncode != 0:
                        print(f"Couldn't find jar for {path_to_library}")
                        out = subprocess.run(["touch", f"{path_to_library / '.no_jar'}"])
                        out.check_returncode()
                        count += 1
                        print(f"== PROGRESS {int(count/total*100)}% ({count}/{total}) - {path_to_library}")
                        continue
                    assert Path.is_file(path_to_jar)

            out = subprocess.run(["mkdir", "-p", path_to_classes])
            out.check_returncode()

            assert Path.is_dir(path_to_classes)
            out = subprocess.run(["unzip", path_to_jar, "-d", path_to_classes], stdout=subprocess.DEVNULL)
            out.check_returncode()

            count += 1
            print(f"== PROGRESS {int(count/total*100)}% ({count}/{total}) - {path_to_library}")


def expand_library_poms(recompute=False, pass_2= False, path_to_libraries=LOCAL_M2):
    start_time = time.time()
    with Session(engine) as db:
        libraries = get_dependencies(db)
        stats = {}
        count = 0
        total = len(libraries)

        for library in libraries:
            path_to_library = (path_to_libraries / library.group_id.replace(".", "/")
                               / library.artifact_id / library.version)
            path_to_pom = path_to_library / f"{library.artifact_id}-{library.version}.pom"
            if not Path.is_file(path_to_pom):
                print(f"\n== Could not expand POM of {path_to_library}, does not exist")
                continue
            print(f"\n== Expanding POM of {path_to_library}")
            path_to_backup_pom = path_to_library / f"original_{library.artifact_id}-{library.version}.pom"
            if Path.is_file(path_to_backup_pom) and not pass_2:
                if recompute:
                    # Restore original pom
                    shutil.copy(path_to_backup_pom, path_to_pom)
                else:
                    count += 1
                    end_time = time.time()
                    print(f"== PROGRESS {int(count/total*100)}% ({count}/{total}) -- Elapsed time {format_time(end_time - start_time)}")
                    continue  # To avoid re-replacing projects we've already done
            if not pass_2:
                utils.backup_pom(path_to_pom, path_to_backup_pom)
            expansions, replacements = expand_and_replace(path_to_library, pom_path=path_to_pom)
            stats[path_to_library] = {'expansions': expansions, 'replacements': replacements}
            print(f"Made {expansions} expansions and {replacements} replacements to {path_to_library}")
            if expansions > 0 or replacements > 0:
                # input("Press any key to continue.")
                pass
            count += 1
            end_time = time.time()
            print(f"== PROGRESS {int(count/total*100)}% ({count}/{total}) -- Elapsed time {format_time(end_time - start_time)}")
        pprint(stats)


def expand_project_poms(recompute=False):
    start_time = time.time()
    with Session(engine) as db:
        projects = get_projects_that_compile_and_has_tests(db)
        stats = {}
        count = 0
        total = len(projects)
        for project in projects:
            print(f"\n== Expanding POM of {project.repository}")
            project_path = path_to_repos / project.repository
            if not project.sha.strip() == repo_utils.get_sha_of_repo_head(project_path).strip():
                utils.checkout_sha(project)
            if Path.is_file(project_path / "original_pom.xml"):
                if recompute:
                    # Restore original pom
                    shutil.copy(project_path / "original_pom.xml", project_path / "pom.xml")
                else:
                    count += 1
                    end_time = time.time()
                    print(f"== PROGRESS {int(count/total*100)}% ({count}/{total}) -- Elapsed time {format_time(end_time - start_time)}")
                    continue  # To avoid re-replacing projects we've already done
            # Create backup of original pom in case we need it
            utils.backup_pom(project_path / "pom.xml", project_path / "original_pom.xml")
            expansions, replacements = expand_and_replace(path_to_repos / project.repository)
            stats[project.repository] = {'expansions': expansions, 'replacements': replacements}
            # repo_utils.compile_repo(path_to_repos / project.repository)  # Whut
            print(f"Made {expansions} expansions and {replacements} replacements to {project.repository}")
            # if expansions > 0 or replacements > 0:
            #     input("Press any key to continue.")
            count += 1
            end_time = time.time()
            print(f"== PROGRESS {int(count/total*100)}% ({count}/{total}) -- Elapsed time {format_time(end_time - start_time)}")
        pprint(stats)


def generate_compatibility_store():
    start_time = time.time()
    with Session(engine) as db:
        dependencies = get_dependencies_that_are_processed(db)
        total = len(dependencies)
        count = 0
        compatibility_dict = {}
        df = pd.DataFrame(columns=['gav', 'compatibilities'])
        for dependency in dependencies:
            count += 1
            end_time = time.time()
            print(f"PROGRESS {count}/{total} ({int(count/total*100)}%) -- Elapsed time {format_time(end_time - start_time)}")
            gav = f"{dependency.group_id}:{dependency.artifact_id}:{dependency.version}"
            compatibilities = [dependency.version]
            compatibilities += [x.v_cand for x in get_compatibilities_of_base(dependency.group_id,
                                                                              dependency.artifact_id,
                                                                              dependency.version, db)]
            compatibility_dict[gav] = set(compatibilities)
            row = {'gav': gav, 'compatibilities': len(compatibilities)}
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        pprint(compatibility_dict)
        print(f"Saving compatibility store to json: {COMPATIBILITY_STORE}")
        save_compatibility_store(compatibility_dict)
        print(f"Saving compatibility info to csv: rq5_compatibilities.csv")
        df.to_csv('rq5_compatibilities.csv', index=False)
        print(f"Done")


def collect_compatibilities():
    skip_on_err = ["TEST_TIMEOUT", "COMPILE_TIMEOUT", "NO_RESOLVE", "NO_COMPILE", "NO_TEST", "NO_POM", "NO_GITHUB",
                   "NO_TAG"]
    with Session(engine) as db:
        dependencies = get_dependencies(db)
        num_dep = len(dependencies)
        count = 0
        for dependency in dependencies:
            # Skipping dependencies for which we know already evaluated/errored
            # if dependency.err in skip_on_err or dependency.evaluated is not None:
            if dependency.err is not None or dependency.evaluated is not None:
                count += 1
                print("")
                print(utils.bcolors.OKCYAN +
                      f"PROGRESS {int((count / num_dep) * 100)}% ({count}/{num_dep})"
                      + utils.bcolors.ENDC)
                continue
            if not dependency.is_new:
                print(f"something illegal happened: {dependency.group_id}:{dependency.artifact_id}:{dependency.version}")
            assert dependency.is_new  # Remove if recomputing
            try:
                compatibility_results = find_compatibility_results(dependency.group_id, dependency.artifact_id,
                                                                   dependency.version)
                for result in compatibility_results:
                    add_compatibility(result.group_id, result.artifact_id, result.v_base, result.v_cand, db,
                                      result.statically_compatible, result.dynamically_compatible, result.err)
                update_dependency_evaluated_with_date(dependency, db)
                if dependency.err is not None:
                    print(f"Dependency.err was {dependency.err}, but is now gone")
                    update_dependency_err(dependency, "", db)
            except BaseMavenTestTimeout as e:
                print(e)
                update_dependency_err(dependency, "TEST_TIMEOUT", db)
            except BaseMavenCompileTimeout as e:
                print(e)
                update_dependency_err(dependency, "COMPILE_TIMEOUT", db)
            except MavenSurefireTestFailedException as e:
                print(e)
                update_dependency_err(dependency, "NO_TEST", db)
            except MavenNoPomInDirectoryException as e:
                print(e)
                update_dependency_err(dependency, "NO_POM", db)
            except MavenMetadataNotFound as e:
                print(e)
                update_dependency_err(dependency, "NO_VER", db)
                # Found 0 versions on maven, probably maven 404'd on the ga
            except MavenResolutionFailedException as e:
                print(e)
                update_dependency_err(dependency, "NO_RESOLVE", db)
            except MavenCompileFailedException as e:
                print(e)
                update_dependency_err(dependency, "NO_COMPILE", db)
            except GithubRepoNotFoundException as e:
                print(e)
                update_dependency_err(dependency, "NO_GITHUB", db)
            except GithubTagNotFoundException as e:
                print(e)
                update_dependency_err(dependency, "NO_TAG", db)

            count += 1
            print("")
            print(utils.bcolors.OKGREEN +
                  f"PROGRESS {int((count / num_dep) * 100)}% ({count}/{num_dep})"
                  + utils.bcolors.ENDC)


def collect_dependencies(use_original_pom=False):
    save_tree_as = "original_dep.tree" if use_original_pom else "new_dep.tree"
    save_log_as = "original_build.log" if use_original_pom else "new_build.log"
    is_new = not use_original_pom
    with Session(engine) as db:
        projects = get_projects_that_compile_and_has_tests(db)  # "Selected projects"
        count = 0
        total = len(projects)
        for project in projects:
            project_path = path_to_repos / project.repository

            if use_original_pom and Path.is_file(project_path / save_log_as):
                pass
            else:
                # original compilation log should've already been created in collect_projects()
                # mvn clean test-compile to download possibly new POMs to .m2.
                repo_utils.compile_repo(project_path, save_as=save_log_as)

            # Add new dependencies to db for the compatibility computation
            if use_original_pom and Path.is_file(project_path / save_tree_as):
                all_gavs = utils.get_dependencies(project.repository, project.sha.strip(), "dependency:tree",
                                                  original=use_original_pom)
            else:
                all_gavs = utils.get_dependencies(project.repository, project.sha.strip(), "dependency:tree",
                                                  original=use_original_pom, save_as=save_tree_as)

            resolved_gavs = utils.get_dependencies(project.repository, project.sha.strip(), "dependency:list",
                                                   original=use_original_pom)
            for gav in all_gavs:
                resolved = gav in resolved_gavs
                add_dependency(project, gav.group_id, gav.artifact_id, gav.version, resolved, is_new, db)

            count += 1
            print(f"== PROGRESS {int(count/total*100)}% ({count}/{total}) - {project.repository}")


def collect_projects():
    """
    - Project has pom.xml in root\
    - Pom has no modules? (feasibility)
    - Has no properties
    - has dependencies section
    - Pom has compile/runtime dependencies declared with SoftVer
    - Project compiles and the tests run
    """
    total_start_time = time.time()
    with Session(engine) as db:
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
                total = repos.totalCount
                count = 0
                for repo in repos:
                    count += 1
                    end_time = time.time()
                    print(f"Elapsed time for query {idx+1}/{len(queries)}: {format_time(end_time - start_time)} "
                          f"(total: {format_time(end_time - total_start_time)}")
                    if project_exists(repo.full_name, db):
                        continue

                    if repo.get_commits().totalCount >= 50:  # Skip projects with less than 50 commits
                        if repo_has_pom(repo):  # Skip projects with no pom.xml in root
                            pom = get_file(repo, "pom.xml").decoded_content
                            try:
                                root = ET.fromstring(pom)
                                # Skip projects with <modules> or no compile/runtime dependencies
                                if not utils.pom_has_tag("modules", root) \
                                        and utils.pom_has_compile_or_runtime_dependencies(root):
                                    download_path = download_repo_by_name(repo.full_name)

                                    # mvn clean test-compile > original_build.log
                                    compiles = repo_utils.compile_repo(download_path, save_as="original_build.log")
                                    # mvn dependency:tree > original_dep.tree & original_dep.log
                                    resolves = create_dep_tree(download_path, save_log_as="original_dep.log", save_tree_as="original_dep.tree")
                                    sha = repo_utils.get_sha_of_repo_head(download_path)
                                    # mvn surefire:tests
                                    has_tests = repo_utils.repo_has_tests(download_path) if compiles else False
                                    if has_tests:
                                        # Save original surefire reports outside of target folder
                                        shutil.copytree(download_path / "target" / "surefire-reports",
                                                        download_path / "original_surefire-reports")
                                    print(utils.bcolors.OKGREEN +
                                          f"[ADDING] {repo.full_name}, compiles={compiles}, has_tests={has_tests}"
                                          + utils.bcolors.ENDC)
                                    add_project(repo.full_name, sha, compiles, has_tests, db)
                            except Exception as e:
                                print(e)
                                print(utils.bcolors.WARNING +
                                      f"[SKIPPING] Could not parse {repo.full_name}"
                                      + utils.bcolors.ENDC)
                            else:
                                print(f"[SKIPPING] {repo.full_name}")
                    print_progress(count, total)


def create_project_resources(use_original=False):
    start_time = time.time()
    prefix = "original" if use_original else "new"
    use_pom = "original_pom.xml" if use_original else "pom.xml"
    with Session(engine) as db:
        print("Creating project resources...")
        projects = get_projects_that_compile_and_has_tests(db)
        count = 0
        total = len(projects)
        for project in projects:
            project_path = path_to_repos / project.repository
            # mvn clean test-compile > original_build.log
            compiles = repo_utils.compile_repo(project_path, use_pom=use_pom, save_as=f"{prefix}_build.log")
            print(f"[{project.repository}] compiles={compiles}, "
                  f"created original_build.log={Path.is_file(project_path / f'{prefix}_build.log')}")

            # mvn dependency:tree > original_dep.tree
            resolves = create_dep_tree(project_path, save_log_as=f"{prefix}_dep.log", save_tree_as=f"{prefix}_dep.tree", pom_file=use_pom)
            print(f"[{project.repository}] resolves={resolves}, "
                  f"created original_dep.tree={Path.is_file(project_path / f'{prefix}_dep.tree')}")

            # mvn surefire:tests
            has_tests = repo_utils.repo_has_tests(project_path) if compiles else False
            # if not compiles or not resolves or not has_tests:
            #     input(f"[{project.repository}] Something went wrong, compiles={compiles}, resolves={resolves},"
            #           f" has_tests={has_tests}")
            if has_tests:
                # Save original surefire reports outside of target folder
                shutil.copytree(project_path / "target" / "surefire-reports",
                                project_path / f"{prefix}_surefire-reports", dirs_exist_ok=True)
            print(f"[{project.repository}] has_tests={has_tests}, "
                  f"created {prefix}_surefire-reports={Path.is_dir(project_path / f'{prefix}_surefire-reports')}")
            count += 1
            end_time = time.time()
            print(f"== PROGRESS {int(count/total*100)}% ({count}/{total}) - {project.repository}  -- Elapsed time {format_time(end_time - start_time)}")
        print("Creating project resources complete.")


def clean_projects():
    """Reset all projects to the commit we collected them at"""
    with Session(engine) as db:
        print("Cleaning projects...")
        projects = get_projects_that_compile_and_has_tests(db)
        count = 0
        total = len(projects)
        for project in projects:
            old_dir = os.getcwd()
            os.chdir(path_to_repos / project.repository)
            subprocess.run(["git", "clean", "-df"]).check_returncode()  # Remove created files and folders
            subprocess.run(["git", "checkout", "-f", project.sha.strip()]).check_returncode()  # Check out correct commit
            subprocess.run(["git", "reset", "--hard"]).check_returncode()  # Remove changes made to existing files
            os.chdir(old_dir)
            count += 1
            print(f"== PROGRESS {int(count/total*100)}% ({count}/{total}) - {project.repository}")
        print("Clean complete.")


def switch_m2(switch_to: str, path_to_libraries=LOCAL_M2):
    assert switch_to == "original" or switch_to == "replaced"
    with Session(engine) as db:
        libraries = get_dependencies(db)
        count = 0
        total = len(libraries)

        for library in libraries:
            path_to_library = (path_to_libraries / library.group_id.replace(".", "/")
                               / library.artifact_id / library.version)
            path_to_pom = path_to_library / f"{library.artifact_id}-{library.version}.pom"
            path_to_replaced_pom = path_to_library / f"replaced_{library.artifact_id}-{library.version}.pom"
            path_to_original_pom = path_to_library / f"original_{library.artifact_id}-{library.version}.pom"
            if not Path.is_file(path_to_original_pom): continue
            if Path.is_file(path_to_original_pom) and not Path.is_file(path_to_replaced_pom):
                shutil.copy(path_to_pom, path_to_replaced_pom)

            print(f"\n== Switching POM of {path_to_library} to {switch_to}_{library.artifact_id}-{library.version}.pom")
            if switch_to == "original":
                shutil.copy(path_to_original_pom, path_to_pom)
            elif switch_to == "replaced":
                shutil.copy(path_to_replaced_pom, path_to_pom)

            count += 1
            print(f"== PROGRESS {int(count/total*100)}% ({count}/{total})")


def generate_metrics():
    """
    Repository: full name of github repository
    Resolves: 1 if the dependencies resolve after replacement, 0 otherwise
    Compiles: 1 if the repository compiles after replacement, 0 otherwise
    Passes tests: 1 if the repositories tests pass after replacement, 0 otherwise
    Overlapping: number of overlapping dependency GAs before and after replacement
    Additions: number of GAs that are new after replacement
    Subtractions: number of GAs that were dropped after replacement
    Resolved: number of resolved dependencies after replacement
    Replacements: number of resolved dependencies that originate from a replaced dependency declaration
    Downgrades: number of resolved dependencies that had their version downgraded after replacement
    Upgrades: number of resolved dependencies that had their version upgraded after replacement
    Downgrade steps: the sum of how many total downgrade steps are made
    Update steps: the sum of how many total update steps are made
    :return:
    """
    df = pd.DataFrame(columns=['Repository', 'Resolves', 'Compiles', 'Passes tests',
                               'Overlapping', 'Additions', 'Subtractions', 'Resolved',
                               'Replacements', 'Replacement rate', 'Downgrades', 'Upgrades', 'Change rate',
                               'Downgrade steps', 'Upgrade steps', 'Change magnitude'])
    with Session(engine) as db:
        print("Evaluating metrics for projects...")
        projects = get_projects_that_compile_and_has_tests(db)
        count = 0
        total = len(projects)
        resolution_failures = 0
        compilation_failures = 0
        test_failures = 0
        replacement_total = 0
        change_total = 0
        for project in projects:
            repository = project.repository
            resolves = False
            compiles = False
            passes_tests = False
            overlapping = 0
            additions = 0
            subtractions = 0
            resolved = 0
            replacements = 0
            downgrades = 0
            upgrades = 0
            change_rate = 0
            downgrade_steps = 0
            upgrade_steps = 0
            change_magnitude = 0
            replacement_rate = 0

            print(f"Evaluating metrics for {repository}")
            project_path = path_to_repos / repository
            old_dep_tree = project_path / "original_dep.tree"
            new_dep_tree = project_path / "new_dep.tree"
            new_dep_log = project_path / "new_dep.log"
            old_build_log = project_path / "original_build.log"
            new_build_log = project_path / "new_build.log"
            old_test_reports = project_path / "original_surefire-reports"
            new_test_reports = project_path / "new_surefire-reports"

            with open(new_build_log, 'r') as f:
                compiles = True if "BUILD SUCCESS" in f.read() else False
            with open(new_dep_log, 'r') as f:
                resolves = True if "BUILD SUCCESS" in f.read() else False
            if resolves:
                old_tree = dt.parse(old_dep_tree)
                new_tree = dt.parse(new_dep_tree)
                comparator = TreeComparator(old_tree, new_tree, repo=project_path)
                resolved, overlapping = comparator.overlapping
                additions, subtractions = comparator.difference
                replacements = comparator.replacements
                downgrades, downgrade_steps, upgrades, upgrade_steps = comparator.version_changes

                changes = upgrades + downgrades
                change_rate = changes / resolved
                change_magnitude = 0 if changes == 0 else (downgrade_steps + upgrade_steps) / changes
                replacement_rate = replacements / resolved
                passes_tests = comparator.passes_test_suite

            print(f"[{project.repository}] resolves={resolves}, compiles={compiles},"
                  f" passes_tests={passes_tests}, change_rate={change_rate}, replacemen_ratet={replacement_rate}")

            count += 1
            resolution_failures += 1 if not resolves else 0
            compilation_failures += 1 if not compiles and resolves else 0
            test_failures += 1 if not passes_tests and resolves and compiles else 0
            change_total += change_rate
            replacement_total += replacement_rate

            row = {'Repository': repository, 'Resolves': resolves, 'Compiles': compiles,
                   'Passes tests': passes_tests, 'Overlapping': overlapping, 'Additions': additions,
                   'Subtractions': subtractions, 'Resolved': resolved, 'Replacements': replacements,
                   'Replacement rate': replacement_rate,
                   'Downgrades': downgrades, 'Upgrades': upgrades, 'Change rate': change_rate,
                   'Downgrade steps': downgrade_steps, 'Upgrade steps': upgrade_steps,
                   'Change magnitude': change_magnitude
                   }
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            df.to_csv('rq5_results_n105_2pass.csv', index=False)
            print(f"== PROGRESS {int(count/total*100)}% ({count}/{total}) - {project.repository}")

    results = {
        'resolution_failure_rate': resolution_failures / total,
        'compilation_failures_rate': compilation_failures / (total - resolution_failures),
        'test_failure_rate': test_failures / (total - resolution_failures - compilation_failures),
        'replacement_rate': replacement_total / total,
        'change_rate': change_total / total,
    }
    with open('result_2pass.json', 'w') as f:
        json.dump(results, f, indent=4)

    pprint(results)

    print("Test report generation complete. See result.json")


def generate_test_reports():
    with Session(engine) as db:
        print("Generating test reports for projects...")
        projects = get_projects_that_compile_and_has_tests(db)
        count = 0
        total = len(projects)
        for project in projects:
            old_dir = os.getcwd()
            os.chdir(path_to_repos / project.repository)
            subprocess.run(["mvn", "clean", "test", "-Dspotbugs.skip=true", "-Dspotless.check.skip=true", "-Dspotless.apply.skip=true"])
            surefire_reports = path_to_repos / project.repository / "target" / "surefire-reports"
            if Path.is_dir(surefire_reports):
                subprocess.run(["mv", surefire_reports, "original_surefire-reports"]).check_returncode()
            else:
                input(f"Found not surefire-reports for {project.repository}")

            os.chdir(old_dir)

            count += 1
            print(f"== PROGRESS {int(count/total*100)}% ({count}/{total}) - {project.repository}")
        print("Test report generation complete.")


def confirm(step: str, recompute: bool):
    input(f"[RQ5-MAIN] Running collection step {step} with recompute={recompute}. Press any key to begin.")


def main():
    parser = argparse.ArgumentParser(description='Script that collects the datapoints used to evaluate RQ5.')
    parser.add_argument('-s', '--step', choices=['projects', 'dependencies', 'compatibilities',
                                                 'generate_compatibility_store', 'expand_projects',
                                                 'extract_library_jars', 'expand_library_poms', 'clean_projects',
                                                 'generate_test_reports', 'create_project_resources',
                                                 'switch_m2_to_original', 'switch_m2_to_replaced', 'generate_metrics'],
                        help='Specify which collection step in the data collection pipeline you would like to run. '
                             'Options (in logical order): projects, dependencies, compatibilities, '
                             'generate_compatibility_store, expand_projects, extract_library_jars, expand_library_poms,'
                             ' clean_projects, create_project_resources',
                        required=True)
    parser.add_argument('-r', '--recompute', action='store_true', default=False,
                        help='Specify whether to recompute existing data')
    parser.add_argument('-o', '--original', action='store_true', default=False,
                        help='Specify whether to use the original, unexpanded pom file')

    args = parser.parse_args()
    collection_step = args.step
    recompute = args.recompute
    original = args.original

    set_up_db()

    confirm(collection_step, recompute)
    if collection_step == 'projects':
        # Collect projects, generate original_dep.tree, original_build.log, and original_surefire-reports
        collect_projects()
    elif collection_step == 'dependencies':
        collect_dependencies(use_original_pom=original)
    elif collection_step == 'compatibilities':
        collect_compatibilities()
    elif collection_step == 'generate_compatibility_store':
        generate_compatibility_store()
    elif collection_step == 'expand_projects':
        expand_project_poms(recompute=recompute)
    elif collection_step == 'extract_library_jars':
        extract_library_jars(recompute=recompute)
    elif collection_step == 'expand_library_poms':
        expand_library_poms(recompute=recompute, pass_2=False)  # Remove pass_2 if performing pass 1
    elif collection_step == 'clean_projects':
        # Reset Github projects to initial state
        clean_projects()
    elif collection_step == 'generate_test_reports':
        generate_test_reports()
    elif collection_step == 'create_project_resources':
        # From collected projects, generate original_dep.tree, original_build.log, and original_surefire-reports
        # If not using original, created new_dep.tree, new_build.log, new_surefire-reports
        create_project_resources(use_original=original)
    elif collection_step == 'switch_m2_to_original':
        switch_m2(switch_to="original")
    elif collection_step == 'switch_m2_to_replaced':
        switch_m2(switch_to="replaced")
    elif collection_step == 'generate_metrics':
        generate_metrics()

