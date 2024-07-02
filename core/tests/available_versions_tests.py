import pathlib
from unittest.mock import patch, MagicMock

from core import get_available_versions, scrape_available_versions

TEST_RESOURCES = pathlib.Path(__file__).parent.parent.resolve() / "test_resources"


def test_scrape_available_versions():
    g = "com.sun.istack"
    a = "istack-commons-runtime"
    actual_versions = scrape_available_versions(g, a)
    expected_versions = ["1.0", "2.10", "2.11", "2.12", "2.13", "2.14", "2.15", "2.16", "2.17", "2.18", "2.19",
                         "2.2", "2.2.1", "2.20", "2.21", "2.22", "2.23", "2.24", "2.3", "2.4", "2.5", "2.6",
                         "2.6.1", "2.7", "2.8", "2.9", "3.0", "3.0.1", "3.0.10", "3.0.11", "3.0.12", "3.0.2",
                         "3.0.3", "3.0.4", "3.0.5", "3.0.7", "3.0.8", "3.0.9", "4.0.0", "4.0.0-M1", "4.0.0-M2",
                         "4.0.0-M3", "4.0.1", "4.1.0", "4.1.0-M1", "4.1.1", "4.1.2", "4.2.0"]
    expected_versions.reverse()
    assert actual_versions == expected_versions


def test_available_versions_single():
    expected_versions = ['1']
    with open(TEST_RESOURCES / "single-maven-metadata.xml", 'rb') as f:
        metadata = f.read()

    mock = MagicMock
    mock.headers = {'Content-Type': 'text/xml'}
    mock.content = metadata

    with patch('core.requests.get', return_value=mock):
        avs = get_available_versions("", "")

    assert avs == expected_versions


def test_available_versions_multiple():
    expected_versions = ['2', '1']
    with open(TEST_RESOURCES / "multiple-maven-metadata.xml", 'rb') as f:
        metadata = f.read()

    mock = MagicMock
    mock.headers = {'Content-Type': 'text/xml'}
    mock.content = metadata

    with patch('core.requests.get', return_value=mock):
        avs = get_available_versions("", "")

    assert avs == expected_versions


def test_available_versions_many():
    expected_versions = ['2.0.0-RC1', '2.0.0-RC2', '2.0.0-RC3', '2.0.0', '2.0.1', '2.0.2', '2.0.4', '2.0.5', '2.0.6',
                         '2.1.0', '2.1.1', '2.1.2', '2.1.3', '2.1.4', '2.1.5', '2.2.0-rc1', '2.2.0']
    expected_versions.reverse()

    with open(TEST_RESOURCES / "many-maven-metadata.xml", 'rb') as f:
        metadata = f.read()

    mock = MagicMock
    mock.headers = {'Content-Type': 'text/xml'}
    mock.content = metadata

    with patch('core.requests.get', return_value=mock):
        avs = get_available_versions("", "")

    assert avs == expected_versions


