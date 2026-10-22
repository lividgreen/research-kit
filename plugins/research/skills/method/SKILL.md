---
name: method
description: Method rules for a project that writes documents and makes claims — how to review, what counts as evidence, what to check before pricing a piece of work, how to change a target honestly when a wall is hit, and, where the project keeps a machine-checked library, how a formal target is picked and scoped and what a wall is. Use before a design round, a list refresh, a review pass or the pricing of a formal target. The rules come from one research programme, and the incidents that earned them are not part of the kit.
license: Apache-2.0
compatibility: No tooling; read before design, review and target changes.
metadata:
  version: "0.1.0"
---

# Research method

These are one project's rules, earned over a research programme that pairs written documents with a machine-checked library; each is contestable, a project adopts them by installing this skill and keeps what fits, and the incidents behind them stay in that programme's log, which is not public.

## Review

- A structural pass and a correctness pass find disjoint defect classes; a section is reviewed only after both.
- The citation discipline applies inward: open the exporting statement before citing it, even when it sits three paragraphs up in the same file.
- A correction reaches every summary site — the headline, the abstract, the registry, the companion prose — not only the detailed site where it was found; the project binds the list.
- A scope qualifier sits on the claim, not on the sentence's conclusion.
- A negative-coverage sentence ("nothing in this work does X") is a claim about every document at once; its counterexample is usually a companion's own headline result under a hypothesis — and every landing re-reads such sentences for the landed result's kind, since no gate does.
- A sentence found false of the artifact is corrected by the session that finds it, at its exact size, in that session; it is never put to the project's owner as a choice. The owner decides scope and significance; whether a false sentence stands is not a decision. A project whose instructions file says the owner is asked before any correction has opted out, and the session then puts the sentence, its evidence and the correction to them instead.
- Crediting the work with settling a NAMED external result requires reading that result's primary source first — its quantifiers, its resources and the author's own caveats; a partial match names the special case proved and the gap.

## Evidence

- A counting or closed-form claim gets its planted-defect probe in the same round it is made.
- Unverified code is not evidence; a numerical check a reader would need is an argument for checking it mechanically, not for shipping the script.
- Suspect the bound, not the witness: a residue that keeps coming out wrong is a fact about the bound until the bound has been pushed.
- A row or a remark about a checked artifact is written from the landed artifact, never from the design record that commissioned it.
- A record paraphrase can name the wrong referent; agreement between two citations is not verification — open what they point at.
- A whole-tree count (declarations, guards, modules) is a tree-derived figure: recomputed by a check at every occurrence, stated in the fewest places, never copied into a memory.
- A declaration name in a document is a claim that the declaration exists with that statement; a document never names a declaration in order to say it does NOT exist, since the check that resolves names cannot tell assertion from denial.

## Before pricing a target

- Check what structure the target already carries before pricing a replacement into it.
- A label or category tag is a filing address, not a statement.
- An item's own pointer can be the stale thing, or born wrong.
- Existence is the cheap half: check what CONSUMES the object before pricing its existence.
- Checking a target's inputs is not checking what the project already derives from them.
- An equivalence proved about a hypothesis does not discharge it.
- When a bill misbehaves, ask of each term who holds it and whether it is a count or a clock.
- A parking reason can be priced against the wrong object; the cheapest check is the document's own definition.

## Changing the target honestly

The freedom is of route: on a wall, change the statement, the definition, the object or the currency to reach the goal.
These invariants keep that honest.

1. **The original question stays on record.** Beside the result, write the statement before, the statement after, why, and whether the original is now settled, still open or refuted. An original open is never deleted by a change; it is answered, re-parked with the new reason, or marked refuted.
2. **A change is not a settle.** A result proved after a change is registered as a result about the changed statement; its status label, its verification row and every summary site name that statement, and no sentence claims the original was settled unless the change is shown equivalent or stronger.
3. **Weakening is disclosed where a reader looks first.** A change that adds a hypothesis, narrows a class or swaps a currency is carried at the headline, the abstract, the status label and the contributions, not only in an appendix row.
4. **Every consumer is swept in the same session.** A changed definition or statement reaches every document, registry entry and docstring that cites it before the commit; the project binds the audit that checks this.
5. **Evaluation is fixed before the result.** Probes, sweep sets, kill criteria and named hypotheses fixed for a round are not altered after seeing its result; changing them opens a new round with its own record. A probe that now passes because the statement moved is re-derived against the moved statement and says so.
6. **A change that drops the interesting property is a finding, not a route.** When the provable form loses what made the question worth asking, record "the natural statement is unreachable or false; the provable form is X" and keep the natural statement open.
7. **No change to please a check.** A statement is never weakened because a cited result lacks a mechanical proof, and never strengthened in prose beyond what the artifact proves; a named hypothesis with a citation is the honest form.

## With a prover

Where the project pairs its documents with a machine-checked library, these rules decide which statement is proved next and when a target changes; the prover session's own mechanics — the handoff, the landing, the sweeps — are the `formal` plugin's.

- Statement-first: the statement is designed from the document's actual text, opened, never from memory.
- Ties among formal targets are ordered by: what a document needs; statement readiness; the kind of effect on the document; elaboration risk; then how many rows move and how big the piece is.
- Check computability of what a construction reads before commissioning it; a search over an infinite object is a wall, not a target.
- A generic piece and a specific piece of one bundle carry the same quantification; a bundle lands sink-first — the composite statement nothing in the bundle depends on, with its predecessors' statements as hypotheses, read back before any predecessor is proved — and each predecessor is computed at its edge parameters before dispatch.
- A refute-first computation at the smallest parameters precedes every handoff; a theorem with two or more hypotheses is commissioned with a non-vacuity witness beside it.
- A wall names its kind: expressivity (the statement cannot be expressed), elaboration (the prover cannot handle the term), missing-upstream (a needed library result is absent), misstated (the statement was wrong); a wall fitting none is a new kind, recorded.
- On a wall, change the target under the invariants above; another attempt that restates the object is tried before the wall is recorded as such.
- A repair loop against a failing build is bounded: three attempts, then stop and report the wall honestly with its error blocks trimmed to what matters.
