# Domain Model

The canonical domain model lives in `src/grounded_research/models.py`. That
file has field-level types, docstrings, and validation rules for every entity.

This document provides a quick-reference index. When models.py and this file
disagree, models.py wins.

Current runtime note:

- Tyler-native literal entities in `src/grounded_research/tyler_v1_models.py`
  are the canonical semantic runtime artifacts and persist in `PipelineState`
- `models.py` now mostly holds support entities: evidence records, validation,
  phase traces, Stage 3 attempt traces, and top-level pipeline state
- if you need literal Tyler artifact shapes, consult
  `docs/TYLER_LITERAL_PARITY_AUDIT.md` and `tyler_v1_models.py`

## ID Conventions

| Prefix | Entity |
|--------|--------|
| `S-` | SourceRecord |
| `E-` | EvidenceItem |
| `A-` | Tyler assumption IDs inside canonical artifacts |
| `C-` | Tyler claim IDs inside canonical artifacts |
| `D-` | Tyler dispute IDs inside canonical artifacts |

IDs are trace-facing and human-readable, not content hashes.

## Literal Types

| Type | Values |
|------|--------|
| `TimeSensitivity` | `stable`, `mixed`, `time_sensitive` |
| `SourceType` | `government_db`, `court_record`, `news`, `academic`, `primary_document`, `web_search`, `social_media`, `platform_transparency`, `other` |
| `QualityTier` | `authoritative`, `reliable`, `unknown`, `unreliable` |
| `PipelinePhase` | `init`, `ingest`, `analyze`, `canonicalize`, `adjudicate`, `export`, `complete`, `failed` |

## Entity Relationships

```
ResearchQuestion
    └─► EvidenceBundle (1:1)
            ├─► SourceRecord (1:many)
            └─► EvidenceItem (1:many, each links to one SourceRecord)

EvidenceBundle + Tyler Stage 1/2
    └─► Tyler AnalysisObject[] (1:3+, parallel, blind)
            └─► Tyler ClaimExtractionResult
                    └─► Tyler VerificationResult
                            └─► Tyler SynthesisReport

PipelineState = full trace (question + bundle + Tyler stage artifacts + warnings)
```

## Planned-Future Entities

- `AssumptionLedger` — cross-analyst assumption deduplication (deferred; not
  part of the current active implementation plans)

## Open Design Questions

- whether `models.py` should remain a mixed support-model + pipeline-state file
  or be narrowed further now that semantic runtime contracts live in
  `tyler_v1_models.py`

## Resolved Direction

- Tyler-literal stage artifacts are the canonical runtime target
- legacy structured-report and handoff outputs are already removed from the
  live runtime path
- historical current-shape artifacts are preserved only by commits and archived
  docs, not as co-equal runtime APIs
