# The flow

The flow is the tool that keeps a project's research work as records: ideas, questions with a criterion, tasks and findings whose evidence a machine resolves, one Markdown file each, moved through their states by the `flow` command.
The records, not the chat, are the memory between sessions: a session starts from the inbox, a ranked list of what to do next and the log's top entry, reads records by id, and changes a state only through a transition.
The tool is `scripts/flow.py` of the [`flow`](../../plugins/research/skills/flow/SKILL.md) skill (`/research:flow` in Claude Code), one Python 3.11 file with no dependencies: the CLI, the validator, the index generator and the selftest; the skill says how to work with it, and this page is the tool itself — its commands, the files it keeps, its bindings, its check and its words.
[Flow cards](flow-cards.md) is the specification of the records, and [Getting started](getting-started.md) shows the first commands with the files they write.
A session's start and its end are two skills over these commands: [What is next](whatsnext.md) (`/research:whatsnext`) and [The freeze](freeze.md) (`/research:freeze`).

## What it does

You capture an idea, frame it as a question with a criterion (what would answer it, or show it wrong or impossible), refine the question into tasks, and close each task with its resolution.
A finding is minted after the work that produced it, names its evidence, such as a proved declaration or a script that asserts the result, and may answer the question; the check confirms that the evidence exists.
A generated index keeps a ranked list of open work with a reason for each rank and what each ranked record waits on, and `flow state` prints what a new session reads first, so the agent continues from the top of the list instead of asking where things stand.
`flow check` fails when a hand-edited state leaves a record inconsistent, when a record points to an id that does not exist, when a finding's evidence does not resolve, when a rank has no reason, or when the index is out of date; it checks that the records hold together, not who wrote them, and runs offline as a pre-commit hook.

## The commands

| Transitions | Command |
| --- | --- |
| an idea from a source, or worked out of another record | `flow capture "…" --source S`, `flow capture "…" --from idea-0001` |
| a standalone task, or one that came from a question, an idea or a task | `flow task "…" --kind upkeep`, `flow task "…" --kind work --from question-0001` |
| ideas, or one finding, into a question with its criterion | `flow frame idea-0001 --summary "…" --criterion "…"` |
| a question into tasks, sub-questions and ideas | `flow refine question-0001 --task "…" work --subq "…" "…" --idea "…"` |
| a task or an idea into a hand, and back out | `flow draw task-0001 --owner agent`, `flow return task-0001 --note "…"` |
| close a task with its resolution and follow-ups | `flow make task-0001 --resolution FILE --task "…" --question "…" "…" --idea "…"`, `flow abort task-0001 --reason "…"` |
| mint a finding, answering a question | `flow finding "…" verified Lib/Foo.lean#decl --from task-0001 --answers question-0001` |
| close a question otherwise | `flow wrong question-0001 --reason "…"`, `flow impossible question-0001 --by finding-0002` |
| an idea consumed into every card that came from it | `flow consume idea-0001` |
| drop an open idea, an open question or a ready task | `flow remove ID --reason "…"` |
| set aside by decision, wait on something | `flow park ID --reason "…" --revival "…"`, `flow unpark ID --note "…"`, `flow block ID --on question-0002 --reason "…"`, `flow unblock ID --note "…"` |
| the ranked next list | `flow rank task-0001 1 --why "…" --first-move "…"`, `--insert`, `flow rank --set ID…`, `flow rank task-0001 --clear` |
| refresh a question's checked date | `flow checked question-0001` |
| one hand-editable field | `flow set task-0001 size small`, `flow set question-0001 criterion "…"`, `flow set task-0001 rider on` |

