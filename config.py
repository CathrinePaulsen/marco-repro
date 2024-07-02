"""Collection of shared variables and methods."""
import os
import sqlalchemy
from sqlalchemy.orm import Session
import models

path_to_repos = os.path.abspath("../repos")
path_to_test_repos = os.path.abspath("server/resources/repos")
path_to_jars = os.path.abspath("./jars")
path_to_japicmp_jar = os.path.abspath("./libs/japicmp/japicmp-0.18.3-jar-with-dependencies.jar")
path_to_range_conversion_script = os.path.abspath("client/client/convert_to_range.py")

HTTP_headers = None

TIMEOUT_SECONDS = 300

ERROR_NO_POM = "POM not found"
ERROR_TIMEOUT = "Compilation timed out"


def get_projects_with_tree(session: Session):
    """Queries the db for projects that have been compiled, i.e. for which the dependency tree has been successfully
    generated, and returns the result."""
    return session.query(models.Project).filter(models.Project.compiles == sqlalchemy.true()).all()


def get_projects_without_tree(session: Session):
    """Queries the db for projects that have NOT yet been compiled, i.e. for which the dependency tree has not yet been
     successfully generated, and returns the result."""
    return session.query(models.Project).filter(models.Project.compiles == sqlalchemy.null()).all()


def get_conflicts(project: models.Project, session: Session):
    """Returns the conflicts reported for the given project."""
    return session.query(models.Conflict).filter(models.Conflict.project_name == project.name).all()


def get_github_token(filename: str = "github_api.token") -> str:
    try:
        with open(os.path.join(os.path.dirname(__file__), filename)) as f:
            return f.readline()
    except FileNotFoundError as e:
        print('No Github API token found.')
        raise e
