from __future__ import annotations

import unittest

from public_record_versioned.site import _side_payload


class SiteDataTests(unittest.TestCase):
    def test_side_payload_preserves_page_evidence(self) -> None:
        item = {
            "left_year": 1974,
            "left_context": "Source context",
            "left": {
                "text": "Accounting Policies",
                "page_index": 29,
                "source_url": "https://archive.org/details/example/page/n29/mode/2up",
            },
        }
        result = _side_payload(item, "left", {1974: "1974/75"})
        self.assertEqual(result["volume_label"], "1974/75")
        self.assertEqual(result["page_index"], 29)
        self.assertEqual(result["context"], "Source context")


if __name__ == "__main__":
    unittest.main()
