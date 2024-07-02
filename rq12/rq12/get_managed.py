import os
from rq12.get_deps import get_projects_with_tree
from rq12.models import engine, Dependency, Conflict, Project
from sqlalchemy.orm import Session
from pathlib import Path

path_to_repos = Path(__file__).parent.parent.resolve() / "resources" / "repos"


def get_dependency_management_overrides():
    """Returns true if a conflict has been manually mediated using dependencyManagement to version override."""
    return


def get_direct_overrides():
    """Returns true if a conflict has been manually mediated using direct dependency declaration to version override."""
    return


def is_overriden_by_dependency_management(dep: Dependency):
    """Returns true if a conflict has been manually mediated using dependencyManagement to version override."""
    return


def is_overriden_by_direct_declaration(dep: Dependency):
    """Returns true if a conflict has been manually mediated using direct dependency declaration to version override."""
    return


def get_conflicts(project: Project, session: Session):
    return session.query(Conflict).where(Conflict.project_name == project.name).all()


def get_managed():
    print("RUNNING MANUAL MEDIATION CHECK")
    with Session(engine) as session:
        projects = get_projects_with_tree(session)

        for project in projects:
            print(f"Evaluating {project.name}")
            project_path = os.path.join(path_to_repos, project.name)
            tree_path = os.path.join(project_path, "dep.tree")
            assert (os.path.isfile(tree_path))

            conflicts = get_conflicts(project, session)
            for conflict in conflicts:
                print(f"Found conflict {conflict.dependency_name}:{conflict.version}:{conflict.scope}, managed={conflict.managed}")
                resolved_dep = session.query(Dependency).filter(Dependency.name == conflict.dependency_name).first()
                if not resolved_dep:
                    continue
                print(f"For dependency {resolved_dep.name}:{resolved_dep.version}:{resolved_dep.scope}, unused_declared={resolved_dep.unused_declared}, used_undeclared={resolved_dep.used_undeclared}")
                if resolved_dep.unused_declared:
                    print("HELLO WORLD")
                    setattr(conflict, "managed", True)
                elif not conflict.managed:
                    setattr(conflict, "managed", False)
                session.commit()


"""
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
                    if dep.is_conflict:
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
                dep_model = models.Conflict(project_name=project.name, dependency_name=dep.name,
                                            version=dep.version, scope=dep.scope)
                exists = session.query(models.Conflict).filter(
                        models.Conflict.project_name    == dep_model.project_name,
                        models.Conflict.dependency_name == dep_model.dependency_name,
                        models.Conflict.version         == dep_model.version,
                        models.Conflict.scope           == dep_model.scope).first()
                if not exists:
                    print(f"Added it to conflicts.")
                    session.add(dep_model)
                else:
                    print(f"Already in conflicts.")
            session.commit()
"""
