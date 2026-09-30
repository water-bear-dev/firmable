# Human Review — ASIC Company

## Validation outcome

- Held-out records: 1,000
- Extracted records: 1,000
- Contract/extraction errors: none
- Decision: awaiting human approval

## Mappings

| Destination | Source column | Confidence | Held-out coverage |
| --- | --- | ---: | ---: |
| `entity.legal_name` | `Company Name` | 0.95 | 100.0% |
| `entity.acn` | `ACN` | 0.98 | 100.0% |
| `entity.abn` | `ABN` | 0.98 | 91.5% |
| `entity.date_registered` | `Date of Registration` | 0.96 | 100.0% |

The revision selected `Company Name` rather than the proposal's `Current Name`
for the legal-name claim. The latter is intentionally left unmapped, so this
choice needs reviewer confirmation even though the structural validation passes.

## Revision diff summary

The revision changes legal name from `Current Name` to `Company Name`, adds
`strip` before ACN/ABN normalisation, and supplies `%d/%m/%Y` for registration
date parsing. It leaves eleven low-confidence or semantically ambiguous fields
unmapped.

## Recorded Codex usage

- Turn 1: 16,539 input tokens (6,912 cached), 637 output tokens, 363 reasoning-output tokens.
- Turn 2: 17,055 input tokens (6,912 cached), 667 output tokens, 376 reasoning-output tokens.
- Codex CLI reports plan quota rather than USD cost.
