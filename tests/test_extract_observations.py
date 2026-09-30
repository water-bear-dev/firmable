import json
import tempfile
import unittest
from pathlib import Path

from extract_observations import extract_source
from test_contracts import CONFIG


class BatchExtractionTests(unittest.TestCase):
    def test_writes_observations_and_metrics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = {**CONFIG, "source": {**CONFIG["source"], "source_id": "sample"}}
            config_path = root / "config.json"
            sample_path = root / "sample.jsonl"
            output_path = root / "observations.jsonl"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            sample_path.write_text(json.dumps({"source_record_id": "one", "raw": {"id": "one", "name": " Example ", "abn": "11 000 000 948", "state": "vic"}}) + "\n", encoding="utf-8")
            metrics = extract_source(config_path, sample_path, output_path, "2026-09-30T00:00:00+00:00")
            self.assertTrue(metrics["passes"])
            self.assertEqual(metrics["unique_source_record_ids"], 1)
            observation = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(observation["ingested_at"], "2026-09-30T00:00:00+00:00")
