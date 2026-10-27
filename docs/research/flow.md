# The flow

The flow is the tool that keeps a project's research work as records: ideas, questions with kill criteria, tasks and findings whose evidence a machine resolves, one Markdown file each, moved through their states by the `flow` command.
The records, not the chat, are the memory between sessions: a session starts from a short generated summary and a ranked list of what to do next, reads records by id, and changes a state only through a transition.
The tool is `scripts/flow.py` of the [`flow`](../../plugins/research/skills/flow/SKILL.md) skill (`/research:flow` in Claude Code), one Python 3.11 file with no dependencies: the CLI, the validator, the index generator and the selftest; the skill says how to work with it, and this page is the tool itself — its commands, the files it keeps, its bindings, its check and its words.
[Flow cards](flow-cards.md) is the specification of the records, and [Getting started](getting-started.md) shows the first commands with the files they write.

## What it does

You capture an idea, frame it as a question with a kill criterion (what would settle it), split the question into tasks, and close each task with what it produced.
A finding names its evidence, such as a proved declaration or a script that asserts the result, and the check confirms that the evidence exists.
A generated index keeps a ranked list of open work with a reason for each rank, and `flow state` prints the summary a new session reads first, so the agent continues from the top of the list instead of asking where things stand.
`flow check` fails when a hand-edited state leaves a record inconsistent, when a record points to an id that does not exist, when a finding's evidence does not resolve, when a rank has no reason, or when the index is out of date; it checks that the records hold together, not who wrote them, and runs offline as a pre-commit hook.

## The commands

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
The log and the close: `flow log add FILE` writes an entry at the top of the log, `flow log archive --before DATE` moves the old ones to one file per month, and `flow state --check --owner agent` checks what a machine can see of a session's close; `flow reflow --check PATH…` holds the project's other prose to one sentence per line, and `flow reflow --as DEST DRAFT` checks a draft before it is placed.
Every command takes `--json`; `flow init` is the write behind the setup; `flow --help` lists every command and `flow <command> --help` its flags, and neither needs a bindings file.
The [skill](../../plugins/research/skills/flow/SKILL.md) names every flag, and the kit's tests hold it to the script.

## The files it keeps

The records live under the directory `flow.toml` binds (`records/` by default), one subdirectory per kind and an archive for the closed tasks; [Flow cards](flow-cards.md) specifies them.
Three files stand beside them.

`INDEX.md` is written by `flow index` and never by hand; `flow check` fails when it differs from a fresh render.
Its sections, in order: the counts by kind and state; `Next (ranked)`, each item with its direction, why now and first move, and the riders for the next hand-over; `Hand`, one subsection per owner with the active tasks it holds; `Ready`, the ready tasks that are not owner-only, by size; `Open questions`, by their checked date; `Parked questions`; `Needs refine or answer`, the decomposed questions with no task or none open; `Recent findings`; `Owner-only`, the ready and active tasks of a decision kind or under a decision owner; `Settled, do not re-open`; and `Heap`, the open ideas with the oldest listed.
`flow state` prints the cold-start bundle a session reads first — the inbox slot, the ranked list and the log's top entry — and the index is what it reads next.

`directions.md` is the owner's and is written by hand, in the form `flow init` leaves: a title, an `## Inbox` section and a `## Directions` section.
The inbox is the slot where the owner leaves items for the next session, which processes each — a record minted, an action taken — names it in the log entry and removes it; a line left there outside a comment fails `flow state --check`.
A direction is one bullet of the form `- **Name** (YYYY-MM-DD) — what interests the owner`, and a question's `direction` carries the bold name, which `flow check` holds to the file (V22); sessions propose directions in the log and mint none.

The log is bound by `[paths] log` and is not a record: its entries are level-2 headings `## YYYY-MM-DD — headline`, newest first, each opening with a `**State.**` paragraph, written by `flow log add FILE` and archived by month by `flow log archive`; the [flow](../../plugins/research/skills/flow/SKILL.md) skill says the rest.

## `flow.toml`

`flow init --log WORKLOG.md` writes the bindings file at the project root, with the bindings filled in and the optional ones commented; it is the schema, with every binding explained where it stands, and the kit's tests hold this page to what `init` writes.
The project's instructions name the log, the registry, the gates that cover the records and the archive rule; the skill names no project path itself.

