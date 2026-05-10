from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from .session import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    project_type = Column(String, nullable=False)  # dev_only | ops_only | dev_and_ops
    phase = Column(String, nullable=False)  # budget | bidding | planning | change | settled
    city = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    client = Column(String)
    evaluator = Column(String)
    mode = Column(String, nullable=False)  # forward | reverse
    target_cost = Column(Float)
    other_cost = Column(Float, default=0)
    include_ops = Column(Boolean, default=False)
    alpha_dev = Column(Float, default=1.0)
    fp_method = Column(String, default="nesma_estimated")
    basis_data_ver = Column(String, nullable=False)


class FunctionPoint(Base):
    __tablename__ = "function_points"

    id = Column(String, primary_key=True)
    project_id = Column(
        String, ForeignKey("projects.id"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False, default=1)
    subsystem = Column(String)
    l1_module = Column(String)
    l2_module = Column(String)
    description = Column(Text)
    name = Column(String)
    category = Column(String, nullable=False)  # EI|EO|EQ|ILF|EIF
    complexity = Column(String, nullable=False)  # low|average|high
    ufp = Column(Float, nullable=False)
    reuse_level = Column(String)
    modify_type = Column(String)
    us = Column(Float, nullable=False)
    source = Column(String)  # claude_draft|manual|imported|allocator
    locked = Column(Boolean, default=False)
    notes = Column(Text)
    ord = Column(Integer)


class FPSnapshot(Base):
    __tablename__ = "fp_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    version = Column(Integer, nullable=False)
    snapshot_at = Column(DateTime, server_default=func.now(), nullable=False)
    snapshot_json = Column(Text, nullable=False)
    reason = Column(String)


Index("idx_fp_snapshots_project", FPSnapshot.project_id, FPSnapshot.id)


class ParamGlobal(Base):
    __tablename__ = "params_global"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    basis_version = Column(String, nullable=False)
    modified = Column(Boolean, default=False)
    updated_at = Column(DateTime, server_default=func.now())


class ParamOverride(Base):
    __tablename__ = "params_override"

    project_id = Column(String, ForeignKey("projects.id"), primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    reason = Column(String)
    updated_at = Column(DateTime, server_default=func.now())


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        String, ForeignKey("projects.id"), nullable=False, index=True
    )
    computed_at = Column(DateTime, server_default=func.now())
    mode = Column(String, nullable=False)
    fp_version = Column(Integer, nullable=False)
    params_hash = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    is_stale = Column(Boolean, default=False)


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    filename = Column(String, nullable=False)
    size = Column(Integer)
    uploaded_at = Column(DateTime, server_default=func.now())
    filetype = Column(String)
    parsed_text_path = Column(String)  # 大文本不进 DB
