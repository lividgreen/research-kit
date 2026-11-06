---
name: flow
description: The typed flow of research work — ideas, tasks, questions with a criterion, findings whose evidence a machine resolves, the goals the owner forms and the directions they set, one Markdown record each, transitions through the `flow` CLI, a validator, a generated index with a ranked next list, and a cold-start bundle. Use when reading a project's records to pick up work, when capturing an idea, minting, drawing or closing a task, framing a question or closing it answered, wrong, impossible or removed, minting a finding or adding evidence to one, forming, reaching or giving up a goal, opening or dropping a direction, parking or blocking a record, ranking the next list, or restructuring the records. The project's own instructions bind the directory, the prefixes and the gates through `flow.toml`; this skill names none of them.
license: Apache-2.0
compatibility: Python 3.11 or later, standard library only. Optional - markdownlint on PATH (a write that adds a violation is reverted), git (the log's part of the freeze check), a project reflow module (one sentence per line; built in otherwise); a declaration manifest, a probes register and a reference library for the findings' evidence, without which formal, probe and peer-reviewed evidence is reported unchecked.
metadata:
  version: "0.4.3"
  script: scripts/flow.py
---

# The flow

Work is records: one Markdown file each, front matter plus a prose body, stitched together by transitions that consume and produce records.
The records hold data only; rules live in the project's instructions, the skills and the hooks the project runs.
`scripts/flow.py` beside this file is the CLI, the validator, the index generator and the selftest; `flow …` below is that script run by its path from the project root (`python3 ${CLAUDE_PLUGIN_ROOT}/skills/flow/scripts/flow.py …` under Claude Code), never a `flow` found on PATH, which may be another version.
`flow.toml` at the project root binds the paths and the vocabulary.

## Ideas and tasks

| Kind | What it is | States |
| --- | --- | --- |
| idea | a thought worth keeping that is not yet a question: no criterion of what would answer it, no route; one thing, not a basket of several | open, consumed, removed |
| task | a unit of work one owner can finish within its size: a design round, a prose sweep, upkeep, a community item | ready, active, done, aborted, removed |

Distinguishing tests: can one owner finish it within its size? then it is a task, not an idea.
Is it a thing you want to know rather than a thing to do? then it is a question, the kind below.
A task closes one of three ways: made (state `done`), aborted when started and failed, or removed with a reason while ready, never started or returned.
A closed task moves to the archive at its closing transition, so the record directories show the live front of work.

An idea is worked, not only framed: drawn into a hand like a task, it produces what it holds, ideas, questions, tasks and findings, each naming it in `derived_from`, until everything in it is folded into them and it is consumed into all of them, or it is removed; an idea put back partly worked is returned, its note listing what it produced so far.
A thought that holds several things produces one idea per thing while it is worked; there is no split command.
An idea's size is its independence, not its length: two thoughts that can be framed, worked or dropped apart are two ideas, and a long body that gives one thought its context stays one idea.

A task is work that is big, or that must outlive the turn: a later session or the other hand needs to know it is underway or done, or its result has to be linked; either test is enough, applied with judgment rather than a limit.
Work that passes neither is done in the turn and named in the log entry, and an operation on a card is never a task.
An operation that finds a big piece of work recommends a task and does not do it: `task --from` mints it with a summary and a definition of done saying what was being attempted; an idea is sorted into cards and never waits on one (returned with what is left, consumed when nothing is), while a question is what waits on its tasks.
Independent pieces of work are not bundled into one task, and a task whose done cannot be stated in one definition of done is split; `size` is an estimate for ordering.
A task may carry a due date (`--due YYYY-MM-DD`, `flow set T due DATE|none`), which never moves a rank: the index lists the open tasks that have one under `Due`, soonest first, `flow state` prints that list first, within `[index] due_within` days where `flow.toml` binds it (the index keeps the whole list, since it never reads the day), and names a date that has passed, and `flow check` warns on one, never fails; a not-before date is no field but a block on a condition in words carrying the date (`flow block T --on "2026-12-01" --reason "…"`), which `flow state` names once it has passed.
A task may carry a post-done instruction (`--after "…"`, `flow set T after "…"|none`), free text written at the open and printed by `make` and `abort` at the close for the agent to follow; a repeat is the agent minting the follow-up with `make --task`, no interval in the script.
Tags are free words and no vocabulary is validated: `research` and `upkeep` are the usual ones, written at the mint (`--tag`) and changed after it with `flow tag ID +T -U`, a project's own words beside them; `flow tags` reports every tag in use with the records carrying it and the records carrying none, and a project's rule that rode on a kind rides on a tag, unchecked.

## Hands

A hand is an owner's, and holds the active tasks and the ideas drawn into it, within the limit `[hand]` sets.
There are two hands: the agent's, which spans its sessions and holds what its subagents do, and the person's.
A task handed to another session, a prover's, stays active in the agent's hand; the handoff's log entry says where it went.
A drawn task that must wait is returned first, with a note, and then parked or blocked; the hand holds only what is being worked.

## Transitions

| Transition | Consumes and produces | Command |
| --- | --- | --- |
| capture | external → idea | `flow capture "…" --source S`; `--from ID` for an idea worked out of another record, `--tag T`, `--body FILE` |
| task | external → task | `flow task "…" --tag upkeep`; `--from ID` for what it came from, a question, an idea or a task (a question named there is open), `--size`, `--dod`, `--due YYYY-MM-DD`, `--after "…"`, `--source`, `--tag`, `--body FILE` |
| draw | ready task → active, or open idea → in the hand, under the owner's hand limit; refused while the task is parked or blocked | `flow draw task-0001 --owner agent` |
| return | active task → ready, or an idea out of the hand | `flow return task-0001 --note "…"` |
| make | active task → done and archived; follow-up tasks, questions and ideas; the task's `after` printed | `flow make task-0001 --resolution FILE --task "…" --idea "…"`; `--question SUMMARY CRITERION` mints a question, `--tag T` tags the tasks minted |
| abort | active task → aborted and archived, with its dated reason | `flow abort task-0001 --reason "…"`; `--resolution FILE` |
| consume | open idea → consumed into every card that names it in `derived_from`, one or many of any kind, listed in `consumed_by` | `flow consume idea-0001` |
| remove | open idea, open question or ready task → removed with a dated reason; an active task is aborted instead | `flow remove idea-0001 --reason "…"` |
| park, unpark | an open question or a ready task gains or loses a parking block: the date, the reason, and revival triggers where known (`--revival` is optional); the rank stays | `flow park task-0001 --reason "…" --revival "…"`; `flow unpark task-0001 --note "…"` |
| block, unblock | an open question or a ready task gains or loses a block: the date, what it waits on (a task, a question, or a condition in words; `--on` repeated for several, kept as a list, each record among them followed by the index) and the reason; the rank stays | `flow block task-0001 --on question-0002 --on "the 2026-12 release" --reason "…"`; `flow unblock task-0001 --note "…"` |
| rank | the ranked next list: one record's rank, the whole order at once, or a rank cleared | `flow rank task-0001 1 --why "…" --first-move "…"`; `--direction D` and `--serves G` on a question; `--insert` to take a held rank and move the rest down; `flow rank --set ID…`; `flow rank task-0001 --clear` |
| set | one hand-editable field: summary, size, dod, due, after, rider on or off (true or false); `--note "…"` appends why to the body under the date | `flow set task-0001 size small`, `flow set task-0001 due 2026-12-01` |
| tag | a record's tags after its mint: `+T` adds one, `-T` removes one, the rest kept | `flow tag task-0001 +upkeep -research` |
| note | a file's text appended to a record's body under today's date, through the record's write; no field changes | `flow note task-0001 --body FILE` |

A record may be parked and blocked at once: parked is by decision, a thing not worked on on purpose; blocked is by an obstacle, a thing waited on.
A task waiting on the person's decision is parked with a reason naming the decision, and the person's answer is the unpark note and a log entry; a decision is no card and no kind.
`requires` keeps its meaning beside a block: the findings that must exist before a ready task is drawn.

Views: `flow find --type task --state ready` (also `--kind`, a question's, `--form`, a finding's evidence form, `--tag`, `--owner`, `--from ID`, `--refers ID|PATH`, the records naming a record or a repository path in any reference field, an evidence item, a `source` that is a path of the tree or a body link, with `--deep` the records naming those and so on, `--requires ID`, `--depends-on ID`, `--parked`, `--blocked`, `--held`, `--ranked`, `--id ID`, and `--grep PATTERN`, a case-insensitive regular expression over the whole record; a removed record is left out unless asked for by `--state removed` or `--id`), `flow show ID` (the record, its links and its back-references), `flow graph --from ID` (`--dot` for Graphviz), `flow state` (the cold-start bundle; `--from N` continues it, `--budget N` bounds it; `--check` is the freeze's check, below), `flow directions` (the open directions as the owner's list), `flow tags` (every tag with its records, then the untagged; `--type` narrows), `flow artifacts` (every repository path the records refer to, by evidence, body link or a `source` that is a path, with the records naming each and whether it is in the tree), `flow touched` (below), `flow index` (`--print` to stdout, `--check` for drift), `flow check`, `flow doctor` (below).
`flow --help` lists every command, `flow <command> --help` its flags, and neither needs a bindings file.
The global flags are `--json` (any command emits one JSON object), `--root DIR` (the project, found upward from the working directory otherwise) and `--today DATE`; `flow pages` prints the page manifest the `dashboard` skill renders.
A `--body FILE` or `--resolution FILE` takes a file, never inline text, so a long body is drafted first and checked by the project's text gates — its own checks on prose, such as a linter or a line rule.
Make and abort append the resolution to the task's body under its date, as refine appends its `--body` to the question's and says so, so the archived task keeps what was asked and its notes.
A transition that closes a ranked record closes the ranks up, and prints each record so moved as `re-ranked ID N → M`, never as changed.
A ready or active task's `rider` field marks it as riding the next piece of work handed to another session; the index lists such tasks under "Rider for the next hand-over".

A design round is a task tagged `design`: drawn before the round, closed by make or abort with the round record as its resolution and its discarded options one line each inside that record.
Make and abort are where follow-up work is minted: a residue sharp enough to name becomes a task or a question of its own rather than prose in the resolution or a line appended to a question's body.

## Invariants the validator enforces

- Every id is unique and matches its filename prefix; every referenced id exists and has the type the field demands; no cycles in `derived_from`.
- State, a question's kind, size and owner are legal values from `flow.toml`, and every field is the model's: a word of an older model fails, and `flow doctor` says what it reads now.
- Every repository path a live record's body links is in the tree; one a closed record links is warned of.
- What a hand holds stays within its limit; a closed task lives in the archive and an open one does not; a removed, aborted or wrong record carries its dated reason in `closed`, and no other record carries one.
- Parked and blocked sit on an open question or a ready task, each with its date and reason, a block with what it waits on; a block on a record that has closed is warned of.
- Ranks are unique and contiguous, never on a closed record, and a ranked record says why now and what the first move is ("none yet" is allowed).
- Every body is one sentence per line; the committed index equals a fresh render.
- Every library key a record cites is a card the library holds, where a library is bound.

`flow check` prints a coverage line saying which resolvers were configured, so a green says what it did not look at; on a failure it names the command that reproduces it, for a session where no skill is loaded.
`flow.py --selftest` plants one defect per code the check reports, fails when one is planted nowhere, and must stay green.

## Reading discipline

Start with `flow state`: the inbox, the due tasks, the ranked next list, the hands, the dates that have passed and the log's top entry, every line carrying its file and line.
The log is dated entries, newest first, each a level-2 heading `## YYYY-MM-DD — headline` opening with a State paragraph; `flow state` prints the whole top entry, and its State paragraph is the one a cold session trusts.
Then the generated index, which lists the ranked list with each record's waits, each owner's hand, the open goals with the questions serving each, the open directions, the ready work, the open, parked and blocked questions, and the settled ones.
Locate records with `flow find` or `flow show ID`; open record files only by ID.
Never glob the record directories, and never read a record directory whole.
A session's start is the `whatsnext` skill: it reads the inbox, proposes what to make of each item, ranks under the focus the person gives, and draws.

## Writing discipline

Transitions go through `flow`.
Never edit `id`, `type`, `state`, `derived_from`, `consumed_by`, `owner`, `drawn`, `direction`, `serves`, `rank`, `parked`, `blocked`, `closed`, `origin` or `created` by hand.
The one record written by hand is one imported from before the flow: its whole file, with `origin: legacy`, which exempts it from the criterion rule until its first round; no transition writes that value.
Edit a body freely, by hand or with `flow note ID --body FILE`, which appends the file's text under today's date and needs no file name, and a `summary`, `size`, `dod`, `due`, `after` or `rider`, a question's `criterion` or `serves`, a goal's `criterion` or `horizon`, or a finding's `depends_on` with `flow set`, which refuses a field the record's type does not carry and a value the field does not take; a body is one sentence per line, and a write that adds a markdownlint violation is reverted where markdownlint is on PATH (with the project's configuration where `flow.toml` binds one or the root keeps one, else a built-in one under which a record's `summary:` is its title).
A body refers to a repository path, a document, a probe, a dataset, by a Markdown link whose target is the path from the project root (`[the theorem](<papers/alpha.md#Theorem 2.1>)`, the angle brackets where the target holds a space); a URL, a bare `#anchor` and a path in backticks are prose, so the check never fails on a guess.
The front matter is the subset of YAML the script writes: plain scalars, single-quoted strings (a quote doubled inside), double-quoted strings with escapes, `null`, `true`/`false`, integers, block lists (`- item`) and one-level maps; a hand edit stays inside that subset, and `flow check` reads every record back.
A record points at where its subject is STATED and never restates it, because the statement moves and a copy does not.
A design record is never authority: a record points at a round for its reasoning or its history, never cites it for a rule, a criterion or a method, since the criteria a round fixed bound that round alone.
Run `flow check` before committing; the project's hook runs it as well.

## An older model's records

`flow doctor` names every record and binding written in the words of a model before this one, each with what it reads now, and exits 1 where it finds one: `abandoned` (now `closed`, the state `removed`, or `aborted` for a task that was drawn), `decomposed` (now `open`), `kill` (now `criterion`), a task in a question's `answered_by` (a finding settles a question: mint it with `flow finding … --from T`), `answered_by` as a list (one value now), several findings there (one answers, the others name the question in `derived_from`), `consumed_by` as one id (a list now), a task's or a finding's `question` field (gone: a task names the question it came from in `derived_from`), a task's `kind` (a tag now), a finding's `status` (gone: the forms of its evidence stand for it; a refuted one gains the tag `refuted`) and `paper` (gone: the document is a reference `flow find --refers PATH` groups by), an evidence item with no form (the prefix read off its shape: `formal:` for a declaration, `statistical:` for a probe, `stated:` for a statement or row), a `statistical` or `reference` item whose document anchor is no row, numbered statement or heading's anchor (checked as a `stated` item's is since v0.5.0, held to the file's existence before: the hand rewrites it, the line naming the nearest heading), a finding under a shard directory (one `findings/` directory now), a question's `direction` holding a bold name (the id of a direction record now), the directions file and `[paths] directions` (directions are records: `flow direction NAME --body FILE` for each bullet), `[task] kinds` and `default_kind`, the `[finding]` section, a missing `[evidence] forms`, `question_optional_kinds`, an owner `[hand]` does not list, the `decision` kind or tag on a task not parked, and the `decision_kinds` and `decision_owners` bindings, a third hand, the directions file's `## Inbox` section, a missing inbox, and the fields a record lacks.
The lines come in two classes.
The mechanical ones state the exact edit — a field the record lacks, a word renamed, a state read into this model's, a kind made a tag, `question` folded into `derived_from`, `status` and `paper` deleted, an evidence item prefixed by its shape, a finding moved out of a shard, a closed task moved into the archive, `answered_by` and `consumed_by` between a list and one value, a direction's name rewritten to its record's id once that record exists, an owner cleared on a ready or a closed record — and `flow doctor` counts them per class (`--all` lists each), while `flow doctor --fix` writes them in place, re-ordering each record's front matter to the schema and refreshing the index.
The judgment ones — a task or several findings in a question's `answered_by`, a decision task, the directions file's bullets, a third hand, an owner on a held record, the bindings — are printed one per record for the hand, by `--fix` as well, and settled from their lines; `--fix` exits 1 while any is left, and no migration logic exists for them.
A question a task answered keeps one hand-write: once its finding is minted (`flow finding … --from T`), its id is written into `answered_by`, the migration's one exception to the rule above.
The order of an upgrade: move the pins and restart, mint the migration task (`flow task`, `flow state` and `flow show` run on an unmigrated tree, the mint refreshing the index in the new form; a session that must mint before its restart runs the new version's script by its cache path), `flow doctor --fix`, the by-hand list, `flow index`, `flow check`; the migration lands in the commit that moves the pins, since `flow-check` at the new tag fails every record-touching commit until it is done — or the intermediate commit runs with `SKIP=flow-check` and the log entry says so.

## The log, the freeze and the project's other prose

`flow log add FILE` writes the entry FILE holds at the top of the log, under its title: reflowed to one sentence per line, a bold label of at most four words ending in a period, such as `**State.**` or `**Theorem 2.1.**`, a parenthetical allowed after its words as in `**Proposition 5.3 (Jen 1990).**`, kept with its sentence, and reverted where markdownlint reports a violation the log did not have, as a record's write is.
It refuses an entry that does not open with its `## YYYY-MM-DD — headline` and its State paragraph, labelled `**State.**` or `**State (…).**` with a parenthesis of the project's, one dated after today or before the top entry, and a file holding two entries.
`flow log archive --before DATE` moves every entry dated before DATE, verbatim and newest first, into one file per month (`2026-09.md`) in the log's archive directory, merging into a month's file that exists and keeping the link definitions closing it, and leaves one line under the log's title (under its front matter where it has no title) pointing there; the top entry always stays, and an entry whose heading carries no date is refused, since the archive files an entry by its date.
The log's entries are its level-2 headings outside its front matter and its code fences, a fence closing only on a run of its own character at least as long as the one that opened it.
A link definition closing the log goes to every file whose text uses its label: it moves to the archive files where only archived entries use it, is copied where the log uses it too, and stays in the log where nothing does.
The log and its archive files are written together or not at all, and a markdownlint violation either would gain undoes both.

`flow state --check`, at the freeze, decides what a machine can see of it and prints one line per failure:

- the log's top entry is not dated today while the tree has changed since the commit of the newest committed entry — any commit since, on a shared repository another's as well;
- a record changed since that commit, and no entry from the top down to that one names its id.

It prints each hand's active tasks and drawn ideas for the State paragraph, and fails on none: each hand continues its own work.
An inbox holding items fails nothing, since the next session reads it.
Both parts need git and a committed log; where either is missing, the check says which part it did not decide.
`flow touched` lists the records the second part reads, those changed since the commit of the newest committed entry, each with its summary, type and state, so today's entry names them without the ids gathered by hand: `--unnamed` only those no entry names yet, `--ids` the ids alone on one line, `--since REV` since another commit, a record then named by an entry from the top down to the newest the log held at REV.
It exits 1 when a part fails, else 2 when a part could not be decided, so a freeze it could not see whole is never read as clean, else 0.
What it cannot see stays the session's: what the conversation holds that no record does, and whether every site a change reaches says the same; the `freeze` skill is the whole of it.

`flow reflow --check PATH…` holds the project's other prose to the reflow the records get: it prints each line, as file and line, that the reflow would change, skipping a front matter block, reads the Markdown files under a directory, and exits 1 on any, or 2 on a path that is not there; it runs where no `flow.toml` stands, with the built-in reflow.
A line the reflow does not split is left as written, so a hard break's two trailing spaces are not a change, and a line it splits keeps them on its last part; a code fence is read as the log's are.
`flow reflow --as DEST DRAFT` checks a draft before it is placed: its lines the reflow would change, and the markdownlint violations it adds when appended to DEST (DEST a file or a record's id; a missing file named for an existing record is refused with that record's path, one named for a record not minted yet stands for a record's body under its front matter, and any other missing file for the draft alone), under the configuration a record's write runs with, each at the draft's own line, and never one DEST had already; it writes nothing.

## The next list

The ranked records are the schedule of the WORK, and the only one; the registry below orders the deliverables, not the work.
A session works from the top.
The list is filled or refreshed by the `whatsnext` skill, when the person asks or when it is empty, on no cadence, with no per-landing re-triage.
Nothing is ranked down or left off for lacking a route: a record with no known route is ranked with a first move of "none yet", and finding the route is its first round's job.
A parked or blocked record keeps its rank, and the list marks what it waits for, so the order survives the wait.
Goals and directions bias the choice of the next moves and never order the list; a goal given up releases its questions, which keep their ranks for `whatsnext` to re-rank.
A done item clears its own rank through its transition, and the ranks below it close up, so the list stays 1..n without a hand on it.

## Questions and findings

The two kinds above hold the work; these two hold what is KNOWN and what is WANTED.

### The two kinds

| Kind | What it is | States |
| --- | --- | --- |
| question | what we think we have to answer to move the research, with a criterion: what would answer it, or show it wrong or impossible | open, answered, wrong, impossible, removed |
| finding | a CHECKABLE claim: each item of its evidence names its form and its target, `formal:Lib/Foo.lean#decl`, and the forms it carries are its trust | none; it accumulates and never closes |

Distinguishing tests: can you say what would count as an answer? then it is a question, not an idea.
Can its evidence be named in a form the project accepts and resolved by a machine where the form allows? then it is a finding; otherwise it is a claim inside a task's resolution until it earns evidence.
Every task done and nobody can state the answer? then the question goes back to refine.
A conjecture is a question of kind `conjecture` (`flow frame … --kind conjecture`), never a finding; a dead end is an aborted task's resolution, never a finding.
A finding needs no goal above it, nor a question: the cards stand on their own where none is set.

A question is minted in the expectation of a finding, a part of the research and not of the conversation, and closes one of four ways:

- answered, by the one finding that settles it, minted `--answers Q`; the tasks that came from it stay linked to it through their `derived_from`, and other findings the answering produced name it in `derived_from`;
- wrong, when it is shown to be stated incorrectly, with a reason and no finding; a re-stated question names the wrong one as its origin;
- impossible, when it is shown that it cannot be answered, a paradox for one, by a finding with its evidence like any other; with no such evidence the question is not impossible but removed;
- removed, dropped with a reason, its card kept but in none of the index's lists and out of `flow find` unless asked, the findings minted under it before staying.

Tasks do not belong to a question: one made while answering it names it in `derived_from`, and a task may come from nothing.
Each closing is refused while a task that came from the question is ready or active; before removing those tasks, weigh whether one should be made first.
That a question was refined is read from the tasks that came from it, not from a state: an open question whose tasks are all closed is listed as needing refine or answer.
Parking or blocking a question, propose what becomes of its tasks: those of a parked question are usually parked with it, while a blocked question may have tasks that go on.

A question asks one thing, and its criterion says what answers it.
An open end a round finds beyond that criterion is framed as a question of its own, from the finding that exposed it (`flow frame finding-0001 …`) or from an idea captured first, and is never appended to the first question's body as what stays open: a question that gathers its residues has no answer anyone can reach, and the next list can no longer rank it by how near it is to done.
A question whose parts each carry weight alone is split: at framing, into one question per part; at answering, the part answered closes the question, and each part still open is framed on its own with a pointer to where it is stated.

### Evidence and trust

An evidence item is `form:target`: the form one of the words `[evidence] forms` lists, the target what the form takes, each resolved by the validator and by `flow finding`.
The kit ships five forms, words with no rank, and a project picks the ones it accepts at its setup and adds its own; what each means for the project is in its instructions as prose:

| Form | Example | Resolved against |
| --- | --- | --- |
| `formal` | `formal:Lib/Foo.lean#lemma_L`, or a whole module `formal:Lib/Foo.lean` (the extension is the project's: `.v`, `.thy`, whatever its manifest names) | machine-checked: the declaration manifest the project binds (`[evidence] manifest`, a text file of `Module.Path name` lines, a prover library's declaration list being the instance), the file looked up under `manifest_roots`; the extension is `manifest_extension`, required beside a manifest, and any extension but `md` and `py` passes as a declaration where none is bound |
| `statistical` | `statistical:probes/p.py`; `statistical:results/run.md#FV-1`; `statistical:results/run.md#measured-rates` | the project's own data: a self-asserting script, named with its directory, listed in the probes register the project binds (`[evidence] probes`, a Markdown table whose first column holds the file's name in backticks); or a committed result by its path, with an anchor checked as a document's is where it has one; a result too big to commit is named by its probe alone |
| `peer-reviewed` | `peer-reviewed:jen1990`, `peer-reviewed:jen1990#lemma` | a card of the reference library the project binds, by its key, an extract after `#` |
| `stated` | `stated:papers/alpha.md#Theorem 2.1`; `stated:papers/alpha.md#FV-1`; `stated:docs/adr/0003.md#decision` | the project's own word, a document of the project and an anchor in it: a table row whose first cell is the id, two or three capitals, a hyphen, then letters and digits (`\| FV-1 \|`; `[evidence] row_id` binds another pattern); a numbered statement — Theorem, Proposition, Lemma, Corollary, Definition, Remark, Fact, Conjecture or Example, then `N` or `N.M…`, found at a line start, after `**` or in a heading (`[evidence] statement_words` binds other words, a symbol such as `§` taking its number with no space); or a heading, by the anchor GitHub gives it, a repeated one numbered `-1`, `-2` |
| `reference` | `reference:https://doi.org/…` | any other source: a link, held to its form alone, or a repository path, held to its existence, a document's anchor checked as a stated item's is |

A form the project adds (`forms = […, "benchmark"]`) is held to its path's existence where its target is one, and otherwise reported unchecked; a form the project did not pick is refused, and so is an item with no form.
A declaration resolves when it exists in the manifest, whatever its row's kind, a private declaration's included: that claim is existence.
Whether a document may cite it is another claim, the `formal` plugin's gates' at the document row and the citation, and a finding resting on a private declaration is one no document row can cite.
A finding's trust is the set of forms its evidence carries, read and never set: the index and `flow find` show them where a status stood, and `flow find --form F` lists the findings carrying one.
The forms give a finding's evidence a direction to improve in: a finding resting on `stated` alone is work waiting, a proof to formalize, a probe to run, a work to cite, and `flow evidence F ITEM…` adds the evidence that raises its trust, each item resolved as at the mint; evidence is added and never removed.
A refutation is a finding whose claim is a negation, with evidence like any other, tagged `refuted` (`--tag refuted`); there is no status.
Where no manifest, register or library is bound, such evidence is reported unchecked, and the coverage line of `flow check` says so.
Findings live in one directory, and the document a finding belongs to is a reference `flow find --refers papers/alpha.md` groups by.

### Their transitions

| Transition | Consumes and produces | Command |
| --- | --- | --- |
| frame | ideas → question (ideas consumed), one finding → question, or a document → question | `flow frame idea-0001 --summary "…" --criterion "…"`; `flow frame --source docs/adr/0003.md --summary "…" --criterion "…"` frames it from a document of the tree, an ADR or a report, no idea captured first; `--kind conjecture`, `--parent Q` for a sub-question, `--size`, `--direction D` and `--serves G` for an open direction and goal by their ids, `--tag`, `--source`, `--body FILE` |
| refine | open question → tasks, sub-questions, ideas, the question staying open (a parked one is unparked first) | `flow refine question-0001 --task "…" --subq "…" "…" --idea "…"`; `--size`, `--dod`, `--requires ID` and `--tag T` for the tasks minted, `--body FILE` appended to the question's body under its date and never to a task's, which `flow task "…" --from Q --body FILE` writes |
| finding | the one mint of a finding, whatever produced it; with `--answers Q`, an open question → answered by it | `flow finding "…" formal:Lib/Foo.lean#decl stated:papers/alpha.md#FV-1 --from task-0001 --answers question-0001`; `--from ID` names what it came from, a done or aborted task, an idea or a question, `--depends-on F` a finding it rests on, `--tag T` (`refuted` for a disproof), `--body FILE` |
| evidence | a finding → the same finding with more evidence, its trust raised | `flow evidence finding-0001 formal:Lib/Foo.lean#decl`; added, never removed |
| wrong | an open question → wrong, with a dated reason | `flow wrong question-0001 --reason "…"` |
| impossible | an open question → impossible, by the finding that shows it, minted first | `flow impossible question-0001 --by finding-0002` |
| remove | an open question → removed with a dated reason | `flow remove question-0001 --reason "…"` |
| checked | refresh a question's last-checked date | `flow checked question-0001 …` |
| set | `criterion` and `serves` on a question, `criterion` and `horizon` on a goal (what it read kept in the body), `depends_on` on a finding (a cycle is refused) | `flow set question-0001 criterion "…"`, `flow set question-0001 serves goal-0001`, `flow set goal-0001 criterion "…" --note "the owner: …"` |

On the usual path a task is made first and its finding minted after it: `flow make T`, then `flow finding … --from T --answers Q`.
One finding answers a question, so `--answers` on a question already answered is refused; a later finding names it with `--from Q`.
`flow task "…" --from Q --tag research` mints a task from an open question outside a refine; any task may stand alone.
A wrong or impossible question is listed by the index under "Settled, do not re-open" with its word; so is any question but a removed one tagged `do-not-reopen` (`--tag` at frame, or a hand edit of `tags`), the person's mark for a matter that must not be asked again; a removed record is in none of the index's lists and none of its counts, listed only by `flow find --state removed` or `--id`.
Refine is the commitment point: anything ready may be drawn without further approval, so refine with that weight.
The last cheap "no" is at refine; most ideas should be removed, and a removal keeps its reason.
The criterion a question carries is fixed when it is framed; the probes and criteria a round fixes bind that round alone, and the `method` skill's honest-change invariants say how a target may change.

### Goals and directions

A goal is a destination the project commits to: an outcome with what reached means (its `criterion`) and a horizon in words ("before the talk", "Q1 2027", or none), formed by the owner alone, possibly after the work has started; there may be several, one may appear while the research runs, and a goal may be absent, yet to be formed.
A direction is the way the research moves, not a boundary or a gate: the owner's dated statement of what interests them, its name the summary and the words its body; the next moves lean toward the directions without being bound by them, a goal being the stronger pull where one is set, and the list stays open to new directions.
A goal implies its own direction, towards itself, so no direction record stands behind one; a direction needs no goal, and may produce goals along the way (`flow goal … --from D`), staying open.
Both are records minted and closed on the owner's word alone: `flow goal SUMMARY --criterion "…" [--horizon "…"] [--from D|IDEA]`, `flow reach G --reason "…"` (what shows it reached), `flow giveup G --reason "…"`; `flow direction NAME --body FILE`, `flow drop D --reason "…"`; a session proposes them in the log entry and mints none unasked.
A question names the direction it leans toward in `direction` and the goal it serves in `serves`, each an open record's id (`frame --direction D --serves G`, `rank --direction D --serves G`, `flow set Q serves G|none`), and may carry both.
A goal's `criterion` and `horizon` are the owner's words: `flow set G criterion "…"` leaves what it read in the body, dated, and `--note "…"` the owner's words for the change.
A goal given up releases its open questions, which serve nothing and keep their ranks for `whatsnext` to re-rank; a direction dropped clears its open questions' `direction`; a closed question keeps what it served and leaned toward as history.
`flow directions` renders the open directions as the owner's list; the index lists the open goals under `Goals`, each with the open questions serving it, and the open directions under `Directions`, and `whatsnext` reads its case off them: no goal and no direction, directions and no goal, a goal.

### Invariants the validator adds

- An open task that came from a question came from an open one.
- Every finding has evidence, each item of a form `[evidence] forms` lists and resolved by that form's shape, no item twice.
- Every open question has a last-checked date; a current question has a criterion, and a question imported from before the flow gains one at its first round.
- An answered or impossible question names the one finding that settles it in `answered_by`, one value, never a task, one imported from before the flow excepted where it names none; no other question names one.
- A consumed idea lists in `consumed_by` the cards it was folded into, each naming it in `derived_from`.
- An open question's `direction` names an open direction and its `serves` an open goal.
- A reached or given-up goal, and a closed direction, carry their dated reason in `closed`.
- No cycles in `depends_on`.

### Reading and writing them

Everything above holds; in addition:
never edit `answered_by` by hand, and change the criterion through `flow set … criterion`; a question's body points at where the question is STATED (a document's section, a module) and never restates it.
No question is parked, ranked down or excluded for lacking a route; parking carries a dated reason, and revival triggers where they are known.
A result is registered in a document as a specific numbered statement with its rows and boundary, never as a thesis rewrite, and the finding that records it is written from the landed artifact, never from the design record that commissioned it.

## What else a project keeps

- A LOG of dated entries, newest first, one per landing or decision, each `## YYYY-MM-DD — headline` opening with a State paragraph, the top one the paragraph a cold session trusts, written by `flow log add`; the commit message carries its headline and a pointer, never the entry; old entries are archived by month, verbatim, by `flow log archive`.
- An INBOX, `INBOX.md` at the root unless `[paths] inbox` names another, where the person leaves items between sessions and a freeze leaves a directive for the next one; the next session's `whatsnext` reads it and proposes what to make of each item, and no rule empties it at a freeze.
- Its ARTIFACTS — the papers, datasets, probes, figures and releases it makes — as repository paths the records refer to, by an evidence item or a body link, listed by `flow artifacts` from the records alone, no register to keep consistent; a stale artifact is a task, and the artifacts a project must name, the papers it targets, are in its instructions as prose.
- A REGISTRY of the deliverables — what the project produces (documents, a library, releases) and in what order they are read or shipped — the one place that order is stated; the ranked list orders the work, the registry the products.
- Optionally a reference library of the works it refers to, the `library` skill's, bound to the flow by one command.
- Optionally an annex for the artifacts it made that a recorded claim depends on and no other container owns, its front page carrying the test for what is admitted, a subdirectory made only when what fills it exists.

## What the project binds

`flow init` in an empty project writes `flow.toml` with the bindings filled in and the optional ones commented, the record directories under `records/` (`--records DIR` for another), the inbox, the log where `--log FILE` names one, and the index, and prints the paragraph the project's instructions should carry; `--force` overwrites a bindings file that exists.
It writes two owners unless `--owner` names others: `agent`, with a hand limit of four, and `owner`, the person, with no limit (a limit of 0 is unlimited).
`flow.toml` names the record directory, the index, the archive, the inbox, the log and its archive directory (beside the log, `WORKLOG-archive/` for `WORKLOG.md`, where unbound), the id prefixes and width, the owners and their hand limits, the sizes, the evidence forms the project accepts (`[evidence] forms`, the five shipped ones as written; the setup asks the owner which to keep and which words of the project's to add) and the evidence resolvers, the reflow module and the markdownlint config, and the reference library's command, which may stay unset: with a `library.toml` at the root the flow asks the library skill installed beside this one, else `library` on PATH, and `flow check`'s coverage line says which.
The project's instructions name the log, the registry, the gates that cover the records and the archive rule, and what each evidence form means for the project.
The project's instructions also name where results are registered and what gates cover them.
