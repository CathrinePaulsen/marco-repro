from dataclasses import dataclass
# from rq5 import LOCAL_M2
from pathlib import Path
from typing import Self

import lxml.etree as ET

from core import get_available_versions, namespace, GAV
from server.config import path_to_repos
from server.test_failure import get_test_failures_from_dir

CONFLICT_LINE = "omitted for conflict with "
M2_PATH = Path("/home/cathrine/.m2/repository")
# TEST_M2 = Path(__file__).parent.parent.resolve() / "test_resources" / "m2"
# M2_PATH = TEST_M2  # Set M2_PATH to TEST_M2 when running tests... idk why but patch doens't apply recursively


class Omitted:
    pass


class Duplicate(Omitted):
    pass


@dataclass
class Conflict(Omitted):
    conflict_version: str


class Node:
    raw: str
    children: list[Self]
    parent: Self | None = None
    indentation: int
    omitted: Omitted | None = None
    gav: GAV
    pom_path: Path
    m2_path: Path
    __num_components: int

    def __init__(self, raw: str, indentation: int, parent: Self | None = None) -> None:
        self.raw = raw
        self.indentation = indentation
        self.parent = parent
        self.children = []
        self.parse()

    def parse(self) -> None:
        self.__parse_ommitted()
        self.__parse_gav()

    def add_child(self, child: Self) -> None:
        self.children.append(child)

    def get_root(self) -> Self:
        root = self
        while root.parent is not None:
            root = root.parent
        return root

    def get_parent(self, indentation: int) -> Self:
        root = self
        while root.parent is not None:
            if root.indentation == indentation:
                return root.parent
            root = root.parent
        raise IndexError

    def __repr__(self) -> str:
        return self.raw

    @property
    def depth(self) -> int:
        depth = 0
        root = self
        while root.parent is not None:
            root = root.parent
            depth += 1
        return depth

    @property
    def is_omitted(self) -> bool:
        return isinstance(self.omitted, Omitted)

    @property
    def is_root(self) -> bool:
        return not self.parent

    @property
    def __version_idx(self):
        if self.__num_components == 6:
            return 4
        return 3

    @property
    def __scope_idx(self):
        if self.__num_components == 5:
            return 4
        return 5

    def __get_dependency_string(self):
        """Parses a branch and returns a dependency string in the format
        {groupId}:{artifactId}:{type}:{classifier}:{version}:{scope}, where classifier may or may not be present."""
        # Remove tree formatting
        dep = self.raw
        dep = dep.replace("+- ", "").replace("\- ", "").replace("|  ", "").strip()
        # Remove encapsulating brackets
        if dep[0] == "(" and dep[-1] == ")":
            dep = dep[1:-1]
        return dep.split(' ')[0]

    def __parse_ommitted(self):
        if index := find(self.raw, CONFLICT_LINE):
            self.omitted = Conflict(self.raw[index + len(CONFLICT_LINE) : -2])
        elif "omitted for duplicate" in self.raw:
            self.omitted = Duplicate()

    def __parse_gav(self):
        components = self.__get_dependency_string().split(":")
        self.__num_components = len(components)
        assert self.__num_components in range(4, 7)
        scope = "" if self.is_root else components[self.__scope_idx]
        self.gav = GAV(group_id=components[0], artifact_id=components[1],
                       version=components[self.__version_idx], scope=scope)

    @property
    def m2_path(self):
        g_slashes = self.gav.group_id.replace(".", "/")
        return M2_PATH / g_slashes / self.gav.artifact_id / self.gav.version

    @property
    def pom_path(self):
        return self.m2_path / f"{self.gav.artifact_id}-{self.gav.version}.pom"


def create_pom_path(group_id: str, artifact_id: str, version: str, m2_path: Path) -> Path:
    """
    An m2 resource can then be found in:
        /path/to/.m2/repository/my/group/id/my.artifact.id/my.version/my.artifact.id.my-my.version.extension
    """
    g_slashes = group_id.replace(".", "/")
    return m2_path / g_slashes / artifact_id / version / f"{artifact_id}-{version}.pom"


