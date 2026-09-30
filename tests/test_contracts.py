import unittest

from contracts import ContractError, load_ontology, validate_config
from extractor import extract_record


CONFIG = {
    "version": "0.1", "extractor_version": "0.1.0",
    "source": {"source_id": "fixture", "licence": "CC BY 3.0 AU", "source_reliability": 0.9},
    "record_id": {"source_fields": ["id"]}, "unmapped_fields": ["unused"],
    "field_mappings": [
        {"source_field": "name", "destination": "entity.legal_name", "operations": [{"op": "strip"}], "field_confidence": 0.99, "derivation_level": "L0"},
        {"source_field": "abn", "destination": "entity.abn", "operations": [{"op": "digits_only"}, {"op": "validate_abn"}], "field_confidence": 0.99, "derivation_level": "L1"},
        {"source_field": "state", "destination": "address.state", "operations": [{"op": "upper"}], "field_confidence": 0.98, "derivation_level": "L1"},
    ],
}


class ContractTests(unittest.TestCase):
    def test_extracts_valid_observation(self):
        result = extract_record({"id": "row-1", "name": " Example Pty Ltd ", "abn": "11 000 000 948", "state": "vic"}, CONFIG, "2026-09-29T00:00:00+00:00")
        self.assertEqual(result["claims"]["entity.abn"]["value"], "11000000948")
        self.assertEqual(result["claims"]["address.state"]["value"], "VIC")

    def test_rejects_unknown_destination(self):
        invalid = {**CONFIG, "field_mappings": [{**CONFIG["field_mappings"][0], "destination": "entity.invented"}]}
        with self.assertRaises(ContractError): validate_config(invalid, load_ontology())

    def test_rejects_record_id_field_marked_unmapped(self):
        invalid = {**CONFIG, "unmapped_fields": ["id"]}
        with self.assertRaisesRegex(ContractError, "record ID fields"):
            validate_config(invalid, load_ontology())

    def test_optional_blank_date_abstains_without_failing(self):
        config = {**CONFIG, "field_mappings": [
            *CONFIG["field_mappings"],
            {"source_field": "registered", "destination": "entity.date_registered", "operations": [{"op": "strip"}, {"op": "parse_date", "format": "%d/%m/%Y"}], "field_confidence": 0.9, "derivation_level": "L1"},
        ]}
        result = extract_record({"id": "row-1", "name": "Example", "abn": "11 000 000 948", "state": "VIC", "registered": ""}, config)
        self.assertNotIn("entity.date_registered", result["claims"])
