"""Given a Maven project, expand its pom twice:
first with undeclared used dependencies, second expand SoftVers with ranges."""
import argparse
import os.path
import pathlib
import subprocess

import requests
from lxml import etree as ET

from core import get_available_versions, namespace, dependencies_are_equal, get_text_of_child

RANGE_CONVERSION_SCRIPT = pathlib.Path(__file__).parent.resolve() / "range_converter.py"
SERVER_URL = "http://127.0.0.1:5000"


def convert_compat_list_to_range(g: str, a: str, compatible_versions: list[str], use_remote=False):
    """Calls the range converter which uses Maven's ComparableVersion via Jython."""
    available_versions = get_available_versions(g, a, use_remote=use_remote)
    # Need to call range converter via subprocess as it uses a different python environment (Python 2)
    output = subprocess.run(["jython", RANGE_CONVERSION_SCRIPT, "-a"] + available_versions +
                            ["-c"] + compatible_versions, stdout=subprocess.PIPE)
    print(output)
    return output.stdout


def is_softver(v: str) -> bool:
    range_characters = ["[", "]", "(", ")", ","]
    for char in range_characters:
        if char in v:
            return False
    return True


def version_is_property(version: str):
    """
    Returns True if the text in a version tag references a property eg <version>${junit.version}</version>
    """
    if version[:2] == "${" and version[-1] == "}":
        return True
    return False


def parse_properties_to_dict(tree: ET.Element):
    """
    Parses the list of <properties></properties> in the POM and stores the result in a dict where the key is the
    tag name and the value is the tag contents.
    """
    properties = tree.find(".//maven:properties", namespace)
    dict = {}
    if properties is not None:
        for property in properties:
            if property.tag is ET.Comment:
                continue  # Skip comment nodes
            name = f"${{{ET.QName(property).localname}}}"
            dict[name] = property.text
    return dict


def replace_property(pom: ET.Element, replace_by: str, property: str, properties: dict) -> str:
    """Given a parsed POM, replace the given property value with the replace_by value."""
    property_name = property[2:-1]
    property_tag = pom.find(f".//maven:properties", namespace).find(f"maven:{property_name}", namespace)
    if property_tag is not None and property_tag.text is not None:
        previous_value = property_tag.text
        if properties[property] != previous_value:
            # We already replaced this property
            # TODO: get union of what is was previously replaced by, and what we want to replace it with now
            return properties[property]
        property_tag.text = replace_by
        property_tag.set("replaced_value", previous_value)
        return previous_value


def replace_dep(soft_dep: ET.Element, range: str, pom: ET.Element, properties: dict, write_to=None) -> bool:
    """Given a <dependency>-element, a range, and a pom, replace the content of the <version> subtag with the range."""
    replaced = False

    dependencies = pom.findall(".//maven:dependency", namespaces=namespace)
    for dep in dependencies:
        if dependencies_are_equal(dep, soft_dep):
            version_tag = dep.find(f".//maven:version", namespaces=namespace)
            # Commented out because putting a range in a property is not supported by Maven 3.9.6,
            # so we replace the property reference by the range directly instead
            # if version_is_property(version_tag.text):
            #     replaced_value = replace_property(pom, range, version_tag.text, properties)
            # else:
            #     replaced_value = version_tag.text
            #     version_tag.text = range
            replaced_value = version_tag.text
            version_tag.text = range
            if replaced_value:
                version_tag.set("replaced_value", replaced_value)
            else:
                version_tag.set("replaced_value", "unknown")
            replaced = True

    if write_to:  # To make testing easier
        pom.write(write_to, encoding='utf-8')

    return replaced


def get_compatible_version_list(g: str, a: str, v: str):
    """Query server for, and return, the pre-calculated compatible versions of GAV"""
    query = f"{SERVER_URL}/compatibilities/{g}:{a}:{v}"
    response = requests.get(query)
    if response.status_code == 200:
        return response.json()['compatible_versions']
    else:
        return None


def get_compatible_version_range(dep: ET.Element, properties: dict):
    """Given a <dependency>-element, query the server for the list of compatible versions, convert the list
    into a valid Maven range spec and return it."""
    g = get_text_of_child(dep, "groupId")
    a = get_text_of_child(dep, "artifactId")
    v = get_text_of_child(dep, "version")
    if version_is_property(v) and properties:
        v = properties.get(v, "")
    if not v:
        return None
    compatible_versions = get_compatible_version_list(g, a, v)
    if not compatible_versions:
        return None
    return convert_compat_list_to_range(g, a, compatible_versions).decode('utf-8')


def get_softver_deps(pom: ET.Element, effective_pom: ET.Element) -> (list[ET.Element], dict):
    """Returns a list of <dependency>-elements which have a <version>-tag that is a soft constraint."""
    dependencies = pom.findall(".//maven:dependency", namespace)
    properties = parse_properties_to_dict(effective_pom)
    softvers = []
    for dep in dependencies:
        v = get_text_of_child(dep, "version")
        scope = get_text_of_child(dep, "scope")
        scope = scope if scope else "compile"  # Non-specified scope defaults to "compile"
        if scope != "compile" and scope != "runtime":
            continue  # We only replace compile/runtime dependencies
        if version_is_property(v) and properties:
            v = properties.get(v, "")
        if v and is_softver(v):
            softvers.append(dep)
    return softvers, properties