class DependencyTree:
    root: Node
    nodes = list[Node]
    resolved_nodes = list[Node]
    omitted_nodes = list[Node]
    test_reports: Path

    def __init__(self, root: Node, nodes: list[Node]):
        self.root = root
        self.nodes = nodes
        self.resolved_nodes = [x for x in nodes if not x.is_omitted]
        self.omitted_nodes = [x for x in nodes if x.is_omitted]


def parse(filename: Path) -> DependencyTree:
    node: Node | None = None
    indentation: int = -1
    nodes = []

    with open(filename, "r") as input_file:
        for line in input_file:
            if node is None:
                node = Node(line, indentation)
                continue

            try:
                new_indentation = line.index("+-")
            except ValueError:
                new_indentation = line.index("\\-")

            line = line[new_indentation + 3 :]
            if new_indentation > indentation:
                # Child
                node = add_node(node, line, new_indentation)
            elif new_indentation == indentation:
                # Sibling
                node = add_node(node.parent, line, new_indentation)
            else:
                # Uncle
                node = add_node(node.get_parent(new_indentation), line, new_indentation)
            nodes.append(node)
            indentation = new_indentation

    return DependencyTree(node.get_root(), nodes)


def add_node(parent: Node, line: str, indentation: int) -> Node:
    new_node = Node(line, indentation, parent)
    parent.add_child(new_node)
    return new_node


def find(line: str, substring: str) -> int:
    try:
        return line.index(substring)
    except ValueError:
        return 0


