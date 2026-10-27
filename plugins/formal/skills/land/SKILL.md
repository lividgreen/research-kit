---
name: land
description: Land a prover session's handback — verify the report at the tree (the manifest diff with `formal handback`, a cold read-back of every landed statement from a packet `formal readback` builds, the binders tiered, the guards), sweep the drift the landing caused, write the document's rows and the registration from the LANDED proof, close the records and commit with named paths. Use whenever a prover session reports back, whether the agent or the owner's own session.
license: Apache-2.0
compatibility: Python 3.11 or later, standard library only, for `scripts/formal.py` (`formal probe`, `init`, `check`, `handoffcheck`, `handback`, `readback`, `cite`, `anchors`, `register`, `hypotheses`, `witnesses`); git for the manifest diff; the prover, its build and the manifest generator `scripts/DeclManifest.lean` (Lean 4; another prover writes the same rows its own way) are the project's. Needs `formal.toml` at the project root, which `formal init` writes.
metadata:
  version: "0.2.1"
  script: scripts/formal.py
---

# Landing a handback

The prover session left its work UNCOMMITTED by design and handed back a report; the report is a claim about the tree, and every step below reads the tree rather than the report.
The tool is `scripts/formal.py` beside this file, run by its path from the project root (`python3 ${CLAUDE_PLUGIN_ROOT}/skills/land/scripts/formal.py …` under Claude Code; `formal …` below means it), reading `formal.toml` at the project root: the workspace, the prover session's instructions, the declaration manifests, the library roots with their package directories, the documents whose cited names and anchors are read, what ships and the register it never carries, the handoff's bans.
`formal init --workspace DIR` writes the bindings file with every binding explained, `[packages]`, the manifests and their commands filled from the workspace's lakefiles (`--force` overwrites one that exists); `formal check` says the manifests parse and the bindings resolve, and, with `[packages]` bound, that the manifests' modules are the tree's, that each root's umbrella `<Root>.lean` imports every module under `<Root>/` and nothing absent (`umbrellas = false` where a project's umbrella leaves modules out on purpose), and that no module imports one of a later package of `package_order`; it ends with a coverage line.
`formal probe` reports the workspaces under the root with their roots and toolchains, the tools on PATH, the project's bindings and what the prover side's setup is missing, writing nothing (`--json` for the same as data); the `formal-init` skill reads it.

## 1. `formal handback --handoff DRAFT` — read the WHOLE manifest diff, not the names the report lists

Against HEAD (or `--base REV`) it prints:

- the new public and new private declarations, the removals, the visibility flips, the field changes and the per-module count deltas;
- the INSTANTIATIONS of an existing generic (`mul_comm_int` under `mul_comm`) — the shape a report compresses into one clause and a document boundary turns on;
- the joint-satisfiability witnesses owed: new public theorems with two or more named conditions and no `_nonvacuous` sibling — named conditions only, so count the binders yourself for the rest;
- the guard delta in the workspace diff, untracked files included;
- every document site citing a declaration of a touched module, classed as a row, a boundary paragraph or prose;
- the COMMISSION — every name of the handoff's `Commissioned:` line sorted into landed, already at base, and ABSENT.

Everything the report names must be there; everything the diff shows that the report omits is the surplus that makes a document boundary stale.
It exits 1 on a document citing a name that is now private or removed.
It reads no proof: a `sorry`, an `admit`, a `native_decide` or a new `axiom` is the build's warnings and the project's `#print axioms` guards to catch, so quote both in the landing.
Name each ABSENT commissioned declaration in the log entry under what did not land, whatever the report says.
Each manifest is compared with the edited modules of its own package only, so regenerating one package's manifest does not refuse on another's, and an edited umbrella that holds only imports and guards needs no regeneration; a proof-only edit elsewhere still does, since the text cannot tell it from a changed statement.

`formal hypotheses` fails where a public theorem shipped at HEAD (`--base REV`) gained a named condition, and reports the new theorems, the discharges and the theorems gone; against a pinned `--baseline FILE` instead, which lists every public declaration with its conditions (`-` for none), `--update` locks a discharge and a new declaration in and never a growth.
A manifest with no `hypothesis` row is INERT, reported as such and never as a pass.
`formal witnesses` lists, by module, every public theorem with two or more named conditions and no `_nonvacuous` sibling over the whole tree (`--base REV` for those new since it): the sweep's view of what step 1 prints for a landing, a report that fails nothing.

## 2. Read-back BEFORE reading at the binders — a cold reader writes each landed statement out from the Lean alone

The root session opens a declaration with the document already in mind, and that is the condition under which quantifier gaps survive an audit.
So first `formal readback <every commissioned declaration> -o PACKET` builds the packet: each statement with its modifiers and scope lines, every project-local definition it names to depth two (`--depth N` for another), docstrings and comments STRIPPED, its own limits in its header; a bare name declared in two modules is refused as ambiguous and named by module instead.
Then one fresh subagent, given the packet and nothing else — no document, no record, no other source file — writes out in plain prose what each declaration literally asserts: every binder and its role, the conclusion exactly as strong as written, what is NOT claimed; "as defined elsewhere" where a name has no definition in the packet.
Where the packet is too large for one cold reader, build one per commissioned declaration (`formal readback NAME -o PACKET` each) and give each its own fresh subagent; a subagent never reads two halves of one statement.
Compare that prose to the document's statement sentence by sentence and quantifier by quantifier, and record the verdict per declaration in the log entry, quoting any mismatch verbatim.
A mismatch is resolved by changing the ROW or sending the statement back — never by reading the document into the Lean.

## 3. Open every commissioned declaration at its binders, and TIER every binder

The manifest resolves a NAME; the statement behind it is read in the source — quantifiers, hypotheses, what is existential and what is universal, the guard's own axiom line — copied from the file, never from the report and never from the design record that commissioned it.
Every binder is one of four tiers: VERBATIM (the document's statement carries it); ADAPTER (an encoding the document has no counterpart for — a typeclass instance, a decidability, finiteness or measurability witness, a carrier's encoding; the packet's instance-binder line is where this tier starts, not where it ends); IMPLIED (a regularity the document assumes globally and states once); UNANCHORED (a proof-route convenience with no counterpart).
"Implied" is never the sole justification for a binder that changes the statement's strength, and an UNANCHORED binder is not written into the document's statement as mathematics until the landing has said why it is there.
Guards commissioned together — one refuting instance per hypothesis, described in parallel — are read one by one, each at its own statement, since parallel prose is not evidence of parallel binders: whether its witness is in the statement or only built in the proof (an `∃` over worlds names none), at which stage or parameters it is stated, and whether it proves a value or only a bound; each row is written from its own guard.
A theorem under a hypothesis A and a guard refuting it under a condition B make an "exactly when" only where B is literally not-A: put the two conditions side by side before any threshold or two-sided sentence, since a guard shows a hypothesis cannot be deleted, not that it is sharp.

## 4. The gates over the tree

`formal check`, then the three gates over what the landing touched, each with its bindings in `formal.toml` and each exiting 1 with every site named:

- `formal cite`: every declaration name a scanned document backticks resolves in the manifests — a cited `X.lean` is a module, a name qualified under a namespace of the manifests is exactly a declaration or a field, a name scoped under a declaration ends a manifest name, and any other declaration-shaped name resolves against the modules its own line names, then by its last component or a dotted suffix, then as a module or a namespace, then against `[documents]`' allowlists (`upstream`, `notation`, `open_targets`, `retired`, `ambiguous_namespaces`); one resolving only to private declarations, a retired name still in the manifests and an API-docs link (`docs_url`) to a module not in the tree drift.
  It reads a name as cited whatever the sentence says of it, so a document never names a declaration to say it is absent;
- `formal anchors`: every `[Key] §N` (each endpoint of a chain), `[Key] Theorem N.M` (the kind matching, abbreviations read whole) and `[Key] Appendix X` in the files of `[anchors] scan` names a numbered heading, a bold numbered statement or an appendix heading of the document the key is bound to, with no fallback from a heading to a same-numbered statement, and a statement riding a section anchor lies in that section; bare keys are counted as the frontier.
  An anchor that resolves may still name a section other than the one meant;
- `formal register`: the tracked files under `[register] ship`, minus `exclude`, carry none of the bound pattern classes — internal vocabulary, case-sensitive tags, stage forms, private paths, a package naming nothing above it by `scope` — each line matched after the `sanctioned` expressions are cut from it, so an internal tag beside a sanctioned word still fails; an empty scope fails as rot, since what ships carries zero internal register: a docstring renders into the public API docs.

Where the project states tree-derived figures (guard totals, module counts), run its check, quote the drift list and sweep every site it names; write the new TOTAL, never a delta.

## 5. Register by the project's test, then write the rows and the registration from the LANDED proof

Whether and where a landed result enters a document is the project's rule, read from its instructions, and where it has none the `method` skill's register test under Documents; the `method` skill's honest-change invariants hold where the statement moved.
A row cites the file and the bare declaration name, never a private name, and never names a declaration to say it does not exist; its boundary paragraph names each ADAPTER binder as such and each UNANCHORED binder with the landing's reason; a theorem with two or more hypotheses cites its `_nonvacuous` witness, or says the witness is owed.
A sentence saying a result is the first in any prover is checked by one prior-art search per ingredient, never one search for the whole.
Draft the rows in a scratch file and run the project's text gates on the draft before writing them.

## 6. Sweep the SUMMARY sites, not just the detailed ones

The recurring failure is a qualifier carried in the row and dropped at the headline: the statement's status label, the main results, the abstract, the contributions, the settled-and-open lists, the boundary paragraph of an EARLIER row that named this one as the gap, an earlier row that stated its boundary by POINTING at this one's, the not-formalized list, the registry's per-document line, the companion prose, the proof paragraph's "the only named hypothesis is X", which goes false when a clause consumes another; and every negative-coverage sentence about the landed result's KIND, in every document ("no statement in this series…", "nothing here relates…", "stays open"), found by grepping for the kind's words, since no gate reads them.
If any part stays conditional, the STATUS LABEL carries it.
A sentence found false of the tree is corrected here, in this landing — never put to the owner as a decision, unless the project's instructions say the owner is asked before any correction, in which case it is put to them with its evidence.

## 7. Gates, records, commit

The project's offline gates by exit code; then the flow: `flow make TASK --finding "…" <verified status> <Path.lean#decl> <document row> --resolution DRAFT` closes the prover's task, archives it, clears its rank and mints each finding from the LANDED proof (evidence that does not resolve against the manifest or the document refuses the call); `flow answer Q --by F` closes the question a finding settles; a residue is a `frame` or a `park`, never a "what stays open" line appended to the question's body.
Commit with NAMED paths — the prover session's sources, the package files, the manifests and the documents swept — never everything at once, since a sibling's in-flight work has been swept into a mislabelled commit that way.
If the landing rewired a cross-document import, run the project's consistency audit in the same session, before the commit; if it did not, say so in the entry.

## The manifest generator

`scripts/DeclManifest.lean` beside the CLI writes a Lean package's manifest in the row grammar the CLI and `flow` read: from the workspace, after a genuine build, `lake env lean --run DeclManifest.lean --roots Root1,Root2 --out ../scripts/decls.txt`, with `--own` naming the roots whose Prop-valued definitions count as named conditions, by default every root built in the workspace's own packages — a package required by path among them, a dependency's checkout under `.lake/packages/` and the toolchain left out — and printed (the project copies the file into its workspace, once, and binds one command per package in `formal.toml`'s `generate`).
It walks the compiled environment, so it needs the build current, and its counting rule is stated in its own header: what counts as a declaration, what is a field, what is private, which binders are named conditions and which instance classes a theorem carries.
Another prover writes the same six row kinds with its own tool.
