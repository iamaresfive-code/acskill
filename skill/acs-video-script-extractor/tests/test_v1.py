#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(*args: object) -> str:
    process = subprocess.run(
        [sys.executable, *map(str, args)], capture_output=True, text=True, check=False
    )
    if process.returncode != 0:
        raise AssertionError(
            f"command failed: {args}\nstdout={process.stdout}\nstderr={process.stderr}"
        )
    return process.stdout


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        source_hash = "abc123"
        first = {
            "source_sha256": source_hash,
            "model": "large-v3",
            "duration": 12.0,
            "segments": [
                {"start": 0.0, "end": 4.0, "text": "今年招生一百人"},
                {"start": 4.0, "end": 8.0, "text": "这个项目不会取消"},
                {"start": 8.0, "end": 12.0, "text": "负责人是 Alice"},
            ],
        }
        second = {
            "source_sha256": source_hash,
            "model": "medium",
            "duration": 12.1,
            "segments": [
                {"start": 0.0, "end": 4.0, "text": "今年招生一千人"},
                {"start": 4.0, "end": 8.0, "text": "这个项目会取消"},
                {"start": 8.0, "end": 12.0, "text": "负责人是 Alis"},
            ],
        }
        write_json(out / "raw-large-v3.json", first)
        write_json(out / "raw-medium.json", second)
        (out / "raw-large-v3-timestamped.txt").write_text("ok\n", encoding="utf-8")
        (out / "raw-medium-timestamped.txt").write_text("ok\n", encoding="utf-8")
        write_json(
            out / "run-manifest.json",
            {
                "source_sha256": source_hash,
                "results": [
                    {
                        "model": "large-v3",
                        "json": "raw-large-v3.json",
                        "timestamped_text": "raw-large-v3-timestamped.txt",
                    },
                    {
                        "model": "medium",
                        "json": "raw-medium.json",
                        "timestamped_text": "raw-medium-timestamped.txt",
                    },
                ],
                "failures": [],
            },
        )
        write_json(
            out / "source-probe.json",
            {"source_sha256": source_hash, "duration": 12.0, "streams": [{"codec_type": "video"}]},
        )

        run(
            SCRIPTS / "compare_transcripts.py",
            out / "raw-large-v3.json",
            out / "raw-medium.json",
            "--output-dir",
            out,
        )
        review = json.loads((out / "review-points.json").read_text(encoding="utf-8"))
        assert review["points"]
        reasons = {reason for point in review["points"] for reason in point["reasons"]}
        assert "数字/日期风险" in reasons
        assert "否定词风险" in reasons
        assert any(point["risk_score"] >= 6 for point in review["points"])

        for name in ("逐字稿-校对版.md", "文案-还原整理版.md", "待确认疑点.md"):
            (out / name).write_text(f"# {name}\n\n测试内容\n", encoding="utf-8")

        result = run(SCRIPTS / "validate_outputs.py", out)
        assert "PASS｜完整交付有效" in result

    print("PASS: acs-video-script-extractor v1 smoke tests")


if __name__ == "__main__":
    main()
