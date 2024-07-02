"""Module containing logic related to the creation of TestFailures from surefire test reports."""
import os
import pathlib
from pathlib import Path
from xml.etree import ElementTree
# from lxml import etree as ET

# TODO: refactor TestFailure into TestResult maybe?
class TestFailure:
    """Class representing a failed test case (due to failure or error)"""
    __test__ = False   # To avoid being collected by pytest

    def __init__(self, testsuite_name: str, testcase_name: str, testcase_classname: str, type: str):
        self.testsuite_name = testsuite_name
        self.testcase_name = testcase_name
        self.testcase_classname = testcase_classname
        self.type = type

    def __eq__(self, other):
        if isinstance(other, TestFailure):
            return self.testsuite_name == other.testsuite_name and self.testcase_name == other.testcase_name \
                   and self.testcase_classname == other.testcase_classname
        return False

    def __hash__(self):
        return hash((self.testsuite_name, self.testcase_name, self.testcase_classname))

    def __repr__(self):
        return f"TestFailure(suite={self.testsuite_name}, case={self.testcase_name}, class={self.testcase_classname})"


def get_test_failures_from_file(path_to_filename: Path) -> set[TestFailure]:
    """Parses the given .xml test report and creates TestFailures for each <testcase> with a <failure> or <error> tag"""
    # TODO: can a report contain more than one testsuite (this code assumes not)? What happens then?
    assert os.path.isfile(path_to_filename) and path_to_filename.suffix == ".xml"
    try:
        tree = ElementTree.parse(path_to_filename)
    except ElementTree.ParseError as e:
        print(e)
        return set()

    root = tree.getroot()
    testsuite_name = root.get("name")
    testcases = root.findall("testcase")

    failures = set()
    for testcase in testcases:
        testcase_name = testcase.get("name")
        testcase_classname = testcase.get("classname")
        failure_subtag = testcase.find("failure")
        error_subtag = testcase.find("error")
        skipped_subtag = testcase.find("skipped")

        failure_type = ""
        if failure_subtag is not None:
            failure_type = "failure"
        elif error_subtag is not None:
            failure_type = "error"
        elif skipped_subtag is not None:
            failure_type = "skipped"
        if failure_type:
            failures.add(TestFailure(testsuite_name, testcase_name, testcase_classname, failure_type))

    return failures


def at_least_one_passing_test(path_to_dir: Path) -> bool:
    """Parses test results from the given surefire-reports directory."""
    if os.path.isdir(path_to_dir):
        results = get_test_results_from_dir(path_to_dir)
        return True if results['pass'] else False
    return False


def get_test_results_from_file(path_to_filename: Path) -> dict:
    """returns dict of tests results: {'pass': int, 'failure': int, 'error': int, 'skipped': int}"""
    assert os.path.isfile(path_to_filename) and path_to_filename.suffix == ".xml"
    try:
        tree = ElementTree.parse(path_to_filename)
    except ElementTree.ParseError as e:
        print(e)
        # This happens for orphan-oss/ognl/target/surefire-reports/TEST-org.ognl.test.NumericConversionTest.xml
        return {}

    root = tree.getroot()
    testcases = root.findall("testcase")
    results = {
        'pass': 0,
        'failure': 0,
        'error': 0,
        'skipped': 0,
    }

    for testcase in testcases:
        failure_subtag = testcase.find("failure")
        error_subtag = testcase.find("error")
        skipped_subtag = testcase.find("skipped")

        if failure_subtag is not None:
            results['failure'] += 1
        elif error_subtag is not None:
            results['error'] += 1
        elif skipped_subtag is not None:
            results['skipped'] += 1
        else:
            results['pass'] += 1

    return results


def get_test_results_from_dir(path_to_dir: Path) -> dict:
    """Parses test results from the given surefire-reports directory."""
    assert os.path.isdir(path_to_dir)
    overall_results = {
        'pass': 0,
        'failure': 0,
        'error': 0,
        'skipped': 0,
    }
    for filename in os.listdir(path_to_dir):
        if filename.endswith(".xml"):
            path_to_filename = pathlib.Path.joinpath(path_to_dir, filename)
            single_results = get_test_results_from_file(path_to_filename)
            if not single_results:
                continue
            overall_results['pass'] += single_results['pass']
            overall_results['failure'] += single_results['failure']
            overall_results['error'] += single_results['error']
            overall_results['skipped'] += single_results['skipped']
    return overall_results


def get_test_failures_from_dir(path_to_dir: Path) -> set[TestFailure]:
    """Parses TestFailures from the given surefire-reports directory."""
    print(f"get_test_results_from_dir with dir={path_to_dir}")
    assert os.path.isdir(path_to_dir)
    all_failures = set()
    for filename in os.listdir(path_to_dir):
        if filename.endswith(".xml"):
            path_to_filename = pathlib.Path.joinpath(path_to_dir, filename)
            all_failures.update(get_test_failures_from_file(path_to_filename))
    return all_failures
