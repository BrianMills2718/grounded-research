# Grounded Research Validation Register

Wiki home: http://localhost:8088/index.php/Project_Wiki

## Validation Position

This project has substantial implementation, audit, and benchmark evidence, but
the claims must stay scoped. The tracked benchmark wins and Tyler-compliance
work are evidence for specific artifacts and cases. They are not proof of
universal research-agent superiority.

## Current Evidence

| Evidence area | Current artifact | Claim licensed |
|---|---|---|
| Feature implementation | `docs/FEATURE_STATUS.md` | Original v1 scorecard features are mostly implemented or intentionally skipped/cut. |
| Tyler code-vs-spec review | `docs/TYLER_SPEC_GAP_LEDGER.md` | Tyler divergences and ambiguities are tracked as evidence-backed rows. |
| Architecture contracts | `docs/CONTRACTS.md`, `docs/DOMAIN_MODEL.md` | Phase boundaries and artifact contracts are documented. |
| Runtime tests | `tests/` | Stage contracts and runtime slices have deterministic coverage. |
| Benchmark comparisons | README and saved output/eval docs | The reported wins are scoped to tracked cases and comparison conditions. |
| Audit matrices | Tyler audit docs under `docs/` | Compliance claims are backed by audit artifacts, not only README prose. |

## Evidence Not Yet Present

Do not claim the following without additional evidence:

- general-purpose research-agent superiority;
- robust performance across arbitrary domains;
- complete hallucination prevention;
- complete retrieval recall;
- all Tyler ambiguities resolved by the upstream packet;
- complete source-quality calibration;
- suitability for high-stakes use without human review.

## Commands

Core verification:

```bash
make test
make check
python -m pytest
git diff --check
```

Focused examples:

```bash
python engine.py "Your research question"
python engine.py --fixture path/to/bundle.json
python scripts/compare_outputs.py --help
python scripts/eval_tyler_variants.py --help
```

Use actual saved run artifacts before making any portfolio claim about output
quality. For LLM costs, query the shared observability database rather than
estimating.

## Portfolio Readiness Gate

The project is already credible as an engineering artifact. It becomes much
stronger as a portfolio artifact when it has:

1. One short public question example.
2. A saved trace bundle.
3. A source-to-claim walkthrough.
4. A comparison note explaining what the benchmark does and does not prove.
5. A final public-facing caveat table.

