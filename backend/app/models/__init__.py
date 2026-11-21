import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Parent(Base):
    __tablename__ = "parents"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Child(Base):
    __tablename__ = "children"
    __table_args__ = (UniqueConstraint("parent_id", "username", name="uq_child_parent_username"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parents.id", ondelete="CASCADE"), index=True)
    username: Mapped[str] = mapped_column(String(20))  # stored lowercase
    level: Mapped[str] = mapped_column(String(2))  # P2 | P3 | P4
    pin_hash: Mapped[str] = mapped_column(String)
    failed_pin_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Worksheet(Base):
    __tablename__ = "worksheets"
    __table_args__ = (Index("ix_worksheet_child_status", "child_id", "status"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String(16))
    level: Mapped[str] = mapped_column(String(2))
    topic: Mapped[str] = mapped_column(String(120), default="")  # normalised
    status: Mapped[str] = mapped_column(String(16), default="uploaded")
    failure_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String, nullable=True)  # key only, never bytes
    topic_hint: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # INTERNAL ONLY: never returned by the API. Kept for generation and the one permitted retry.
    extracted_pages: Mapped[list | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, default="")
    worked_example: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parent_note: Mapped[str] = mapped_column(Text, default="")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Question(Base):
    """Practice question plus the backend-only AnswerKey (expected_answer, explanation)."""
    __tablename__ = "questions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worksheet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worksheets.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(Text)
    choices: Mapped[list] = mapped_column(JSON)
    expected_answer: Mapped[str] = mapped_column(String)
    explanation: Mapped[str] = mapped_column(Text)


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (UniqueConstraint("child_id", "question_id", name="uq_attempt_once"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    worksheet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worksheets.id", ondelete="CASCADE"))
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    answer: Mapped[str] = mapped_column(String)
    is_correct: Mapped[bool]
    feedback: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TopicProgress(Base):
    __tablename__ = "topic_progress"
    __table_args__ = (UniqueConstraint("child_id", "subject", "topic", name="uq_progress_topic"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String(16))
    level: Mapped[str] = mapped_column(String(2))
    topic: Mapped[str] = mapped_column(String(120))
    mastery: Mapped[str] = mapped_column(String(16), default="not_started")
    questions_attempted: Mapped[int] = mapped_column(Integer, default=0)
    questions_correct: Mapped[int] = mapped_column(Integer, default=0)
    last_practised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
