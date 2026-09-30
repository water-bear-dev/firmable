## Phase 1: Data Discovery & Triage (Hour 1)

* **Programmatic Retrieval:** Query the CKAN API from `data.gov.au` (or state equivalents) to pull at least 200 catalogue records.


* **Shortlisting (with Bias):** Based on the interviewer's advice, intentionally bias your filtering toward interconnected domains (e.g., procurement, ABN registers, charities) to maximize overlapping entities. Output a ranked shortlist of 50 datasets containing dataset ID, title, publisher, format, confidence, and a one-line reason.


* **False Positive Check:** Hand-check 20 of the 50 datasets and document your honest false positive rate.



## Phase 2: Agentic Schema Inference & Extraction (Hours 2 - 3.5)

* **Dataset Selection:** Choose 6 datasets from your shortlist, ensuring at least one is not a clean CSV.


* **Agent Pipeline Design:** Build the multi-step agent to inspect the source, propose a mapping against `firmable_ontology.yaml`, validate it against unseen records, and revise its own output.


* **Human-in-the-Loop UI:** Per the interviewer's feedback, implement a clean interactive CLI or basic UI prompt that presents the agent's proposed mapping and asks for your approval before finalizing the config.
* **Declarative Configurations:** Ensure the agent emits configs using strictly declarative primitives (e.g., regex, date-casting) rather than dynamic code, as the interviewer confirmed this is preferred.
* **Generic Extractor Engine:** Write exactly one extractor engine that parses these configs. Run it over 10,000 to 20,000 records per source (rather than just 1,000) to guarantee you find enough overlapping entities for the next phase.



## Phase 3: Entity Resolution & Assembly (Hours 3.5 - 5)

* **Relationship Modeling:** Build a flat deduplication model (pairwise links or clusters) as the baseline. To capture the "edge" the interviewer mentioned, add a lightweight semantic matching layer (e.g., fuzzy string matching or cheap embeddings on company names/addresses) to detect non-exact overlaps.
* **Verification & Abstention:** Hand-check 50 proposed links to measure precision. Generate an "unlinked queue" documenting records you refused to link and why.


* **Profile Generation:** Produce 50 merged company profiles (one per entity). Ensure each field explicitly tracks its source provenance, its field-level confidence (not a global score), and documents the conflict-handling logic used when sources disagreed.



## Phase 4: Write-up and Repository Polish (Hours 5 - 6)

* **Documentation:** Write a `README.md` guaranteeing the project can run from a clean checkout in under 10 minutes.


* **The Write-up (Max 2 Pages):**
* Detail your total API cost and token usage per source.


* Explain your agent's state management and identify its weakest step.


* Identify the hardest dataset you tackled and how you handled it.


* Explain what breaks when scaling from 6 to 500 sources.


* **Crucial focus:** Detail your strategy for updating millions of existing links if the matching model improves in six months.




* **Final Output Check:** Ensure your repo contains the 50-item shortlist, 6 mapping configs, canonical observations, proposed links, unlinked queue, 50 profiles, and your precision hand-check materials.