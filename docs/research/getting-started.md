# Getting started

A first project, step by step, as the commands the agent runs and the files they write; you never need to type them, but they show what the agent does and what a record holds.
The shell blocks below run in order in one empty directory, and the kit's tests run them exactly so.
In a project with an agent, `/research:research-init` does the setup of the first block and more; [The research setup](research-init.md) says what it probes, asks and writes.

## The records

```sh
flow init --log WORKLOG.md     # flow.toml, records/{ideas,tasks,questions,findings,goals,directions,archive} with records/INDEX.md, INBOX.md, a first log entry
library init --kept --scan records --scan WORKLOG.md --documents "papers/*.md"
flow capture "A might imply B" --source "a talk"
flow frame idea-0001 --summary "Does A imply B?" --criterion "a finite counterexample, or a proof"
flow refine question-0001 --task "prove the lemma" --task "design the route" --tag research
flow check
flow state
```

`flow init` writes two hands: `agent`, the agent's across its sessions, with a limit of four (its active tasks and the ideas drawn into it), and `owner`, the person's, with no limit (0 is unlimited); `--owner` names others.
A task has no kind: a tag says what it is, `research` for work that came from the research and `upkeep` for the project's own, any word of yours beside them, and `flow tags` reports them; a task may come from a question, an idea or another task, named in its `derived_from`, or stand alone.
It also writes `INBOX.md`, where you leave items between sessions; `flow state` prints it first, before the due tasks, the ranked list, the hands and the log's top entry.
It writes the five evidence forms a finding's items may take, `[evidence] forms` in `flow.toml`, which [The flow](flow.md) shows whole: `formal`, `statistical`, `peer-reviewed`, `stated` and `reference`; keep the ones the project accepts, add its own words, and say in the project's instructions what each means here.
Then bind the evidence resolvers in `flow.toml` where the project has them — `[evidence] manifest`, `manifest_roots` and `manifest_extension` for a declaration manifest (a text file a prover's build regenerates, one `Module.Path name` line per declaration; of the other row kinds the `formal` plugin's generator writes, the flow reads `private`, `field` and `instance` rows as declarations too and passes over `module` and `hypothesis`), `probes` for a register of self-asserting scripts.
The library needs no binding: where `library.toml` stands at the root, `flow check` asks the library skill installed beside the flow skill, else a `library` command on PATH, and its coverage line says which; `[library] command` in `flow.toml` names another command, and `command = []` asks none.
Unbound, formal, probe and peer-reviewed evidence is reported unchecked and the check's coverage line says so.

`library init --documents "papers/*.md"` binds the documents whose reference entries the library ties to cards: each entry is one line under a `## References` heading opening with the authors and the year in parentheses, as `Jen, E. (1990). *Title*. Venue.`, and an entry with no card, or with two, fails the check.
A project whose documents keep a BibTeX or numbered bibliography binds no documents and cites by key alone.
`--kept` turns on the tracked kept directory (`library/kept`) for copies nothing can fetch again; a copy there is redistributed with the repository, so it holds only what the project may redistribute, and `library keep` writes there only with `--redistributable`.

### What a record looks like

The first task the block above minted is `records/tasks/task-0001-prove-the-lemma.md`:

```markdown
---
id: task-0001
type: task
state: ready
summary: prove the lemma
derived_from:
- question-0001
requires: []
serves: null
size: null
owner: null
drawn: null
dod: null
due: null
after: null
rank: null
why_now: null
first_move: null
rider: false
parked: null
blocked: null
closed: null
origin: current
source: null
created: '2026-10-23'
tags:
- research
---
```

The front matter is what the tool owns: `state`, `derived_from`, `owner`, `drawn`, `rank`, `parked`, `blocked`, `closed` and the rest move only through a transition (`flow draw task-0001 --owner agent`, `flow make task-0001 --resolution notes.md`); `due` and `after`, a due date and what follows the task's completion, are set at the mint or with `flow set`.
The body below it is yours, one sentence per line.

### What a failed check looks like

Set the task's `state` to `active` by hand and run `flow check`:

