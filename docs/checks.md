# The checks

Every problem `flow check` and `library check` report carries a code; this page names each, then says what the checks reporting in words verify: `flow state --check`, `flow reflow`, `library citecheck` and the `formal` plugin's checks.
The kit's tests hold it to the scripts: a code a script can report and this page does not name fails them.
Each check ends with coverage lines saying what it looked at and what it did not, and each script's `--selftest` plants one defect per code and fails when a code it can report is planted nowhere.

## Exit codes

Every check exits 0 when clean, 1 when it found problems, each printed with its place, and 2 when it could not run: no bindings file at the root, or one that does not parse.
The 2 is its own code so that a hook or a CI job never reads "did not run" as "clean".
`flow reflow --check` and `library citecheck` given a file that is not there, `library citecheck` with no document given and none bound, and `flow state --check` without an owner `flow.toml` lists, exit 2 as well; `flow state --check` exits 1 when a part fails, else 2 when a part could not be decided, else 0.

## `flow check`

| Code | What it says |
| --- | --- |
| V0 | a record file cannot be read: no front matter, a value outside the subset the tool writes, a byte that is not UTF-8, or an id another file carries; the check reads the rest of the tree without it |
| V1 | the record's type is not one of the four, it has no id, or its id does not match its filename or its type's prefix |
| V2 | a reference field names an id that does not exist, or a record of the wrong type |
| V3 | a field is missing or unknown, or a state, kind, size, owner, status or origin is not a legal value |
| V4 | a task of a kind that needs a question has none |
| V5 | a ready task has unmet `requires` |
| V6 | a finding has no evidence, an evidence item does not resolve, or the status does not match the kinds of evidence present |
| V8 | a cycle through `derived_from`, `depends_on` or a question's `parent` |
| V9 | an active task has no owner, or an owner holds more active tasks than its hand limit |
| V10 | a decomposed question has no task |
| V11 | the index is missing or stale — run `flow index` |
| V12 | an open or decomposed question has no last-checked date |
| V13 | an open task sits under a question that is neither open nor decomposed |
| V14 | a rank on a closed record, on owner-only work or on a parked question, a ranked record with no `why_now` or `first_move`, two records at one rank, or ranks that are not 1..n |
| V15 | a parking block that is not a map with a date and a reason, or on a question that is not open |
| V16 | a current question has no kill criteria |
| V17 | an abandoned record has no dated reason, or a consumed idea has no question deriving from it |
| V18 | an answered question names nothing it is answered by, or names a task that is not done or not drawn under it |
| V19 | a body is not one sentence per line |
| V20 | a date — `created`, `checked`, `drawn`, a parking's or an abandonment's — is not an ISO date or is in the future, or a done task still carries an owner |
| V21 | a record is not in its type's directory, a closed task is not in the archive, or an open one is |
| V22 | a question's direction names no bullet of the directions file |
| V23 | a record cites a library key the library does not hold, or an extract its card does not carry; or the library did not answer |

The codes are names, not a sequence: V7 is unassigned.
The one warning (which does not fail the check) names a decomposed question whose tasks are all closed, which needs refine or answer.

## `flow state --check`

`flow state --check --owner O` checks what a machine can see of a session's close, O the working session's owner, and prints one line per failure, each with its file:

- the directions file's inbox holds a line outside a comment;
- an active task is held by another owner than O, a decision owner `flow.toml` names aside;
- the log's top entry is not dated today, and the tree has changed since the commit of the newest committed entry, another's commit on a shared repository included;
- a record changed since that commit, and no entry from the top down to that one names its id.

Its last line says what it checked; a part it could not decide — no inbox section, no log bound, no git, no committed entry — is named on a line of its own and is not counted as passed: with no failure, the check exits 2.
Under `--json` each failure is a problem of code `STATE`.

## `flow reflow`

`flow reflow --check PATH…` prints each line, as file and line, that the reflow would change, and `flow reflow --as DEST DRAFT` each line of the draft that the reflow would change and each markdownlint violation the draft adds appended to DEST, never one DEST had already.
Under `--json` they are problems of code `REFLOW` and `MARKDOWNLINT`; the last line says which reflow ran and whether markdownlint did.

## `library check`

