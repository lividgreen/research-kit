# Changelog

Each release is a tag; the version is read from the tag and the version fields `docs/development.md` names, and each release's section is headed by its tag and date; a change not yet released goes under an `## Unreleased` heading above them, which becomes the tag and the date at the release.

## Unreleased

- `docs/project-card.md`, the project's card on [www.livid.work](https://livid.work/projects/research-kit/), which the website copies at each release, held to the card's rules by the tests.

## v0.2.0 — 2026-10-27

**Upgrading**:

1. Move the hooks' `rev`, the marketplace's `ref` and the plugins to this release; in Claude Code, add the marketplace again at the tag with `--scope project` and run `claude plugin update`, and never remove the marketplace, which uninstalls the plugins for every project on the machine. [Install](docs/install.md#the-plugins-at-the-hooks-tag) gives the commands.
2. Copy the `land` skill's `scripts/DeclManifest.lean` over the workspace's copy: its `--own` now defaults to every root of the workspace's own packages, so the regenerated manifests can gain `hypothesis` rows for conditions defined in another package. Regenerate and commit the manifests before running `formal hypotheses` against an older revision.
3. With `[packages]` bound, `formal check` now reads the tree, and the `formal-check` hook fails on a stale manifest, an umbrella that leaves a module out, a module under a root `[packages]` does not bind, an untracked file under a root that git does not ignore, and an import against `[workspace] package_order`; regenerate or fix, or set `umbrellas = false` where an umbrella leaves modules out on purpose.
4. For the new gates, add `[anchors]`, `[register]` and the `[documents]` allowlists to `formal.toml` by hand, as [The bindings files](docs/bindings.md) shows them (`formal init` leaves an existing file alone), then the `formal-cite`, `formal-anchors` and `formal-register` hooks.

`[handoff] records` still reads a string, and the log's archive defaults to a directory beside the log.

The `formal` plugin:

- `formal cite` checks that every declaration name the documents cite resolves in the manifests, and that none is private only, retired yet present, or an API-docs link to a module not in the tree ([The checks](docs/checks.md#formal-cite-formal-anchors-formal-register) has the resolution order).
- `formal anchors` checks every `[Key] §N`, `[Key] Theorem N.M` and `[Key] Appendix X` of the Lean files against the numbered headings, bold statements and appendices of the document the key is bound to.
- `formal register` checks that the tracked files that ship carry none of the bound pattern classes, matched after the sanctioned expressions are cut from each line; an empty scope fails.
- `formal hypotheses` fails where a public theorem shipped at a base revision, or listed in a `--baseline` file, gained a named condition; `--update` locks a discharge and a new declaration into the baseline and never a growth, and a manifest with no `hypothesis` row is reported INERT, with exit 0 and nothing compared.
- `formal witnesses` reports, by module, the public theorems with two or more named conditions and no `_nonvacuous` witness.
- The three gates are hooks: `formal-cite`, `formal-anchors` and `formal-register`.
- `formal check` reads the tree: the manifests' modules against the files under each root, each root's umbrella, and the import direction of `package_order`.
- The handback compares each manifest with its own package's edited modules, and an edited umbrella of imports and guards needs no regenerated manifest.
- The handoff check reads a record named by any of `[handoff] records`' path prefixes, a file of `meta_names` or a reference key of `key_patterns`.
- `formal probe` and `formal init` read a lakefile under a workspace, or one it requires by path, as a package of it: one generator in the workspace, one manifest and command per package, `[packages]` and the package order filled; the probe marks an item not written yet `--`.
- `DeclManifest.lean`'s `--own` defaults to every root built in the workspace's own packages, so a condition defined in another package is no longer dropped; it prints the roots it took.

The `research` plugin:

- `flow log add FILE` writes an entry at the top of the log, reflowed and linted as a record's write is; `flow log archive --before DATE` moves the older entries verbatim into one file per month in `[paths] log_archive`, each link definition going with every file that uses it, and leaves a pointer under the log's title.
- `flow state --check --owner O` checks what a machine can see of a session's close: the inbox emptied, the active tasks in O's hand, the log's top entry dated today, every changed record named; it exits 2 for a part it could not decide.
- `flow reflow --check PATH…` holds the project's other prose to one sentence per line, and `flow reflow --as DEST DRAFT` checks a draft before it is placed, reporting only the markdownlint violations it would add.
- `library citecheck [DOC…]` checks that every author-year citation in a document has an entry in its own references, by first author and date, and that every entry is cited.
- An internal document's card takes its key from its file's stem (`reports/review-1.md` is `review-1`); a card already written keeps its key.
- `flow refine --body FILE` says that the body went to the question and names `flow task --question Q --body FILE` for a task's own body.
- The built-in reflow keeps a short bold label such as `**State.**` or `**Proposition 5.3 (Jen 1990).**` with the sentence it opens, keeps a Markdown hard break, and reads code fences by CommonMark's rule, as `library citecheck` does.

The skills and the documentation:

- `land` reads a guard pair one guard at a time, splits a read-back packet too large for one reader, and sweeps the proof paragraph's "the only named hypothesis" sentence; `handoff` falls back to a general-purpose subagent where the prover agent is not loaded and keeps the task's id out of the prompt; the workspace template gains the dependency and toolchain bump procedure and the nested-package trap.
- `method` gains Terminology, Documents (with a register test for a project that has none), Working with the owner, Evidence rules and `references/reviews.md`; `flow` says a design record is never authority and gains `references/closing.md` for a session's close; `debug` reads a background command's exit code from the tool.
- Install says how a Claude Code project moves its pin without removing the marketplace, as tested with Claude Code 2.1.310, and how sessions sharing a tree keep the hooks' stash from reverting each other's files.

## v0.1.1 — 2026-10-26

**Upgrading**: after moving the hooks' `rev`, the marketplace's `ref` and the plugin to this release, run `flow index` once and commit the index: the flow renders its table in a new form, and `flow check` fails V11, naming the cause, until the index is regenerated; the library's index is unchanged.
A directions file written by v0.1.0 keeps its title `# Directions` beside its `## Directions` section, which markdownlint's MD024 flags where a project lints all its Markdown; rename the title by hand.

- The Zenodo concept DOI, 10.5281/zenodo.23664863, in `CITATION.cff` and the README, and the citation abstract names the agents the kit supports.
- `library check`'s L12 reads a line under the references heading as an entry, or names it as one it cannot read, only where it is written like one — a list item, a line opening with a surname and an initial, or a year in parentheses with names before it — so a paragraph of prose that mentions a year is left alone; an author with a particle such as d'Alembert is read.
- L12 names, for an entry no card agrees with, the nearest card and which of title, first author and year disagreed, and where the card's venue names the entry's year, says so: the mark of a card typed from its preprint.
- `flow rank ID N --insert` takes a rank another record holds and moves the rest down, so a new item goes to the top of the ranked list in one step; the next-list reference says so.
- A resolution or a refinement file appended to a record is set apart from its dated line by one blank line, so one opening with a heading no longer fails markdownlint's MD022 and is reverted.
- The flow's built-in markdownlint configuration, used where a project has none, turns MD013 off, since a record is one sentence per line; the files `flow init` writes pass it — the directions file is titled `# The owner's directions`, and the index's table has a delimiter row markdownlint's MD060 accepts — and the form of a direction in that file's comment is no longer read as a direction.
- V11 says when an index differs from the render only in its form, its records unchanged.
- The setup probe skips a git submodule or a vendored clone when it looks for documents and Lean workspaces; shows a log or an instructions file not yet written as absent, marked `--`, rather than as present or missing; says when it runs from a git clone of the kit; compares the hooks' `rev`, the marketplace's `ref` in the project's settings and the plugin's own version; and reads a Makefile for a `check` target that runs the hooks rather than assuming one.
- The `method` skill checks a probe that ports a machine-checked statement against the prover, and counts a library docstring that summarizes a result among the summary sites a correction reaches; the `handoff` skill's refactor warning says the sweep touches names, visibility and file boundaries only.
- Install says how a project pins each agent's marketplace to the tag its hooks pin, and how a Makefile, a CI job or a script runs the kit outside the agent; Development says how a local trial of the plugins is cleared from Claude Code's cache, and the workflows install markdownlint, which the flow's selftest needs in CI.

## v0.1.0 — 2026-10-26

The first release: two plugins in one repository, installed as plugins in Claude Code, Grok Build and Factory Droid, as Agent Plugins in Codex, GitHub Copilot, Cursor, Kiro, OpenHands, Devin, Cline, Goose and Antigravity CLI, and as skills in any agent that reads the Agent Skills layout.

- `research`: the setup (`/research:research-init`), the flow of ideas, questions with kill criteria, tasks and findings as typed Markdown records with transitions, a check, a ranked index and a session summary; the reference library of cards with read grades, extracts and online lookups, and the check that ties a document's reference entries to the cards; the read-only dashboard over both; the method, design and debug working rules — seven skills over four self-contained Python 3.11 scripts, standard library only.
- `formal`: the prover side for a project with a Lean 4 library — the `formal-init`, `handoff` and `land` skills over the `formal` script (the handoff check, the handback's manifest diff, the read-back packet), the prover session as an agent, and the declaration manifest's generator.
- The Agent Plugins 1.0 and Claude Code manifests over each plugin, and marketplaces for Claude Code (also read by GitHub Copilot and VS Code), Codex and Cursor; the pre-commit hooks `flow-check`, `library-check` and `formal-check`; the tests and their workflow; the release workflow; the documentation, published at [research-kit.livid.work](https://research-kit.livid.work).
