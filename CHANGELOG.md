# Changelog

Each release is a tag; the version is read from the tag and the version fields `docs/development.md` names, and each release's section is headed by its tag and date; a change not yet released goes under an `## Unreleased` heading above them, which becomes the tag and the date at the release.

## Unreleased

## v0.4.2 — 2026-11-06

A logo: `docs/assets/logo/` holds `logo.svg`, a small-size `favicon.svg`, the 1200×630 `og.png` for link previews and the original `logo.jpg`; the README shows it, and the project's site reads the folder from the tag for its header mark, favicon and link preview.
`tests/run.py` checks the folder: the files' sizes, nothing active in an SVG, the preview's dimensions.

## v0.4.1 — 2026-11-05

The migration to v0.4.0's model, made a procedure for a project of any size: `flow doctor --fix` writes the mechanical part, the upgrade steps say how the bump and the migration go under the hooks, and the doctor's text, the install page's pin order and the flow script's own usage are corrected from two consumers' upgrades.

**Upgrading**, from v0.4.0: move the three pins, as [Install](docs/install.md#the-plugins-at-the-hooks-tag) now says in five steps, and restart; nothing in the records changes.
From v0.3.0 or earlier: the steps of v0.4.0 below hold, with two corrections — step 2's "edit each file by hand" is `flow doctor --fix` for the mechanical classes, then the by-hand list it prints; and the bump and the migration land in one commit, since `flow-check` at the new tag fails every record-touching commit until the migration is done (or the intermediate commit runs with `SKIP=flow-check`, said so in the log); `flow task`, `flow state` and `flow show` run on the unmigrated tree, so the migration task is minted first.
Rewrite the comments `flow init` wrote beside the `flow.toml` lines the doctor says to delete, which it does not read.

The flow:

- `flow doctor --fix` writes every edit whose line states it, in place: a field the record lacks, `kill`, `abandoned`, the states `abandoned` and `decomposed`, a task's `kind` to a tag, `question` into `derived_from`, a finding's `status` (the tag `refuted` where it was that) and `paper`, an evidence item's form prefix read off its shape, a finding moved out of a shard, a closed task moved into the archive, `answered_by` and `consumed_by` between a list and one value, a question's `direction` by name rewritten to its record's id once the record exists, an owner cleared on a ready or a closed record, and the inbox created; each record's front matter is re-ordered to the schema and the index refreshed. What needs judgment — a task or several findings in `answered_by`, a decision task, the directions file's bullets, a third hand, an owner on a held record, the bindings — stays printed for the hand, and `--fix` exits 1 while any is left.
- `flow doctor` without `--fix` counts the mechanical classes one line each ("645 × a field of this model the record lacks") instead of one line per record per field; `--all` lists each; under `--json` they are `mechanical` with a `class` and `summary`, the judgment lines `problems` as before, and `--fix` reports `fixed`.
- The doctor's text: the third-hand line no longer names `flow out`, a command that does not exist, and says the prover's task stays active in the agent's hand; the line for a task in `answered_by` mints the finding in this model's form (`flow finding SUMMARY FORM:TARGET… --from T`); `paper: null` prints as such; a directions file with no bullets is told to go, not to mint each bullet; a decision task is found by its tag once its kind is one.
- The flow script's module docstring describes this model (it still gave the v0.2.0 usage; nothing printed it).
- Python 3.15 joins the test matrix: the kit's tests pass on 3.11, 3.13, 3.14 and 3.15, and every selftest runs clean with deprecation warnings as errors, so nothing the scripts use is slated for removal.

The `formal` plugin:

- `formal probe` names a workspace's `DeclManifest.lean` stale where it differs from the land skill's copy, with the copy as a proposal: the one upgrade step no check saw.

The pages:

- Install's pin order for Claude Code: edit the `ref` in every settings file that holds the entry first, since `marketplace add` refuses while a user-level entry names another ref, then `add`, then `plugin update` per plugin; the bump and the migration in one commit, or `SKIP=flow-check` said in the log; a session that must mint before its restart runs the new script by its cache path.

## v0.4.0 — 2026-11-05

The flow gains the two ends of its chain, goals above the questions and the artifacts below the findings, a finding's trust read off the forms of its evidence in place of a status, tags in place of task kinds, and a task's due date and post-done instruction; a project's records and `flow.toml` are brought to it by hand, from what `flow doctor` prints.

**Upgrading**:

1. Move the hooks' `rev`, the marketplace's `ref` and the plugins to this release, as [Install](docs/install.md#the-plugins-at-the-hooks-tag) says, and restart the session before the next transition.
2. Run `flow doctor` and edit each file it names by hand, as it says; no transition migrates a record. A task's `kind` goes, its value a tag where it says something; a finding's `status` and `paper` go, each evidence item gains its form as a prefix (`formal:` for a declaration, `statistical:` for a probe, `stated:` for a statement or row of the project's own document), a refuted finding gains the tag `refuted`, and a finding under a shard directory moves to `findings/`; every task gains `due` and `after`, every question `serves`. Then `flow index`; the `flow-check` hook fails until `flow check` is green.
3. Directions are records: for each bullet of the directions file, `flow direction "Name" --body FILE` with the bullet's words in FILE, then write the new id into each question's `direction` in place of the bold name, and delete the file and `[paths] directions`; the doctor lists the bullets.
4. In `flow.toml`, delete the `[task]` and `[finding]` sections, and add `[evidence] forms = ["formal", "statistical", "peer-reviewed", "stated", "reference"]`, keeping the forms the project accepts and adding its own words; say in the project's instructions what each form means for it.
5. Where the project's instructions, scripts or notes call a command that is gone, name its replacement: `flow task … --kind K` is `flow task … --tag K`; `--task SUMMARY KIND` on `refine` and `make` is `--task SUMMARY`, with `--tag T` for the tasks minted; `flow finding SUMMARY STATUS EVIDENCE…` is `flow finding SUMMARY FORM:TARGET…`, `--tag refuted` for a disproof and no `--paper`; `flow find --status S` is `--form F`, `--paper P` is `--refers PATH`; the directions file is `flow directions`.
6. A goal the project has is formed on the owner's word, `flow goal "…" --criterion "…" [--horizon "…"]`, and the questions serving it name it with `flow set Q serves G`.

The flow:

- Two record types, `goal` and `direction`, both the owner's: a goal is formed with what reached means and a horizon in words (`flow goal`, `flow reach G --reason R`, `flow giveup G --reason R`), a question names the goal it serves in `serves` (`frame --serves`, `rank --serves`, `flow set Q serves G|none`), and a goal given up releases its open questions, which keep their ranks; a direction is a record with its name as summary and the owner's words as body (`flow direction NAME --body FILE`, `flow drop D --reason R`), a question's `direction` names it by its id, a dropped direction clears it on the open questions, and `flow directions` renders the open ones in place of the directions file, which is gone with `[paths] directions`. A goal implies its own direction and may be produced along one (`goal --from D`), which stays open. The index gains `Goals`, each with the questions serving it, and `Directions`; V22 holds an open question's direction and goal to open records.
- A finding's `status` is gone, and so are `[finding]`, `paper`, `--paper` and the shards: each evidence item is `form:target`, the form one of the words `[evidence] forms` lists, and the set of forms a finding carries is its trust, shown where the status stood and filtered by `flow find --form F`. The kit ships five forms — `formal`, `statistical`, `peer-reviewed`, `stated`, `reference` — resolved by their shape against the manifest, the probes register or a committed result, the library, a document of the project, or a link; a project adds its own, held to a path's existence or reported unchecked; a form not listed, an item with no form and an item twice fail V6. `flow finding SUMMARY EVIDENCE…` takes no status and gains `--tag`; `flow evidence F ITEM…` adds evidence and never removes it, the way a finding's trust is raised, and `refuted` is a tag.
- A task's `kind` is gone, with `[task] kinds`, `default_kind`, `--kind` and the second word of `--task`: tags carry what a kind said, `research` and `upkeep` the usual ones, written by the agent at the mint (`--tag` on `task`, `refine` and `make`), no vocabulary validated; `flow tags` reports every tag with its records and the untagged (`--type` narrows).
- A task carries a due date (`--due YYYY-MM-DD`, `flow set T due DATE|none`), which never moves a rank: the index lists the open tasks that have one under `Due`, soonest first, `flow state` prints that list before the ranked one and names a date that has passed, as it does a block on a condition whose date has passed, and `flow check` warns on both; and a post-done instruction (`--after "…"`, `flow set T after "…"|none`), which `make` and `abort` print at the close.
- `flow artifacts` lists every repository path the records refer to, by an evidence item or a Markdown link in a body (root-relative; a URL, a bare anchor and a path in backticks are prose), with the records naming each and `MISSING` where it is gone; the check's V24 fails a live record whose body links a path that is not in the tree and warns on a closed one.
- `flow find --refers ID|PATH` lists the records naming a record or a path in any reference field, an evidence item or a body link, and `--deep` the records naming those and so on; `flow show` and the back-references list `direction` and `serves`.
- `flow doctor` names a task's `kind`, a finding's `status` and `paper`, an evidence item with no form and the prefix it takes, a finding under a shard, a question's `direction` holding a bold name, the directions file and its bullets, `[task] kinds` and `default_kind`, the `[finding]` section and a missing `[evidence] forms`; `flow init` writes `goals/` and `directions/`, the five forms, and no directions file.
- The dashboard's record list shows a finding's forms, and gains the Artifacts and Tags pages.

The `research` plugin:

- The flow skill carries the tests for an idea's size (independence, not length), a task (big, or outliving the turn; an operation on a card never one, and one that finds work recommends a task), a task's size (one definition of done), and how a body refers to a repository path.
- `/research:whatsnext` reads the open goals and directions off the index, ranks the questions serving a goal first under it, mints or closes a goal or a direction only on the person's word, re-ranks the questions a given-up goal released, and names a finding resting on `stated` evidence alone as work waiting.
- The setup asks which evidence forms the project accepts and writes them into `[evidence] forms`, and the instructions section says what each means for the project.

The `formal` plugin:

- The handoff mints the prover's task with `--tag research`, and the landing mints each finding with `formal:Path.lean#decl` among its evidence, a failed handoff's refuting finding tagged `refuted`.

## v0.3.0 — 2026-11-05

The flow's model is re-settled in this release: its states, its closings, its hands and the session's start and end; a project's records and `flow.toml` are brought to it by hand, from what `flow doctor` prints.

**Upgrading**:

1. Move the hooks' `rev`, the marketplace's `ref` and the plugins to this release, as [Install](docs/install.md#the-plugins-at-the-hooks-tag) says, and restart the session before the next transition.
2. Run `flow doctor` and edit each file it names by hand, as it says; no transition migrates a record. `abandoned` becomes `closed`, its state `removed`, or `aborted` for a task that was drawn; `decomposed` becomes `open`; `kill` becomes `criterion`; every record gains the fields it lacks; a task's and a finding's `question` field goes, the question named in `derived_from` where it is not; `answered_by` becomes one value and `consumed_by` a list. A question answered by a task gains a finding: mint it with `flow finding … --from TASK`, without `--answers`, which refuses a question that is not open, then write the finding's id into the question's `answered_by`, one value, in place of the list; where no finding is to be had, the question reads as removed, with `closed` holding the date and the reason. A question answered by several findings keeps the one that settles it in `answered_by`, and each other names the question in its `derived_from`. Then `flow index`; the `flow-check` hook fails until `flow check` is green.
3. In `flow.toml`, delete `decision_kinds`, `decision_owners`, `question_optional_kinds` and the `decision` kind, park each open decision task with a reason naming the decision, and fold a prover's hand into the agent's (`agent = 4` is the new default).
4. Move the directions file's `## Inbox` items to `INBOX.md` at the root (`[paths] inbox` names another) and delete the section.
5. Where the project's instructions, scripts or notes call a command that is gone, name its replacement: `flow kill ID` is `flow remove ID --reason R` for an idea, an open question or a ready task, and `flow abort T --reason R` for an active task; `flow answer Q --by F` is `flow finding … --answers Q`, the finding minted with it; `flow make T --finding …` and `flow abort T --finding …` are the make or the abort, then `flow finding … --from T`; `--kill` is `--criterion`, on `frame`, and on `--subq` and `--question` as their second word; `flow task --question Q` and `flow find --question Q` are `--from Q`; `flow state --check --owner O` is `flow state --check`, and the freeze around it is `/research:freeze`; the flow's `references/closing.md` is `/research:freeze` and its `references/next-list.md` is `/research:whatsnext`.
6. The paragraph `flow init` prints for the instructions file now names the inbox and the two skills; bring the project's own paragraph to it in the project's words.
7. With the `formal` plugin, copy the `land` skill's `scripts/DeclManifest.lean` over the workspace's copy (its usage line changed), and remove a prover owner from `[hand]`.

The flow:

- A question closes answered, wrong, impossible or removed, each by its own verb: `flow finding … --answers Q`, `flow wrong Q --reason R`, `flow impossible Q --by F` and `flow remove ID --reason R`; a task closes made (state `done`), aborted or removed; an idea is consumed or removed. The dated reason is in one map, `closed`, and `flow kill` and the states `abandoned` and `decomposed` are gone; that a question was refined is read from its tasks.
- `flow finding SUMMARY STATUS EVIDENCE… [--from ID]… [--answers Q]` is the one mint of a finding, whatever produced it; `make` and `abort` mint none, and `flow answer` is gone. One finding answers a question, and a later one names it with `--from Q`; a task id in `answered_by` fails V18.
- A question's kill criteria are its `criterion`, read as what would answer it or show it wrong or impossible: the field, `flow frame --criterion`, `--subq SUMMARY CRITERION`, `--question SUMMARY CRITERION` and `flow set Q criterion`.
- An open question or a ready task may be parked, by decision, and blocked, on a task, a question or a condition in words (`flow block ID --on X --reason R`, `flow unblock ID`), both at once; it keeps its rank, the index marks the wait, and `draw` refuses it until it is unparked and unblocked. A drawn task that must wait is returned first.
- An idea is drawn into a hand like a task, works into cards that name it (`flow capture --from`, `flow task --from`, `flow finding --from`), and is consumed with `flow consume IDEA` into every card it was folded into, which `consumed_by` lists; one put back partly worked is returned with a note listing what it produced so far.
- Two hands, the agent's and the person's: `flow init` writes `agent = 4`; a task handed to a prover session stays active in the agent's hand; the `decision` kind, `decision_kinds`, `decision_owners` and the index's Owner-only section are gone, and a task waiting on a decision is parked with a reason naming it.
- Tasks no longer belong to questions: a task's `question` field, `flow task --question`, `[task] question_optional_kinds` and the check's V4 are gone, any task may stand alone, and a task names the question, idea or task it came from in `derived_from` (`flow task --from ID`, `flow find --from ID`); a question's closing is refused while a task that came from it is open.
- A question's `answered_by` is one value, the finding that settles it; a finding has no `question` field and names what it came from in `derived_from`.
- The inbox is `INBOX.md` at the root, written by `flow init`; `flow state` prints it, the ranked list, the hands and the log's top entry.
- `flow state --check` is the freeze's check: `--owner`, its owner rule and its inbox rule are gone, and it prints the hands' active tasks; its help names both exit codes.
- `flow doctor` names every record and binding written in an older model's words, with what each reads now.
- The index lists wrong and impossible questions under "Settled, do not re-open", the parked and blocked questions together, and a removed record in no list and no count; `flow find` leaves a removed record out unless asked by `--state removed` or `--id`, and gains `--blocked` and `--held`.
- A rank a closing moves is printed `re-ranked ID N → M`, not as a change; a rank refused as held names `rank --set`.
- `flow log add` takes a State label with a parenthesis of the project's, `**State (…).**`.
- `flow reflow --check` runs where no `flow.toml` stands, with the built-in reflow.
- A failed `flow check` or `library check` names the command that reproduces it where no skill is loaded.

The `research` plugin:

- `/research:whatsnext` reads the inbox and proposes what to make of each item, ranks under the focus the person gives, draws the top work into the agent's hand and returns what no longer fits; it replaces the flow's `references/next-list.md`.
- `/research:freeze` saves what only the conversation holds, runs `flow state --check` and the gates, commits and reports item by item; it replaces the flow's `references/closing.md`.
- The flow skill says that a declaration resolves when it exists in the manifest, a private one included, and that citability is the `formal` gates' claim.
- The library skill says that `library keep` with neither `--from` nor `--redistributable` refuses only where a kept directory is bound, and that `resolve --at NAME` asks that interface alone, any of the four; the flow skill calls `--grep` a regular expression and names the library's command once.
- The setup skill says that the machine's items carry a need word and the project's what was found.

The `formal` plugin:

- `formal` takes `--root DIR` after its subcommand as well as before it, as `flow` and `library` do.
- `formal handoffcheck` leaves an absolute path, and a path under a directory the project does not name, alone; it no longer fails a draft naming a file under the plugin's own install for a segment that equals the workspace's name or a root directory.
- `formal init` takes the workspace's own instructions file, the manifests `flow.toml` binds (with the generate commands writing them), and the handoff's records, id prefixes, log name and citation-key pattern from `flow.toml` and `library.toml` where those exist.
- The manifest generator's usage line names a neutral `<manifest>.txt`, so a project whose register forbids paths into its private tree no longer fails `formal register` on the kit's copy.
- `formal handback` prints the live guard total after the change beside the delta, and counts the guards of a deleted file in the delta.
- The handoff skill says the turn's order plainly: the records, the gates and the commit first, then the draft, its check and the dispatch, and nothing after.
- The handoff keeps the prover's task active in the agent's hand, one handoff in flight at a time, and the landing closes it with `flow make` before minting each finding with `flow finding … --from T`; the prover owner in `[hand]` is gone.
- The land skill names the four classes `formal handback` sorts a commission into: landed, private, already at base and absent.
- The setup's report says the `formal:prover` agent type appears after a restart, and the handoff's fallback subagent is given the project root's absolute path.
- The setup skill says the generate commands pass `--own` only where the workspace has several packages.

The documentation:

- [What is next](docs/research/whatsnext.md) and [The freeze](docs/research/freeze.md) are the two new skills' pages, listed by the README, the site's home and the documentation's index; Scope's table gains the inbox and says where a decision to take lives.
- The README and the citation's abstract say a question carries a criterion; the dashboard colours the new states and no longer the old ones.
- The marketplaces and the `research` plugin's manifests name a session's start and its freeze among what the plugin holds.

- One page per tool: `docs/research/` holds the flow, the library, the dashboard, the working rules and the setup, `docs/formal/` the setup, the handoff and the landing, each page with the tool's commands, the files it keeps, its bindings file as `init` writes it, every code its check reports and its words, so the pages that mixed the tools' bindings, checks and glossary are gone; `docs/README.md` lists the pages, which is the site's navigation, and the tests read `docs/` whole.
- `docs/research/flow-cards.md` and `docs/research/library-cards.md` specify the records and the cards: the files and their names, the front matter's form, every field and who writes it, the states, the grades and the transitions between them; the tests hold the field lists to the scripts' schemas.
- Install says what the upgrade commands print and that the session is restarted before the next transition, that the `formal:prover` agent type is loaded at the next start, and how a session opened in a subdirectory, where the plugins are disabled, runs the checks that gate its commits.
- Scope gains a table of where each kind of fact lives: a record, the log, the registry, a decision record, a direction, the agent's memory.
- The pages read alike: a tool's page opens with what the tool is and what the page holds, then what it does, its commands, its files, its bindings, its check and its words; Install's pin table names `<tag>` rather than a release, its Claude Code pin is four numbered steps, and the sessions that share one tree have a section of their own; the plugin READMEs and Getting started point at the tool pages instead of repeating them.

## v0.2.1 — 2026-10-27

- `docs/project-card.md`, the project's card on [www.livid.work](https://livid.work/projects/research-kit/), which the website copies at each release, held to the card's rules by the tests.

## v0.2.0 — 2026-10-27

**Upgrading**:

1. Move the hooks' `rev`, the marketplace's `ref` and the plugins to this release; in Claude Code, add the marketplace again at the tag with `--scope project` and run `claude plugin update`, and never remove the marketplace, which uninstalls the plugins for every project on the machine. [Install](docs/install.md#the-plugins-at-the-hooks-tag) gives the commands.
2. Copy the `land` skill's `scripts/DeclManifest.lean` over the workspace's copy: its `--own` now defaults to every root of the workspace's own packages, so the regenerated manifests can gain `hypothesis` rows for conditions defined in another package. Regenerate and commit the manifests before running `formal hypotheses` against an older revision.
3. With `[packages]` bound, `formal check` now reads the tree, and the `formal-check` hook fails on a stale manifest, an umbrella that leaves a module out, a module under a root `[packages]` does not bind, an untracked file under a root that git does not ignore, and an import against `[workspace] package_order`; regenerate or fix, or set `umbrellas = false` where an umbrella leaves modules out on purpose.
4. For the new gates, add `[anchors]`, `[register]` and the `[documents]` allowlists to `formal.toml` by hand, as [The formal setup](docs/formal/formal-init.md) shows them (`formal init` leaves an existing file alone), then the `formal-cite`, `formal-anchors` and `formal-register` hooks.

`[handoff] records` still reads a string, and the log's archive defaults to a directory beside the log.

The `formal` plugin:

- `formal cite` checks that every declaration name the documents cite resolves in the manifests, and that none is private only, retired yet present, or an API-docs link to a module not in the tree ([The landing](docs/formal/land.md#formal-cite-formal-anchors-formal-register) has the resolution order).
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