```toml
# flow.toml — the flow's bindings for THIS project.  Every path is relative to this file's
# directory.  The `flow` skill reads it; the project's own instructions name the log, the
# gates and the rest.

[paths]
records = "records"                 # one file per record: ideas/ tasks/ questions/ findings/ archive/
index = "records/INDEX.md"          # generated by `flow index`; `flow check` fails on drift
archive = "records/archive"         # closed tasks move here at their closing transition
directions = "records/directions.md" # owner-owned: an `## Inbox` slot and `## Directions`
log = "WORKLOG.md"                 # the dated log whose top entry `flow state` prints
log_archive = "WORKLOG-archive"   # `flow log archive` moves the old entries here verbatim, one file per month
# reflow_module = "scripts/reflow.py"   # exports reflow_text(text): one sentence per line; built-in otherwise
# markdownlint_config = ".markdownlint.jsonc"  # a NEW violation after a write reverts it

[prefixes]
idea = "idea"
question = "question"
task = "task"
finding = "finding"
id_width = 4

[hand]
# Active tasks an owner may hold; 0 = unlimited.  `init` made the last owner named here the
# decision owner — the person the owner-only tasks go to, never ranked — but what binds is
# `decision_owners` under [task] below.
agent = 2
owner = 0

[task]
kinds = ["work", "design", "prose", "survey", "upkeep", "community", "decision"]
default_kind = "work"
question_optional_kinds = ["upkeep", "community", "decision"]   # the kinds a task may be minted in with no question
decision_kinds = ["decision"]     # owner-only work: never ranked; a decision gates a landing, never a start
decision_owners = ["owner"]   # a task of a decision kind is minted under this owner's hand; empty for none
[question]
sizes = ["small", "medium", "large"]

[finding]
# The four status roles, named as the project says them: verified needs a declaration of the
# manifest, stated a document's statement or row, empirical a probe, refuted a guard or a probe.
verified = "verified"
stated = "stated"
empirical = "empirical"
refuted = "refuted"
# Findings shard by the document that registers them (records/findings/<paper>/).
shards = []

[evidence]
# A declaration manifest: a text file listing `Module.Path name` per line (a prover library's
# declaration list is the instance); `manifest_roots` are the directories a `Path.ext#name`
# item is looked up under.  Absent, declaration evidence is unchecked and the check says so.
# manifest = ["scripts/decls.txt"]
# manifest_roots = ["src"]
# manifest_extension = "lean"   # required beside manifest: the extension the cited paths carry
# A probes register: a Markdown table whose first column names each self-asserting script.
# probes = "probes/README.md"

[library]
# The reference library, when the project has one: the command that answers `keys`.  Unset, the
# flow asks the library skill installed beside the flow skill, else `library` on PATH, either only
# where a library.toml stands at the root; `command = []` asks none.
# command = ["library"]

