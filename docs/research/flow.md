# The flow

The flow is the tool that keeps a project's research work as records: ideas, questions, tasks, findings whose evidence a machine resolves, the goals the owner forms and the directions they set, one Markdown file each, moved through their states by the `flow` command.
The records, not the chat, are the memory between sessions: a session starts from the inbox, a ranked list of what to do next and the log's top entry, reads records by id, and changes a state only through a transition.
The tool is `scripts/flow.py` of the [`flow`](../../plugins/research/skills/flow/SKILL.md) skill (`/research:flow` in Claude Code), one Python 3.11 file with no dependencies: the CLI, the validator, the index generator and the selftest; the skill says how to work with it, and this page is the tool itself — its commands, the files it keeps, its bindings, its check and its words.
[Flow cards](flow-cards.md) is the specification of the records, and [Getting started](getting-started.md) shows the first commands with the files they write.
A session's start and its end are two skills over these commands: [What is next](whatsnext.md) (`/research:whatsnext`) and [The freeze](freeze.md) (`/research:freeze`).

## What it does

You note an idea, mint a question from it whose body says what would answer it, mint the tasks the question needs, and close each task with its resolution.
A finding is minted after the work that produced it, names its evidence, such as a proved declaration or a script that asserts the result, and may answer the question; the check confirms that the evidence exists.
Records link to each other: every kind by `references`, the general link with no rule, and a question by `answered_by`, `blocked_by` and `serves`, an idea by `consumed_by`, each with its own.
A generated index keeps a ranked list of open work and what each ranked record waits on, and `flow state` prints what a new session reads first, so the agent continues from the top of the list instead of asking where things stand.
`flow check` fails when a hand-edited state leaves a record inconsistent, when a record links an id that does not exist, when a finding's evidence does not resolve, or when the index is out of date; it checks that the records hold together, not who wrote them, and runs offline as a pre-commit hook.

## The commands

| Transitions | Command |
| --- | --- |
| an idea, a question, a task, a finding, a goal or a direction minted, each with `--ref ID`, `--tag T`, `--source S` and `--body FILE` | `flow idea "…"`; `flow question "…" --consume idea-0001 --serves goal-0001 --size medium`; `flow task "…" --ref question-0001 --tag research --due YYYY-MM-DD --after "…"`; `flow finding "…" --evidence formal:Lib/Foo.lean#decl --ref task-0001 --answers question-0001`; `flow goal "…"`; `flow direction "Name" --body FILE` |
| a task or an idea into a hand, and back out | `flow draw task-0001 --owner agent`, `flow return task-0001 --note "…"` |
| close a task with its resolution | `flow make task-0001 --resolution FILE`, `flow abort task-0001 --reason "…"` |
| close a question, or open it again | `flow answer question-0001 --by finding-0002`, `flow impossible question-0001 --by finding-0002`, `flow wrong question-0001 --reason "…"`, `flow reopen question-0001 --reason "…"` |
| add evidence to a finding, or swap or retire an item | `flow evidence finding-0001 stated:papers/alpha.md#FV-1`, `flow evidence finding-0001 --replace OLD NEW`, `flow evidence finding-0001 --retire OLD --reason "…"` |
| a goal reached or given up, a direction dropped, on the owner's word | `flow reach goal-0001 --reason "…"`, `flow giveup goal-0001 --reason "…"`, `flow drop direction-0001 --reason "…"` |
| an idea consumed into every card that references it | `flow consume idea-0001` |
| drop an open idea, an open question, a ready task or a standing finding | `flow remove ID --reason "…"` |
| set aside by decision, wait on something | `flow park ID --reason "…" --revival "…"`, `flow unpark ID --note "…"`, `flow block ID --on question-0002 --on 2026-12-01 --on "the vendor's reply" --reason "…"`, `flow unblock ID --on "the vendor's reply" --note "…"` |
| the ranked next list | `flow rank task-0001 1`, `--insert`, `flow rank --set ID…`, `flow rank task-0001 --clear` |
| refresh an open question's checked date | `flow checked question-0001` |
| a field changed after the mint | `flow set task-0001 size small`, `flow set task-0001 due 2026-12-01`, `flow set goal-0001 summary "…" --note "…"` |
| the links changed after the mint | `flow ref task-0001 +question-0002 -idea-0004`, `flow serves question-0001 +goal-0001 -direction-0002` |
| a record's tags after its mint | `flow tag task-0001 +upkeep -research` |
| a body appended to, under the date, with no file name guessed | `flow note task-0001 --body FILE` |

