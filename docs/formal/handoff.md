# The handoff

When work goes to a prover session, the agent composes the prompt statement-first from the document's own text, with the declarations quoted, a refute-first line, the bundle's shape and the witnesses commissioned, checks it with `formal handoffcheck`, and either dispatches it to the prover agent or emits it for your own prover session.
A prover session has none of the conversation, so everything it needs is in the prompt, and everything the prompt decides is checked before it goes anywhere; what comes back is landed by [The landing](land.md), which reads the tree and not the report.
The [`handoff`](../../plugins/formal/skills/handoff/SKILL.md) skill, `/formal:handoff` in Claude Code, is the procedure; the check is a command of the `formal` script, which lives in the `land` skill.

## What a handoff carries

- One title line saying what the bundle is, inside literal `<prompt session=fresh>` or `<prompt session=continue — why>` tags, with nothing after the closing tag.
- Numbered targets, each with the goal, its sources (the record, the document section or row quoted, the modules) and its own bar; a target with two or more hypotheses commissions a `<theorem>_nonvacuous` witness beside it, and a bundle of more than one piece lands sink-first, its `Bundle shape:` line saying so or why not.
- Target-specific warnings only — a known trap of the workspace, a refactor's byte-identical set, the docstring-register warning wherever a record is named as a source — since the standing rules live in the workspace's instructions and load in every prover session.
- The close, a `Refute first:` line naming the smallest parameters at which the commissioned statement can be computed, and a `Commissioned:` line listing every declaration the prompt commissions, which the landing looks up in the manifests.

It assigns no work on the root's side, restates no standing rule, carries none of the phrases `formal.toml` bans, writes every path relative to the workspace (`../papers/x.md`), and names no record id, since a session cites what it was given.
Before the prompt is written, the work is minted in the flow — a task under its question, drawn by the prover's owner, an owner with a hand limit of one — and the prompt is the last thing in the turn, after the records, the gates and the commit.

## The prover agent

The [`prover`](../../plugins/formal/agents/prover.md) agent, `formal:prover` in Claude Code, is the prover session as a subagent: it reads the workspace's standing instructions first, never commits, and ends with the report the landing verifies.
Claude Code's copy, [`claude-agents/prover.md`](../../plugins/formal/claude-agents/prover.md), pins `model: sonnet`, on which a prover session follows a checked handoff well at less cost than a larger model; the portable copy under `agents/` inherits the session's model, and GitHub Copilot, OpenHands and Antigravity read the agent from a directory of their own in the plugin, each holding the same text.
The agent type is loaded when a session starts, so in the session that installed the plugin the skill falls back to a general-purpose subagent given the agent's text; where no agent runs, the prompt is emitted and you paste the report back.
The workspace's standing instructions — the build gate, the manifest regeneration, the known traps, the report-back list — are the project's, written by the setup from the skill's [`references/workspace-instructions.md`](../../plugins/formal/skills/handoff/references/workspace-instructions.md).

## The check

The check exits 0 when the draft passes, 1 with each failure named, and 2 when there was nothing to check; the skill writes the draft to a scratch file outside the repository, re-runs to exit 0, and keeps the draft until the landing, which passes it to `formal handback --handoff DRAFT`.
A pass does not replace re-reading the prompt against the current text it quotes: a prose correction invalidates any handoff built on it.

`formal handoffcheck DRAFT` checks the decidable shape of a prover handoff before it is sent, never its content:

- one `<prompt session=fresh>` or `<prompt session=continue>` block, closed, with nothing after the closing tag, and a `continue` that states its reason;
- none of the phrases `formal.toml` bans;
- a record named as a source — a path under `[handoff] records`, a record id, a file of `meta_names`, a key of `key_patterns` — carries the docstring-register warning;
- paths relative to the workspace, the project's own directories written `../`;
- a `Refute first:` line and a `Commissioned:` line naming the declarations (or `none —` and why);
- a bundle of two or more pieces with a `Bundle shape:` line and a sentence keeping its own words out of the docstrings.

A draft with no prompt block exits 2, since there was nothing to check; the [skill](../../plugins/formal/skills/handoff/SKILL.md) says what each line is for.

## Words

- **handoff, handback** — the prompt a prover session is given and the report it returns, landed only after verification at the tree.
- **commission, commissioned** — what a handoff asks the prover session to produce: the declarations named on its `Commissioned:` line, which the landing looks up in the manifests.
- **witness, joint-satisfiability witness** — a `<theorem>_nonvacuous` declaration showing a theorem's hypotheses hold at once, commissioned beside any theorem with two or more; a theorem with none is the finding.
- **refute first** — the prover session's opening move: a bounded computation at the smallest parameters where the commissioned statement can be computed, reported either way.
- **sink-first** — a bundle lands its composite statement, the one nothing in the bundle depends on, before its predecessors are proved.
