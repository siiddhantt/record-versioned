from __future__ import annotations

import argparse
from pathlib import Path

from .analysis import analyze_series, fetch_series, load_series
from .archive import InternetArchiveClient
from .evaluation import evaluate_review_sample
from .site import build_site_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the bounded Public Record, Versioned viability spike."
    )
    parser.add_argument(
        "command",
        choices=("fetch", "analyze", "spike", "evaluate", "site"),
    )
    parser.add_argument(
        "--series",
        type=Path,
        default=PROJECT_ROOT / "data" / "series.json",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw",
    )
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=PROJECT_ROOT / "artifacts",
    )
    parser.add_argument("--review-labels", type=Path)
    parser.add_argument(
        "--site-data",
        type=Path,
        default=PROJECT_ROOT / "site" / "data.json",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "evaluate":
        if args.review_labels is None:
            raise SystemExit("evaluate requires --review-labels")
        result = evaluate_review_sample(
            args.artifacts / "review-sample.json",
            args.review_labels,
            args.artifacts,
        )
        print(f"Manual precision: {result['precision']:.1%}")
        print(f"Verdict: {result['verdict']}")
        return 0

    if args.command == "site":
        if args.review_labels is None:
            raise SystemExit("site requires --review-labels")
        payload = build_site_data(
            args.series,
            args.artifacts / "review-sample.json",
            args.review_labels,
            args.artifacts / "analysis.json",
            args.artifacts / "manual-review.json",
            args.site_data,
        )
        print(f"Published alignments: {len(payload['alignments'])}")
        print(f"Site data: {args.site_data}")
        return 0

    series = load_series(args.series)
    client = InternetArchiveClient(args.cache)

    if args.command in {"fetch", "spike"}:
        fetch_series(series, client)
    if args.command in {"analyze", "spike"}:
        result = analyze_series(series, client, args.artifacts)
        print(f"Automated signal: {result['automated_signal']}")
        print(f"Manual verdict: {result['verdict']}")
        print(f"Report: {args.artifacts / 'viability-report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
