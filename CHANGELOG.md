# Changelog

Each release is a tag; the version is read from the tag and the version fields `docs/development.md` names, and each release's section is headed by its tag and date; a change not yet released goes under an `## Unreleased` heading above them, which becomes the tag and the date at the release.

## Unreleased

## v0.1.0 — 2026-10-26

The first release: two plugins in one repository, installed as plugins in Claude Code, Grok Build and Factory Droid, as Agent Plugins in Codex, GitHub Copilot, Cursor, Kiro, OpenHands, Devin, Cline, Goose and Antigravity CLI, and as skills in any agent that reads the Agent Skills layout.

- `research`: the setup (`/research:research-init`), the flow of ideas, questions with kill criteria, tasks and findings as typed Markdown records with transitions, a check, a ranked index and a session summary; the reference library of cards with read grades, extracts and online lookups, and the check that ties a document's reference entries to the cards; the read-only dashboard over both; the method, design and debug working rules — seven skills over four self-contained Python 3.11 scripts, standard library only.
- `formal`: the prover side for a project with a Lean 4 library — the `formal-init`, `handoff` and `land` skills over the `formal` script (the handoff check, the handback's manifest diff, the read-back packet), the prover session as an agent, and the declaration manifest's generator.
- The Agent Plugins 1.0 and Claude Code manifests over each plugin, and marketplaces for Claude Code (also read by GitHub Copilot and VS Code), Codex and Cursor; the pre-commit hooks `flow-check`, `library-check` and `formal-check`; the tests and their workflow; the release workflow; the documentation, published at [research-kit.livid.work](https://research-kit.livid.work).