`flow make` and `flow abort` mint no finding: a task is made first, and its finding minted after it with `flow finding … --from task-0001`, `--answers Q` where it settles a question; one finding answers a question, and a later one names it with `--from Q`.
Views: `flow state` (the cold-start bundle), `flow find` (`--type`, `--state`, `--kind`, `--status`, `--tag`, `--owner`, `--from`, `--paper`, `--requires`, `--depends-on`, `--parked`, `--blocked`, `--held`, `--ranked`, `--id`, `--grep`; `--from ID` lists the records naming ID in `derived_from`, and a removed record is left out unless `--state removed` or `--id` asks for it), `flow show ID`, `flow graph --from ID`, `flow directions`, `flow index`, `flow check`, and `flow doctor`, which names every record and binding written in an older model's words.
The log and the freeze: `flow log add FILE` writes an entry at the top of the log, `flow log archive --before DATE` moves the old ones to one file per month, and `flow state --check` checks what a machine can see of a freeze; `flow reflow --check PATH…` holds the project's other prose to one sentence per line, with no `flow.toml` needed, and `flow reflow --as DEST DRAFT` checks a draft before it is placed.
Every command takes `--json`; `flow init` is the write behind the setup; `flow --help` lists every command and `flow <command> --help` its flags, and neither needs a bindings file.
A transition that closes a ranked record renumbers the ranks below it and prints each as `re-ranked ID N → M`.
The [skill](../../plugins/research/skills/flow/SKILL.md) names every flag, and the kit's tests hold it to the script.

## The files it keeps

The records live under the directory `flow.toml` binds (`records/` by default), one subdirectory per kind and an archive for the closed tasks; [Flow cards](flow-cards.md) specifies them.
Four files stand beside them.

`INDEX.md` is written by `flow index`, and refreshed by every transition, never by hand; `flow check` fails when it differs from a fresh render.
Its sections, in order: the counts by kind and state; `Next (ranked)`, each item with its direction, why now, first move and a `waits:` line for each parking or block it carries, then the riders for the next hand-over; `Hand`, one subsection per owner with the active tasks, each with its kind, its drawn date and the ids it came from, and the ideas drawn into it; `Ready`, the ready tasks by size, with the ids each came from and its waits; `Open questions`, those neither parked nor blocked, by their checked date; `Parked or blocked questions`; `Needs refine or answer`, the open questions that tasks came from and whose every such task is closed; `Recent findings`; `Settled, do not re-open`, the wrong and impossible questions and those tagged `do-not-reopen`; and `Heap`, the open ideas in no hand, the oldest listed.
A removed record is in no list and no count; `flow find --state removed` lists it, and `flow find --id ID` opens it.

`INBOX.md` at the project root, or the file `[paths] inbox` names, is where the person leaves items between sessions and a freeze leaves one directive for the next; `flow init` writes it as a title and a comment.
No check reads it: the next session's `/research:whatsnext` proposes what to make of each item and removes the ones it acted on.

`directions.md` is the owner's and is written by hand, in the form `flow init` leaves: a title and a `## Directions` section.
A direction is one bullet of the form `- **Name** (YYYY-MM-DD) — what interests the owner`, and a question's `direction` carries the bold name, which `flow check` holds to the file (V22); sessions propose directions in the log and mint none.

The log is bound by `[paths] log` and is not a record: its entries are level-2 headings `## YYYY-MM-DD — headline`, newest first, each opening with a State paragraph labelled `**State.**` or `**State (…).**`, written by `flow log add FILE` and archived by month by `flow log archive`; the [flow](../../plugins/research/skills/flow/SKILL.md) skill says the rest.

`flow state` prints, every line with its file and line, the inbox, the index's `Next (ranked)` and `Hand` sections and the log's top entry; the index is what a session reads next.

## `flow.toml`

`flow init --log WORKLOG.md` writes the bindings file at the project root, with the bindings filled in and the optional ones commented; it is the schema, with every binding explained where it stands, and the kit's tests hold this page to what `init` writes.
It writes two hands: `agent`, the agent's across its sessions, with a limit of four, and `owner`, the person's, with none (0 is unlimited); `--owner` names others.
The project's instructions name the log, the registry, the gates that cover the records and the archive rule; the skill names no project path itself.

