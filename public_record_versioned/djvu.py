from __future__ import annotations

import statistics
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OcrLine:
    text: str
    bbox: tuple[int, int, int, int]
    mean_word_height: float
    mean_confidence: float
    word_count: int


@dataclass(frozen=True)
class OcrPage:
    index: int
    width: int
    height: int
    median_word_height: float
    lines: tuple[OcrLine, ...]


def parse_djvu_pages(path: Path) -> list[OcrPage]:
    """Parse page-separated OCR lines without retaining the source XML tree."""

    pages: list[OcrPage] = []
    current_width = 0
    current_height = 0
    current_lines: list[OcrLine] | None = None

    for event, element in ET.iterparse(path, events=("start", "end")):
        tag = _local_name(element.tag)
        if event == "start" and tag == "OBJECT":
            current_width = _positive_int(element.get("width"), field="OBJECT width")
            current_height = _positive_int(element.get("height"), field="OBJECT height")
            current_lines = []
            continue

        if event == "end" and tag == "LINE" and current_lines is not None:
            line = _parse_line(element)
            if line is not None:
                current_lines.append(line)
            element.clear()
            continue

        if event == "end" and tag == "OBJECT" and current_lines is not None:
            word_heights = [
                line.mean_word_height for line in current_lines if line.mean_word_height > 0
            ]
            median_height = statistics.median(word_heights) if word_heights else 0.0
            pages.append(
                OcrPage(
                    index=len(pages),
                    width=current_width,
                    height=current_height,
                    median_word_height=median_height,
                    lines=tuple(current_lines),
                )
            )
            current_lines = None
            element.clear()

    if not pages:
        raise ValueError(f"No OCR pages found in {path}")
    return pages


def _parse_line(element: ET.Element) -> OcrLine | None:
    words: list[str] = []
    heights: list[int] = []
    confidences: list[int] = []
    boxes: list[tuple[int, int, int, int]] = []

    for word in element.iter():
        if _local_name(word.tag) != "WORD":
            continue
        text = " ".join("".join(word.itertext()).split())
        if not text:
            continue
        coords = _parse_coords(word.get("coords"))
        if coords is None:
            continue
        confidence = _bounded_int(word.get("x-confidence"), default=0, minimum=0, maximum=100)
        x1, y1, x2, y2 = coords
        words.append(text)
        heights.append(max(1, y2 - y1))
        confidences.append(confidence)
        boxes.append(coords)

    if not words:
        return None

    bbox = (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )
    return OcrLine(
        text=" ".join(words),
        bbox=bbox,
        mean_word_height=statistics.fmean(heights),
        mean_confidence=statistics.fmean(confidences),
        word_count=len(words),
    )


def _parse_coords(value: str | None) -> tuple[int, int, int, int] | None:
    if not value:
        return None
    try:
        raw = [int(part) for part in value.split(",")]
    except ValueError:
        return None
    if len(raw) != 4:
        return None
    x1, y_a, x2, y_b = raw
    return min(x1, x2), min(y_a, y_b), max(x1, x2), max(y_a, y_b)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _positive_int(value: str | None, *, field: str) -> int:
    try:
        parsed = int(value or "")
    except ValueError as error:
        raise ValueError(f"Invalid {field}: {value!r}") from error
    if parsed <= 0:
        raise ValueError(f"Invalid {field}: {value!r}")
    return parsed


def _bounded_int(
    value: str | None, *, default: int, minimum: int, maximum: int
) -> int:
    try:
        parsed = int(value or "")
    except ValueError:
        return default
    return min(maximum, max(minimum, parsed))
