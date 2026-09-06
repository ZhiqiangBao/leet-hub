from __future__ import annotations

import math
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .base import RunResult

_UNSHARE_OK: bool | None = None


def _can_unshare() -> bool:
    global _UNSHARE_OK
    if _UNSHARE_OK is not None:
        return _UNSHARE_OK
    if not sys.platform.startswith("linux") or not shutil.which("unshare"):
        _UNSHARE_OK = False
        return False
    try:
        proc = subprocess.run(
            ["unshare", "--net", "true"],
            capture_output=True,
            timeout=2,
            check=False,
        )
        _UNSHARE_OK = proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        _UNSHARE_OK = False
    return _UNSHARE_OK


def wrap_linux(
    argv: list[str],
    time_ms: int,
    memory_mb: int,
    *,
    for_compile: bool = False,
) -> list[str]:
    """Wrap argv with Ubuntu-native unshare/prlimit when present.

    Compile must not use a tight nproc/AS cap: g++ spawns cc1plus, and
    RLIMIT_NPROC is counted per user. A desktop session already has more
    than 64 processes, which yields posix_spawn EAGAIN (资源暂时不可用).
    """
    if not sys.platform.startswith("linux"):
        return argv
    cmd: list[str] = []
    if not for_compile and _can_unshare():
        cmd += ["unshare", "--net"]
    if shutil.which("prlimit"):
        cpu_sec = max(1, math.ceil(time_ms / 1000))
        if for_compile:
            as_bytes = 8 * 1024 * 1024 * 1024
            cmd += [
                "prlimit",
                f"--cpu={cpu_sec}",
                f"--as={as_bytes}",
                "--fsize=268435456",
                "--",
            ]
        else:
            as_bytes = max(memory_mb, 256) * 1024 * 1024 * 4
            cmd += [
                "prlimit",
                f"--cpu={cpu_sec}",
                f"--as={as_bytes}",
                "--nproc=4096",
                "--fsize=33554432",
                "--",
            ]
    cmd += argv
    return cmd


def run_limited(
    argv: list[str],
    *,
    cwd: Path,
    stdin: str,
    time_ms: int,
    memory_mb: int,
    for_compile: bool = False,
    extra_env: dict[str, str] | None = None,
) -> RunResult:
    wall = time_ms / 1000.0 + 1.0
    cmd = wrap_linux(argv, time_ms, memory_mb, for_compile=for_compile)

    scratch = Path(cwd) / ".scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    scratch_s = str(scratch)
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPYCACHEPREFIX": scratch_s,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
        "TMPDIR": scratch_s,
        "TMP": scratch_s,
        "TEMP": scratch_s,
        "XDG_CACHE_HOME": scratch_s,
        "XDG_CONFIG_HOME": scratch_s,
    }
    if extra_env:
        env.update(extra_env)
    start = time.perf_counter()
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=env,
        )
    except FileNotFoundError as exc:
        return RunResult(stderr=str(exc), returncode=127)
    try:
        stdout_b, stderr_b = proc.communicate(stdin.encode("utf-8"), timeout=wall)
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        try:
            proc.communicate(timeout=2)
        except Exception:
            pass
        return RunResult(tle=True, time_ms=time_ms, returncode=-1)
    elapsed = int((time.perf_counter() - start) * 1000)
    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")
    mle = _looks_like_mle(proc.returncode, stderr)
    return RunResult(
        stdout=stdout,
        stderr=stderr,
        returncode=proc.returncode,
        time_ms=elapsed,
        mle=mle,
    )


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        if sys.platform.startswith("win"):
            proc.kill()
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        try:
            proc.kill()
        except OSError:
            pass


def _looks_like_mle(returncode: int, stderr: str) -> bool:
    text = stderr.lower()
    if "std::bad_alloc" in text or "memoryerror" in text:
        return True
    if returncode in {137, -9} and "killed" in text:
        return True
    return False
