import pathlib

import pytest

from server.exceptions import BaseJarNotFoundException, CandidateJarNotFoundException
from server.static import run_static_check, statically_compatible


def get_jar_paths():
    return [
        get_path_to_jar(1),
        get_path_to_jar(2),
        get_path_to_jar(3),
        get_path_to_jar(4),
    ]


def get_path_to_jar(v: int) -> pathlib.Path:
    return (pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "minimal" / f"dep-{v}" / "target" /
            f"dep-{v}.jar")


def test_always_passes():
    assert True


def test_statically_compatible_v1():
    jar_v1, jar_v2, jar_v3, jar_v4 = get_jar_paths()

    # v2 has added one function that was not in v1 => v2 is statically backwards compatible
    compatible = run_static_check(jar_v1, jar_v2)
    assert compatible
    # v3 has removed one function that was available in v1 => v3 is not statically backwards compatible
    compatible = run_static_check(jar_v1, jar_v3)
    assert not compatible
    # v4 has changed the behavior of one function in v1 => v4 is statically backwards compatible
    compatible = run_static_check(jar_v1, jar_v4)
    assert compatible


def test_statically_compatible_v2():
    jar_v1, jar_v2, jar_v3, jar_v4 = get_jar_paths()

    # v1 has one less function than v2 => v1 is not statically forwards compatible with v2
    compatible = run_static_check(jar_v2, jar_v1)
    assert not compatible
    # v3 has one less function than v2 => v3 is not statically backwards compatible with v2
    compatible = run_static_check(jar_v2, jar_v3)
    assert not compatible
    # v4 has changed the behavior of one function in v2 => v4 is statically backwards compatible with v2
    compatible = run_static_check(jar_v2, jar_v4)
    assert compatible


def test_statically_compatible_v3():
    jar_v1, jar_v2, jar_v3, jar_v4 = get_jar_paths()

    # v1 has one less function than v3 => v1 is not statically forwards compatible with v3
    compatible = run_static_check(jar_v3, jar_v1)
    assert not compatible
    # v2 has one additional function compared to v3 => v2 is statically forwards compatible with v3
    compatible = run_static_check(jar_v3, jar_v2)
    assert compatible
    # v4 has one additional function compared to v3 => v4 is statically backwards compatible with v3
    compatible = run_static_check(jar_v3, jar_v4)
    assert compatible


def test_statically_compatible_v4():
    jar_v1, jar_v2, jar_v3, jar_v4 = get_jar_paths()

    # v1 has one less function than v4 => v1 is not statically forwards compatible with v4
    compatible = run_static_check(jar_v4, jar_v1)
    assert not compatible
    # v2 has different behavior of one of the functions in v4 => v2 is statically forwards compatible with v4
    compatible = run_static_check(jar_v4, jar_v2)
    assert compatible
    # v3 has one less function than v4 => v3 is not statically forwards compatible with v4
    compatible = run_static_check(jar_v4, jar_v3)
    assert not compatible


def test_statically_compatible_lib_example():
    g = "com.fasterxml.jackson.core"
    a = "jackson-databind"
    v_2_16_0 = "2.16.0"
    v_2_16_1 = "2.16.1"
    v_nonsense = "asldkdjf"

    # 2.16.1 is backwards compatible with 2.16.0
    compatible = statically_compatible(g, a, v_2_16_0, v_2_16_1)
    assert compatible
    # 2.16.0 is not forwards compatible with 2.16.1 since 2.16.1 contains additional methods not in 2.16.0
    compatible = statically_compatible(g, a, v_2_16_1, v_2_16_0)
    assert not compatible

    # BaseJarNotFoundException is raised when the base jar cannot be found
    with pytest.raises(BaseJarNotFoundException):
        statically_compatible(g, a, v_nonsense, v_2_16_1)

    # CandidateJarNotFoundException is raised when the candidate jar cannot be found
    with pytest.raises(CandidateJarNotFoundException):
        statically_compatible(g, a, v_2_16_1, v_nonsense)


# Use to test individual static compatibility
def test_tt():
    g = "org.codehaus.plexus"
    a = "plexus-io"
    base = "3.2.0"
    cand = "3.3.1"

    # 2.16.1 is backwards compatible with 2.16.0
    compatible = statically_compatible(g, a, base, cand)
    print(f"{base} is statically compatible with {cand}? {compatible}")

    # 2.16.0 is not forwards compatible with 2.16.1 since 2.16.1 contains additional methods not in 2.16.0
    compatible = statically_compatible(g, a, cand, base)
    print(f"{cand} is statically compatible with {base}? {compatible}")
