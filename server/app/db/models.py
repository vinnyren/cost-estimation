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
from sqlalchemy.orm import relationship
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

    # Cascade-delete child rows when the project is removed. Both ORM-level
    # `cascade="all, delete-orphan"` (so SQLAlchemy emits child DELETEs in the
    # right order) and FK-level `ondelete="CASCADE"` (defense in depth at the
    # SQLite layer; PRAGMA foreign_keys=ON is set in session.py) are required
    # to keep this safe across direct deletes and ORM deletes.
    function_points = relationship(
        "FunctionPoint",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    fp_snapshots = relationship(
        "FPSnapshot",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    results = relationship(
        "Result",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    param_overrides = relationship(
        "ParamOverride",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    uploads = relationship(
        "Upload",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class FunctionPoint(Base):
    __tablename__ = "function_points"

    id = Column(String, primary_key=True)
    project_id = Column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    source = Column(String)  # manual | imported | ai_extracted | claude_draft | allocator
    locked = Column(Boolean, default=False)
    notes = Column(Text)
    ord = Column(Integer)

    project = relationship("Project", back_populates="function_points")


class FPSnapshot(Base):
    __tablename__ = "fp_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    version = Column(Integer, nullable=False)
    snapshot_at = Column(DateTime, server_default=func.now(), nullable=False)
    snapshot_json = Column(Text, nullable=False)
    reason = Column(String)

    project = relationship("Project", back_populates="fp_snapshots")


Index("idx_fp_snapshots_project", FPSnapshot.project_id, FPSnapshot.id)
# UNIQUE 防止并发 bulk_write 在同一 (project, version) 上插入重复快照导致
# restore 非确定。/review round 5 加，并由 alembic migration 8a2e6b41c3d7
# 落到已有 DB。
Index(
    "uq_fp_snapshots_project_version",
    FPSnapshot.project_id,
    FPSnapshot.version,
    unique=True,
)


class ParamGlobal(Base):
    __tablename__ = "params_global"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    basis_version = Column(String, nullable=False)
    modified = Column(Boolean, default=False)
    updated_at = Column(DateTime, server_default=func.now())


class ParamOverride(Base):
    __tablename__ = "params_override"

    project_id = Column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    reason = Column(String)
    updated_at = Column(DateTime, server_default=func.now())

    project = relationship("Project", back_populates="param_overrides")


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    computed_at = Column(DateTime, server_default=func.now())
    mode = Column(String, nullable=False)
    fp_version = Column(Integer, nullable=False)
    params_hash = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    is_stale = Column(Boolean, default=False)

    project = relationship("Project", back_populates="results")


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename = Column(String, nullable=False)
    size = Column(Integer)
    uploaded_at = Column(DateTime, server_default=func.now())
    filetype = Column(String)
    parsed_text_path = Column(String)  # 大文本不进 DB

    project = relationship("Project", back_populates="uploads")
