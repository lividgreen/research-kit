# research

The record side of research-kit: what a research project keeps in its own repository so that a coding agent works from it instead of from memory.
Ideas, questions, tasks and findings are Markdown records the `flow` command moves through their states; the works the project cites are cards in a library that records how far each was read; a dashboard shows both; three working rules say how the agent reviews, designs and debugs.
It needs nothing else, and the [`formal` plugin](../formal/README.md) builds on it for a project with a Lean 4 library.

In Claude Code 2.1.275 or later it installs in one step; [Install](../../docs/install.md) covers every other agent:

```text
/plugin install research --marketplace lividgreen/research-kit
```

Seven skills: four over a script each, three with no script behind them; the sections below take them one by one, with the commands each script answers.

## Records that hold

Ideas, questions, tasks and findings are Markdown files, one per item, that the `flow` command creates and moves through their states.
You capture an idea, frame it as a question with a kill criterion (what would settle it), split the question into tasks, and close each task with what it produced.
A finding names its evidence, such as a proved declaration or a script that asserts the result, and the check confirms that the evidence exists.

`flow check` fails when a hand-edited state leaves a record inconsistent (an active task with no owner, a closed one outside the archive, an answered question answered by nothing), when a record points to an id that does not exist, when a finding's evidence does not resolve, when a rank has no reason, or when the index is out of date.
It checks that the records hold together, not who wrote them: a hand edit that also writes everything its transition would passes, and shows in the diff.
It runs offline as a pre-commit hook, and its last line lists what it did not look at, so a passing check never overstates what it covered.
A generated index keeps a ranked list of open work with a reason for each rank, and `flow state` prints the summary a new session reads first, so the agent continues from the top of the list instead of asking where things stand.

### The `flow` skill and its commands

The [`flow`](skills/flow/SKILL.md) skill, `/research:flow` in Claude Code.

| Transitions | Command |
| --- | --- |
| an idea from a source | `flow capture "…" --source S` |
| a standalone task | `flow task "…" --kind upkeep` |
| ideas into a question with a kill criterion | `flow frame idea-0001 --summary "…" --kill "…"` |
| a question into tasks, sub-questions and ideas | `flow refine question-0001 --task "…" work --subq "…" "…"` |
| take a task, hand it back | `flow draw task-0001 --owner agent`, `flow return task-0001 --note "…"` |
| close a task with its resolution, findings and follow-ups | `flow make task-0001 --resolution FILE --finding "…" verified EVIDENCE`, `flow abort task-0001 --reason "…"` |
| settle a question | `flow answer question-0001 --by finding-0001`, `flow kill ID --reason "…"` |
| shelve and revive a question | `flow park question-0001 --reason "…"`, `flow unpark question-0001`, `flow checked question-0001` |
| the ranked next list | `flow rank task-0001 1 --why "…"`, `flow rank --set ID…` |
| one hand-editable field | `flow set task-0001 size small` |

Views: `flow state` (the cold-start summary), `flow find`, `flow show ID`, `flow graph --from ID`, `flow directions`, `flow index`, `flow check`.
Every command takes `--json`; `flow init` is the write behind the setup.

## A reference library that refuses an unread citation

`library` keeps one card per work the project refers to: a paper, a book, a preprint, a dataset, a piece of software.
A card records how far the work was actually read, what may be claimed from it and at which page, and what the project noted about it.
The reference list of each bound document is tied to the cards, so citing a work that has no card, or one marked unread without naming the source it is known through, fails the check.
Optional online lookups (arXiv, Crossref, OpenAlex and others) fill in the metadata, find open copies and watch for new citing work.

### The `library` skill and its commands

The [`library`](skills/library/SKILL.md) skill, `/research:library` in Claude Code.

| Offline | Command |
| --- | --- |
| a new card | `library register "Title" --kind article --author "…" --year 1990 --doi …` |
| how far it was read | `library read KEY --grade parts --what "sections 1 to 3"` |
| a dated note, an addressed extract | `library note KEY --note "…"`, `library extract KEY ID --at "Theorem 4" --quote "…"` |
| a copy obtained by hand, its pages, its text searched | `library keep KEY FILE`, `library page KEY`, `library find --text WORDS` |
| search, links, citing sites | `library find WORDS`, `library related KEY`, `library cited KEY`, `library claims`, `library entries` |
| the check and the index | `library check`, `library index` |

| Online | Command |
| --- | --- |
| a card from a reference entry, an identifier or a URL | `library resolve "ENTRY" --register`, `library resolve --url URL --register` |
| a copy, a re-check, a lost copy back | `library fetch KEY`, `library verify KEY`, `library restore` |
| works citing a card, a saved query | `library watch --add NAME --citing KEY`, `library watch`, `library candidates` |

[What goes online](../../docs/network.md) lists the hosts each online command calls; nothing else leaves the machine.

## A dashboard

`dashboard` serves the records and the cards as a read-only page on localhost: the ranked list, each record with its links and back-references, each card with its notes and extracts, and the verdicts of `flow check` and `library check`.
Every page is the answer of a command with `--json`, so the page and the command line cannot disagree.

### The `dashboard` skill

The [`dashboard`](skills/dashboard/SKILL.md) skill, `/research:dashboard` in Claude Code.
`dashboard` serves on port 8765; `--port`, `--host`, `--allow-host NAME` (another name it answers to, behind a proxy or a tunnel), `--root`, `--component CMD` (a command mounted by hand) and `--list` (what would be mounted) are its flags.

## A setup the agent proposes and you approve

`/research:research-init` inspects the project and the machine, proposes what is missing, and installs nothing without your confirmation.
It writes the bindings files, the records and the cards directories, the paragraphs for the agent's instructions file and the pre-commit hooks, then runs the checks and reports.

### The `research-init` skill

The [`research-init`](skills/research-init/SKILL.md) skill, `/research:research-init` in Claude Code; with another agent, ask it to set research-kit up in the project.
The probe behind it, the research-init skill's `scripts/setup.py probe`, writes nothing; the writes are `flow init --log WORKLOG.md` and `library init`.

## Working rules for the agent

Three skills with no script behind them, each triggered by the conversation itself.
`method` says how to review, what counts as evidence and how to change a target honestly when a wall is hit.
`design` runs a design pass before anything new is built, whenever you say "let's add X" or "what about Y".
`debug` insists on the root cause before a fix, and again before anything is called fixed.
They came out of one research project and are optional; the tools work without them.

### The `method`, `design` and `debug` skills

[`method`](skills/method/SKILL.md), [`design`](skills/design/SKILL.md) and [`debug`](skills/debug/SKILL.md), as `/research:method`, `/research:design` and `/research:debug` in Claude Code.

## The scripts

The four scripts are single Python 3.11 files in their skills' `scripts/` directories, standard library only; the agent runs them through their skills, and the pre-commit hooks run `flow check` and `library check` from a copy of their own.
A project binds them in `flow.toml` and `library.toml` at its root, which [The bindings files](../../docs/bindings.md) shows whole; the skills name no project path themselves.
The three working rules are optional: the tools neither read nor need them.
