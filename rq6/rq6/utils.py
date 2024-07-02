from enum import StrEnum, auto
from pathlib import Path

from server.dynamic import dynamically_compatible
from server.exceptions import (BaseJarNotFoundException, CandidateJarNotFoundException, MavenNoPomInDirectoryException,
                               MavenSurefireTestFailedException, GithubRepoNotFoundException,
                               MavenCompileFailedException, GithubTagNotFoundException, MavenResolutionFailedException,
                               BaseMavenCompileTimeout, BaseMavenTestTimeout)
from server.static import statically_compatible
from server.template.base_template import BaseTemplate

RESOURCES = Path(__file__).parent.parent.resolve() / 'resources'


class Result(StrEnum):
    NO_GITHUB_TAG = auto()
    NO_JAR = auto()
    NO_MAVEN = auto()
    NO_POM = auto()
    NO_RESOLVE = auto()
    NO_TEST = auto()
    NO_COMPILE = auto()
    NO_GITHUB_LINK = auto()
    UNKNOWN = auto()
    COMPATIBLE = auto()
    STATICALLY_COMPATIBLE = auto()
    STATICALLY_INCOMPATIBLE = auto()
    DYNAMICALLY_INCOMPATIBLE = auto()
    DYNAMICALLY_COMPATIBLE = auto()


def get_pairwise_result(ga: str, old_version: str, new_version: str, github_repo=None, dynamic_only=False) -> Result:
    g, a = ga.split(":")

    if dynamic_only:
        return get_dynamic_result(g, a, old_version, new_version, github_repo=github_repo)

    result = get_static_result(g, a, old_version, new_version)
    if result == Result.COMPATIBLE:
        result = get_dynamic_result(g, a, old_version, new_version, github_repo=github_repo)

    return result


def get_static_result(g: str, a: str, old_version: str, new_version: str) -> Result | None:
    try:
        compatible = statically_compatible(g, a, old_version, new_version)
        return Result.COMPATIBLE if compatible else Result.STATICALLY_INCOMPATIBLE
    except (BaseJarNotFoundException, CandidateJarNotFoundException) as e:
        print(e)
        print(f"Found no jar for base or candidate.")
        return Result.NO_JAR


def get_dynamic_result(g: str, a: str, old_version: str, new_version: str, github_repo=None) -> Result | None:
    try:
        base_template = BaseTemplate(g, a, old_version, repo_name=github_repo)
        compatible = dynamically_compatible(base_template, new_version, repo_name=github_repo)
    except MavenNoPomInDirectoryException as e:
        print(e)
        return Result.NO_MAVEN
    except (MavenSurefireTestFailedException, BaseMavenTestTimeout) as e:
        print(e)
        return Result.NO_TEST
    except MavenResolutionFailedException as e:
        print(e)
        return Result.NO_RESOLVE
    except (MavenCompileFailedException, BaseMavenCompileTimeout) as e:
        print(e)
        return Result.NO_COMPILE
    except GithubRepoNotFoundException as e:
        print(e)
        return Result.NO_GITHUB_LINK
    except GithubTagNotFoundException as e:
        print(e)
        return Result.NO_GITHUB_TAG
    except (BaseJarNotFoundException, CandidateJarNotFoundException) as e:
        print(e)
        return Result.NO_JAR

    return Result.COMPATIBLE if compatible else Result.DYNAMICALLY_INCOMPATIBLE