#!/usr/bin/env python3
"""Fetch CKAN package metadata for explicitly selected Phase 2 candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import certifi

PACKAGE_SHOW = "https://data.gov.au/data/api/3/action/package_show"
DEFAULT_IDS = [
    "5bd7fcab-e315-42cb-8daf-50b7efc2027e",  # ABN Bulk Extract
    "7b8656f9-606d-4337-af29-66b89b2eeefb",  # ASIC Company
    "ab7eddce-84df-4098-bc8f-500d0d9776d1",  # ASIC AFS Licensee
    "fa0b0d71-b8b8-4af8-bc59-0b000ce0d5e4",  # ASIC Credit Licensee
    "c2524c87-cea4-4636-acac-599a82048a26",  # Corporate Tax Transparency
    "ff6905d6-9d5d-4ef1-8478-72b833864fb7",  # ACNC 2023 AIS
]


def package_show(dataset_id: str) -> dict:
    query = urllib.parse.urlencode({"id": dataset_id})
    request = urllib.request.Request(f"{PACKAGE_SHOW}?{query}", headers={"User-Agent": "firmable-assignment-inventory/0.1"})
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=45, context=context) as response:
        payload = json.load(response)
    if not payload.get("success"):
        raise RuntimeError(f"package_show failed for {dataset_id}: {payload.get('error')}")
    return payload["result"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", action="append", dest="dataset_ids")
    parser.add_argument("--output", type=Path, default=Path("outputs/manifests/phase2_package_metadata.json"))
    args = parser.parse_args()
    dataset_ids = args.dataset_ids or DEFAULT_IDS
    packages = [package_show(dataset_id) for dataset_id in dataset_ids]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"retrieved_at_utc": datetime.now(UTC).isoformat(), "packages": packages}, indent=2), encoding="utf-8")
    print(f"Wrote metadata for {len(packages)} packages to {args.output}")
    print(hashlib.sha256(args.output.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Inventory failed: {error}", file=sys.stderr)
        raise SystemExit(1)
