"""Module responsible for evaluating 'The Tool' on the BUMP benchmark (breaking changes dataset)."""
import argparse
import json
from pathlib import Path

import rq4.breaking.print_logic as p
from core import (PomNotFoundException, get_github_repo_and_tag)
from rq4.breaking import config, utils
from rq4.breaking.datapoint import datapoints
from server.dynamic import dynamically_compatible
from server.exceptions import (MavenNoPomInDirectoryException, BaseJarNotFoundException, CandidateJarNotFoundException,
                               MavenResolutionFailedException, MavenCompileFailedException, BaseMavenCompileTimeout,
                               MavenSurefireTestFailedException, CandidateMavenCompileTimeout)
from server.static import statically_compatible, run_static_check
from server.template.base_template import BaseTemplate
from server.template.candidate_template import CandidateTemplate
from models.pr import get_update_type


def create_cleaned_dataset(override=False):
    """
    Creates a new subset of the original dataset in bump_benchmark/cleaned.
    The original dataset is filtered according to the following rules:
    1. Remove duplicate updates
    2. Remove plugin dependencies
    3. Remove project-specific failure categories (dependency lock failures and enforcer failures)
    4. Remove POM-type dependencies

    if override=True then pre-existing datapoints in bump_benchmark/cleaned are removed.
    """
    filtered_datapoints = utils.get_unique_datapoints(config.original_dataset)  # Filter Step 1
    filtered_datapoints = utils.remove_plugins(filtered_datapoints)  # Filter Step 2
    filtered_datapoints = utils.remove_project_specific_failures(filtered_datapoints)  # Filter Step 3
    filtered_datapoints = utils.remove_pom_types(filtered_datapoints)  # Filter Step 4

    if override:
        for datapoint in datapoints(config.cleaned_dataset):
            datapoint.remove()

    for datapoint in filtered_datapoints:
        datapoint.store(config.cleaned_dataset)


def create_static_dataset(dataset=config.cleaned_dataset, override=False):
    """
    Evaluates the datapoints in the given dataset, and creates a new dataset of the datapoints that were
    statically compatible in bump_benchmark/static.
    - Datapoints that were statically incompatible are placed in bump_benchmark/no_static
    - Datapoints that could not be evaluated due to
            1. Jars could not be found on maven central => no_jar   (n=0 before)

    If override is set to True, then static, no_static and no_jar are purged beforehand.
    :return:
    """
    p.print_static_progress()

    if override:
        input(f"Press any key to confirm purging of the static/no_static/no_jar datasets")
        utils.purge_dataset(config.static_dataset)
        utils.purge_dataset(config.no_static_dataset)
        utils.purge_dataset(config.no_jar_dataset)
        p.print_static_progress()

    for datapoint in datapoints(dataset):
        print(f"Evaluating FILE: {datapoint.filepath}")
        static_filepath = config.static_dataset / datapoint.filename
        no_static_filepath = config.no_static_dataset / datapoint.filename
        no_jar_filepath = config.no_jar_dataset / datapoint.filename

        # Skip datapoints already processed (successfully or unsuccessfully run)
        if Path.is_file(static_filepath) or Path.is_file(no_static_filepath) or Path.is_file(no_jar_filepath):
            continue

        ga = f"{datapoint.group_id}:{datapoint.artifact_id}"
        print(f"\nEvaluating base: {ga}:{datapoint.version_pre}, candidate: {ga}:{datapoint.version_new}")

        # Run static check
        try:
            compatible = statically_compatible(datapoint.group_id, datapoint.artifact_id,
                                               datapoint.version_pre, datapoint.version_new)
        except (BaseJarNotFoundException, CandidateJarNotFoundException) as e:
            print(e)
            print(f"Found no jar for base or candidate. Getting jar from docker image.")
            # input("Press any key to continue.")
            try:
                jars_path_root = datapoint.get_jars_from_images()
                jar_path_pre = jars_path_root / datapoint.m2_jar_path_pre.name
                jar_path_new = jars_path_root / datapoint.m2_jar_path_new.name
                compatible = run_static_check(jar_path_pre, jar_path_new)
            except Exception as e:
                print(e)
                print("Could not find jar from docker image either. Adding datapoint to no_jar dataset.")
                datapoint.store(config.no_jar_dataset)
                p.print_static_progress()
                continue

        if not compatible:
            print(f"Adding datapoint to no_static.")
            datapoint.store(config.no_static_dataset)
            p.print_static_progress()
            continue

        print("Adding datapoint to static.")
        datapoint.store(config.static_dataset)
        p.print_static_progress()


