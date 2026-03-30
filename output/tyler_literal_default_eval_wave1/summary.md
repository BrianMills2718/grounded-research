# tyler_literal_default_eval_wave1

**Judge model:** `openrouter/openai/gpt-5.4-mini`
**Replicates per variant:** 3
**Question:** What is the current evidence from academic literature, pilot programs, and governmental reports regarding the impact of Universal Basic Income (with varying parameters) on workforce participation rates and related labor market outcomes?

## Variant Means

### tyler_literal
- mean score: `0.85`
- trials: `3`
- errors: `0`
- analytical_depth: `0.75`
- completeness: `0.75`
- conflict_and_nuance: `1.0`
- decision_usefulness: `1.0`
- factual_accuracy: `0.75`

### calibrated_legacy
- mean score: `0.6833333333333333`
- trials: `3`
- errors: `0`
- analytical_depth: `0.75`
- completeness: `0.5833333333333334`
- conflict_and_nuance: `0.9166666666666666`
- decision_usefulness: `0.6666666666666666`
- factual_accuracy: `0.5`

## Comparison

- mean tyler_literal: `0.85`
- mean calibrated_legacy: `0.6833333333333333`
- difference: `0.16666666666666663`
- confidence interval: `[0.09999999999999998, 0.25]`
- significant: `True`
- detail: SciPy bootstrap CI (95%) across 3 scored trials per variant: [0.1000, 0.2500]

## Limits

- one shared benchmark case only
- judge replicates estimate scoring noise but do not create broad task coverage
