# Bringing an existing project in

A project that already keeps its research somewhere — notes, a roadmap, a to-do list, an issue list, a results table, a log, a bibliography — is set up as any other, then its material is brought into the records and the cards.
The `flow` and `library` skills define what the records and the cards are; this file says only how material that was not written for them is carried across, whatever shape it is in.

## Principles

1. **Survey before writing.**
   Read what the project keeps and where, and propose the mapping in one message: each source, what it becomes, what stays where it is.
   Nothing is written before the person's word, as with the rest of the setup.
2. **Classify by the kinds' own tests, not by the old file's labels.**
   A thing to do is a task, a thing to know is a question, a raw signal is an idea, a claim whose evidence a machine resolves is a finding.
   A claim with no such evidence is never a finding: it stays prose where it stands, or becomes the task that would earn it evidence.
   An item that fits no kind is left where it is and named in the report.
3. **Carry the open work and every finding.**
   What is open now becomes ideas, questions and tasks; work that is settled stays in the old files and in git, and a record points at it rather than copying it.
   Findings never close, so they are not the history to leave behind: every committed measurement, evaluation or result whose evidence resolves today is a finding, the oldest as well as the newest, and a survey that mints only the recent ones leaves the rest out silently.
   A finding is minted only where its evidence resolves today; a result whose evidence does not resolve stays prose, as principle 2 says.
4. **Through the tools wherever a command exists.**
   Records are made with `flow` and cards with `library`, so they are valid by construction.
   A record written by hand is only one the commands cannot express, with `origin: legacy`; an older list of works is loaded as seeded cards (`--seed`), ungraded, since no reading is claimed that nobody made.
5. **Point, never restate.**
   A record or a card names where its subject is stated — the document's section, the module, the old note — so the migration copies no statement.
6. **Remove nothing.**
   The old files stay until the person retires them, after the checks pass; the migration adds and never deletes.
7. **End with the checks.**
   `flow check` and `library check` pass, or the report names each problem that stands, beside the mapping that was applied and what was left out and why.

## What a project of measurements brings

A project whose results are Markdown tables of measured rates in its reports, with no manifest, no probes register and no row ids, earns findings the same way: the evidence is the report, named by its path and an anchor the check resolves.

- A table under a heading is cited by the heading's anchor, `statistical:reports/latency.md#measured-rates-2026-10`, the anchor GitHub gives it; a report that is one result is cited by its path alone, `statistical:reports/latency.md`.
- A table whose first column carries the project's own ids, its rounds or its runs (`A2`, `M3`, `R4`), is cited row by row once `[evidence] row_id` in `flow.toml` matches them (`row_id = "[A-Z][0-9]+"`); the default, two or three capitals, a hyphen, then letters and digits, matches none of them.
- A document that numbers its statements by words of its own ("Confirmation 3", "Law 2", "§4.2") binds them in `[evidence] statement_words`, and `stated:doc/adr/0005.md#Confirmation 3` resolves.
- A claim the reports state with no table, no anchor and no committed data behind it is no finding: it stays prose, or becomes the task that would measure it.

So "no findings at migration, the results stay in the reports" is not a start: the results stay in the reports and a finding points at each, which is what lets a question be answered by one.

A roadmap is two things the model keeps apart.
Its order of deliverables, what ships and when, is the project's registry, which stays the roadmap's and is named in the instructions; its open items are the work, which become records, ranked on the next list, the roadmap pointing at no record and no record copying it.
How the records point at the roadmap's workstreams is the project's own: the survey asks the person, and the mapping message says it (a tag per workstream, a goal for an outcome the person commits to, or nothing).
A design record that raises a question, an ADR's open point, is framed from the document itself, `flow frame --source doc/adr/0010.md --summary "…" --criterion "…"`, with no idea captured first.

## A worked survey

A project keeps `doc/ROADMAP.md` (three workstreams, C1 to C3, each a list of items with done marks), `doc/adr/` (fourteen decision records, three with open points), `reports/` (eleven reports of measured rates, tables under dated headings) and a `TODO.md` of chores.
The survey reads each and counts what it holds before proposing anything:

| Source | What it holds | What it becomes |
| --- | --- | --- |
| `doc/ROADMAP.md` | the order C1 → C3, 31 items, 19 marked done | the registry, in place; the 12 open items, each by the kinds' tests: 9 tasks, 2 questions, 1 idea, pointing at the workstreams as the person says |
| `doc/adr/` | 14 decisions, 3 with open points | the decisions stay; each open point a question framed `--source` its ADR |
| `reports/` | 11 reports, 27 measured rates under 16 headings | 27 findings, `statistical:reports/….md#heading-anchor`; 2 claims with no table stay prose |
| `TODO.md` | 8 chores, 2 done | 6 tasks tagged `upkeep`; the file retired by the person once the checks pass |
| the old log | dated notes | stays as it is; the first entry of the flow's log points at it |

The mapping goes to the person as one message, in this shape, before anything is written:

```text
The migration, proposed — nothing is written until you say so.

Registry: doc/ROADMAP.md stays the order of deliverables (C1 → C3); the instructions will name it.
Records:
- 9 tasks and 2 questions from the roadmap's 12 open items; 1 item is an idea.
  How should they point at the workstreams C1 to C3: a tag each (c1, c2, c3), a goal for one you commit to, or nothing?
  The list, one line each with the roadmap line it comes from: …
- 3 questions framed from the ADRs' open points (0005, 0010, 0014), each naming its ADR as its source.
- 27 findings from the reports, one per measured rate, each citing its report and heading; the list: …
- 6 upkeep tasks from TODO.md.
Left where they are, and why:
- 19 done roadmap items and 11 decided ADRs: settled, in git; records point at them where needed.
- 2 claims in reports/cache.md with no table behind them: no evidence resolves; proposed as one task to measure them.
Bindings: [evidence] forms = statistical, stated, reference; row_id unchanged (no table carries ids).
Goals and directions: none minted; if C3's outcome is a goal you commit to, say so and I mint it.
Then: flow check and library check, and a report of what stands.
```

Each list in the message is complete, one line per record to be minted, so the person approves or strikes items, and what is struck stays where it is.
