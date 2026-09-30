#!/usr/bin/env python3
"""Programmatically retrieve and rank CKAN datasets for business-entity signals."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
import ssl
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import certifi

DEFAULT_API = "https://data.gov.au/data/api/3/action/package_search"
KEYWORD_WEIGHTS = {
    "abn": 8, "acn": 7, "australian business number": 8, "company": 5,
    "companies": 5, "business": 5, "businesses": 5, "supplier": 5,
    "suppliers": 5, "contractor": 5, "contractors": 5, "procurement": 5,
    "tender": 4, "tenders": 4, "licence": 4, "license": 4, "charity": 5,
    "charities": 5, "organisation": 3, "organization": 3, "employer": 4,
    "employers": 4, "registered entity": 5, "trading name": 5,
    "developer": 3, "provider": 3, "operator": 3,
}
PREFERRED_FORMATS = {"csv", "xlsx", "xls", "json", "geojson", "xml"}
EXCLUDED_TERMS = {"household", "individuals", "population", "weather", "traffic"}


def normalise_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def resource_formats(dataset: dict[str, Any]) -> list[str]:
    formats = {normalise_text(r.get("format")) for r in dataset.get("resources", []) if normalise_text(r.get("format"))}
    return sorted(formats) or ["unknown"]


def rank_dataset(dataset: dict[str, Any]) -> tuple[int, str]:
    """Return a deterministic score and compact, data-derived rationale."""
    title = normalise_text(dataset.get("title"))
    notes = normalise_text(dataset.get("notes"))
    tags = " ".join(normalise_text(tag.get("name")) for tag in dataset.get("tags", []))
    text, title_text = f"{title} {notes} {tags}", f"{title} {tags}"
    matched = [(term, weight) for term, weight in KEYWORD_WEIGHTS.items() if term in text]
    score = sum(weight for _, weight in matched) + sum(weight for term, weight in matched if term in title_text)
    formats = resource_formats(dataset)
    if any(fmt in PREFERRED_FORMATS for fmt in formats): score += 2
    if dataset.get("organization"): score += 1
    if any(term in text for term in EXCLUDED_TERMS): score -= 5
    strongest = sorted(matched, key=lambda item: (-item[1], item[0]))[:3]
    reason = ("Metadata signals: " + ", ".join(term for term, _ in strongest)) if strongest else "No direct business-entity metadata signal; retained only by relative rank"
    if any(fmt in PREFERRED_FORMATS for fmt in formats): reason += "; machine-readable resource available"
    return score, reason


def confidence(score: int) -> str:
    return "high" if score >= 18 else "medium" if score >= 9 else "low"


def fetch_catalogue(api_url: str, rows: int, search_term: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"q": search_term, "rows": rows, "start": 0, "sort": "score desc, metadata_modified desc"})
    request = urllib.request.Request(f"{api_url}?{query}", headers={"User-Agent": "firmable-assignment-discovery/0.1"})
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=45, context=ssl_context) as response:
        payload = json.load(response)
    if not payload.get("success"): raise RuntimeError(f"CKAN API returned unsuccessful payload: {payload.get('error')}")
    return payload


def catalogue_row(dataset: dict[str, Any], score: int, reason: str) -> dict[str, str]:
    organisation = dataset.get("organization") or {}
    return {
        "dataset_id": str(dataset.get("id", "")), "title": str(dataset.get("title", "")),
        "publisher": str(organisation.get("title") or organisation.get("name") or "unknown"),
        "resource_formats": ";".join(resource_formats(dataset)), "confidence": confidence(score),
        "score": str(score), "reason": reason, "dataset_url": str(dataset.get("url", "")),
    }


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=DEFAULT_API)
    parser.add_argument("--records-per-query", type=int, default=75)
    parser.add_argument("--queries", default="business,company,supplier,procurement,tender,charity,abn")
    parser.add_argument("--shortlist-size", type=int, default=50)
    parser.add_argument("--audit-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260929)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    if args.records_per_query < 1: parser.error("--records-per-query must be positive")
    if args.shortlist_size < args.audit_size: parser.error("--shortlist-size must be at least --audit-size")
    queries = [query.strip() for query in args.queries.split(",") if query.strip()]
    if not queries: parser.error("--queries must contain at least one search term")
    payloads = []
    by_id: dict[str, dict[str, Any]] = {}
    for query in queries:
        payload = fetch_catalogue(args.api_url, args.records_per_query, query)
        payloads.append({"query": query, "payload": payload})
        for dataset in payload["result"].get("results", []):
            by_id.setdefault(str(dataset.get("id", "")), dataset)
    datasets = list(by_id.values())
    if len(datasets) < 200: raise RuntimeError(f"CKAN returned only {len(datasets)} records; expected at least 200")
    ranked = []
    for dataset in datasets:
        score, reason = rank_dataset(dataset)
        ranked.append((score, normalise_text(dataset.get("title")), str(dataset.get("id", "")), catalogue_row(dataset, score, reason)))
    ranked.sort(key=lambda entry: (-entry[0], entry[1], entry[2]))
    shortlist = [entry[3] for entry in ranked[:args.shortlist_size]]
    if len(shortlist) != args.shortlist_size: raise RuntimeError("Not enough catalogue records to produce shortlist")
    raw_path = args.output_dir / "manifests" / "ckan_package_search.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(payloads, indent=2), encoding="utf-8")
    manifest = {
        "api_url": args.api_url, "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "queries": queries, "requested_records_per_query": args.records_per_query,
        "unique_received_records": len(datasets), "sort": "score desc, metadata_modified desc",
        "raw_response": str(raw_path), "raw_response_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "ranking_version": "metadata-keywords-v1", "audit_seed": args.seed,
    }
    (args.output_dir / "manifests" / "discovery_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    fields = ["dataset_id", "title", "publisher", "resource_formats", "confidence", "score", "reason", "dataset_url"]
    write_csv(args.output_dir / "shortlist.csv", shortlist, fields)
    audit_indices = sorted(random.Random(args.seed).sample(range(len(shortlist)), args.audit_size))
    audit_rows = []
    for index in audit_indices:
        row = dict(shortlist[index])
        row.update({"shortlist_rank": str(index + 1), "contains_business_entities": "", "review_notes": ""})
        audit_rows.append(row)
    write_csv(args.output_dir / "reviews" / "shortlist_audit.csv", audit_rows, ["shortlist_rank", *fields, "contains_business_entities", "review_notes"])
    print(f"Retrieved {len(datasets)} catalogue records; wrote {len(shortlist)} shortlist records.")
    print(f"Audit template: {args.output_dir / 'reviews' / 'shortlist_audit.csv'} ({len(audit_rows)} seeded rows)")
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"Discovery failed: {error}", file=sys.stderr); raise SystemExit(1)
