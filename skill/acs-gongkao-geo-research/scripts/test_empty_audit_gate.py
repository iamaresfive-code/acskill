#!/usr/bin/env python3
"""Focused v2.2 regression for header-only release audit false-greens."""
from __future__ import annotations
import csv,json,subprocess,sys,tempfile
from pathlib import Path
from test_v22_core import fixture

HERE=Path(__file__).resolve().parent
VALIDATOR=HERE/"validate_run.py"


def wcsv(path:Path,fields:list[str]):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        csv.DictWriter(f,fieldnames=fields).writeheader()


def read_answers(path:Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_answers(path:Path,rows:list[dict]):
    path.write_text("\n".join(json.dumps(row,ensure_ascii=False) for row in rows)+"\n",encoding="utf-8")


def release_meta(run:Path):
    path=run/"run_metadata.json";meta=json.loads(path.read_text(encoding="utf-8"))
    meta.update(measurement_profile="release",repeat_runs_expected=3,fresh_context_required=True)
    path.write_text(json.dumps(meta,ensure_ascii=False),encoding="utf-8")


def strict_measurement(run:Path):
    return subprocess.run(
        [sys.executable,str(VALIDATOR),str(run),"--stage","measurement","--strict"],
        cwd=HERE,capture_output=True,text=True,encoding="utf-8"
    )


def main():
    checks=0
    with tempfile.TemporaryDirectory() as td:
        run=Path(td);fixture(run);release_meta(run)
        answers=read_answers(run/"ai_answers.jsonl");answers[0]["citations"]=["https://jia.example/source"]
        write_answers(run/"ai_answers.jsonl",answers)
        wcsv(run/"citation_audit.csv",[
            "mention_id","answer_id","entity_id","canonical_name","answer_citation_count",
            "candidate_citation_refs","linked_citation_refs","citation_linked","link_basis","review_status","notes"
        ])
        probe=strict_measurement(run);out=probe.stdout+probe.stderr
        assert probe.returncode!=0,out
        assert "[empty-citation-audit]" in out,out
        checks+=1

    with tempfile.TemporaryDirectory() as td:
        run=Path(td);fixture(run);release_meta(run)
        answers=read_answers(run/"ai_answers.jsonl")
        # The core fixture has 8 Answer Cells. Add two unique run-2 cells so the release
        # annotation-recheck >=10 threshold is exercised through the real CLI path.
        for source in answers[:2]:
            extra=dict(source);extra["answer_id"]=source["answer_id"]+"-R2";extra["sample_run"]=2
            extra["context_id"]=extra["answer_id"];answers.append(extra)
        write_answers(run/"ai_answers.jsonl",answers)
        wcsv(run/"annotation_rechecks.csv",[
            "review_id","answer_id","first_positive_set","second_positive_set","first_intents",
            "second_intents","disagreement","resolution","reviewer","notes"
        ])
        probe=strict_measurement(run);out=probe.stdout+probe.stderr
        assert probe.returncode!=0,out
        assert "[empty-annotation-rechecks]" in out,out
        checks+=1

    print(f"PASS: v2.2 empty-audit release gate ({checks} checks)")
    return 0


if __name__=="__main__":raise SystemExit(main())