def replace_softvers(pom: ET.Element, effective_pom: ET.Element, write_to=None):
    """Replaces all declared soft version constraints with their compatible ranges."""
    soft_deps, properties = get_softver_deps(pom, effective_pom)
    num_replaced = 0
    for dep in soft_deps:
        range = get_compatible_version_range(dep, properties)
        if not range:
            continue
        range = range.replace("\n", "")
        if not range:
            continue
        g = get_text_of_child(dep, "groupId")
        a = get_text_of_child(dep, "artifactId")
        v = get_text_of_child(dep, "version")
        replaced = replace_dep(dep, range, pom, properties)
        print(f"Replaced {g}:{a}:{v} with {g}:{a}:{range}")
        num_replaced += 1 if replaced else 0

    if write_to:  # To make testing easier
        pom.write(write_to, encoding='utf-8')

    return num_replaced


def insert_deps(deps: list[ET.Element], pom: ET.Element, write_to=None):
    """Append the given dependencies to the pom's <dependencies> tag."""
    num_inserted = 0
    dependencies_tag = pom.find('.//maven:dependencies', namespace)
    if dependencies_tag is None:
        # No dependencies to replace
        raise NotImplementedError("<dependencies> tag not found in the XML.")
    for dep in deps:
        version_tag = dep.find("version")  # Does not have namespace
        version_tag.set("inserted", "true")
        dependencies_tag.append(dep)
        num_inserted += 1

    if write_to:  # To make testing easier
        ET.indent(pom, space="  ", level=0)
        pom.write(write_to, encoding='utf-8')

    return num_inserted


def parse_missing(output: subprocess.CompletedProcess) -> list[ET.Element]:
    """Returns the XML Element representing the missing dependencies."""
    start = f"[INFO] Add the following to your pom to correct the missing dependencies:"
    grab_line = False
    # Need to wrap the missing dependencies in parent tag <dependencies></dependencies> otherwise XML parsing fails
    xml_strings = ["<dependencies>"]

    for line in output.stdout.splitlines():
        if line.startswith(start):
            grab_line = True

        elif grab_line:
            if line.startswith("[INFO]"):
                continue
            else:
                xml_strings.append(line)

    xml_strings.append("</dependencies>")

    root = ET.fromstringlist(xml_strings)

    missing_deps = []
    for dep in root.findall("dependency"):
        scope_tag = dep.find("scope")
        scope = scope_tag.text if scope_tag is not None and scope_tag.text is not None else "compile"
        if scope == "compile" or scope == "runtime":
            # Will only insert missing compile or runtime dependencies
            missing_deps.append(dep)

    return missing_deps


def expand_pom(project: pathlib.Path, pom: ET.Element, pom_path=None):
    old_dir = os.getcwd()
    os.chdir(project)
    if pom_path:
        commands = ["mvn", "dependency:analyze-only", "-DoutputXML", "-f", pom_path]
    else:
        commands = ["mvn", "dependency:analyze-only", "-DoutputXML"]
    output = subprocess.run(commands, stdout=subprocess.PIPE,
                            universal_newlines=True)
    missing_deps: list[ET.Element] = parse_missing(output)
    num_expansions = 0 if len(missing_deps) == 0 else insert_deps(missing_deps, pom)
    os.chdir(old_dir)
    return num_expansions


def clean_effective_pom(effective_pom_file: pathlib.Path):
    # Clean effective pom from unwanted generated input, only keep the xml bit (content between first < and last >)
    with open(effective_pom_file, 'r') as f:
        xml_content = f.read()
    # Find the index of the first '<' character
    start_index = xml_content.find('<')

    # Find the index of the last '>' character
    end_index = xml_content.rfind('>')

    # Extract the substring between the first '<' and last '>'
    filtered_xml = xml_content[start_index:end_index+1]

    # Write filtered XML content back to the file
    with open(effective_pom_file, "w") as file:
        file.write(filtered_xml)


def expand_and_replace(project_dir: pathlib.Path, pom_path=None):
    if not pom_path:
        pom_path = project_dir / "pom.xml"
    assert pathlib.Path.is_dir(project_dir)
    assert pathlib.Path.is_file(pom_path)
    effective_pom_path = project_dir / "effective_pom.xml"

    try:
        subprocess.run(["mvn", "help:effective-pom", "-f", pom_path, f"-Doutput=effective_pom.xml"]).check_returncode()
        # Clean effective pom from unwanted generated input, only keep the xml bit (content between first < and last >)
        clean_effective_pom(effective_pom_path)
    except subprocess.CalledProcessError as e:
        print(e)
        # If we for some reason cannot generate the effective-pom, then use the regular pom instead
        # e.g. where this error happens is in org.eclipse.sisu:org.eclipse.sisu.plexus:0.3.0.M1
        effective_pom_path = pom_path
    pom = ET.parse(pom_path)
    effective_pom = ET.parse(effective_pom_path)
    num_expansions = expand_pom(project_dir, pom)
    if num_expansions > 0:
        ET.indent(pom, space="  ", level=0)  # Fix indentation, will remove whitespace from file however
        pom.write(pom_path, encoding='utf-8')

    pom = ET.parse(pom_path)
    num_replacements = replace_softvers(pom, effective_pom)
    if num_replacements > 0:
        pom.write(pom_path, encoding='utf-8', xml_declaration=True)

    return num_expansions, num_replacements


def main():
    """
    Example: client-example path/to/maven/project
    """
    parser = argparse.ArgumentParser(description='POM Expander')
    parser.add_argument('path', type=str, help='path/to/maven/project')

    args = parser.parse_args()
    project_dir = pathlib.Path(args.path).resolve()

    print(f"Performing POM expansion on {project_dir}")
    confirm = input('Confirm (y/n)?: ')
    if confirm == "y":
        expansions, replacements = expand_and_replace(project_dir)
        print(f"Made {expansions} expansions, and {replacements} replacements")
    else:
        print(f"Aborted.")

