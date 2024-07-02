"""Setting up of SQLite database."""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

path_to_db = Path(__file__).parent.parent.parent.resolve() / "resources" / "rq5.db"
engine = create_engine(f"sqlite:///{path_to_db}")


def set_up_db():
    Base.metadata.create_all(engine)
