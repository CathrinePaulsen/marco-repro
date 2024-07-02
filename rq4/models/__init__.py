"""Setting up of SQLite database."""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

path_to_db = Path(__file__).parent.parent.resolve() / "resources" / "rq4.db"
engine = create_engine(f"sqlite:///{path_to_db}")
Base.metadata.create_all(engine)
