# Phase 2: Candidate Overlap Matrix

This is a desktop review of the Phase 1 CKAN metadata snapshot (`outputs/manifests/ckan_package_search.json`) and the shortlisted titles.  It is deliberately a feasibility assessment: exact header names and identifier coverage must be confirmed from each selected resource during acquisition.  “Likely” below is not a claim that a field has been verified.

| Candidate | Entity-bearing data and identifiers to verify | Conservative linkage path | Format / quality risks | Recommendation |
| --- | --- | --- | --- | --- |
| **ABN Bulk Extract** (ABR) | Public ABN-register attributes; metadata explicitly lists ABN, status, names and addresses. ACN may be present for company records—verify against schema XML. | Reference spine for exact normalized ABN; possibly ACN→ABN. Name + state/postcode only as a blocking signal. | ~1 GB across ZIP parts; XML/ZIP parsing; repeated names and historical trading names. Sample / stream only. | **Core**, but never full-load by default. |
| **ASIC – Company Dataset** | Company name, ACN, company status/dates are expected; ABN availability must be verified from the help file/header. | Exact ACN to ABR (or ABN if available); name + registration date only for review candidates. | 400 MB CSV / 79 MB ZIP; weekly schema changes (recent deregistration field); company ≠ business-name ambiguity. | **Core**. |
| **ASIC – Australian Financial Services Licensee** | Licensee identity, licence number, likely ABN/ACN, legal name and address components. | Exact ABN/ACN to ABR/company; exact licence number only intra-source. | Multiple representation files; geographic columns recently changed; one licensee may have related entities. | **Core**. |
| **ASIC – Credit Licensee** | Licensee identity, licence number, likely ABN/ACN, name and postal/business address. | Exact ABN/ACN to ABR/company and AFS where the same legal entity holds both licences. | Similar ASIC schema but not identical; licence holder can be an individual, trust or company. | **Core**: adds a distinct regulatory relationship and direct-link volume. |
| **Corporate Tax Transparency** (ATO) | Metadata explicitly states entity name and ABN plus income/tax amounts. | Exact ABN to ABR and ASIC-derived sources; names useful to diagnose legal/trading-name differences. | Annual XLSX; thresholded population (not representative); financial fields need sensitivity/provenance treatment. | **Core** and preferred non-CSV source. |
| **ACNC 2023 AIS Data** | Charity name, charity/ABN identifier, address and annual-statement attributes are likely; verify main-sheet headers. | Exact ABN to ABR; ACN only where the charity is incorporated. | XLSX has multiple sheets/resources; charity/group/member rows are not interchangeable; reporting year is historical. | **Core**, use main XLSX only for non-CSV coverage. |
| **ACNC Registered Charities** | Current register: name, ABN and charity regulatory status are likely. | Exact ABN to ABR / AIS; validates time-varying status and address conflicts. | Near-duplicate publisher/domain with AIS; weekly changes; can overstate source diversity. | Reserve / substitute for AIS if AIS main sheet lacks a usable stable record ID. |
| **Fair Jobs Code Registers** | Certificate/application business identity and status; ABN or address is unconfirmed in metadata. | Exact ABN if present; otherwise name + suburb/state only yields review candidates, not automatic links. | Tiny certificate resource; Salesforce export may change headers or redirect; uncertain identifier coverage. | Acquire-and-inspect fallback, not a core source until identifiers are verified. |
| **Tenders WA Contract Awards 2023–24** | Awarded supplier name, award/contract identifiers and agency/context; ABN is not asserted by metadata. | Exact ABN if a column exists; otherwise normalized supplier name + independently compatible state/address is review-only. | Supplier may be trading name, consortium or individual; contract rows repeat suppliers; WA-specific. | Useful diversity fallback, but insufficient alone for high-precision automatic links. |
| **Townsville Local Suppliers List** | Supplier identity and locality; ABN is unconfirmed, despite its procurement framing. | Exact ABN if supplied; otherwise name + locality is a candidate generator only. | Current, council-specific supplier list; XLSX/CSV representation drift; likely many small entities. | Optional diversity source after a header check. |
| **Victorian Government Schools ABNs** | Metadata explicitly promises school number and ABN; school name/location likely. | Exact ABN to ABR; school number is source-local. | XLSX; government schools may use distinct organisational ABNs and have limited overlap with commercial licensees. | Good small verification fixture, but weaker than the core six for 50 cross-source links. |

## Recommended six-source set

1. ABN Bulk Extract — sampled/streamed reference backbone.
2. ASIC Company Dataset.
3. ASIC Australian Financial Services Licensee Dataset.
4. ASIC Credit Licensee Dataset.
5. Corporate Tax Transparency (2023–24 XLSX).
6. ACNC 2023 AIS main XLSX.

This set yields several independent, conservative link paths: ABN is the primary edge; ACN↔ABN may support company records after verification; normalized legal name plus corroborating locality is only a blocking/review signal. It includes two non-CSV sources (Corporate Tax and ACNC AIS) while avoiding any need to assert fuzzy matches as links. The three ASIC datasets are intentionally related: that overlap is useful for a precision-first demonstration, while ABR, ATO and ACNC provide distinct publishers and domain-specific attributes.

## Source substitutions and gates

- If a core source has no stable source record ID, clear licence, or exact identifier in the selected resource, replace it in this order: **ACNC Registered Charities**, **Fair Jobs Code Registers**, then **Tenders WA** after a header inspection.
- Do not select both ACNC AIS and ACNC Registered Charities unless a documented test needs time-varying charity status; they are too close to count as meaningful source diversity.
- Do not automate a supplier/name-only match from Tenders WA, Fair Jobs or Townsville. Retain such records as unlinked or review candidates.
- Download only resource-level files selected after `package_show`; record resource ID, retrieval timestamp, licence, checksum, content type, stable-ID definition and exact-header evidence in the authoritative manifest.

