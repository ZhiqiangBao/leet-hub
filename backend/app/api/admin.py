from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_admin_user
from ..models import Submission, User
from ..schemas import (
    AdminStatsOut,
    AdminSubmissionOut,
    ProblemCreateIn,
    ProblemStat,
    ProblemUpdateIn,
    TestsAppendIn,
    TestsReplaceIn,
)
from ..services.problems import ProblemError, bank

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _admin_submission_out(sub: Submission, username: str, include_source: bool = False) -> AdminSubmissionOut:
    details = None
    if sub.details_json:
        try:
            details = json.loads(sub.details_json)
        except json.JSONDecodeError:
            details = {"message": sub.details_json}
    return AdminSubmissionOut(
        id=sub.id,
        user_id=sub.user_id,
        username=username,
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


@router.get("/stats", response_model=AdminStatsOut)
def stats(_admin: User = Depends(get_admin_user), db: Session = Depends(get_db)) -> AdminStatsOut:
    users = int(db.scalar(select(func.count()).select_from(User)) or 0)
    submissions = int(db.scalar(select(func.count()).select_from(Submission)) or 0)
    accepted = int(
        db.scalar(select(func.count()).select_from(Submission).where(Submission.verdict == "AC")) or 0
    )
    by_problem: list[ProblemStat] = []
    for problem in bank.list():
        total = int(
            db.scalar(
                select(func.count()).select_from(Submission).where(Submission.problem_slug == problem.slug)
            )
            or 0
        )
        ac = int(
            db.scalar(
                select(func.count())
                .select_from(Submission)
                .where(Submission.problem_slug == problem.slug, Submission.verdict == "AC")
            )
            or 0
        )
        by_problem.append(ProblemStat(slug=problem.slug, title=problem.title, submissions=total, accepted=ac))
    return AdminStatsOut(
        users=users,
        submissions=submissions,
        accepted=accepted,
        problems=len(bank.list()),
        by_problem=by_problem,
    )


@router.get("/submissions", response_model=list[AdminSubmissionOut])
def list_submissions(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
    slug: str | None = None,
    username: str | None = None,
    language: str | None = None,
    limit: int = 100,
) -> list[AdminSubmissionOut]:
    stmt = select(Submission, User.username).join(User, User.id == Submission.user_id)
    if slug:
        stmt = stmt.where(Submission.problem_slug == slug)
    if language:
        stmt = stmt.where(Submission.language == language)
    if username:
        stmt = stmt.where(User.username == username)
    stmt = stmt.order_by(Submission.id.desc()).limit(min(max(limit, 1), 300))
    rows = db.execute(stmt).all()
    return [_admin_submission_out(sub, name) for sub, name in rows]


@router.get("/submissions/{sub_id}", response_model=AdminSubmissionOut)
def get_submission(
    sub_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> AdminSubmissionOut:
    row = db.execute(
        select(Submission, User.username).join(User, User.id == Submission.user_id).where(Submission.id == sub_id)
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "提交不存在")
    sub, name = row
    return _admin_submission_out(sub, name, include_source=True)


@router.post("/problems")
def create_problem(body: ProblemCreateIn, _admin: User = Depends(get_admin_user)) -> dict:
    try:
        problem = bank.write_problem(
            slug=body.slug,
            title=body.title,
            difficulty=body.difficulty,
            time_limit_ms=body.time_limit_ms,
            memory_limit_mb=body.memory_limit_mb,
            tags=body.tags,
            statement_md=body.statement_md,
            signature=body.signature,
            starter=body.starter,
            tests=body.tests,
            overwrite=False,
        )
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "slug": problem.slug, "tests": len(problem.tests)}


@router.put("/problems/{slug}")
def update_problem(slug: str, body: ProblemUpdateIn, _admin: User = Depends(get_admin_user)) -> dict:
    try:
        current = bank.get(slug)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    try:
        problem = bank.write_problem(
            slug=slug,
            title=body.title or current.title,
            difficulty=body.difficulty or current.difficulty,
            time_limit_ms=body.time_limit_ms or current.time_limit_ms,
            memory_limit_mb=body.memory_limit_mb or current.memory_limit_mb,
            tags=body.tags if body.tags is not None else current.tags,
            statement_md=body.statement_md if body.statement_md is not None else current.statement_md,
            signature=body.signature or current.signature,
            starter=body.starter if body.starter is not None else current.starter,
            tests=current.tests,
            overwrite=True,
        )
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "slug": problem.slug}


@router.put("/problems/{slug}/tests")
def replace_tests(slug: str, body: TestsReplaceIn, _admin: User = Depends(get_admin_user)) -> dict:
    try:
        bank.get(slug)
        problem = bank.write_tests(slug, body.tests, append=False)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "slug": slug, "tests": len(problem.tests)}


@router.post("/problems/{slug}/tests:append")
def append_tests(slug: str, body: TestsAppendIn, _admin: User = Depends(get_admin_user)) -> dict:
    try:
        bank.get(slug)
        problem = bank.write_tests(slug, body.tests, append=True)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "题目不存在") from None
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "slug": slug, "tests": len(problem.tests)}


@router.post("/reload")
def reload(_admin: User = Depends(get_admin_user)) -> dict:
    try:
        bank.reload()
    except ProblemError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "count": len(bank.list())}
