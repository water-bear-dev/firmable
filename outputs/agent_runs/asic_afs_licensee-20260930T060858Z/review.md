# Human Review — ASIC AFS Licensee

## Validation outcome

- Held-out records: 1,000
- Extracted records: 1,000
- Contract/extraction errors: none
- Decision: awaiting human approval

## Mappings

| Destination | Source column | Confidence | Held-out coverage |
| --- | --- | ---: | ---: |
| `entity.legal_name` | `AFS_LIC_NAME` | 0.98 | 100.0% |
| `entity.date_registered` | `AFS_LIC_START_DT` | 0.95 | 100.0% |
| `address.locality` | `AFS_LIC_ADD_LOCAL` | 0.97 | 99.9% |
| `address.state` | `AFS_LIC_ADD_STATE` | 0.98 | 99.9% |
| `address.postcode` | `AFS_LIC_ADD_PCODE` | 0.97 | 99.9% |
| `address.country` | `AFS_LIC_ADD_COUNTRY` | 0.98 | 100.0% |

## Reviewer attention

- `AFS_LIC_ABN_ACN` is intentionally unmapped. Its mixed identifier semantics
  make it unsafe to claim as an ABN without a source-specific format check.
- `AFS_LIC_NUM` is the stable source-record ID but is also listed as unmapped.
  Remove it from `unmapped_fields` before approval; this is a deterministic
  metadata correction and does not alter extraction output.

## Revision summary and recorded usage

The revision removes the unsafe ABN mapping, uses `AFS_LIC_NUM` alone as the
record ID, and supplies the date format. It used 33,544 input tokens (26,112
cached), 1,430 output tokens, and 660 reasoning-output tokens. Codex CLI did
not return a USD cost.
