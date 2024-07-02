from core.dependency_tree import DependencyTree, parse, TreeComparator
from pathlib import Path
from unittest.mock import patch

RESOURCE_PATH = Path(__file__).parent.parent.resolve() / "test_resources" / "dep_trees"
TEST_M2 = Path(__file__).parent.parent.resolve() / "test_resources" / "m2"


def test_change_rate_equal():
    input_file = RESOURCE_PATH / "input2.txt"
    tree1: DependencyTree = parse(input_file)
    tree2: DependencyTree = parse(input_file)
    comparator = TreeComparator(tree1, tree2)

    assert comparator.change_rate == 0


def test_change_rate_one_upgrade():
    input_file1 = RESOURCE_PATH / "input2.txt"
    input_file2 = RESOURCE_PATH / "input.txt"
    tree1: DependencyTree = parse(input_file1)
    tree2: DependencyTree = parse(input_file2)
    comparator = TreeComparator(tree1, tree2)

    assert comparator.change_rate == (1/12)


def test_change_rate_big_upgrade():
    input_file1 = RESOURCE_PATH / "input3.txt"
    input_file2 = RESOURCE_PATH / "input.txt"
    tree1: DependencyTree = parse(input_file1)
    tree2: DependencyTree = parse(input_file2)
    comparator = TreeComparator(tree1, tree2)

    assert comparator.change_rate == (31/12)


def test_change_rate_one_downgrade():
    input_file1 = RESOURCE_PATH / "input.txt"
    input_file2 = RESOURCE_PATH / "input2.txt"
    tree1: DependencyTree = parse(input_file1)
    tree2: DependencyTree = parse(input_file2)
    comparator = TreeComparator(tree1, tree2)

    assert comparator.change_rate == (1/12)


def test_change_rate_big_downgrade():
    input_file1 = RESOURCE_PATH / "input.txt"
    input_file2 = RESOURCE_PATH / "input3.txt"
    tree1: DependencyTree = parse(input_file1)
    tree2: DependencyTree = parse(input_file2)
    comparator = TreeComparator(tree1, tree2)

    assert comparator.change_rate == (31/12)


def test_difference_none():
    input_file1 = RESOURCE_PATH / "input.txt"
    input_file2 = RESOURCE_PATH / "input3.txt"
    tree1: DependencyTree = parse(input_file1)
    tree2: DependencyTree = parse(input_file2)
    comparator = TreeComparator(tree1, tree2)

    assert comparator.difference == (0, 0)


def test_difference_additions_and_subtractions():
    input_file1 = RESOURCE_PATH / "input.txt"
    input_file2 = RESOURCE_PATH / "input4.txt"
    tree1: DependencyTree = parse(input_file1)
    tree2: DependencyTree = parse(input_file2)
    comparator = TreeComparator(tree1, tree2)

    assert comparator.difference == (1, 1)


def test_overlapping():
    input_file1 = RESOURCE_PATH / "input.txt"
    input_file2 = RESOURCE_PATH / "input4.txt"
    tree1: DependencyTree = parse(input_file1)
    tree2: DependencyTree = parse(input_file2)
    comparator = TreeComparator(tree1, tree2)

    assert comparator.overlapping == (12, 11)


def test_version_changes():
    input_file1 = RESOURCE_PATH / "input.txt"
    input_file2 = RESOURCE_PATH / "input4.txt"
    tree1: DependencyTree = parse(input_file1)
    tree2: DependencyTree = parse(input_file2)
    comparator = TreeComparator(tree1, tree2)

    downgrades = 0
    downgrade_steps = 0
    upgrades = 1
    upgrade_steps = 31
    assert comparator.version_changes == (downgrades, downgrade_steps, upgrades, upgrade_steps)


def mocked_create_pom_path(group_id: str, artifact_id: str, version: str, m2_path: Path) -> Path:
    # Define the custom m2 path
    custom_m2_path = TEST_M2

    # Replicate the behavior of create_pom_path with the custom m2 path
    g_slashes = group_id.replace(".", "/")
    print(f"custom m2 = {custom_m2_path}")
    return custom_m2_path / g_slashes / artifact_id / version / f"{artifact_id}-{version}.pom"


def test_replacement_rate_and_replacements():
    # TODO: still cant figure out how to get this test to work
    #   for now you need to change the m2_path in dependency_tree to the test path
    #   before running the test
    input_file = RESOURCE_PATH / "input.txt"
    with patch('core.dependency_tree.M2_PATH', TEST_M2), \
            patch('core.dependency_tree.create_pom_path', new=mocked_create_pom_path), \
            patch('rq5.LOCAL_M2', TEST_M2):
        tree1: DependencyTree = parse(input_file)
        tree2: DependencyTree = parse(input_file)
        comparator = TreeComparator(tree1, tree2, repo=RESOURCE_PATH.parent.resolve() / "repo")

    assert comparator.replacements == 3
    assert comparator.replacement_rate == 3/12
