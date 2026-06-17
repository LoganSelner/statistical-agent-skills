#!/usr/bin/env python3
"""Download the InfiAgent-DABench dev set into data/benchmarks/dabench/ with hashes.

Fetches da-dev-questions.jsonl, da-dev-labels.jsonl, and the referenced CSV tables from
the HuggingFace dataset, then writes a hashes.json manifest (sha256 per file) for
provenance (ROADMAP §9). The data dir is gitignored.

Usage:  python scripts/fetch_dabench.py   (or: make dabench-data)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import quote
import urllib.request

REPO_ROOT = Path(__file__).resolve().parents[1]
DEST = REPO_ROOT / "data" / "benchmarks" / "dabench"
BASE = "https://huggingface.co/datasets/infiagent/DABench/resolve/main"


def _download(url: str, path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "statskills"})
    with urllib.request.urlopen(request) as response:
        path.write_bytes(response.read())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    tables = DEST / "da-dev-tables"
    tables.mkdir(parents=True, exist_ok=True)

    print("Downloading questions + labels ...")
    for name in ("da-dev-questions.jsonl", "da-dev-labels.jsonl"):
        _download(f"{BASE}/{name}", DEST / name)

    questions = [
        json.loads(line)
        for line in (DEST / "da-dev-questions.jsonl").read_text().splitlines()
        if line.strip()
    ]
    file_names = sorted({q["file_name"] for q in questions})
    print(f"Downloading {len(file_names)} CSV tables ...")
    for file_name in file_names:
        # File names may contain spaces (e.g. "beauty and the labor market.csv").
        _download(f"{BASE}/da-dev-tables/{quote(file_name)}", tables / file_name)

    manifest = {
        str(p.relative_to(DEST)): _sha256(p)
        for p in sorted(DEST.rglob("*"))
        if p.is_file() and p.name != "hashes.json"
    }
    (DEST / "hashes.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nDownloaded {len(manifest)} files to {DEST}")
    print(f"Recorded sha256 hashes in {DEST / 'hashes.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
