#!/usr/bin/env python3
"""Refresh universe_review.json after an agent/reviewer edits market_universe.csv."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from build_market_universe import write_review


def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args();run=a.run_dir
    with (run/"market_universe.csv").open("r",encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
    meta=json.loads((run/"run_metadata.json").read_text(encoding="utf-8"))
    review=write_review(run,rows,meta)
    print(json.dumps({"total_entities":review["total_entities"],"buckets":{k:len(v) for k,v in review["buckets"].items()},"bucket_audit":review["bucket_audit"]},ensure_ascii=False))
    return 0
if __name__=="__main__":raise SystemExit(main())
