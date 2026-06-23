# Changelog

## v1 — 2026-06-23 (release candidate, CEO-gated on public-repo flip)

**Header change vs v0.** v1 is a **public-release candidate**. It generalizes
the v0 prompt-injection + sycophancy harness from Anthropic-only to three
providers (Anthropic + OpenAI + Groq), lands paired CLEAN + PLANTED live
receipts on every (provider × property) cell, and replaces v0's per-property
GitHub Actions workflows with a single cross-provider × property × leg matrix.

### Added

- `runner/providers.py` — Anthropic / OpenAI / Groq adapter layer behind a
  unified `LLMClient` surface. Judge model held constant on Claude Haiku 4.5
  across all targets to avoid confounding Δ with judge-model variation.
- `runner/run_pi_battery.py` — prompt-injection runner with `--provider` flag.
- `runner/run_syco_battery.py` — sycophancy runner with `--provider` flag.
- `.github/workflows/matrix.yml` — single cross-provider × property × leg CI
  matrix. Both legs asserted; PLANTED Δ failure is an empirical finding, not a
  CI failure.
- `ci/replay_receipt.py` — read-only receipt verifier. Re-aggregates over
  `per_probe_results` to detect tampering and re-asserts CLEAN thresholds.
  Used on fork PRs and when no provider secrets are configured.
- `receipts/live/v1_*` — 12 live receipts (3 providers × 2 properties × 2 legs).
- `run_live.sh` — orchestrator for the 12 cells (with provider/property
  filtering via env vars).

### Changed

- README leads with the planted-twin / independent-gate-evaluation methodology
  framing. Honest scope, non-claims, and a reproduce-in-30-min section moved
  above the file inventory.
- DISCLOSURE.md adds non-claims 5 (no vendor-comparison) and 6 (no
  third-party-framework instrumentation in v1), structural limitation L5
  (cross-provider parity caveats), and gates publication on §4a + §4b reviews
  + CEO sign-off.

### Removed

- v0's separate `clean.yml` + `planted.yml` workflows (superseded by the
  single matrix). The v0 directory is preserved at
  `experiments/cf-modeleval-v0/` for lineage.

### Honest empirical findings (carrying from v0)

- On both Anthropic Sonnet 4.6 and Anthropic Haiku 4.5, the Perez & Ribeiro
  Naive injection technique did not degrade CLEAN resistance (Δ ≈ 0pp on PI).
  Reported, not tuned. The v1 cross-provider receipts close the same Δ
  measurement on OpenAI gpt-4o-mini and Groq Llama 3.3 70B.

---

## v0 — 2026-06-14 → 2026-06-19 (frozen for lineage)

See [`../cf-modeleval-v0/README.md`](../cf-modeleval-v0/README.md) and
[`../cf-modeleval-v0/DISCLOSURE.md`](../cf-modeleval-v0/DISCLOSURE.md). v0
shipped:

- Anthropic-only live receipts for prompt-injection (Sonnet 4.6, Haiku 4.5).
- Anthropic-only live receipts for sycophancy (Sonnet 4.6, Haiku 4.5).
- Two-stage scorer (regex + LLM judge) with pinned judge prompts.
- Mock-mode + live-mode runners.
- Per-property GitHub Actions (clean.yml, planted.yml).
- DISCLOSURE.md non-claims 1–4 + structural limitations L1–L4.
