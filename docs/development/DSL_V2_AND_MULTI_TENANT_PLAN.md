# Strategy DSL v2 and Multi‑Tenant Scoping — Plan

## Goals
- Strategy DSL v2: AND/OR nesting, duration (temporal hold), sequence semantics.
- Multi‑tenant scoping: full isolation per user/scope across indicators, strategies, sessions, and results.

## DSL v2 — Design Outline
- Data model:
  - Node: Condition | Composite(op: AND|OR, children: Node[]) | Duration(seconds, node) | Sequence(nodes: Node[], max_gap_s?: int).
  - Backing JSON structure compatible z JSON Schema (new schema v2).
- Evaluation:
  - Short‑circuit for AND/OR; three‑valued logic: TRUE/FALSE/PENDING.
  - Temporal state store per (strategy, symbol, nodeId): timestamps of last TRUE/FALSE transitions; duration windows.
  - Sequence: finite‑state machine over nodes with time bounds.
- Integration:
  - StrategyManager: add evaluator + per‑symbol node state; preserve existing 5‑group architecture.
  - Telemetria: emit detailed `strategy.*` events with node results for UI podglądu.
- Acceptance criteria:
  - Unit tests: semantics (AND/OR), duration windows, sequence order; edge cases (flapping, missing data, resets).
  - JSON Schema validation + helpful error messages.

## Multi‑Tenant — Design Outline
- Scope propagation:
  - API: `scope` param in REST/WS envelope; validated and logged.
  - Indicators: already support `scope` prefix in keys (tests added).
  - Strategies: registry per scope, file layout `config/strategies/{scope}/{name}.json`.
  - Sessions & results: directory layout `{mode}/{mode}_results/{scope}/{session_id}`; merge supports `base_dir` per scope.
- Isolation rules:
  - No cross‑scope listing by default; explicit admin scope only.
  - EventBus: tag events with `scope` and filter subscribers (optional in MVP).
- Acceptance criteria:
  - Tests: CRUD in separate scopes don’t leak; sessions in scope A aren’t visible in scope B; results merge limited to scope.

## Risks and Mitigations
- UI complexity (Canvas): progressive disclosure; templates; live validation; backend evaluator returns granular diagnostics.
- Performance: cache layer for indicator reuse; batch evaluation; rate‑limiting updates; load tests and memory profiling.
- Data consistency: symbol leasing (already in ExecutionController); per‑scope locks; idempotent session start.

## Phased Delivery
1) Schema + evaluator core (AND/OR) + tests.
2) Duration state store + tests; basic UI preview.
3) Sequence FSM + tests; UI sequence editor.
4) Full scope propagation (strategies, sessions, results) + access filters + tests.
5) Load testing and caching layer integration.

