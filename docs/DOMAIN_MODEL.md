# Domain Model

The canonical domain model lives in `src/grounded_research/models.py`. That
file has field-level types, docstrings, and validation rules for every entity.

This document provides a quick-reference index. When models.py and this file
disagree, models.py wins.

Current runtime note:

- this document indexes the shipped compatibility/public entities in
  `models.py`
- Tyler-native literal entities also exist in
  `src/grounded_research/tyler_v1_models.py` and now persist in
  `PipelineState`
- if you need literal Tyler artifact shapes, consult
  `docs/TYLER_LITERAL_PARITY_AUDIT.md` and `tyler_v1_models.py`

## ID Conventions

| Prefix | Entity |
|--------|--------|
| `S-` | SourceRecord |
| `E-` | EvidenceItem |
| `A-` | Assumption |
| `AN-` | AnalystRun |
| `RC-` | RawClaim |
| `C-` | Claim (canonical) |
| `D-` | Dispute |
| `AR-` | ArbitrationResult |

IDs are trace-facing and human-readable, not content hashes.

## Literal Types

| Type | Values |
|------|--------|
| `TimeSensitivity` | `stable`, `mixed`, `time_sensitive` |
| `SourceType` | `government_db`, `court_record`, `news`, `academic`, `primary_document`, `web_search`, `social_media`, `platform_transparency`, `other` |
| `QualityTier` | `authoritative`, `reliable`, `secondary`, `unknown` |
| `ClaimStatus` | `initial`, `supported`, `revised`, `refuted`, `inconclusive` |
| `DisputeType` | `factual_conflict`, `interpretive_conflict`, `preference_conflict`, `ambiguity` |
| `DisputeRoute` | `verify`, `arbitrate`, `surface` |
| `ArbitrationVerdict` | `supported`, `revised`, `refuted`, `inconclusive` |
| `AnalystFrame` | `verification_first`, `structured_decomposition`, `step_back_abstraction`, `general` |
| `PipelinePhase` | `init`, `ingest`, `analyze`, `canonicalize`, `adjudicate`, `export`, `complete`, `failed` |

## Entity Relationships

```
ResearchQuestion
    └─► EvidenceBundle (1:1)
            ├─► SourceRecord (1:many)
            └─► EvidenceItem (1:many, each links to one SourceRecord)

EvidenceBundle
    └─► AnalystRun (1:3+, parallel, blind)
            ├─► RawClaim (1:many)
            ├─► Assumption (1:many)
            ├─► Recommendation (1:many)
            └─► Counterargument (1:many)

RawClaim ──dedup──► Claim (many:1, provenance preserved)

Claim ──conflict──► Dispute (many:many, route code-owned)

Dispute ──verify──► ArbitrationResult (1:1, cites new evidence)
                        └─► claim_updates (updates Claim.status)

ClaimLedger = claims + disputes + arbitration_results

PipelineState = full trace (question + bundle + runs + ledger + report + warnings)
```

## Planned-Future Entities

- `AssumptionLedger` — cross-analyst assumption deduplication (deferred; not
  part of the current active implementation plans)

## Open Design Questions

- Whether `AnalystRun.succeeded` should require non-empty claims beyond `error is None`
- Whether `FinalReport` should split into typed sections or stay compact in v1
- When `AssumptionLedger` should be promoted from deferred to current

## Resolved Direction

- Tyler-literal stage artifacts are the canonical runtime target
- compatibility/public surfaces are temporary migration debt slated for removal,
  not long-term co-equal APIs
