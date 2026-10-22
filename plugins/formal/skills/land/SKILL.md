---
name: land
description: Land a prover session's handback — verify the report at the tree (the manifest diff with `formal handback`, a cold read-back of every landed statement from a packet `formal readback` builds, the binders tiered, the guards), sweep the drift the landing caused, write the document's rows and the registration from the LANDED proof, close the records and commit with named paths. Use whenever a prover session reports back, whether the agent or the owner's own session.
license: Apache-2.0
compatibility: Python 3.11 or later, standard library only, for `scripts/formal.py` (`formal probe`, `init`, `check`, `handoffcheck`, `handback`, `readback`); git for the manifest diff; the prover, its build and the manifest generator `scripts/DeclManifest.lean` (Lean 4; another prover writes the same rows its own way) are the project's. Needs `formal.toml` at the project root, which `formal init` writes.
metadata:
  version: "0.1.0"
  script: scripts/formal.py
---

# Landing a handback

The prover session left its work UNCOMMITTED by design and handed back a report; the report is a claim about the tree, and every step below reads the tree rather than the report.
The tool is `scripts/formal.py` beside this file, run by its path from the project root (`python3 ${CLAUDE_PLUGIN_ROOT}/skills/land/scripts/formal.py …` under Claude Code; `formal …` below means it), reading `formal.toml` at the project root: the workspace, the prover session's instructions, the declaration manifests, the library roots with their package directories, the documents whose cited names are read, the handoff's bans.
`formal init --workspace DIR` writes the bindings file with every binding explained (`--force` overwrites one that exists); `formal check` says the manifests parse and the bindings resolve, and ends with a coverage line.
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

## 2. Read-back BEFORE reading at the binders — a cold reader writes each landed statement out from the Lean alone

The root session opens a declaration with the document already in mind, and that is the condition under which quantifier gaps survive an audit.
So first `formal readback <every commissioned declaration> -o PACKET` builds the packet: each statement with its modifiers and scope lines, every project-local definition it names to depth two (`--depth N` for another), docstrings and comments STRIPPED, its own limits in its header; a bare name declared in two modules is refused as ambiguous and named by module instead.
Then one fresh subagent, given the packet and nothing else — no document, no record, no other source file — writes out in plain prose what each declaration literally asserts: every binder and its role, the conclusion exactly as strong as written, what is NOT claimed; "as defined elsewhere" where a name has no definition in the packet.
Compare that prose to the document's statement sentence by sentence and quantifier by quantifier, and record the verdict per declaration in the log entry, quoting any mismatch verbatim.
A mismatch is resolved by changing the ROW or sending the statement back — never by reading the document into the Lean.

## 3. Open every commissioned declaration at its binders, and TIER every binder

The manifest resolves a NAME; the statement behind it is read in the source — quantifiers, hypotheses, what is existential and what is universal, the guard's own axiom line — copied from the file, never from the report and never from the design record that commissioned it.
Every binder is one of four tiers: VERBATIM (the document's statement carries it); ADAPTER (an encoding the document has no counterpart for — a typeclass instance, a decidability, finiteness or measurability witness, a carrier's encoding; the packet's instance-binder line is where this tier starts, not where it ends); IMPLIED (a regularity the document assumes globally and states once); UNANCHORED (a proof-route convenience with no counterpart).
"Implied" is never the sole justification for a binder that changes the statement's strength, and an UNANCHORED binder is not written into the document's statement as mathematics until the landing has said why it is there.

## 4. The project's figure gate

Where the project states tree-derived figures (guard totals, module counts), run its check, quote the drift list and sweep every site it names; write the new TOTAL, never a delta.

## 5. Register by the project's test, then write the rows and the registration from the LANDED proof

Whether and where a landed result enters a document is the project's rule, read from its instructions; the `method` skill's honest-change invariants hold where the statement moved.
A row cites the file and the bare declaration name, never a private name, and never names a declaration to say it does not exist; its boundary paragraph names each ADAPTER binder as such and each UNANCHORED binder with the landing's reason; a theorem with two or more hypotheses cites its `_nonvacuous` witness, or says the witness is owed.
Draft the rows in a scratch file and run the project's text gates on the draft before writing them.

## 6. Sweep the SUMMARY sites, not just the detailed ones

The recurring failure is a qualifier carried in the row and dropped at the headline: the statement's status label, the main results, the abstract, the contributions, the settled-and-open lists, the boundary paragraph of an EARLIER row that named this one as the gap, an earlier row that stated its boundary by POINTING at this one's, the not-formalized list, the registry's per-document line, the companion prose; and every negative-coverage sentence about the landed result's KIND, in every document ("no statement in this series…", "nothing here relates…", "stays open"), found by grepping for the kind's words, since no gate reads them.
If any part stays conditional, the STATUS LABEL carries it.
A sentence found false of the tree is corrected here, in this landing — never put to the owner as a decision, unless the project's instructions say the owner is asked before any correction, in which case it is put to them with its evidence.

## 7. Gates, records, commit

The project's offline gates by exit code; then the flow: `flow make TASK --finding "…" <verified status> <Path.lean#decl> <document row> --resolution DRAFT` closes the prover's task, archives it, clears its rank and mints each finding from the LANDED proof (evidence that does not resolve against the manifest or the document refuses the call); `flow answer Q --by F` closes the question a finding settles; a residue is a `frame` or a `park`, never a "what stays open" line appended to the question's body.
Commit with NAMED paths — the prover session's sources, the package files, the manifests and the documents swept — never everything at once, since a sibling's in-flight work has been swept into a mislabelled commit that way.
If the landing rewired a cross-document import, run the project's consistency audit in the same session, before the commit; if it did not, say so in the entry.

## The manifest generator

`scripts/DeclManifest.lean` beside the CLI writes a Lean package's manifest in the row grammar the CLI and `flow` read: from the workspace, after a genuine build, `lake env lean --run DeclManifest.lean --roots Root1,Root2 --out ../scripts/decls.txt`, with `--own` naming every root of the workspace whose Prop-valued definitions count as named conditions when the workspace holds several packages (the project copies the file into its workspace and binds the command in `formal.toml`'s `generate`).
It walks the compiled environment, so it needs the build current, and its counting rule is stated in its own header: what counts as a declaration, what is a field, what is private, which binders are named conditions and which instance classes a theorem carries.
Another prover writes the same six row kinds with its own tool.
