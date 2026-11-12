---
name: flow
description: The typed flow of research work — ideas, tasks, questions, findings whose evidence a machine resolves, the goals the owner forms and the directions they set, one Markdown record each, linked by references and four links with a rule, moved through the `flow` CLI, with a validator, a generated index with a ranked next list, and a cold-start bundle. Use when reading a project's records to pick up work, when minting an idea, a question, a task, a finding, a goal or a direction, drawing or closing a task, answering, closing or reopening a question, removing a finding found false, adding evidence, reaching or giving up a goal, dropping a direction, parking or blocking a record, linking records, ranking the next list, or restructuring the records. The project's own instructions bind the directory, the prefixes and the gates through `flow.toml`; this skill names none of them.
license: Apache-2.0
compatibility: Python 3.11 or later, standard library only. Optional - markdownlint on PATH (a write that adds a violation is reverted), git (the log's part of the freeze check), a project reflow module (one sentence per line; built in otherwise); a resolver for the findings' formal evidence (the formal plugin's, where a formal.toml stands), a probes register and a reference library, without which formal, probe and peer-reviewed evidence is reported unchecked.
metadata:
  version: "0.7.0"
  script: scripts/flow.py
---

# The flow

Work is records: one Markdown file each, front matter plus a prose body, connected by links and moved by transitions.
The records hold data only; rules live in the project's instructions, the skills and the hooks the project runs.
`scripts/flow.py` beside this file is the CLI, the validator, the index generator and the selftest; `flow …` below is that script run by its path from the project root (`python3 ${CLAUDE_PLUGIN_ROOT}/skills/flow/scripts/flow.py …` under Claude Code), never a `flow` found on PATH, which may be another version.
`flow.toml` at the project root binds the paths and the vocabulary.

## The kinds

| Kind | What it is | States |
| --- | --- | --- |
| idea | a thought worth keeping that is not yet a question: nothing says what would answer it, no route; one thing, not a basket of several | open, consumed, removed |
| question | what we think we have to answer to move the research; its body says what counts as an answer, or points at where that is stated | open, answered, wrong, impossible, removed |
| task | a unit of work one owner can finish within its size: a design round, a prose sweep, upkeep, a community item; its body says what done means | ready, active, done, aborted, removed |
| finding | a CHECKABLE claim: each item of its evidence names its form and its target, `formal:Lib/Foo.lean#decl`, and the forms it carries are its trust | standing, removed |
| goal | a destination the owner commits to: its summary names the outcome, its body what reached means and how far out it lies | open, reached, given_up |
| direction | the owner's dated statement of where the research moves, its name the summary and their words the body | open, closed |

Distinguishing tests: can one owner finish it within its size? then it is a task, not an idea.
Is it a thing you want to know rather than a thing to do? then it is a question.
Can you say what would count as an answer? then it is a question, not an idea.
Can its evidence be named in a form the project accepts and resolved by a machine where the form allows? then it is a finding; otherwise it is a claim inside a task's resolution until it earns evidence.
A conjecture is a question tagged `conjecture` (`flow question … --tag conjecture`), never a finding; a dead end is an aborted task's resolution, never a finding.

Tasks stand across the main axis, idea to question to finding: a task is a unit of work, and a question's closing is its own act, never a consequence of a task's.
A record needs nothing above it: a question may stand alone, a task may come from nothing, a finding needs no question and no goal.

## The links

Five fields connect the records, one general and four with a rule.

| Field | On | Holds | Its rule |
| --- | --- | --- | --- |
| `references` | every kind | a list of record ids | none: the general link |
| `answered_by` | question | one finding | the finding that settles it, answered or impossible |
| `blocked_by` | question, task | a map of `date`, `on` (a list) and `reason` | `draw` is refused while an item of `on` holds |
| `serves` | question | a list of goal and direction ids | biases the ranking; the index lists each goal's and direction's questions |
| `consumed_by` | idea | a list of record ids | the cards that name the idea in `references`, written with the reference |

`references` is a connection with no obligation in the flow, a clue that persists: a record names what it came from, rests on or is about.
Its target is a record of any kind in any state, a closed or a removed one included, since nothing is deleted.
It is written at any mint with `--ref ID`, repeatable, and changed afterwards with `flow ref ID +X -Y`; an entry is an id that exists, never the record's own and never one it holds already, and nothing else is refused, warned of or failed because one exists.
Where the entry is an idea, the script writes the card into the idea's `consumed_by` in the same command, whatever the idea's state, and `flow ref ID -X` takes it out again: `consumed_by` is exactly the records that name the idea in `references`, and the command reports the idea as changed beside the record.
A task connected to a question names it; a follow-up task that is not, does not, and nothing is inherited from the task it follows.

## Hands

A hand is an owner's, and holds the active tasks and the ideas drawn into it, within the limit `[hand]` sets.
There are two hands: the agent's, which spans its sessions and holds what its subagents do, and the person's.
The skills write `agent` and `owner` for them, the names `[hand]` gives them by default, and the names a project's `[hand]` sets are what the commands take.
A task handed to another session, a prover's, stays active in the agent's hand; the handoff's log entry says where it went.
A drawn task that must wait is returned first, with a note, and then parked or blocked; the hand holds only what is being worked.

## The mints

Only the mints mint, one per kind, each the kind's name; every one takes the summary as its one positional, `--ref ID` (repeatable), `--tag T` (repeatable), `--source S` and `--body FILE`.

| Mint | The kind's own flags |
| --- | --- |
| `flow idea "…"` | none |
| `flow question "…"` | `--serves ID` (repeatable): an open goal or direction; `--size` |
| `flow task "…"` | `--size`, `--due YYYY-MM-DD`, `--after "…"` |
| `flow finding "…"` | `--evidence FORM:TARGET…` (one or more, required, repeatable); `--answers Q`, the open question it settles, which closes answered |
| `flow goal "…"` | none |
| `flow direction "…"` | none |

A question is minted with its `checked` date at today; a finding it comes from, or a wrong question it re-states, is a `--ref`, and a document it is framed from, an ADR or a report, is its `--source PATH`.
A source with a path's shape (no space, a `/` or an extension) is held to the tree; one in words takes a space.
The words that went before this model are answered with the new way: `capture` is `flow idea`, `frame` is `flow question "…" --ref IDEA` and `flow consume IDEA` once the idea is fully processed, and refining a question, the act of minting its first tasks, is `flow task "…" --ref Q` for each, `flow question "…" --ref Q` for a sub-question.

An idea is worked, not only framed: drawn into a hand like a task, it produces what it holds, ideas, questions, tasks and findings, each naming it with `--ref` and listed in its `consumed_by` as it is minted, until everything in it is folded into them and the idea is fully processed, when `flow consume IDEA` closes it, or it is removed; an idea put back partly worked is returned, its note listing what it produced so far.
A fresh idea is an open one whose `consumed_by` is empty, calculated and never stored; no mint closes an idea, and `flow consume IDEA` is refused on a fresh one, since an idea that produced nothing is removed with a reason.
A thought that holds several things produces one idea per thing while it is worked; there is no split command.
An idea's size is its independence, not its length: two thoughts that can be framed, worked or dropped apart are two ideas, and a long body that gives one thought its context stays one idea.

A task is work that is big, or that must outlive the turn: a later session or the other hand needs to know it is underway or done, or its result has to be linked; either test is enough, applied with judgment rather than a limit.
Work that passes neither is done in the turn and named in the log entry, and an operation on a card is never a task.
An operation that finds a big piece of work recommends a task and does not do it: `flow task "…" --ref ID` mints it, its body saying what was being attempted and what done means.
Independent pieces of work are not bundled into one task, and a task whose done cannot be stated at once is split; `size` is an estimate for ordering.
A task may carry a due date (`--due YYYY-MM-DD`, `flow set T due DATE|none`), which never moves a rank: the index lists the open tasks that have one under `Due`, soonest first, `flow state` prints that list first, within `[index] due_within` days where `flow.toml` binds it (the index keeps the whole list, since it never reads the day), and names a date that has passed, and `flow check` warns on one, never fails; a not-before date is a block on the date written alone (`flow block T --on 2026-12-01 --reason "…"`), which holds until that day.
A due date is a day of the calendar: `--due 2026-13-01` is refused.
A task may carry a post-done instruction (`--after "…"`, `flow set T after "…"|none`), free text written at the open and printed by `make` and `abort` at the close for the agent to follow; a repeat is the agent minting the follow-up after the make, no interval in the script.
Tags are free words and no vocabulary is validated: `research` and `upkeep` are the usual ones, written at the mint (`--tag`) and changed after it with `flow tag ID +T -U`, a project's own words beside them; `flow tags` reports every tag in use with the records carrying it and the records carrying none, and a project's rule that rides on a tag is unchecked.
The tag `rider` marks a task riding the next piece of work handed to another session, read by `flow find --tag rider --state ready`; the tag `conjecture` marks a conjecture.

## The closings

| Transition | Consumes and produces | Command |
| --- | --- | --- |
| draw | ready task → active, or open idea → in the hand, under the owner's hand limit; refused while the task is parked or its block holds | `flow draw task-0001 --owner agent` |
| return | active task → ready, or an idea out of the hand | `flow return task-0001 --note "…"` |
| make | active task → done and archived, its resolution appended under the date; the task's `after` printed; it mints nothing | `flow make task-0001 --resolution FILE` (required, refused empty; `-` reads the standard input) |
| abort | active task → aborted and archived, with its dated reason | `flow abort task-0001 --reason "…"`; `--resolution FILE` |
| answer | open question → answered by a standing finding | `flow answer question-0001 --by finding-0002` |
| impossible | open question → impossible, by the standing finding that shows it | `flow impossible question-0001 --by finding-0002` |
| wrong | open question → wrong, with a dated reason | `flow wrong question-0001 --reason "…"` |
| reopen | any closed question (answered, impossible, wrong, removed) → open, its `answered_by` and its closing cleared, `checked` at today, a dated note keeping what it was; a consumed idea → open, its `consumed_by` kept | `flow reopen question-0001 --reason "…"`, `flow reopen idea-0001 --reason "…"` |
| remove | open idea, open question, ready task or standing finding → removed with a dated reason; an active task is aborted instead | `flow remove idea-0001 --reason "…"` |
| consume | open idea → consumed, fully processed: its `consumed_by` lists the cards it produced and is kept, the hand cleared; refused where `consumed_by` is empty | `flow consume idea-0001` |
| reach, giveup | open goal → reached or given up, with a dated reason | `flow reach goal-0001 --reason "…"` (what shows it reached), `flow giveup goal-0001 --reason "…"` |
| drop | open direction → closed, with a dated reason | `flow drop direction-0001 --reason "…"` |
| evidence | a standing finding → the same finding with more evidence, its trust raised | `flow evidence finding-0001 formal:Lib/Foo.lean#decl`; `--replace OLD NEW` swaps an item and `--retire OLD --reason R` removes one, each with a dated note in the body |

A task closes one of three ways: made (state `done`), aborted when started and failed, or removed with a reason while ready, never started or returned.
A closed task moves to the archive at its closing transition, so the record directories show the live front of work.
A done task with no resolution is never legitimate: the resolution says what was done, and the archived task keeps what was asked and its notes.
A residue sharp enough to name becomes a task, a question or an idea of its own, minted after the make with `--ref T`, rather than prose in the resolution or a line appended to a question's body.
A design round is a task tagged `design`: drawn before the round, closed by make or abort with the round record as its resolution and its discarded options one line each inside that record.

A question is minted in the expectation of a finding, a part of the research and not of the conversation, and closes one of four ways:

- answered, by the one finding that settles it: `flow finding … --answers Q` mints it and closes the question in one, `flow answer Q --by F` names a finding that exists; one finding may settle several questions;
- wrong, when it is shown to be stated incorrectly, with a reason and no finding; a re-stated question references the wrong one;
- impossible, when it is shown that it cannot be answered, a paradox for one, by a finding with its evidence like any other; with no such evidence the question is not impossible but removed;
- removed, dropped with a reason, its card kept but in none of the index's lists and out of `flow find` unless asked, the findings minted under it before staying.

No closing of a question is refused for a task that names it, and no task's closing closes a question; `answer`, `impossible` and `--answers` refuse a removed finding and a question that is not open, which is reopened first.
`flow reopen` is refused on a question or an idea tagged `do-not-reopen`, the person's mark that a matter stays settled: on that refusal the agent asks the person what to do and never lifts the tag (`flow tag Q -do-not-reopen`) unasked.
Its note reads `reopened: REASON; it was STATE`, with `by F` where a finding settled it and `(DATE: its closing reason)` where it carried one; an idea takes it only consumed, a removed idea staying final and restored from git where it was removed by mistake; no other kind is reopened, redone work being a new task that references the old one.

An idea removed keeps its `consumed_by`: an idea dropped partly worked keeps what it produced.
A finding found false is removed: `flow remove F --reason R` keeps its card, out of the index's lists and counts, and the notice names everything that refers to it.
What rested on it is the session's to review by hand, case by case: a question it answered is reopened, re-answered or left, and the finding that replaces it references the removed one.
The check says nothing afterwards; the tag `refuted` keeps its meaning, a finding whose claim is a negation.

## The notice

A transition that changes a record's state, or parks, unparks, blocks or unblocks it, prints under that record's `changed` line the records that refer to it by any link, each with its state: `refers to it, may need a follow-up: task-0002 (ready)`; under `--json` the list `notices`, `{"id": …, "refers": [{"id": …, "state": …}]}` for each.
A removed record is left out, and so is a record the same command minted or changed; a closed one is listed.
The link `consumed_by` is read only where the record ended badly or came back, so an idea is named for a card it produced only then: a question closed wrong, removed or reopened, a task aborted or removed, a finding removed; it is not named where a question is answered or impossible or a task done, nor on a park, an unpark, a block, an unblock, a draw or a return, and `flow consume IDEA` prints no notice.
The other links are read on every change, so `flow remove IDEA` and `flow reopen IDEA` name the cards that name the idea.
It is printed by the command that makes the change and nowhere else: `flow state --check`, `flow touched` and `flow check` repeat none of it, and `flow show ID` lists what refers to a record for whoever looks again.
It refuses nothing, fails nothing and asks for no reference to be removed: what follows is the session's to decide, record by record, the task done anyway, removed with a reason, or something else.

## The positions and the fields

| Transition | What it does | Command |
| --- | --- | --- |
| park, unpark | an open question or a ready task gains or loses a parking block: the date, the reason, and revival triggers where known (`--revival` is optional); the rank stays; on a question either sets `checked` to today | `flow park task-0001 --reason "…" --revival "…"`; `flow unpark task-0001 --note "…"` |
| block, unblock | an open question or a ready task gains a block, `blocked_by`, or loses it or one of its items; the rank stays; on a question either sets `checked` to today | `flow block task-0001 --on question-0002 --on 2026-12-01 --on "the vendor's reply" --reason "…"`; `flow unblock task-0001 --on "the vendor's reply" --note "…"`, or with no `--on` the whole block |
| rank | the ranked next list: one record's rank, the whole order at once, or a rank cleared | `flow rank task-0001 1`, `--insert` to take a held rank and move the rest down; `flow rank --set ID…`; `flow rank task-0001 --clear` |
| checked | an open question's last-checked date refreshed: a read recorded | `flow checked question-0001 …` |
| set | `summary` on every kind, `size` on a question or a task, `due` and `after` on a task; `--note "…"` appends why to the body under the date | `flow set task-0001 size small`, `flow set goal-0001 summary "…" --note "the owner: …"` |
| ref | a record's references: `+X` adds one, `-Y` removes one, any record in any state | `flow ref task-0001 +question-0002 -idea-0004` |
| serves | an open question's goals and directions: `+G` adds an open one, `-D` removes one | `flow serves question-0001 +goal-0001 -direction-0002` |
| tag | a record's tags after its mint: `+T` adds one, `-T` removes one, the rest kept | `flow tag task-0001 +upkeep -research` |
| note | a file's text appended to a record's body under today's date, through the record's write; no field changes | `flow note task-0001 --body FILE` |

A record may be parked and blocked at once: parked is by decision, a thing not worked on on purpose; blocked is by an obstacle, a thing waited on.
A task waiting on the person's decision is parked with a reason naming the decision, and the person's answer is the unpark note and a log entry; a decision is no card and no kind.
Parking or blocking a question, propose what becomes of the tasks that reference it: those of a parked question are usually parked with it, while a blocked question may have tasks that go on.

Blocked is calculated, never marked: a record is blocked while an item of its `blocked_by.on` holds, and is not once none does, and a blocker reopened blocks again.
An item is one of three kinds, told apart exactly: a task's or a question's id, which holds until that record is settled (done, aborted, removed, answered, wrong or impossible); a date written alone, `YYYY-MM-DD`, which holds until that day; and anything else, words, which hold until removed by hand (`flow unblock T --on "…"`).
Words that mention a date are words: a date waited on is an item of its own.
`block` refuses an item that would never hold, a record already settled or a date not after today, refuses an item written as `YYYY-MM-DD` that is no day of the calendar (`2026-02-30`), which would otherwise be read as words, and refuses a second block while the first holds; a block that no longer holds is replaced.
`draw` reads the day, and clears a block none of whose items holds; `flow find --blocked` lists the records whose block holds today, `flow state` names a date waited on that has passed, and the index, which never reads the day, leaves out a record item that is settled and lists dates and words as written.
`unblock` is for words and for a mistake, never needed because a blocker closed.

`flow set` changes the fields a record's prose owner may change at any time; a `summary` set appends `summary set; it read: OLD` to the body under the date, with `. N` where `--note N` says why, so what a goal or a question stated stays in the record; on the other fields `--note N` appends `FIELD set: N`.
A field that went before this model is refused with its way: words for the body go in with `flow note`, links with `flow ref` and `flow serves`, a hand-off and a conjecture with `flow tag`.
`flow ref` and `flow serves` take `flow tag`'s refusals: no change given, one entry both added and removed, an entry removed that is not held, an entry added that is held; `flow ref` also refuses to remove the last card a consumed idea lists, the way out being `flow reopen IDEA` first.

Views: `flow find --type task --state ready` (also `--form`, a finding's evidence form, repeatable, a finding listed when it carries every form given, with `--only` those whose evidence carries no other, `flow find --form stated --only` being the findings resting on `stated` alone, `--tag`, `--owner`, `--refers ID|PATH`, the records naming a record or a repository path by any link, an evidence item, a `source` that is a path of the tree or a body link, with `--deep` the records naming those and so on, `--parked`, `--blocked`, `--held`, `--ranked`, `--id ID`, and `--grep PATTERN`, a case-insensitive regular expression over the whole record; a removed record is left out unless asked for by `--state removed` or `--id`), `flow show ID` (the record, its links by field and its back-references, `blocked_by` for the records among a block's items), `flow graph --from ID` (each link an edge labelled by its field, `consumed_by` left out as the mirror of a reference; `--dot` for Graphviz), `flow state` (the cold-start bundle; `--from N` continues it, `--budget N` bounds it; `--check` is the freeze's check, below), `flow directions` (the open directions as the owner's list), `flow tags` (every tag with its records, then the untagged; `--type` narrows), `flow artifacts` (every repository path the records refer to, by evidence, body link or a `source` that is a path, with the records naming each and whether it is in the tree), `flow touched` (below), `flow index` (`--print` to stdout, `--check` for drift), `flow check`, `flow doctor` (below).
`flow --help` lists every command, `flow <command> --help` its flags, and neither needs a bindings file.
The global flags are `--json` (any command emits one JSON object), `--root DIR` (the project, found upward from the working directory otherwise) and `--today DATE`; `flow pages` prints the page manifest the `dashboard` skill renders.
A `--body FILE` or `--resolution FILE` takes a file, never inline text (`--body "words…"` is refused as a file not found), so a long body is drafted first and checked by the project's text gates — its own checks on prose, such as a linter or a line rule; `-` reads it from the standard input, so a one-off body needs no scratch file (`printf '…\n' | flow idea SUMMARY --body -`), and `flow log add -` reads an entry the same way.
A transition that closes a ranked record closes the ranks up, and prints each record so moved as `re-ranked ID N → M`, never as changed; `flow rank --set` prints each record it placed as `ranked ID N` and each it cleared as `unranked ID (was N)`, under `--json` beside `changed` the lists `ranked` and `unranked`.

## Invariants the validator enforces

- Every id is unique and matches its filename prefix; every id in `references` and `consumed_by` exists, `answered_by` names a finding and `serves` a goal or a direction.
- State, size and owner are legal values from `flow.toml`, and every field is the model's: a field of an older model fails, and `flow doctor` says what it reads now.
- Every finding standing has evidence, each item of a form `[evidence] forms` lists and resolved by that form's shape, no item twice; a removed finding's evidence is history and no longer resolved.
- Every open question has a last-checked date; an answered or impossible question names the one finding that settles it in `answered_by`, one value, never a task, one imported from before the flow excepted where it names none; no other question names one.
- An idea's `consumed_by` is exactly the records that name it in `references`, whatever the idea's state, and a consumed idea lists at least one.
- Every repository path a live record's body links is in the tree; one a closed or removed record links is warned of.
- What a hand holds stays within its limit; a closed task lives in the archive and an open one does not; a removed, aborted or wrong record, a removed finding, a reached or given-up goal and a closed direction carry their dated reason in `closed`, and no other record carries one.
- Parked and blocked sit on an open question or a ready task, each with its date and reason, a block with what it waits on.
- Ranks are unique and contiguous, never on a closed record.
- Every body is one sentence per line; the committed index equals a fresh render.
- Every library key a record cites is a card the library holds, where a library is bound.

The warnings, never failures: an open question whose tasks are all closed, a due date passed, a closed record's body linking a path that is gone, evidence reported unchecked.
`flow check` prints a coverage line saying which resolvers were configured, so a green says what it did not look at; on a failure it names the command that reproduces it, for a session where no skill is loaded.
`flow.py --selftest` plants one defect per code the check reports, fails when one is planted nowhere, and must stay green.

## Reading discipline

Start with `flow state`: the inbox, the due tasks, the ranked next list, the hands, the dates that have passed and the log's top entry, every line carrying its file and line.
The log is dated entries, newest first, each a level-2 heading `## YYYY-MM-DD — headline` opening with a State paragraph; `flow state` prints the whole top entry, and its State paragraph is the one a cold session trusts.
Then the generated index, which lists the ranked list with each question's `serves` and each record's waits, each owner's hand, the open goals and directions with the questions serving each, the ready work, the open, parked and blocked questions, the questions whose tasks are all closed, and the settled ones.
Locate records with `flow find` or `flow show ID`; open record files only by ID.
Never glob the record directories, and never read a record directory whole.
A session's start is the `whatsnext` skill: it reads the inbox, proposes what to make of each item, ranks under the focus the person gives, and draws.

## Writing discipline

Transitions go through `flow`.
A body is edited freely, by hand or with `flow note ID --body FILE`, which appends the file's text under today's date and needs no file name.
Every field of the front matter is written by its command — `flow set`, `flow tag`, `flow ref`, `flow serves` and the transitions — and `tags` alone also by hand.
The one record written by hand is one imported from before the flow: its whole file, with `origin: legacy`, which lets an answered question name no finding; no transition writes that value.
A body is one sentence per line, and a write that adds a markdownlint violation is reverted where markdownlint is on PATH (with the project's configuration where `flow.toml` binds one or the root keeps one, else a built-in one under which a record's `summary:` is its title).
A question's body says what counts as an answer, or points at where that is stated; a goal's body what reached means and how far out it lies; a task's body what done means.
The script reads none of these: they are the session's practice, and the summary is the one field stating a goal or a question.
A body refers to a repository path, a document, a probe, a dataset, by a Markdown link whose target is the path from the project root (`[the theorem](<papers/alpha.md#Theorem 2.1>)`, the angle brackets where the target holds a space), an absolute path or one climbing above the root by `..` being outside the tree and failing V24 as an evidence item's fails V6; a URL, a bare `#anchor` and a path in backticks are prose, so the check never fails on a guess.
The front matter is the subset of YAML the script writes: plain scalars, single-quoted strings (a quote doubled inside), double-quoted strings with escapes, `null`, `true`/`false`, integers, block lists (`- item`) and one-level maps; a hand edit stays inside that subset, and `flow check` reads every record back.
A record points at where its subject is STATED and never restates it, because the statement moves and a copy does not.
A design record is never authority: a record points at a round for its reasoning or its history, never cites it for a rule, a criterion or a method, since the criteria a round fixed bound that round alone.
Run `flow check` before committing; the project's hook runs it as well.

## An older model's records

`flow doctor` names every record and binding written in the words of a model before this one, each with what it reads now, and exits 1 where it finds one.
From v0.7.0: `derived_from` (now `references`), a question's `parent`, a task's `requires` and a finding's `depends_on` (each value added to `references`, the field dropped), a question's `direction` (added to `serves`, a list now), `blocked` (now `blocked_by`), a question's or a goal's `criterion`, a task's `dod`, a goal's `horizon`, `why_now` and `first_move` (the words appended to the body as a dated line, `DATE — criterion (moved from the field): …`, nothing written lost), a question's `kind: conjecture` (the tag `conjecture`), a task's `rider: true` (the tag `rider`), and a finding with no `state` (`standing`, with `closed: null`); a block whose `on` holds words with a date inside stays words, and a line says that a date waited on is an item written alone, printed by `flow doctor` and by `flow doctor --fix`, with or without `--all`, and carried under `--json` in the list `remarks`; it is a remark, no thing for the hand.
From the models before: `abandoned` (now `closed`, the state `removed`, or `aborted` for a task that was drawn), `decomposed` (now `open`), `kill` (the body's words, as `criterion`), a task in a question's `answered_by` (a finding settles a question: mint it with `flow finding … --ref T`), `answered_by` as a list (one value now), several findings there (one answers, the others name the question in `references`), `consumed_by` as one id (a list now), a task's or a finding's `question` field (gone: the question named in `references`), a task's `kind` (a tag now), a finding's `status` (gone: the forms of its evidence stand for it; a refuted one gains the tag `refuted`) and `paper` (gone: the document is a reference `flow find --refers PATH` groups by), an evidence item with no form (the prefix read off its shape: `formal:` for a declaration, `statistical:` for a probe, `stated:` for a statement or row), a `statistical` or `reference` item whose document anchor is no row, numbered statement or heading's anchor (checked as a `stated` item's is since v0.5.0, held to the file's existence before: the hand rewrites it, the line naming the nearest heading), a finding under a shard directory (one `findings/` directory now), a question's `direction` holding a bold name (the id of a direction record, named in `serves`), the directions file and `[paths] directions` (directions are records: `flow direction NAME --body FILE` for each bullet), `[task] kinds` and `default_kind`, the `[finding]` section, a missing `[evidence] forms`, the three manifest bindings `[evidence] manifest`, `manifest_roots` and `manifest_extension` (the manifests are `formal.toml`'s alone now: delete the lines), `question_optional_kinds`, an owner `[hand]` does not list, the `decision` kind or tag on a task not parked, and the `decision_kinds` and `decision_owners` bindings, a third hand, the directions file's `## Inbox` section, a missing inbox, a `flow.toml` with no `[kit] release`, and the fields a record lacks.
The lines come in two classes.
The mechanical ones state the exact edit — a field the record lacks, a word renamed, a state read into this model's, a link folded into `references` or `serves`, an idea's `consumed_by` given the records that name it in `references` as the fix leaves them (the missing ones appended in the ids' order), a field's words moved to the body, a kind or a rider made a tag, `status` and `paper` deleted, an evidence item prefixed by its shape, a finding moved out of a shard, a closed task moved into the archive, `answered_by` and `consumed_by` between a list and one value, a direction's name rewritten to its record's id once that record exists, an owner cleared on a ready or a closed record — and `flow doctor` counts them per class (`--all` lists each), while `flow doctor --fix` writes them in place, re-ordering each record's front matter to the schema, reflowing a body that gained a line, and refreshing the index.
The judgment ones — a task or several findings in a question's `answered_by`, an entry of an idea's `consumed_by` whose record does not name the idea (removed from the list, or the idea named in that record with `flow ref`), a decision task, the directions file's bullets, a third hand, an owner on a held record, the bindings, a missing `[kit] release` among them — are printed one per record for the hand, by `--fix` as well, and settled from their lines; `--fix` exits 1 while any is left, and no migration logic exists for them.
Then come the notes, which fail nothing: each key `flow init` writes now, set or commented, that the project's `flow.toml` has neither set nor commented (a file an earlier init wrote: `[paths] log_archive`, `[evidence] statement_words`, `[evidence] row_id`), with its default and the command that reads it, under `--json` the list `notes`.
A question a task answered keeps one hand-write: once its finding is minted (`flow finding … --ref T`), its id is written into `answered_by`, the migration's one exception to the rule above.
The order of an upgrade: move the pins and restart, then `flow doctor --fix` first, the by-hand list, `flow check`, and only then any mint, the migration's own task among them; the script promises nothing on a tree not yet fixed but the doctor, and refuses nothing on one either (`flow state` prints its line where `[kit] release` is behind, `flow check` fails V3 on each field of an older model).
The migration lands in the commit that moves the pins, since `flow-check` at the new tag fails every record-touching commit until it is done — or the intermediate commit runs with `SKIP=flow-check` and the log entry says so.

## The log, the freeze and the project's other prose

`flow log add FILE` writes the entry FILE holds at the top of the log, under its title: reflowed to one sentence per line, a bold label of at most four words ending in a period, such as `**State.**` or `**Theorem 2.1.**`, a parenthetical allowed after its words as in `**Proposition 5.3 (Jen 1990).**`, kept with its sentence, and reverted where markdownlint reports a violation the log did not have, as a record's write is.
It refuses an entry that does not open with its `## YYYY-MM-DD — headline` and its State paragraph, labelled `**State.**` or `**State (…).**` with a parenthesis of the project's, one dated after today or before the top entry, and a file holding two entries.
`flow log archive --before DATE` moves every entry dated before DATE, verbatim and newest first, into one file per month (`2026-09.md`) in the log's archive directory, merging into a month's file that exists and keeping the link definitions closing it, and leaves one line under the log's title (under its front matter where it has no title) pointing there; the top entry always stays, and an entry whose heading carries no date is refused, since the archive files an entry by its date.
The log's entries are its level-2 headings outside its front matter and its code fences, a fence closing only on a run of its own character at least as long as the one that opened it.
A link definition closing the log goes to every file whose text uses its label: it moves to the archive files where only archived entries use it, is copied where the log uses it too, and stays in the log where nothing does.
The log and its archive files are written together or not at all, and a markdownlint violation either would gain undoes both.

`flow state --check`, at the freeze, decides what a machine can see of it and prints one line per failure:

- the log's top entry is not dated today while the tree has changed since the commit of the newest committed entry — any commit since, on a shared repository another's as well;
- a record changed since that commit, and no entry from the top down to that one names its id: written out, or within a range of the same prefix and width, `finding-0015…0035` (an en dash or three dots for the ellipsis, written with no spaces around it) naming every id from 0015 to 0035; a record whose only change is its rank, which one `flow rank … --insert` gives every record below the one inserted, is not a change the entry must name.

It prints each hand's active tasks and drawn ideas for the State paragraph, and fails on none: each hand continues its own work.
An inbox holding items fails nothing, since the next session reads it.
Both parts need git and a committed log; where either is missing, the check says which part it did not decide.
`flow touched` lists the records the second part reads, those changed since the commit of the newest committed entry, each with its summary, type and state, so today's entry names them without the ids gathered by hand: `--unnamed` only those no entry names yet, `--ids` the ids alone on one line, `--since REV` since another commit, a record then named by an entry from the top down to the newest the log held at REV.
A record whose only change is its rank is left out of the list and printed on one line at the end (`re-ranked only: id, id, …`), under `--json` as `reranked_only`, and out of `--ids`; the entry does not name it.
A question `flow rank --set` only moved is re-ranked only too: the command writes an order and refreshes no `checked` date, while `flow rank ID N`, a judgment about that one record, refreshes it, and `flow checked ID …` records a read, so a question the session reviewed is named.
It exits 1 when a part fails, else 2 when a part could not be decided, so a freeze it could not see whole is never read as clean, else 0.
What it cannot see stays the session's, and it prints those steps as a checklist the freeze's report answers (under `--json` the list `session_steps`): the conversation's inventory item by item, the sweep by meaning over the documents the session's records touch, the agent's memory checked, and the gates by exit code; the `freeze` skill is the whole of it.

`flow reflow --check PATH…` holds the project's other prose to the reflow the records get: it prints each line, as file and line, that the reflow would change, skipping a front matter block, reads the Markdown files under a directory, and exits 1 on any, or 2 on a path that is not there; it runs where no `flow.toml` stands, with the built-in reflow, which leaves a sentence unsplit after the common scholarly abbreviations (`cf.`, `e.g.`, `i.e.`, `et al.`, `Prop.`, `Thm.`, `Fig.` and their like) and not after a single capital such as `Theorem A.`, and a project with other abbreviations, a journal's names for one, binds its own reflow module.
A line the reflow does not split is left as written, so a hard break's two trailing spaces are not a change, and a line it splits keeps them on its last part; a code fence is read as the log's are.
`flow reflow --as DEST DRAFT` checks a draft before it is placed: its lines the reflow would change, and the markdownlint violations it adds when appended to DEST (DEST a file or a record's id; a missing file named for an existing record is refused with that record's path, one named for a record not minted yet stands for a record's body under its front matter, and any other missing file for the draft alone), under the configuration a record's write runs with, each at the draft's own line, and never one DEST had already; it writes nothing.

## The next list

The ranked records are the schedule of the WORK, and the only one; the registry below orders the deliverables, not the work.
A session works from the top.
The list is filled or refreshed by the `whatsnext` skill, when the person asks or when it is empty, on no cadence, with no per-landing re-triage; a rank is a number alone, and why a record stands where it does goes in the log's entry for that ranking.
Nothing is ranked down or left off for lacking a route: finding the route is its first round's job.
A parked or blocked record keeps its rank, and the list marks what it waits for, so the order survives the wait.
Goals and directions bias the choice of the next moves and never order the list.
A done item clears its own rank through its transition, and the ranks below it close up, so the list stays 1..n without a hand on it.
`flow rank ID N` is a judgment about one record and sets a question's `checked` to today; `flow rank --set` writes an order and asserts no read.

## Evidence and trust

An evidence item is `form:target`: the form one of the words `[evidence] forms` lists, the target what the form takes, each resolved by the validator and by `flow finding`.
The kit ships five forms, words with no rank, and a project picks the ones it accepts at its setup and adds its own; what each means for the project is in its instructions as prose:

| Form | Example | Resolved against |
| --- | --- | --- |
| `formal` | `formal:Lib/Foo.lean#lemma_L`, or a whole module `formal:Lib/Foo.lean` | machine-checked: asked of the resolver, `formal resolve --protocol` of the `formal` plugin, which answers from the manifests `formal.toml` binds and whose rules (the module a path names, the names a declaration answers to) are its own; the flow reads no manifest |
| `statistical` | `statistical:probes/p.py`; `statistical:results/run.md#FV-1`; `statistical:results/run.md#measured-rates` | the project's own data: a self-asserting script, named with its directory, listed in the probes register the project binds (`[evidence] probes`, a Markdown table whose first column holds the file's name in backticks); or a committed result by its path, with an anchor checked as a document's is where it has one; a result too big to commit is named by its probe alone |
| `peer-reviewed` | `peer-reviewed:jen1990`, `peer-reviewed:jen1990#lemma` | a card of the reference library the project binds, by its key, an extract after `#` |
| `stated` | `stated:papers/alpha.md#Theorem 2.1`; `stated:papers/alpha.md#FV-1`; `stated:docs/adr/0003.md#decision` | the project's own word, a document of the project and an anchor in it: a table row whose first cell is the id, two or three capitals, a hyphen, then letters and digits (`\| FV-1 \|`; `[evidence] row_id` binds another pattern); a numbered statement — Theorem, Proposition, Lemma, Corollary, Definition, Remark, Fact, Conjecture or Example, then `N` or `N.M…`, found at a line start, after `**` or in a heading (`[evidence] statement_words` binds other words, a symbol such as `§` taking its number with no space); or a heading, by the anchor GitHub gives it, a repeated one numbered `-1`, `-2` |
| `reference` | `reference:https://doi.org/…` | any other source: a link, held to its form alone, or a repository path, held to its existence, a document's anchor checked as a stated item's is |

A form the project adds (`forms = […, "benchmark"]`) is held to its path's existence where its target is one, and otherwise reported unchecked, unless the project binds a resolver to it (below); a form the project did not pick is refused, and so is an item with no form.
A form whose targets another tool owns is asked of that tool, as the library is asked `keys` and never read: the flow runs the form's resolver once with every item of the form on its standard input, one JSON object `{"protocol": 1, "form": "formal", "items": [TARGET, …]}`, and reads back one, `{"protocol": 1, "items": {TARGET: {"ok": true} | {"ok": false, "why": "…"} | {"unchecked": "…"}}}`, the exit 0 whenever it answered, whatever the items say.
The flow finds the `formal` resolver first in the binding `[evidence.resolvers] formal = […]`, with or without a `formal.toml`, the whole command as a list of strings, run at the project root with a limit of 60 seconds; else, only where a `formal.toml` stands at the root, the `formal` plugin installed beside the research one (`formal resolve --protocol`); else `formal` on PATH, the hooks' environment; `formal = []` asks none.
Another prover, or a form of the project's own, binds a command that speaks the protocol under its form's word, any form but `statistical`, `peer-reviewed`, `stated` and `reference`; the targets of such a form are the resolver's, so the flow reads no path out of them (`flow artifacts` and `flow find --refers` name none) and holds the item to `form:target` and `[evidence] forms` alone.
With no resolver found, or one turned off, the form's items are reported unchecked, as `peer-reviewed` is with no library; an answer in a protocol other than 1 leaves every item unchecked with that reason; a resolver that does not answer (a nonzero exit, the limit passed, no JSON object, a target left unanswered) leaves its items unchecked at a mint and fails the check once, V6 with no record, `the resolver for formal did not answer: …`.
A declaration resolves when it exists in the manifests, whatever its row's kind, a private declaration's included: that claim is existence (`formal resolve --public` is the plugin's command for the stricter reading, run by hand over a list of names).
Whether a document may cite it is another claim, the `formal` plugin's gates' at the document row and the citation, and a finding resting on a private declaration is one no document row can cite.
A finding's trust is the set of forms its evidence carries, read and never set: the index and `flow find` show them where a status stood, a removed finding showing `removed`, and `flow find --form F` lists the findings carrying one (`--form F --form G` those carrying both, `--only` those carrying no other).
The forms give a finding's evidence a direction to improve in: a finding resting on `stated` alone (`flow find --form stated --only`) is work waiting, a proof to formalize, a probe to run, a work to cite, and `flow evidence F ITEM…` adds the evidence that raises its trust, each item resolved as at the mint.
An item whose file a later change deleted is swapped for its successor by `flow evidence F --replace OLD NEW`, OLD matched exactly as written and NEW resolved as an added item is, or removed by `flow evidence F --retire OLD --reason R`, which is refused where it would leave the finding no evidence, the check failing a finding with none; either writes a dated note into the finding's body, as `flow note` does, so the record keeps what the evidence was.
Where no resolver, register or library is found, such evidence is reported unchecked, and the coverage line of `flow check` says so: it names, for each form asked of a resolver, the route that answered (`via the formal plugin beside the research plugin`) or why none did.
Findings live in one directory, and the document a finding belongs to is a reference `flow find --refers papers/alpha.md` groups by.

## Questions in practice

On the usual path a task is made first and its finding minted after it: `flow make T --resolution FILE`, then `flow finding … --evidence … --ref T --answers Q`.
An open question whose tasks are all closed is listed as needing refine or answer: its next tasks are minted, or it is answered.
A question asks one thing, and its body says what answers it.
An open end a round finds beyond that is a question of its own, referencing the finding that exposed it (`flow question "…" --ref finding-0001`) or minted from an idea captured first (`--ref IDEA`), and is never appended to the first question's body as what stays open: a question that gathers its residues has no answer anyone can reach, and the next list can no longer rank it by how near it is to done.
A question whose parts each carry weight alone is split: at its mint, into one question per part; at answering, the part answered closes the question, and each part still open is minted on its own with a pointer to where it is stated.
A wrong or impossible question is listed by the index under "Settled, do not re-open" with its word; so is any question but a removed one tagged `do-not-reopen` (`--tag` at its mint, or `flow tag`), the person's mark for a matter that must not be asked again; a removed record is in none of the index's lists and none of its counts, listed only by `flow find --state removed` or `--id`.
Minting a question's first tasks is the commitment point: anything ready may be drawn without further approval, so mint them with that weight.
The last cheap "no" is there; most ideas should be removed, and a removal keeps its reason.
What a question takes as its answer is fixed at its mint; the probes and criteria a round fixes bind that round alone, and the `method` skill's honest-change invariants say how a target may change.
A question's body points at where the question is STATED (a document's section, a module) and never restates it.
No question is parked, ranked down or excluded for lacking a route; parking carries a dated reason, and revival triggers where they are known.
A result is registered in a document as a specific numbered statement with its rows and boundary, never as a thesis rewrite, and the finding that records it is written from the landed artifact, never from the design record that commissioned it.

## Goals and directions

A goal is a destination the project commits to, formed by the owner alone, possibly after the work has started; there may be several, one may appear while the research runs, and a goal may be absent, yet to be formed.
A direction is the way the research moves, not a boundary or a gate: the owner's dated statement of what interests them; the next moves lean toward the directions without being bound by them, a goal being the stronger pull where one is set, and the list stays open to new directions.
A goal implies its own direction, towards itself, so no direction record stands behind one; a direction needs no goal, and may produce goals along the way (`flow goal "…" --ref D`), staying open.
Both are records minted and closed on the owner's word alone, which is the skill's rule and not the script's: `flow goal SUMMARY --body FILE`, `flow reach G --reason "…"`, `flow giveup G --reason "…"`; `flow direction NAME --body FILE`, `flow drop D --reason "…"`; a session proposes them in the log entry and mints none unasked.
A question names the goals and directions it serves in `serves`, a list (`flow question … --serves ID`, `flow serves Q +G -D`), the entry added an open one, on any open question, ranked or not.
A task serves a goal only through the question it references: a task minted from no question stands alone, its link to a goal prose in its body or a reference, never read as a route.
A goal's summary is the owner's words: `flow set G summary "…" --note "…"` leaves what it read in the body, dated, with the owner's words for the change.
Reaching, giving up or dropping clears nothing on the questions: each keeps what it served, and the notice names them for the session to decide on by hand, re-ranked, served elsewhere, or left.
`flow directions` renders the open directions as the owner's list; the index lists the open goals under `Goals` and the open directions under `Directions`, each with the open questions serving it, and `whatsnext` reads its case off them: no goal and no direction, directions and no goal, a goal.

## What else a project keeps

- A LOG of dated entries, newest first, one per landing or decision, each `## YYYY-MM-DD — headline` opening with a State paragraph, the top one the paragraph a cold session trusts, written by `flow log add`; the commit message carries its headline and a pointer, never the entry; old entries are archived by month, verbatim, by `flow log archive`.
- An INBOX, `INBOX.md` at the root unless `[paths] inbox` names another, where the person leaves items between sessions and a freeze leaves a directive for the next one; the next session's `whatsnext` reads it and proposes what to make of each item, and no rule empties it at a freeze.
- Its ARTIFACTS — the papers, datasets, probes, figures and releases it makes — as repository paths the records refer to, by an evidence item or a body link, listed by `flow artifacts` from the records alone, no register to keep consistent; a stale artifact is a task, and the artifacts a project must name, the papers it targets, are in its instructions as prose.
- A REGISTRY of the deliverables — what the project produces (documents, a library, releases) and in what order they are read or shipped — the one place that order is stated; the ranked list orders the work, the registry the products.
- Optionally a reference library of the works it refers to, the `library` skill's, bound to the flow by one command.
- Optionally an annex for the artifacts it made that a recorded claim depends on and no other container owns, its front page carrying the test for what is admitted, a subdirectory made only when what fills it exists.

## What the project binds

`flow init` in an empty project writes `flow.toml` with the bindings filled in and the optional ones commented, the record directories under `records/` (`--records DIR` for another), the inbox, the log where `--log FILE` names one, and the index, and prints the paragraph the project's instructions should carry; `--force` overwrites a bindings file that exists.
`flow init --print-instructions` prints that paragraph for the bindings as they stand, the records directory and the log read from `flow.toml` where it exists, the defaults otherwise, and writes nothing and refuses nothing, so an existing instructions section is compared with it.

`flow init` writes `[kit] release`, the release the setup last brought the project to, at this script's version (read from this skill's `metadata.version`); the setup's verify step (`/research:research-init`) moves it once every step up to the installed release is taken, on the person's word, and a value that is no `vN.N.N` is refused when `flow.toml` is read.
Where it is newer than this script, the project was migrated on another machine or checkout and this plugin, or the hooks' pinned tag, is behind: every write (a transition, `init --force`, `doctor --fix`, `log add`, `index`) is refused and `flow check` reports the mismatch as a problem (exit 1), each naming both releases and the commands that move the plugin, `claude plugin marketplace update research-kit`, `claude plugin update research@research-kit --scope project` and a restart, or `prek autoupdate` for remote hooks; the reads answer, with a warning on the standard error first.
Where it is older, nothing refuses: `flow state` prints one line first, that the setup was last brought to that release and `/research:research-init` is to run, and `flow check` says nothing; a `flow.toml` without the line is a thing for `flow doctor`'s hand.
It writes two owners unless `--owner` names others: `agent`, with a hand limit of four, and `owner`, the person, with no limit (a limit of 0 is unlimited).
`flow.toml` names the record directory, the index, the archive, the inbox, the log and its archive directory (beside the log, `WORKLOG-archive/` for `WORKLOG.md`, where unbound), the id prefixes and width, the owners and their hand limits, the sizes, the evidence forms the project accepts (`[evidence] forms`, the five shipped ones as written; the setup asks the owner which to keep and which words of the project's to add), the evidence resolvers (the probes register, the anchors a document's items take, and `[evidence.resolvers]`, whose `formal` may stay unset), the reflow module and the markdownlint config, and the reference library's command, which may stay unset: with a `library.toml` at the root the flow asks the library skill installed beside this one, else `library` on PATH, and `flow check`'s coverage line says which.
The project's instructions name the log, the registry, the gates that cover the records and the archive rule, and what each evidence form means for the project.
The project's instructions also name where results are registered and what gates cover them.
