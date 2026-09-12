#!/usr/bin/env python3
"""GEO v2.2 regression gate plus the Stage 2.4 Target Closure focused suite."""
from __future__ import annotations
from test_v22_core import main as run_core
from test_stage24 import main as run_stage24


def main():
    rc=run_core()
    if rc:return rc
    return run_stage24()


if __name__=="__main__":raise SystemExit(main())
