import json
import shlex
import subprocess
from pathlib import Path

from rq4.breaking import config


class Datapoint:
    """
    Class representing a BUMP datapoint
    """

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filename = filepath.name
        self.data = self._get_data()
        self.failure_category = self.data['failureCategory']
        self.dependency_info = self.data['updatedDependency']
        self.breaking_commit = self.data['breakingCommit']
        self.img_name_pre = f"ghcr.io/chains-project/breaking-updates:{self.breaking_commit}-pre"
        self.img_name_new = f"ghcr.io/chains-project/breaking-updates:{self.breaking_commit}-breaking"

        self.group_id = self.dependency_info['dependencyGroupID']
        self.artifact_id = self.dependency_info['dependencyArtifactID']
        self.version_pre = self.dependency_info['previousVersion']
        self.version_new = self.dependency_info['newVersion']
        self.dependency_section = self.dependency_info['dependencySection']
        self.updated_file_type = self.dependency_info['updatedFileType']
        self.version_update_type = self.dependency_info['versionUpdateType']

        # TODO implement setters for these?
        self.repo = self.dependency_info.get('gitHubLink', "")
        self.commit_base = self.dependency_info.get('previousVersionGitHubCommit', "")
        self.commit_candidate = self.dependency_info.get('newVersionGitHubCommit', "")
        self.dynamically_compatible = self.dependency_info.get('dynamicallyCompatible', "")

        self.m2_jar_path_pre = self._create_m2_resource_path("jar", self.version_pre)
        self.m2_jar_path_new = self._create_m2_resource_path("jar", self.version_new)
        self.m2_pom_path_pre = self._create_m2_resource_path("pom", self.version_pre)
        self.m2_pom_path_new = self._create_m2_resource_path("pom", self.version_new)

    def store(self, dataset: Path) -> None:
        """
        Stores the datapoint in the given destination dataset.
        """
        assert Path.is_dir(dataset)
        with open(dataset / self.filename, 'w') as file:
            json.dump(self.data, file)

    def remove(self):
        """Removes self from where it is stored."""
        Path.unlink(self.filepath)

    def get_poms_from_images(self, host_storage_path=config.missing_pom_path) -> Path:
        """
        Fetches the poms from the BUMP docker images, stores them in <storage_path>/breaking_commit, and returns the path
        """
        # TODO basically identical to get_jars_from_images, how can we generalize?
        img_storage_path = Path("/missing_poms")
        copy_to = img_storage_path / self.breaking_commit
        if not Path.is_file(host_storage_path / self.breaking_commit / self.m2_pom_path_pre.name):
            command_pre = f'docker run --rm --platform linux/amd64 --entrypoint "/bin/sh" ' \
                          f'-v {host_storage_path}:{img_storage_path} {self.img_name_pre} ' \
                          f'-c "mkdir -p {copy_to} && cp {self.m2_pom_path_pre} {copy_to}"'
            print(f"\nGetting pom from {self.img_name_pre} using command: {command_pre}")
            subprocess.run(shlex.split(command_pre), stdout=subprocess.PIPE)

        if not Path.is_file(host_storage_path / self.breaking_commit / self.m2_pom_path_new.name):
            command_new = f'docker run --rm --platform linux/amd64 --entrypoint "/bin/sh" ' \
                          f'-v {host_storage_path}:{img_storage_path} {self.img_name_new} ' \
                          f'-c "mkdir -p {copy_to} && cp {self.m2_pom_path_new} {copy_to}"'
            print(f"\nGetting pom from {self.img_name_new} using command: {command_new}")
            subprocess.run(shlex.split(command_new), stdout=subprocess.PIPE)

        print(f"\nDeleting docker images just downloaded")
        command_cleanup_pre = f'docker image rm {self.img_name_pre}'
        command_cleanup_new = f'docker image rm {self.img_name_new}'
        subprocess.run(shlex.split(command_cleanup_pre))
        subprocess.run(shlex.split(command_cleanup_new))

        print(f"\nPoms were stored in {host_storage_path / self.breaking_commit}.")
        return host_storage_path / self.breaking_commit

    def get_jars_from_images(self, host_storage_path=config.missing_jar_path) -> Path:
        """
        Fetches the jars from the BUMP docker images, stores them in <storage_path>/breaking_commit, and returns the path.
        """
        img_storage_path = Path("/missing_jars")
        copy_to = img_storage_path / self.breaking_commit
        if not Path.is_file(host_storage_path / self.breaking_commit / self.m2_jar_path_pre.name):
            command_pre = f'docker run --rm --platform linux/amd64 --entrypoint "/bin/sh" ' \
                          f'-v {host_storage_path}:{img_storage_path} {self.img_name_pre} ' \
                          f'-c "mkdir -p {copy_to} && cp {self.m2_jar_path_pre} {copy_to}"'
            print(f"\nGetting jar from {self.img_name_pre} using command: {command_pre}")
            subprocess.run(shlex.split(command_pre), stdout=subprocess.PIPE)

        if not Path.is_file(host_storage_path / self.breaking_commit / self.m2_jar_path_new.name):
            command_new = f'docker run --rm --platform linux/amd64 --entrypoint "/bin/sh" ' \
                          f'-v {host_storage_path}:{img_storage_path} {self.img_name_new} ' \
                          f'-c "mkdir -p {copy_to} && cp {self.m2_jar_path_new} {copy_to}"'
            print(f"\nGetting jar from {self.img_name_new} using command: {command_new}")
            subprocess.run(shlex.split(command_new), stdout=subprocess.PIPE)

        print(f"\nDeleting docker images just downloaded")
        command_cleanup_pre = f'docker image rm {self.img_name_pre}'
        command_cleanup_new = f'docker image rm {self.img_name_new}'
        subprocess.run(shlex.split(command_cleanup_pre))
        subprocess.run(shlex.split(command_cleanup_new))

        print(f"\nJars were stored in {host_storage_path / self.breaking_commit}.")
        return host_storage_path / self.breaking_commit

    def _create_m2_resource_path(self, extension: str, v: str) -> Path:
        """
        The .m2 folder is located in /root/ inside the BUMP images.
        An m2 resource can then be found in:
            /root/.m2/repository/my/group/id/my/artifact/id/my.version/my-artifact-id-my.version.extension
        """
        g_slashes = self.group_id.replace(".", "/")
        a_slashes = self.artifact_id.replace(".", "/")
        a_dashes = self.artifact_id.replace(".", "-")
        m2_path = Path("/root/.m2/repository") / g_slashes / a_slashes / v / f"{a_dashes}-{v}.{extension}"
        return m2_path

    def _get_data(self):
        with open(self.filepath, 'r') as file:
            return json.load(file)

    def __eq__(self, other):
        if self.group_id == other.group_id:
            if self.artifact_id == other.artifact_id:
                if self.version_pre == other.version_pre:
                    if self.version_new == other.version_new:
                        return True
        return False

    def __repr__(self):
        return f"{self.group_id}:{self.artifact_id}:{self.version_pre}->{self.version_new}"

    def __hash__(self):
        return hash(self.__repr__())


def datapoints(dataset: Path):
    """
    Generator that yields Datapoints created from the json datapoint files in the given dataset
    :param dataset: absolute Path to BUMP dataset
    :return: Datapoints
    """
    assert (Path.is_dir(dataset))
    for filepath in dataset.glob("*.json"):
        yield Datapoint(filepath)


def sum_datapoints(dataset: Path) -> int:
    """
    Returns how many datapoints are stored in the given dataset.
    """
    return sum([1 for _ in datapoints(dataset)])
