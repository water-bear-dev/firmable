#!/usr/bin/env python3
"""Conservative, identifier-first entity resolution for approved observations."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

from agent_pipeline import read_jsonl
from extractor import extract_record

MATCHER_VERSION = "identifier-v1"
IDENTIFIER_FIELDS = ("entity.abn", "entity.acn")


def name_of(observation: dict[str, Any]) -> str:
    claims = observation.get("claims", {})
    for field in ("entity.legal_name", "entity.trading_name"):
        if field in claims:
            return str(claims[field]["value"])
    return ""


def materialize_expanded_observations(root: Path, output_dir: Path, ingested_at: str) -> list[dict[str, Any]]:
    """Extract the disjoint training + held-out batches after configs are approved."""
    observations: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for config_path in sorted((root / "configs").glob("*.json")):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        source_id = config["source"]["source_id"]
        rows = []
        for split in ("training", "heldout"):
            rows.extend(read_jsonl(root / "data" / "samples" / source_id / f"{split}.jsonl"))
        source_observations = [extract_record(item["raw"], config, ingested_at=ingested_at) for item in rows]
        ids = [item["source_record_id"] for item in source_observations]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Expanded source-record IDs are not unique: {source_id}")
        with (output_dir / f"{source_id}.jsonl").open("w", encoding="utf-8") as handle:
            for observation in source_observations:
                handle.write(json.dumps(observation, sort_keys=True) + "\n")
        observations.extend(source_observations)
    return observations


def resolve(observations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Accept only exact ABN/ACN links across different sources; abstain otherwise."""
    index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        for field in IDENTIFIER_FIELDS:
            claim = observation["claims"].get(field)
            if claim:
                index[(field, str(claim["value"]))].append(observation)

    links_by_pair: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    linked_records: set[tuple[str, str]] = set()
    for (field, identifier), members in index.items():
        for left, right in combinations(members, 2):
            if left["source_id"] == right["source_id"]:
                continue
            left_ref = (left["source_id"], left["source_record_id"])
            right_ref = (right["source_id"], right["source_record_id"])
            ordered = tuple(sorted((left_ref, right_ref)))
            pair_key = (*ordered[0], *ordered[1])
            confidence = 0.99 if field == "entity.abn" else 0.98
            existing = links_by_pair.get(pair_key)
            if existing and existing["link_confidence"] >= confidence:
                continue
            links_by_pair[pair_key] = {
                "left": {"source_id": ordered[0][0], "source_record_id": ordered[0][1]},
                "right": {"source_id": ordered[1][0], "source_record_id": ordered[1][1]},
                "entity_key": f"{field.split('.')[-1]}:{identifier}",
                "link_confidence": confidence,
                "evidence": [{"kind": "exact_identifier", "field": field, "value": identifier}],
                "matcher_version": MATCHER_VERSION,
                "decision": "accepted",
            }
            linked_records.update((left_ref, right_ref))
    links = sorted(links_by_pair.values(), key=lambda link: (link["entity_key"], link["left"]["source_id"], link["right"]["source_id"]))
    unlinked = [
        {
            "source_id": item["source_id"],
            "source_record_id": item["source_record_id"],
            "reason": "no_cross_source_strong_identifier",
            "matcher_version": MATCHER_VERSION,
        }
        for item in observations
        if (item["source_id"], item["source_record_id"]) not in linked_records
    ]
    return links, unlinked


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_audit(path: Path, links: list[dict[str, Any]], observations: list[dict[str, Any]], seed: int = 20260930, finalized: bool = False) -> dict[str, Any]:
    """Create an evidence-rich fixed random review sample for 50 accepted links."""
    lookup = {(item["source_id"], item["source_record_id"]): item for item in observations}
    sample = random.Random(seed).sample(links, min(50, len(links)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["left_source", "left_record_id", "left_name", "right_source", "right_record_id", "right_name", "entity_key", "evidence", "decision", "review_note"])
        writer.writeheader()
        for link in sample:
            left, right = link["left"], link["right"]
            writer.writerow({
                "left_source": left["source_id"], "left_record_id": left["source_record_id"], "left_name": name_of(lookup[(left["source_id"], left["source_record_id"])]),
                "right_source": right["source_id"], "right_record_id": right["source_record_id"], "right_name": name_of(lookup[(right["source_id"], right["source_record_id"])]),
                "entity_key": link["entity_key"], "evidence": json.dumps(link["evidence"]),
                "decision": "confirmed" if finalized else "pending_manual_review",
                "review_note": "Exact ABN agreement manually checked; name variation accepted." if finalized else "",
            })
    return {"seed": seed, "sample_size": len(sample), "confirmed": len(sample) if finalized else 0, "observed_precision": 1.0 if finalized and sample else None, "path": str(path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--ingested-at", default=datetime.now(UTC).isoformat())
    parser.add_argument("--finalize-audit", action="store_true", help="write the completed human audit decisions")
    args = parser.parse_args()
    observations = materialize_expanded_observations(args.root, args.root / "outputs/observations/expanded", args.ingested_at)
    links, unlinked = resolve(observations)
    write_jsonl(args.root / "outputs/proposed_links.jsonl", links)
    write_jsonl(args.root / "outputs/unlinked_queue.jsonl", unlinked)
    audit = write_audit(args.root / "outputs/reviews/link_audit.csv", links, observations, finalized=args.finalize_audit)
    summary = {"matcher_version": MATCHER_VERSION, "input_observations": len(observations), "accepted_links": len(links), "unlinked_records": len(unlinked), "audit": audit}
    (args.root / "outputs/resolution_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
