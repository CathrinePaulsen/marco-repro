import filecmp
import pathlib
import shutil
from unittest.mock import patch, MagicMock

import lxml.etree as ET

from client import (parse_missing, insert_deps, get_text_of_child, dependencies_are_equal, replace_dep,
                    replace_softvers, get_softver_deps, clean_effective_pom)
from core import namespace

TEST_RESOURCES = pathlib.Path(__file__).parent.parent.resolve() / "test_resources"


def get_compatible_version_range_mock(dep: ET.Element, properties: dict):
    """Given a <dependency>-element, query the server for the list of compatible versions, convert the list
    into a valid Maven range spec and return it."""
    g = get_text_of_child(dep, "groupId")
    a = get_text_of_child(dep, "artifactId")
    v = get_text_of_child(dep, "version")
    v = properties.get(v, v)
    ranges = {
        "com.example.libB:libB:1": "[1]",
        "com.example.libB:libB:2": "[2]",
        "com.example.libA:libA:1": "[1]",
        "com.example.libC:libC:1": "[1]",
        "com.example.libC:libC:2": "[1,2]",
        "org.yaml:snakeyaml:1.33": "[1.33, 1.4]",
        "com.google.code.gson:gson:2.10.1": "[2.10.1]",
        "com.aventstack:extentreports:5.1.1": "[5.1.1]",
        "com.fasterxml.jackson.core:jackson-databind:2.17.0": "[2.17.0]",
        "com.fasterxml.jackson.core:jackson-core:2.17.0": "[2.17.0, 2.17.1]",
        "net.datafaker:datafaker:2.1.0": "[2.1.0]",
    }
    return ranges.get(f'{g}:{a}:{v}', None)


def get_project_path(project: str):
    return TEST_RESOURCES / "example_maven_projects" / "range_replacement_example" / project


def create_dependency_element(group_id, artifact_id, version, ns=namespace['maven']):
    ns = ns if ns else ""

    dependency = ET.Element(f"{{{ns}}}dependency")

    group_id_element = ET.Element(f"{{{ns}}}groupId")
    group_id_element.text = group_id
    dependency.append(group_id_element)

    artifact_id_element = ET.Element(f"{{{ns}}}artifactId")
    artifact_id_element.text = artifact_id
    dependency.append(artifact_id_element)

    version_element = ET.Element(f"{{{ns}}}version")
    version_element.text = version
    dependency.append(version_element)

    return dependency


def test_dependencies_are_equal():
    x = create_dependency_element("com.example.appD", "appD", "1")
    y = create_dependency_element("com.example.appD", "appD", "1")
    assert dependencies_are_equal(x, y)


def test_dependencies_are_not_equal():
    x = create_dependency_element("com.example.appD", "appD", "1")
    y = create_dependency_element("com.example.appD", "appD", "2")
    assert not dependencies_are_equal(x, y)

    y = create_dependency_element("com.example.appC", "appC", "1")
    assert not dependencies_are_equal(x, y)


def test_parse_missing_single():
    out = TEST_RESOURCES / "analyze_output_single.txt"
    with open(out, 'r') as f:
        bytes = f.read()

    mock = MagicMock()
    mock.stdout = bytes

    actual_missing_deps = parse_missing(mock)
    expected_missing_deps = [
        create_dependency_element("com.example.appC", "appC", "1", ns=None),
    ]

    for (actual_dep, expected_dep) in zip(actual_missing_deps, expected_missing_deps):
        assert dependencies_are_equal(actual_dep, expected_dep)


def test_parse_missing_multiple():
    out = TEST_RESOURCES / "analyze_output_double.txt"
    with open(out, 'r') as f:
        bytes = f.read()

    mock = MagicMock()
    mock.stdout = bytes

    actual_missing_deps = parse_missing(mock)
    expected_missing_deps = [
        create_dependency_element("com.example.appD", "appD", "1", ns=None),
        create_dependency_element("com.example.appC", "appC", "1", ns=None),
    ]

    for (actual_dep, expected_dep) in zip(actual_missing_deps, expected_missing_deps):
        assert dependencies_are_equal(actual_dep, expected_dep)


