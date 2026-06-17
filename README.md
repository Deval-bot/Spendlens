## Methodology & Research Background

### The problem this addresses

Across industries, a large share of procurement value leaks away not through
the big strategic contracts but through **tail spend** — the long tail of
low-value, high-frequency, scattered purchases that no team has the bandwidth
to manage. The tail typically accounts for roughly 80% of transactions but only
about 20% of total spend, and it is where duplicate suppliers, off-contract
buying, and price inconsistencies concentrate. The Hackett Group's 2025 Tail
Spend Management Study reported that only about 4% of companies actively manage
most of their tail spend, while 64% of procurement leaders were dissatisfied
with their current approach.

The root cause is a **data problem, not a strategy problem.** Procurement
records in ERP systems (e.g., SAP) are full of the same supplier entered under
many different names, and items described in free-text shorthand. This makes
spend impossible to aggregate, classify, or benchmark reliably. SpendLens
attacks that data problem directly, then turns the cleaned data into decisions.

### Research foundation

- **Spend-analysis automation** — Li, Culmone, De Reyck & Yoo (2025), *INFORMS
  Journal on Applied Analytics* — the end-to-end pipeline this project is built on.
- **AI + human oversight** — *"AI meets spend classification: A new frontier in
  information processing"* (2025), *Journal of Purchasing and Supply Management* —
  the basis for keeping the user in control of classification.
- **Field map** — *"AI and ML in procurement and purchasing decision-support: a
  taxonomic literature review"* (2025), *Artificial Intelligence Review*.
- **Entity resolution with LLMs** — Fu et al. (2025), *Proceedings of the ACM on
  Management of Data*; Peeters, Steiner & Bizer (2025), *EDBT* — the basis for
  AI-based supplier-name matching.
- **Agentic procurement** — Jannelli, Schoepf, Bickel, Netland & Brintrup (2025),
  *International Journal of Production Research*; AlMahri, Xu & Brintrup (2026),
  *arXiv* — the basis for the multi-agent layer.

### How SpendLens implements these principles

| Capability | Method | Research basis |
|---|---|---|
| Supplier consolidation | Fuzzy matching + LLM in-context clustering | Fu et al. (2025); Peeters et al. (2025) |
| Universal classification | LLM infers categories per dataset, with human review | Li et al. (2025); spend-classification literature |
| Leverage analysis | Kraljic matrix (spend vs. supply risk) | Standard procurement strategy |
| Savings opportunities | Price-variance + tail-spend analysis | Industry best practice (Hackett, Sievo) |
| Agentic action | Supplier Risk agent → Sourcing Strategist agent | Jannelli & Brintrup (2025) |

### Roadmap

- **v1 — Descriptive analysis (done):** supplier consolidation, AI category
  classification, Kraljic leverage map, savings estimate. Industry-agnostic;
  bring-your-own-API-key; CSV and Excel upload.
- **v2 — Prescriptive savings (done):** price-variance detection and tail-spend /
  supplier-fragmentation analysis, output as value-ranked opportunities.
- **v2.5 — Frontier accuracy (done):** AI in-context clustering merges supplier
  aliases that fuzzy matching misses; a human-in-the-loop step lets the user
  correct any AI category before analysis.
- **v3 — Multi-agent action (done):** a Supplier Risk agent flags single-source
  and concentrated categories, then a Sourcing Strategist agent drafts risk-aware
  recommendations — opportunities, actions, RFQ shortlist, negotiation angles.
- **v4 — Planned:** agent-to-agent consensus-seeking, and external supplier-risk
  monitoring from live signals (after AlMahri, Xu & Brintrup, 2026).

### References

1. Li, X., Culmone, V., De Reyck, B., & Yoo, O. S. (2025). Automating
   Procurement Practices Using Artificial Intelligence. *INFORMS Journal on
   Applied Analytics, 55*(3), 195–223. https://doi.org/10.1287/inte.2023.0099
2. AI meets spend classification: A new frontier in information processing
   (2025). *Journal of Purchasing and Supply Management.*
3. AI and ML in procurement and purchasing decision-support: a taxonomic
   literature review and research opportunities (2025). *Artificial
   Intelligence Review.* https://doi.org/10.1007/s10462-025-11336-1
4. Fu, et al. (2025). In-context Clustering-based Entity Resolution with Large
   Language Models. *Proceedings of the ACM on Management of Data.*
   https://doi.org/10.1145/3749170
5. Peeters, R., Steiner, A., & Bizer, C. (2025). Entity Matching using Large
   Language Models. *EDBT*, 529–541.
6. Jannelli, V., Schoepf, S., Bickel, M., Netland, T., & Brintrup, A. (2025).
   Agentic LLMs in the Supply Chain: Towards Autonomous Multi-Agent
   Consensus-Seeking. *International Journal of Production Research.*
   https://doi.org/10.1080/00207543.2025.2604311
7. AlMahri, S., Xu, L., & Brintrup, A. (2026). Automating Supply Chain
   Disruption Monitoring via an Agentic AI Approach. *arXiv:2601.09680.*
   https://arxiv.org/abs/2601.09680