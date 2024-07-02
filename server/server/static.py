"""Module containing logic related to checking jars for static compatibility (source + binary)."""
import os
import pathlib
import subprocess
from pathlib import Path

from server.config import PATH_TO_JAPICMP, PATH_TO_JARS
from server.exceptions import BaseJarNotFoundException, CandidateJarNotFoundException


def run_static_check(path_to_jar_old: Path, path_to_jar_new: Path) -> bool:
    """
    :param path_to_jar_old: path to the jar of the original version of the dependency
    :param path_to_jar_new: path to the jar of the upgraded/downgraded version of the dependency
    :return: True if japicmp returned no source/binary incompatibility between the old and new jars, otherwise False
    """
    if not os.path.isfile(path_to_jar_new):
        raise FileNotFoundError(f"Could not find jar: {path_to_jar_new}")
    if not os.path.isfile(path_to_jar_old):
        raise FileNotFoundError(f"Could not find jar: {path_to_jar_old}")

    # Run CLI command
    out = subprocess.run(["java", "-jar", PATH_TO_JAPICMP, "--ignore-missing-classes",
                          "--error-on-binary-incompatibility", "--error-on-source-incompatibility",
                          "--new", path_to_jar_new, "--old", path_to_jar_old],
                         stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
    # If stderr is empty, no source/binary compatibility was detected
    return not out.stderr


def statically_compatible(g: str, a: str, v: str, cv: str) -> bool:
    """
    :param g: groupId
    :param a: artifactId
    :param v: base version
    :param cv: candidate version
    :return: True if candidate version is statically compatible with base version, False otherwise
    """
    old_jar = pathlib.Path.joinpath(PATH_TO_JARS, f"{a}-{v}.jar")
    new_jar = pathlib.Path.joinpath(PATH_TO_JARS, f"{a}-{cv}.jar")

    if not os.path.isfile(old_jar):
        subprocess.run(["mvn", "dependency:copy", f"-Dartifact={g}:{a}:{v}",
                        "-DexcludeTransitive=true", f"-DoutputDirectory={PATH_TO_JARS}"])
    if not os.path.isfile(old_jar):
        raise BaseJarNotFoundException(f"Could not find base jar for the static compatibility check: {old_jar}")

    if not os.path.isfile(new_jar):
        subprocess.run(["mvn", "dependency:copy", f"-Dartifact={g}:{a}:{cv}",
                        "-DexcludeTransitive=true", f"-DoutputDirectory={PATH_TO_JARS}"])
    if not os.path.isfile(new_jar):
        raise CandidateJarNotFoundException(f"Could not find candidate jar for static compatibility check: {new_jar}")

    return run_static_check(old_jar, new_jar)
