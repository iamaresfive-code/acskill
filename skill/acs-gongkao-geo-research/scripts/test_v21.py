#!/usr/bin/env python3
"""Compatibility entrypoint: v2.1.1 supersedes the v2.1 regression suite."""
from __future__ import annotations
from test_v211 import main

if __name__ == "__main__":
    print("test_v21.py 已由 v2.1.1 回归套件接管；正在运行 test_v211.py。")
    raise SystemExit(main())
