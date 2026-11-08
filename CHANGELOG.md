# Changelog

Each release is a tag; the version is read from the tag and the version fields `docs/development.md` names, and each release's section is headed by its tag and date; a change not yet released goes under an `## Unreleased` heading above them, which becomes the tag and the date at the release.

## Unreleased

A marketplace follows the releases: the kit keeps a branch `latest` that each release moves to its tag, and a project's marketplace at `ref` `latest` gets every release from a marketplace update, never the default branch's unreleased work, where it was pinned to a tag it moved by hand.

**Upgrading**, in Claude Code, once: edit the marketplace's `ref` to `latest` in the project's `.claude/settings.json` and in `~/.claude/settings.json` where the user's settings declare it, run `claude plugin marketplace add 'lividgreen/research-kit#latest' --scope project`, then `claude plugin update research@research-kit --scope project` and the same for `formal@research-kit`, and restart; [Install](docs/install.md#following-the-releases) has the steps, and the setup probe names them.

- The release workflow moves the branch `latest` to each release tag by a fast-forward, after the GitHub Release is made; a resend for an older tag leaves it where it is.
- The setup probes (`setup.py probe` and `formal probe`) read a marketplace at `latest` as following the releases, no pin to compare, its step for a plugin behind the latest release `claude plugin marketplace update research-kit`; a marketplace at a tag, the latest one included, or at no ref is off, its steps the `ref` edited to `latest` and the marketplace added at it; a remote hooks' `rev` behind is moved by `prek autoupdate` or `pre-commit autoupdate`.
- [Install](docs/install.md), the READMEs, the setup skills and their pages add the marketplace at `latest` (`#latest`, Codex's `--ref latest`), and "The plugins at the hooks' tag" is "Following the releases".

## v0.6.0 — 2026-11-08

The two consumers' first sessions at v0.5.0, a post-upgrade check and a first `whatsnext` and `freeze`: the freeze no longer holds the log to a renumbering, an entry may name a range of ids, an evidence item is replaced or retired by the CLI, a filter for the findings resting on one form alone, and the checks' summaries read as sentences; and from the first consumer's cut of its layers over the kit, the setup probe stating only the hooks pin it read, the built-in reflow leaving the common abbreviations unsplit, `formal cite --json`, and three review skills, an audit across the documents, scrutiny of one argument and an attribution check against a named result's primary source.
**Upgrading**: no step is required, the records and the bindings being unchanged; a project set up before that will use the review skills runs `/research:research-init` once, which re-checks the setup and forms the `### Reviews` part of its instructions with the person.

The flow:

- `flow state --check` no longer asks the log to name a record whose only change is its rank: one `flow rank T 7 --insert` renumbers every ranked record below it, which the session did not work on, and each failed the check until the entry named it; a record whose file differs from the base commit's in `rank` alone is left out of `flow touched`'s list and `--ids`, printed on one line at the end (`re-ranked only: id, id, …`) and listed under `--json` as `reranked_only`, while a moved record whose summary or body changed too is held as before, as is a question `flow rank --set` names, whose checked date it refreshes, a review the entry names, and a record whose rank did not change (re-saved with only its quoting changed, say) is not so labelled but stays an unnamed change.
- The log's entry may name a range of ids, `finding-0015…0035`, with an en dash or three dots for the ellipsis, written with no spaces around it: it names every id of that prefix and digit width from the first number to the second, where the check read only the ids written out; a range whose second number is smaller than the first, such as `finding-0035…0015`, names only the first id, which is written out.
- `flow evidence F --replace OLD NEW` swaps an evidence item for another, NEW resolved as an added item is, and `flow evidence F --retire OLD --reason R` removes one, so a finding whose file a later change deleted is mended by the CLI rather than by the hand in the front matter; each writes a dated note into the finding's body as `flow note` does, so the record keeps what the evidence was, OLD not among the items is refused naming them, a retire that would leave the finding no evidence is refused, since V6 fails a finding with none, and an item a hand-edited finding holds twice is acted on once, the first occurrence swapped or removed and the other kept.
- `flow find --form` is repeatable, a finding listed when it carries every form given, and `--only` holds its forms to exactly those given, so `flow find --form stated --only` lists the findings resting on `stated` alone, which the `whatsnext` skill's step 3 now asks for where `--form stated` listed every finding carrying the form.
- `flow find --kind` takes only `question` or `conjecture`, as `flow frame --kind` does, with a help line, where any word was taken and listed nothing; the refusal comes from the command and not from the argument parser, so a caller that reads the page under `--json`, the dashboard's filter among them, still gets an answer to parse.
- `flow check`'s coverage line reads an unbound manifest or register as a sentence (`declaration evidence unchecked (no manifest bound)`, `probe evidence unchecked (no register bound)`), and, where the manifest or register is bound and its file is absent, `unchecked (manifest X not found)` or `unchecked (register X not found)`, not `NOT CONFIGURED` in either case; its library line reads `none bound` where no library is bound, and says its count is the keys cited from the records, with the number of records citing, and that the documents the library's scan binds are not read there, so a project whose records cite nothing and whose scan binds citing documents no longer reads as a dead library.

- The built-in reflow no longer splits a sentence after the common scholarly abbreviations (`cf.`, `e.g.`, `i.e.`, `vs.`, `et al.`, `Prop.`, `Thm.`, `Lem.`, `Def.`, `Eq.`, `Fig.`, `Sec.`, `Ch.`, `No.`, `Vol.` and their plurals), so `By Prop. 3.4 and Thm. 2 it holds.` is one line to `flow reflow --check`, while a single capital initial such as `Theorem A.` still ends a sentence; a project whose prose carries others, a journal's `Amer.` and `Math.`, binds its own reflow module, and the library's copy of the splitter changes with it.

The `research` plugin:

- `library check` and `library entries` say "no document bound" in a sentence where `[entries] documents` is empty, in place of "of NO DOCUMENT CONFIGURED", and `library check` says "no store bound", "no path bound" and "no directory is bound" where it printed `NOT CONFIGURED`, `NO PATH CONFIGURED` and `NO DIRECTORY CONFIGURED`.
- The `whatsnext` skill and its page say what the draw does when the top of the ranked list is a question: the agent refines it into the task that is its first move (`flow refine Q --task "…"`) and draws that, or leaves the hand as it is where the question waits on something the hand cannot do.
- The `freeze` skill says that an entry's range of ids is read and that a record only re-ranked need not be named.
- [The flow](docs/research/flow.md) and the flow skill say that a task serves a goal only through the question it came from: one meant to serve a goal is framed from a question that serves it (`flow frame … --serves G`, then `flow refine Q --task "…"`), and a task minted from no question stands alone, its link to a goal prose in its body; a `derived_from` naming a goal is not read as a route.
- [Install](docs/install.md), under "Outside the agent", says a project on the plugin install that wants a Makefile target writes its own runner locating the script under the plugin cache at the pinned version, and that the kit ships none.

- The setup probe states only the hooks pin it read: it reads `.pre-commit-config.yaml` by its lines, a comment naming research-kit no longer counting as the kit's hooks, and tells three forms apart, a hook repo naming the kit, `repo: local` hooks whose entries run the installed plugin's scripts, and neither; for local hooks `pins at one tag` says that no hook pins the kit by `rev` and that the hooks follow the plugins' pins, the init leaves such a file as it is, and the `kit:` line gives the plugin's version and release tag where it called the tag the hooks' pin.
- [Install](docs/install.md) describes that install-run form beside the remote hooks: a plugin-install project wanting one version everywhere writes its hooks as `repo: local`, `language: system`, each entry its own runner followed by the script's command, the marketplace `ref` then the one pin.
- The skills write `agent` and `owner` for the two hands, the names `[hand]` gives them by default, and the skills and [The flow](docs/research/flow.md) say that the names a project's `[hand]` sets are what the commands take.

- Three review skills, each with a page of its own, carry as steps what the `method` skill stated as rules, so a project need not keep a local command for each: [`/research:audit`](docs/research/audit.md), a consistency audit across the documents, the mechanical checks first and then every import read at its exporting statement, a regime condition's constants, a status's label, definitional drift and every negative-coverage sentence against the artifact; [`/research:scrutinize`](docs/research/scrutinize.md), argument-level scrutiny of one target, its claims with their status, its gaps as a missing result or a missing method, its load-bearing steps read hardest, checking and not verification; and [`/research:attribution`](docs/research/attribution.md), every sentence crediting the project with a named external result held to the primary source on four axes, the resource, the quantifiers, the scope and the author's caveats, from `library claims` and `--uncovered` and the shapes they miss, each verdict written on the work's card as an extract.
  Each reports first and edits nothing while it does, then corrects in the same session each sentence it found false, of the artifact or of a source, at its own size and at every summary site, unless the project's instructions file says the person is asked first.
- `/research:research-init` and `/formal:formal-init` re-check on every run everything their setup covers that exists, the bindings, the instructions and the hooks, against the project as it stands, and add what is missing on the person's word, where they wrote what was absent and left what existed as it was; nothing is rewritten without the person's word, what is stale is named with the edit proposed, and the probe's report of a file present no longer stands for what the file holds.
- What a project's reviews hold its documents to — its corpus, which document imports which, its regime conditions with their constants, the definitions compared, its own rules, the documents a reader sees beyond the bound ones — is formed with the person by the setup, `/research:research-init`, and written under `### Reviews` in the instructions file's `## Research records` section, since no script reads it; a project set up before gets that part from a run of the setup, and a review that finds the part missing advises the setup, or asks for its own part in place where a full setup is not needed.
  `method`'s `references/reviews.md` keeps answering and triaging a review and the outsider pass, and `method` names the three skills where it stated the audit's and scrutiny's rules.

The tests:

- The workflow runs the tests on Python 3.12 too, so every release from 3.11, the oldest the scripts accept, to the newest is tried, where 3.12 was skipped.

The `formal` plugin:

- `formal cite --json` prints one JSON document in place of the text: every citation that resolved with its document, line, token, kind and the sorted manifest names it resolved to, the allowlisted tokens by list, the drift and `ok`, exiting as the text mode does, so a tool that needs the cited declarations reads them rather than copying the rule; without `--json` the output is unchanged.
- `formal probe` reads the hooks as the research probe does: with no hook naming the kit's repository it says no hook pins the kit by `rev`, and its `formal-check hook` item is met by a local hook whose entry runs `formal check` under any id, where it matched the word `formal-check` anywhere in the file, a comment included.

## v0.5.0 — 2026-11-06

The consumers' pieces after v0.4.3: a pins check held to the latest release for both plugins, the setup probe naming what an upgrade still asks, a document's anchors the project binds and its headings, a block on several things, a question framed from a document, the records a freeze's log is to name, a window on the due list, and a file class for the register.

**Upgrading**, from v0.4.3 or earlier:

1. Move the pins to the latest release, as [Install](docs/install.md#following-the-releases) says, and restart; `research-init`'s probe now asks GitHub for the latest release, names each pin that is off it with its command, and the releases from the oldest pin whose **Upgrading** paragraphs to read.
2. A block's `on` is a list now: run `flow doctor --fix`, which writes each block's one value as a one-item list, then `flow check`. The `flow-check` hook at the new tag fails every record-touching commit while a block of the old shape stands, so the bump and this edit land in one commit, as in v0.4.1; a project with no block has nothing to fix.
3. With the `formal` plugin: copy the `land` skill's `scripts/DeclManifest.lean` over the workspace's copy (`formal probe` names it stale) and regenerate every manifest; each gains a second line, `# own roots: …`, and its rows are unchanged, and `formal check` fails on a manifest without the line. An explicit `--own` in `[manifest] generate` that lists the project's roots can go: the default takes the same roots, and the check now holds them against `[packages]`.
4. A `statistical:` or `reference:` item naming a Markdown document with an anchor is checked as a `stated` one is now, where it was held to the file's existence alone: an anchor that is no row, numbered statement or heading's anchor fails V6, `flow doctor` names each such item for the hand with the nearest heading's anchor, and the hand rewrites it to the row, the statement, the heading's anchor or the path alone. Nothing else in the records changes; `[evidence] statement_words` and `row_id` default to the words and the id pattern the check read before.
5. An evidence item or a body link naming an absolute path, or one climbing above the project root by `..`, fails `flow check` now (V6, V24), where the check read the machine's file and passed while it was there: rewrite it from the project root (`papers/alpha.md`); `flow check` names each.

The flow:

- A document's anchor in evidence may be a heading, by the anchor GitHub gives it (`stated:docs/adr/0003.md#decision`, `statistical:reports/rates.md#measured-rates-2026-10`, a repeated heading numbered `-1`, `-2`), beside a row and a numbered statement, an ATX or a setext heading, its emphasis, HTML tags and entities read as GitHub renders them; `statistical` and `reference` items naming a Markdown document with an anchor are checked as a `stated` one is, and a refusal names the nearest heading's anchor.
- `[evidence] statement_words` binds the words a numbered statement takes (the nine the check read, unset; "Law", "Confirmation", or a symbol such as `§` taking its number with no space) and `[evidence] row_id` the pattern a table row's id matches (two or three capitals, a hyphen, then letters and digits, unset; `[A-Z][0-9]+` for rounds named `A2`, `M3`); `flow init` writes both commented, and a word with a space or a pattern matching an empty anchor is refused when `flow.toml` is read.
- `flow block ID --on X --on Y --reason R` waits on several things at once, the records among them followed by the index's wait, `flow show`'s back-references and `flow find --refers`; a block's `on` is always a list, one item for one thing, V15 failing one value with `flow doctor --fix` writing it as a list, and the check warns when every one of them has closed or passed; `flow state`'s line for a block's date that has passed names what a block on several still waits on.
- `flow frame --source PATH --summary … --criterion …` frames a question from a document of the tree, an ADR or a report, with no idea captured first; a record's `source` that is a path of the tree is read by `flow artifacts` and `flow find --refers`. A `--source` with a path's shape (no space, no URL, a `/` or an extension) is held to the tree at every mint that takes one, so `arXiv:2301.12345` or `v1.2` is refused for words with a space rather than listed as a missing path.
- A repository path a record names, an evidence item's, a body link's or a source's, is written from the project root: an absolute one or one climbing above the root by `..` is outside the tree, refused by `flow frame --source` and `flow evidence`, failing V6 or V24, a source of that shape read as words, and never listed by `flow artifacts` or matched by `--refers`.
- `flow touched` lists the records changed since the commit of the log's newest committed entry, each with its summary, type and state, the ones `flow state --check` holds today's entry to name: `--unnamed` only those no entry names yet, `--ids` the ids on one line, `--since REV` since another commit, a record then named by an entry from the top down to the newest the log held at REV; the check's failure line names it.
- `flow set G criterion "…"` and `flow set G horizon "…"` on a goal leave what the field read in the body under the date, and `--note "…"` on any `set` appends the words given, the owner's for a goal.
- `[index] due_within = N` narrows `flow state`'s due list to the tasks due within N days and every passed date, with a line counting the later ones; the index keeps the whole list, since it never reads the day, and `flow init` writes the binding commented.
- The records' front matter takes a list under a map's key, the shape a block's `on` writes, which PyYAML reads as the same list.

The `research` plugin:

- The setup probe's `pins at one tag` asks GitHub's API for the kit's latest release (`releases/latest`, 5 s, nothing of the project sent; [What goes online](docs/network.md) names it) and holds every pin to it: the hooks' `rev`, the marketplace's `ref`, the plugin the probe runs from and every plugin of the research-kit marketplace that Claude Code installed for the project, from its install record `~/.claude/plugins/installed_plugins.json` (`CLAUDE_CONFIG_DIR` moving `~/.claude`; the project's own entry, local or project scope, over a user one). It names each pin off the latest release, and a plugin the settings enable and the record lacks, with the commands that move every pin to it; where the record is absent it says so and compares the rest. Where the latest release cannot be read (offline, refused, or `RESEARCH_KIT_OFFLINE=1` set) it says so and why, and compares the pins among themselves against the newest of them.
- The setup probe's new `upgrade` section, in the text and under `--json`, names the steps a move to another release still asks, each with its command: the pins' steps with the releases from the oldest pin up to the latest whose **Upgrading** paragraphs to read (by tag and the changelog's URL); what `flow doctor` of the flow skill beside it finds, as N mechanical edits for `flow doctor --fix` and M things for the hand; a stale index for `flow index`. It runs the two flow commands read-only and still writes nothing.
- [Install](docs/install.md#outside-the-agent) says how a Makefile target or a script runs a skill's script outside the agent: by its path from the project root where the skills are installed into the project (`python3 .agents/skills/flow/scripts/flow.py check` after `npx skills add`, `.claude/skills/…` for Claude Code), since a plugin install's path in the agent's cache changes with each version.
- The migration guide says what a project of measurements brings — a report's heading or a row id the project binds as a finding's evidence, the roadmap as the registry beside the records, how its workstreams are pointed at asked of the person, an ADR's open point framed `--source` it — and gives a worked survey and the mapping message the person approves.
- `/research:freeze` names `flow touched --unnamed` for the ids the log's entry is to name.

The `formal` plugin:

- `formal register` holds a package to the files it names: a `[[register.files]]` class reads every `.lean` file name its `scope` mentions, bare or with a path, and fails where it is no module of the class's `packages` (omitted: each file's own package and those before it in `package_order`) and no `allow` expression, written for another project's files, matches it as written: `^Average\.lean$` allows a bare `Average.lean` and not `ALT/Ergodic/Average.lean`, which needs an expression of its own (`^Mathlib/`).
- A `packages` entry that is no package directory, an empty list or a key the class does not read is refused when `formal.toml` is read. A file class reaching no shipped file, or naming a package with no tracked `.lean` file, fails as rot. A package directory outside the repository, a library required by path, is listed by what its own repository tracks, or by its `.lean` files on disk where it is in none. `formal register` runs with only file classes bound.
- `formal probe` holds the pins to the kit's latest release as the setup probe does (the helpers held byte-identical by the tests): the hooks' `rev`, the marketplace's `ref`, each installed research-kit plugin and the `formal` plugin's own version. Where one is off, the proposal `pins` names the releases from the oldest pin up to the latest and the steps that move every pin to it; where the latest release cannot be read it says so and compares the pins among themselves.
- `DeclManifest.lean` writes the roots whose Prop-valued definitions it read as named conditions, given by `--own` or its default, as the manifest's second line, `# own roots: A,B`; `formal check` fails where a manifest lacks the line, where it names a root `[packages]` does not bind (a library required by path from outside the project, read as the project's own), and where a bound root the package's modules import, directly or through another module, is left out (a package required by git, under `.lake/packages/`, or an explicit `--own` that misses one). `formal init` and the probe no longer write `--own` into the generate commands, the default with the check standing for the list each command repeated.

## v0.4.3 — 2026-11-06

Two consumers' first sessions under v0.4.1's model, read for where a command and its validator disagree, where an instruction misled and where a refusal left the session guessing; nothing in the records changes.

**Upgrading**, from v0.4.1 or v0.4.2: move the three pins, as [Install](docs/install.md#following-the-releases) says, and restart.
Where the project's instructions call `flow …` or `library …` bare, add the line the inits now print: it means the skill's script by its installed path, no command on PATH.
A migration that brought only the recent results in as findings has more to mint: every committed measurement whose evidence resolves is one (the migration guide's third principle, below).

The flow:

- `flow tag ID +T -U…` adds and removes a record's tags after its mint, the others kept in their order; a tag it lacks, one both added and removed, or a change with no sign is refused.
- `flow note ID --body FILE` appends a file's text to a record's body under today's date (`YYYY-MM-DD — note:`), through the record's own write, the reflow and markdownlint with it; a body is edited without its file name guessed.
- The check's V0 on a file named for a record that reads at another path (a guessed name, most often) names that record's path and calls the file a stray, where it said "no frontmatter" alone.
- `flow reflow --as DEST DRAFT` takes a record's id for DEST; a missing DEST named for a record that is elsewhere is refused with the record's path, and one named for a record not minted yet lints the draft as a record's body, under front matter whose `summary:` waives MD041, where it linted the draft alone and reported MD041.
- An empty or blank `--reason` is refused by every command taking one (`park`, `block`, `abort`, `remove`, `wrong`, `reach`, `giveup`, `drop`), where `flow check` flagged the record after the write (V15).
- `flow set T rider true|false`, the words the record stores, as well as `on|off`.
- `make`, `abort` and `return` on a ready task say to draw it first, with the command.
- `flow doctor`'s `kind: decision` line settles once the task is parked, as its own remedy says; it fired on a parked task tagged `decision` all the same.

The three scripts:

- A command that does not exist is answered with the way the usual word for it goes (`flow done` → `make T` or `finding … --answers Q`, `library grade` → `read KEY --grade GRADE`, `formal landing` → `handback`, `readback`) and the nearest names, in place of argparse's list of every command.
- The paragraphs `flow init`, `library init` and `formal init` print for the project's instructions say that `flow …`, `library …` and `formal …` there mean the skill's script run by its installed path, the plugin cache's under Claude Code.

The `research` plugin:

- The README opens with what the kit is for and its *How to use* table, and points at the site for the agents, the reasons and the page list, which it no longer repeats.
- The migration guide's third principle carries the open work and every finding: findings never close, so every committed measurement, evaluation or result whose evidence resolves today is a finding, the oldest as well as the newest, where "carry the live front, not the history" led a migration to fold 14 of about 35 evaluations.

## v0.4.2 — 2026-11-06

A logo: `docs/assets/logo/` holds `logo.svg`, a small-size `favicon.svg`, the 1200×630 `og.png` for link previews and the original `logo.jpg`; the README shows it, and the project's site reads the folder from the tag for its header mark, favicon and link preview.
`tests/run.py` checks the folder: the files' sizes, nothing active in an SVG, the preview's dimensions.

## v0.4.1 — 2026-11-05

The migration to v0.4.0's model, made a procedure for a project of any size: `flow doctor --fix` writes the mechanical part, the upgrade steps say how the bump and the migration go under the hooks, and the doctor's text, the install page's pin order and the flow script's own usage are corrected from two consumers' upgrades.

**Upgrading**, from v0.4.0: move the three pins, as [Install](docs/install.md#following-the-releases) now says in five steps, and restart; nothing in the records changes.
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

1. Move the hooks' `rev`, the marketplace's `ref` and the plugins to this release, as [Install](docs/install.md#following-the-releases) says, and restart the session before the next transition.
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

1. Move the hooks' `rev`, the marketplace's `ref` and the plugins to this release, as [Install](docs/install.md#following-the-releases) says, and restart the session before the next transition.
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

1. Move the hooks' `rev`, the marketplace's `ref` and the plugins to this release; in Claude Code, add the marketplace again at the tag with `--scope project` and run `claude plugin update`, and never remove the marketplace, which uninstalls the plugins for every project on the machine. [Install](docs/install.md#following-the-releases) gives the commands.
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