def create_linked_dataset(override=False):
    """
    Finds the datapoints in the static dataset for which we can find the GitHub link.
    Successfully linked datapoints are stored in the linked dataset.
    Unsuccessful datapoints are stored in the no_link dataset.
    There are three causes for unsuccessful linking:
        1. no_github: the pom file does not contain a link to a github repository
        2. no_pom: we could not find the pom file (on Maven Central or in missing_poms)
        3. no_tag: we found the github repository but could not find the tag for the version
    """
    p.print_link_progress()
    p.print_statistics()

    if override:
        input(f"Press any key to confirm purging of the linked/no_link_no_pom/no_link_no_github/no_link_no_tag datasets")
        utils.purge_dataset(config.linked_dataset)
        utils.purge_dataset(config.no_link_no_pom_dataset)
        utils.purge_dataset(config.no_link_no_tag_dataset)
        utils.purge_dataset(config.no_link_no_github_dataset)
        p.print_link_progress()

    # Extract gavs, find Github links, store in linked
    for datapoint in datapoints(config.static_dataset):
        linked_filepath = config.linked_dataset / datapoint.filename
        no_link_no_pom_filepath = config.no_link_no_pom_dataset / datapoint.filename
        no_link_no_github_filepath = config.no_link_no_github_dataset / datapoint.filename
        no_link_no_tag_filepath = config.no_link_no_tag_dataset / datapoint.filename

        if not override:
            # Skip datapoints already processed (successfully or unsuccessfully linked)
            if Path.is_file(linked_filepath) or Path.is_file(no_link_no_pom_filepath) or \
                    Path.is_file(no_link_no_github_filepath) or Path.is_file(no_link_no_tag_filepath):
                continue

        print(f"\nEvaluating base: {datapoint.group_id}:{datapoint.artifact_id}:{datapoint.version_pre}, "
              f"candidate: {datapoint.group_id}:{datapoint.artifact_id}:{datapoint.version_new}")

        try:
            repo_base, tag_base = get_github_repo_and_tag(datapoint.group_id, datapoint.artifact_id, datapoint.version_pre)
            repo_cand, tag_cand = get_github_repo_and_tag(datapoint.group_id, datapoint.artifact_id, datapoint.version_new)
        except PomNotFoundException as e:
            print(e)
            print(f"Found no pom for base or candidate. Getting pom from docker image.")

            try:
                pom_path_root = datapoint.get_poms_from_images()
                pom_path_pre = pom_path_root / datapoint.m2_pom_path_pre.name
                pom_path_new = pom_path_root / datapoint.m2_pom_path_new.name

                repo_base, tag_base = get_github_repo_and_tag(datapoint.group_id, datapoint.artifact_id,
                                                              datapoint.version_pre, pom_path=pom_path_pre)
                repo_cand, tag_cand = get_github_repo_and_tag(datapoint.group_id, datapoint.artifact_id,
                                                              datapoint.version_new, pom_path=pom_path_new)
            except Exception as e:
                print(e)
                print("Could not find pom from docker image either. Adding datapoint to no_link/no_pom dataset.")
                datapoint.store(config.no_link_no_pom_dataset)
                p.print_link_progress()
                continue

        if not repo_base and not repo_cand:
            print("\nFAILURE: Could not find repo for base or candidate")
            datapoint.store(config.no_link_no_github_dataset)
            p.print_link_progress()
            # input("Press any key to go to continue.")
            continue

        # If the base and candidate were successfully linked, add them to linked/
        if tag_base and tag_cand:
            datapoint.data['updatedDependency']['gitHubLink'] = repo_base.full_name
            datapoint.data['updatedDependency']['previousVersionGitHubCommit'] = tag_base.commit
            datapoint.data['updatedDependency']['newVersionGitHubCommit'] = tag_cand.commit
            datapoint.store(config.linked_dataset)
            print("\nSUCCESS: Successfully linked base and candidate.")
            p.print_link_progress()
        else:
            print("\nFAILURE: Could not find tag for base and candidate.")
            datapoint.store(config.no_link_no_tag_dataset)
            p.print_link_progress()
            input("Press any key to go to continue.")

    p.print_statistics()


