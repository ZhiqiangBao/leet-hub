from __future__ import annotations

import shutil

from ..base import LanguageAdapter


class _StubAdapter(LanguageAdapter):
    implemented = False

    def wrap(self, user_code: str, signature: dict) -> str:
        raise NotImplementedError(f"{self.id} adapter is a reserved stub")

    def run_argv(self, workdir: str) -> list[str]:
        raise NotImplementedError(f"{self.id} adapter is a reserved stub")


class GoAdapter(_StubAdapter):
    id = "go"
    display_name = "Go"
    source_filename = "solution.go"

    def detect(self) -> bool:
        return shutil.which("go") is not None


class RustAdapter(_StubAdapter):
    id = "rust"
    display_name = "Rust"
    source_filename = "solution.rs"

    def detect(self) -> bool:
        return shutil.which("rustc") is not None


class ZigAdapter(_StubAdapter):
    id = "zig"
    display_name = "Zig"
    source_filename = "solution.zig"

    def detect(self) -> bool:
        return shutil.which("zig") is not None
