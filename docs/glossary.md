# Glossary

The words the skills use, each in one line, grouped by the skill that owns them; the skill says the rest.

## The setup

- **research-init, formal-init** — the skill, one per plugin, that sets a project up: it probes, proposes, writes what is absent and nothing that exists, and reports; `/research:research-init`, `/formal:formal-init`.
- **probe** — the report `setup probe` (the research side) or `formal probe` (the prover side) prints: the environment, the project, the kit's version, the proposals and a coverage line; it writes and installs nothing.
- **required, recommended, optional** — the probe's three words for an item: without a required one the flow does not run; a recommended one is proposed; an optional one serves what the project does.

## The flow

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
- **the log** — dated entries, newest first, each opening with a State paragraph; the top one is what a cold session trusts.
- **the registry** — the one place the project's deliverables and their order are stated; the ranked list orders the work, the registry the products.
- **evidence, status** — a finding's evidence items and the status they imply: `verified` (a declaration resolves in the manifest), `stated` (a document's statement or row), `empirical` (a probe), `refuted` (a guard or a probe as counterexample); the names are the project's.
- **declaration manifest** — a text file a prover's build regenerates, one `Module.Path name` line per declaration; the evidence resolver for declarations.
- **probe** — a self-asserting script, exiting non-zero when its own checks fail, listed in the project's probes register.
- **shard** — the subdirectory of findings named after the document that registers them.
- **do-not-reopen** — a tag on a question the index lists under "Settled, do not re-open" whatever its state, so a settled matter is seen before it is asked again.
- **legacy** — the `origin` of a record imported from before the flow, the one record written by hand; it gains its kill criteria at its first round.
- **text gates** — the project's own checks on prose, such as a linter or a one-sentence-per-line rule, run on a draft before a body or a row is written.
- **coverage line** — the last line of a check, saying which resolvers it looked at, so a green says what it did not look at (also `library`).

## The library

- **card** — one file per referred work: its fields, how it was read, our notes, its extracts, its copy.
- **key** — a card's pinned name, the first author's surname and the year by default, `--key` for another; a record cites a work as `lib:<key>`.
- **register (a work)** — `library register`: a new card for a work; distinct from registering a result, below.
- **read grade** — `unread`, `skimmed`, `parts`, `full`: a claim about the reader, not the work; a resolver's answer is never a read.
- **via** — the card a work is known through when it was not read itself.
- **extract** — what a work says at a place: a locator, the words quoted or restated, the author's caveat, the rule on what may be claimed; cited as `lib:<key>#<id>`.
- **copy, kept copy, the store** — a work's file: in the ignored store with the address it can be fetched from again, or in the tracked kept directory when nothing can, where it is redistributed with the repository, so `keep` writes there only with `--redistributable`.
- **resolver** — an online interface the library asks for a work's fields: arXiv, DOI, Crossref, OpenAlex and the others `docs/network.md` lists; never asked by a check.
- **watch** — a standing look for new works citing or related to a card, run by hand, keeping what it has seen and no clock.
- **candidate** — a work a watch surfaced and nobody has registered, kept in the candidates file until it is registered or set aside.
- **seeded** — a card loaded from an older list of works rather than registered for a citation, marked so.
- **internal document** — a document of the project itself with a card of an internal kind naming its tracked file; cited by key, never from a document's reference entries.
- **reference entry** — a line of a document's `## References` section, tied to exactly one card by title, first author and year.

## The method

- **landing** — bringing a result into the record and the documents: the finding, the registration in a document, the log entry, in one change.
- **register (a result), registration** — writing a landed result into a document as a specific numbered statement with its rows and boundary; where and whether is the project's rule.
- **summary sites** — the places a result is restated in short — the headline, the abstract, the contributions, the status label, the registry — which a correction must reach as well as the detailed site.
- **status label** — the words beside a statement saying how it is established — proved, machine-checked with what stays elementary, conditional on a named hypothesis, open.
- **pricing a target** — estimating what a piece of work costs and what it changes before committing to it.
- **currency** — the quantity a bound is measured in (a description length, a count, a time); on a wall the currency may change, and the change is disclosed.
- **bill** — a bound's cost accounting: the terms that add up to what a construction pays, each held by some object and each a count or a clock.
- **wall** — a reason a formal target cannot be reached as stated, named by kind: expressivity, elaboration, missing-upstream, misstated (with a prover).
- **tree-derived figure** — a count read off the artifact (declarations, guards, modules), stated only where the project's figure check recomputes it.
- **root session** — the session that holds the conversation and writes the documents and records; the prover session is the other, with none of its context.

## The formal plugin

- **handoff, handback** — the prompt a prover session is given and the report it returns, landed only after verification at the tree.
- **commission, commissioned** — what a handoff asks the prover session to produce: the declarations named on its `Commissioned:` line, which the landing looks up in the manifests.
- **guard, guard family** — a checked expectation beside a theorem (`#guard_msgs` over `#print axioms` in Lean) that a declaration's axioms, or a named instance's value, are as stated; a family is the set of instances that pin a theorem's hypotheses as load-bearing.
- **witness, joint-satisfiability witness** — a `<theorem>_nonvacuous` declaration showing a theorem's hypotheses hold at once, commissioned beside any theorem with two or more; a theorem with none is the finding.
- **refute first** — the prover session's opening move: a bounded computation at the smallest parameters where the commissioned statement can be computed, reported either way.
- **instantiation of an existing generic** — a landed declaration that is an existing generic theorem at one instance (`mul_comm_int` under `mul_comm`), the shape a report compresses into a clause.
- **drift, drift list** — the document sites a landing makes false or stale — figures, boundaries, citations — reported verbatim by the prover session and swept by the root session.
- **read-back packet** — a landed statement with the project-local definitions it names, docstrings and comments stripped, for a reader who has not seen the document.
- **binder tiers** — VERBATIM, ADAPTER, IMPLIED, UNANCHORED: what each binder of a landed declaration is against the document's statement.
- **sink-first** — a bundle lands its composite statement, the one nothing in the bundle depends on, before its predecessors are proved.

## The dashboard

- **component** — a skill whose CLI answers `--json pages`, which the dashboard mounts.
