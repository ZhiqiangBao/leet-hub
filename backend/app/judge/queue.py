from __future__ import annotations

import asyncio
import json
from collections.abc import Coroutine

from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import Submission
from .engine import apply_result, judge_source

_queue: asyncio.Queue[int] | None = None
_task: asyncio.Task | None = None


def queue() -> asyncio.Queue[int]:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


async def _worker() -> None:
    q = queue()
    while True:
        sub_id = await q.get()
        try:
            await asyncio.to_thread(_judge_one, sub_id)
        except Exception as exc:
            _mark_internal_error(sub_id, str(exc))
        finally:
            q.task_done()


def _mark_internal_error(sub_id: int, message: str) -> None:
    db = SessionLocal()
    try:
        sub = db.get(Submission, sub_id)
        if not sub:
            return
        sub.status = "done"
        sub.verdict = "RE"
        sub.details_json = json.dumps({"message": f"internal judge error: {message}"}, ensure_ascii=False)
        db.commit()
    finally:
        db.close()


def _judge_one(sub_id: int) -> None:
    db: Session = SessionLocal()
    try:
        sub = db.get(Submission, sub_id)
        if not sub:
            return
        sub.status = "running"
        db.commit()
        result = judge_source(sub.problem_slug, sub.language, sub.source)
        apply_result(sub, result)
        db.commit()
    finally:
        db.close()


def start_worker() -> Coroutine:
    async def _run():
        global _task
        _task = asyncio.create_task(_worker())
        await _task

    return _run()


async def spawn_worker() -> None:
    global _task
    _task = asyncio.create_task(_worker())


async def stop_worker() -> None:
    global _task
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None


async def enqueue(submission_id: int) -> None:
    await queue().put(submission_id)
