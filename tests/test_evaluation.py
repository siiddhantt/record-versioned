from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from public_record_versioned.evaluation import evaluate_review_sample


class ReviewEvaluationTests(unittest.TestCase):
    def test_requires_labels_to_match_the_current_sample(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample_path = root / "sample.json"
            labels_path = root / "labels.json"
            sample_path.write_text(
                json.dumps(
                    [
                        {
                            "classification": "same",
                            "left_year": 1,
                            "right_year": 2,
                            "left": {
                                "scope": "a",
                                "page_index": 3,
                                "normalized": "alpha beta",
                            },
                            "right": {
                                "scope": "a",
                                "page_index": 4,
                                "normalized": "alpha beta",
                            },
                        }
                    ]
                ),
                encoding="utf-8",
            )
            labels_path.write_text(
                json.dumps(
                    {
                        "corpus": "test",
                        "reviewer": "test",
                        "criteria": "test",
                        "labels": [],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                evaluate_review_sample(sample_path, labels_path, root / "out")


if __name__ == "__main__":
    unittest.main()
