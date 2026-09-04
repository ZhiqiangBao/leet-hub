from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import DATA_DIR
from ..services.problems import bank
from .languages import get_adapter
from .sandbox import run_limited

MAX_LOG = 8000


def _last_json(stdout: str) -> dict[str, Any] | None:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _public_details(raw: dict[str, Any], tests: list) -> dict[str, Any]:
    details = {
        "verdict": raw.get("verdict"),
        "passed": raw.get("passed"),
        "total": raw.get("total", len(tests)),
        "message": raw.get("message"),
        "failed_index": raw.get("failed_index"),
        "cases": [],
    }
    failed_index = raw.get("failed_index")
    passed_count = int(raw.get("passed") or 0)
    if raw.get("verdict") == "AC":
        details["cases"] = [{"index": i, "passed": True} for i in range(len(tests))]
        return details
    cases = []
    for i, test in enumerate(tests):
        case: dict[str, Any] = {"index": i, "passed": i < passed_count, "hidden": bool(test.hidden)}
        if failed_index is not None and i == failed_index:
            case["passed"] = False
            if not test.hidden:
                case["args"] = test.args
                case["expected"] = test.expected
                if "got" in raw:
                    case["got"] = raw["got"]
                if raw.get("message"):
                    case["message"] = raw["message"]
        cases.append(case)
    details["cases"] = cases
    return details


def judge_source(problem_slug: str, language: str, source: str) -> dict[str, Any]:
    adapter = get_adapter(language)
    if adapter is None:
        return {"verdict": "NA", "details": {"message": f"未知语言: {language}"}, "compile_log": None, "time_ms": 0}
    if not adapter.implemented:
        return {
            "verdict": "NA",
            "details": {"message": f"{adapter.display_name} 接口已保留，尚未实现评测"},
            "compile_log": None,
            "time_ms": 0,
        }
    if not adapter.detect():
        return {
            "verdict": "NA",
            "details": {"message": f"{adapter.display_name} 运行时未安装"},
            "compile_log": None,
            "time_ms": 0,
        }

    problem = bank.get(problem_slug)
    signature = problem.signature.model_dump()
    tmp_root = DATA_DIR / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="job-", dir=tmp_root) as td:
        workdir = Path(td)
        wrapped = adapter.wrap(source, signature)
        (workdir / adapter.source_filename).write_text(wrapped, encoding="utf-8")
        compiled = adapter.compile(str(workdir))
        if not compiled.ok:
            return {
                "verdict": "CE",
                "details": {"message": "编译失败"},
                "compile_log": (compiled.log or "")[-MAX_LOG:],
                "time_ms": 0,
            }
        run = run_limited(
            adapter.run_argv(str(workdir)),
            cwd=workdir,
            stdin=problem.tests_stdin(),
            time_ms=problem.time_limit_ms,
            memory_mb=problem.memory_limit_mb,
        )
        if run.tle:
            return {
                "verdict": "TLE",
                "details": {"message": "超出时间限制", "total": len(problem.tests)},
                "compile_log": compiled.log,
                "time_ms": problem.time_limit_ms,
            }
        if run.mle:
            return {
                "verdict": "MLE",
                "details": {"message": "超出内存限制", "total": len(problem.tests)},
                "compile_log": compiled.log,
                "time_ms": run.time_ms,
            }
        payload = _last_json(run.stdout)
        if run.returncode != 0 and not payload:
            return {
                "verdict": "RE",
                "details": {
                    "message": (run.stderr or run.stdout or "runtime error")[-MAX_LOG:],
                    "total": len(problem.tests),
                },
                "compile_log": compiled.log,
                "time_ms": run.time_ms,
            }
        if not payload:
            return {
                "verdict": "RE",
                "details": {"message": "评测输出无法解析", "stderr": run.stderr[-2000:]},
                "compile_log": compiled.log,
                "time_ms": run.time_ms,
            }
        verdict = str(payload.get("verdict") or "RE")
        if verdict not in {"AC", "WA", "RE"}:
            verdict = "RE"
        return {
            "verdict": verdict,
            "details": _public_details(payload, problem.tests),
            "compile_log": compiled.log,
            "time_ms": run.time_ms,
        }


def apply_result(submission, result: dict[str, Any]) -> None:
    submission.status = "done"
    submission.verdict = result["verdict"]
    submission.details_json = json.dumps(result.get("details") or {}, ensure_ascii=False)
    submission.compile_log = result.get("compile_log")
    submission.time_ms = result.get("time_ms")
    submission.judged_at = datetime.utcnow()
