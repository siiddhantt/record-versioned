from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def evaluate_review_sample(
    sample_path: Path,
    labels_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    label_document = json.loads(labels_path.read_text(encoding="utf-8"))
    predictions = [
        item
        for item in sample
        if item["classification"] in {"same", "possible_rename"}
    ]
    labels = {item["key"]: item for item in label_document["labels"]}
    prediction_keys = {_match_key(item) for item in predictions}

    missing = sorted(prediction_keys - labels.keys())
    extra = sorted(labels.keys() - prediction_keys)
    if missing or extra:
        raise ValueError(
            f"Review labels do not match the current sample: "
            f"{len(missing)} missing, {len(extra)} extra"
        )

    valid_count = sum(bool(labels[key]["valid_alignment"]) for key in prediction_keys)
    reviewed_count = len(prediction_keys)
    precision = valid_count / reviewed_count if reviewed_count else 0.0
    minimum_sample = int(label_document.get("minimum_sample", 20))
    target_precision = float(label_document.get("target_precision", 0.9))
    viable = reviewed_count >= minimum_sample and precision >= target_precision

    result = {
        "corpus": label_document["corpus"],
        "reviewer": label_document["reviewer"],
        "criteria": label_document["criteria"],
        "reviewed_count": reviewed_count,
        "valid_count": valid_count,
        "invalid_count": reviewed_count - valid_count,
        "precision": round(precision, 4),
        "minimum_sample": minimum_sample,
        "target_precision": target_precision,
        "verdict": "viable_for_bounded_prototype" if viable else "not_yet_viable",
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "manual-review.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output_root / "manual-review.md").write_text(
        _render_review(result),
        encoding="utf-8",
        newline="\n",
    )
    return result


def _match_key(item: dict[str, Any]) -> str:
    left = item["left"]
    right = item["right"]
    return "|".join(
        str(value or "")
        for value in (
            item["left_year"],
            item["right_year"],
            left.get("scope"),
            left["page_index"],
            left["normalized"],
            right.get("scope"),
            right["page_index"],
            right["normalized"],
        )
    )


def _render_review(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Manual review",
            "",
            f"Verdict: **{result['verdict']}**",
            "",
            f"- Reviewed alignments: {result['reviewed_count']}",
            f"- Valid alignments: {result['valid_count']}",
            f"- Invalid alignments: {result['invalid_count']}",
            f"- Precision: {result['precision']:.1%}",
            f"- Target: {result['target_precision']:.1%} across at least "
            f"{result['minimum_sample']} alignments",
            "",
            "The score applies only to this frozen, scope-aware three-volume corpus. "
            "It is evidence for a bounded prototype, not a claim that arbitrary series "
            "can be aligned automatically.",
            "",
        ]
    )
