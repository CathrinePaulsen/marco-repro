import pathlib

from server.test_failure import (TestFailure, get_test_failures_from_file, get_test_failures_from_dir,
                                 at_least_one_passing_test, get_test_results_from_dir)

TEST_REPORTS = pathlib.Path(__file__).parent.parent.resolve() / "test_resources" / "test_reports"


def test_get_test_failures_from_dir():
    path_to_test_reports = TEST_REPORTS / "surefire-reports"
    failures = get_test_failures_from_dir(path_to_test_reports)
    assert len(failures) == (2 + 55)  # 2 test failures + 55 test errors


def test_get_test_failures_from_file():
    path_to_report = (TEST_REPORTS / "TEST-com.fasterxml.jackson.databind.deser.jdk.UntypedDeserializationTest.xml")
    testsuite_name = "com.fasterxml.jackson.databind.deser.jdk.UntypedDeserializationTest"
    f1 = TestFailure(testsuite_name, "testPolymorphicUntypedVanilla",
                     "com.fasterxml.jackson.databind.deser.jdk.UntypedDeserializationTest", "failure")
    f2 = TestFailure(testsuite_name, "testPolymorphicUntypedCustom",
                     "com.fasterxml.jackson.databind.deser.jdk.UntypedDeserializationTest", "failure")
    f3 = TestFailure(testsuite_name, "testSimpleVanillaScalars",
                     "com.fasterxml.jackson.databind.deser.jdk.UntypedDeserializationTest", "failure")
    f4 = TestFailure(testsuite_name, "testNonVanilla",
                     "com.fasterxml.jackson.databind.deser.jdk.UntypedDeserializationTest", "failure")
    expected_failures = {f1, f2, f3, f4}
    actual_failures = get_test_failures_from_file(path_to_report)

    assert expected_failures == actual_failures


def test_get_test_results_from_dir_all_zero():
    dir_path = TEST_REPORTS / "surefire-reports_all_zeroes"
    results = get_test_results_from_dir(dir_path)
    assert results['pass'] == 0
    assert results['failure'] == 0
    assert results['error'] == 0
    assert results['skipped'] == 0


def test_get_test_results_from_dir_non_zero():
    dir_path = TEST_REPORTS / "surefire-reports_skipped"
    results = get_test_results_from_dir(dir_path)
    assert results['pass'] == 50
    assert results['failure'] == 0
    assert results['error'] == 0
    assert results['skipped'] == 25


def test_get_test_results_from_dir_big():
    dir_path = TEST_REPORTS / "surefire-reports_big"
    results = get_test_results_from_dir(dir_path)
    assert results['pass'] == 3182
    assert results['failure'] == 1
    assert results['error'] == 0
    assert results['skipped'] == 0


def test_get_test_results_from_dir_empty():
    dir_path = TEST_REPORTS / "surefire-reports_empty"
    results = get_test_results_from_dir(dir_path)
    assert results['pass'] == 0
    assert results['failure'] == 0
    assert results['error'] == 0
    assert results['skipped'] == 0


def test_at_least_one_passing_test_pass():
    dir_path = TEST_REPORTS / "surefire-reports_skipped"
    assert at_least_one_passing_test(dir_path)


def test_at_least_one_passing_test_fails_no_running():
    dir_path = TEST_REPORTS / "surefire-reports_all_zeroes"
    assert not at_least_one_passing_test(dir_path)


def test_at_least_one_passing_test_fails_no_passing():
    dir_path = TEST_REPORTS / "surefire-reports_no_passing"
    assert not at_least_one_passing_test(dir_path)
