from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from ..config import PROBLEMS_DIR
from ..schemas import ParamSpec, Signature, TestCase

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SUPPORTED_TYPES = {"int", "long", "float", "bool", "str"}


class ProblemError(ValueError):
    pass


def _check_type(type_name: str) -> None:
    name = type_name.strip()
    if name in SUPPORTED_TYPES:
        return
    if name.startswith("List[") and name.endswith("]"):
        _check_type(name[5:-1])
        return
    raise ProblemError(f"不支持的类型: {type_name}")


def parse_signature(raw: dict[str, Any]) -> Signature:
    sig = Signature(
        class_name=raw.get("class_name") or "Solution",
        method=raw["method"],
        params=[ParamSpec(**p) for p in raw.get("params") or []],
        return_type=raw["return_type"],
        compare=raw.get("compare") or "exact",
    )
    _check_type(sig.return_type)
    for param in sig.params:
        _check_type(param.type)
    return sig


def parse_tests(text: str) -> list[TestCase]:
    tests: list[TestCase] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            tests.append(TestCase.model_validate(obj))
        except Exception as exc:
            raise ProblemError(f"tests.jsonl 第 {line_no} 行无效: {exc}") from exc
    return tests


def dump_tests(tests: list[TestCase]) -> str:
    lines = [
        json.dumps(t.model_dump(), ensure_ascii=False, separators=(",", ":"))
        for t in tests
    ]
    return "\n".join(lines) + ("\n" if lines else "")


class Problem:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.slug = path.name
        meta_path = path / "meta.yaml"
        statement_path = path / "statement.md"
        signature_path = path / "signature.yaml"
        tests_path = path / "tests.jsonl"
        if not meta_path.is_file() or not statement_path.is_file() or not signature_path.is_file():
            raise ProblemError(f"题目 {self.slug} 缺少 meta/statement/signature")
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        self.title = str(meta.get("title") or self.slug)
        self.difficulty = str(meta.get("difficulty") or "easy")
        self.time_limit_ms = int(meta.get("time_limit_ms") or 2000)
        self.memory_limit_mb = int(meta.get("memory_limit_mb") or 256)
        self.tags = [str(t) for t in (meta.get("tags") or [])]
        self.statement_md = statement_path.read_text(encoding="utf-8")
        self.signature = parse_signature(yaml.safe_load(signature_path.read_text(encoding="utf-8")) or {})
        self.tests = parse_tests(tests_path.read_text(encoding="utf-8")) if tests_path.is_file() else []
        self.starter: dict[str, str] = {}
        starter_dir = path / "starter"
        if starter_dir.is_dir():
            for file in starter_dir.iterdir():
                if file.is_file():
                    self.starter[file.stem] = file.read_text(encoding="utf-8")

    def selected_tests(self, *, public_only: bool = False) -> list[TestCase]:
        if public_only:
            return [t for t in self.tests if not t.hidden]
        return list(self.tests)

    def tests_stdin(self, *, public_only: bool = False) -> str:
        return dump_tests(self.selected_tests(public_only=public_only))

    def meta_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "title": self.title,
            "difficulty": self.difficulty,
            "time_limit_ms": self.time_limit_ms,
            "memory_limit_mb": self.memory_limit_mb,
            "tags": self.tags,
        }


class ProblemBank:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PROBLEMS_DIR
        self._items: dict[str, Problem] = {}
        self.reload()

    def reload(self) -> None:
        items: dict[str, Problem] = {}
        if self.root.is_dir():
            for path in sorted(self.root.iterdir()):
                if not path.is_dir() or path.name.startswith("."):
                    continue
                items[path.name] = Problem(path)
        self._items = items

    def list(self) -> list[Problem]:
        return list(self._items.values())

    def get(self, slug: str) -> Problem:
        problem = self._items.get(slug)
        if not problem:
            raise KeyError(slug)
        return problem

    def write_problem(
        self,
        *,
        slug: str,
        title: str,
        difficulty: str,
        time_limit_ms: int,
        memory_limit_mb: int,
        tags: list[str],
        statement_md: str,
        signature: Signature,
        starter: dict[str, str],
        tests: list[TestCase] | None = None,
        overwrite: bool = False,
    ) -> Problem:
        if not _SLUG_RE.match(slug):
            raise ProblemError("slug 只能包含小写字母、数字和连字符")
        dest = self.root / slug
        if dest.exists() and not overwrite:
            raise ProblemError(f"题目已存在: {slug}")
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "starter").mkdir(exist_ok=True)
        meta = {
            "slug": slug,
            "title": title,
            "difficulty": difficulty,
            "time_limit_ms": time_limit_ms,
            "memory_limit_mb": memory_limit_mb,
            "tags": tags,
        }
        (dest / "meta.yaml").write_text(
            yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (dest / "statement.md").write_text(statement_md, encoding="utf-8")
        (dest / "signature.yaml").write_text(
            yaml.safe_dump(signature.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        if tests is not None:
            (dest / "tests.jsonl").write_text(dump_tests(tests), encoding="utf-8")
        for lang, code in starter.items():
            (dest / "starter" / f"{lang}{ _starter_ext(lang)}").write_text(code, encoding="utf-8")
        problem = Problem(dest)
        self._items[slug] = problem
        return problem

    def write_tests(self, slug: str, tests: list[TestCase], append: bool = False) -> Problem:
        problem = self.get(slug)
        merged = list(problem.tests) + tests if append else tests
        (problem.path / "tests.jsonl").write_text(dump_tests(merged), encoding="utf-8")
        self._items[slug] = Problem(problem.path)
        return self._items[slug]


def _starter_ext(lang: str) -> str:
    return {
        "python3": ".py",
        "c": ".c",
        "cpp17": ".cpp",
        "javascript": ".js",
        "go": ".go",
        "rust": ".rs",
        "zig": ".zig",
        "typescript": ".ts",
    }.get(lang, ".txt")


bank = ProblemBank()