def create_dynamic_dataset(override=False):
    print("\nPreparing dynamic test.")
    find_runnable(override=override)
    print("\nRunning dynamic test.")
    check_runnable()


def find_runnable(override=False):
    """
    Finds the datapoints in the linked dataset for which we are able to run the dynamic check on.
    Runnable datapoints are stored in the runnable dataset.
    Non-runnable datapoints are stored in the no_run dataset.
    There are three causes for unsuccessful linking:
        1. no_comp: we could not compile the repository for either of the dependencies
        2. no_maven: there was no pom in the repository
        3. no_test: there was no test suite in the repository
    """
    p.print_runnable_progress()

    if override:
        input(f"Press any key to confirm purging of the runnable/no_run_no_comp/no_run_no_test/no_run_no_maven datasets")
        utils.purge_dataset(config.runnable_dataset)
        utils.purge_dataset(config.no_run_no_comp_dataset)
        utils.purge_dataset(config.no_run_no_maven_dataset)
        utils.purge_dataset(config.no_run_no_test_dataset)
        p.print_runnable_progress()

    count = 0
    for datapoint in datapoints(config.linked_dataset):
        print(f"Evaluating FILE: {datapoint.filepath}")
        count += 1
        runnable_filepath = config.runnable_dataset / datapoint.filename
        no_comp_filepath = config.no_run_no_comp_dataset / datapoint.filename
        no_test_filepath = config.no_run_no_test_dataset / datapoint.filename
        no_maven_filepath = config.no_run_no_maven_dataset / datapoint.filename

        if not override:
            # Skip datapoints already processed (successfully or unsuccessfully run)
            if Path.is_file(runnable_filepath) or Path.is_file(no_comp_filepath) or Path.is_file(no_test_filepath) \
                    or Path.is_file(no_maven_filepath):
                continue

        print(
            f"\nEvaluating base: {datapoint.group_id}:{datapoint.artifact_id}:{datapoint.version_pre}, "
            f"candidate: {datapoint.group_id}:{datapoint.artifact_id}:{datapoint.version_new}, "
            f"repo: {datapoint.repo}, commits: {datapoint.commit_base} ({datapoint.commit_candidate})")

        # Prepare templates
        try:
            print(f"Creating base template for {datapoint.group_id}:{datapoint.artifact_id}:{datapoint.version_pre}, "
                  f"repo is stored at {config.repo_path}")
            base_template = BaseTemplate(datapoint.group_id, datapoint.artifact_id, datapoint.version_pre,
                                         repo_storage_path=config.repo_path)
            # input("!!!!!!!!!!!!!")
        except PomNotFoundException as e:
            # input("????????????")
            print(e)
            pom_path_root = datapoint.get_poms_from_images()
            pom_path_pre = pom_path_root / datapoint.m2_pom_path_pre.name
            try:
                base_template = BaseTemplate(datapoint.group_id, datapoint.artifact_id, datapoint.version_pre,
                                             repo_storage_path=config.repo_path, pom_path=pom_path_pre)
            except MavenNoPomInDirectoryException as e:
                print(e)
                print("Adding datapoint to no maven dataset")
                datapoint.store(config.no_run_no_maven_dataset)
                p.print_runnable_progress()
                continue
            except MavenResolutionFailedException as e:
                print(e)
                datapoint.store(config.no_run_no_resolve_dataset)
                p.print_runnable_progress()
                continue
            except (MavenCompileFailedException, BaseMavenCompileTimeout) as e:
                print(e)
                datapoint.store(config.no_run_no_comp_dataset)
                p.print_runnable_progress()
                continue
            except MavenSurefireTestFailedException as e:
                print(e)
                datapoint.store(config.no_run_no_test_dataset)
                p.print_runnable_progress()
                continue
        except MavenNoPomInDirectoryException as e:
            print(e)
            print("Adding datapoint to no maven dataset")
            datapoint.store(config.no_run_no_maven_dataset)
            p.print_runnable_progress()
            continue
        except MavenResolutionFailedException as e:
            print(e)
            datapoint.store(config.no_run_no_resolve_dataset)
            p.print_runnable_progress()
            continue
        except (MavenCompileFailedException, BaseMavenCompileTimeout) as e:
            print(e)
            datapoint.store(config.no_run_no_comp_dataset)
            p.print_runnable_progress()
            continue
        except MavenSurefireTestFailedException as e:
            print(e)
            datapoint.store(config.no_run_no_test_dataset)
            p.print_runnable_progress()
            continue

        try:
            print(f"Creating candidate template for "
                  f"{datapoint.group_id}:{datapoint.artifact_id}:{datapoint.version_new}, "
                  f"repo is stored at {config.repo_path}")
            try:
                cand_template = CandidateTemplate(datapoint.group_id, datapoint.artifact_id, datapoint.version_new,
                                                  repo_storage_path=config.repo_path)
            except PomNotFoundException as e:
                print(e)
                pom_path_root = datapoint.get_poms_from_images()
                pom_path_new = pom_path_root / datapoint.m2_pom_path_new.name
                cand_template = CandidateTemplate(datapoint.group_id, datapoint.artifact_id, datapoint.version_new,
                                                  repo_storage_path=config.repo_path, pom_path=pom_path_new)
        except MavenResolutionFailedException as e:
            print(e)
            datapoint.store(config.no_run_no_resolve_dataset)
            p.print_runnable_progress()
            continue
        except (MavenCompileFailedException, CandidateMavenCompileTimeout) as e:
            print(e)
            datapoint.store(config.no_run_no_comp_dataset)
            p.print_runnable_progress()
            continue
        except MavenSurefireTestFailedException as e:
            print(e)
            datapoint.store(config.no_run_no_test_dataset)
            p.print_runnable_progress()
            continue

        print("Adding datapoint to runnable dataset")
        datapoint.store(config.runnable_dataset)
        p.print_runnable_progress()
        input("-- SUCCESS. Both templates generated. Press any key to continue.")
    print(f"Evaluated {count} files. {count} == 15? {count == 15}")


