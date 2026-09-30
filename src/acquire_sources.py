#!/usr/bin/env python3
"""Download selected Phase 2 resources and write an immutable acquisition manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import certifi


def extension(source: dict) -> str:
    return {"csv": ".csv", "xlsx": ".xlsx", "zip/csv": ".zip"}.get(source["format"], ".zip")


def download(source: dict, raw_dir: Path) -> dict:
    raw_dir.mkdir(parents=True, exist_ok=True)
    destination = raw_dir / f"{source['source_id']}{extension(source)}"
    request = urllib.request.Request(source["url"], headers={"User-Agent": "firmable-assignment-acquisition/0.1"})
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=120, context=context) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
        content_type = response.headers.get("Content-Type")
    return {
        "source_id": source["source_id"], "path": str(destination), "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "content_type": content_type, "bytes_downloaded": destination.stat().st_size,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=Path("data/manifests/selected_sources.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--include-streamed", action="store_true", help="also download sources marked stream_or_sample")
    parser.add_argument("--source-id", action="append", help="download only a named source; repeatable")
    parser.add_argument("--output", type=Path, default=Path("outputs/manifests/acquisition_manifest.json"))
    args = parser.parse_args()
    sources = json.loads(args.sources.read_text(encoding="utf-8"))["sources"]
    selected = [source for source in sources if args.include_streamed or source["acquisition_mode"] == "download"]
    if args.source_id:
        requested = set(args.source_id)
        selected = [source for source in selected if source["source_id"] in requested]
        if not selected:
            parser.error("none of the requested --source-id values are selected")
    records = [download(source, args.raw_dir) for source in selected]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"manifest_version": "1.0", "acquisitions": records}, indent=2), encoding="utf-8")
    print(f"Downloaded {len(records)} resources; manifest: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Acquisition failed: {error}", file=sys.stderr)
        raise SystemExit(1)
