from __future__ import annotations

from ..base import LanguageAdapter
from .cpp17 import Cpp17Adapter
from .python3 import Python3Adapter
from .stubs import GoAdapter, JavascriptAdapter, RustAdapter, ZigAdapter

ADAPTERS: dict[str, LanguageAdapter] = {
    adapter.id: adapter
    for adapter in (
        Python3Adapter(),
        Cpp17Adapter(),
        JavascriptAdapter(),
        GoAdapter(),
        RustAdapter(),
        ZigAdapter(),
    )
}


def get_adapter(language: str) -> LanguageAdapter | None:
    return ADAPTERS.get(language)


def language_status() -> list[dict]:
    out = []
    for adapter in ADAPTERS.values():
        out.append(
            {
                "id": adapter.id,
                "display_name": adapter.display_name,
                "implemented": adapter.implemented,
                "available": adapter.available(),
                "runtime_detected": adapter.detect(),
                "reason": adapter.reason(),
            }
        )
    return out
