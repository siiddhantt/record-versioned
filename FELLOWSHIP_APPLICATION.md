# AI Builders Fellowship application

Deadline: August 21, 2026 at 11:59 PM Pacific.

This is the form-ready answer sheet. The application form is the proposal, so no separate PDF is
required. Keep the repository private for now and leave the optional repository field blank unless
review access is arranged or the repository is made public.

## About you

**Your name**

Siddhant Rai

**Email**

[Enter the email you want the selection team to use]

**Location**

India

## The project

**Project title**

The Public Record Has a Changelog

**Project summary**

Government annual reports often enter an archive as isolated scans. Their catalogue records may
not reveal the reporting period inside a document, its neighboring volumes, or which sections can
be compared honestly.

I want to build an open-source change navigator for recurring Canadian government publications.
It will recover the sequence of a report series, follow programs and institutions across adjacent
volumes, and show each useful change beside the exact scanned pages that support it.

The working prototype reconstructs three Ontario Ministry of Housing reports from 1974/75 to
1976/77. It presents five reviewed change threads and an audit view of 23 validated section
alignments. During the fellowship I would expand this into a credible public artifact covering at
least ten volumes from the same series. It will surface evidence and uncertainty, not generate
claims about policy intent.

**Public benefit**

The primary user is someone trying to answer a concrete question such as: how did this program,
funding commitment, or public institution change from one annual report to the next?

A local journalist or civic researcher currently has to find each scan, infer its order, search
imperfect OCR, and compare pages side by side. The navigator would turn that work into a source-led
path: start with a reviewed change thread, see where it sits in the report sequence, then open both
original pages.

Librarians and archivists could also reuse the ordered manifests, reporting-period corrections,
and scope annotations as finding aids. Missing volumes, weak OCR, and uncertain matches would stay
visible instead of being hidden behind a clean narrative. The goal is not to tell people what the
record means. It is to make the evidence easier to reach, inspect, and challenge.

**Proposed approach**

I will start with the Ontario Ministry of Housing annual-report series already represented in the
collection. The prototype provides a three-volume vertical slice and a frozen labelled set.

The ingestion pipeline will cache Internet Archive metadata and DjVu XML, preserve page boundaries,
verify identifiers and checksums, and keep reporting periods separate from catalogue dates. Each
volume will be segmented by document scope so a heading under one corporation cannot be matched to
the same generic heading under another.

Matching will begin with deterministic normalized headings, adjacent-volume constraints, and scope
rules. A lightweight semantic model will only rank candidates whose wording changed. It earns a
place in the pipeline only if it improves precision on the frozen review set. Human review controls
what is published, and every displayed alignment carries two item identifiers, scan-page indexes,
source excerpts, method, and review status.

The public result will be a fast static explorer generated from a reproducible data export. If a
series lacks recurring structure, the system will publish a series navigator or a documented
negative result rather than force it into a changelog.

**Dataset interest**

This idea depends on the Canadian civics and open-government collection because the useful context
is split between catalogue records and the scanned documents themselves.

In the current prototype, the reports labelled 1974/75, 1975/76, and 1976/77 all have the catalogue
date 1975. The real sequence has to be recovered from internal volume evidence. A single scan can
also contain the ministry report plus separate reports for Ontario Housing Corporation, Ontario
Mortgage Corporation, Ontario Student Housing Corporation, and other bodies. That hierarchy is
both valuable public context and a necessary constraint for accurate comparison.

The archive's unevenness is part of the project. An earlier Alberta corpus looked like an annual
series by title but turned out to contain themed editions on unrelated subjects. The prototype
rejected it for change comparison. The original Internet Archive items remain the source of truth;
the project adds a reproducible navigation and evidence layer without replacing the scans.

**Work plan**

Week 1: Freeze the Ontario series and the project's public scope. Verify reporting periods, volume
membership, missing items, and document boundaries. Expand the labelled review set.

Week 2: Harden cached metadata and DjVu XML ingestion. Export an ordered manifest, page index, and
provenance record for each derived field.

Week 3: Implement hierarchical segmentation and deterministic section alignment. Add negative tests
for cross-entity matches, repeated headers, and OCR artifacts.

Week 4: Evaluate a semantic candidate ranker against the frozen labels. Keep it only if it improves
measured precision without weakening provenance. This is the planned decision point, not an assumed
feature.

Week 5: Expand the timeline, change digest, and paired-evidence interface. Manually review at least
100 high-confidence candidates across the series and fix systematic errors.

Week 6: Reduce scope if the evidence threshold is not met. Otherwise deploy the reviewed artifact
and publish the code, manifests, labels, exports, tests, and an engineering note covering successes,
failed corpora, and limitations.

**Expected deliverable**

A deployed open-source explorer for one fully reviewed Canadian government annual-report series,
covering at least ten ordered volumes. A user can begin with a program, funding decision, or public
institution, follow it across adjacent reports, and open the exact source pages behind each
displayed change.

The release will include a searchable change digest, reconstructed source timeline, paired-evidence
viewer, and downloadable evidence index. The repository will contain the ingestion and alignment
pipeline, frozen series manifest, review labels, tests, reproducible JSON export, and a short report
on useful results, rejected matches, and gaps in the archive. The artifact will be static and
portable; rebuilding it will not require a permanently running server.

**Success metric**

At least 10 ordered volumes, 100 manually reviewed high-confidence candidates, at least 90 percent
precision, source-page links for every displayed alignment, and zero cross-scope matches in the
frozen review set. A new user should reach both original scans behind a change thread in no more
than three interactions. If the precision target is missed, the honest fallback is a useful series
navigator plus a published negative result, not misleading change claims.

## Experience and links

**Relevant experience**

I am a backend engineer with about three years of experience building production systems in Python,
TypeScript, Go, and SQL. At DocsGPT I worked on retrieval, agent workflows, model routing, MCP
integrations, typed tool contracts, tracing, and provider fallbacks. I improved Qdrant retrieval
concurrency by 5x, reduced query latency by 1.3 seconds, and added CI coverage that reduced reported
production regressions by 40 percent.

My recent work is centered on systems that keep evidence and system behavior inspectable. I have
built read-only evidence correlation across operational sources, linked model and tool traces to
cost and outcomes, and contributed to projects including Coral, OLake, OpenFGA, and mcp-use.

For this application I built and tested the first vertical slice rather than assuming the archive
would cooperate. One candidate corpus failed the comparability test. The Ontario corpus produced 24
reviewed alignments, 23 of which were valid, for 95.8 percent precision. That process reflects how I
would approach the fellowship: preserve provenance, measure on labelled evidence, and narrow the
claim when the data does not support it.

**Portfolio URL**

https://record-versioned.vercel.app/

**Repository URL**

Leave blank while the repository is private. The code can be opened before the build period if the
project is selected.

**How did you hear about the fellowship?**

Through the Internet Archive Canada and BC + AI fellowship announcement.

## Confirm and submit

- Confirm availability from September 1 through mid-October 2026.
- Confirm private Notion storage and selection-team review after reading the privacy policy.
- Leave the optional newsletter box unchecked unless you want those updates.
