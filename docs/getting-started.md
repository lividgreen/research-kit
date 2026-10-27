# Getting started

A first project, step by step, as the commands the agent runs and the files they write; you never need to type them, but they show what the agent does and what a record holds.
The shell blocks below run in order in one empty directory, and the kit's tests run them exactly so.
In a project with an agent, `/research:research-init` does the setup of the first block and more: the [research-init](../plugins/research/skills/research-init/SKILL.md) skill probes the project and the machine, proposes what is missing and writes the bindings, the instructions and the hooks.

## The records

```sh
flow init --log WORKLOG.md     # flow.toml, records/{ideas,tasks,questions,findings,archive} with records/directions.md and records/INDEX.md, a first log entry
library init --kept --scan records --scan WORKLOG.md --documents "papers/*.md"
flow capture "A might imply B" --source "a talk"
flow frame idea-0001 --summary "Does A imply B?" --kill "a finite counterexample, or a proof"
flow refine question-0001 --task "prove the lemma" work --task "design the route" design
flow check
flow state
```

`flow init` writes two owners: `agent`, the working session, with a hand limit of two active tasks, and `owner`, the person, with no limit (0 is unlimited), who holds the decision tasks; `--owner` names others.
The task kinds it writes are `work`, `design`, `prose`, `survey`, `upkeep`, `community` and `decision`; a task of the first four stands under a question, the last three stand alone; edit the lists in `flow.toml`, which [The bindings files](bindings.md) shows whole.
Then bind the evidence resolvers in `flow.toml` where the project has them — `[evidence] manifest`, `manifest_roots` and `manifest_extension` for a declaration manifest (a text file a prover's build regenerates, one `Module.Path name` line per declaration; the flow reads those lines and passes over the other row kinds the `formal` plugin's generator writes), `probes` for a register of self-asserting scripts.
The library needs no binding: where `library.toml` stands at the root, `flow check` asks the library skill installed beside the flow skill, else a `library` command on PATH, and its coverage line says which; `[library] command` in `flow.toml` names another command, and `command = []` asks none.
Unbound, declaration and probe evidence is reported unchecked and the check's coverage line says so.

`library init --documents "papers/*.md"` binds the documents whose reference entries the library ties to cards: each entry is one line under a `## References` heading opening with the authors and the year in parentheses, as `Jen, E. (1990). *Title*. Venue.`, and an entry with no card, or with two, fails the check.
A project whose documents keep a BibTeX or numbered bibliography binds no documents and cites by key alone.
`--kept` turns on the tracked kept directory (`library/kept`) for copies nothing can fetch again; a copy there is redistributed with the repository, so it holds only what the project may redistribute, and `library keep` writes there only with `--redistributable`.

### What a record looks like

The first task the block above minted is `records/tasks/task-0001-prove-the-lemma.md`:

```markdown
---
id: task-0001
type: task
kind: work
state: ready
summary: prove the lemma
question: question-0001
derived_from:
- question-0001
requires: []
size: null
owner: null
drawn: null
dod: null
rank: null
why_now: null
first_move: null
rider: false
abandoned: null
origin: current
source: null
created: '2026-10-23'
tags: []
---
```

The front matter is what the tool owns: `state`, `owner`, `drawn`, `rank` and the rest move only through a transition (`flow draw task-0001 --owner agent`, `flow make task-0001 --resolution notes.md`).
The body below it is yours, one sentence per line.

### What a failed check looks like

Set the task's `state` to `active` by hand and run `flow check`:

```text
records/tasks/task-0001-prove-the-lemma.md: V9 active without an owner
records/INDEX.md: V11 records/INDEX.md is stale — run `flow index`
flow check: 4 records of the kinds idea, question, task, finding; 2 problem(s), 0 warning(s); declaration evidence via NOT CONFIGURED; probe evidence via NOT CONFIGURED; reflow via built-in; markdownlint present
library: 0 key(s) cited from 0 record(s); 0 of them excluded cards; the papers' reference entries are not read here; asked through the library skill beside this one
```

The first two lines are the problems; the coverage lines after them say what the check looked at and vary by machine (here markdownlint was on PATH).

