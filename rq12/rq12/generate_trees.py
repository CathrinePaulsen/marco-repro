import os
import subprocess

import sqlalchemy

from server.config import COMPILE_TIMEOUT as TIMEOUT_SECONDS
from rq12.models import Project
from rq12.models import engine
from sqlalchemy.orm import Session
from pathlib import Path

ERROR_NO_POM = "NO_POM"
ERROR_TIMEOUT = "TIMEOUT"
path_to_repos = Path(__file__).parent.parent.resolve() / "resources" / "repos"


def get_projects_without_tree(session: Session):
    return session.query(Project).where(Project.compiles == sqlalchemy.null()).all()

def generate_trees():
    """Visits all 'unprocessed' projects stored in the db, and generates dependency trees for them."""
    with Session(engine) as session:
        projects = get_projects_without_tree(session)
        total = len(projects)
        print(f"Got {total} projects without trees")

        for project in projects:
            project_path = os.path.join(path_to_repos, project.name)
            pom_path = os.path.join(project_path, "pom.xml")
            tree_path = os.path.join(project_path, "dep.tree")

            if not os.path.isfile(pom_path):
                print(f"Could not find pom.xml in {project_path}")
                project.compiles = False
                project.error = ERROR_NO_POM
                session.commit()
                continue

            # Resolve dependency tree
            print(f"Resolving dependencies for {project.name}:")
            os.chdir(project_path)
            try:
                # timeout 5m
                output = subprocess.run(["mvn", "dependency:tree", "-DoutputFile=dep.tree", "-Dverbose"],
                                        timeout=TIMEOUT_SECONDS)
                print(output)
            except subprocess.TimeoutExpired:
                print(f"Timed out during tree generation. Marking project as not compiling.")
                project.error = ERROR_TIMEOUT

            if os.path.isfile(tree_path):
                with open(tree_path, 'r') as f:
                    if "BUILD FAILURE" in f:
                        project.compiles = 0
                    elif output.returncode == 0:
                        project.compiles = 1
            else:
                project.compiles = 0

            session.commit()
