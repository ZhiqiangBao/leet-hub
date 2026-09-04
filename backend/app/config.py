from __future__ import annotations

import os
import secrets
from pathlib import Path

ROOT = Path(os.environ.get("LOCAL_LEET_ROOT", Path(__file__).resolve().parents[2]))
PROBLEMS_DIR = Path(os.environ.get("LOCAL_LEET_PROBLEMS", ROOT / "problems"))
DATA_DIR = Path(os.environ.get("LOCAL_LEET_DATA", ROOT / "data"))
FRONTEND_DIST = ROOT / "frontend" / "dist"

HOST = os.environ.get("LOCAL_LEET_HOST", "0.0.0.0")
PORT = int(os.environ.get("LOCAL_LEET_PORT", "8080"))
ADMINS = {
    name.strip()
    for name in os.environ.get("LOCAL_LEET_ADMINS", "").split(",")
    if name.strip()
}

COOKIE_NAME = "local_leet_session"
SOURCE_MAX_BYTES = 256 * 1024


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "tmp").mkdir(parents=True, exist_ok=True)
    PROBLEMS_DIR.mkdir(parents=True, exist_ok=True)


def secret_key() -> str:
    env = os.environ.get("LOCAL_LEET_SECRET")
    if env:
        return env
    ensure_dirs()
    path = DATA_DIR / "secret.txt"
    if not path.exists():
        path.write_text(secrets.token_hex(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()
