"""Ontology-derived contracts for declarative mappings and canonical observations."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

ALLOWED_OPERATIONS = {"strip", "upper", "lower", "digits_only", "regex_extract", "coalesce", "concat", "parse_date", "validate_abn", "default"}
DERIVATION_LEVELS = {"L0", "L1", "L2", "L3", "L4"}
REQUIRED_ENVELOPE = {"source_id", "source_record_id", "observed_at", "ingested_at", "licence", "extractor_version"}


class ContractError(ValueError):
    """Raised when a config or emitted observation violates the ontology contract."""


def load_ontology(path: str | Path = "firmable_ontology.yaml") -> dict[str, Any]:
    ontology = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(ontology, dict) or "entity" not in ontology or "observation" not in ontology:
        raise ContractError("Ontology must define entity and observation sections")
    return ontology


def canonical_fields(ontology: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        **{f"entity.{field}": definition for field, definition in ontology["entity"].items()},
        **{f"address.{field}": definition for field, definition in ontology["address"].items()},
    }


def validate_config(config: dict[str, Any], ontology: dict[str, Any]) -> None:
    required = {"version", "source", "record_id", "field_mappings", "unmapped_fields"}
    missing = required - config.keys()
    if missing: raise ContractError(f"Mapping config missing keys: {sorted(missing)}")
    source = config["source"]
    if not isinstance(source, dict) or not source.get("source_id") or not source.get("licence"):
        raise ContractError("source must contain source_id and licence")
    if not config["record_id"].get("source_fields"):
        raise ContractError("record_id must declare one or more source_fields")
    unmapped_fields = config["unmapped_fields"]
    if not isinstance(unmapped_fields, list) or not all(isinstance(field, str) and field for field in unmapped_fields):
        raise ContractError("unmapped_fields must be a list of non-empty source-field names")
    record_id_fields = set(config["record_id"]["source_fields"])
    overlap = record_id_fields.intersection(unmapped_fields)
    if overlap:
        raise ContractError(f"record ID fields cannot be unmapped: {sorted(overlap)}")
    allowed_fields = canonical_fields(ontology)
    destinations: set[str] = set()
    for mapping in config["field_mappings"]:
        destination = mapping.get("destination")
        if destination not in allowed_fields: raise ContractError(f"Unknown ontology destination: {destination}")
        if destination in destinations: raise ContractError(f"Duplicate mapping destination: {destination}")
        destinations.add(destination)
        confidence = mapping.get("field_confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ContractError(f"Invalid field_confidence for {destination}")
        operations = mapping.get("operations", [])
        for operation in operations:
            if operation.get("op") not in ALLOWED_OPERATIONS:
                raise ContractError(f"Unsupported declarative operation: {operation.get('op')}")
        if mapping.get("derivation_level", "L0") not in DERIVATION_LEVELS:
            raise ContractError(f"Invalid derivation_level for {destination}")
        source_field = mapping.get("source_field")
        if source_field is not None and (not isinstance(source_field, str) or not source_field):
            raise ContractError(f"Invalid source_field for {destination}")


def valid_abn(value: str) -> bool:
    if not re.fullmatch(r"\d{11}", value): return False
    weights = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)
    digits = [int(digit) for digit in value]
    digits[0] -= 1
    return sum(digit * weight for digit, weight in zip(digits, weights)) % 89 == 0


def validate_value(value: Any, definition: dict[str, Any]) -> bool:
    if value is None: return True
    field_type = definition.get("type")
    if definition.get("pattern") and not re.fullmatch(definition["pattern"], str(value)): return False
    if field_type == "string": return isinstance(value, str)
    if field_type == "enum": return value in definition["values"]
    if field_type == "date":
        try: date.fromisoformat(str(value)); return True
        except ValueError: return False
    return True


def validate_observation(observation: dict[str, Any], ontology: dict[str, Any]) -> None:
    missing = REQUIRED_ENVELOPE - observation.keys()
    if missing: raise ContractError(f"Observation missing envelope fields: {sorted(missing)}")
    for timestamp in ("observed_at", "ingested_at"):
        try: datetime.fromisoformat(str(observation[timestamp]).replace("Z", "+00:00"))
        except ValueError as error: raise ContractError(f"Invalid {timestamp}") from error
    fields = canonical_fields(ontology)
    for destination, claim in observation.get("claims", {}).items():
        if destination not in fields: raise ContractError(f"Unknown claim destination: {destination}")
        if not isinstance(claim, dict) or not 0 <= claim.get("field_confidence", -1) <= 1:
            raise ContractError(f"Invalid claim confidence: {destination}")
        if claim.get("derivation_level") not in DERIVATION_LEVELS:
            raise ContractError(f"Invalid claim derivation level: {destination}")
        if not validate_value(claim.get("value"), fields[destination]):
            raise ContractError(f"Invalid value for {destination}: {claim.get('value')!r}")
        if destination == "entity.abn" and not valid_abn(str(claim.get("value"))):
            raise ContractError("Invalid ABN checksum")
