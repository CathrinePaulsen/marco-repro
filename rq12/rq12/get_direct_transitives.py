"""Analyzes each project for instances of transitive dependencies used directly and adds it to the db"""
import os
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from rq12.get_deps import Dependency, query_dependency, get_projects_with_tree
from rq12.models import engine
from server.config import COMPILE_TIMEOUT as TIMEOUT_SECONDS

USED_UNDECLARED = "Used undeclared"
UNUSED_DECLARED = "Unused declared"

path_to_repos = Path(__file__).parent.parent.resolve() / "resources" / "repos"


def parse(output: subprocess.CompletedProcess, violation: str):
    """Parses the output stream of mvn dependency:analyze into Dependency objects
    where each Dependency is a violation (either USED_UNDECLARED or UNUSED_DECLARED)."""

    start_of_violations_used_undeclared = f"[WARNING] {violation} dependencies found:"
    violation_prefix = "[WARNING]    "
    grab_line = False
    violations = []

    for line in output.stdout.splitlines():
        # Found start of violations, begin extraction
        if line == start_of_violations_used_undeclared:
            grab_line = True

        # Grab violation
        elif grab_line and line.startswith(violation_prefix):
            dep = Dependency(line.replace(violation_prefix, "").strip())
            violations.append(dep)

        # No more violations, end extraction
        elif grab_line and not line.startswith(violation_prefix):
            break

    return violations


def get_direct_transitives():
    with Session(engine) as session:
        projects = get_projects_with_tree(session)

        for project in projects:
            print(f"====== EVALUATING PROJECT {project.name}")
            project_path = os.path.join(path_to_repos, project.name)
            pom_path = os.path.join(project_path, "pom.xml")
            tree_path = os.path.join(project_path, "dep.tree")
            assert (os.path.isfile(tree_path))
            assert(os.path.isfile(pom_path))

            print(f"Looking for instances of direct usage of transitive dependencies in {project.name}:")
            os.chdir(project_path)
            try:
                # timeout 5m
                output = subprocess.run(["mvn", "dependency:analyze"], timeout=TIMEOUT_SECONDS, stdout=subprocess.PIPE, universal_newlines=True)
                print(output.stdout)
                direct_trans = parse(output, USED_UNDECLARED)
                direct_trans = [query_dependency(x, project, session) for x in direct_trans]
                unused_declared = parse(output, UNUSED_DECLARED)
                unused_declared = [query_dependency(x, project, session) for x in unused_declared]

            except subprocess.TimeoutExpired:
                # print(f"Timed out during tree generation. Marking project as not compiling.")
                # project.error = ERROR_TIMEOUT
                pass

            for dep in project.dependencies:
                if dep in direct_trans:
                    print("VIOLATION")
                    print(dep.name)
                    setattr(dep, "used_undeclared", True)
                else:
                    setattr(dep, "used_undeclared", False)
                if dep in unused_declared:
                    print("VIOLATION")
                    print(dep.name)
                    setattr(dep, "unused_declared", True)
                else:
                    setattr(dep, "unused_declared", False)
                session.commit()

