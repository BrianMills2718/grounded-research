# Grounded Research Adjudication Walkthrough

Wiki home: http://localhost:8088/index.php/Project_Wiki

## Portfolio Claim

Grounded Research is strongest as an adjudication architecture. It shows how a research system can decompose a question, run independent analyst passes, detect disagreements, seek fresh evidence, and produce a final answer with provenance.

## Walkthrough

1. A question enters the planner.
2. The system decomposes it into claims and research tasks.
3. Multiple analyst passes produce independent evidence and conclusions.
4. The claim ledger records agreements, disagreements, and unsupported claims.
5. Dispute detection identifies claims requiring arbitration.
6. Fresh evidence search resolves or narrows disputes.
7. The final synthesis reports what changed, what remains uncertain, and which sources support the conclusion.

## What A Reviewer Should Inspect

| Artifact | Why it matters |
|----------|----------------|
| `README.md` | States the system claim and benchmark-style comparison record |
| `docs/ARCHITECTURE_ONE_PAGE.md` | Shows the architecture at a glance |
| `docs/DOMAIN_MODEL.md` | Defines claims, evidence, analysts, disputes, and synthesis objects |
| `docs/CONTRACTS.md` | Shows cross-component contracts |
| `output/fair_tyler_literal_parity_ubi_reanchor_v8_vs_ubi_dense_dedup_eval.md` | Shows an evaluation artifact rather than a polished-only demo |

## Caveat

Do not present this as a complete general-purpose research agent. Present it as evidence of dispute-aware, provenance-aware research architecture.
