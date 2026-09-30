# Firmable schema-inference assignment

This repository contains a reproducible implementation of the technical assignment. Work is organised in phases and recorded in `EXECUTION_LOG.md`. Design decisions, cost, and the entity-relationship model are in `WRITEUP.md`.

## Prerequisites

- Python 3.11 or newer.
- Network access if you re-download the public sources (the ABN archive is about 615 MB).
- A logged-in [Codex CLI](https://github.com/openai/codex) only if you onboard a new source. Reproducing the delivered extraction, links, and profiles does not call a model; the approved configs are already in `configs/`.

Install the local package:

```bash
python3 -m pip install -e .
```

## Model

Schema inference used the Codex CLI provider (`--provider codex`) with no `--model` flag, so each propose/revise turn ran on the CLI’s default model. Run records label that model `Codex default`. Turns were capped at 2. One earlier Platform API attempt named `gpt-6-luna` was rejected for insufficient quota before inference and did not produce a config.

## Reproduce the delivered outputs

Run the tests:

```bash
PYTHONPATH=src:tests python3 -m unittest discover -s tests -v
```

The large public source files and derived samples are intentionally git-ignored.
To recreate them, download the selected sources (including the streamed ABN
archive; approximately 615 MB), then create deterministic training/held-out
samples:

```bash
PYTHONPATH=src python3 src/acquire_sources.py --include-streamed
PYTHONPATH=src python3 src/sample_sources.py
```

To regenerate the discovery shortlist independently:

```bash
PYTHONPATH=src python3 src/discovery.py
```

The commands below then recreate the delivered Phase 4–6 outputs without
additional model calls. Model-generated configs are already supplied in
`configs/`; onboarding a new source requires a logged-in Codex CLI or a funded
Platform API key.

## Runtime mapping agent

The agent defaults to the locally authenticated Codex CLI rather than the
Platform API:

```bash
PYTHONPATH=src python3 src/agent_pipeline.py abn_bulk_extract --provider codex --max-codex-turns 2 --max-cost-usd 10
```

It runs the propose and revise turns read-only, captures every prompt and
response in `outputs/agent_runs/`, and waits for human approval before writing
a configuration. Codex CLI reports plan quota rather than a dollar charge, so
the two-turn limit is the enforceable guard; the US$10 value is recorded and
enforced only for providers that expose dollar metering (such as the Platform
API).

## Phase 4 extraction

Emit validated canonical observations from every approved mapping config:

```bash
PYTHONPATH=src python3 src/extract_observations.py --ingested-at 2026-09-30T06:30:00+00:00
```

The command writes one JSONL observation file per source and
`outputs/observations/extraction_metrics.json`. It exits non-zero when any
record fails extraction or source-record IDs are not unique.

## Phase 5 resolution

Run conservative entity resolution after configs are approved. This expands the
disjoint training and held-out batches only because the original held-out batch
did not yield enough exact identifier overlaps for the 50-link review target.

```bash
PYTHONPATH=src python3 src/resolution.py --ingested-at 2026-09-30T07:00:00+00:00 --finalize-audit
```

Only exact cross-source ABN/ACN agreement produces accepted links. Every other
record is written to `outputs/unlinked_queue.jsonl` with an abstention reason.

## Phase 6 profiles

Build 50 field-level, provenance-rich profiles and a source-deletion
counterfactual:

```bash
PYTHONPATH=src python3 src/profiles.py --count 50
```

This writes `outputs/profiles.jsonl`, `outputs/profile_metrics.json`, and `outputs/source_deletion_counterfactual.json`.

## Where the outputs are

| Part | Files |
| --- | --- |
| 1. Shortlist | `outputs/shortlist.csv`, hand-check `outputs/reviews/shortlist_audit.csv`, view `outputs/shortlist.html` |
| 2. Mappings and observations | `configs/*.json`, `outputs/observations/*.jsonl`, `outputs/observations/extraction_metrics.json`, agent traces `outputs/agent_runs/`, view `outputs/part2.html` |
| 3. Links | `outputs/proposed_links.jsonl`, `outputs/unlinked_queue.jsonl`, hand-check `outputs/reviews/link_audit.csv`, `outputs/resolution_metrics.json`, view `outputs/part3.html` |
| 4. Profiles | `outputs/profiles.jsonl`, `outputs/profile_metrics.json`, `outputs/source_deletion_counterfactual.json`, view `outputs/part4.html` |
| 5. Write-up | `WRITEUP.md` |

Open the HTML files in a browser. Each one is self-contained and filters the table in the page.
