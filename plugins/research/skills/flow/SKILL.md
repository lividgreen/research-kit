---
name: flow
description: The typed flow of research work — ideas, tasks, questions with kill criteria and findings whose evidence a machine resolves, one Markdown record each, transitions through the `flow` CLI, a validator, a generated index with a ranked next list, and a cold-start bundle. Use when reading a project's records to pick up work, when capturing an idea, minting or drawing a task, closing one with its resolution, framing or answering a question, recording a checkable result, ranking the next list, or restructuring the records. The project's own instructions bind the directory, the prefixes and the gates through `flow.toml`; this skill names none of them.
license: Apache-2.0
compatibility: Python 3.11 or later, standard library only. Optional - markdownlint on PATH (a write that adds a violation is reverted), git (the log's part of a session's close check), a project reflow module (one sentence per line; built in otherwise); a declaration manifest and a probes register for the findings' evidence, without which declaration and probe evidence is reported unchecked.
metadata:
  version: "0.2.1"
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
| idea | a raw signal worth attention: one sentence and a source; most die | open, consumed, abandoned |
| task | a unit of work one owner can finish within its size: a design round, a prose sweep, upkeep, a community item, an owner decision | ready, active, done, abandoned |

Distinguishing tests: can one owner finish it within its size? then it is a task, not an idea.
Is it a thing you want to know rather than a thing to do? then it is a question, the kind below.
A closed task moves to the archive at its closing transition, so the record directories show the live front of work.

## Transitions

| Transition | Consumes and produces | Command |
| --- | --- | --- |
| capture | external → idea | `flow capture "…" --source S`; `--tag T`, `--body FILE` |
| task | external → task | `flow task "…" --kind upkeep`; `--question Q` for a task under a question, `--size`, `--dod`, `--source`, `--tag`, `--body FILE` |
| draw | ready task → active, under the owner's hand limit | `flow draw task-0001 --owner agent` |
| return | active task → ready | `flow return task-0001 --note "…"` |
| make | active task → done and archived; follow-up tasks and ideas | `flow make task-0001 --resolution FILE --task "…" --idea "…"`; `--question SUMMARY KILL` mints a question |
| abort | active task → abandoned and archived | `flow abort task-0001 --reason "…"`; `--resolution FILE` |
| kill | idea, ready task, or open or decomposed question → abandoned with a dated reason; an active task is aborted instead | `flow kill idea-0001 --reason "…"` |
| rank | the ranked next list: one record's rank, the whole order at once, or a rank cleared | `flow rank task-0001 1 --why "…" --first-move "…"`; `--direction D`; `--insert` to take a held rank and move the rest down; `flow rank --set ID…`; `flow rank task-0001 --clear` |
| set | one hand-editable field: summary, size, dod, rider on or off | `flow set task-0001 size small` |

