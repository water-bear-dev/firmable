# Implementation Plan — Schema Inference and Entity Identification

## Objective

Deliver a reproducible, six-hour technical-assignment repository that discovers
candidate business datasets, uses a runtime multi-step agent to generate and
validate declarative mapping configurations, resolves entities conservatively,
and produces provenance-rich company profiles.

## Guiding Decisions

- **Prioritise evidence over volume.** Validate every source on a held-out
  1,000-record sample first; expand only the 2–3 sources needed to obtain 50
  high-confidence cross-source links.
- **Use one declarative extraction engine.** Mapping configs may use a bounded
  set of operations (rename, coalesce, regex extraction, normalisation, type
  casting, date parsing, constants, and field concatenation), never inline
  executable code.
- **Make abstention the default.** Fuzzy/semantic similarity only generates
  candidates. A proposed link needs an identifier match or a conservative,
  explainable combination of independent signals.
- **Make the agent auditable.** Every onboarding run persists its state,
  prompts/responses, proposed and revised config, validation report, elapsed
  time, and model/token/cost measurements.

## Per-Phase Execution Log

At the end of **every** phase, append a Markdown section to `EXECUTION_LOG.md`
using the following format. Record costs actually incurred where available;
otherwise label estimates clearly. Zero-cost deterministic work should still be
listed so the execution trail is complete.

```md
## Phase N — <name>

- **Actions completed:** <specific commands, artifacts, and decisions>
- **Outputs produced:** <paths and record counts>
- **Validation/result:** <acceptance-gate outcome or known failure>
- **Time:** <wall-clock duration>
- **Approximate cost:** <USD total; API/model token breakdown when applicable>
- **Notes / next step:** <risks, abstentions, or resumption point>
```

For model calls, the cost line must include model name, input tokens, output
tokens, and the pricing basis used for the estimate. The final `WRITEUP.md`
will aggregate these entries into one-time onboarding cost and per-record cost.

## Repository Layout

```text
README.md
WRITEUP.md
firmable_ontology.yaml
src/
  discovery.py               # CKAN catalogue retrieval and deterministic ranking
  agent_pipeline.py          # Stateful runtime mapping-inference workflow
  extractor.py               # Generic declarative-config extraction engine
  validation.py              # Held-out extraction/config checks
  resolution.py              # Candidate generation, scoring, abstention
  profiles.py                # Field-level merge, conflicts, provenance
  config_schema.py           # Typed config and observation contracts
configs/                     # Agent-approved mapping configs only
data/                        # Small raw samples and reproducible manifests
outputs/
  shortlist.csv
  observations/
  proposed_links.jsonl
  unlinked_queue.jsonl
  profiles.jsonl
  reviews/
  agent_runs/
```

Raw data that is too large to commit will be downloaded by a documented command
and represented in the repository by resource URLs, checksums, and manifests.

## Phase 0 — Bootstrap and Contracts (20 minutes)

1. Obtain and inspect `firmable_ontology.yaml`; stop if it is unavailable.
2. Initialise Python project metadata, dependencies, and a single runnable CLI.
3. Define versioned schemas for mapping configs, canonical observations, links,
   field provenance, conflicts, and review records.
4. Implement the allowed declarative transformation primitives and unit-test the
   generic extractor against small synthetic records.

**Acceptance gate:** One sample config produces a valid canonical observation;
unknown operations or nonexistent source fields fail clearly.

**Phase log:** Append Phase 0 actions, unit-test result, elapsed time, and
development/API cost (expected USD $0 before model calls) to `EXECUTION_LOG.md`.

## Phase 1 — Discovery and Triage (40 minutes)

1. Retrieve at least 200 CKAN catalogue records programmatically, saving the
   query parameters and raw response manifest.
2. Rank datasets deterministically using title, notes, organisation, tags,
   resource formats, and business-entity signals (e.g. ABN, company,
   contractor, supplier, licence, tender, charity).
3. Write `outputs/shortlist.csv` with exactly 50 records: ID, title, publisher,
   formats, confidence, and generated reason.
4. Select a seeded random sample of 20 shortlisted datasets and record manual
   review decisions and notes in `outputs/reviews/shortlist_audit.csv`.
