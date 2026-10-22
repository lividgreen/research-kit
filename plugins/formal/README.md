# formal

The prover side of research-kit: the harness of a prover session for a project that pairs its documents with a machine-checked library.
It is built for Lean 4, the only prover it has run with: the manifest generator is a Lean program, and the agent's tools are Lean's language server.
The bar it assumes is no `sorry`, `admit` or `native_decide` behind a landed declaration; `formal.toml`'s `banned` is another list, the phrases a handoff prompt may not carry.
Another prover would need its own generator writing the same six row kinds, and none is written.
It needs the `research` plugin; nothing in `research` needs it.

In Claude Code 2.1.275 or later it installs in one step, after the `research` plugin; [Install](../../docs/install.md) covers every other agent:

```text
/plugin install formal --marketplace lividgreen/research-kit
```

Three skills, an agent and a generator; the sections below take them one by one, with the commands of the `formal` script.

## A prover handoff that is checked before it is sent

When work goes to a prover session, the agent composes the prompt statement-first from the document's own text, with the declarations quoted, a refute-first line, the bundle's shape and the witnesses commissioned, and checks it before dispatch.
The prover session runs as a subagent, or the prompt is emitted for your own session.

### The `handoff` skill and the `prover` agent

The [`handoff`](skills/handoff/SKILL.md) skill, `/formal:handoff` in Claude Code; `formal handoffcheck DRAFT` checks a drafted prompt's decidable invariants before it is dispatched or emitted.
The [`prover`](agents/prover.md) agent, `formal:prover`, is the prover session as a subagent: it reads the workspace's standing instructions first, never commits, and ends with the report the landing verifies.
A template of those instructions is [`workspace-instructions.md`](skills/handoff/references/workspace-instructions.md), which the setup fills in for the project.

## A landing that reads the tree, not the report

Before any document changes, what the prover session reports is checked against the built library: the declaration manifest's diff, a cold read-back of every landed statement, the binders and guards.
The document's rows are written from the landed proof, the summary sites swept, the records closed, and the commit names its paths.

### The `land` skill

The [`land`](skills/land/SKILL.md) skill, `/formal:land` in Claude Code.
`formal handback` prints the manifest diff, the instantiations, the witnesses owed, the guard delta, the document sites to re-read and the commission against the manifest; `formal readback NAME…` builds the docstring-stripped packet a cold reader writes each statement out from; `formal check` confirms the manifests parse and the bindings resolve.
[`DeclManifest.lean`](skills/land/scripts/DeclManifest.lean), beside the script, generates a Lean package's declaration manifest after a genuine build, writing the six row kinds `formal` and `flow` read.

## The prover-side setup

`/formal:formal-init` reads the Lean workspaces under the root with their roots and toolchains, proposes what is missing, writes `formal.toml`, places the manifest generator, writes the prover session's standing instructions from the template, and binds the flow's declaration evidence and the `formal-check` hook.

### The `formal-init` skill

The [`formal-init`](skills/formal-init/SKILL.md) skill, `/formal:formal-init` in Claude Code; `formal probe` reports the workspaces, the tools and what the setup is missing, and writes nothing.

## The script and the bindings

The plugin has one CLI, `formal`, and its script lives in the `land` skill (`skills/land/scripts/formal.py`, beside the generator), since landing is where every check of a report runs; the `handoff` skill calls the same script for `handoffcheck` and requires `land`.
`formal init` writes `formal.toml` at the project root: the workspace and its instructions file, the manifests and how they are regenerated, the library roots with their package directories, the documents whose cited names are read at a landing, the handoff's bans.
The prover's language server is registered by the project itself (its own `.mcp.json`), since the workspace path is the project's; the agent uses whatever prover tools are registered.
Claude Code's copy of the agent, [`claude-agents/prover.md`](claude-agents/prover.md), pins `model: sonnet`: a prover session follows a checked handoff well on it and costs less than a larger model, which was the finding of the project research-kit was extracted from; the portable copy under `agents/` inherits the session's model, and a project that wants another model edits that line.
GitHub Copilot, OpenHands and Antigravity read the agent from a directory of their own in the plugin, each holding the same text; Antigravity's also lists the tools the prover needs, since Antigravity gives an agent only the tools it names.
Which statement is proved next, how ties are ordered and what a wall is are the `research` plugin's `method` skill, under "With a prover".
The rules these skills are written around come from that project, each contestable; the incidents behind them stay in its log, which is not public.
