from __future__ import annotations

import collections
import re
import unicodedata
from dataclasses import asdict, dataclass

from .djvu import OcrLine, OcrPage


_SPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class HeadingCandidate:
    identifier: str
    page_index: int
    text: str
    normalized: str
    score: float
    size_ratio: float
    mean_confidence: float
    source_url: str
    scope: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def detect_heading_candidates(
    pages: list[OcrPage],
    identifier: str,
    scopes: list[dict[str, object]] | None = None,
) -> list[HeadingCandidate]:
    repeated = _repeated_line_norms(pages)
    scope_definitions = scopes or []
    page_scopes = _resolve_page_scopes(pages, scope_definitions)
    scope_aliases = {
        normalize_heading(alias)
        for definition in scope_definitions
        for alias in definition.get("aliases", [])
        if isinstance(alias, str)
    }
    candidates: list[HeadingCandidate] = []

    for page in pages:
        baseline = page.median_word_height
        if baseline <= 0:
            continue
        page_candidates: list[HeadingCandidate] = []
        for line in page.lines:
            candidate = _score_line(
                line,
                page,
                identifier,
                repeated,
                scope=page_scopes.get(page.index),
            )
            if candidate is not None and candidate.normalized not in scope_aliases:
                page_candidates.append(candidate)
        page_candidates.sort(key=lambda item: item.score, reverse=True)
        candidates.extend(page_candidates[:8])

    best_by_text: dict[tuple[str | None, str], HeadingCandidate] = {}
    for candidate in candidates:
        key = (candidate.scope, candidate.normalized)
        previous = best_by_text.get(key)
        if previous is None or candidate.score > previous.score:
            best_by_text[key] = candidate
    return sorted(
        best_by_text.values(),
        key=lambda item: (item.page_index, -item.score, item.normalized),
    )


def normalize_heading(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return _NON_WORD_RE.sub(" ", ascii_text.lower()).strip()


def _score_line(
    line: OcrLine,
    page: OcrPage,
    identifier: str,
    repeated: set[str],
    *,
    scope: str | None,
) -> HeadingCandidate | None:
    text = _SPACE_RE.sub(" ", line.text).strip(" |\t")
    normalized = normalize_heading(text)
    if len(text) < 4 or len(text) > 120 or len(normalized) < 3:
        return None
    if line.word_count > 16:
        return None

    letters = [character for character in text if character.isalpha()]
    if len(letters) < 3:
        return None
    digits = [character for character in text if character.isdigit()]
    if len(digits) / max(1, len(letters) + len(digits)) > 0.35:
        return None

    tokens = [token for token in re.split(r"\s+", text) if token]
    cased_tokens = [token for token in tokens if any(character.isalpha() for character in token)]
    uppercase_ratio = sum(character.isupper() for character in letters) / len(letters)
    title_ratio = (
        sum(token[:1].isupper() for token in cased_tokens) / len(cased_tokens)
        if cased_tokens
        else 0.0
    )
    size_ratio = line.mean_word_height / page.median_word_height

    if _looks_like_person_name(tokens):
        return None
    if re.search(r"\d[\d,]{2,}", text):
        return None
    single_character_tokens = sum(
        len(re.sub(r"[^A-Za-z0-9]", "", token)) == 1 for token in tokens
    )
    if single_character_tokens > 1:
        return None

    score = 0.0
    if size_ratio >= 1.65:
        score += 2.7
    elif size_ratio >= 1.35:
        score += 2.0
    elif size_ratio >= 1.18:
        score += 0.9

    if uppercase_ratio >= 0.9:
        score += 1.6
    elif uppercase_ratio >= 0.7:
        score += 0.9
    if title_ratio >= 0.8 and 1 <= len(cased_tokens) <= 10:
        score += 0.8
    if 1 <= line.word_count <= 10:
        score += 0.5
    if line.mean_confidence >= 70:
        score += 0.4
    elif line.mean_confidence < 30:
        score -= 0.8
    if text.endswith((".", ",", ";", "?", "!")) and line.word_count >= 5:
        score -= 1.2
    if normalized in repeated:
        score -= 3.0
    if len(set(normalized.replace(" ", ""))) <= 2:
        score -= 2.0

    if score < 2.5:
        return None

    return HeadingCandidate(
        identifier=identifier,
        page_index=page.index,
        text=text,
        normalized=normalized,
        score=round(score, 3),
        size_ratio=round(size_ratio, 3),
        mean_confidence=round(line.mean_confidence, 3),
        source_url=f"https://archive.org/details/{identifier}/page/n{page.index}/mode/2up",
        scope=scope,
    )


def _repeated_line_norms(pages: list[OcrPage]) -> set[str]:
    page_occurrences: collections.Counter[str] = collections.Counter()
    for page in pages:
        seen_on_page = {
            normalize_heading(line.text)
            for line in page.lines
            if 3 <= len(normalize_heading(line.text)) <= 120
        }
        page_occurrences.update(seen_on_page)
    threshold = max(3, round(len(pages) * 0.15))
    return {text for text, count in page_occurrences.items() if count >= threshold}


def _resolve_page_scopes(
    pages: list[OcrPage],
    scope_definitions: list[dict[str, object]],
) -> dict[int, str | None]:
    definitions: list[tuple[str, tuple[str, ...]]] = []
    for definition in scope_definitions:
        scope_id = definition.get("id")
        aliases = definition.get("aliases")
        if not isinstance(scope_id, str) or not isinstance(aliases, list):
            continue
        normalized_aliases = tuple(
            alias
            for value in aliases
            if isinstance(value, str) and (alias := normalize_heading(value))
        )
        if normalized_aliases:
            definitions.append((scope_id, normalized_aliases))

    current_scope: str | None = definitions[0][0] if definitions else None
    resolved: dict[int, str | None] = {}
    for page in pages:
        matches: list[tuple[float, str]] = []
        for line in page.lines:
            normalized = normalize_heading(line.text)
            if not normalized:
                continue
            letters = [character for character in line.text if character.isalpha()]
            uppercase_ratio = (
                sum(character.isupper() for character in letters) / len(letters)
                if letters
                else 0.0
            )
            size_ratio = (
                line.mean_word_height / page.median_word_height
                if page.median_word_height > 0
                else 0.0
            )
            if uppercase_ratio < 0.65 and size_ratio < 1.3:
                continue
            for scope_id, aliases in definitions:
                for alias in aliases:
                    if alias in normalized:
                        matches.append((len(alias) + size_ratio, scope_id))
        if matches:
            current_scope = max(matches)[1]
        resolved[page.index] = current_scope
    return resolved


def _looks_like_person_name(tokens: list[str]) -> bool:
    if not 2 <= len(tokens) <= 4:
        return False
    cleaned = [re.sub(r"[^A-Za-z]", "", token) for token in tokens]
    if not all(cleaned):
        return False
    if not all(value.isupper() or value.istitle() for value in cleaned):
        return False
    return any(len(value) == 1 for value in cleaned)
