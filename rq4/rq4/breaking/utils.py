from pathlib import Path

from rq4.breaking.datapoint import Datapoint, datapoints


def purge_dataset(dataset: Path):
    """
    Deletes all datapoints in the given dataset.
    """
    for datapoint in datapoints(dataset):
        datapoint.remove()


def remove_datapoints_not_in_dataset(remove_from_dataset: Path, not_in_dataset: Path):
    """
    Removes datapoints in the remove_from_dataset that are not in the not_in_dataset.
    """
    for filepath in remove_from_dataset.glob("*.json"):
        not_in_filepath = not_in_dataset / filepath.name
        if not Path.is_file(not_in_filepath):
            Path.unlink(filepath)


def remove_pom_types(datapoints: set[Datapoint]) -> set[Datapoint]:
    """
    Takes a set of datapoints, removes the datapoints with file type "POM", and returns the remainder.
    :param datapoints:
    :return:
    """
    new_datapoints = set()
    for datapoint in datapoints:
        if datapoint.updated_file_type != "POM":
            new_datapoints.add(datapoint)
    return new_datapoints


def remove_project_specific_failures(datapoints: set[Datapoint]) -> set[Datapoint]:
    """
    Takes a set of datapoints, and returns a new set of datapoints which only contains the datapoints with
    'failure category' equal to 'COMPILATION_FAILURE', 'TEST_FAILURE', or 'DEPENDENCY_RESOLUTION_FAILURE'
    """
    failure_categories = ['COMPILATION_FAILURE', 'TEST_FAILURE', 'DEPENDENCY_RESOLUTION_FAILURE']
    new_datapoints = set()
    for datapoint in datapoints:
        if datapoint.failure_category in failure_categories:
            new_datapoints.add(datapoint)
    return new_datapoints


def get_unique_datapoints(dataset: Path) -> set[Datapoint]:
    """
    Returns a list of datapoints in the dataset with unique dependency updates.
    """
    unique_datapoints = set()
    for datapoint in datapoints(dataset):
        unique_datapoints.add(datapoint)
    return unique_datapoints


def remove_plugins(datapoints: set[Datapoint]) -> set[Datapoint]:
    """
    Takes a set of datapoints, and returns a new set of datapoints which only contains the datapoints with
    'dependency section' equal to 'dependencies' or 'dependencyManagement'
    """
    dependency_sections = ['dependencies', 'dependencyManagement']
    new_datapoints = set()
    for datapoint in datapoints:
        if datapoint.dependency_section in dependency_sections:
            new_datapoints.add(datapoint)
    return new_datapoints