Only the mints mint: `flow make` and `flow abort` close a task and mint nothing, a follow-up being `flow task "…" --ref T` after it, and a task's finding is minted after it with `flow finding … --ref task-0001`, `--answers Q` where it settles a question; both print the task's `after`, the post-done instruction, for the agent to follow.
`flow make` requires its resolution and refuses an empty one: a done task says what was done.
A question's closing is its own act, refused for no task that references it; `answer`, `impossible` and `--answers` take a standing finding and an open question, and a closed question is reopened first with `flow reopen`, which a question tagged `do-not-reopen` refuses.
Views: `flow state` (the cold-start bundle), `flow find` (`--type`, `--state`, `--form` (repeatable: a finding carrying every form given; `--only`: those carrying no other), `--tag`, `--owner`, `--refers`, `--deep`, `--parked`, `--blocked`, `--held`, `--ranked`, `--id`, `--grep`; `--refers ID|PATH` lists the records naming a record or a repository path by any link, an evidence item, a `source` that is a path of the tree or a body link, `--deep` the records naming those and so on, `--blocked` the records whose block holds today, and a removed record is left out unless `--state removed` or `--id` asks for it), `flow show ID` (its links and back-references by field), `flow graph --from ID` (each link an edge labelled by its field), `flow directions` (the open directions as the owner's list), `flow tags` (every tag with its records, then the untagged; `--type`), `flow artifacts` (every repository path the records refer to, with the records naming each and whether it is in the tree), `flow index`, `flow check`, and `flow doctor`, which names every record and binding written in an older model's words.
The log and the freeze: `flow log add FILE` writes an entry at the top of the log, `flow log archive --before DATE` moves the old ones to one file per month, `flow state --check` checks what a machine can see of a freeze, and `flow touched` lists the records changed since the log's newest committed entry, the ones today's entry names (`--unnamed`, `--ids`, `--since REV`), a record only re-ranked left out and named on a line of its own; `flow reflow --check PATH…` holds the project's other prose to one sentence per line, with no `flow.toml` needed, and `flow reflow --as DEST DRAFT` checks a draft before it is placed, DEST a file or a record's id.
Every command takes `--json`; `flow init` is the write behind the setup, and `flow init --print-instructions` prints the paragraphs for the instructions file for the bindings as they stand, writing nothing and refusing nothing; `flow --help` lists every command and `flow <command> --help` its flags, and neither needs a bindings file; a command that does not exist is answered with the nearest ones and, for a usual word such as `done` or `close`, or a command that went, `capture`, `frame` or `refine`, the way it goes.
A `--reason` is words: an empty one is refused, as an empty `--on` is.
A `--body` or `--resolution` is a file, `--body FILE`, whose text the command takes, never inline words, which are refused as a file not found; `-` reads the text from the standard input, for `flow log add -` too.
A transition that closes a ranked record renumbers the ranks below it and prints each as `re-ranked ID N → M`; `flow rank --set` prints each record it placed as `ranked ID N` and each it cleared as `unranked ID (was N)`.
The [skill](../../plugins/research/skills/flow/SKILL.md) names every flag, and the kit's tests hold it to the script.

## The notice

A transition that changes a record's state, or parks, unparks, blocks or unblocks it, prints one line under that record's `changed` line naming the records that refer to it by any link — `references`, `answered_by`, `serves`, `consumed_by` or an item of `blocked_by.on` — each with its state: `refers to it, may need a follow-up: task-0002 (ready)`.
Under `--json` it is the list `notices`, `[{"id": "question-0003", "refers": [{"id": "task-0002", "state": "ready"}]}]`, empty where there is none.
A removed record is left out, and so is one the same command minted or changed; a closed one is listed, since a finding removed as false reaches closed work.
A mint changes no state and prints none for the record it mints; a finding's evidence replaced or retired prints none.
It is printed by the command that makes the change and nowhere else: `flow state --check`, `flow touched` and `flow check` repeat none of it, and `flow show ID` lists what refers to a record for whoever looks again.
It refuses nothing, fails nothing, warns of nothing afterwards and asks for no reference to be removed: what to do with an open task whose question closed, or with the work that rested on a finding removed as false, is the session's to decide by hand.

## The files it keeps

The records live under the directory `flow.toml` binds (`records/` by default), one subdirectory per kind and an archive for the closed tasks; [Flow cards](flow-cards.md) specifies them.
Three files stand beside them.

`INDEX.md` is written by `flow index`, and refreshed by every transition, never by hand; `flow check` fails when it differs from a fresh render.
Its sections, in order: the counts by kind and state, a finding's by the forms its evidence carries; `Due`, where an open task has a due date, soonest first; `Next (ranked)`, each item by its summary, a question with what it serves and each with a `waits:` line for each parking or block it carries; `Hand`, one subsection per owner with the active tasks, each with its tags, its drawn date and its references, and the ideas drawn into it; `Goals`, where a goal is open, each by its summary with the open questions serving it; `Directions`, the open ones with their dates and the open questions serving each; `Ready`, the ready tasks by size, with their tags, their references and their waits; `Open questions`, those neither parked nor blocked, by their checked date; `Parked or blocked questions`; `Needs refine or answer`, the open questions that tasks reference and whose every such task is closed; `Recent findings`, each with its forms; `Settled, do not re-open`, the wrong and impossible questions and those tagged `do-not-reopen`; and `Heap`, the open ideas in no hand, the oldest listed.
A removed record, a finding among them, is in no list and no count; `flow find --state removed` lists it, and `flow find --id ID` opens it.
The index never reads the day, so it is the same render until a record changes: a block's item that is a record settled is left out of its wait, and a question none of whose items is left stands under `Open questions`, while a date and words are listed as written; `flow state` names a due date or a block's date that has passed, `flow check` warns of a due date, and `draw` and `flow find --blocked` read the day.

`INBOX.md` at the project root, or the file `[paths] inbox` names, is where the person leaves items between sessions and a freeze leaves one directive for the next; `flow init` writes it as a title and a comment.
No check reads it: the next session's `/research:whatsnext` proposes what to make of each item and removes the ones it acted on.

The log is bound by `[paths] log` and is not a record: its entries are level-2 headings `## YYYY-MM-DD — headline`, newest first, each opening with a State paragraph labelled `**State.**` or `**State (…).**`, written by `flow log add FILE` and archived by month by `flow log archive`; the [flow](../../plugins/research/skills/flow/SKILL.md) skill says the rest.

Directions are records, not a file: `flow directions` renders the open ones as the owner's list, `- **Name** (date, id) — the words`, from their summaries and bodies; a question's `serves` names one by its id.

`flow state` prints, every line with its file and line, the inbox, the index's `Due` (within `[index] due_within` days where that is bound, with a line counting the later ones the index lists), `Next (ranked)` and `Hand` sections, a line for each due date that has passed and each date a block waits on that has, naming what a block on several still waits on where it holds on the rest, and the log's top entry; the index is what a session reads next.
`flow artifacts` lists every repository path the records refer to — a probe, a result, a document, by an evidence item, a body link or a `source` that is a path of the tree — with the records naming each and `MISSING` where it is not in the tree: the artifacts index, generated from the records as `INDEX.md` is, with no register to keep consistent.

## `flow.toml`

`flow init --log WORKLOG.md` writes the bindings file at the project root, with the bindings filled in and the optional ones commented; it is the schema, with every binding explained where it stands, and the kit's tests hold this page to what `init` writes.
It writes two hands: `agent`, the agent's across its sessions, with a limit of four, and `owner`, the person's, with none (0 is unlimited); `--owner` names others.
It writes the five evidence forms the kit ships in `[evidence] forms`; the project keeps the ones it accepts and adds its own words, and an item of a form not listed is refused.
The project's instructions name the log, the registry, the gates that cover the records, the archive rule and what each evidence form means for the project; the skill names no project path itself.
It writes `[kit] release`, the release the setup last brought the project to, at the running plugin's version, and `--force` keeps the one the file holds; the setup's verify step moves it, on the person's word, once every step up to the installed release is taken, and the page shows it as `vX.Y.Z`.
A value that is no `vN.N.N` is refused when `flow.toml` is read.

```toml
# flow.toml — the flow's bindings for THIS project.  Every path is relative to this file's
# directory.  The `flow` skill reads it; the project's own instructions name the log, the
# gates and the rest.

[paths]
records = "records"                 # one file per record: ideas/ tasks/ questions/ findings/ goals/ directions/ archive/
index = "records/INDEX.md"          # generated by `flow index`; `flow check` fails on drift
archive = "records/archive"         # closed tasks move here at their closing transition
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
goal = "goal"
direction = "direction"
id_width = 4

[hand]
# The records an owner's hand may hold at once, active tasks and ideas drawn, 0 = unlimited: two hands,
# the agent's (across sessions; a subagent works on it) and the person's.
agent = 4
owner = 0

[question]
sizes = ["small", "medium", "large"]

[evidence]
# The forms a finding's evidence takes, each item `form:target`, the finding's trust the forms it carries.
# The kit ships five: formal (a declaration of the prover's library, machine-checked), statistical (a probe of the
# register, or a committed result by its path), peer-reviewed (a card of the library), stated (a row, a
# statement or a heading of a document of the project: its own word, the trust to raise) and reference (any
# other source, a link).  Keep the ones the project accepts and add its own words; the instructions say what
# each means here.
forms = ["formal", "statistical", "peer-reviewed", "stated", "reference"]
# What a document's anchor names beside a heading (`doc.md#its-anchor`): a numbered statement, one of these
# words then its number (`doc.md#Theorem 2.1`, `doc.md#§4.2`), and a table row, whose first cell matches
# row_id (`doc.md#FV-1`).  Unset, the words and the id shown.
# statement_words = ["Theorem", "Proposition", "Lemma", "Corollary", "Definition", "Remark", "Fact", "Conjecture", "Example"]
# row_id = "[A-Z]{2,3}-[A-Za-z0-9]+"
# A probes register: a Markdown table whose first column names each self-asserting script.
# probes = "probes/README.md"
# A form whose targets another tool owns is asked of that tool: one request on its standard input holds every item
# of the form, one answer on its standard output says each resolves or why not (the flow's page names the
# protocol).  Unset, `formal` is asked of the formal plugin installed beside the research one, else `formal` on PATH,
# either only where a formal.toml stands at the root; `formal = []` asks none.  Another prover's, or a form of the
# project's own, binds the whole command here, run at the project root.
# [evidence.resolvers]
# formal = ["formal", "resolve", "--protocol"]

[library]
# The reference library, when the project has one: the command that answers `keys`.  Unset, the
# flow asks the library skill installed beside the flow skill, else `library` on PATH, either only
# where a library.toml stands at the root; `command = []` asks none.
# command = ["library"]

[index]
recent_findings = 10
oldest_ideas = 5
# due_within = 14   # `flow state` lists the tasks due within this many days, and every passed date; unset, all

[kit]
# The research-kit release the setup last brought this project to: written by `flow init`, moved by the
# setup's verify step (`/research:research-init`) once every step up to the installed release is taken.  A flow
# script older than it refuses to write, the project having been brought further on another machine.
release = "vX.Y.Z"
```

### Evidence resolvers

An evidence item is `form:target`.
The flow resolves what it owns: a path of the tree, a document's anchor, a URL's shape, a probe of the register, a card of the library.
A form whose targets another tool owns is asked of that tool, as the library is asked `keys` and never read: `formal` evidence is asked of the `formal` plugin, and the flow reads no manifest.
It runs the form's resolver once with every item of that form on the standard input, one JSON object, and reads back one on the standard output:

```json
{"protocol": 1, "form": "formal", "items": ["Lib/Foo.lean#lemma_L", "Lib/Foo.lean"]}
{"protocol": 1, "items": {"Lib/Foo.lean#lemma_L": {"ok": true}, "Lib/Foo.lean": {"ok": false, "why": "module Lib.Foo is not in the manifest"}}}
```

Each item is the target as written after `form:`, and the answer holds one key of `items` for each target asked: `{"ok": true}`, `{"ok": false, "why": "…"}` or `{"unchecked": "…"}`, with exit 0 whenever the resolver answered, whatever the items say.
An answer in another protocol than the flow's own (the number `RESOLVER_PROTOCOL`, both scripts carrying it) leaves every item unchecked, with that reason, and is no problem.
A resolver that does not answer (a nonzero exit, the limit of 60 seconds passed, no JSON object, a target asked and not answered) leaves its items unchecked at a mint, as the library does, and `flow check` reports one problem, V6 with no record, `the resolver for formal did not answer: …`.

The `formal` resolver is found in this order, the last two only where a `formal.toml` stands at the root:

1. the binding `[evidence.resolvers] formal = […]`, the whole command as a list of strings (one string is one word), run as written at the project root; `formal = []` asks none;
2. the `formal` plugin installed beside the research one, its `skills/land/scripts/formal.py` run as `formal resolve --protocol`: next to the research plugin's directory in a checkout, in the directory of the same version beside it in Claude Code's cache, or in the `land` skill's directory beside the `flow` skill where the skills were installed flat;
3. `formal` on PATH, where the package installs it beside `flow`, which is the hooks' environment.

With none found, `formal` evidence is reported unchecked, as `peer-reviewed` is with no library, and the coverage line says which route answered or why none did.
Another prover, or a form of the project's own, binds a command that speaks the protocol under its form's word, any form but `statistical`, `peer-reviewed`, `stated` and `reference`, which the flow resolves itself.
The targets of a bound form are the resolver's, so the flow reads no path out of them (`flow artifacts` and `flow find --refers` name none) and holds the item to `form:target` and `[evidence] forms` alone.

### The release a project was brought to

`[kit] release` is a committed fact of the project, so a script on any machine reads the same answer.
The flow's script reads its own release from the `SKILL.md` beside it, or from the package the remote hooks install; a copy of the script alone has none and refuses nothing on the marker.
Where the marker is newer than the script, the project was migrated on another machine or checkout and this plugin, or this hook's pinned tag, is behind: every write (a transition, `flow init --force`, `flow doctor --fix`, `flow log add`, `flow index`) is refused and `flow check` reports the mismatch as a problem (exit 1), each naming both releases and the commands that move the plugin, `claude plugin marketplace update research-kit`, `claude plugin update research@research-kit --scope project` and a restart, or `prek autoupdate` for remote hooks; the reads answer, with a warning on the standard error first.
A remote hook's `rev` is committed, so a checkout gets the tag the migrating commit moved it to; a local hook runs the installed plugin, which refuses as above, so the commit fails with the commands.
Where the marker is older than the script, nothing refuses: `flow state` prints one line first, `the setup was last brought to vX; this is vY: run /research:research-init`, and `flow check` says nothing.
A `flow.toml` without the line, written before v0.7.0, is a thing for `flow doctor`'s hand, never mechanical, since the machine does not know which release the project stood at.

## The check

Every check exits 0 when clean, 1 when it found problems, each printed with its place, and 2 when it could not run: no bindings file at the root, or one that does not parse.
The 2 is its own code so that a hook or a CI job never reads "did not run" as "clean".
`flow reflow --check` given a path that is not there exits 2 as well; `flow state --check` exits 1 when a part fails, else 2 when a part could not be decided, else 0; `flow doctor` exits 1 when it names anything.
Each check ends with coverage lines saying what it looked at and what it did not — which route answered for each form asked of a resolver, whether the library answered — so a green says what it did not look at; on a failure, `flow check` adds a line naming the command that reproduces it, for a session where no skill is loaded.
`flow.py --selftest` plants one defect per code and fails when a code it can report is planted nowhere, and the kit's tests hold the table below to the script.

### `flow check`

| Code | What it says |
| --- | --- |
| V0 | a record file cannot be read: no front matter, a value outside the subset the tool writes, a byte that is not UTF-8, or an id another file carries; a file named for a record that reads at another path is named a stray beside that record; the check reads the rest of the tree without it |
| V1 | the record's type is not one of the six, it has no id, or its id does not match its filename or its type's prefix |
| V2 | `references` or `consumed_by` names an id that does not exist, `answered_by` names a record that is not a finding, or `serves` one that is not a goal or a direction, or is one value instead of a list |
| V3 | a field is missing or unknown, a field of an older model among them (`flow doctor` says what it reads now), or a state, a size, an owner, an origin or a rank is not a legal value |
| V6 | a finding has no evidence, an evidence item has no form or a form `[evidence] forms` does not list, does not resolve by its form's shape (a document's anchor among them: a row, a numbered statement or a heading; a path outside the tree, absolute or climbing above the root by `..`, never resolves), appears twice, or is of a form a resolver answers for and the resolver did not answer (once, with no record named: `the resolver for formal did not answer: …`) |
| V9 | an active task has no owner, a ready task carries an owner or a drawn date, an idea in a hand is not open or has no drawn date, an idea in no hand has one, or an owner holds more records than its hand limit |
| V11 | the index is missing or stale — run `flow index`; or in another version's form, its records unchanged — run `flow index` once after an upgrade |
| V12 | an open question has no last-checked date |
| V14 | a rank on a closed record, two records at one rank, or ranks that are not 1..n |
| V15 | a parking or a block not on an open question or a ready task, or without its date and reason, or a block without what it waits on, or with it as one value instead of a list |
| V17 | a removed, aborted or wrong record, a removed finding, a reached or given-up goal or a closed direction has no dated reason in `closed`, or a record of another state carries one; a consumed idea does not list the cards it was folded into, each naming it in `references`, or carries a single id in `consumed_by` instead of a list; or an idea not consumed lists one |
| V18 | an answered or impossible question does not name in `answered_by` the one finding that settles it (it names a task or a record that is not a finding, or none, which only a legacy question may), `answered_by` is a list instead of one value, or a question of another state carries one |
| V19 | a body is not one sentence per line |
| V20 | a date — `created`, `checked`, `drawn`, or that of a `parked`, `blocked_by` or `closed` — is not an ISO date or is in the future, a task's `due` is not an ISO date (it may lie ahead), or a closed task still carries an owner (its `drawn` date stays, the day its work began) |
| V21 | a record is not in its type's directory (a finding under a shard directory of an older model among them), a closed task is not in the archive, or an open one is |
| V23 | a record cites a library key the library does not hold, or an extract its card does not carry; or the library did not answer |
| V24 | a live record's body links a repository path that is not in the tree, or one outside it, absolute or climbing above the root by `..` (a Markdown link's target, root-relative; a URL, a bare anchor and a path in backticks are prose) |

The codes are names, not a sequence: V4, V5, V7, V8, V10, V13, V16 and V22 are unassigned.
No link has a cycle rule, an open task may reference a closed question, a question may serve a closed goal or direction, and a removed finding's evidence is not resolved: the notice names who refers to a record whose state changes, and the rest is the session's.
Warnings do not fail the check: an open question that tasks reference, all of them closed, which needs refine or answer; a task whose due date has passed; a closed or removed record whose body links a path that is gone; and evidence reported unchecked because no resolver, register or library is found for its form, because a resolver answered in a protocol the flow does not read, or because its form is the project's own and its target no path.

A declaration resolves when it exists in the manifests, whatever its row's kind, a private declaration's included: the flow's claim is existence, and the [`formal`](../formal/land.md) plugin's resolver answers it.
Whether a document may cite it is another claim, the [`formal`](../formal/land.md) plugin's gates' at the document row and the citation, and a finding resting on a private declaration is one no document row can cite.

### `flow state --check`

`flow state --check` checks what a machine can see of a freeze, and prints one line per failure, each with its file:

- the log's top entry is not dated today, and the tree has changed since the commit of the newest committed entry, another's commit on a shared repository included;
- a record changed since that commit, and no entry from the top down to that one names its id.

An entry names an id by writing it out, or by a range of the same prefix and digit width, `finding-0015…0035` (an en dash or three dots for the ellipsis, written with no spaces around it), which names every id of that prefix from 0015 to 0035; a range whose second number is smaller than the first, such as `finding-0035…0015`, names only the first id, which is written out.
A record whose only change since that commit is its `rank` — the front matter's other fields and their order, and the body, as the commit has them — is not a change the entry must name: one `flow rank T 7 --insert` renumbers every ranked record below the one inserted, and the session did not work on those.
A question `flow rank --set` only moved is re-ranked only too: the command writes an order and refreshes no `checked` date; `flow rank ID N`, a judgment about that one record, refreshes it, and `flow checked ID …` records a read, so a question the session reviewed is named.
`flow touched` leaves such a record out of its list and out of `--ids`, prints it on one line at the end (`re-ranked only: id, id, …`), and under `--json` lists the ids as `reranked_only`.

It prints each hand's active tasks and drawn ideas first, as lines for the State paragraph, and fails on none, since each hand continues its own work; an inbox holding items fails nothing either, since the next session reads it.
Before its last line it prints, as a checklist, the steps that are the session's own and that it cannot see: the conversation's inventory item by item, the sweep by meaning over the documents the session's records touch, the agent's memory checked, and the gates by exit code; the freeze's report answers each, and under `--json` they are the list `session_steps`.
Its last line says what it checked; a part it could not decide — no log bound, no git, no committed entry — is named on a line of its own and is not counted as passed: with no failure, the check exits 2.
Under `--json` each failure is a problem of code `STATE`, and the hands are a list of their own.

### `flow doctor`

`flow doctor` prints one line per thing an older model wrote, with what it reads now.
Of v0.7.0's model: `derived_from` (now `references`), a question's `parent`, a task's `requires` and a finding's `depends_on` (each value added to `references` where it is not there, the field dropped), a question's `direction` (added to `serves`, which becomes a list), `blocked` (now `blocked_by`; an item of words holding a date stays words, and `flow doctor` and `flow doctor --fix` print a line for each such record, with or without `--all`, saying a date waited on is an item written alone), a question's or a goal's `criterion`, a task's `dod`, a goal's `horizon`, `why_now` and `first_move` (the words appended to the body as a dated line, `DATE — criterion (moved from the field): …`, in that order, a null or an empty one dropped with no line), a question's `kind` (the tag `conjecture` where it was that), a task's `rider` (the tag `rider` where it was true), and a finding with no `state` (`standing`) or `closed` (`null`).
Of the models before it: a record's `abandoned` field (now `closed`) or state (now `removed`, or `aborted` for a task that was drawn), `decomposed` (now `open`), `kill` (the body's words, as `criterion`), a task or several findings in a question's `answered_by`, `answered_by` written as a list (now one value), `consumed_by` written as one id (now a list), a task's or a finding's `question` field (it goes, and the question is added to `references` where it is not there, unless the question names that finding as its answer), a task's `kind` (a tag now), a finding's `status` (it goes, the forms of its evidence standing for it; a refuted one gains the tag `refuted`) and `paper` (it goes; the document is a reference `flow find --refers PATH` groups by), an evidence item with no form (the prefix read off its shape: `formal:` for a declaration, `statistical:` for a probe, `stated:` for a statement or row), a `statistical` or `reference` item whose document anchor is no row, numbered statement or heading's anchor (checked as a `stated` item's is since v0.5.0; the line names the nearest heading, and the hand rewrites the item), a finding under a shard directory (one `findings/` directory now), a question's `direction` holding a bold name (the id of a direction record, named in `serves`), a task of the `decision` kind or tag that is not parked, an owner or a drawn date on a ready task, an owner `[hand]` does not list on a task or an idea, a field the record lacks; the directions file and `[paths] directions` (directions are records, `flow direction NAME --body FILE` for each bullet, which it lists), the `[task]` section's `kinds`, `default_kind`, `decision_kinds`, `decision_owners` and `question_optional_kinds`, the `[finding]` section, a missing `[evidence] forms`, the three manifest bindings `[evidence] manifest`, `manifest_roots` and `manifest_extension` (the manifests are `formal.toml`'s alone, and the lines are deleted by hand), a third hand, the directions file's `## Inbox` section, a missing inbox, and a missing `[kit] release`.
The lines are of two classes: the mechanical ones, whose line states the exact edit (a field the record lacks, a word renamed, a state read into this model's, a link folded into `references` or `serves`, a field's words moved to the body, a kind or a rider made a tag, a finding given its state, `status` and `paper` deleted, an evidence item prefixed by its shape, a finding moved out of a shard, a closed task moved into the archive, `answered_by` and `consumed_by` between a list and one value, a direction's name rewritten to its record's id once that record exists, an owner cleared on a ready or a closed record, the inbox created), and the judgment ones (a task or several findings in `answered_by`, a decision task, the directions file's bullets, a third hand, an owner on a held record, the bindings, `[kit] release` among them).
After them it prints the notes, which never fail: each key `flow init` writes now, set or commented, that the project's `flow.toml` has neither set nor commented, as an earlier init wrote it — `[paths] log_archive`, `[evidence] statement_words` and `[evidence] row_id` for a file of v0.5.0 — with the default the template carries and the command that reads it; under `--json` they are the list `notes`, and the setup probe relays their count.
`flow doctor` prints the judgment lines one per record and the mechanical classes as one line each with a count (`--all` lists each edit); `flow doctor --fix` writes every mechanical edit in place — each record's edits together, its front matter re-ordered to the schema, no lint, and the reflow only on a body a field's words were appended to — refreshes the index, and prints what it fixed by class and what is left to the hand; it exits 1 while anything is left, 0 otherwise, and a second run after the hand's part settles what the first could not (a direction's name, once its record exists).
No migration logic exists for the judgment classes: each is settled by hand from its line, then `flow check` runs; the one hand-write of a field a command owns is a migrated question's `answered_by`, once its finding is minted.
Nothing refuses on a tree not yet fixed: after an upgrade `flow doctor --fix` runs first, then the hand's part and `flow check`, and only then any mint; `flow state` prints its line where `[kit] release` is behind, and `flow check` fails V3 on each field of an older model until then.
Under `--json` the judgment lines are problems of code `DOCTOR`, the mechanical ones `mechanical` with their `class`, the counts `summary`, and what `--fix` wrote `fixed`.

### `flow reflow`

`flow reflow --check PATH…` prints each line, as file and line, that the reflow would change, and `flow reflow --as DEST DRAFT` each line of the draft that the reflow would change and each markdownlint violation the draft adds appended to DEST, never one DEST had already.
Under `--json` they are problems of code `REFLOW` and `MARKDOWNLINT`; the last line says which reflow ran and whether markdownlint did.
The built-in reflow leaves a sentence unsplit after the common scholarly abbreviations (`cf.`, `e.g.`, `i.e.`, `et al.`, `Prop.`, `Thm.`, `Fig.` and their like) but splits after a single capital, as in `Theorem A. Then it holds.`, and a project whose prose carries others, such as a journal's `Amer.` and `Math.`, binds its own reflow module, which is the escape.

## Words

- **record** — one Markdown file with YAML front matter and a prose body, of one of six kinds; the records, not the chat, are the memory between sessions.
- **idea** — a thought worth keeping that is not yet a question: nothing says what would answer it, no route; one thing, not a basket, its size its independence and not its length; drawn into a hand and worked, it produces cards that reference it, until it is consumed into them or removed.
- **task** — work that is big or must outlive the turn, which one owner finishes within its size, its body saying what done means; it references what it is connected to — a question, an idea, another task — or stands alone, and stands across the main axis, its closing never a question's; a task serves a goal only through the question it references; its tags say what it is, `research` and `upkeep` the usual ones, `rider` one riding the next hand-over; it may carry a due date and a post-done instruction; closed — done, aborted or removed — it moves to the archive.
- **question** — what the project has to answer to move the research, its body saying what counts as an answer; a conjecture is one tagged `conjecture`; it may serve goals and directions; it closes answered, wrong, impossible or removed, and is reopened by `flow reopen`.
- **finding** — a checkable claim whose evidence a machine resolves where its form allows, each item `form:target`; the forms it carries are its trust, evidence is added, and an item whose file is gone is replaced or retired with a dated note in the body; it stands until it is found false and removed.
- **goal** — a destination the owner commits to, its summary the outcome and its body what reached means and how far out it lies, formed by the owner alone, served by questions, reached or given up; it implies its own direction.
- **direction** — the way the research moves, the owner's dated statement of what interests them, a record its name the summary and the words the body; a lean on the next moves, never a gate and never an order; it may produce goals along the way, and is dropped by the owner.
- **references** — the general link, on every kind: a list of the records a record came from, rests on or is about, in any state, a removed one included; it obliges nothing, and `flow ref` changes it.
- **answered_by, blocked_by, serves, consumed_by** — the four links with a rule: the finding that settles a question; what a question or a task waits on; the goals and directions a question serves; the cards a consumed idea was folded into.
- **mint** — the one way a record comes to be, one per kind, each the kind's name: `idea`, `question`, `task`, `finding`, `goal`, `direction`.
- **transition** — a command that writes the records: the mints, `draw`, `return`, `make`, `abort`, `answer`, `impossible`, `wrong`, `reopen`, `remove`, `consume`, `evidence`, `reach`, `giveup`, `drop`, `park`, `unpark`, `block`, `unblock`, `rank`, `checked`, `set`, `ref`, `serves`, `tag`, `note`; every field of the front matter is written by its command, and `tags` alone also by hand.
- **refine** — the act of minting a question's first tasks, `flow task "…" --ref Q` for each: the commitment point.
- **draw, return, make, abort** — a ready task or an open idea is drawn into an owner's hand; a task is made (done, with its resolution) or aborted (with its dated reason), or either is returned out of the hand.
- **answered, wrong, impossible** — a question settled by the one finding that answers it; shown stated incorrectly, with a reason; shown unanswerable by a finding; wrong and impossible ones are listed under "Settled, do not re-open".
- **reopen** — a closed question back to open, its answer and its closing cleared, a dated note keeping what it was; refused on a question tagged `do-not-reopen`.
- **remove** — an open idea, an open question, a ready task or a standing finding dropped with a dated reason in `closed`; its card is kept, opened by its id, and in no list or count of the index.
- **the notice** — the line a transition prints under a record whose state it changed, or that it parked, unparked, blocked or unblocked, naming the records that refer to it; it refuses nothing.
- **park, block** — an open question or a ready task set aside by decision, with a date, a reason and revival triggers where known, or waiting on a task, a question, a date written alone or words; both may hold at once, the rank stays, and the lists mark the wait; never for lacking a route.
- **blocked** — calculated, never marked: a record is blocked while an item of its block holds, a record until it is settled, a date until that day, words until removed by hand.
- **hand, hand limit** — what an owner holds, its active tasks and drawn ideas, and how many at once `flow.toml`'s `[hand]` allows; the agent's spans its sessions, and the person's is the other; a task handed to a prover's session stays active in the agent's hand, and the handoff's log entry says it is with the prover.
- **owner** — a name in `[hand]`: `agent` and `owner`, the person, by default; the skills write those two, and the names a project's `[hand]` sets are what the commands take.
- **the ranked list, the next list** — the records with a rank, a number alone, in `INDEX.md`: the schedule of the work, worked from the top, refreshed by `/research:whatsnext` when the person asks or it is empty, why each stands where it does said in the log's entry.
- **due date, after** — a task's date, which never moves a rank: the index lists the open tasks that have one under `Due`, `flow state` names one that has passed and `flow check` warns on it; and the words that follow a task's completion, printed by `make` and `abort` for the agent to follow.
- **tag** — a free word on a record, no vocabulary validated; `flow tags` reports every one in use with its records and the untagged.
- **artifact** — a repository path a record refers to, a paper, a dataset, a probe, a figure, by an evidence item or a Markdown link in its body; `flow artifacts` lists them with the records naming each, and the check fails a live record whose path is gone; no record, no register, a stale artifact being a task.
- **the inbox** — `INBOX.md`, where the person leaves items between sessions and a freeze leaves one directive; the next session reads it first, and no rule empties it at a freeze.
- **the log** — dated entries, newest first, each opening with a State paragraph; the top one is what a cold session trusts; `flow log add` writes one at the top, `flow log archive` moves the old ones to one file per month.
- **the freeze** — a session's end: what a machine can see of it, `flow state --check` decides — the log's date and the records it names — and the rest is the session's, `/research:freeze`.
- **the registry** — the one place the project's deliverables and their order are stated; the ranked list orders the work, the registry the products.
- **evidence, form, trust** — a finding's evidence items, each `form:target`; the form one of the words `[evidence] forms` lists — the kit ships `formal` (a declaration or a module of the prover's library, asked of the resolver), `statistical` (a probe or a committed result), `peer-reviewed` (a card of the library), `stated` (a row, a numbered statement or a heading of a document of the project, its own word) and `reference` (any other source) — and the project adds its own; the set of forms a finding carries is its trust, words with no rank, and a finding resting on `stated` alone is the trust to raise.
- **declaration manifest** — a text file a prover's build regenerates, one `Module.Path name` line per declaration, in the [`formal`](../formal/land.md) plugin's grammar; the flow never reads it, and the plugin's resolver answers `formal` items from it, whose claim is existence, not citability.
- **resolver** — the command that answers for the evidence items of one form, as `formal resolve --protocol` does for `formal`; it speaks the protocol under [Evidence resolvers](#evidence-resolvers), and the flow asks it once for every item of its form.
- **probe** — a self-asserting script, exiting non-zero when its own checks fail, listed in the project's probes register; a `statistical` item.
- **do-not-reopen** — a tag on a question the index lists under "Settled, do not re-open", so a settled matter is seen before it is asked again; `flow reopen` refuses it, and the agent asks the person.
- **legacy** — the `origin` of a record imported from before the flow, the one record written by hand; an answered legacy question may name no finding.
- **text gates** — the project's own checks on prose, such as a linter or a one-sentence-per-line rule, run on a draft before a body or a row is written.
- **clone test** — a session is frozen when a clone of the repository on another computer could continue from it; the agent's memory, the scratchpad and a running subagent do not travel.
- **annex** — an optional directory for the artifacts a recorded claim depends on that no other container owns.
- **coverage line** — the last line of a check, saying which route answered for each form asked of a resolver, so a green says what it did not look at (also `library`).
