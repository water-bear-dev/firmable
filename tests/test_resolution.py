import unittest

from resolution import resolve


def observation(source_id, record_id, claims):
    return {"source_id": source_id, "source_record_id": record_id, "claims": claims}


class ResolutionTests(unittest.TestCase):
    def test_accepts_exact_abn_and_abstains_without_identifier(self):
        left = observation("one", "a", {"entity.abn": {"value": "11000000948"}})
        right = observation("two", "b", {"entity.abn": {"value": "11000000948"}})
        unmatched = observation("three", "c", {"entity.legal_name": {"value": "Example"}})
        links, unlinked = resolve([left, right, unmatched])
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["link_confidence"], 0.99)
        self.assertEqual(unlinked, [{"source_id": "three", "source_record_id": "c", "reason": "no_cross_source_strong_identifier", "matcher_version": "identifier-v1"}])
