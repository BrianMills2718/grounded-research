# Tavily Integration Wave 1

**Status:** In Progress
**Type:** implementation
**Priority:** High
**Blocked By:** `open_web_retrieval` Tavily adapter landed on `main`
**Blocks:** faithful Tyler provider execution from the live `grounded-research` runtime

---

## Gap

**Current:** `grounded-research` still imports `grounded_research.tools.brave_search`
and hardcodes Brave-backed search semantics in Stage 2 collection and Stage 5
verification. Shared Tavily support now exists in `open_web_retrieval`, but the
application does not consume it.

**Target:** replace the Brave-specific search tool with one shared-provider
search tool. Default provider becomes Tavily for quality-first execution, while
remaining configurable in `config.yaml`.

**Why:** Tyler assumed Tavily-class search behavior. Now that shared infra
provides it, keeping Brave hardcoded in the application is just stale local debt.

---

## Pre-Made Decisions

1. Replace `grounded_research.tools.brave_search` with
   `grounded_research.tools.web_search`.
2. Keep one caller-facing tool contract:
   - `search_web(query, count, freshness, trace_id, task) -> JSON string`
   - downstream `collect.py` / `verify.py` callers should not fork by provider
3. Default provider is Tavily via config:
   - `collection.search_provider: "tavily"`
4. Provider remains configurable:
   - `"tavily"`, `"brave"`, or `"searxng"`
5. Result schema returned to callers stays stable:
   - `source`
   - `query`
   - `freshness`
   - `results[]` with `title`, `url`, `description`, `age`
6. Tavily's missing `age` field maps to an empty string rather than a second
   result contract.
7. No provider fallback chain in this wave.

---

## Files Affected

- `docs/notebooks/33_tavily_integration_wave1.ipynb` (create)
- `docs/plans/tavily_integration_wave1.md` (create)
- `docs/plans/CLAUDE.md` (modify)
- `docs/ROADMAP.md` (modify)
- `docs/PLAN.md` (modify)
- `config/config.yaml` (modify)
- `src/grounded_research/config.py` (modify)
- `src/grounded_research/tools/web_search.py` (create)
- `src/grounded_research/tools/brave_search.py` (delete)
- `src/grounded_research/collect.py` (modify)
- `src/grounded_research/verify.py` (modify)
- `tests/test_web_search.py` (create)
- `tests/test_brave_search.py` (delete)
- `tests/test_collect.py` (modify)
- `tests/test_verify.py` (modify)

---

## Success Criteria

### Step 1: Tool contract cutover

Pass:

- no live import of `grounded_research.tools.brave_search` remains
- new `web_search.py` reads provider config and env cleanly
- Tavily is the shipped default provider

Fail:

- provider logic leaks into `collect.py` or `verify.py`
- separate result schemas appear per provider

### Step 2: Verification

Pass:

- targeted web-search, collect, and verify tests pass
- one live Tavily search smoke succeeds from `grounded-research`
- docs reflect Tavily as the quality-first default and provider choice as config

Fail:

- tests only pass by preserving Brave-only imports
- docs still imply Brave is the canonical search path

---

## Failure Modes

| Failure Mode | Detection | Response |
|--------------|-----------|----------|
| Tavily result fields do not match current caller assumptions | `collect.py` or `verify.py` tests fail on missing `age` | preserve the old caller schema in `web_search.py` and normalize missing fields there |
| Config drift creates hidden provider behavior | tests need environment-specific patching in many places | centralize provider selection in `config.py` and keep the tool interface fixed |
| Stage 5 verification quality depends on provider-specific metadata not preserved by the old schema | dispute tests or live smoke look weaker | add only the minimum extra provider metadata needed, documented as an extension |

---

## Implementation Order

1. Add config accessor for search provider
2. Create `tools/web_search.py`
3. Replace imports in `collect.py` and `verify.py`
4. Update tests to the new import path
5. Delete the Brave-specific tool and tests
6. Run targeted tests and one live Tavily smoke
7. Reconcile active docs
