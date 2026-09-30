#!/usr/bin/env python3
"""Build provenance-rich profiles from accepted identifier-linked observations."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def entity_key(observation: dict[str, Any]) -> str | None:
    abn = observation.get("claims", {}).get("entity.abn")
    return f"abn:{abn['value']}" if abn else None


def field_candidates(observations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        for field, claim in observation["claims"].items():
            candidates[field].append({
                "value": claim["value"], "raw_value": claim["raw_value"],
                "mapping_confidence": claim["field_confidence"],
                "source_reliability": observation["source_reliability"],
                "score": round(claim["field_confidence"] * observation["source_reliability"], 4),
                "source_id": observation["source_id"], "source_record_id": observation["source_record_id"],
                "observed_at": observation["observed_at"], "licence": observation["licence"],
            })
    return candidates


def build_profile(key: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
    fields = {}
    for field, candidates in field_candidates(observations).items():
        ranked = sorted(candidates, key=lambda item: (-item["score"], item["source_id"], item["source_record_id"]))
        winner = ranked[0]
        alternates = [item for item in ranked[1:] if item["value"] != winner["value"]]
        fields[field] = {
            "value": winner["value"], "field_confidence": winner["score"],
            "provenance": {key: winner[key] for key in ("source_id", "source_record_id", "raw_value", "observed_at", "licence", "mapping_confidence", "source_reliability")},
            "alternates": alternates,
            "conflict_resolution": "highest mapping_confidence × source_reliability; alternatives retained" if alternates else "no conflicting observed value",
        }
    return {"entity_key": key, "link_confidence": 0.99, "linked_observation_count": len(observations), "fields": fields}


def build_profiles(observations: list[dict[str, Any]], selected_keys: list[str]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        key = entity_key(observation)
        if key in selected_keys:
            groups[key].append(observation)
    return [build_profile(key, groups[key]) for key in selected_keys]


def counterfactual(profiles: list[dict[str, Any]], observations: list[dict[str, Any]], selected_keys: list[str]) -> dict[str, Any]:
    sources = sorted({item["source_id"] for item in observations})
    result = {}
    original = {profile["entity_key"]: profile for profile in profiles}
    for source_id in sources:
        without_source = build_profiles([item for item in observations if item["source_id"] != source_id], selected_keys)
        changed_profiles = changed_fields = 0
        for profile in without_source:
            before, after = original[profile["entity_key"]]["fields"], profile["fields"]
            changes = {field for field in set(before) | set(after) if before.get(field, {}).get("value") != after.get(field, {}).get("value")}
            if changes:
                changed_profiles += 1
                changed_fields += len(changes)
        result[source_id] = {"profiles_changed": changed_profiles, "fields_changed": changed_fields}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--count", type=int, default=50)
    args = parser.parse_args()
    links = read_jsonl(args.root / "outputs/proposed_links.jsonl")
    keys = sorted({link["entity_key"] for link in links})[:args.count]
    if len(keys) < args.count:
        raise SystemExit(f"Need {args.count} linked entities; found {len(keys)}")
    observations = []
    for path in sorted((args.root / "outputs/observations/expanded").glob("*.jsonl")):
        observations.extend(read_jsonl(path))
    profiles = build_profiles(observations, keys)
    output_path = args.root / "outputs/profiles.jsonl"
    with output_path.open("w", encoding="utf-8") as handle:
        for profile in profiles:
            handle.write(json.dumps(profile, sort_keys=True) + "\n")
    deletion_impact = counterfactual(profiles, observations, keys)
    summary = {"profile_count": len(profiles), "entity_keys": keys, "counterfactual": deletion_impact}
    (args.root / "outputs/profile_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (args.root / "outputs/source_deletion_counterfactual.json").write_text(json.dumps(deletion_impact, indent=2), encoding="utf-8")
    print(json.dumps({"profile_count": len(profiles), "counterfactual": summary["counterfactual"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
