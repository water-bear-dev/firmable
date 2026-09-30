## Dataset Overlap
I'm pulling the 1,000-record samples right now. To ensure I can successfully find 50 overlapping businesses for the company profiles, should I intentionally bias my Part 1 triage toward interconnected domains (like procurement and charities), or keep the dataset selection domain-agnostic?
Answer: You can bias the sample or increase the top of the funnel. Overlap does not have to across all. If you ingest 10k-20k from each source, you will likely have some overlap.

## Human Review Boundary
I'm wiring up the multi-step agent's review step. Is an interactive CLI prompt showing a mapping diff sufficient for the "clear point at which a human is asked to approve", or do you prefer the pipeline to run headless and just emit artifacts for post-run review?
Answer: Yes, UI would be awesome to review run time.

## Transformation Configs
For the generic extractor engine. To adhere to the "config beats code" principle, should the agent-emitted config rely on declarative primitives (e.g., regex, type casting), or is allowing it to write dynamic code snippets (like inline Python) acceptable for this test?
Answer: Declarative primitives is better in config and you have a next step generating code.

## Entity Relationships
For part 3, I'm designing the relationship model. Since the prompt notes we can choose to explain why we left parent/subsidiary relationships alone, is a clean, flat deduplication model (pairwise links/clusters) perfectly fine for the 50 merged company profiles, or are you explicitly looking for hierarchical corporate mapping?
Answer: Simple model is fine for relationships, but more advanced, semantic solution will carry an edge and will highlight your work.. not expecting a fully formed hierarchy

