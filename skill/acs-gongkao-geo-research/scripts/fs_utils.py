#!/usr/bin/env python3
"""Filesystem helpers for GEO render/research pipelines."""
from __future__ import annotations

import os
import time
from pathlib import Path


class DirectoryError(RuntimeError):
    pass


def ensure_directory(path: Path, *, writable: bool = True, retries: int = 2) -> Path:
    """Create a directory idempotently and fail with a precise diagnosis.

    This intentionally does more than Path.mkdir(exist_ok=True): it distinguishes
    an existing non-directory path, parent/permission issues, and transient races.
    """
    path = Path(path)
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            if path.exists():
                if not path.is_dir():
                    raise DirectoryError(f"路径已存在但不是目录：{path}")
            else:
                os.makedirs(path, exist_ok=True)
            if writable and not os.access(path, os.W_OK):
                raise DirectoryError(f"目录不可写：{path}")
            return path
        except DirectoryError:
            raise
        except (PermissionError, OSError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(0.05 * (attempt + 1))
                continue
            raise DirectoryError(f"无法准备目录 {path}：{exc}") from exc
    raise DirectoryError(f"无法准备目录 {path}：{last}")
