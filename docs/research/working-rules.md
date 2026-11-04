# The working rules

Three skills with no script behind them, each brought in by the conversation itself; they came out of one research project and are optional, and the tools neither read nor need them.

- [`method`](../../plugins/research/skills/method/SKILL.md), `/research:method`, says how to review, what to call things, what a document holds and when a landed result enters one, what counts as evidence, what to check before pricing a piece of work, how to change a target honestly when a wall is hit, and how to work with the project's owner; its `references/reviews.md` is the review procedure, and its section "With a prover" orders ties among formal targets, which the `formal` plugin's landing follows.
- [`design`](../../plugins/research/skills/design/SKILL.md), `/research:design`, runs a design pass before anything new is built, whenever you say "let's add X" or "what about Y"; a design round is a task of the design kind in the flow, and a design record is never authority.
- [`debug`](../../plugins/research/skills/debug/SKILL.md), `/research:debug`, insists on the root cause before a fix, and again before anything is called fixed.

Two defaults of theirs matter to the flow: without asking, the agent corrects a sentence it finds false of the project's artifact at the sentence's own size, and registers a landed result by the method's register test where the project has no rule of its own; a project that wants to be asked first says so in one sentence of its instructions file, and the skills yield.

## Words

- **landing** — bringing a result into the record and the documents: the finding, the registration in a document, the log entry, in one change.
- **register (a result), registration** — writing a landed result into a document as a specific numbered statement with its rows and boundary; where and whether is the project's rule, the method's register test where it has none.
- **register test** — the four clauses under which a landed result enters a document (it changes a sentence there, steps on a named open, continues a section's story, or stands as a labelled side story); otherwise it is library content.
- **source, sink; root, leaf** — what depends on nothing and what nothing depends on in a dependency graph; the top and the ends of a directory or module tree; the two pairs are never mixed.
- **class claim, instance claim** — a statement about every member of a class, and one about a named member; a sentence says which it makes.
- **outsider pass** — a review of what is true only of a document an outsider reads, run when a posting is decided and never otherwise.
- **summary sites** — the places a result is restated in short — the headline, the abstract, the contributions, the status label, the registry — which a correction must reach as well as the detailed site.
- **status label** — the words beside a statement saying how it is established — proved, machine-checked with what stays elementary, conditional on a named hypothesis, open.
- **pricing a target** — estimating what a piece of work costs and what it changes before committing to it.
- **currency** — the quantity a bound is measured in (a description length, a count, a time); on a wall the currency may change, and the change is disclosed.
- **bill** — a bound's cost accounting: the terms that add up to what a construction pays, each held by some object and each a count or a clock.
- **wall** — a reason a formal target cannot be reached as stated, named by kind: expressivity, elaboration, missing-upstream, misstated (with a prover).
- **tree-derived figure** — a count read off the artifact (declarations, guards, modules), stated only where the project's figure check recomputes it.
- **root session** — the session that holds the conversation and writes the documents and records; the prover session is the other, with none of its context.
