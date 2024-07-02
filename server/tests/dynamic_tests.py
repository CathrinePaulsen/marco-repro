import filecmp
import pathlib
from unittest.mock import patch, MagicMock

import pytest
from tests.template import BASE_TEMPLATES_TEST_DIR, CAND_TEMPLATES_TEST_DIR, REPOS_TEST_DIR, cleanup_repo

from core import PomNotFoundException
from server.dynamic import dynamic_check, run_tests, merge_poms, get_test_deps
from server.template.base_template import BaseTemplate
from server.template.candidate_template import CandidateTemplate
from server.test_failure import get_test_failures_from_dir


def mock_template(v: int, type: str) -> MagicMock:
    if type != "base" and type != "cand":
        raise ValueError(f"type must be 'base' or 'cand', but was {type}")

    mock = MagicMock()
    mock.target_path = (pathlib.Path(__file__).parent.parent.resolve() / "test_resources" /
                        f"{type}_templates" / f"com.example.dep:dep:{v}" / "target")
    mock.pom_path = (pathlib.Path(__file__).parent.parent.resolve() / "test_resources" /
                     f"{type}_templates" / f"com.example.dep:dep:{v}" / "pom.xml")
    mock.tag_name = f"v{v}"
    return mock


def test_dynamic_check_lib_nonexistent():
    g = "com.fasterxml.jackson.core"
    a = "jackson-databind"

    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        with pytest.raises(PomNotFoundException):
            BaseTemplate(g, a, "aksldjfh")

    with patch('server.template.candidate_template.CAND_TEMPLATES_DIR', CAND_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        with pytest.raises(PomNotFoundException):
            CandidateTemplate(g, a, "aksldjfh")


def test_dynamic_check_lib_example1():
    g = "com.fasterxml.jackson.core"
    a = "jackson-databind"

    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        base_template_2_16_0 = BaseTemplate(g, a, "2.16.0")
        base_template_2_16_1 = BaseTemplate(g, a, "2.16.1")

    with patch('server.template.candidate_template.CAND_TEMPLATES_DIR', CAND_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        cand_template_2_16_0 = CandidateTemplate(g, a, "2.16.0")
        cand_template_2_16_1 = CandidateTemplate(g, a, "2.16.1")

    # CASE: base 2.16.0, cand 2.16.1
    # # 2.16.1 is backwards compatible with 2.16.0 as they pass the same test (same behavior from 2.16.0's perspective)
    baseline_fails = run_tests(base_template_2_16_0, cand_template_2_16_0)
    candidate_fails = run_tests(base_template_2_16_0, cand_template_2_16_1)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert compatible

    # CASE: base 2.16.1, cand 2.16.0
    # # 2.16.0 is not forwards compatible with 2.16.1 since 2.16.1 tests for behavior not included in 2.16.0
    baseline_fails = run_tests(base_template_2_16_1, cand_template_2_16_1)
    candidate_fails = run_tests(base_template_2_16_1, cand_template_2_16_0)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert not compatible

    cleanup_repo(base_template_2_16_0)


def test_dynamic_check_lib_example2():
    g = "com.fasterxml.jackson.core"
    a = "jackson-databind"

    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        base_template_2_16_0 = BaseTemplate(g, a, "2.16.0")
        base_template_2_16_0_rc = BaseTemplate(g, a, "2.16.0-rc1")

    with patch('server.template.candidate_template.CAND_TEMPLATES_DIR', CAND_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        cand_template_2_16_0 = CandidateTemplate(g, a, "2.16.0")
        cand_template_2_16_0_rc = CandidateTemplate(g, a, "2.16.0-rc1")

    # CASE: base 2.16.0, cand 2.16.0-rc1
    # 2.16.0-rc1 < 2.16.0 and fails 4 tests (+1 failure, +3 errors) originally passing in 2.16.0
    #   => 2.16.0-rc1 is not forwards compatible with 2.16.0
    baseline_fails = run_tests(base_template_2_16_0, cand_template_2_16_0)
    candidate_fails = run_tests(base_template_2_16_0, cand_template_2_16_0_rc)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert not compatible

    # CASE: base 2.16.0-rc1, cand 2.16.0
    # 2.16.0 > 2.16.0-rc1 and passes the same tests as 2.16.0-rc1
    #   => 2.16.0 is backwards compatible with 2.16.0-rc1
    baseline_fails = run_tests(base_template_2_16_0_rc, cand_template_2_16_0_rc)
    candidate_fails = run_tests(base_template_2_16_0_rc, cand_template_2_16_0)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert compatible

    cleanup_repo(base_template_2_16_0)


def test_dynamic_check_lib_example_2_15_0():
    g = "com.fasterxml.jackson.core"
    a = "jackson-databind"

    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        base_template_2_15_0 = BaseTemplate(g, a, "2.15.0")

    with patch('server.template.candidate_template.CAND_TEMPLATES_DIR', CAND_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        cand_template_2_15_0 = CandidateTemplate(g, a, "2.15.0")
        cand_template_2_15_1 = CandidateTemplate(g, a, "2.15.1")
        cand_template_2_15_2 = CandidateTemplate(g, a, "2.15.2")

    # 2.15.0 as base: 2 failures, 18 errors

    # CASE: base 2.15.0, cand 2.15.1
    # 2.15.0 < 2.15.1 but 2.15.1 has 5 more failures and 10 fewer errors than 2.15.0
    #   => 2.15.1 is not backwards compatible with 2.15.0
    baseline_fails = run_tests(base_template_2_15_0, cand_template_2_15_0)
    candidate_fails = run_tests(base_template_2_15_0, cand_template_2_15_1)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert not compatible

    # CASE: base 2.15.0, cand 2.15.2
    # 2.15.0 < 2.15.2 but 2.15.2 has 5 more failures and 10 fewer errors than 2.15.0
    #   => 2.15.2 is not backwards compatible with 2.15.0
    candidate_fails = run_tests(base_template_2_15_0, cand_template_2_15_2)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert not compatible


def test_dynamic_check_lib_example_2_15_1():
    g = "com.fasterxml.jackson.core"
    a = "jackson-databind"

    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        base_template_2_15_1 = BaseTemplate(g, a, "2.15.1")

    with patch('server.template.candidate_template.CAND_TEMPLATES_DIR', CAND_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        cand_template_2_15_0 = CandidateTemplate(g, a, "2.15.0")
        cand_template_2_15_1 = CandidateTemplate(g, a, "2.15.1")
        cand_template_2_15_2 = CandidateTemplate(g, a, "2.15.2")

    # 2.15.1 as base: 5 failures, 15 errors

    # CASE: base 2.15.1, cand 2.15.0
    # 2.15.1 > 2.15.0, 2.15.0 has 3 FEWER failures and 3 FEWER errors TODO: ehh? does this make sense?
    #   => 2.15.0 is not forwards compatible with 2.15.1(?)
    baseline_fails = run_tests(base_template_2_15_1, cand_template_2_15_1)
    candidate_fails = run_tests(base_template_2_15_1, cand_template_2_15_0)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert not compatible

    # CASE: base 2.15.1, cand 2.15.2
    # 2.15.2 > 2.15.1 and passes the same tests as 2.15.1
    #   => 2.15.2 is backwards compatible with 2.15.1
    candidate_fails = run_tests(base_template_2_15_1, cand_template_2_15_2)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert compatible


def test_dynamic_check_lib_example_2_15_2():
    g = "com.fasterxml.jackson.core"
    a = "jackson-databind"

    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        base_template_2_15_2 = BaseTemplate(g, a, "2.15.2")

    with patch('server.template.candidate_template.CAND_TEMPLATES_DIR', CAND_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        cand_template_2_15_0 = CandidateTemplate(g, a, "2.15.0")
        cand_template_2_15_1 = CandidateTemplate(g, a, "2.15.1")
        cand_template_2_15_2 = CandidateTemplate(g, a, "2.15.2")

    # 2.15.2 as base: 5 failures, 15 errors

    # CASE: base 2.15.2, cand 2.15.0
    # 2.15.2 > 2.15.0 but 2.15.0 has 3 FEWER failures and 3 FEWER errors  TODO: ehh? does this make sense?
    #   => 2.15.0 is not forwards compatible with 2.15.2(?)
    baseline_fails = run_tests(base_template_2_15_2, cand_template_2_15_2)
    candidate_fails = run_tests(base_template_2_15_2, cand_template_2_15_0)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert not compatible

    # CASE: base 2.15.2, cand 2.15.1
    # 2.15.1 < 2.15.2 and passes the same tests as 2.15.2
    #   => 2.15.1 is forwards compatible with 2.15.2(?)
    candidate_fails = run_tests(base_template_2_15_2, cand_template_2_15_1)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert not compatible


def test_run_tests_v1():
    t1 = mock_template(v=1, type="base")
    t2 = mock_template(v=2, type="cand")
    t3 = mock_template(v=3, type="cand")
    t4 = mock_template(v=4, type="cand")

    # v2 contains all functions under tests in v1 => v2 is backwards compatible with v1
    test_failures = run_tests(t1, t2)
    assert not test_failures
    # v3 is missing a function under test in v1 => v3 is not backwards compatible with v1
    test_failures = run_tests(t1, t3)
    assert test_failures
    # v4 changes a function's behavior which causes its v1 test to fail => v4 is not backwards compatible with v1
    test_failures = run_tests(t1, t4)
    assert test_failures


def test_run_tests_v2():
    t2 = mock_template(v=2, type="base")
    t1 = mock_template(v=1, type="cand")
    t3 = mock_template(v=3, type="cand")
    t4 = mock_template(v=4, type="cand")

    # v1 is missing a function under test in v2 => v1 is not forwards compatible with v2
    test_failures = run_tests(t2, t1)
    assert test_failures
    # v3 is missing a function under test in v2 => v3 is not backwards compatible with v2
    test_failures = run_tests(t2, t3)
    assert test_failures
    # v4 changes a function's behavior which causes its v2 test to fail => v4 is not backwards compatible with v2
    test_failures = run_tests(t2, t4)
    assert test_failures


def test_run_tests_v3():
    t3 = mock_template(v=3, type="base")
    t1 = mock_template(v=1, type="cand")
    t2 = mock_template(v=2, type="cand")
    t4 = mock_template(v=4, type="cand")

    # v1 is missing a function under test in v3 => v1 is not forwards compatible with v3
    test_failures = run_tests(t3, t1)
    assert test_failures
    # v2 contains all functions under test in v3 => v2 is forwards compatible with v3
    test_failures = run_tests(t3, t2)
    assert not test_failures
    # v4 contains all functions under test in v3 => v4 is backwards compatible with v3
    test_failures = run_tests(t3, t4)
    assert not test_failures


def test_run_tests_v4():
    t4 = mock_template(v=4, type="base")
    t1 = mock_template(v=1, type="cand")
    t2 = mock_template(v=2, type="cand")
    t3 = mock_template(v=3, type="cand")

    # v1 is missing a function that is in v4 => v1 is not forwards compatible with v4
    test_failures = run_tests(t4, t1)
    assert test_failures
    # v2 has a function with different behavior but its not captured by v4's test => v2 is forwards "compatible" with v4
    test_failures = run_tests(t4, t2)
    assert not test_failures
    # v3 is missing a function that is in v4 => v3 is not forwards compatible with v4
    test_failures = run_tests(t4, t3)
    assert test_failures


def test_get_test_deps_1():
    pom_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom-2.15.0.xml"
    test_deps = get_test_deps(pom_path, "dependencies")
    assert len(test_deps) == 6


def test_get_test_deps_2():
    pom_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom-2.15.1.xml"
    test_deps = get_test_deps(pom_path, "dependencies")
    assert len(test_deps) == 8


def test_merge_poms_0():
    pom_path_base = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "sonar-maven-plugin-3.9.1.2184.pom"
    pom_path_cand = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "sonar-maven-plugin-3.10.0.2594.pom"
    save_to_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "sonar-maven-plugin_merged_actual.pom.xml"
    expected_merged_pom_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "sonar-maven-plugin_merged.pom"

    merge_poms(pom_path_base, pom_path_cand, save_to_path)

    assert filecmp.cmp(save_to_path, expected_merged_pom_path, shallow=False)

    pathlib.Path.unlink(save_to_path)   # Cleanup, remove file


def test_merge_poms_1():
    pom_path_base = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom-2.15.0.xml"
    pom_path_cand = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom-2.15.1.xml"
    save_to_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "actual_pom_merged.xml"
    expected_merged_pom_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom_merged_1.xml"

    merge_poms(pom_path_base, pom_path_cand, save_to_path)

    assert filecmp.cmp(save_to_path, expected_merged_pom_path, shallow=False)

    pathlib.Path.unlink(save_to_path)   # Cleanup, remove file


def test_merge_poms_2():
    pom_path_base = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom-2.15.1.xml"
    pom_path_cand = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom-2.15.0.xml"
    save_to_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "actual_pom_merged.xml"
    expected_merged_pom_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom_merged_2.xml"

    merge_poms(pom_path_base, pom_path_cand, save_to_path)

    assert filecmp.cmp(save_to_path, expected_merged_pom_path, shallow=False)

    pathlib.Path.unlink(save_to_path)   # Cleanup, remove file


def test_merge_poms_3():
    pom_path_base = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom-2.15.2.xml"
    pom_path_cand = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom-2.15.0.xml"
    save_to_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "actual_pom_merged.xml"
    expected_merged_pom_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom_merged_3.xml"

    merge_poms(pom_path_base, pom_path_cand, save_to_path)

    assert filecmp.cmp(save_to_path, expected_merged_pom_path, shallow=False)

    pathlib.Path.unlink(save_to_path)   # Cleanup, remove file


def test_merge_poms_4():
    pom_path_base = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom-2.15.2.xml"
    pom_path_cand = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom-2.15.1.xml"
    save_to_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "actual_pom_merged.xml"
    expected_merged_pom_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom_merged_4.xml"

    merge_poms(pom_path_base, pom_path_cand, save_to_path)

    assert filecmp.cmp(save_to_path, expected_merged_pom_path, shallow=False)

    pathlib.Path.unlink(save_to_path)   # Cleanup, remove file


def test_merge_poms_5():
    pom_path_base = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom-2.15.1.xml"
    pom_path_cand = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom-2.15.2.xml"
    save_to_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "actual_pom_merged.xml"
    expected_merged_pom_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom_merged_5.xml"

    merge_poms(pom_path_base, pom_path_cand, save_to_path)

    assert filecmp.cmp(save_to_path, expected_merged_pom_path, shallow=False)

    pathlib.Path.unlink(save_to_path)   # Cleanup, remove file


def test_merge_poms_6():
    pom_path_base = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom_6-2.14.3.xml"
    pom_path_cand = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom_6-2.14.4.xml"
    save_to_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "actual_pom_6_merged.xml"
    expected_merged_pom_path = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "pom_merged_6.xml"

    merge_poms(pom_path_base, pom_path_cand, save_to_path)

    assert filecmp.cmp(save_to_path, expected_merged_pom_path, shallow=False)

    # pathlib.Path.unlink(save_to_path)   # Cleanup, remove file


def test_dynamic_check_lib_example_plexus_io_3_2_0():
    """base template org.codehaus.plexus:plexus-io:3.2.0, 3.3.1 => dynamic false but it fails/runs the same amount of tests
Tests run: 47, errors: 4"""
    g = "org.codehaus.plexus"
    a = "plexus-io"
    v = "3.2.0"

    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        base_template_3_2_0 = BaseTemplate(g, a, "3.2.0")

    with patch('server.template.candidate_template.CAND_TEMPLATES_DIR', CAND_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        cand_template_3_3_1 = CandidateTemplate(g, a, "3.3.1")
        cand_template_3_2_0 = CandidateTemplate(g, a, "3.2.0")

    baseline_fails = run_tests(base_template_3_2_0, cand_template_3_2_0)

    candidate_fails = run_tests(base_template_3_2_0, cand_template_3_3_1)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert compatible


def test_dynamic_check_lib_example_2_16_2():
    g = "com.fasterxml.jackson.core"
    a = "jackson-databind"

    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        base_template_2_16_2 = BaseTemplate(g, a, "2.16.2")

    with patch('server.template.candidate_template.CAND_TEMPLATES_DIR', CAND_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        cand_template_2_16_0 = CandidateTemplate(g, a, "2.16.0")
        cand_template_2_16_1 = CandidateTemplate(g, a, "2.16.1")
        cand_template_2_16_2 = CandidateTemplate(g, a, "2.16.2")

    baseline_fails = run_tests(base_template_2_16_2, cand_template_2_16_2)

    candidate_fails = run_tests(base_template_2_16_2, cand_template_2_16_2)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert compatible

    candidate_fails = run_tests(base_template_2_16_2, cand_template_2_16_0)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert not compatible

    candidate_fails = run_tests(base_template_2_16_2, cand_template_2_16_1)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert not compatible


def test_dynamic_check_lib_example_2_16_1():
    g = "com.fasterxml.jackson.core"
    a = "jackson-databind"

    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        base_template_2_16_1 = BaseTemplate(g, a, "2.16.1")

    with patch('server.template.candidate_template.CAND_TEMPLATES_DIR', CAND_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        cand_template_2_16_1 = CandidateTemplate(g, a, "2.16.1")
        cand_template_2_16_2 = CandidateTemplate(g, a, "2.16.2")

    baseline_fails = run_tests(base_template_2_16_1, cand_template_2_16_1)

    candidate_fails = run_tests(base_template_2_16_1, cand_template_2_16_1)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert compatible

    candidate_fails = run_tests(base_template_2_16_1, cand_template_2_16_2)
    compatible = dynamic_check(baseline_fails, candidate_fails)
    assert compatible


def test_tt():
    # Use this test for experimentation
    "com.alibaba:transmittable-thread-local:2.14.3->2.14.4 => compatible"
    "org.codehaus.plexus:plexus-io:3.2.0->3.3.1 => compatible"
    g = "org.codehaus.plexus"
    a = "plexus-io"
    v_base = "3.2.0"
    v_cand = "3.3.1"

    with patch('server.template.base_template.BASE_TEMPLATES_DIR', BASE_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        base = BaseTemplate(g, a, v_base)

    with patch('server.template.candidate_template.CAND_TEMPLATES_DIR', CAND_TEMPLATES_TEST_DIR), \
            patch('server.config.path_to_repos', REPOS_TEST_DIR):
        baseline = CandidateTemplate(g, a, v_base)
        cand = CandidateTemplate(g, a, v_cand)

    baseline_fails_read = get_test_failures_from_dir(base.target_path / "surefire-reports_BASE")
    baseline_fails = run_tests(base, baseline)
    input(f"base RERUN ({v_base}) has {len(baseline_fails)} fails: {baseline_fails}")
    input(f"base READ FROM REPORTS ({v_base}) has {len(baseline_fails_read)} fails: {baseline_fails_read}")
    candidate_fails = run_tests(base, cand)
    input(f"cand ({v_cand}) has {len(candidate_fails - baseline_fails)} fails not in base ({v_base}): {candidate_fails - baseline_fails}")
    compatible = dynamic_check(baseline_fails, candidate_fails)
    input(f"is cand ({v_cand}) compatible with base ({v_base})? {compatible}")