"""Force UTF-8 on stdio so Windows cp936 does not scramble JSON."""
from __future__ import annotations

import json
import sys


def configure() -> None:
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        reconf = getattr(stream, "reconfigure", None)
        if reconf is None:
            continue
        try:
            reconf(encoding="utf-8")
        except Exception:
            pass


def dump(obj) -> None:
    configure()
    json.dump(obj, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    print()
