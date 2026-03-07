# Agent Operating Guide

This repository uses a `/dev` workflow as the default development protocol.

Codex compatibility is provided through this file plus `.agent/workflows/dev-codex.md`.
Do not treat `/dev`, `/dev start`, `/dev review`, or similar strings as literal shell
commands. Treat them as intent labels and execute the documented workflow steps directly.

## Primary workflow source

- Canonical legacy workflow: `.agent/workflows/dev.md`
- Codex bridge workflow: `.agent/workflows/dev-codex.md`
- Detailed phase steps: `.agent/workflows/full-development-steps/`
- Role mapping: `.agent/workflows/metagpt-enhanced/roles.yaml`

## Always-on rules

1. Use `.dev-state.yaml` as the single source of truth for phase progress.
2. Respect the canonical phase order:
   `requirements -> prd -> ux_design -> architecture -> stories -> database -> backend -> frontend -> testing -> review -> deployment`
3. Enforce mandatory phase review and re-review before marking a phase completed.
4. Follow Windows PowerShell execution constraints in this repo.
5. Read textbook references before any workflow phase, skill-driven task, implementation, testing, or review work, and use textbook-sourced rationale for those decisions.
6. Prefer templates and scripts in `.agent/templates/` and `.agent/scripts/` before creating new structures from scratch.
7. Maintain `docs/process/textbook-compliance-log.md` as a cumulative correction ledger for textbook-lookup misses, late citations, and rule hardening updates.

## Codex routing rules

When the user intent matches one of the following cases, read the referenced file first
and then execute the task directly.

- Dev workflow continuation, `/dev start`, progress checks, phase skipping, or jumping:
  read `.agent/workflows/dev-codex.md`
- Phase completion, quality gate, re-review, or review report generation:
  read `.agent/skills/dev-phase_reviewer/SKILL.md`
- Product, requirements, PRD, discovery, or prioritization tasks:
  read `.agent/skills/dev-product_manager/SKILL.md`
- Backend implementation, API design, database-access code, or backend review:
  read `.agent/skills/dev-senior_backend/SKILL.md`
- Python frontend implementation, UI work, or frontend review in this repository:
  read `.agent/skills/dev-python_frontend/SKILL.md`
- JavaScript/TypeScript frontend work for a different stack:
  read `.agent/skills/dev-senior_frontend/SKILL.md`
- Architecture or system design tasks:
  read `.agent/skills/dev-senior_architect/SKILL.md`
- Testing strategy, pytest work, or coverage work:
  read `.agent/skills/dev-senior_qa/SKILL.md`
- DevOps, CI/CD, deployment, or environment validation:
  read `.agent/skills/dev-senior_devops/SKILL.md`
- Data pipeline, ETL, indexing, or data engineering work:
  read `.agent/skills/dev-senior_data_engineer/SKILL.md`
- UX design work:
  read `.agent/skills/dev-ui_ux_designer/SKILL.md`
- Code review requests:
  read `.agent/skills/dev-code_reviewer/SKILL.md`

## Execution constraints

- Apply the short, always-on constraints in `.cursor/rules/` as repository policy.
- Prefer PowerShell-native commands on Windows.
- Python commands must use `uv run`.
- Do not use `cd` in shell commands; use the tool working directory.
- If a skill contains examples that conflict with repository rules, follow repository rules.
- Textbook lookup is a blocking prerequisite, not an optional documentation step.

## Rule precedence

1. Direct user instruction
2. This `AGENTS.md`
3. `.cursor/rules/*.mdc`
4. `.agent/workflows/dev-codex.md`
5. Other long-form documents under `.agent/`

If two repository instructions conflict and the safer resolution is not obvious, ask the user.
