from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import get_admin_user
from ..models import User
from ..schemas import ProblemCreateIn, ProblemUpdateIn, TestsAppendIn, TestsReplaceIn
from ..services.problems import ProblemError, bank

router = APIRouter(prefix="/api/admin", tags=["admin"])


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