```toml
# flow.toml — the flow's bindings for THIS project.  Every path is relative to this file's
# directory.  The `flow` skill reads it; the project's own instructions name the log, the
# gates and the rest.

[paths]
records = "records"                 # one file per record: ideas/ tasks/ questions/ findings/ archive/
index = "records/INDEX.md"          # generated by `flow index`; `flow check` fails on drift
archive = "records/archive"         # closed tasks move here at their closing transition
directions = "records/directions.md" # owner-owned: the directions, one bullet each
inbox = "INBOX.md"                 # the person's inbox: dropped between sessions, read at the next one's start
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
# The records an owner's hand may hold at once, active tasks and ideas drawn, 0 = unlimited: two hands,
# the agent's (across sessions; a subagent works on it) and the person's.
agent = 4
owner = 0

[task]
kinds = ["work", "design", "prose", "survey", "upkeep", "community"]
default_kind = "work"
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
`flow reflow --check` given a path that is not there exits 2 as well; `flow state --check` exits 1 when a part fails, else 2 when a part could not be decided, else 0; `flow doctor` exits 1 when it names anything.
Each check ends with coverage lines saying what it looked at and what it did not — which evidence resolvers were bound, whether the library answered — so a green says what it did not look at; on a failure, `flow check` adds a line naming the command that reproduces it, for a session where no skill is loaded.
`flow.py --selftest` plants one defect per code and fails when a code it can report is planted nowhere, and the kit's tests hold the table below to the script.

### `flow check`

| Code | What it says |
| --- | --- |
| V0 | a record file cannot be read: no front matter, a value outside the subset the tool writes, a byte that is not UTF-8, or an id another file carries; the check reads the rest of the tree without it |
| V1 | the record's type is not one of the four, it has no id, or its id does not match its filename or its type's prefix |
| V2 | a reference field names an id that does not exist, or a record of the wrong type |
| V3 | a field is missing or unknown, a word of an older model among them (`flow doctor` says what it reads now), or a state, kind, size, owner, status, origin or rank is not a legal value |
| V5 | a ready task has unmet `requires` |
| V6 | a finding has no evidence, an evidence item does not resolve, or the status does not match the kinds of evidence present |
| V8 | a cycle through `derived_from`, `depends_on` or a question's `parent` |
| V9 | an active task has no owner, a ready task carries an owner or a drawn date, an idea in a hand is not open or has no drawn date, an idea in no hand has one, or an owner holds more records than its hand limit |
| V11 | the index is missing or stale — run `flow index`; or in another version's form, its records unchanged — run `flow index` once after an upgrade |
| V12 | an open question has no last-checked date |
| V13 | an open task came from a question that is not open |
| V14 | a rank on a closed record, a ranked record with no `why_now` or `first_move`, two records at one rank, or ranks that are not 1..n |
| V15 | a parking or a block not on an open question or a ready task, or without its date and reason, or a block without what it waits on |
| V16 | a current question has no criterion |
| V17 | a removed, aborted or wrong record has no dated reason in `closed`, or a record of another state carries one; a consumed idea does not list the cards it was folded into, each naming it in `derived_from`, or carries a single id in `consumed_by` instead of a list; or an idea not consumed lists one |
| V18 | an answered or impossible question does not name in `answered_by` the one finding that settles it (it names a task or a record that is not a finding, or none, which only a legacy question may), `answered_by` is a list instead of one value, or a question of another state carries one |
| V19 | a body is not one sentence per line |
| V20 | a date — `created`, `checked`, `drawn`, or that of a `parked`, `blocked` or `closed` — is not an ISO date or is in the future, or a closed task still carries an owner (its `drawn` date stays, the day its work began) |
| V21 | a record is not in its type's directory, a closed task is not in the archive, or an open one is |
| V22 | a question's direction names no bullet of the directions file |
| V23 | a record cites a library key the library does not hold, or an extract its card does not carry; or the library did not answer |

The codes are names, not a sequence: V4, V7 and V10 are unassigned.
Three warnings do not fail the check: an open question that tasks came from, all of them closed, which needs refine or answer; a record blocked on a task or a question that has closed, to unblock or re-aim; and a finding's declaration or probe evidence reported unchecked because no manifest or register is bound.

A declaration resolves when it exists in the manifest, whatever its row's kind, a private declaration's included: the flow's claim is existence.
Whether a document may cite it is another claim, the [`formal`](../formal/land.md) plugin's gates' at the document row and the citation, and a finding resting on a private declaration is one no document row can cite.

### `flow state --check`

`flow state --check` checks what a machine can see of a freeze, and prints one line per failure, each with its file:

- the log's top entry is not dated today, and the tree has changed since the commit of the newest committed entry, another's commit on a shared repository included;
- a record changed since that commit, and no entry from the top down to that one names its id.

It prints each hand's active tasks and drawn ideas first, as lines for the State paragraph, and fails on none, since each hand continues its own work; an inbox holding items fails nothing either, since the next session reads it.
Its last line says what it checked; a part it could not decide — no log bound, no git, no committed entry — is named on a line of its own and is not counted as passed: with no failure, the check exits 2.
Under `--json` each failure is a problem of code `STATE`, and the hands are a list of their own.

### `flow doctor`

`flow doctor` prints one line per thing an older model wrote, with what it reads now: a record's `abandoned` field (now `closed`) or state (now `removed`, or `aborted` for a task that was drawn), `decomposed` (now `open`), `kill` (now `criterion`), a task or several findings in a question's `answered_by`, `answered_by` written as a list (now one value), `consumed_by` written as one id (now a list), a task's or a finding's `question` field (it goes, and the question is added to `derived_from` where it is not there, unless the question names that finding as its answer), a task of the `decision` kind, an owner or a drawn date on a ready task, an owner `[hand]` does not list on a task or an idea, a field the record lacks; the `decision_kinds`, `decision_owners` and `question_optional_kinds` bindings of `[task]`, `decision` among the kinds, a third hand, the directions file's `## Inbox` section and a missing inbox.
There is no migration logic: each file is edited by hand from its line, then `flow index` and `flow check` run.
Under `--json` each line is a problem of code `DOCTOR`.