The exit code is 1, each problem carries its code ([The checks](checks.md) lists them), and the last lines are the coverage: which resolvers were bound, what was not looked at.

## A task closed

Set the state back to `ready`, and the work goes on from where the first block left it:

```sh
mkdir probes && printf 'assert 2 + 2 == 4\n' > probes/lemma.py   # a self-asserting script, the finding's evidence
printf 'The lemma holds, and probes/lemma.py asserts it.\n' > resolution.md
flow draw task-0001 --owner agent
flow make task-0001 --resolution resolution.md --finding "A implies B" empirical probes/lemma.py
flow kill task-0002 --reason "the lemma settles the question, so no route is left to design"
flow answer question-0001 --by finding-0001
flow check
flow state
```

`flow draw` puts the task in the agent's hand, and `flow make` closes it with its resolution and mints `finding-0001`, whose evidence is the probe.
The other task is killed with its reason, since the result settles the question, and `flow answer` closes the question by the finding; both tasks are now in `records/archive/`.
The check passes with one warning: no probes register is bound, so the probe is reported unchecked rather than resolved (`[evidence] probes` in `flow.toml` binds one, a Markdown table naming each self-asserting script).

The log is not a transition.
The entry for the result is written by the agent, or by you, in the same commit as the transitions, newest first — `flow log add entry.md` puts the file's entry at the top, reflowed and linted as a record is — and `flow state` prints the top one:

```markdown
## 2026-10-23 — A implies B

**State.** question-0001 is answered by finding-0001, asserted by probes/lemma.py; nothing is in flight.
```

## A card

`library register "Dynamical Systems and Numerical Analysis" --kind book --author "Stuart, A. M." --author "Humphries, A. R." --year 1996 --isbn 9780521645638` writes `library/cards/stuart1996.md`:

```markdown
---
key: stuart1996
state: registered
excluded: null
kind: book
title: "Dynamical Systems and Numerical Analysis"
authors:
- "Stuart, A. M."
- "Humphries, A. R."
year: 1996
venue: null
doi: null
arxiv: null
openalex: null
zbmath: null
isbn: "9780521645638"
url: null
metadata:
  from: hand
  on: "2026-10-23"
  typed: null
verified: null
read:
  grade: unread
  on: null
  what: null
via: null
copy: null
related: []
tags: []
seeded: false
created: "2026-10-23"
---

## Notes

## Extracts
```

The read grade is a claim about the reader, not the work: it moves only through `library read`; a record's cite of an unread card is reported by grade in the check's coverage line, and a bound document's reference entry tied to an unread card fails the check unless the card names the work it is known through (`via`).
`library resolve "Stuart, A. M. and Humphries, A. R. (1996). Dynamical Systems and Numerical Analysis." --register` would have asked the online interfaces for the fields instead; [What goes online](network.md) lists them.

## The dashboard

With the above, ask the agent for the dashboard (`/research:dashboard` in Claude Code) and open <http://127.0.0.1:8765/>.
It mounts every component installed beside it whose bindings file exists at the project root — `flow.toml` for the records, `library.toml` for the cards — and `dashboard --list` says which.
It is read-only and reads no record or card file itself: every page is the component's own command-line answer, rendered.

## The agent's instructions

Each `init` prints the paragraph the project's agent instructions (`CLAUDE.md`, `AGENTS.md`) should carry, in the project's own words: where the records are, that a state changes only through a transition, that the check runs before a commit, that the ranked list is the schedule.
The skills name no project path themselves; the bindings files do.

## An existing project

A project that already keeps its research in notes, a roadmap, a to-do list or a bibliography is set up the same way, then asked to bring that material in: "Move our notes and the reading list into research-kit."
The skills already describe the records and the cards the material has to become, so the agent maps any project's shape onto them, along a few general principles in the research-init skill's [`references/migration.md`](../plugins/research/skills/research-init/references/migration.md): survey and propose before writing, classify by the kinds' own tests, carry only the open work and point at the settled, go through the commands wherever one exists — a record the commands cannot express is written by hand with `origin: legacy`, an older reading list loads as seeded cards — remove nothing, and end with both checks.
