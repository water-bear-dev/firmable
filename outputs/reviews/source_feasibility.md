# Phase 2 — Resource Feasibility Review

This review is based on live CKAN `package_show` responses saved under
`outputs/manifests/`. All selected resources are CC BY 3.0 AU and publicly
downloadable without credentials as checked on 2026-09-29.

| Candidate | Chosen resource | Publisher / format / size | Feasibility and stable-ID evidence | Decision |
| --- | --- | --- | --- | --- |
| ABN Bulk Extract | `0ae4d427-6fa8-4d40-8e76-c6909b5a071b`, Part 1 ZIP | Australian Business Register; ZIP; 498.4 MB | Public bulk extract with XSD and readme. ABN must be confirmed as the row-level identifier from the sampled XML; stream/sample rather than fully loading. | Select as identifier reference source. |
| ASIC Company Dataset | `d6d03876-71a4-4e82-8c77-2e4df5da4236`, current ZIP | ASIC; ZIP/CSV; 79.2 MB | Public current extract and companion help file. Confirm company ACN column and use it as the source-record ID if unique. | Select. |
| ASIC AFS Licensee | `d98a113d-6b50-40e6-b65f-2612efc877f4`, current CSV | ASIC; CSV; 11.4 MB | Public current extract with help file and alternate TSV/XLSX representations. Confirm licence number and ABN/ACN fields. | Select. |
| ASIC Credit Licensee | `35953a01-a9a8-4609-8566-c9fa7de465d3`, current CSV | ASIC; CSV; 6.9 MB | Public current extract with help file. Likely high overlap but would make three of six from ASIC. | Reserve fallback. |
| Corporate Tax Transparency | `491b366b-aa6f-4b1c-b39d-cebaeeb6f874`, 2023–24 XLSX | Australian Taxation Office; XLSX; 276 KB | Public annual report. Inspect sheet/header to confirm ABN and retain ABN as record ID. | Select; non-CSV source. |
| ACNC 2023 AIS | `f8d9f239-012b-46af-86b5-5f6d9a49af1a`, main XLSX | ACNC; XLSX; 21.5 MB | Public main annual-statement workbook, separate from group-members/programs resources. Confirm charity ABN/registration number. | Select; non-CSV source. |
| Tenders WA 2023–24 | `855378f8-0398-4a0a-a1c2-218816508ec9`, CSV | WA Department of Treasury and Finance; CSV; 4.6 MB | Public contract-award extract. Contract identifier is likely stable; supplier ABN is not claimed by metadata and must be verified. | Select as the deliberately messier, different-publisher source. |
| Fair Jobs Code Registers | Multiple CSV resources | Victorian Department of Jobs, Skills, Industry and Regions; CSV | Public registers but likely smaller and ABN presence is unverified. | Fallback if Tenders WA cannot produce entity-bearing observations. |

## Final six and rationale

1. ABN Bulk Extract (sampled reference spine)
2. ASIC Company Dataset
3. ASIC Australian Financial Services Licensee Dataset
4. Corporate Tax Transparency 2023–24
5. ACNC 2023 AIS main workbook
6. Tenders WA Contract Awards 2023–24

This preserves five publishers, includes ZIP/CSV/XLSX shapes, and gives both
identifier-led links (ABN/ACN expected in the first five) and a realistic
supplier-name source that will exercise abstention. ASIC Credit Licensee is the
first substitution if the selected Tenders resource fails the header/entity
check.