def test_available_versions_online_test():
    g = "com.fasterxml.jackson.core"
    a = "jackson-databind"
    avs = get_available_versions(g, a)

    vs = """<version>2.0.0-RC1</version>
<version>2.0.0-RC2</version>
<version>2.0.0-RC3</version>
<version>2.0.0</version>
<version>2.0.1</version>
<version>2.0.2</version>
<version>2.0.4</version>
<version>2.0.5</version>
<version>2.0.6</version>
<version>2.1.0</version>
<version>2.1.1</version>
<version>2.1.2</version>
<version>2.1.3</version>
<version>2.1.4</version>
<version>2.1.5</version>
<version>2.2.0-rc1</version>
<version>2.2.0</version>
<version>2.2.1</version>
<version>2.2.2</version>
<version>2.2.3</version>
<version>2.2.4</version>
<version>2.3.0-rc1</version>
<version>2.3.0</version>
<version>2.3.1</version>
<version>2.3.2</version>
<version>2.3.3</version>
<version>2.3.4</version>
<version>2.3.5</version>
<version>2.4.0-rc1</version>
<version>2.4.0-rc2</version>
<version>2.4.0-rc3</version>
<version>2.4.0</version>
<version>2.4.1</version>
<version>2.4.1.1</version>
<version>2.4.1.2</version>
<version>2.4.1.3</version>
<version>2.4.2</version>
<version>2.4.3</version>
<version>2.4.4</version>
<version>2.4.5</version>
<version>2.4.5.1</version>
<version>2.4.6</version>
<version>2.5.0-rc1</version>
<version>2.5.0</version>
<version>2.5.1</version>
<version>2.5.2</version>
<version>2.5.3</version>
<version>2.5.5</version>
<version>2.6.0-rc1</version>
<version>2.6.0-rc2</version>
<version>2.6.0-rc3</version>
<version>2.6.0-rc4</version>
<version>2.6.0</version>
<version>2.6.1</version>
<version>2.6.2</version>
<version>2.6.3</version>
<version>2.6.4</version>
<version>2.6.5</version>
<version>2.6.6</version>
<version>2.6.7</version>
<version>2.6.7.1</version>
<version>2.6.7.2</version>
<version>2.6.7.3</version>
<version>2.6.7.4</version>
<version>2.6.7.5</version>
<version>2.7.0-rc1</version>
<version>2.7.0-rc2</version>
<version>2.7.0-rc3</version>
<version>2.7.0</version>
<version>2.7.1</version>
<version>2.7.1-1</version>
<version>2.7.2</version>
<version>2.7.3</version>
<version>2.7.4</version>
<version>2.7.5</version>
<version>2.7.6</version>
<version>2.7.7</version>
<version>2.7.8</version>
<version>2.7.9</version>
<version>2.7.9.1</version>
<version>2.7.9.2</version>
<version>2.7.9.3</version>
<version>2.7.9.4</version>
<version>2.7.9.5</version>
<version>2.7.9.6</version>
<version>2.7.9.7</version>
<version>2.8.0.rc1</version>
<version>2.8.0.rc2</version>
<version>2.8.0</version>
<version>2.8.1</version>
<version>2.8.2</version>
<version>2.8.3</version>
<version>2.8.4</version>
<version>2.8.5</version>
<version>2.8.6</version>
<version>2.8.7</version>
<version>2.8.8</version>
<version>2.8.8.1</version>
<version>2.8.9</version>
<version>2.8.10</version>
<version>2.8.11</version>
<version>2.8.11.1</version>
<version>2.8.11.2</version>
<version>2.8.11.3</version>
<version>2.8.11.4</version>
<version>2.8.11.5</version>
<version>2.8.11.6</version>
<version>2.9.0</version>
<version>2.9.0.pr1</version>
<version>2.9.0.pr2</version>
<version>2.9.0.pr3</version>
<version>2.9.0.pr4</version>
<version>2.9.1</version>
<version>2.9.2</version>
<version>2.9.3</version>
<version>2.9.4</version>
<version>2.9.5</version>
<version>2.9.6</version>
<version>2.9.7</version>
<version>2.9.8</version>
<version>2.9.9</version>
<version>2.9.9.1</version>
<version>2.9.9.2</version>
<version>2.9.9.3</version>
<version>2.9.10</version>
<version>2.9.10.1</version>
<version>2.9.10.2</version>
<version>2.9.10.3</version>
<version>2.9.10.4</version>
<version>2.9.10.5</version>
<version>2.9.10.6</version>
<version>2.9.10.7</version>
<version>2.9.10.8</version>
<version>2.10.0</version>
<version>2.10.0.pr1</version>
<version>2.10.0.pr2</version>
<version>2.10.0.pr3</version>
<version>2.10.1</version>
<version>2.10.2</version>
<version>2.10.3</version>
<version>2.10.4</version>
<version>2.10.5</version>
<version>2.10.5.1</version>
<version>2.11.0.rc1</version>
<version>2.11.0</version>
<version>2.11.1</version>
<version>2.11.2</version>
<version>2.11.3</version>
<version>2.11.4</version>
<version>2.12.0-rc1</version>
<version>2.12.0-rc2</version>
<version>2.12.0</version>
<version>2.12.1</version>
<version>2.12.2</version>
<version>2.12.3</version>
<version>2.12.4</version>
<version>2.12.5</version>
<version>2.12.6</version>
<version>2.12.6.1</version>
<version>2.12.7</version>
<version>2.12.7.1</version>
<version>2.13.0-rc1</version>
<version>2.13.0-rc2</version>
<version>2.13.0</version>
<version>2.13.1</version>
<version>2.13.2</version>
<version>2.13.2.1</version>
<version>2.13.2.2</version>
<version>2.13.3</version>
<version>2.13.4</version>
<version>2.13.4.1</version>
<version>2.13.4.2</version>
<version>2.13.5</version>
<version>2.14.0-rc1</version>
<version>2.14.0-rc2</version>
<version>2.14.0-rc3</version>
<version>2.14.0</version>
<version>2.14.1</version>
<version>2.14.2</version>
<version>2.14.3</version>
<version>2.15.0-rc1</version>
<version>2.15.0-rc2</version>
<version>2.15.0-rc3</version>
<version>2.15.0</version>
<version>2.15.1</version>
<version>2.15.2</version>
<version>2.15.3</version>
<version>2.15.4</version>
<version>2.16.0-rc1</version>
<version>2.16.0</version>
<version>2.16.1</version>
<version>2.16.2</version>
<version>2.17.0-rc1</version>
<version>2.17.0</version>"""
    expected_versions = vs.replace("<version>", "").replace("</version>", "").split("\n")
    expected_versions.reverse()

    assert avs == expected_versions

