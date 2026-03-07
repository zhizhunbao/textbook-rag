# Textbook Compliance Log

This file is the repository's cumulative correction ledger for textbook-lookup compliance.

Use it as a process notebook for misses and hardening updates:
- Record every case where workflow, skill use, implementation, testing, or review started before textbook lookup.
- Record every rule upgrade that was added to prevent the same miss from recurring.
- Append entries; do not rewrite history.

## Entry Template

| Date | Scope | Issue | Correction | Prevention |
| --- | --- | --- | --- | --- |
| YYYY-MM-DD | testing / backend / review / workflow | What textbook step was missed or delayed | What was re-read, rewritten, or re-reviewed | What rule or checklist change prevents recurrence |

## Entries

| Date | Scope | Issue | Correction | Prevention |
| --- | --- | --- | --- | --- |
| 2026-03-06 | testing | Added backend tests and only afterward backfilled textbook citations instead of reading mapped textbook sections first. | Re-read `dev-senior_qa`, `.agent/config/textbook-skill-mapping.yaml`, relevant textbook sections, then updated test headers and testing review artifacts to state the textbook basis. | Hardened `AGENTS.md`, `.agent/workflows/dev-codex.md`, and `.cursor/rules/textbook-source-required.mdc` so textbook lookup is a blocking prerequisite and misses must be logged here. |
| 2026-03-06 | review | Review gate initially did not require reviewers to verify textbook lookup or update this compliance ledger. | Rewrote `dev-phase_reviewer`, review checklists, and the phase re-review rule so reviewer workflow now checks textbook basis and records misses. | Review is now covered by explicit hard rules and checklists instead of relying on outer workflow guidance alone. |
