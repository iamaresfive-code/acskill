#!/usr/bin/env python3
from __future__ import annotations
import os, time
from pathlib import Path


def ensure_directory(path: str | Path, retries: int = 2) -> Path:
    p = Path(path)
    if p.exists() and not p.is_dir():
        raise NotADirectoryError(f"路径已存在但不是目录：{p}")
    last = None
    for attempt in range(retries + 1):
        try:
            os.makedirs(p, exist_ok=True)
            if not p.is_dir():
                raise NotADirectoryError(f"无法创建目录：{p}")
            probe = p / ".write-probe.tmp"
            try:
                probe.write_text("ok", encoding="utf-8")
            finally:
                probe.unlink(missing_ok=True)
            return p
        except (PermissionError, OSError) as exc:
            last = exc
            if attempt >= retries:
                break
            time.sleep(0.05 * (attempt + 1))
    raise PermissionError(f"目录不可写：{p}；原因：{last}")
