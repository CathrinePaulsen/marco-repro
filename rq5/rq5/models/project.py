import sqlalchemy
from sqlalchemy import Column, Boolean, String
from sqlalchemy.orm import Session, relationship

from rq5.models import Base


class Project(Base):
    __tablename__ = "projects"

    repository = Column(String, primary_key=True)
    sha = Column(String, nullable=False)
    compiles = Column(Boolean, nullable=False)
    has_tests = Column(Boolean, nullable=False)

    dependencies = relationship("Dependency", secondary="project_dependencies", uselist=True, overlaps="projects")


def project_exists(repository: str, session: Session) -> bool:
    return session.query(Project).where(Project.repository == repository).scalar()


def add_project(repository: str, sha: str, compiles: bool, has_tests: bool, session: Session):
    if not project_exists(repository, session):
        row = Project(repository=repository, sha=sha, compiles=compiles, has_tests=has_tests)
        session.add(row)
        session.commit()


def get_project_by_repository(repository: str, session: Session):
    return session.query(Project).where(Project.repository == repository).first()


def get_projects_that_compile_and_has_tests(session: Session):
    return session.query(Project).where(Project.compiles == sqlalchemy.true(),
                                        Project.has_tests == sqlalchemy.true()).all()