### `flow reflow`

`flow reflow --check PATH…` prints each line, as file and line, that the reflow would change, and `flow reflow --as DEST DRAFT` each line of the draft that the reflow would change and each markdownlint violation the draft adds appended to DEST, never one DEST had already.
Under `--json` they are problems of code `REFLOW` and `MARKDOWNLINT`; the last line says which reflow ran and whether markdownlint did.

## Words

- **record** — one Markdown file with YAML front matter and a prose body, of one of four kinds; the records, not the chat, are the memory between sessions.
- **idea** — a thought worth keeping that is not yet a question: no criterion, no route; one thing, not a basket; drawn into a hand and worked, it produces cards that name it in `derived_from`, until it is consumed into them or removed.
- **task** — a unit of work one owner can finish within its size; it names what it came from — a question, an idea, another task — in `derived_from`, or stands alone; closed — done, aborted or removed — it moves to the archive.
- **question** — what the project has to answer to move the research, or a conjecture, with a criterion; it closes answered, wrong, impossible or removed, and that it was refined is read from the tasks that came from it, not from a state.
- **finding** — a checkable claim whose evidence a machine resolves: a declaration in a manifest, a document's numbered statement or table row, or a self-asserting probe; it never closes.
- **transition** — the one way a record's state changes: `capture`, `task`, `frame`, `refine`, `draw`, `return`, `make`, `abort`, `finding`, `consume`, `remove`, `wrong`, `impossible`, `park`, `unpark`, `block`, `unblock`, `rank`, `checked`, `set`; the fields a transition owns are never edited by hand.
- **capture, frame, refine** — an idea is captured from outside or from a record it was worked out of; ideas are framed into a question and are then `consumed`; a question is refined into tasks, sub-questions and ideas, which is the commitment point.
- **draw, return, make, abort** — a ready task or an open idea is drawn into an owner's hand; a task is made (done, with its resolution) or aborted (with its dated reason), or either is returned out of the hand.
- **criterion** — what would answer a question, or show it wrong or impossible, fixed when it is framed.
- **answered, wrong, impossible** — a question settled by the one finding minted `--answers` it; shown stated incorrectly, with a reason; shown unanswerable by a finding; wrong and impossible ones are listed under "Settled, do not re-open".
- **remove** — an open idea, an open question or a ready task dropped with a dated reason in `closed`; its card is kept, opened by its id, and in no list or count of the index.
- **park, block** — an open question or a ready task set aside by decision, with a date, a reason and revival triggers where known, or waiting on a task, a question or a condition in words; both may hold at once, the rank stays, and the lists mark the wait; never for lacking a route.
- **hand, hand limit** — what an owner holds, its active tasks and drawn ideas, and how many at once `flow.toml`'s `[hand]` allows; the agent's spans its sessions, and the person's is the other; a task handed to a prover's session stays active in the agent's hand, and the handoff's log entry says it is with the prover.
- **owner** — a name in `[hand]`: `agent` and `owner`, the person, by default.
- **the ranked list, the next list** — the records with a rank, in `INDEX.md`: the schedule of the work, worked from the top, refreshed by `/research:whatsnext` when the person asks or it is empty.
- **first move, why now** — what a ranked record says: why it is ranked and what its first step is; "none yet" is a legal first move.
- **rider** — a ready or active task marked as riding the next piece of work handed to another session; the index lists it under "Rider for the next hand-over".
- **direction** — the owner's dated statement of what interests them, in the directions file: a lean on the next moves, never a gate and never an order.
- **the inbox** — `INBOX.md`, where the person leaves items between sessions and a freeze leaves one directive; the next session reads it first, and no rule empties it at a freeze.
- **the log** — dated entries, newest first, each opening with a State paragraph; the top one is what a cold session trusts; `flow log add` writes one at the top, `flow log archive` moves the old ones to one file per month.
- **the freeze** — a session's end: what a machine can see of it, `flow state --check` decides — the log's date and the records it names — and the rest is the session's, `/research:freeze`.
- **the registry** — the one place the project's deliverables and their order are stated; the ranked list orders the work, the registry the products.
- **evidence, status** — a finding's evidence items and the status they imply: `verified` (a declaration resolves in the manifest), `stated` (a document's statement or row), `empirical` (a probe), `refuted` (a guard or a probe as counterexample); the names are the project's.
- **declaration manifest** — a text file a prover's build regenerates, one `Module.Path name` line per declaration; the evidence resolver for declarations, whose claim is existence, not citability.
- **probe** — a self-asserting script, exiting non-zero when its own checks fail, listed in the project's probes register.
- **shard** — the subdirectory of findings named after the document that registers them.
- **do-not-reopen** — a tag on a question the index lists under "Settled, do not re-open", so a settled matter is seen before it is asked again.
- **legacy** — the `origin` of a record imported from before the flow, the one record written by hand; it gains its criterion at its first round.
- **text gates** — the project's own checks on prose, such as a linter or a one-sentence-per-line rule, run on a draft before a body or a row is written.
- **clone test** — a session is frozen when a clone of the repository on another computer could continue from it; the agent's memory, the scratchpad and a running subagent do not travel.
- **annex** — an optional directory for the artifacts a recorded claim depends on that no other container owns.
- **coverage line** — the last line of a check, saying which resolvers it looked at, so a green says what it did not look at (also `library`).
