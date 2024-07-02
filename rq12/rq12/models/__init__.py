"""Setting up of SQLite database."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Boolean, String, Integer, ForeignKey
from sqlalchemy.schema import ForeignKeyConstraint
from pathlib import Path


Base = declarative_base()


class Project(Base):
    """Table representation of a GitHub Maven project."""
    __tablename__ = "projects"
    name = Column(String, primary_key=True)
    commit = Column(String, nullable=False)
    compiles = Column(Boolean, nullable=True, default=None)
    error = Column(String, nullable=True, default=None)

    dependencies = relationship("Dependency", uselist=True, cascade="all, delete-orphan")


class Dependency(Base):
    """Table representation of a GitHub Maven project's resolved dependencies."""
    __tablename__ = "dependencies"
    project_name = Column(String, ForeignKey("projects.name"), primary_key=True)
    name = Column(String, primary_key=True)
    version = Column(String, nullable=False)
    scope = Column(String, nullable=False)
    direct = Column(Boolean, nullable=False)
    used_undeclared = Column(Boolean, nullable=True, default=None)
    unused_declared = Column(Boolean, nullable=True, default=None)

    conflicts = relationship("Conflict", uselist=True, cascade="all, delete-orphan")


class Conflict(Base):
    """Table representation of a GitHub Maven project's conflicting SoftVer dependency ignored during mediation."""
    __tablename__ = "conflicts"

    project_name = Column(String, primary_key=True)
    dependency_name = Column(String, primary_key=True)
    version = Column(String, primary_key=True)
    scope = Column(String, primary_key=True)
    compatible = Column(Boolean, nullable=False, default=True)
    managed = Column(Boolean, nullable=True, default=None)

    __table_args__ = (
        ForeignKeyConstraint([project_name, dependency_name], [Dependency.project_name, Dependency.name]),
    )


path_to_db = Path(__file__).parent.parent.parent.resolve() / "resources" / "rq12.db"
# path_to_db = Path(__file__).parent.parent.parent.resolve() / "resources" / "dependencies_backup.db"
engine = create_engine(f"sqlite:///{path_to_db}")
Base.metadata.create_all(engine)
