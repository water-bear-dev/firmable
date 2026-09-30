import unittest

from profiles import build_profile


def observation(source_id, name, confidence):
    return {"source_id": source_id, "source_record_id": source_id, "observed_at": "2026-01-01T00:00:00+00:00", "licence": "CC", "source_reliability": 0.9, "claims": {"entity.legal_name": {"value": name, "raw_value": name, "field_confidence": confidence}}}


class ProfileTests(unittest.TestCase):
    def test_preserves_conflicting_alternate_and_provenance(self):
        profile = build_profile("abn:1", [observation("low", "Old Name", 0.8), observation("high", "New Name", 0.99)])
        field = profile["fields"]["entity.legal_name"]
        self.assertEqual(field["value"], "New Name")
        self.assertEqual(field["provenance"]["source_id"], "high")
        self.assertEqual(field["alternates"][0]["value"], "Old Name")