def test_insert_deps_single():
    pomfile = ET.parse(TEST_RESOURCES / "simple_pom.xml")
    actual_expanded_pomfile = TEST_RESOURCES / "simple_pom_expanded_actual.xml"
    expected_expanded_pomfile = TEST_RESOURCES / "simple_pom_expanded.xml"
    deps = [
        create_dependency_element("com.example.appC", "appC", "1", ns=None),
    ]
    insert_deps(deps, pomfile, actual_expanded_pomfile)

    assert filecmp.cmp(actual_expanded_pomfile, expected_expanded_pomfile, shallow=False)

    pathlib.Path.unlink(actual_expanded_pomfile)


def test_insert_deps_multiple():
    pomfile = ET.parse(TEST_RESOURCES / "simple_pom.xml")
    actual_expanded_pomfile = TEST_RESOURCES / "simple_pom_multiple_expanded_actual.xml"
    expected_expanded_pomfile = TEST_RESOURCES / "simple_pom_multiple_expanded.xml"
    deps = [
        create_dependency_element("com.example.appC", "appC", "1", ns=None),
        create_dependency_element("com.example.appD", "appD", "1", ns=None),
    ]
    insert_deps(deps, pomfile, actual_expanded_pomfile)

    assert filecmp.cmp(actual_expanded_pomfile, expected_expanded_pomfile, shallow=False)

    pathlib.Path.unlink(actual_expanded_pomfile)


def test_replace_dep_single():
    pomfile = ET.parse(TEST_RESOURCES / "simple_pom.xml")
    actual_expanded_pomfile = TEST_RESOURCES / "simple_pom_range_expanded_actual.xml"
    expected_expanded_pomfile = TEST_RESOURCES / "simple_pom_range_expanded.xml"
    dep = create_dependency_element("com.example.appB", "appB", "1")
    range = "[1,3]"

    print("test input dep:")
    print(get_text_of_child(dep, "groupId"))
    print(get_text_of_child(dep, "artifactId"))
    print(get_text_of_child(dep, "version"))

    replace_dep(dep, range, pomfile, {}, actual_expanded_pomfile)

    assert filecmp.cmp(actual_expanded_pomfile, expected_expanded_pomfile, shallow=False)

    pathlib.Path.unlink(actual_expanded_pomfile)


def test_replace_softvers_multiple():
    new_pom_path = get_project_path("app") / "pom.xml"
    old_pom_path = get_project_path("app") / "pom_old.xml"
    expected_pom_path = get_project_path("app") / "pom_expected.xml"

    with patch('client.get_compatible_version_range', wraps=get_compatible_version_range_mock):
        replace_softvers(ET.parse(new_pom_path), ET.parse(new_pom_path), new_pom_path)

    assert filecmp.cmp(new_pom_path, expected_pom_path, shallow=False)

    shutil.copy(old_pom_path, new_pom_path)   # Cleanup


def test_get_softver_deps_0():
    pomfile = ET.parse(TEST_RESOURCES / "simple_pom_with_management.xml")
    actual_softvers, _ = get_softver_deps(pomfile, pomfile)
    expected_softvers = [
        create_dependency_element("com.example.libB", "libB", "1"),
        create_dependency_element("com.example.libC", "libC", "2"),
    ]

    for (actual_softvers, expected_softvers) in zip(actual_softvers, expected_softvers):
        assert dependencies_are_equal(actual_softvers, expected_softvers)


def test_replace_softvers_management():
    old_pom_path = TEST_RESOURCES / "simple_pom_with_management.xml"
    to_expand_pom_path = TEST_RESOURCES / "simple_pom_with_management_to_expand.xml"
    expected_pom_path = TEST_RESOURCES / "simple_pom_with_management_expanded.xml"

    # Setup
    shutil.copy(old_pom_path, to_expand_pom_path)

    with patch('client.get_compatible_version_range', wraps=get_compatible_version_range_mock):
        replace_softvers(ET.parse(to_expand_pom_path), ET.parse(to_expand_pom_path), to_expand_pom_path)

    assert filecmp.cmp(to_expand_pom_path, expected_pom_path, shallow=False)


