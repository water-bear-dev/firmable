#!/usr/bin/env python3
"""Stateful multi-step agent that produces reviewable declarative mapping configs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from contracts import ContractError, load_ontology, validate_config
from extractor import extract_record


class Provider(Protocol):
    def complete(self, prompt: str) -> tuple[str, dict[str, Any]]: ...


class OpenAIResponsesProvider:
    """Optional provider; uses the official Responses API when a key is supplied."""
    def __init__(self, model: str):
        from openai import OpenAI
        self.client, self.model = OpenAI(), model

    def complete(self, prompt: str) -> tuple[str, dict[str, Any]]:
        response = self.client.responses.create(model=self.model, input=prompt, store=False, reasoning={"effort": "low"})
        usage = getattr(response, "usage", None)
        usage_data = usage.model_dump() if usage else {}
        input_tokens, output_tokens = usage_data.get("input_tokens", 0), usage_data.get("output_tokens", 0)
        # Current gpt-6-luna standard pricing: USD $0.10/M input and $0.50/M output.
        estimated_cost_usd = (input_tokens * 0.10 + output_tokens * 0.50) / 1_000_000
        return response.output_text, {"model": self.model, "response_id": response.id, "usage": usage_data, "estimated_cost_usd": estimated_cost_usd}


class CodexCliProvider:
    """Run a single, read-only Codex CLI turn using the local Codex entitlement.

    Codex plan usage is reported as quota, not a dollar amount, so this provider
    intentionally records usage as unpriced rather than inventing an API-price
    estimate.  ``max_turns`` is the enforceable guard; it defaults to the two
    turns required by the propose/revise workflow.
    """

    def __init__(self, model: str | None, max_turns: int = 2):
        self.model, self.max_turns, self.turns_used = model, max_turns, 0

    def complete(self, prompt: str) -> tuple[str, dict[str, Any]]:
        if self.turns_used >= self.max_turns:
            raise RuntimeError(f"Codex turn limit reached ({self.max_turns}); no further model call was made")
        self.turns_used += 1
        with tempfile.TemporaryDirectory(prefix="firmable-codex-") as temp_dir:
            output_path = Path(temp_dir) / "last_message.txt"
            # The outer automation sandbox can obscure the Git worktree from
            # Codex's trust check. This does not broaden file permissions:
            # Codex remains ephemeral and read-only.
            codex_binary = shutil.which("codex")
            bundled_binary = Path("/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex")
            if not codex_binary and bundled_binary.exists():
                codex_binary = str(bundled_binary)
            if not codex_binary:
                raise RuntimeError("Codex CLI was not found on PATH or in the ChatGPT app bundle")
            command = [codex_binary, "exec", "--ephemeral", "--json", "--sandbox", "read-only", "--skip-git-repo-check", "-o", str(output_path)]
            if self.model:
                command.extend(["--model", self.model])
            command.append("-")
            result = subprocess.run(command, input=prompt, text=True, capture_output=True, cwd=Path.cwd())
            if result.returncode != 0:
                message = result.stderr.strip() or result.stdout.strip() or f"codex exec exited {result.returncode}"
                raise RuntimeError(message)
            if not output_path.exists():
                raise RuntimeError("Codex completed without a final response")
            events = [json.loads(line) for line in result.stdout.splitlines() if line.strip().startswith("{")]
            return output_path.read_text(encoding="utf-8"), {
                "provider": "codex_cli",
                "model": self.model or "Codex default",
                "turn": self.turns_used,
                "max_turns": self.max_turns,
                "usage_events": events[-1:] if events else [],
                "estimated_cost_usd": None,
                "cost_accounting": "Codex plan quota is not dollar-metered by the CLI",
            }


@dataclass
class RunState:
    source_id: str
    run_id: str
    completed_steps: list[str] = field(default_factory=list)
    status: str = "running"
    costs: list[dict[str, Any]] = field(default_factory=list)


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
            if limit and len(rows) >= limit: break
    return rows


def profile(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, list[Any]] = {}
    for item in rows:
        for key, value in item["raw"].items(): values.setdefault(key, []).append(value)
    result = {}
    for key, column in values.items():
        nonempty = [value for value in column if value not in (None, "")]
        result[key] = {"non_null_rate": round(len(nonempty) / len(column), 3), "distinct_count": len({str(value) for value in nonempty}), "examples": [str(value)[:120] for value in nonempty[:3]]}
    return result


def validation_report(config: dict[str, Any], training: list[dict[str, Any]], heldout: list[dict[str, Any]], ontology: dict[str, Any]) -> dict[str, Any]:
    errors, extracted, field_counts, record_ids = [], 0, {}, []
    available = set().union(*(item["raw"].keys() for item in training[:20]))
    missing_fields = sorted({mapping.get("source_field") for mapping in config["field_mappings"] if mapping.get("source_field") and mapping["source_field"] not in available})
    if missing_fields: errors.append({"kind": "unknown_source_fields", "fields": missing_fields})
    try: validate_config(config, ontology)
    except ContractError as error: errors.append({"kind": "config_contract", "message": str(error)})
    if not errors:
        for item in heldout:
            try:
                observation = extract_record(item["raw"], config, ontology_path="firmable_ontology.yaml")
                extracted += 1
                record_ids.append(observation["source_record_id"])
                for field in observation["claims"]: field_counts[field] = field_counts.get(field, 0) + 1
            except (ContractError, KeyError, ValueError) as error:
                errors.append({"kind": "extraction", "source_record_id": item["source_record_id"], "message": str(error)})
                if len(errors) >= 20: break
    duplicate_record_ids = extracted - len(set(record_ids))
    if duplicate_record_ids:
        errors.append({"kind": "non_unique_source_record_id", "duplicate_count": duplicate_record_ids})
    return {"heldout_records": len(heldout), "extracted_records": extracted, "unique_source_record_ids": len(set(record_ids)), "field_coverage": {key: round(value / len(heldout), 3) for key, value in field_counts.items()}, "errors": errors, "passes": not errors}


def config_prompt(source: dict[str, Any], inspection: dict[str, Any], field_profile: dict[str, Any], ontology: dict[str, Any], validation: dict[str, Any] | None = None) -> str:
    task = "Revise the proposed config to fix the validation report" if validation else "Propose a mapping config"
    config_shape = {
        "version": "0.1",
        "extractor_version": "1.0.0",
        "source": {"source_id": source["source_id"], "licence": source["licence"], "source_reliability": 0.9},
        "record_id": {"source_fields": ["EXACT_SOURCE_COLUMN"], "separator": "|"},
        "field_mappings": [{
            "source_field": "EXACT_SOURCE_COLUMN",
            "destination": "entity.legal_name",
            "operations": [{"op": "strip"}],
            "field_confidence": 0.95,
            "derivation_level": "L1",
        }],
        "unmapped_fields": ["EXACT_SOURCE_COLUMN"],
    }
    return f"""You are one step in a schema-mapping agent. {task}. Return ONLY one valid JSON object.
