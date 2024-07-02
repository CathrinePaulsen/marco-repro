import sqlalchemy
from sqlalchemy import Column, Boolean, String
from sqlalchemy.orm import Session
from sqlalchemy.orm import relationship

from models import Base


class Project(Base):
    """Table representation of the projects used to extract datapoints of updates."""
    __tablename__ = "projects"

    repository = Column(String, primary_key=True)
    dependabot = Column(Boolean, nullable=False)

    prs = relationship("PR", uselist=True, cascade="all, delete-orphan")


def project_exists(repository: str, session: Session) -> bool:
    return session.query(Project).where(Project.repository == repository).scalar()


def add_project(repository: str, dependabot_enabled: bool, session: Session):
    print(f"[ADD {dependabot_enabled}] {repository}")
    if not project_exists(repository, session):
        row = Project(repository=repository, dependabot=dependabot_enabled)
        session.add(row)
        session.commit()


def get_project_by_repository(repository: str, session: Session):
    return session.query(Project).where(Project.repository == repository).first()


def get_projects_by_dependabot(dependabot: bool, session: Session):
    dependabot = sqlalchemy.true() if dependabot else sqlalchemy.false()
    return session.query(Project).where(Project.dependabot == dependabot).all()