def check_runnable():
    """Runs the actual dynamic check for the datapoints in the runnable_dataset
    (i.e. the datapoints we were able to create templates for.
    The outcome of the check is either that the update described by the datapoint is dynamically compatible or not.
    The outcome is stored in the datapoint under a new field: datapoint.updatedDependency.dynamicallyCompatible
    """
    for filepath in config.runnable_dataset.glob("*.json"):
        input(f"Evaluating FILE: {filepath}")

        with open(filepath, 'r') as file:
            data = json.load(file)
        g = data['updatedDependency']['dependencyGroupID']
        a = data['updatedDependency']['dependencyArtifactID']
        v = data['updatedDependency']['previousVersion']

        print(f"Getting base template for {g}:{a}:{v}...")
        base = BaseTemplate(g, a, v, repo_storage_path=config.repo_path)
        cv = data['updatedDependency']['newVersion']
        print(f"Running dynamic check on base {g}:{a}:{v} ,   candidate v {cv}")
        if dynamically_compatible(base, cv):
            print(f"CAND {g}:{a}:{cv} is dynamically compatible with BASE {g}:{a}:{v}")
            data['updatedDependency']['dynamicallyCompatible'] = True
        else:
            print(f"CAND {g}:{a}:{cv} is not dynamically compatible with BASE {g}:{a}:{v}")
            data['updatedDependency']['dynamicallyCompatible'] = False

        with open(filepath, 'w') as file:
            json.dump(data, file)
        input("Continue?\n")


