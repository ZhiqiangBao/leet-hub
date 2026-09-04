from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Difficulty = Literal["easy", "medium", "hard"]
CompareMode = Literal["exact", "any_order"]


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=4, max_length=72)


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool


class ParamSpec(BaseModel):
    name: str
    type: str


class Signature(BaseModel):
    class_name: str = "Solution"
    method: str
    params: list[ParamSpec]
    return_type: str
    compare: CompareMode = "exact"


class TestCase(BaseModel):
    args: list[Any]
    expected: Any
    hidden: bool = False


class ProblemMetaOut(BaseModel):
    slug: str
    title: str
    difficulty: Difficulty
    time_limit_ms: int
    memory_limit_mb: int
    tags: list[str]
    solved: bool = False
    attempted: bool = False


class ProblemDetailOut(ProblemMetaOut):
    statement_md: str
    signature: Signature
    starter: dict[str, str]


class SubmitIn(BaseModel):
    language: str
    source: str = Field(min_length=1, max_length=262144)


class SubmissionOut(BaseModel):
    id: int
    problem_slug: str
    language: str
    status: str
    verdict: str | None
    details: dict[str, Any] | None = None
    compile_log: str | None = None
    time_ms: int | None = None
    created_at: str
    judged_at: str | None = None
    source: str | None = None


class LanguageOut(BaseModel):
    id: str
    display_name: str
    implemented: bool
    available: bool
    runtime_detected: bool
    reason: str | None = None


class ProblemCreateIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)
    title: str = Field(min_length=1, max_length=120)
    difficulty: Difficulty = "easy"
    time_limit_ms: int = Field(default=2000, ge=100, le=30000)
    memory_limit_mb: int = Field(default=256, ge=32, le=2048)
    tags: list[str] = Field(default_factory=list)
    statement_md: str
    signature: Signature
    starter: dict[str, str] = Field(default_factory=dict)
    tests: list[TestCase] = Field(default_factory=list)


class ProblemUpdateIn(BaseModel):
    title: str | None = None
    difficulty: Difficulty | None = None
    time_limit_ms: int | None = Field(default=None, ge=100, le=30000)
    memory_limit_mb: int | None = Field(default=None, ge=32, le=2048)
    tags: list[str] | None = None
    statement_md: str | None = None
    signature: Signature | None = None
    starter: dict[str, str] | None = None


class TestsReplaceIn(BaseModel):
    tests: list[TestCase]


class TestsAppendIn(BaseModel):
    tests: list[TestCase] = Field(min_length=1)
