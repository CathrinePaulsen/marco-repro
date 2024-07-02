import argparse
import os
import sys
from functools import cmp_to_key

dirname = os.path.dirname(__file__)
MAVEN_ARTIFACT = os.path.join(dirname, '../libs/maven-artifact/maven-artifact-3.0-alpha-1.jar')
sys.path.append(str(MAVEN_ARTIFACT))
from org.apache.maven.artifact.versioning import ComparableVersion  # Java import, ignore IDE errors


def create_range_spec_from_list(list):
    """
    Given a list of ComparableVersions, e.g. [1,2,3], return the corresponding range, i.e. [1,3]
    :param list: list[ComparableVersion]
    :return: str
    """
    lower_bound = str(list[0])
    upper_bound = str(list[-1])
    if lower_bound == upper_bound:
        return "[" + lower_bound + "]"
    return "[" + lower_bound + "," + upper_bound + "]"


def get_continuous_ranges(compatible_versions, available_versions):
    """
    Groups elements in compatible_versions that appear consecutively in available_versions.
    :param compatible_versions: list[ComparableVersion]
    :param available_versions: list[ComparableVersion]
    :return: list[ComparableVersion]
    """
    continuous_ranges = []
    current_range = []

    for av in available_versions:
        if av in compatible_versions:
            current_range.append(av)
        elif current_range:
            continuous_ranges.append(current_range)
            current_range = []

    if current_range:
        continuous_ranges.append(current_range)

    return continuous_ranges


def create_range_spec(compatible_versions, available_versions):
    """
    Creates a valid Maven range spec based on the given compatible and available versions.
    :param compatible_versions: list[ComparableVersion]
    :param available_versions: list[ComparableVersion]
    :return: str representing the range spec
    """
    if len(compatible_versions) == 0:
        # If there are no compatible versions, then the compatible version range is empty.
        return "[]"

    continuous_ranges = get_continuous_ranges(compatible_versions, available_versions)

    range_spec = ""
    for cr in continuous_ranges:
        range = create_range_spec_from_list(cr)
        if not range_spec:
            range_spec += range
        else:
            range_spec += "," + range

    return range_spec


def create_ordered_list_of_comparable_versions(string_versions):
    """
    Takes a list of strings representing versions, and returns a list of ComparableVersions ordered according to
    Maven's version sorting algorithm.
    :param string_versions: list[str] representing versions
    :return: list[ComparableVersions] in ascending version order as defined by Maven.
    """
    comparable_versions = {ComparableVersion(x) for x in string_versions}

    return sorted(comparable_versions, key=cmp_to_key(ComparableVersion.compareTo))


def parse_args():
    """
    Handles CLI input.
    :return: parsed input arguments
    """
    cli = argparse.ArgumentParser(description='Range Converter')
    cli.add_argument(
        "-c", "--compatible",
        nargs="*",
        type=str,
        default=[],
        help="Space-separated list of compatible versions, e.g.: '[1, 2.0, 3-beta, test-4.2]' "
             "should be passed as '1 2.0 3-beta test-4.2'. Defaults to an empty list."
    )
    cli.add_argument(
        "-a", "--available",
        nargs="*",
        type=str,
        default=[],
        help="Space-separated list of available versions, e.g.: '[1, 2.0, 3-beta, test-4.2]' "
             "should be passed as '1 2.0 3-beta test-4.2'. Defaults to an empty list."
    )
    cli.add_argument(
        "--debug",
        action='store_true',
        help="Enables extra printing for debugging."
    )

    return cli.parse_args()


if __name__ == "__main__":
    args = parse_args()
    compatible_versions = args.compatible
    available_versions = args.available
    if args.debug:
        print("Range Converter called with compatible_versions=" + str(compatible_versions) +
              " and available_versions=" + str(available_versions))

    available_versions = create_ordered_list_of_comparable_versions(available_versions)
    compatible_versions = create_ordered_list_of_comparable_versions(compatible_versions)

    version_spec = create_range_spec(compatible_versions, available_versions)

    print(version_spec)
