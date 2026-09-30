#!/usr/bin/env python3
"""Emit validated canonical observations and source-level extraction metrics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent_pipeline import read_jsonl
from contracts import ContractError, load_ontology, validate_config
from extractor import extract_record


def extract_source(config_path: Path, sample_path: Path, output_path: Path, ingested_at: str) -> dict[str, Any]:
    """Extract one held-out sample, retaining every successful canonical observation."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    ontology = load_ontology()
    validate_config(config, ontology)
    rows = read_jsonl(sample_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    field_counts: Counter[str] = Counter()
    record_ids: set[str] = set()
    errors: list[dict[str, str]] = []
    extracted = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for item in rows:
            try:
                observation = extract_record(item["raw"], config, ingested_at=ingested_at)
                record_id = observation["source_record_id"]
                if record_id in record_ids:
                    raise ContractError(f"Duplicate source_record_id: {record_id}")
                record_ids.add(record_id)
                handle.write(json.dumps(observation, sort_keys=True) + "\n")
                extracted += 1
                field_counts.update(observation["claims"].keys())
            except (ContractError, KeyError, ValueError) as error:
                errors.append({"source_record_id": str(item.get("source_record_id", "unknown")), "message": str(error)})
    return {
        "source_id": config["source"]["source_id"],
        "config_path": str(config_path),
        "sample_path": str(sample_path),
        "observation_path": str(output_path),
        "input_records": len(rows),
        "extracted_records": extracted,
        "unique_source_record_ids": len(record_ids),
        "field_coverage": {field: round(count / len(rows), 3) for field, count in sorted(field_counts.items())},
        "unmapped_fields": config["unmapped_fields"],
        "errors": errors,
        "passes": extracted == len(rows) and len(record_ids) == len(rows) and not errors,
    }


def run(root: Path, output_dir: Path, ingested_at: str) -> dict[str, Any]:
    metrics = []
    for config_path in sorted((root / "configs").glob("*.json")):
        source_id = json.loads(config_path.read_text(encoding="utf-8"))["source"]["source_id"]
        metrics.append(extract_source(
            config_path,
            root / "data" / "samples" / source_id / "heldout.jsonl",
            output_dir / f"{source_id}.jsonl",
            ingested_at,
        ))
    summary = {
        "phase": 4,
        "ingested_at": ingested_at,
        "sources": metrics,
        "total_input_records": sum(item["input_records"] for item in metrics),
        "total_observations": sum(item["extracted_records"] for item in metrics),
        "all_sources_pass": all(item["passes"] for item in metrics),
    }
    (output_dir / "extraction_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/observations"))
    parser.add_argument("--ingested-at", help="ISO-8601 timestamp; defaults to this run's UTC time")
    args = parser.parse_args()
    ingested_at = args.ingested_at or datetime.now(UTC).isoformat()
    output_dir = args.output_dir if args.output_dir.is_absolute() else args.root / args.output_dir
    summary = run(args.root, output_dir, ingested_at)
    print(json.dumps({key: summary[key] for key in ("total_input_records", "total_observations", "all_sources_pass")}, indent=2))
    return 0 if summary["all_sources_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
