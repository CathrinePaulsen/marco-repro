from datetime import datetime

import sqlalchemy
from sqlalchemy import Column, String, ForeignKeyConstraint, Boolean
from sqlalchemy.orm import Session, relationship

from rq5.models import Base
from rq5.models.project import Project


class Dependency(Base):
    __tablename__ = "dependencies"

    group_id = Column(String, primary_key=True)
    artifact_id = Column(String, primary_key=True)
    version = Column(String, primary_key=True)
    err = Column(String, nullable=True)
    evaluated = Column(String, nullable=True)
    is_new = Column(Boolean, nullable=True)  # Dependency collected during/after pom expansion

    projects = relationship("Project", secondary="project_dependencies", uselist=True)


class ProjectDependency(Base):
    __tablename__ = "project_dependencies"
    __table_args__ = (
        ForeignKeyConstraint(["repository"], [Project.repository]),
        ForeignKeyConstraint(["group_id", "artifact_id", "version"],
                             [Dependency.group_id, Dependency.artifact_id, Dependency.version]),
    )

    repository = Column(String, primary_key=True)
    group_id = Column(String, primary_key=True)
    artifact_id = Column(String, primary_key=True)
    version = Column(String, primary_key=True)
    resolved = Column(Boolean, nullable=True)
    is_new = Column(Boolean, nullable=True)  # Dependency collected during/after pom expansion


def dependency_exists(group_id: str, artifact_id: str, version: str, session: Session) -> bool:
    return session.query(Dependency).where(Dependency.group_id == group_id,
                                           Dependency.artifact_id == artifact_id,
                                           Dependency.version == version).scalar()


def add_dependency(project: Project, group_id: str, artifact_id: str, version: str, resolved: bool, is_new: bool, session: Session):
    if not dependency_exists(group_id, artifact_id, version, session):
        print(f"[ADDING] Dependency: {group_id}:{artifact_id}:{version}")
        dependency = Dependency(group_id=group_id, artifact_id=artifact_id, version=version, is_new=is_new)
        session.add(dependency)
    if not project_dependency_exists(project.repository, group_id, artifact_id, version, session):
        print(f"[ADDING] Project Dependency to repo {project.repository}: {group_id}:{artifact_id}:{version} "
              f"resolved={resolved}")
        project_dependency = ProjectDependency(repository=project.repository,
                                               group_id=group_id, artifact_id=artifact_id, version=version,
                                               resolved=resolved, is_new=is_new)
        session.add(project_dependency)
    # else:
        # To update resolved info, can be removed later
        # proj_dep = get_project_dependency(project.repository, group_id, artifact_id, version, session)
        # update_project_dependency_resolved(proj_dep, resolved, session)
        # session.add(proj_dep)
    session.commit()


def update_project_dependency_resolved(project_dependency: ProjectDependency, resolved: bool, session: Session):
    if project_dependency.resolved != resolved:
        project_dependency.resolved = resolved
        session.add(project_dependency)
        session.commit()


def update_dependency_err(dependency: Dependency, err: str, session: Session):
    dependency.err = err
    session.add(dependency)
    session.commit()


def update_dependency_evaluated_with_date(dependency: Dependency, session: Session):
    date = datetime.today().strftime('%Y-%m-%d')
    dependency.evaluated = date
    session.add(dependency)
    session.commit()


def get_dependencies(session: Session):
    return session.query(Dependency).all()


def get_dependencies_that_are_processed(session: Session):
    return session.query(Dependency).where(Dependency.evaluated.is_not(None)).all()


def get_dependency(group_id: str, artifact_id: str, version: str, session: Session):
    return session.query(Dependency).where(Dependency.group_id == group_id,
                                           Dependency.artifact_id == artifact_id,
                                           Dependency.version == version).first()


def project_dependency_exists(repository: str, group_id: str, artifact_id: str, version: str, session: Session) -> bool:
    return session.query(ProjectDependency).where(ProjectDependency.repository == repository,
                                                  ProjectDependency.group_id == group_id,
                                                  ProjectDependency.artifact_id == artifact_id,
                                                  ProjectDependency.version == version).scalar()


def add_project_dependency(repository: str, group_id: str, artifact_id: str, version: str, session: Session):
    if not project_dependency_exists(repository, group_id, artifact_id, version, session):
        row = ProjectDependency(repository=repository, group_id=group_id, artifact_id=artifact_id, version=version)
        session.add(row)
        session.commit()


def get_project_dependencies_by_repository(repository: str, session: Session):
    return session.query(ProjectDependency).where(ProjectDependency.repository == repository).all()


def get_project_dependency(repository: str, group_id: str, artifact_id: str, version: str, session: Session):
    return session.query(ProjectDependency).where(ProjectDependency.repository == repository,
                                                  ProjectDependency.group_id == group_id,
                                                  ProjectDependency.artifact_id == artifact_id,
                                                  ProjectDependency.version == version).first()

