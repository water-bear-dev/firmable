"""Generic extractor for bounded, declarative mapping configurations."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from contracts import ContractError, load_ontology, valid_abn, validate_config, validate_observation


def apply_operations(value: Any, row: dict[str, Any], operations: list[dict[str, Any]]) -> Any:
    for operation in operations:
        name = operation["op"]
        if name == "coalesce": value = next((row.get(field) for field in operation["fields"] if row.get(field) not in (None, "")), value)
        elif name == "concat": value = operation.get("separator", " ").join(str(row.get(field, "")).strip() for field in operation["fields"] if row.get(field) not in (None, ""))
        elif name == "default" and value in (None, ""): value = operation["value"]
        elif value not in (None, ""):
            if name == "strip": value = str(value).strip()
            elif name == "upper": value = str(value).upper()
            elif name == "lower": value = str(value).lower()
            elif name == "digits_only": value = re.sub(r"\D", "", str(value))
            elif name == "regex_extract":
                match = re.search(operation["pattern"], str(value)); value = match.group(operation.get("group", 1)) if match else None
            elif name == "parse_date":
                value = datetime.strptime(str(value), operation["format"]).date().isoformat()
            elif name == "validate_abn" and not valid_abn(str(value)): value = None
    return value


def extract_record(row: dict[str, Any], config: dict[str, Any], observed_at: str | None = None, ingested_at: str | None = None, ontology_path: str = "firmable_ontology.yaml") -> dict[str, Any]:
    ontology = load_ontology(ontology_path)
    validate_config(config, ontology)
    source_fields = config["record_id"]["source_fields"]
    record_id = config["record_id"].get("separator", "|").join(str(row[field]).strip() for field in source_fields)
    if not record_id: raise ContractError("Empty source record ID")
    claims = {}
    for mapping in config["field_mappings"]:
        source_field = mapping.get("source_field")
        value = row.get(source_field) if source_field else None
        value = apply_operations(value, row, mapping.get("operations", []))
        if value not in (None, ""):
            claims[mapping["destination"]] = {"value": value, "raw_value": row.get(source_field), "field_confidence": mapping["field_confidence"], "derivation_level": mapping.get("derivation_level", "L0")}
    now = ingested_at or datetime.now(UTC).isoformat()
    observation = {"source_id": config["source"]["source_id"], "source_record_id": record_id, "observed_at": observed_at or config["source"].get("observed_at") or now, "ingested_at": now, "licence": config["source"]["licence"], "extractor_version": config.get("extractor_version", "0.1.0"), "source_reliability": config["source"].get("source_reliability", 0.5), "claims": claims}
    validate_observation(observation, ontology)
    return observation
