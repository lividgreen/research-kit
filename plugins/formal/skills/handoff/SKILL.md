---
name: handoff
description: Compose a prover-session handoff prompt for the formal target(s) named — statement-first from the document's text, with the declarations quoted, a refute-first line, the bundle's shape and the witnesses commissioned — check it with `formal handoffcheck`, and dispatch it to the prover agent or emit it for the owner's own prover session. Use whenever work is handed to the prover, since Lean (or another prover's) work always ships as a checked prompt.
license: Apache-2.0
compatibility: Python 3.11 or later for the check (`scripts/formal.py` of the `land` skill); the prover and its build are the project's. Reads `formal.toml` at the project root where there is one, the default bindings otherwise.
metadata:
  version: "0.1.0"
  requires: land
---

# Handing work to the prover

A prover session has none of this conversation, so everything it needs is in the prompt, and everything the prompt decides is checked before it goes anywhere.
The prompt is composed to the shape below inside literal `<prompt session=…>` … `</prompt>` tags, whichever route it takes, checked with `formal handoffcheck DRAFT` — the `land` skill's script beside this one: `${CLAUDE_PLUGIN_ROOT}/skills/land/scripts/formal.py` under Claude Code, `../land/scripts/formal.py` from this skill's directory under any other agent — and then either dispatched to the `formal:prover` agent as it stands, the records and the commit first and the dispatch the turn's last tool call, or emitted for the owner's own prover session with nothing after the closing tag.
Which route a handoff takes is the owner's call, the agent when nothing is said.
A design round whose deliverable is a prover prompt hands over to this skill rather than writing the prompt inline, and the landing that answers it is the `land` skill.

## Sequencing

The prompt is the LAST thing in the turn: finish every tool call first — the records, the gates, the commit — then compose the prompt and end the turn with it, nothing after the closing tag.
Before writing, mint the work the prompt carries in the flow: a task under its question, drawn by the prover's owner — an owner the project adds to `flow.toml`'s `[hand]` with a limit of one and names in its instructions, so the hand holds the one handoff in flight; the `land` skill closes it — and read the records for riders — a ready task marked as riding the next handoff is carried as a trailing piece or re-pointed in the same commit, never left.

## The session attribute

`session=fresh` is the default: a new prover session, always for review- or verification-shaped work, where reading the exporting statements cold is what catches things.
`session=continue` resumes the previous session, only when iterating on the same module where its earned context (tactics tried, walls hit, approaches rejected) would otherwise be rediscovered; the body states the reason in one clause right after the title (`session=continue — <why>`).

## What a handoff never does

It assigns no work on the root's side — no document edit, no record, no packaging; the prover session reports and the root session writes.
A file the prover session must touch outside its workspace is named explicitly, which is the only override.
It restates no standing rule: the build gate, the manifest regeneration, the known traps and the report-back list live in the workspace's instructions (`formal.toml`'s `instructions`, a template in `references/workspace-instructions.md`) and load in every prover session; the prompt carries what is target-specific.
It carries none of the phrases `formal.toml` bans, and every path is relative to the workspace (`../papers/x.md`, never `papers/x.md`; never the workspace's own name as a prefix).

## Gathering, for each target

Its record (the bar it states: axiom-clean, guard, scope); the document section or row it serves, quoted enough that the prover session finds the exporting statement, since statements are designed from the document's ACTUAL text, opened, never from memory; the modules it touches; and the hypotheses of the statement drafted, counted at its binders — two or more means the joint-satisfiability witness is a commissioned item.

## The prompt's shape

1. One title line saying what the bundle is.
2. Numbered targets, each with the goal, its sources (record, document, module pointers) and its own bar.
   A target with two or more hypotheses commissions `<theorem>_nonvacuous` beside it: a witness that all hold at once — a fixed instance by default, the asymptotic form when the theorem is a bound — guarded as the guard families are; a theorem whose hypotheses cannot be met at once is the finding a witness exists to surface, and the session reports that rather than proving on.
   A bundle of more than one piece lands SINK-FIRST: the first handoff commissions the bundle's sink — the composite theorem the lemmas feed, which nothing in the bundle depends on — with every predecessor's statement as its hypotheses (each a `Prop` definition, the sink proved from them), the read-back runs on the sink at its landing, and the predecessors are then commissioned as independent fresh sessions with their binders fixed by the sink's.
   Name the pieces `Piece N` and write `Bundle shape: sink-first — sink <name>, predecessors <names>`; a bundle that cannot be sink-first says `Bundle shape: sequential — <why>`; a one-piece prompt may say `Bundle shape: single piece`.
3. Target-specific warnings only, chosen by what the work touches:
   - a construction near a known trap of the workspace's instructions: the trap, said by name;
   - a guard-adding target: drift lists are reported verbatim, never swept;
   - a refactor: what stays byte-identical (guards, public docstrings, statement texts), and that the sweep touches names, visibility and file boundaries only — a move that needs a proof to change means the boundary is wrong, and the session stops and reports it;
   - a multi-piece bundle: the docstrings name no piece of any handoff, no bundle, no landing, no session and no record;
   - a prompt naming a record as a source: this sentence verbatim — "The records named above are sources to READ, not citations: a docstring renders verbatim into the public artifact, so it cites the document's section and row ids — never a record or the log.";
   - a witness or guard at a named object: a public statement cannot name a private declaration, so the object is made public rather than the statement weakened to an existential, and a commissioned existential pins every quantity it is about;
   - every prompt: the report names every commissioned declaration that does not land, and why.
4. The close: "Report back per <the workspace's instructions>, listing EVERY new declaration — public and private — and every instantiation of an existing generic, not only the commissioned ones."
5. A `Refute first:` line naming the smallest parameters at which the commissioned statement can be COMPUTED — the prover session's opening move is a bounded refutation attempt there, reported either way, a refutation arriving as a guard-family candidate before any proof work; a review, refactor or bump writes `Refute first: not applicable — <why>`.
6. A `Commissioned:` line listing, backticked, every declaration the prompt commissions — the targets, their witnesses, a guard family's named instances, a rename's new names — running to the next blank line; a prompt that adds no name writes `Commissioned: none — <why>`; the `land` skill looks each name up in the manifests.

## The check, before emitting

Write the draft, tags included, to a scratch file outside the repository and run `formal handoffcheck DRAFT` (with no file it reads the draft from standard input); fix what it flags and re-run to exit 0 (exit 2 means it could not check — a draft without the tags among the causes — a failure, not a pass).
It checks the decidable invariants only — the session attribute, the closing tag, the continue-reason clause, the banned phrases, the register warning, workspace-relative paths, the `Refute first:`, `Bundle shape:` and `Commissioned:` lines, the bundle-words sentence — and a pass does not replace re-reading the prompt against the current text it quotes: a prose correction invalidates any handoff built on it.
Make the prompt self-contained — the file, the exact declaration signatures, the proof strategy, the reused lemmas with their files, the guard to add — and carry the hard gate: the prover session pushes nothing anywhere.
Keep the draft until the landing: the `land` skill passes it to `formal handback --handoff DRAFT`.
