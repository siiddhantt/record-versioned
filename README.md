# Public Record, Versioned

This repository is a bounded viability spike for reconstructing and comparing a recurring
Canadian government publication series from public Internet Archive derivatives.

The spike answers one question:

> Can adjacent reports be compared at the section level while keeping every result tied to
> exact archive pages?

It deliberately does not generate policy conclusions, silently repair archive metadata, or use
an LLM to force weak matches.

## Corpus

The initial corpus contains the five Alberta State of the Environment annual reports from 1995
through 1999. Their identifiers distinguish the volumes, while their catalogue metadata records
the same year for all five items.

`data/ontario-housing-series.json` is a separate three-volume validation corpus. It contains a
true consecutive run of Ontario Ministry of Housing annual reports (`1974/75` through `1976/77`)
and is used to test whether adjacent-volume comparison is viable after the Alberta corpus exposed
themed editions rather than revisions of one recurring report.

## Data access

The pipeline reads only public Internet Archive endpoints:

- `https://archive.org/metadata/{identifier}`
- `https://archive.org/download/{identifier}/{identifier}_djvu.xml`

If the public metadata gateway is unavailable, the corpus manifest contains the exact official
storage-node locations resolved from the Internet Archive book reader. The fallback reads each
item's `_meta.xml` and `_files.xml`, validates the identifier and derivative inventory, then
downloads the same DjVu XML bytes from that storage node. It does not use a third-party mirror.

Downloads are sequential, cached, bounded by size, and checksum-verified when the archive
provides an MD5 value. The source files remain unmodified.

## Run the spike

```powershell
python -m public_record_versioned.cli spike
```

Run from cache without network requests:

```powershell
python -m public_record_versioned.cli analyze
```

Run the standard-library test suite:

```powershell
python -m unittest discover -s tests -v
```

Run the frozen Ontario review after analysis:

```powershell
python -m public_record_versioned.cli evaluate `
  --artifacts artifacts/ontario-housing `
  --review-labels data/ontario-housing-review.json
```

Build the static evidence data after the review passes:

```powershell
python -m public_record_versioned.cli site `
  --series data/ontario-housing-series.json `
  --artifacts artifacts/ontario-housing `
  --review-labels data/ontario-housing-review.json
```

Run the evidence explorer locally:

```powershell
cd site
npm install
npm run dev
```

Create the production-ready static build:

```powershell
npm run build
```

Generated evidence is written to `artifacts/` and raw cached derivatives to `data/raw/`.
Neither directory is committed by default.

## Viability rules

Automated similarity is a candidate generator, not ground truth. The spike can only support a
fellowship claim after a human reviews the generated sample and confirms that:

1. section candidates are meaningful rather than OCR or running-header noise;
2. adjacent-volume matches describe the same section;
3. added and removed candidates are not extraction failures;
4. every displayed result resolves to both source pages.

If these checks fail, the safer fallback is a publication-series navigator without section-level
comparison.