[index]
recent_findings = 10
oldest_ideas = 5
```

## The check

Every check exits 0 when clean, 1 when it found problems, each printed with its place, and 2 when it could not run: no bindings file at the root, or one that does not parse.
The 2 is its own code so that a hook or a CI job never reads "did not run" as "clean".
`flow reflow --check` given a file that is not there, and `flow state --check` without an owner `flow.toml` lists, exit 2 as well; `flow state --check` exits 1 when a part fails, else 2 when a part could not be decided, else 0.
Each check ends with coverage lines saying what it looked at and what it did not — which evidence resolvers were bound, whether the library answered — so a green says what it did not look at; `flow.py --selftest` plants one defect per code and fails when a code it can report is planted nowhere, and the kit's tests hold the table below to the script.

### `flow check`

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

### `flow state --check`

`flow state --check --owner O` checks what a machine can see of a session's close, O the working session's owner, and prints one line per failure, each with its file:

- the directions file's inbox holds a line outside a comment;
- an active task is held by another owner than O, a decision owner `flow.toml` names aside;
- the log's top entry is not dated today, and the tree has changed since the commit of the newest committed entry, another's commit on a shared repository included;
- a record changed since that commit, and no entry from the top down to that one names its id.

Its last line says what it checked; a part it could not decide — no inbox section, no log bound, no git, no committed entry — is named on a line of its own and is not counted as passed: with no failure, the check exits 2.
Under `--json` each failure is a problem of code `STATE`.

### `flow reflow`

`flow reflow --check PATH…` prints each line, as file and line, that the reflow would change, and `flow reflow --as DEST DRAFT` each line of the draft that the reflow would change and each markdownlint violation the draft adds appended to DEST, never one DEST had already.
Under `--json` they are problems of code `REFLOW` and `MARKDOWNLINT`; the last line says which reflow ran and whether markdownlint did.

## Words

- **record** — one Markdown file with YAML front matter and a prose body, of one of four kinds; the records, not the chat, are the memory between sessions.
- **idea** — a raw signal worth attention: one sentence and a source; most die.
- **task** — a unit of work one owner can finish within its size; closed, it moves to the archive.
- **question** — a precisely stated question or conjecture with kill criteria: what the project wants to know; `decomposed` is its state once refined into tasks.
- **finding** — a checkable claim whose evidence a machine resolves: a declaration in a manifest, a document's numbered statement or table row, or a self-asserting probe.
- **transition** — the one way a record's state changes: `capture`, `task`, `frame`, `refine`, `draw`, `return`, `make`, `abort`, `answer`, `kill`, `park`, `unpark`, `rank`, `checked`, `set`; the fields a transition owns are never edited by hand.
- **capture, frame, refine** — an idea is captured from outside; ideas are framed into a question and are then `consumed`; a question is refined into tasks, sub-questions and ideas, which is the commitment point.
- **draw, make, abort, return** — a ready task is drawn under an owner's hand; it is made (done, with its resolution) or aborted (abandoned, with a reason), or returned to ready.
- **kill** — an idea, a ready task or an open question abandoned with a dated reason, kept findable.
- **kill criteria** — what would count as an answer to a question, or what would show it not worth asking, fixed when it is framed.
- **park** — an open question set aside with a date, a reason and, where known, the triggers that revive it; never for lacking a route.
- **hand, hand limit** — the active tasks an owner holds, and how many at once `flow.toml` allows.
- **owner** — a name in `flow.toml`'s `[hand]`: the working agent and the person by default; a decision owner holds the owner-only tasks.
- **owner-only work, decision** — a task of a decision kind: what only the person can do or should decide; never ranked, and a decision gates a landing, never a start.
- **the ranked list, the next list** — the records with a rank, in `INDEX.md`: the schedule of the work, worked from the top, refreshed when the owner asks or it is empty.
- **first move, why now** — what a ranked record says: why it is ranked and what its first step is; "none yet" is a legal first move.
- **rider** — a ready or active task marked as riding the next piece of work handed to another owner; the index lists it under "Rider for the next hand-over".
- **direction** — the owner's dated statement of what interests them, in the directions file: a hint that ranks items first, never a gate.
- **the inbox** — the slot at the top of the directions file where the owner leaves mail for the next session, which processes it first and empties it.
- **the log** — dated entries, newest first, each opening with a State paragraph; the top one is what a cold session trusts; `flow log add` writes one at the top, `flow log archive` moves the old ones to one file per month.
- **the close** — the end of a session: what a machine can see of it, `flow state --check` decides — the inbox emptied, the hand, the log's date and the records it names — and the rest is the session's.
- **the registry** — the one place the project's deliverables and their order are stated; the ranked list orders the work, the registry the products.
- **evidence, status** — a finding's evidence items and the status they imply: `verified` (a declaration resolves in the manifest), `stated` (a document's statement or row), `empirical` (a probe), `refuted` (a guard or a probe as counterexample); the names are the project's.
- **declaration manifest** — a text file a prover's build regenerates, one `Module.Path name` line per declaration; the evidence resolver for declarations.
- **probe** — a self-asserting script, exiting non-zero when its own checks fail, listed in the project's probes register.
- **shard** — the subdirectory of findings named after the document that registers them.
- **do-not-reopen** — a tag on a question the index lists under "Settled, do not re-open" whatever its state, so a settled matter is seen before it is asked again.
- **legacy** — the `origin` of a record imported from before the flow, the one record written by hand; it gains its kill criteria at its first round.
- **text gates** — the project's own checks on prose, such as a linter or a one-sentence-per-line rule, run on a draft before a body or a row is written.
- **clone test** — a session is closed when a clone of the repository on another computer could continue from it; the agent's memory, the scratchpad and a running subagent do not travel.
- **annex** — an optional directory for the artifacts a recorded claim depends on that no other container owns.
- **coverage line** — the last line of a check, saying which resolvers it looked at, so a green says what it did not look at (also `library`).
