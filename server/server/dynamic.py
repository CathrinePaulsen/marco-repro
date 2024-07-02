"""Module containing logic related to checking for dynamic compatibility between a base and a candidate by running
the base's tests on the source code of the candidate."""
import os
import pathlib
import subprocess
import tempfile

from lxml import etree as ET

from core import namespace, dependencies_are_equal, get_text_of_child
from server.exceptions import MavenSurefireTestFailedException, CandidateMavenTestTimeout
from server.template.base_template import BaseTemplate
from server.template.candidate_template import CandidateTemplate
from server.test_failure import get_test_failures_from_dir, TestFailure
from server.config import TEST_TIMEOUT


def dynamic_check(base: set[TestFailure], candidate: set[TestFailure]) -> bool:
    """
    Returns a boolean indicating whether the base and candidate are dynamically compatible based on the difference
    in passed/failed tests.
    Condition: A candidate is compatible with the base if the candidate did not fail/error any tests that were
    originally passing in the base.
    """
    return (candidate - base) == set()


def dynamically_compatible(base: BaseTemplate, cv: str, repo_name=None):
    """
    Given a base template, runs the base tests in the same "cleaned" environment as the candidates would.
    This is to prevent environment-related factors only affecting the candidate results to gain a more realistic
    baseline as tests relying on external components should now also fail in the base when external components are
    removed.
    :param base: BaseTemplate made from the base version of the GA
    :param cv: candidate version of the GA
    :return: True if candidate version is dynamically compatible with base version, False otherwise
    """
    # TODO: store baseline failures in metadata to avoid recomputation
    baseline = CandidateTemplate(base.group_id, base.artifact_id, base.version, repo_name=repo_name)
    candidate = CandidateTemplate(base.group_id, base.artifact_id, cv, repo_name=repo_name)
    base_failures = run_tests(base, baseline)  # Get baseline failures by running the base with itself
    # base_failures = get_test_failures_from_dir(base.target_path / "surefire-reports_BASE")  # TODO this would be more efficient, but needs testing => yep it broke everything please test before doing anything
    candidate_failures = run_tests(base, candidate)
    return dynamic_check(base_failures, candidate_failures)


def get_test_deps(pom: pathlib.Path, tag_name: str) -> list[ET.Element]:
    tree = ET.parse(pom)
    root = tree.getroot()
    tag = root.find(f".//maven:{tag_name}", namespace)
    if tag is None:
        return []
    dependencies = tag.findall(".//maven:dependency", namespaces=namespace)
    test_dependencies = []

    for dep in dependencies:
        scope = dep.find("maven:scope", namespaces=namespace)
        if scope is not None and scope.text == "test":
            test_dependencies.append(dep)

    return test_dependencies


def merge_dependencies_in_section(pom_base: pathlib.Path, pom_cand: pathlib.Path, root: ET.Element, section: str):
    assert section == "dependencies" or section == "dependencyManagement"

    dependencies_tag = root.find(f".//maven:{section}", namespace)
    if section == "dependencyManagement" and dependencies_tag:
        dependencies_tag = dependencies_tag.find("maven:dependencies", namespace)

    dependencies = dependencies_tag.findall("maven:dependency", namespace) if dependencies_tag is not None else []

    # Get the test dependencies of the base and candidate
    test_deps_base = get_test_deps(pom_base, section)
    test_deps_cand = get_test_deps(pom_cand, section)

    # Get diff in test dependencies
    base_deps_not_in_cand = [dep_base for dep_base in test_deps_base
                             if not any(dependencies_are_equal(dep_base, dep_cand) for dep_cand in test_deps_cand)]
    cand_deps_not_in_base = [dep_cand for dep_cand in test_deps_cand
                             if not any(dependencies_are_equal(dep_cand, dep_base) for dep_base in test_deps_base)]

    # Remove test dependencies only declared in candidate
    for dep in cand_deps_not_in_base:
        group_id = get_text_of_child(dep, "groupId")
        artifact_id = get_text_of_child(dep, "artifactId")
        version = get_text_of_child(dep, "version")
        for d in dependencies:
            if (group_id, artifact_id, version, "test") == \
                    (get_text_of_child(d, "groupId"), get_text_of_child(d, "artifactId"),
                     get_text_of_child(d, "version"), get_text_of_child(d, "scope")):
                parent = d.getparent()
                try:
                    parent.remove(d)
                except AttributeError:
                    pass  # This can happen if the same dependency is declared twice

    # Add test dependencies only declared in base
    for dep in base_deps_not_in_cand:
        if get_text_of_child(dep, "groupId") and get_text_of_child(dep, "artifactId") \
                and get_text_of_child(dep, "version"):
            dependencies_tag.insert(0, dep)


def merge_poms(pom_base: pathlib.Path, pom_cand: pathlib.Path, save_to_path: pathlib.Path):
    tree = ET.parse(pom_cand)
    root = tree.getroot()
    merge_dependencies_in_section(pom_base, pom_cand, root, "dependencies")
    merge_dependencies_in_section(pom_base, pom_cand, root, "dependencyManagement")
    tree.write(save_to_path, doctype='<?xml version="1.0" encoding="UTF-8"?>', encoding='UTF-8')


def run_tests(base: BaseTemplate, candidate: CandidateTemplate) -> set[TestFailure]:
    """Runs the base tests on the candidate code and returns the set of test failures."""
    old_dir = os.getcwd()

    # Store info in temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Made temp dir: {temp_dir}")
        temp_dir = pathlib.Path(temp_dir)
        assert os.path.isdir(temp_dir)

        # Copy base template target as target in temporary directory
        print(f"Copying {base.target_path} into {temp_dir}")
        subprocess.run(["cp", "-r", base.target_path, temp_dir])
        temp_target = pathlib.Path.joinpath(temp_dir, "target")
        assert os.path.isdir(temp_target)

        # Copy candidate template into temporary directory
        assert os.path.isfile(candidate.pom_path)
        merge_poms(base.pom_path, candidate.pom_path, save_to_path=temp_dir / "pom.xml")
        subprocess.run(["cp", "-r", candidate.target_path, temp_dir])

        # Run base tests on candidate and collect the results
        os.chdir(temp_dir)
        try:
            subprocess.run(["mvn", "surefire:test"], timeout=TEST_TIMEOUT)
        except subprocess.TimeoutExpired:
            os.chdir(old_dir)
            raise CandidateMavenTestTimeout(f"mvn surefire:test lasted more than {TEST_TIMEOUT}s")
        cand_test_reports_dir = pathlib.Path.joinpath(temp_target, "surefire-reports")
        if not os.path.isdir(cand_test_reports_dir):
            os.chdir(old_dir)
            raise MavenSurefireTestFailedException(f"Ran {base.tag_name} tests on {candidate.tag_name} source, "
                                                   f"but found no surefire-reports")
        test_failures = get_test_failures_from_dir(cand_test_reports_dir)
        os.chdir(old_dir)

        return test_failures