5. Calculate and report the false-positive rate without excluding failures.

**Acceptance gate:** The shortlist can be regenerated from saved inputs without
manual dataset selection; the audit sample and seed are included.

**Phase log:** Append Phase 1 retrieval/ranking/audit actions, shortlist and
audit paths, false-positive rate, elapsed time, and catalogue/API cost to
`EXECUTION_LOG.md`.

## Phase 2 — Source Selection and Acquisition (20 minutes)

### Delegated research, coordinated acquisition

Use two bounded subagents in parallel. They may inspect public metadata and
make recommendations, but they do not write source-specific parsers, download
unbounded data, choose final sources, or alter shared contracts.

| Role | Assignment | Required hand-off artifact |
| --- | --- | --- |
| **Resource researcher** | Inspect 8–12 highly ranked candidates via CKAN `package_show`; report resource URLs/IDs, publisher, format, licence, access requirements, approximate size, and stable-record-ID evidence. | `outputs/reviews/source_feasibility.md` with a rank-ordered recommendation and rejection reasons. |
| **Overlap researcher** | Assess the same candidates for likely links to ABR/ASIC and across each other; identify identifier fields, entity-bearing fields, likely matching signals, and format/data-quality risks. | `outputs/reviews/source_overlap_matrix.md` with a conservative overlap assessment. |

The primary implementation workflow reviews both hand-offs and then:

1. Select six downloadable shortlist entries across multiple publishers and
   shapes, including at least one non-CSV format (for example XLSX, JSON, or
   GeoJSON). The selection rationale must cite both research artifacts.
2. Prefer sources with likely overlap, but document each source’s licence,
   resource URL, CKAN resource ID, download time, checksum, format, source
   size, and stable record identifier in a single authoritative manifest.
3. Download only selected resources and inspect their actual headers, sheets,
   archive contents, and encoding through shared readers before committing to
   the selection.
4. Create deterministic training and held-out samples for each source. The
   samples must be disjoint by record ID.

**Fallback rule:** Replace a candidate if its licence is unclear, it needs
credentials, cannot be read by shared tooling, lacks a usable stable record ID,
or is too large to sample within the time box. Log the exact reason rather than
quietly substituting it.

**Acceptance gate:** All six sources load through shared readers and have a
documented licence and a held-out validation sample.

**Phase log:** Append Phase 2 subagent assignments and hand-off paths,
source-selection rationale, licences, download manifests, sample sizes, elapsed
time, and download/storage cost (normally USD $0) to `EXECUTION_LOG.md`. Record
the subagents' work separately from primary-workflow integration time.

## Phase 3 — Runtime Agentic Mapping Workflow (90 minutes)

Implement one pipeline which takes an unseen resource and ontology and runs:

1. **Inspect:** identify format, sheets/objects, headers, row count estimate,
   encoding, candidate ID columns, and data-quality issues.
2. **Profile:** calculate field types, null rates, distinctness, representative
   values, and entity-signal hints from the training sample.
3. **Propose:** ask the model for a config conforming to the strict schema,
   mapped/unmapped fields, per-field confidence, and rationale.
4. **Extract:** run the generic extractor against the training sample.
5. **Validate:** apply the config to held-out records and compute structural
   checks (referenced columns exist; transforms succeed; parse failure/null
   rates; identifier uniqueness; canonical type conformance; suspicious values).
6. **Revise:** provide the proposal and machine-generated validation report to
   the model; require a revised config or an explicit abstention.
7. **Review:** render a CLI diff of proposed versus revised config, mapping
   confidences, unmapped fields, and validation results. Require a human
   approve/reject action before writing an approved config.

Persist a JSON state record after every step so failures can resume from the
last completed stage. Default to a low-cost model and record model name, input
and output tokens, estimated cost, and elapsed time.

**Acceptance gate:** Six configs are generated by this workflow, each has a
saved run trace and approval record, and no config contains executable code.

**Phase log:** Append one Phase 3 summary plus a per-source Markdown sub-list
recording pipeline stages completed, config/run-trace path, validation outcome,
human approval decision, elapsed time, model/token usage, and approximate USD
cost to `EXECUTION_LOG.md`.

## Phase 4 — Extraction and Quality Evidence (30 minutes)

