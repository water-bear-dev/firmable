import json
import unittest

from agent_pipeline import CodexCliProvider, config_prompt, parse_model_json, validation_report
from contracts import load_ontology
from test_contracts import CONFIG


class PipelineTests(unittest.TestCase):
    def test_reports_heldout_coverage(self):
        rows = [{"source_record_id": "one", "raw": {"id": "one", "name": "Example", "abn": "11 000 000 948", "state": "NSW"}}]
        report = validation_report(CONFIG, rows, rows, load_ontology())
        self.assertTrue(report["passes"])
        self.assertEqual(report["extracted_records"], 1)

    def test_rejects_duplicate_source_record_ids(self):
        rows = [
            {"source_record_id": "one", "raw": {"id": "same", "name": "Example", "abn": "11 000 000 948", "state": "NSW"}},
            {"source_record_id": "two", "raw": {"id": "same", "name": "Other", "abn": "11 000 000 948", "state": "VIC"}},
        ]
        report = validation_report(CONFIG, rows, rows, load_ontology())
        self.assertFalse(report["passes"])
        self.assertEqual(report["errors"][-1]["kind"], "non_unique_source_record_id")

    def test_accepts_fenced_json(self):
        self.assertEqual(parse_model_json("```json\n{\"ok\": true}\n```"), {"ok": True})

    def test_codex_provider_stops_before_a_third_turn(self):
        provider = CodexCliProvider(None, max_turns=2)
        provider.turns_used = 2
        with self.assertRaisesRegex(RuntimeError, "turn limit"):
            provider.complete("this must not invoke Codex")

    def test_prompt_names_the_contract_keys(self):
        prompt = config_prompt(
            {"source_id": "fixture", "licence": "CC BY 3.0 AU"},
            {"raw_fields": ["id"]}, {"id": {}}, load_ontology(),
        )
        self.assertIn('"destination": "entity.legal_name"', prompt)
        self.assertIn('"source_field": "EXACT_SOURCE_COLUMN"', prompt)
        self.assertIn("Do NOT map observation.source_id", prompt)
