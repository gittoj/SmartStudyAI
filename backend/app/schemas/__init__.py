"""Pydantic models. Field names mirror frontend/lib/types.ts (camelCase on the wire)."""
import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic.alias_generators import to_camel

Level = Literal["P2", "P3", "P4"]
Subject = Literal["mathematics", "english"]
WorksheetStatus = Literal["uploaded", "processing", "ready", "needs_review", "failed"]
Mastery = Literal["not_started", "needs_practice", "developing", "confident"]
FailureReason = Literal["unreadable", "wrong_subject", "too_long", "unsupported_file", "service_unavailable"]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


# ---- Auth / accounts ----
class RegisterRequest(CamelModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=10)


class LoginRequest(CamelModel):
    email: EmailStr
    password: str


class ParentAccount(CamelModel):
    id: uuid.UUID
    email: str
    display_name: str
    created_at: datetime


# ---- Child profiles ----
class CreateChildRequest(CamelModel):
    username: str
    level: Level
    pin: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", value):
            raise ValueError("Use 3 to 20 letters, numbers, or underscores.")
        return value.lower()

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}", value):
            raise ValueError("The PIN must be exactly four digits.")
        return value


class ChildProfile(CamelModel):
    id: uuid.UUID
    parent_id: uuid.UUID
    username: str
    level: Level
    created_at: datetime


class ChildChoice(CamelModel):
    """What the practice screen shows before PIN entry."""
    id: uuid.UUID
    username: str


class SelectChildRequest(CamelModel):
    pin: str


class DeleteChildRequest(CamelModel):
    confirm_username: str


# ---- Worksheets ----
class WorksheetPage(CamelModel):
    page_number: int
    confidence: float | None  # extractedText intentionally omitted: internal only


class WorkedExample(CamelModel):
    prompt: str
    steps: list[str]
    answer: str


class PracticeQuestion(CamelModel):
    id: uuid.UUID
    prompt: str
    choices: list[str] = Field(min_length=4, max_length=4)  # no expectedAnswer / explanation


class WorksheetResult(CamelModel):
    id: uuid.UUID
    child_id: uuid.UUID
    subject: Subject
    level: Level
    topic: str
    status: WorksheetStatus
    explanation: str
    worked_example: WorkedExample | None
    practice_questions: list[PracticeQuestion]
    parent_note: str
    failure_reason: FailureReason | None = None
    created_at: datetime


class WorksheetSummary(CamelModel):
    id: uuid.UUID
    subject: Subject
    topic: str
    status: WorksheetStatus
    created_at: datetime


# ---- AI output (validated before saving) ----
class GeneratedQuestion(BaseModel):
    prompt: str = Field(min_length=1)
    choices: list[str] = Field(min_length=4, max_length=4)
    expected_answer: str
    explanation: str = Field(min_length=1)


class GeneratedWorksheet(BaseModel):
    """Raw model output. Completeness is enforced by ai_service.validate_generated,
    because a subject mismatch legitimately returns no questions."""
    detected_subject: Literal["mathematics", "english", "unclear"]
    topic: str = ""
    explanation: str = ""
    worked_example: WorkedExample | None = None
    parent_note: str = ""
    questions: list[GeneratedQuestion] = Field(default_factory=list, max_length=5)


class WorksheetStatusResponse(CamelModel):
    """Parent polling: status plus the message to show when review or retry is needed."""
    id: uuid.UUID
    status: WorksheetStatus
    parent_note: str
    failure_reason: FailureReason | None = None
    can_retry: bool


# ---- Practice ----
class SubmitAnswerRequest(CamelModel):
    answer: str


class PracticeFeedback(CamelModel):
    id: uuid.UUID
    question_id: uuid.UUID
    is_correct: bool
    correct_choice: str
    explanation: str
    feedback: str
    submitted_at: datetime


# ---- Dashboard ----
class TopicProgress(CamelModel):
    child_id: uuid.UUID
    subject: Subject
    level: Level
    topic: str
    mastery: Mastery
    questions_attempted: int
    questions_correct: int
    last_practised_at: datetime | None


class DashboardChild(CamelModel):
    id: uuid.UUID
    username: str
    level: Level


class ParentDashboard(CamelModel):
    child: DashboardChild
    topics: list[TopicProgress]
    recent_worksheets: list[WorksheetSummary] = Field(max_length=8)
