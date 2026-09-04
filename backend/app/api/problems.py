from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import SOURCE_MAX_BYTES
from ..db import get_db
from ..deps import get_current_user
from ..judge.languages import language_status
from ..judge.engine import judge_source
from ..judge.queue import enqueue
from ..models import Submission, User
from ..schemas import (
    ProblemDetailOut,
    ProblemMetaOut,
    RankingOut,
    RunOut,
    ScoreRow,
    SubmissionOut,
    SubmitIn,
)
from ..services.problems import bank
from ..services.ranking import ranking_for, scores_for_user

router = APIRouter(prefix="/api", tags=["problems"])


def _user_progress(db: Session, user_id: int) -> tuple[set[str], set[str]]:
    rows = db.execute(
        select(Submission.problem_slug, Submission.verdict).where(Submission.user_id == user_id)
    ).all()
    attempted = {slug for slug, _ in rows}
    solved = {slug for slug, verdict in rows if verdict == "AC"}
    return solved, attempted


def _submission_out(sub: Submission, include_source: bool = False) -> SubmissionOut:
    details = None
    if sub.details_json:
        try:
            details = json.loads(sub.details_json)
        except json.JSONDecodeError:
            details = {"message": sub.details_json}
    return SubmissionOut(
        id=sub.id,
        problem_slug=sub.problem_slug,
        language=sub.language,
        status=sub.status,
        verdict=sub.verdict,
        details=details,
        compile_log=sub.compile_log,
        time_ms=sub.time_ms,
        created_at=sub.created_at.isoformat() if sub.created_at else "",
        judged_at=sub.judged_at.isoformat() if sub.judged_at else None,
        source=sub.source if include_source else None,
    )


@router.get("/languages")
def languages() -> list[dict]:
    return language_status()


@router.get("/problems", response_model=list[ProblemMetaOut])
def list_problems(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ProblemMetaOut]:
    solved, attempted = _user_progress(db, user.id)
    out = []
    for problem in bank.list():
        out.append(
            ProblemMetaOut(
                slug=problem.slug,
                title=problem.title,
                difficulty=problem.difficulty,  # type: ignore[arg-type]
                time_limit_ms=problem.time_limit_ms,
                memory_limit_mb=problem.memory_limit_mb,
                tags=problem.tags,
                solved=problem.slug in solved,
                attempted=problem.slug in attempted,
            )
        )
    return out


@router.get("/problems/{slug}", response_model=ProblemDetailOut)
def get_problem(slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ProblemDetailOut:
    try:
        problem = bank.get(slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    solved, attempted = _user_progress(db, user.id)
    return ProblemDetailOut(
        slug=problem.slug,
        title=problem.title,
        difficulty=problem.difficulty,  # type: ignore[arg-type]
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        tags=problem.tags,
        solved=problem.slug in solved,
        attempted=problem.slug in attempted,
        statement_md=problem.statement_md,
        signature=problem.signature,
        starter=problem.starter,
    )


@router.post("/problems/{slug}/submit", response_model=SubmissionOut)
async def submit(
    slug: str,
    body: SubmitIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmissionOut:
    try:
        bank.get(slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    if len(body.source.encode("utf-8")) > SOURCE_MAX_BYTES:
        raise HTTPException(413, "代码过长")
    sub = Submission(
        user_id=user.id,
        problem_slug=slug,
        language=body.language,
        source=body.source,
        status="queued",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    await enqueue(sub.id)
    return _submission_out(sub)


@router.post("/problems/{slug}/run", response_model=RunOut)
async def run_public(
    slug: str,
    body: SubmitIn,
    _user: User = Depends(get_current_user),
) -> RunOut:
    try:
        problem = bank.get(slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    if len(body.source.encode("utf-8")) > SOURCE_MAX_BYTES:
        raise HTTPException(413, "代码过长")
    public = [t for t in problem.tests if not t.hidden]
    if not public:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "本题没有公开测例")
    result = await asyncio.to_thread(judge_source, slug, body.language, body.source, True)
    return RunOut(
        kind="test",
        verdict=str(result.get("verdict") or "NA"),
        details=result.get("details"),
        compile_log=result.get("compile_log"),
        time_ms=result.get("time_ms"),
        public_count=len(public),
    )


@router.get("/problems/{slug}/ranking", response_model=RankingOut)
def problem_ranking(
    slug: str,
    language: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RankingOut:
    try:
        bank.get(slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    return ranking_for(db, slug, language, user.id)


@router.get("/scores", response_model=list[ScoreRow])
def my_scores(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ScoreRow]:
    return scores_for_user(db, user.id)


@router.get("/submissions", response_model=list[SubmissionOut])
def my_submissions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    slug: str | None = None,
    limit: int = 50,
) -> list[SubmissionOut]:
    stmt = select(Submission).where(Submission.user_id == user.id)
    if slug:
        stmt = stmt.where(Submission.problem_slug == slug)
    stmt = stmt.order_by(Submission.id.desc()).limit(min(limit, 200))
    rows = db.scalars(stmt).all()
    return [_submission_out(row) for row in rows]


@router.get("/submissions/{sub_id}", response_model=SubmissionOut)
def get_submission(
    sub_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmissionOut:
    sub = db.get(Submission, sub_id)
    if not sub or sub.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "提交不存在")
    return _submission_out(sub, include_source=True)
