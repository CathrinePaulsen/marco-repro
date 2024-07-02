from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import Column, String
from sqlalchemy.orm import Session
from sqlalchemy.orm import relationship

from models import Base
if TYPE_CHECKING:
    from models.pr import PR


class Link(Base):
    """Table representation of Github links (repository + tag) of GAVs"""
    __tablename__ = "links"

    ga = Column(String, primary_key=True)
    version = Column(String, primary_key=True)
    repository = Column(String, nullable=True)
    tag_name = Column(String, nullable=True)
    tag_commit = Column(String, nullable=True)
    err = Column(String, nullable=True)

    prs = relationship("PR", secondary="pr_links", overlaps="links")  # Added overlaps=Links to silence Warning


def link_exists(ga: str, version: str, session: Session):
    return session.query(Link).where(Link.ga == ga, Link.version == version).scalar()


def get_link(ga: str, version: str, session: Session):
    return session.query(Link).where(Link.ga == ga, Link.version == version).first()
