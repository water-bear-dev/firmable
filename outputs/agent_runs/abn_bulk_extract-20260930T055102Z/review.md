# Human Review — ABN Bulk Extract

## Validation outcome

- Held-out records: 1,000
- Extracted records: 1,000
- Contract/extraction errors: none
- Decision: awaiting human approval

## Mappings

| Destination | Source column | Confidence | Held-out coverage |
| --- | --- | ---: | ---: |
| `entity.abn` | `ABN` | 0.99 | 100.0% |
| `entity.acn` | `ASICNumber` | 0.95 | 82.4% |
| `entity.legal_name` | `NonIndividualNameText` | 0.98 | 96.2% |
| `address.state` | `State` | 0.99 | 99.9% |
| `address.postcode` | `Postcode` | 0.99 | 100.0% |

`EntityTypeText` is intentionally unmapped because no controlled crosswalk to
the ontology enum has been defined.

## Revision diff summary

The revision adds `strip` before ABN/ACN normalization, raises ACN/state/postcode
confidence, and changes postcode from `digits_only` to `strip`. No destinations
were added or removed.

## Recorded Codex usage

- Turn 1: 16,117 input tokens (6,912 cached), 401 output tokens, 128 reasoning-output tokens.
- Turn 2: 16,203 input tokens (13,056 cached), 411 output tokens, 131 reasoning-output tokens.
- Codex CLI reports plan quota rather than USD cost.