```text
records/tasks/task-0001-prove-the-lemma.md: V9 active without an owner
records/INDEX.md: V11 records/INDEX.md is stale — run `flow index`
flow check: 4 records of the kinds idea, question, task, finding, goal, direction; 2 problem(s), 0 warning(s); evidence forms formal, statistical, peer-reviewed, stated, reference; declaration evidence via NOT CONFIGURED; probe evidence via NOT CONFIGURED; reflow via built-in; markdownlint present
library: 0 key(s) cited from 0 record(s); 0 of them excluded cards; the papers' reference entries are not read here; asked through the library skill beside this one
to reproduce: `flow check` at the project root, the flow skill's scripts/flow.py; where no skill is loaded, `pre-commit run flow-check --all-files`
```

The exit code is 1, and the first two lines are the problems, each with its code ([The flow](flow.md#the-check) lists them).
The lines after them are the coverage, which varies by machine: which resolvers were bound, whether the library answered, what was not looked at (here markdownlint was on PATH); the last names the command that reproduces the failure.

## A task closed

Set the state back to `ready`, and the work goes on from where the first block left it:

```sh
mkdir probes && printf 'assert 2 + 2 == 4\n' > probes/lemma.py   # a self-asserting script, the finding's evidence
printf 'The lemma holds, and probes/lemma.py asserts it.\n' > resolution.md
flow draw task-0001 --owner agent
flow make task-0001 --resolution resolution.md
flow remove task-0002 --reason "the lemma settles the question, so no route is left to design"
flow finding "A implies B" statistical:probes/lemma.py --from task-0001 --answers question-0001
flow check
flow state
```

`flow draw` puts the task in the agent's hand, and `flow make` closes it with its resolution.
The other task, never drawn, is removed with its reason, since the result settles the question; both tasks are now in `records/archive/`.
Then `flow finding` mints `finding-0001` from the made task, its evidence the probe in the `statistical` form, and `--answers` closes the question answered by it; a question refuses to close while a task that came from it is ready or active, so the tasks are closed first.
The finding's trust is the forms its evidence carries, here `statistical`; a proof formalized later is added with `flow evidence finding-0001 formal:Lib/Foo.lean#decl`, and evidence is never removed.
The check passes with one warning: no probes register is bound, so the probe is reported unchecked rather than resolved (`[evidence] probes` in `flow.toml` binds one, a Markdown table naming each self-asserting script).

The log is not a transition.
The entry for the result is written by the agent, or by you, in the same commit as the transitions, newest first — `flow log add entry.md` puts the file's entry at the top, reflowed and linted as a record is — and `flow state` prints the top one:

```markdown
## 2026-10-23 — A implies B

**State.** question-0001 is answered by finding-0001, asserted by probes/lemma.py; nothing is in flight.
```

### A session's start and end

With an agent, a session starts with `/research:whatsnext`, optionally with a focus (`/research:whatsnext let's focus on the proofs`): it reads the inbox and proposes what to make of each item, ranks the next list with `flow rank` under the goals you have formed and the directions you have set (`flow goal`, `flow direction`, both on your word), and draws the top work into the agent's hand; [What is next](whatsnext.md) says the rest.
It ends with `/research:freeze`, which saves what the conversation found and no record holds, runs `flow state --check` (the log's top entry dated today where the tree changed, every changed record named by an entry), the gates and a commit, and leaves one directive in the inbox for the next session where there is one; [The freeze](freeze.md) says the rest.

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
`library resolve "Stuart, A. M. and Humphries, A. R. (1996). Dynamical Systems and Numerical Analysis." --register` would have asked the online interfaces for the fields instead; [What goes online](../network.md) lists them.

## The dashboard

With the above, ask the agent for the dashboard (`/research:dashboard` in Claude Code) and open <http://127.0.0.1:8765/>.
It mounts every component installed beside it whose bindings file exists at the project root — `flow.toml` for the records, `library.toml` for the cards — and `dashboard --list` says which.
It is read-only and reads no record or card file itself: every page is the component's own command-line answer, rendered.

## The agent's instructions

Each `init` prints the paragraph the project's agent instructions (`CLAUDE.md`, `AGENTS.md`) should carry, in the project's own words: where the records are, that a state changes only through a transition, that the check runs before a commit, that the ranked list is the schedule.
The skills name no project path themselves; the bindings files do.

## An existing project

A project that already keeps its research in notes, a roadmap, a to-do list or a bibliography is set up the same way, then asked to bring that material in: "Move our notes and the reading list into research-kit."
The agent maps the material onto the records and the cards by the research-init skill's [`references/migration.md`](../../plugins/research/skills/research-init/references/migration.md), which [The research setup](research-init.md) summarizes; a record the commands cannot express is written by hand with `origin: legacy`, and an older reading list loads as seeded cards.
