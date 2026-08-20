from __future__ import annotations

import unittest

from public_record_versioned.compare import compare_heading_sets, heading_similarity
from public_record_versioned.headings import HeadingCandidate


def candidate(
    text: str,
    page: int = 1,
    scope: str | None = None,
) -> HeadingCandidate:
    normalized = text.lower().replace("-", " ")
    return HeadingCandidate(
        identifier="example",
        page_index=page,
        text=text,
        normalized=normalized,
        score=4.0,
        size_ratio=1.5,
        mean_confidence=90.0,
        source_url="https://archive.org/details/example",
        scope=scope,
    )


class HeadingComparisonTests(unittest.TestCase):
    def test_exact_normalized_match_scores_one(self) -> None:
        self.assertEqual(heading_similarity("water quality", "water quality"), 1.0)

    def test_comparison_keeps_added_and_removed_candidates_explicit(self) -> None:
        results = compare_heading_sets(
            [candidate("Water Quality"), candidate("Waste Management")],
            [candidate("Water Quality"), candidate("Forest Health")],
        )
        counts = {classification: 0 for classification in ("same", "removed", "added")}
        for result in results:
            if result.classification in counts:
                counts[result.classification] += 1
        self.assertEqual(counts, {"same": 1, "removed": 1, "added": 1})

    def test_does_not_match_identical_headings_across_scopes(self) -> None:
        results = compare_heading_sets(
            [candidate("Accounting Policies", scope="mortgage")],
            [candidate("Accounting Policies", scope="pickering")],
        )
        self.assertEqual(
            [result.classification for result in results],
            ["removed", "added"],
        )


if __name__ == "__main__":
    unittest.main()