def test_replace_softvers_properties_1():
    old_pom_path = TEST_RESOURCES / "simple_pom_with_properties.xml"
    to_expand_pom_path = TEST_RESOURCES / "simple_pom_with_properties_to_expand.xml"
    expected_pom_path = TEST_RESOURCES / "simple_pom_with_properties_expanded.xml"

    # Setup
    shutil.copy(old_pom_path, to_expand_pom_path)

    with patch('client.get_compatible_version_range', wraps=get_compatible_version_range_mock):
        replace_softvers(ET.parse(to_expand_pom_path), ET.parse(to_expand_pom_path), to_expand_pom_path)

    assert filecmp.cmp(to_expand_pom_path, expected_pom_path, shallow=False)


def test_clean_effective_pom():
    dirty_pom_path = TEST_RESOURCES / "effective_pom_dirty.xml"
    to_clean_pom_path = TEST_RESOURCES / "effective_pom_to_clean.xml"
    cleaned_pom_path = TEST_RESOURCES / "effective_pom_clean.xml"

    # Setup
    shutil.copy(dirty_pom_path, to_clean_pom_path)

    clean_effective_pom(to_clean_pom_path)

    assert filecmp.cmp(to_clean_pom_path, cleaned_pom_path, shallow=False)


def test_replace_softvers_properties_effective_pom():
    old_pom_path = TEST_RESOURCES / "effective-pom_pom.xml"
    effective_pom_path = TEST_RESOURCES / "effective-pom.xml"
    to_expand_pom_path = TEST_RESOURCES / "effective-pom_pom_to_expand.xml"
    expected_pom_path = TEST_RESOURCES / "effective-pom_pom_expanded.xml"

    # Setup
    shutil.copy(old_pom_path, to_expand_pom_path)

    with patch('client.get_compatible_version_range', wraps=get_compatible_version_range_mock):
        replace_softvers(ET.parse(to_expand_pom_path), ET.parse(effective_pom_path), to_expand_pom_path)

    assert filecmp.cmp(to_expand_pom_path, expected_pom_path, shallow=False)


def test_get_softver_deps_properties_1():
    pomfile = ET.parse(TEST_RESOURCES / "simple_pom_with_properties.xml")
    actual_softvers, _ = get_softver_deps(pomfile, pomfile)
    expected_softvers = [
        create_dependency_element("com.example.libB", "libB", "1"),
        create_dependency_element("org.yaml", "snakeyaml", "${snakeyaml.version}"),
        create_dependency_element("com.google.code.gson", "gson", "${gson.version}"),
    ]

    for (actual_softvers, expected_softvers) in zip(actual_softvers, expected_softvers):
        assert dependencies_are_equal(actual_softvers, expected_softvers)


def test_get_softver_deps_properties_2():
    pomfile = ET.parse(TEST_RESOURCES / "simple_pom_with_properties_2.xml")
    actual_softvers, _ = get_softver_deps(pomfile, pomfile)
    expected_softvers = [
        create_dependency_element("com.example.libB", "libB", "1"),
        create_dependency_element("com.google.code.gson", "gson", "${gson.version}"),
    ]

    for (actual_softvers, expected_softvers) in zip(actual_softvers, expected_softvers):
        assert dependencies_are_equal(actual_softvers, expected_softvers)


def test_replace_softvers_properties_and_scope():
    old_pom_path = TEST_RESOURCES / "simple_pom_with_properties_and_scope.xml"
    to_expand_pom_path = TEST_RESOURCES / "simple_pom_with_properties_and_scope_to_expand.xml"
    expected_pom_path = TEST_RESOURCES / "simple_pom_with_properties_and_scope_expanded.xml"

    # Setup
    shutil.copy(old_pom_path, to_expand_pom_path)

    with patch('client.get_compatible_version_range', wraps=get_compatible_version_range_mock):
        replace_softvers(ET.parse(to_expand_pom_path), ET.parse(to_expand_pom_path), to_expand_pom_path)

    assert filecmp.cmp(to_expand_pom_path, expected_pom_path, shallow=False)
