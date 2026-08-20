from __future__ import annotations

from dataclasses import asdict, dataclass
from difflib import SequenceMatcher

from .headings import HeadingCandidate


_STOPWORDS = {"a", "an", "and", "for", "in", "of", "on", "the", "to"}


@dataclass(frozen=True)
class HeadingMatch:
    classification: str
    similarity: float
    left: HeadingCandidate | None
    right: HeadingCandidate | None

    def to_dict(self) -> dict[str, object]:
        return {
            "classification": self.classification,
            "similarity": self.similarity,
            "left": asdict(self.left) if self.left else None,
            "right": asdict(self.right) if self.right else None,
        }


def compare_heading_sets(
    left: list[HeadingCandidate], right: list[HeadingCandidate]
) -> list[HeadingMatch]:
    left = [item for item in left if _is_matchable(item)]
    right = [item for item in right if _is_matchable(item)]
    pairs: list[tuple[float, int, int]] = []
    for left_index, left_item in enumerate(left):
        for right_index, right_item in enumerate(right):
            if (left_item.scope or right_item.scope) and left_item.scope != right_item.scope:
                continue
            score = heading_similarity(left_item.normalized, right_item.normalized)
            if score >= 0.62:
                pairs.append((score, left_index, right_index))
    pairs.sort(reverse=True)

    used_left: set[int] = set()
    used_right: set[int] = set()
    matches: list[HeadingMatch] = []
    for score, left_index, right_index in pairs:
        if left_index in used_left or right_index in used_right:
            continue
        used_left.add(left_index)
        used_right.add(right_index)
        classification = "same" if score >= 0.82 else "possible_rename"
        matches.append(
            HeadingMatch(
                classification=classification,
                similarity=round(score, 3),
                left=left[left_index],
                right=right[right_index],
            )
        )

    matches.extend(
        HeadingMatch("removed", 0.0, item, None)
        for index, item in enumerate(left)
        if index not in used_left
    )
    matches.extend(
        HeadingMatch("added", 0.0, None, item)
        for index, item in enumerate(right)
        if index not in used_right
    )
    order = {"same": 0, "possible_rename": 1, "removed": 2, "added": 3}
    return sorted(
        matches,
        key=lambda match: (
            order[match.classification],
            -match.similarity,
            match.left.normalized if match.left else match.right.normalized,
        ),
    )


def heading_similarity(left: str, right: str) -> float:
    left_tokens = _meaningful_tokens(left)
    right_tokens = _meaningful_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    if left_tokens == right_tokens:
        return 1.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    jaccard = intersection / union if union else 0.0
    sequence = SequenceMatcher(None, " ".join(sorted(left_tokens)), " ".join(sorted(right_tokens))).ratio()
    return 0.6 * jaccard + 0.4 * sequence


def _meaningful_tokens(value: str) -> set[str]:
    return {token for token in value.split() if token not in _STOPWORDS and len(token) > 1}


def _is_matchable(candidate: HeadingCandidate) -> bool:
    tokens = _meaningful_tokens(candidate.normalized)
    if len(tokens) >= 2:
        return True
    return candidate.normalized in {
        "conclusion",
        "conclusions",
        "glossary",
        "introduction",
        "preface",
        "references",
    }