def convert_update_type():
    datasets = [config.original_dataset, config.cleaned_dataset, config.static_dataset, config.no_static_dataset,
                config.no_jar_dataset, config.linked_dataset, config.no_link_no_pom_dataset,
                config.no_link_no_github_dataset, config.no_link_no_tag_dataset, config.runnable_dataset,
                config.no_run_no_comp_dataset, config.no_run_no_maven_dataset, config.no_run_no_test_dataset,
                config.no_run_no_resolve_dataset]
    for dataset in datasets:
        for filepath in dataset.glob("*.json"):
            with open(filepath, 'r+') as file:
                print(f"Reading file {filepath}")
                data = json.load(file)
                update_type = data['updatedDependency']['versionUpdateType']
                old_ver = data['updatedDependency']['previousVersion']
                new_ver = data['updatedDependency']['newVersion']
                new_update_type = get_update_type(old_ver, new_ver)
                if update_type != new_update_type:
                    print(f"Found different update type: old={update_type}, new={new_update_type}")
                    data['updatedDependency']['versionUpdateType'] = new_update_type
                    # Reset the file pointer to the beginning
                    file.seek(0)
                    # Write the modified data back to the file
                    json.dump(data, file, indent=4)
                    # Truncate the remaining content in the file (in case the new data is smaller than the original)
                    file.truncate()


def confirm(step: str):
    input(f"[BREAKING DATASET] Running data collection step {step}. Press any key to begin.")


def main():
    parser = argparse.ArgumentParser(description='Script that collects the datapoints for the breaking dataset '
                                                 'used to evaluate RQ4.')
    parser.add_argument('-s', '--step', choices=['clean', 'static', 'link', 'dynamic', 'convert_update_type'],
                        help='Specify which collection step in the data collection pipeline you would like to run. '
                             'Options (in logical order): clean, static, link, dynamic.', required=True)
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

    if collection_step == 'clean':
        if stats_only:
            p.extract_stats(config.cleaned_dataset)
        else:
            confirm(collection_step)
            create_cleaned_dataset(override=override)
    elif collection_step == 'static':
        if stats_only:
            p.extract_stats(config.static_dataset)
            p.extract_stats(config.no_static_dataset)
            p.extract_stats(config.no_jar_dataset)
        else:
            confirm(collection_step)
            create_static_dataset(override=override)
    elif collection_step == 'link':
        if stats_only:
            p.extract_stats(config.linked_dataset)
            p.extract_stats(config.no_link_no_github_dataset)
            p.extract_stats(config.no_link_no_tag_dataset)
            p.extract_stats(config.no_link_no_pom_dataset)
        else:
            confirm(collection_step)
            create_linked_dataset(override=override)
    elif collection_step == 'dynamic':
        if stats_only:
            p.extract_stats(config.runnable_dataset)
            p.extract_stats(config.no_run_no_comp_dataset)
            p.extract_stats(config.no_run_no_test_dataset)
            p.extract_stats(config.no_run_no_maven_dataset)
        else:
            confirm(collection_step)
            create_dynamic_dataset(override=override)
    elif collection_step == 'convert_update_type':
            confirm(collection_step)
            convert_update_type()

    p.print_statistics()