class TreeComparator:
    old_tree: DependencyTree
    new_tree: DependencyTree
    repo: Path

    def __init__(self, old_tree: DependencyTree, new_tree: DependencyTree, repo=None):
        self.old_tree = old_tree
        self.new_tree = new_tree
        self.repo = repo
        self.old_test_reports = path_to_repos / self.repo / "original_surefire-reports" if repo else None
        self.new_test_reports = path_to_repos / self.repo / "new_surefire-reports" if repo else None

    def _node_has_matching_ga_in_list(self, node: Node, node_list: list[Node]):
        for other in node_list:
            if (node.gav.group_id, node.gav.artifact_id) == (other.gav.group_id, other.gav.artifact_id):
                return True
        return False

    @property
    def overlapping(self) -> (int, int):
        """
        Returns a tuple containing:
            1) the total number of resolved dependencies after replacement,
            2) the number of overlapping GAs in the resolved dependencies before and after replacement
        """
        overlapping = 0
        for old in self.old_tree.resolved_nodes:
            for new in self.new_tree.resolved_nodes:
                if (old.gav.group_id, old.gav.artifact_id) == (new.gav.group_id, new.gav.artifact_id):
                    overlapping += 1
        return len(self.new_tree.resolved_nodes), overlapping

    @property
    def difference(self) -> (int, int):
        """
        Returns a tuple containing:
            1) The number of additions in resolved dependencies after replacement
            2) The number of subtractions in resolved dependencies after replacement
        """
        additions = 0
        subtractions = 0
        for old in self.old_tree.resolved_nodes:
            subtractions += 0 if self._node_has_matching_ga_in_list(old, self.new_tree.resolved_nodes) else 1
        for new in self.new_tree.resolved_nodes:
            additions += 0 if self._node_has_matching_ga_in_list(new, self.old_tree.resolved_nodes) else 1
        return additions, subtractions

    @property
    def replacements(self) -> int:
        """
        Returns the number of resolved dependencies that originate from a replaced dependency declaration.
        """
        replaced_dependencies = 0
        for new in self.new_tree.resolved_nodes:
            node = new
            parent_pom = new.parent.pom_path
            if new.parent.is_root:
                # the project pom (root pom) is not installed in .m2, so must get that from repo
                parent_pom = self.repo / "pom.xml"
            replaced_dependencies += 1 if self._node_is_replaced_in_pom(parent_pom, node) else 0

        return replaced_dependencies

    @property
    def version_changes(self) -> (int, int):
        """
        Returns a 4-tuple containing:
            1) the total number of resolved dependencies that downgraded after replacement
            2) the sum of downgrade steps of the downgraded dependencies
            3) the total number of resolved dependencies that upgraded after replacement
            4) the sum of upgrade steps of the upgraded dependencies
        """
        num_downgrades = 0
        sum_downgrade_steps = 0
        num_upgrades = 0
        sum_upgrade_steps = 0
        for old in self.old_tree.resolved_nodes:
            for new in self.new_tree.resolved_nodes:
                if (old.gav.group_id, old.gav.artifact_id) == (new.gav.group_id, new.gav.artifact_id):
                    if old.gav.version != new.gav.version:
                        available_versions = get_available_versions(old.gav.group_id, old.gav.artifact_id)
                        old_idx = available_versions.index(old.gav.version)
                        new_idx = available_versions.index(new.gav.version)

                        if old_idx > new_idx:
                            num_downgrades += 1
                            sum_downgrade_steps += abs(old_idx - new_idx)
                        elif old_idx < new_idx:
                            num_upgrades += 1
                            sum_upgrade_steps += abs(old_idx - new_idx)

        return num_downgrades, sum_downgrade_steps, num_upgrades, sum_upgrade_steps

    @property
    def passes_test_suite(self):
        old_failures = get_test_failures_from_dir(self.old_test_reports)
        new_failures = get_test_failures_from_dir(self.new_test_reports)
        return old_failures - new_failures == set()

    @property
    def change_rate(self) -> float:
        change = 0
        count = 0
        for old in self.old_tree.resolved_nodes:
            for new in self.new_tree.resolved_nodes:
                if (old.gav.group_id, old.gav.artifact_id) == (new.gav.group_id, new.gav.artifact_id):
                    count += 1
                    if old.gav.version != new.gav.version:
                        available_versions = get_available_versions(old.gav.group_id, old.gav.artifact_id)
                        old_idx = available_versions.index(old.gav.version)
                        new_idx = available_versions.index(new.gav.version)
                        # Newest version is listed first, so freshness/distance becomes old_idx - new_idx
                        change += abs(old_idx - new_idx)
        return change / count

    def _node_is_replaced_in_pom(self, pomfile: Path, node: Node):
        try:
            pom = ET.parse(pomfile)
        except OSError as e:
            print(f"node={node}")
            print(f"node pom_path={node.pom_path}")
            print(f"parent={node.parent}")
            print(f"parent pom_path={node.parent.pom_path}")
            raise e
        dependency_tags = pom.findall('.//maven:dependency', namespace)

        # Return True if node is replaced in the current POM
        for dependency in dependency_tags:
            group_id = dependency.find("maven:groupId", namespace).text
            artifact_id = dependency.find("maven:artifactId", namespace).text
            version = dependency.find("maven:version", namespace)
            if (group_id, artifact_id) == (node.gav.group_id, node.gav.artifact_id):
                if version is not None:
                    if 'replaced_value' in version.attrib:
                        print(f"Found replacement in pom {pomfile.name} for dep {node.gav}")
                        return True

        # If node was not replaced in current POM, check the parent POM if there is one
        parent_tag = pom.find('.//maven:parent', namespace)
        if parent_tag is not None:
            try:
                parent_group_id = parent_tag.find("maven:groupId", namespace).text
                parent_artifact_id = parent_tag.find("maven:artifactId", namespace).text
                parent_version = parent_tag.find("maven:version", namespace).text
            except AttributeError as e:
                print(e)
                parent_group_id = None
                parent_artifact_id = None
                parent_version = None
            if (parent_group_id, parent_artifact_id, parent_version) != (None, None, None):
                parent_pom = create_pom_path(parent_group_id, parent_artifact_id, parent_version, m2_path=M2_PATH)
                return self._node_is_replaced_in_pom(parent_pom, node)

        # Return False if node was not found in the current POM or any of its parent POMs
        return False

    @property
    def replacement_rate(self) -> float:
        dependency_count = 0
        replaced_dependencies = 0
        for new in self.new_tree.resolved_nodes:
            node = new
            parent_pom = new.parent.pom_path
            if new.parent.is_root:
                # the project pom (root pom) is not installed in .m2, so must get that from repo
                parent_pom = self.repo / "pom.xml"
            replaced_dependencies += 1 if self._node_is_replaced_in_pom(parent_pom, node) else 0
            dependency_count += 1

        return replaced_dependencies / dependency_count

