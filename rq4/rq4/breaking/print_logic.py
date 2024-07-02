import json
from pathlib import Path
from pprint import pprint

from rq4.breaking import config
from rq4.breaking.datapoint import datapoints, sum_datapoints


def extract_stats(dataset: Path):
    """
    Prints simple statistics for the given dataset to console.
    Also stores the same statistics in a statistics.info file in the root of the datset.
    """
    assert Path.is_dir(dataset)

    stats = {
        'failure_categories': {},
        'dependency_section': {},
        'updated_file_types': {},
        'version_update_types': {},
        'dynamically_compatibles': {},
        'duplicates': {},
        'num_datapoints': sum_datapoints(dataset)
    }
    seen_datapoints = set()
    for datapoint in datapoints(dataset):
        if datapoint in seen_datapoints:
            stats['duplicates'][str(datapoint)] = stats['duplicates'].get(datapoint, 0) + 1
        seen_datapoints.add(datapoint)
        stats['failure_categories'][datapoint.failure_category] = stats['failure_categories'].get(
            datapoint.failure_category, 0) + 1
        stats['version_update_types'][datapoint.version_update_type] = stats['version_update_types'].get(
            datapoint.version_update_type, 0) + 1
        stats['dependency_section'][datapoint.dependency_section] = stats['dependency_section'].get(
            datapoint.dependency_section, 0) + 1
        stats['updated_file_types'][datapoint.updated_file_type] = stats['updated_file_types'].get(
            datapoint.updated_file_type, 0) + 1
        if dataset == config.runnable_dataset:
            stats['dynamically_compatibles'][str(datapoint)] = datapoint.dynamically_compatible

    stats['duplicates'] = sum(stats['duplicates'].values())

    print(f"\n=========== STATS {dataset.name} ===============")
    pprint(stats)
    print(f"=========================================\n")

    stats_filename = dataset / "statistics.info"
    with open(stats_filename, 'w') as file:
        json.dump(stats, file)


def print_static_progress():
    static_n = sum_datapoints(config.static_dataset)
    no_static_n = sum_datapoints(config.no_static_dataset)
    no_jar_n = sum_datapoints(config.no_jar_dataset)
    processed_n = static_n + no_static_n + no_jar_n
    to_process_n = sum_datapoints(config.cleaned_dataset)
    print(f"STATIC CHECK PROGRESS: processed {processed_n}/{to_process_n} ({int(processed_n / to_process_n * 100)}%),\n"
          f"    - {static_n} are compatible ({int(static_n / to_process_n * 100)}%)\n"
          f"    - {no_static_n} are not compatible ({int(no_static_n / to_process_n * 100)}%)\n"
          f"    - {no_jar_n} could not be evaluated because the jars were not found ({int(no_jar_n / to_process_n * 100)}%)")


def print_runnable_progress():
    run_n = sum_datapoints(config.runnable_dataset)
    linkable_n = sum_datapoints(config.linked_dataset)
    no_comp = sum_datapoints(config.no_run_no_comp_dataset)  # Deps that do not compile
    no_test = sum_datapoints(config.no_run_no_test_dataset)  # Deps that do not have at least one runnable test
    no_maven = sum_datapoints(config.no_run_no_maven_dataset)  # Deps that do not have a pom / not maven project error
    unrunnable_n = no_comp + no_test + no_maven
    processed_n = run_n + unrunnable_n
    print(f"RUNNABLE PROGRESS: processed {processed_n}/{linkable_n} ({int(processed_n / linkable_n * 100)}%),\n"
          f"    {run_n} are runnable ({int(run_n / linkable_n * 100)}%), {unrunnable_n} are not runnable ({int(unrunnable_n / linkable_n * 100)}%) of which:\n"
          f"        - {no_comp} do not compile\n"
          f"        - {no_maven} has no pom in project root\n"
          f"        - {no_test} has no (runnable) tests\n")


def print_link_progress():
    static_n = sum_datapoints(config.static_dataset)
    linked_n = sum_datapoints(config.linked_dataset)
    no_pom_n = sum_datapoints(config.no_link_no_pom_dataset)
    no_github_n = sum_datapoints(config.no_link_no_github_dataset)
    no_tag_n = sum_datapoints(config.no_link_no_tag_dataset)
    no_link_n = no_pom_n + no_github_n + no_tag_n
    processed_n = linked_n + no_link_n

    print(
        f"LINK PROGRESS: processed {processed_n}/{static_n} ({int(processed_n / static_n * 100)}%), linked {linked_n}/{static_n} ({int(linked_n / static_n * 100)}%),\n"
        f"    {no_link_n} are unlinkable ({int(no_link_n / static_n * 100)}%), of which:\n"
        f"        - {no_pom_n} has no poms\n"
        f"        - {no_github_n} has no github link\n"
        f"        - {no_tag_n} has no github tag")


def print_statistics():
    original_n = sum_datapoints(config.original_dataset)
    cleaned_n = sum_datapoints(config.cleaned_dataset)
    static_n = sum_datapoints(config.static_dataset)
    linked_n = sum_datapoints(config.linked_dataset)
    runnable_n = sum_datapoints(config.runnable_dataset)
    print("==== STATISTICS ====")
    print(f"Original n = {original_n}")
    print(f"Cleaned n = {cleaned_n} ({int(cleaned_n / original_n * 100)}%)")
    print(f"Static n = {static_n} ({int(static_n / cleaned_n * 100)}%)")
    print(f"Linked   n = {linked_n} ({int(linked_n / static_n * 100)}%)")
    print(f"Runnable n = {runnable_n} ({int(runnable_n / linked_n * 100)}%)")
    print("====================")
