from __future__ import annotations

import unittest

from public_record_versioned.djvu import OcrLine, OcrPage
from public_record_versioned.headings import detect_heading_candidates, normalize_heading


def line(text: str, height: float, confidence: float = 90.0) -> OcrLine:
    return OcrLine(
        text=text,
        bbox=(0, 0, 500, int(height)),
        mean_word_height=height,
        mean_confidence=confidence,
        word_count=len(text.split()),
    )


class HeadingDetectionTests(unittest.TestCase):
    def test_detects_large_heading_and_removes_repeated_header(self) -> None:
        pages = [
            OcrPage(
                index=index,
                width=1000,
                height=1200,
                median_word_height=40.0,
                lines=(
                    line("ALBERTA ENVIRONMENT", 50.0),
                    line(f"SECTION {index + 1}", 80.0),
                    line("This is ordinary body text ending with a period.", 40.0),
                ),
            )
            for index in range(4)
        ]
        candidates = detect_heading_candidates(pages, "example")
        texts = {candidate.text for candidate in candidates}
        self.assertNotIn("ALBERTA ENVIRONMENT", texts)
        self.assertIn("SECTION 1", texts)

    def test_normalization_is_case_and_punctuation_insensitive(self) -> None:
        self.assertEqual(normalize_heading("Water-Quality"), "water quality")

    def test_rejects_person_names_and_keeps_scope_context(self) -> None:
        pages = [
            OcrPage(
                index=0,
                width=1000,
                height=1200,
                median_word_height=40.0,
                lines=(
                    line("ONTARIO MORTGAGE CORPORATION", 70.0),
                    line("ACCOUNTING POLICIES", 65.0),
                    line("DONALD A. CROSBIE", 65.0),
                ),
            )
        ]
        candidates = detect_heading_candidates(
            pages,
            "example",
            scopes=[
                {
                    "id": "ministry",
                    "aliases": ["Ontario Ministry of Housing"],
                },
                {
                    "id": "mortgage",
                    "aliases": ["Ontario Mortgage Corporation"],
                },
            ],
        )

        self.assertEqual([item.text for item in candidates], ["ACCOUNTING POLICIES"])
        self.assertEqual(candidates[0].scope, "mortgage")


if __name__ == "__main__":
    unittest.main()
