#!/usr/bin/env python3
"""GEO v2.2 regression gate plus the Stage 2.4 and Report Layer focused suites."""
from __future__ import annotations
from test_v22_core import main as run_core
from test_stage24 import main as run_stage24
from test_report_layer import main as run_report_layer


def main():
    rc=run_core()
    if rc:return rc
    rc=run_stage24()
    if rc:return rc
    return run_report_layer()


if __name__=="__main__":raise SystemExit(main())
