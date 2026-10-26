# Changelog

Each release is a tag; the version is read from the tag and the version fields `docs/development.md` names, and each release's section is headed by its tag and date; a change not yet released goes under an `## Unreleased` heading above them, which becomes the tag and the date at the release.

## Unreleased

**Upgrading**: after moving the hooks' `rev`, the marketplace's `ref` and the plugin to this release, run `flow index` once and commit the index: the flow renders its table in a new form, and `flow check` fails V11, naming the cause, until the index is regenerated; the library's index is unchanged.
A directions file written by v0.1.0 keeps its title `# Directions` beside its `## Directions` section, which markdownlint's MD024 flags where a project lints all its Markdown; rename the title by hand.

- The Zenodo concept DOI, 10.5281/zenodo.23664863, in `CITATION.cff` and the README, and the citation abstract names the agents the kit supports.
- `library check`'s L12 reads a line under the references heading as an entry, or names it as one it cannot read, only where it is written like one — a list item, a line opening with a surname and an initial, or a year in parentheses with names before it — so a paragraph of prose that mentions a year is left alone; an author with a particle such as d'Alembert is read.
- L12 names, for an entry no card agrees with, the nearest card and which of title, first author and year disagreed, and where the card's venue names the entry's year, says so: the mark of a card typed from its preprint.
- `flow rank ID N --insert` takes a rank another record holds and moves the rest down, so a new item goes to the top of the ranked list in one step; the next-list reference says so.
- A resolution or a refinement file appended to a record is set apart from its dated line by one blank line, so one opening with a heading no longer fails markdownlint's MD022 and is reverted.
- The flow's built-in markdownlint configuration, used where a project has none, turns MD013 off, since a record is one sentence per line; the files `flow init` writes pass it — the directions file is titled `# The owner's directions`, and the index's table has a delimiter row markdownlint's MD060 accepts — and the form of a direction in that file's comment is no longer read as a direction.
- V11 says when an index differs from the render only in its form, its records unchanged.

## v0.1.0 — 2026-10-26

The first release: two plugins in one repository, installed as plugins in Claude Code, Grok Build and Factory Droid, as Agent Plugins in Codex, GitHub Copilot, Cursor, Kiro, OpenHands, Devin, Cline, Goose and Antigravity CLI, and as skills in any agent that reads the Agent Skills layout.

- `research`: the setup (`/research:research-init`), the flow of ideas, questions with kill criteria, tasks and findings as typed Markdown records with transitions, a check, a ranked index and a session summary; the reference library of cards with read grades, extracts and online lookups, and the check that ties a document's reference entries to the cards; the read-only dashboard over both; the method, design and debug working rules — seven skills over four self-contained Python 3.11 scripts, standard library only.
- `formal`: the prover side for a project with a Lean 4 library — the `formal-init`, `handoff` and `land` skills over the `formal` script (the handoff check, the handback's manifest diff, the read-back packet), the prover session as an agent, and the declaration manifest's generator.
- The Agent Plugins 1.0 and Claude Code manifests over each plugin, and marketplaces for Claude Code (also read by GitHub Copilot and VS Code), Codex and Cursor; the pre-commit hooks `flow-check`, `library-check` and `formal-check`; the tests and their workflow; the release workflow; the documentation, published at [research-kit.livid.work](https://research-kit.livid.work).