Views: `flow find --type task --state ready` (also `--kind`, `--status`, `--tag`, `--owner`, `--question Q`, `--paper P`, `--requires ID`, `--depends-on ID`, `--parked`, `--ranked`, `--grep WORD`), `flow show ID` (the record, its links and its back-references), `flow graph --from ID` (`--dot` for Graphviz), `flow state` (the cold-start bundle; `--from N` continues it, `--budget N` bounds it; `--check --owner O` checks a session's close, below), `flow directions` (the directions file), `flow index` (`--print` to stdout, `--check` for drift), `flow check`.
`flow --help` lists every command, `flow <command> --help` its flags, and neither needs a bindings file.
The global flags are `--json` (any command emits one JSON object), `--root DIR` (the project, found upward from the working directory otherwise) and `--today DATE`; `flow pages` prints the page manifest the `dashboard` skill renders.
A `--body FILE` or `--resolution FILE` takes a file, never inline text, so a long body is drafted first and checked by the project's text gates — its own checks on prose, such as a linter or a line rule.
Make and abort append the resolution to the task's body under its date, as refine appends its `--body` to the question's and says so, so the archived task keeps what was asked and its notes.
A ready or active task's `rider` field marks it as riding the next piece of work handed to another owner; the index lists such tasks under "Rider for the next hand-over".

A design round is a task of the design kind: drawn before the round, closed by make or abort with the round record as its resolution and its discarded options one line each inside that record.
Make and abort are where follow-up work is minted: a residue sharp enough to name becomes a task or a question of its own rather than prose in the resolution or a line appended to a question's body.

## Invariants the validator enforces

- Every id is unique and matches its filename prefix; every referenced id exists and has the type the field demands; no cycles in `derived_from`.
- State, kind, size and owner are legal values from `flow.toml`.
- Active tasks per owner stay within the hand limit; a closed task lives in the archive and an open one does not; an abandoned record carries a dated reason.
- Ranks are unique and contiguous, never on a closed record or on owner-only work, and a ranked record says why now and what the first move is ("none yet" is allowed).
- Every body is one sentence per line; the committed index equals a fresh render.
- Every library key a record cites is a card the library holds, where a library is bound.

`flow check` prints a coverage line saying which resolvers were configured, so a green says what it did not look at.
`flow.py --selftest` plants one defect per code the check reports, fails when one is planted nowhere, and must stay green.

## Reading discipline

Start with `flow state`: the inbox slot of the directions file, the ranked next list and the log's top entry, every line carrying its file and line.
The log is dated entries, newest first, each a level-2 heading `## YYYY-MM-DD — headline` opening with a `**State.**` paragraph; `flow state` prints the whole top entry, and its State paragraph is the one a cold session trusts.
Then the generated index, which lists the ranked list, each owner's hand, ready work and owner-only items.
Locate records with `flow find` or `flow show ID`; open record files only by ID.
Never glob the record directories, and never read a record directory whole.
A cold session processes the inbox slot first, then reads the next list and the log's top State paragraph, and continues without asking, unless the project's instructions say the owner is asked before work is drawn.

## Writing discipline

Transitions go through `flow`.
Never edit `id`, `type`, `state`, `derived_from`, `consumed_by`, `owner`, `drawn`, `rank`, `abandoned`, `origin` or `created` by hand.
The one record written by hand is one imported from before the flow: its whole file, with `origin: legacy`, which exempts it from the kill-criteria rule until its first round; no transition writes that value.
Edit a body freely, and a `summary`, `size`, `dod` or `rider` with `flow set`, which refuses a field the record's type does not carry and a value the field does not take; a body is one sentence per line, and a write that adds a markdownlint violation is reverted where markdownlint is on PATH (with the project's configuration where `flow.toml` binds one or the root keeps one, else a built-in one under which a record's `summary:` is its title).
The front matter is the subset of YAML the script writes: plain scalars, single-quoted strings (a quote doubled inside), double-quoted strings with escapes, `null`, `true`/`false`, integers, block lists (`- item`) and one-level maps; a hand edit stays inside that subset, and `flow check` reads every record back.
A record points at where its subject is STATED and never restates it, because the statement moves and a copy does not.
A design record is never authority: a record points at a round for its reasoning or its history, never cites it for a rule, a criterion or a method, since the criteria a round fixed bound that round alone.
Run `flow check` before committing; the project's hook runs it as well.

## The log, the close and the project's other prose

`flow log add FILE` writes the entry FILE holds at the top of the log, under its title: reflowed to one sentence per line, a bold label of at most four words ending in a period, such as `**State.**` or `**Theorem 2.1.**`, a parenthetical allowed after its words as in `**Proposition 5.3 (Jen 1990).**`, kept with its sentence, and reverted where markdownlint reports a violation the log did not have, as a record's write is.
It refuses an entry that does not open with its `## YYYY-MM-DD — headline` and its `**State.**` paragraph, one dated after today or before the top entry, and a file holding two entries.
`flow log archive --before DATE` moves every entry dated before DATE, verbatim and newest first, into one file per month (`2026-09.md`) in the log's archive directory, merging into a month's file that exists and keeping the link definitions closing it, and leaves one line under the log's title (under its front matter where it has no title) pointing there; the top entry always stays, and an entry whose heading carries no date is refused, since the archive files an entry by its date.
The log's entries are its level-2 headings outside its front matter and its code fences, a fence closing only on a run of its own character at least as long as the one that opened it.
A link definition closing the log goes to every file whose text uses its label: it moves to the archive files where only archived entries use it, is copied where the log uses it too, and stays in the log where nothing does.
The log and its archive files are written together or not at all, and a markdownlint violation either would gain undoes both.

`flow state --check --owner O`, at a session's close, decides what a machine can see of it, O being the working session's owner, and prints one line per failure:

- the directions file's inbox holds a line outside a comment;
- an active task is held by another owner than O, other than a decision owner `flow.toml` names, whose hand the person holds;
- the log's top entry is not dated today while the tree has changed since the commit of the newest committed entry — any commit since, on a shared repository another's as well;
- a record changed since that commit, and no entry from the top down to that one names its id.

The log's two need git and a committed log; where either is missing, or there is no inbox section, the check says which part it did not decide.
It exits 1 when a part fails, else 2 when a part could not be decided, so a close it could not see whole is never read as clean, else 0; without `--owner`, or with one `flow.toml` does not list, it does not run and exits 2.
What it cannot see stays the session's: what the conversation holds that no record does, and whether every site a change reaches says the same; `references/closing.md` is the close — the clone test, the inventory turn by turn, the sweep by meaning — and what the agent's memory holds.

`flow reflow --check PATH…` holds the project's other prose to the reflow the records get: it prints each line, as file and line, that the reflow would change, skipping a front matter block, reads the Markdown files under a directory, and exits 1 on any, or 2 on a path that is not there.
A line the reflow does not split is left as written, so a hard break's two trailing spaces are not a change, and a line it splits keeps them on its last part; a code fence is read as the log's are.
`flow reflow --as DEST DRAFT` checks a draft before it is placed: its lines the reflow would change, and the markdownlint violations it adds when appended to DEST (the draft alone where DEST does not exist yet), under the configuration a record's write runs with, each at the draft's own line, and never one DEST had already; it writes nothing.

## The next list

The ranked records are the schedule of the WORK, and the only one; the registry below orders the deliverables, not the work.
A session works from the top.
The list is filled or refreshed when the owner asks or when it is empty, on no cadence, with no per-landing re-triage; `references/next-list.md` is the refresh procedure.
Nothing is ranked down or left off for lacking a route: a record with no known route is ranked with a first move of "none yet", and finding the route is its first round's job.
The one gate is owner-only work — a task of a decision kind, or held by a decision owner — which is never ranked, since it holds what only the owner can do or should decide; a decision gates a landing, never a start.
A done item clears its own rank through its transition, and the ranks below it close up, so the list stays 1..n without a hand on it.

## Questions and findings

The two kinds above hold the work; these two hold what is KNOWN and what is WANTED.

### The two kinds

| Kind | What it is | States |
| --- | --- | --- |
| question | a precisely stated question or conjecture, with kill criteria; what we want to know | open, decomposed, answered, abandoned |
| finding | a CHECKABLE claim: its evidence is a declaration in a manifest, a document's numbered statement or table row, or a self-asserting probe | none; it accumulates |

Distinguishing tests: can you say what would count as an answer? then it is a question, not an idea.
Can its evidence be resolved by a machine? then it is a finding; otherwise it is a claim inside a task's resolution until it earns evidence.
Every task done and nobody can state the answer? then the question goes back to refine.
A conjecture is a question of kind `conjecture` (`flow frame … --kind conjecture`), never a finding; a dead end is an abandoned task's resolution, never a finding.
There is no artifact record: the documents and the machine-checked library ARE the artifacts, and findings point at them directly.

A question asks one thing, and its kill criteria say what answers it.
An open end a round finds beyond those criteria is framed as a question of its own, from the finding that exposed it (`flow frame finding-0001 …`) or from an idea captured first, and is never appended to the first question's body as what stays open: a question that gathers its residues has no answer anyone can reach, and the next list can no longer rank it by how near it is to done.
A question whose parts each carry weight alone is split: at framing, into one question per part; at answering, the part answered closes the question, and each part still open is framed on its own with a pointer to where it is stated.

### Evidence and status

An evidence item is one of four forms, each resolved by the validator and by `make`:

| Form | Example | Resolved against |
| --- | --- | --- |
| declaration | `Lib/Foo.lean#lemma_L`, or a whole module `Lib/Foo.lean` (the extension is the project's: `.v`, `.thy`, whatever its manifest names) | the declaration manifest the project binds (`[evidence] manifest`, a text file of `Module.Path name` lines, a prover library's declaration list being the instance), the file looked up under `manifest_roots`; the extension is `manifest_extension`, required beside a manifest, and any extension but `md` and `py` passes as a declaration where none is bound |
| row | `papers/alpha.md#FV-1` | a table row of that document whose first cell is the id — two or three capitals, a hyphen, then letters and digits — written `\| FV-1 \|` |
| statement | `papers/alpha.md#Theorem 2.1` | a numbered statement of that document — Theorem, Proposition, Lemma, Corollary, Definition, Remark, Fact, Conjecture or Example, then `N` or `N.M…` — found at a line start, after `**` or in a heading |
| probe | `probes/p.py` | a self-asserting script, named with its directory, listed in the probes register the project binds: a Markdown table whose first column holds the file's name in backticks |

A finding's status is one of four roles the project names in `[finding]` (the defaults are `verified`, `stated`, `empirical`, `refuted`; a prover project may call them `lean-verified`, `proven`, `empirical`, `refuted`): verified needs a declaration among its evidence; stated is document-level, a statement or row and no declaration; empirical needs a probe and no declaration; refuted needs a guard declaration or a probe as the counterexample.
The status follows the evidence and is never set by hand: a finding is verified only because its declaration resolves in the manifest the project's build regenerates.
Where no manifest or register is bound, such evidence is reported unchecked, and the coverage line of `flow check` says so.
Findings shard by the document that registers them (`--paper`, read off a row or statement item when not given) under the shards `flow.toml` lists.

### Their transitions

| Transition | Consumes and produces | Command |
| --- | --- | --- |
| frame | ideas → question (ideas consumed), or one finding → question | `flow frame idea-0001 --summary "…" --kill "…"`; `--kind conjecture`, `--parent Q` for a sub-question, `--size`, `--direction D`, `--tag`, `--source`, `--body FILE` |
| refine | open or decomposed question → tasks, sub-questions, ideas; the question is decomposed (a parked one is unparked first) | `flow refine question-0001 --task "…" work --subq "…" "…" --idea "…"`; `--kind`, `--size`, `--dod` and `--requires ID` for the tasks minted, `--body FILE` appended to the question's body under its date and never to a task's, which `flow task "…" --question Q --body FILE` writes |
| make, abort | an active task's closing transition may mint findings and questions | `flow make task-0001 --finding "…" verified Lib/Foo.lean#decl --resolution FILE`; `--paper P` names the shard, `--depends-on F` a finding's dependence |
| answer | question with a finding → answered; refused while it has open tasks; a question whose kill names work rather than a result is answered by the done tasks drawn under it | `flow answer question-0001 --by finding-0001`; `flow answer question-0002 --by task-0003`; `--by` repeats where several findings or tasks answer it together |
| kill | an open or decomposed question → abandoned with a dated reason | `flow kill question-0001 --reason "…"` |
| park, unpark | an open question gains or loses a parking block: the date, the reason, and revival triggers where known (`--revival` is optional) | `flow park question-0001 --reason "…" --revival "…"`; `flow unpark question-0001` |
| checked | refresh a question's last-checked date | `flow checked question-0001 …` |
| set | `kill` (the criteria), `depends_on` on a finding (a cycle is refused) | `flow set question-0001 kill "…"` |

`flow task "…" --kind work --question Q` mints a task under a question outside a refine; without `--question` only a question-optional kind stands alone.
A question tagged `do-not-reopen` (`--tag` at frame, or a hand edit of `tags`) is listed by the index under "Settled, do not re-open" whatever its state, so a settled matter is seen before it is asked again.
Refine is the commitment point: anything ready may be drawn without further approval, so refine with that weight.
The last cheap "no" is at refine; most ideas should die, and a kill keeps its reason.
The kill criteria a question carries are fixed when it is framed; the probes and criteria a round fixes bind that round alone, and the `method` skill's honest-change invariants say how a target may change.

### Directions

A direction is a hint about what interests the owner, not a boundary or a gate: items toward one rank first on the list and may be opened with no known route; a direction changes nothing else.
Directions are bullets of the directions file's `## Directions` section, written by the owner, each in the form `- **Name** (date) — the words`; a question's `direction` carries the bold name and must match one (the validator's V22), and sessions propose directions in the log and mint none.

### Invariants the validator adds

- A task has one question unless its kind is one the project lists as question-optional; an open task's question is open or decomposed.
- Every finding has evidence, each item resolves by its kind, and the status is consistent with the kinds present.
- Every open question has a last-checked date; a current question has kill criteria, and a question imported from before the flow gains them at its first round; a parked question is open with a date and a reason and is never ranked.
- A decomposed question has a task; one whose tasks are all closed is flagged as needing refine or answer.
- A question's direction names a bullet of the directions file.
- No cycles in `depends_on`.

### Reading and writing them

Everything above holds; in addition:
never edit `question`, `answered_by`, `parked` or `abandoned` by hand, and change the kill criteria through `flow set … kill`; a question's body points at where the question is STATED (a document's section, a module) and never restates it.
No question is parked, ranked down or excluded for lacking a route; parking carries a dated reason, and revival triggers where they are known, and a stalled item is parked rather than left ranked.
A result is registered in a document as a specific numbered statement with its rows and boundary, never as a thesis rewrite, and the finding that records it is written from the landed artifact, never from the design record that commissioned it.

## What else a project keeps

- A LOG of dated entries, newest first, one per landing or decision, each `## YYYY-MM-DD — headline` opening with a `**State.**` paragraph, the top one the paragraph a cold session trusts, written by `flow log add`; the commit message carries its headline and a pointer, never the entry; old entries are archived by month, verbatim, by `flow log archive`.
- A directions file the owner writes: an inbox slot the next session processes before anything else — each item turned into a record or acted on, named in that session's log entry, and removed, the slot never serving as a log — and the owner's dated statements of interest.
- A REGISTRY of the deliverables — what the project produces (documents, a library, releases) and in what order they are read or shipped — the one place that order is stated; the ranked list orders the work, the registry the products.
- Optionally a reference library of the works it refers to, the `library` skill's, bound to the flow by one command.
- Optionally an annex for the artifacts it made that a recorded claim depends on and no other container owns, its front page carrying the test for what is admitted, a subdirectory made only when what fills it exists.

## What the project binds

`flow init` in an empty project writes `flow.toml` with the bindings filled in and the optional ones commented, the record directories under `records/` (`--records DIR` for another), the directions file, the log where `--log FILE` names one, and the index, and prints the paragraph the project's instructions should carry; `--force` overwrites a bindings file that exists.
It writes two owners unless `--owner` names others: `agent`, the working session, with a hand limit of two active tasks, and `owner`, the person, with no limit (a limit of 0 is unlimited), who is the decision owner — a task of a decision kind is minted under that owner's hand and is never ranked.
`flow.toml` names the record directory, the index, the archive, the directions file, the log and its archive directory (beside the log, `WORKLOG-archive/` for `WORKLOG.md`, where unbound), the id prefixes and width, the owners and their hand limits, the task kinds, the default kind, the question-optional kinds, the decision kinds and owners (owners listed under `[hand]`, or none), the sizes, the finding statuses, the shards, the evidence resolvers, the reference library's command, the reflow module and the markdownlint config, and the library's command, which may stay unset: with a `library.toml` at the root the flow asks the library skill installed beside this one, else `library` on PATH, and `flow check`'s coverage line says which.
The project's instructions name the log, the registry, the gates that cover the records and the archive rule.
The project's instructions also name where results are registered and what gates cover them.