Your response must follow this exact CONFIG SHAPE (replace example values; do not add alternative key names):
{json.dumps(config_shape)}
Rules: a mapping's destination key is literally named `destination` and a source column key is literally named `source_field` (singular). record_id contains `source_fields` (plural) and never operations. Every operation is an object such as {{"op":"strip"}}; use only strip, upper, lower, digits_only, regex_extract, coalesce, concat, parse_date, validate_abn, default. A `default` operation is {{"op":"default","value":"..."}}.
Do NOT map observation.source_id, observation.source_record_id, observation.licence, observation.extractor_version, or any observation envelope fields: the extractor supplies those from `source` and `record_id`. Map only ontology entity.* or address.* destinations. Use exact inspected source-column names only. `unmapped_fields` must be an array of source-column-name strings, not objects. Never write code.
Map only confident fields; list every inspected source field not mapped in unmapped_fields. field_confidence must be 0..1 and derivation_level L0 or L1.
ONTOLOGY: {json.dumps(ontology)}
SOURCE: {json.dumps(source)}
INSPECTION: {json.dumps(inspection)}
PROFILE: {json.dumps(field_profile)}
VALIDATION: {json.dumps(validation) if validation else 'none'}"""


def parse_model_json(text: str) -> dict[str, Any]:
    """Accept a JSON response even when a provider wraps it in a Markdown fence."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict): raise ContractError("Model response must be one JSON object")
    return parsed