1. Run the generic extractor over each held-out 1,000-record sample.
2. Write canonical observations with stable source record IDs, source metadata,
   mapping-config version, extraction timestamp, and per-field confidence.
3. For sources yielding too few viable matching candidates, expand extraction
   in measured batches only until enough candidates exist or a stated cap is
   reached.
4. Save source-level extraction metrics and any unmapped or rejected fields.

**Acceptance gate:** Output observations validate against the canonical schema;
source-level coverage and transform failure metrics are reportable.

**Phase log:** Append Phase 4 extraction actions, observations/metrics paths,
record counts by source, validation result, elapsed time, and compute/API cost
to `EXECUTION_LOG.md`.

## Phase 5 — Conservative Entity Resolution (45 minutes)

1. Normalise names, addresses, emails, phones, websites, ABNs/ACNs, and other
   available identifiers while retaining original values.
2. Block candidate comparisons using high-recall keys (ABN/ACN, normalised name,
   postcode/suburb, domain) to avoid all-pairs matching.
3. Score candidates with explicit evidence. Strong identifier agreement is the
   preferred automatic-link path; combinations of independent attributes can
   qualify only at a documented high threshold.
4. Emit `proposed_links.jsonl` containing both source record references, an
   entity key, numeric confidence, evidence, matcher version, and threshold.
5. Send ambiguous, contradictory, or weak-evidence candidates to
   `unlinked_queue.jsonl` with an explicit abstention reason.
6. Draw a seeded random sample of 50 proposed links and manually label it;
   calculate observed precision and retain all review decisions.

**Acceptance gate:** Every accepted link has inspectable evidence and every
ambiguous candidate has a reason for abstention. Precision uses an immutable
50-link review sample.

**Phase log:** Append Phase 5 normalisation and matching actions, threshold,
link/unlinked/review paths and counts, measured precision, elapsed time, and
matching/model cost to `EXECUTION_LOG.md`.

## Phase 6 — Profiles and Delivery (35 minutes)

1. Build one company profile for 50 linked entities using only accepted links.
2. Merge each canonical field independently, preserving winning value,
   field-level confidence, source-record provenance, alternates, and conflict
   resolution rationale. Omit unknown fields.
3. Run a source-deletion counterfactual and report how many profiles/fields
   change if each input source is removed.
4. Produce a two-page `WRITEUP.md` covering cost, agent design and failures,
   hardest source, scaling constraints, relationship model, rematching strategy,
   and next three-week investment.
5. Produce a clean-checkout README with install/run commands, expected runtime,
   environment variables, reproducibility limits, and known issues.

**Acceptance gate:** Required outputs exist, commands complete in under ten
minutes on cached/sample data, and the README honestly identifies any external
dependency or incomplete component.

**Phase log:** Append Phase 6 profile/documentation actions, output paths and
counts, clean-run result, elapsed time, and final incremental cost to
`EXECUTION_LOG.md`. Add a final total that reconciles every prior phase.

## Model-Upgrade / Reprocessing Design

Persist immutable source observations and source-record identifiers separately
from links and profiles. Version mapping configs, extractor, normalisers,
blocking strategy, matching model, scoring weights, threshold, and every input
feature/evidence item. New matching models create a new link-set version rather
than overwriting prior links; compare old/new results, prioritise changed
high-impact links for review, then rebuild profiles from the approved link-set.

## Time-box and Scope Controls

| Stage | Budget | Cut-back rule |
| --- | ---: | --- |
| Bootstrap/contracts | 20 min | Keep schema primitives minimal; defer extras. |
| Discovery/acquisition | 60 min | Use two parallel research subagents; retain one authoritative acquisition manifest and use formats with shared readers. |
| Agentic pipeline | 90 min | Finish one robust end-to-end path before all six runs. |
| Extraction | 30 min | Start at 1,000 records; expand only matching-rich sources. |
| Resolution | 45 min | Prefer exact identifiers and abstain on weak fuzzy candidates. |
| Profiles/docs | 35 min | Deliver accurate partial coverage rather than inferred values. |

If time expires, preserve the run traces and measurements, document the last
completed gate, and list the next engineering step rather than papering over
missing outputs.
