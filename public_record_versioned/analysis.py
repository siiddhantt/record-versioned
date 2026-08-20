from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .archive import InternetArchiveClient
from .compare import HeadingMatch, compare_heading_sets
from .djvu import OcrPage, parse_djvu_pages
from .headings import HeadingCandidate, detect_heading_candidates, normalize_heading


def load_series(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    volumes = value.get("volumes")
    if not isinstance(volumes, list) or len(volumes) < 2:
        raise ValueError("Series manifest must contain at least two volumes")
    years = [volume.get("year") for volume in volumes]
    if years != sorted(years) or len(set(years)) != len(years):
        raise ValueError("Series years must be unique and sorted")
    identifiers = [volume.get("identifier") for volume in volumes]
    if any(not isinstance(identifier, str) or not identifier for identifier in identifiers):
        raise ValueError("Every volume must have a non-empty identifier")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Series identifiers must be unique")
    return value


def fetch_series(series: dict[str, Any], client: InternetArchiveClient) -> None:
    for volume in series["volumes"]:
        client.fetch_volume(
            volume["identifier"],
            storage_base_url=volume.get("storage_base_url"),
        )


def analyze_series(
    series: dict[str, Any],
    client: InternetArchiveClient,
    artifacts_root: Path,
) -> dict[str, Any]:
    artifacts_root.mkdir(parents=True, exist_ok=True)
    volume_root = artifacts_root / "volumes"
    comparison_root = artifacts_root / "comparisons"
    volume_root.mkdir(exist_ok=True)
    comparison_root.mkdir(exist_ok=True)

    candidates_by_year: dict[int, list[HeadingCandidate]] = {}
    pages_by_year: dict[int, list[OcrPage]] = {}
    volume_metrics: list[dict[str, Any]] = []

    for volume in series["volumes"]:
        year = int(volume["year"])
        identifier = volume["identifier"]
        cached = client.require_cached_volume(identifier)
        metadata = json.loads(cached.metadata_path.read_text(encoding="utf-8"))
        pages = parse_djvu_pages(cached.djvu_xml_path)
        pages_by_year[year] = pages
        candidates = detect_heading_candidates(
            pages,
            identifier,
            scopes=series.get("scopes"),
        )
        candidates_by_year[year] = candidates

        catalogue_date = metadata.get("metadata", {}).get("date")
        candidate_payload = [candidate.to_dict() for candidate in candidates]
        _write_json(volume_root / f"{year}.json", candidate_payload)
        volume_metrics.append(
            {
                "year": year,
                "identifier": identifier,
                "catalogue_date": catalogue_date,
                "page_count": len(pages),
                "heading_candidate_count": len(candidates),
                "high_confidence_candidate_count": sum(
                    candidate.score >= 3.2 for candidate in candidates
                ),
            }
        )

    comparison_metrics: list[dict[str, Any]] = []
    all_matches: list[tuple[int, int, HeadingMatch]] = []
    ordered = series["volumes"]
    for left_volume, right_volume in zip(ordered, ordered[1:]):
        left_year = int(left_volume["year"])
        right_year = int(right_volume["year"])
        matches = compare_heading_sets(
            candidates_by_year[left_year], candidates_by_year[right_year]
        )
        all_matches.extend((left_year, right_year, match) for match in matches)
        _write_json(
            comparison_root / f"{left_year}-{right_year}.json",
            [match.to_dict() for match in matches],
        )
        counts = Counter(match.classification for match in matches)
        comparison_metrics.append(
            {
                "left_year": left_year,
                "right_year": right_year,
                "same": counts["same"],
                "possible_rename": counts["possible_rename"],
                "removed": counts["removed"],
                "added": counts["added"],
            }
        )

    automated_gates = {
        "all_manifest_volumes_parsed": len(volume_metrics) == len(series["volumes"]),
        "all_volumes_have_pages": all(metric["page_count"] > 0 for metric in volume_metrics),
        "all_volumes_have_heading_signal": all(
            metric["high_confidence_candidate_count"] >= 5 for metric in volume_metrics
        ),
        "all_adjacent_pairs_have_matches": all(
            metric["same"] + metric["possible_rename"] >= 3
            for metric in comparison_metrics
        ),
    }
    result = {
        "series": {key: value for key, value in series.items() if key != "volumes"},
        "volume_metrics": volume_metrics,
        "comparison_metrics": comparison_metrics,
        "automated_gates": automated_gates,
        "automated_signal": "pass" if all(automated_gates.values()) else "fail",
        "verdict": "needs_manual_review",
        "limitations": [
            "OCR-derived typography is noisy and does not establish document semantics.",
            "Similarity scores generate review candidates; they are not ground truth.",
            "Added or removed candidates may be extraction failures until manually checked.",
            "No output supports a claim about policy intent or policy change.",
        ],
    }
    _write_json(artifacts_root / "analysis.json", result)
    _write_json(
        artifacts_root / "review-sample.json",
        _build_review_sample(all_matches, pages_by_year),
    )
    (artifacts_root / "viability-report.md").write_text(
        _render_report(result), encoding="utf-8", newline="\n"
    )
    return result


def _build_review_sample(
    matches: list[tuple[int, int, HeadingMatch]],
    pages_by_year: dict[int, list[OcrPage]],
) -> list[dict[str, Any]]:
    sample: list[dict[str, Any]] = []
    limits = {"same": 12, "possible_rename": 12, "removed": 8, "added": 8}
    used = Counter()
    for left_year, right_year, match in matches:
        if used[match.classification] >= limits[match.classification]:
            continue
        payload = match.to_dict()
        payload.update(
            {
                "left_year": left_year,
                "right_year": right_year,
                "left_context": _candidate_context(
                    pages_by_year[left_year], match.left
                ),
                "right_context": _candidate_context(
                    pages_by_year[right_year], match.right
                ),
                "review": "unreviewed",
                "review_notes": "",
            }
        )
        sample.append(payload)
        used[match.classification] += 1
    return sample


def _candidate_context(
    pages: list[OcrPage],
    candidate: HeadingCandidate | None,
) -> str | None:
    if candidate is None:
        return None
    page = pages[candidate.page_index]
    target_index = next(
        (
            index
            for index, line in enumerate(page.lines)
            if normalize_heading(line.text) == candidate.normalized
        ),
        0,
    )
    start = max(0, target_index - 2)
    end = min(len(page.lines), target_index + 5)
    context = " ".join(line.text for line in page.lines[start:end])
    context = " ".join(context.split())
    return context[:900]


def _render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Viability report",
        "",
        f"Automated signal: **{result['automated_signal']}**",
        "",
        "This is an extraction signal only. The project remains unvalidated until the review sample is checked against source pages.",
        "",
        "## Volume metrics",
        "",
        "| Year | Catalogue date | Pages | Candidates | High-confidence |",
        "| ---: | --- | ---: | ---: | ---: |",
    ]
    for metric in result["volume_metrics"]:
        lines.append(
            f"| {metric['year']} | {metric['catalogue_date']} | {metric['page_count']} | "
            f"{metric['heading_candidate_count']} | {metric['high_confidence_candidate_count']} |"
        )
    lines.extend(
        [
            "",
            "## Adjacent-volume candidate comparisons",
            "",
            "| Pair | Same | Possible rename | Removed | Added |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for metric in result["comparison_metrics"]:
        lines.append(
            f"| {metric['left_year']}-{metric['right_year']} | {metric['same']} | "
            f"{metric['possible_rename']} | {metric['removed']} | {metric['added']} |"
        )
    lines.extend(["", "## Automated gates", ""])
    for gate, passed in result["automated_gates"].items():
        lines.append(f"- [{'x' if passed else ' '}] {gate.replace('_', ' ')}")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in result["limitations"])
    lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