| Code | What it says |
| --- | --- |
| L0 | a card's front matter cannot be read: it is outside the subset the tool writes |
| L1 | the file's name is not lowercase letters, digits and hyphens, or the key is not the file's name |
| L2 | a field is missing, unknown or of the wrong shape, a kind the project does not list, a title missing, a year that is not a number, `metadata` or `verified` incomplete |
| L3 | two cards carry the same identifier |
| L4 | a read grade is not one of the four, a read without its date or, for a work read in parts, without which parts; an ungraded card that is not seeded |
| L5 | `via`, `related` or a body citation names a card that does not exist, a related card that does not name this one back, or an extract the cited card does not carry |
| L6 | a copy without a path and a hash, outside the store or the kept directory, or not matching its recorded hash |
| L7 | a state not among the legal ones, an excluded card without its reason and date, a registered card with an exclusion |
| L8 | a date that is not an ISO date or is in the future, or a card without its created date |
| L9 | a body is not one sentence per line |
| L10 | a body that is not `## Notes` then `## Extracts` with nothing before them |
| L11 | the index is missing or stale — run `library index` |
| L12 | a reference entry of a bound document that no card agrees with, that two cards agree with, or that names an internal document |
| L13 | a work a bound document cites is graded unread and names no `via` |
| L14 | the watch file or the candidates file cannot be read |
| L15 | an extract the kept copy does not bear out: its quotation is not in the kept text, or its locator names a section, page or statement that is not |
| L16 | an extract is malformed — its id, locator, words, caveat, rule or date — or its `checked` date is not a date or is in the future, or an unread card with no `via` carries an extract |
| L17 | a card naming a project file whose file is not in the tree or whose kind is not internal, an internal document recording another copy, or a card of an internal kind naming no file |

## `library citecheck`

`library citecheck [DOC…]` reads each document's text against its own `## References` section, the bound documents where none is given, and prints, as file and line:

- an author-year citation that no entry answers: none whose first author is the cited name, with the cited date, a letter suffix included;
- an entry the text never cites;
- a line under the heading written like an entry and not read as one, which no citation can reach.

Under `--json` each is a problem of code `CITE`; the last line counts the documents, the citations and the entries read.
It ties no entry to a card, which is `library check`'s L12.

## `formal check`

With the `formal` plugin, `formal check` reads `formal.toml` and reports, in words rather than codes:

- a workspace that is not a directory, or the prover session's instructions file missing;
- a package root with neither `<Root>.lean` nor `<Root>/` under its package directory;
- a declaration manifest missing, with the command that regenerates it, or a row outside the grammar `formal --help` prints;
- with `[packages]` bound: the manifests' modules not the tree's (the files on disk under each root, those git ignores left out), the missing and the extra named with the command that regenerates them, and a module counted under a root `[packages]` does not bind;
- a root's umbrella `<Root>.lean` not importing a module under `<Root>/`, or importing one not in the tree (`umbrellas = false` turns this off; a module the package's lakefile declares as a library root of its own stands outside the umbrella);
- a module importing a module of a later package of `[workspace] package_order`.

Its coverage line names the manifests with their row counts by kind, the packages bound and the documents scanned, and says the prover tree itself is not built.

## `formal cite`, `formal anchors`, `formal register`

Three gates over the documents and what ships, each bound in `formal.toml`, each exiting 1 with every site named and 2 when it could not run:

- `formal cite`: no document matching `[documents] scan`; a declaration name a document cites that resolves nowhere, resolves only to private declarations, or is qualified under a namespace of the manifests and names no declaration; a cited `X.lean` that is not a module; an API-docs link to a module not in the tree; a name bound as retired that the manifests still hold.
  Its coverage lines count the resolutions by kind and the allowlisted names by list;
- `formal anchors`: no file matching `[anchors] scan`; a `[Key] §N`, `[Key] Theorem N.M` or `[Key] Appendix X` naming no heading, statement of that kind or appendix of the key's document, or a statement riding a section it is not in; the bare keys and the § lines with no key are counted, not checked;
- `formal register`: a line of a shipped file matching a bound pattern class after the sanctioned expressions are cut, a class reaching no file, or an empty scope.

`formal hypotheses` exits 1 where a public theorem shipped at the base, or listed in a baseline, gained a named condition, and says INERT, exiting 0, where the manifests carry no `hypothesis` row; `formal witnesses` is a report and exits 0.

## `formal handoffcheck`

`formal handoffcheck DRAFT` checks the decidable shape of a prover handoff before it is sent, never its content:

- one `<prompt session=fresh>` or `<prompt session=continue>` block, closed, with nothing after the closing tag, and a `continue` that states its reason;
- none of the phrases `formal.toml` bans;
- a record named as a source — a path under `[handoff] records`, a record id, a file of `meta_names`, a key of `key_patterns` — carries the docstring-register warning;
- paths relative to the workspace, the project's own directories written `../`;
- a `Refute first:` line and a `Commissioned:` line naming the declarations (or `none —` and why);
- a bundle of two or more pieces with a `Bundle shape:` line and a sentence keeping its own words out of the docstrings.

A draft with no prompt block exits 2, since there was nothing to check; the [handoff](../plugins/formal/skills/handoff/SKILL.md) skill says what each line is for.
