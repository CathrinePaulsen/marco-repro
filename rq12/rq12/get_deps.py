"""Generates dependency trees for each project in db, and counts conflicting softvers encountered during mediation."""
import os

import sqlalchemy

import rq12.models as models
from rq12.models import Project, engine
from sqlalchemy.orm import Session
from pathlib import Path

path_to_repos = Path(__file__).parent.parent.resolve() / "resources" / "repos"


def get_projects_with_tree(session: Session):
    return session.query(Project).where(Project.compiles == sqlalchemy.true(), Project.error == sqlalchemy.null()).all()


class Dependency:
    """Class representing a resolved Maven dependency."""
    __direct_prefixes: list[str] = ["+- ", "\- "]
    conflicts_with = ""
    managed_from = ""

    def __init__(self, branch: str):
        self.is_direct: bool = self.__is_direct(branch)
        self.is_duplicate: bool = self.__is_duplicate(branch)

        dep_str = self.__get_dependency_string(branch).split(":")
        self.__num_components = len(dep_str)
        assert(self.__num_components == 5 or self.__num_components == 6)

        self.group_id: str = dep_str[0]
        self.artifact_id: str = dep_str[1]
        self.version: str = dep_str[self.__get_version_idx()]
        self.scope: str = dep_str[self.__get_scope_idx()]
        self.name: str = f"{self.group_id}:{self.artifact_id}"

        self.is_managed: bool = self.__is_managed(branch)
        self.is_conflict: bool = self.__is_conflict(branch)

    def __get_version_idx(self):
        if self.__num_components == 5:
            return 3
        return 4

    def __get_scope_idx(self):
        if self.__num_components == 5:
            return 4
        return 5

    def __repr__(self):
            return f"{self.group_id}:{self.artifact_id}:{self.version}:{self.scope} " \
                   f"(direct={self.is_direct}, duplicate={self.is_duplicate}, conflict={self.is_conflict} {self.conflicts_with})"

    def __eq__(self, other):
        """Returns true if two Dependencies have the same group_id and artifact_id"""
        if isinstance(other, Dependency):
            return self.group_id == other.group_id and self.artifact_id == other.artifact_id
        return False

    def __is_direct(self, branch: str):
        """Returns True if the dependency is direct, False if transitive."""
        return branch[:3] in self.__direct_prefixes

    def __is_duplicate(self, branch: str):
        """Returns True if the dependency branch is a duplicate of an already resolved branch, False otherwise"""
        return "omitted for duplicate" in branch

    def __is_conflict(self, branch: str):
        """Returns True if the dependency branch conflicts with an already resolved branch, False otherwise"""
        branch = branch.split("omitted for conflict with")
        if len(branch) == 2:
            self.conflicts_with = branch[-1][:-1][:-1].strip()  # Remove trailing ) and whitespace
            return True
        return False

    def __is_managed(self, branch: str):
        """Returns True if the dependency branch is a managed conflict, False otherwise"""
        branch = branch.split("version managed from")
        if len(branch) == 2:
            # Remove trailing ) and whitespace, ignore what comes after ";"
            self.managed_from = branch[-1][:-1][:-1].strip().split(";")[0]
            if self.version != self.managed_from:
                self.conflicts_with = self.version
                return True
        return False

    def __get_dependency_string(self, branch: str):
        """Parses a branch and returns a dependency string in the format
        {groupId}:{artifactId}:{type}:{classifier}:{version}:{scope}, where classifier may or may not be present."""
        # Remove tree formatting
        dep = branch.replace("+- ", "").replace("\- ", "").replace("|  ", "").strip()
        # Remove encapsulating brackets
        if dep[0] == "(" and dep[-1] == ")":
            dep = dep[1:-1]
        return dep.split(' ')[0]


def query_dependency(dep: Dependency, proj: models.Project, session: Session):
    """
    Given a Dependency object, it queries the db for it and returns the record.
    """
    return session.query(models.Dependency).where(models.Dependency.project_name == proj.name,
                                                  models.Dependency.name == dep.name).first()


def get_resolved_dependencies():
    with Session(engine) as session:
        projects = get_projects_with_tree(session)

        for project in projects:
            print(f"====== EVALUATING PROJECT {project.name}")
            project_path = os.path.join(path_to_repos, project.name)
            tree_path = os.path.join(project_path, "dep.tree")
            assert (os.path.isfile(tree_path))

            conflicts = []
            with open(tree_path) as f:
                tree = f.readlines()[1:]  # Remove first line, which contains self
                for branch in tree:
                    dep = Dependency(branch)
                    print(f"\nFound dependency: {dep}")
                    if dep.is_duplicate:
                        # Ignore duplicates, since these were already successfully resolved
                        print(f"found duplicate")
                        continue
                    if dep.is_conflict or dep.is_managed:
                        # Store for later so that conflicts can be added after the dependency it conflicts with
                        print(f"found conflict")
                        conflicts.append(dep)
                    else:
                        dep_model = models.Dependency(project_name=project.name, name=dep.name,
                                                      version=dep.version, scope=dep.scope, direct=dep.is_direct)
                        exists = session.query(models.Dependency).filter(
                                models.Dependency.project_name  == dep_model.project_name,
                                models.Dependency.name          == dep_model.name).first()
                        if not exists:
                            print(f"Added it to dependencies.")
                            session.add(dep_model)
                        else:
                            print(f"Already in dependencies: {exists.name}")

            # Add conflicts to db
            for dep in conflicts:
                if dep.is_managed:
                    resolved_version = dep.version       # The version resolved by Maven for the dependency
                    conflict_version = dep.managed_from  # The version that was ignored in the conflict
                else:
                    resolved_version = dep.conflicts_with
                    conflict_version = dep.version
                dep_model = models.Conflict(project_name=project.name, dependency_name=dep.name,
                                            version=conflict_version, scope=dep.scope, managed=dep.is_managed)
                exists = session.query(models.Conflict).filter(
                        models.Conflict.project_name    == dep_model.project_name,
                        models.Conflict.dependency_name == dep_model.dependency_name,
                        models.Conflict.version         == dep_model.version,
                        models.Conflict.scope           == dep_model.scope).first()
                if not exists:
                    print(f"Added it to conflicts.")
                    session.add(dep_model)
                else:
                    if dep.is_managed:
                        setattr(dep, "managed", True)
                        session.commit()
                    print(f"Already in conflicts.")
            session.commit()
