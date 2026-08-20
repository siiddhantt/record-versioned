from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evaluation import _match_key


def build_site_data(
    series_path: Path,
    sample_path: Path,
    labels_path: Path,
    analysis_path: Path,
    review_path: Path,
    destination: Path,
) -> dict[str, Any]:
    series = _read_json(series_path)
    sample = _read_json(sample_path)
    label_document = _read_json(labels_path)
    analysis = _read_json(analysis_path)
    review = _read_json(review_path)

    labels = {item["key"]: item for item in label_document["labels"]}
    volume_labels = {
        int(volume["year"]): volume.get("label", str(volume["year"]))
        for volume in series["volumes"]
    }
    scope_labels = {
        item["id"]: item["label"]
        for item in series.get("scopes", [])
        if isinstance(item.get("id"), str) and isinstance(item.get("label"), str)
    }

    alignments = []
    for item in sample:
        if item["classification"] not in {"same", "possible_rename"}:
            continue
        label = labels.get(_match_key(item))
        if label is None or not label["valid_alignment"]:
            continue
        scope = item["left"].get("scope") or "unscoped"
        alignments.append(
            {
                "classification": item["classification"],
                "similarity": item["similarity"],
                "scope": scope,
                "scope_label": scope_labels.get(scope, "Unscoped report section"),
                "left": _side_payload(item, "left", volume_labels),
                "right": _side_payload(item, "right", volume_labels),
                "review_note": label["note"],
            }
        )

    metrics_by_year = {item["year"]: item for item in analysis["volume_metrics"]}
    volumes = [
        {
            "year": int(volume["year"]),
            "label": volume_labels[int(volume["year"])],
            "identifier": volume["identifier"],
            "catalogue_date": metrics_by_year[int(volume["year"])]["catalogue_date"],
            "page_count": metrics_by_year[int(volume["year"])]["page_count"],
            "source_url": f"https://archive.org/details/{volume['identifier']}",
        }
        for volume in series["volumes"]
    ]
    payload = {
        "title": series["title"],
        "description": (
            "A bounded reconstruction of three consecutive annual reports with "
            "scope-aware, page-linked section alignments."
        ),
        "volumes": volumes,
        "scopes": [
            {"id": scope_id, "label": label}
            for scope_id, label in scope_labels.items()
            if any(item["scope"] == scope_id for item in alignments)
        ],
        "review": review,
        "alignments": alignments,
        "limitations": [
            "Only manually validated alignments are displayed.",
            "OCR errors remain visible in excerpts and headings.",
            "An alignment establishes comparable document structure, not policy intent.",
            "The result applies to this frozen corpus and does not generalize automatically.",
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload


def _side_payload(
    item: dict[str, Any],
    side: str,
    volume_labels: dict[int, str],
) -> dict[str, Any]:
    candidate = item[side]
    year = int(item[f"{side}_year"])
    return {
        "year": year,
        "volume_label": volume_labels[year],
        "heading": _display_text(candidate["text"]),
        "page_index": candidate["page_index"],
        "context": _display_text(item[f"{side}_context"]),
        "source_url": candidate["source_url"],
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_text(value: str) -> str:
    return value.replace("\N{EM DASH}", "-")
