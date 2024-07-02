import sqlalchemy
from sqlalchemy import Column, Boolean, String
from sqlalchemy.orm import Session

from rq5.models import Base


class Compatibility(Base):
    __tablename__ = "compatibilities"

    group_id = Column(String, primary_key=True)
    artifact_id = Column(String, primary_key=True)
    v_base = Column(String, primary_key=True)
    v_cand = Column(String, primary_key=True)
    static = Column(Boolean, nullable=True)
    dynamic = Column(Boolean, nullable=True)
    err = Column(String, nullable=True)


def get_compatibility(group_id: str, artifact_id: str, v_base: str, v_cand: str, session: Session) -> bool:
    return session.query(Compatibility).where(Compatibility.group_id == group_id,
                                              Compatibility.artifact_id == artifact_id,
                                              Compatibility.v_base == v_base,
                                              Compatibility.v_cand == v_cand).first()


def compatibility_exists(group_id: str, artifact_id: str, v_base: str, v_cand: str, session: Session) -> bool:
    return session.query(Compatibility).where(Compatibility.group_id == group_id,
                                              Compatibility.artifact_id == artifact_id,
                                              Compatibility.v_base == v_base,
                                              Compatibility.v_cand == v_cand).scalar()


def get_compatibilities_of_base(group_id: str, artifact_id: str, v_base: str, session: Session):
    return session.query(Compatibility).where(Compatibility.group_id == group_id,
                                              Compatibility.artifact_id == artifact_id,
                                              Compatibility.v_base == v_base,
                                              Compatibility.static == sqlalchemy.true(),
                                              Compatibility.dynamic == sqlalchemy.true()).all()


def add_compatibility(group_id: str, artifact_id: str, v_base: str, v_cand: str, session: Session,
                      static=None, dynamic=None, err=None):
    if not compatibility_exists(group_id, artifact_id, v_base, v_cand, session):
        print(f"[ADDING] Compatibility {group_id}:{artifact_id}:{v_base}=>{v_cand},"
              f" static={static}, dynamic={dynamic}, err={err}")
        compatibility = Compatibility(group_id=group_id, artifact_id=artifact_id, v_base=v_base, v_cand=v_cand,
                                      static=static, dynamic=dynamic, err=err)
        session.add(compatibility)
        session.commit()
    # else:
    #     compatibility = get_compatibility(group_id, artifact_id, v_base, v_cand, session)
    #     compatibility.static = static
    #     compatibility.dynamic = dynamic
    #     compatibility.err = err
    #     session.add(compatibility)
    #     session.commit()
