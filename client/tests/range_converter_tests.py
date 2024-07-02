from random import shuffle
from unittest.mock import patch

from client import convert_compat_list_to_range


def test_range_conversion_basic():
    versions = ['1', '2', '3']
    available = ['0', '1', '2', '3', '4']
    shuffle(versions)
    shuffle(available)

    with patch('client.get_available_versions', return_value=available):
        range = convert_compat_list_to_range("", "", versions).decode("utf-8").strip()

    assert range == '[1,3]'


def test_range_conversion_one_restriction():
    versions = ['1', '3']
    available = ['0', '1', '2', '3', '4']
    shuffle(versions)
    shuffle(available)

    with patch('client.get_available_versions', return_value=available):
        range = convert_compat_list_to_range("", "", versions).decode("utf-8").strip()

    assert range == '[1],[3]'


def test_range_conversion_two_restrictions():
    versions = ['1', '3', '5']
    available = ['0', '1', '2', '3', '4', '5']
    shuffle(versions)
    shuffle(available)

    with patch('client.get_available_versions', return_value=available):
        range = convert_compat_list_to_range("", "", versions).decode("utf-8").strip()

    assert range == '[1],[3],[5]'


def test_range_conversion_only_one():
    versions = ['1']
    available = ['0', '1', '2']
    shuffle(versions)
    shuffle(available)

    with patch('client.get_available_versions', return_value=available):
        range = convert_compat_list_to_range("", "", versions).decode("utf-8").strip()

    assert range == '[1]'


def test_range_conversion_weird():
    versions = ['1.0.3', '2.20.0', '3.0-rc']
    available = ['0.01', '1.1.1', '1.0.3', '2.20.0', '2.2.2.2', '3.0-rc', 'iamversion']
    shuffle(versions)
    shuffle(available)

    with patch('client.get_available_versions', return_value=available):
        range = convert_compat_list_to_range("", "", versions).decode("utf-8").strip()

    assert range == '[1.0.3],[2.20.0,3.0-rc]'