def run(source_id: str, provider: Provider, approve: bool = False, budget_usd: float | None = None) -> Path:
    root = Path(".")
    sources = {item["source_id"]: item for item in json.loads((root / "data/manifests/selected_sources.json").read_text())["sources"]}
    source = sources[source_id]
    run_id = f"{source_id}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    directory = root / "outputs/agent_runs" / run_id
    directory.mkdir(parents=True)
    state = RunState(source_id=source_id, run_id=run_id)
    def save(name: str, value: Any) -> None:
        (directory / name).write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")
    save("state.json", state.__dict__)
    training = read_jsonl(root / "data/samples" / source_id / "training.jsonl")
    heldout = read_jsonl(root / "data/samples" / source_id / "heldout.jsonl")
    inspection = {"source": {key: source[key] for key in ("source_id", "format", "publisher", "stable_record_id_candidate", "licence")}, "training_records": len(training), "heldout_records": len(heldout), "raw_fields": sorted(training[0]["raw"])}
    field_profile = profile(training)
    save("inspection.json", inspection); save("profile.json", field_profile); state.completed_steps += ["inspect", "profile"]; save("state.json", state.__dict__)
    ontology = load_ontology()
    prompt = config_prompt(source, inspection, field_profile, ontology)
    try:
        proposal_text, usage = provider.complete(prompt)
    except Exception as error:
        state.status = "failed"; save("failure.json", {"step": "propose", "error": str(error)}); save("state.json", state.__dict__); raise
    state.costs.append(usage)
    if budget_usd is not None and usage.get("estimated_cost_usd") is not None and sum(item.get("estimated_cost_usd", 0) or 0 for item in state.costs) > budget_usd:
        raise RuntimeError(f"Run cost budget of US${budget_usd:.2f} exceeded; no revision call was made")
    save("proposal_prompt.json", {"prompt": prompt, "provider": usage})
    proposal = parse_model_json(proposal_text); save("proposal.json", proposal); state.completed_steps.append("propose"); save("state.json", state.__dict__)
    report = validation_report(proposal, training, heldout, ontology); save("validation.json", report); state.completed_steps += ["extract", "validate"]; save("state.json", state.__dict__)
    revision_prompt = config_prompt(source, inspection, field_profile, ontology, report)
    try:
        revised_text, usage = provider.complete(revision_prompt)
    except Exception as error:
        state.status = "failed"; save("failure.json", {"step": "revise", "error": str(error)}); save("state.json", state.__dict__); raise
    state.costs.append(usage)
    if budget_usd is not None and usage.get("estimated_cost_usd") is not None and sum(item.get("estimated_cost_usd", 0) or 0 for item in state.costs) > budget_usd:
        raise RuntimeError(f"Run cost budget of US${budget_usd:.2f} exceeded")
    save("revision_prompt.json", {"prompt": revision_prompt, "provider": usage})
    revised = parse_model_json(revised_text); save("revised_config.json", revised); state.completed_steps.append("revise"); save("state.json", state.__dict__)
    revised_report = validation_report(revised, training, heldout, ontology); save("revised_validation.json", revised_report)
    state.status = "approved" if approve and revised_report["passes"] else "awaiting_human_approval"
    if state.status == "approved":
        config_dir = root / "configs"; config_dir.mkdir(exist_ok=True)
        (config_dir / f"{source_id}.json").write_text(json.dumps(revised, indent=2), encoding="utf-8")
    save("state.json", state.__dict__)
    return directory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_id")
    parser.add_argument("--provider", choices=("codex", "openai"), default="codex")
    parser.add_argument("--model", help="Codex or OpenAI model; omit to use the logged-in Codex default")
    parser.add_argument("--max-codex-turns", type=int, default=2, help="hard cap for Codex CLI calls (propose + revise)")
    parser.add_argument("--max-cost-usd", type=float, default=10.0, help="hard cap when the provider exposes dollar metering")
    parser.add_argument("--approve", action="store_true", help="write only a passing revised config into configs/")
    args = parser.parse_args()
    if args.max_cost_usd <= 0 or args.max_codex_turns <= 0:
        parser.error("budget limits must be positive")
    if args.provider == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            parser.error("OPENAI_API_KEY is required for --provider openai; no model call was made")
        provider: Provider = OpenAIResponsesProvider(args.model or "gpt-6-luna")
    else:
        provider = CodexCliProvider(args.model, args.max_codex_turns)
    print(run(args.source_id, provider, args.approve, args.max_cost_usd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
