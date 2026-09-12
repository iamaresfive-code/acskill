#!/usr/bin/env python3
"""GEO v2.2/v2.2.1 regression gate plus focused suites."""
from __future__ import annotations
from test_v22_core import main as run_core
from test_stage24 import main as run_stage24
from test_report_layer import main as run_report_layer
from test_empty_audit_gate import main as run_empty_audit_gate
from test_first_run_patch import main as run_first_run_patch


def main():
    rc=run_core()
    if rc:return rc
    rc=run_stage24()
    if rc:return rc
    rc=run_report_layer()
    if rc:return rc
    rc=run_empty_audit_gate()
    if rc:return rc
    return run_first_run_patch()


if __name__=="__main__":raise SystemExit(main())
