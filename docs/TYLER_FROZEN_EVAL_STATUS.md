# Tyler Frozen Eval Status

This note records the current frozen Tyler-vs-legacy evidence after the first
eval-expansion wave.

## Current Frozen Cases

| Case | Tyler artifact | Legacy artifact | Tyler mean | Legacy mean | Difference | Significant |
|---|---|---|---:|---:|---:|---|
| UBI | `output/tyler_literal_parity_ubi_reanchor_v8/` | `output/ubi_dense_dedup_eval/` | `0.85` | `0.6833` | `+0.1667` | `True` |
| PFAS | `output/tyler_literal_pfas_eval_wave2/` | `output/pfas_v2_analytical/` | `0.7333` | `0.4333` | `+0.3000` | `True` |

## Conclusion

The frozen evidence is no longer a one-case story.

Current directional result:

- Tyler-literal is favored in `2/2` frozen cases
- both scored comparisons are statistically significant under the current
  bootstrap comparison method
- the result supports keeping Tyler-literal as the canonical runtime default

## Limits

This is still not broad ecosystem proof.

Current limits:

- only `2` matched frozen cases
- both cases are policy/evidence-heavy questions, not a diverse benchmark panel
- judge replicates estimate scoring noise, not task-distribution coverage

## Next Eval Frontier

The next evaluation work should:

1. add at least one non-policy/non-public-health matched frozen case,
2. keep archived calibrated legacy behavior eval-only,
3. continue using `prompt_eval`, not local alternate runtime modes.
