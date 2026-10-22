---
name: formal-init
description: Sets a project up for the formal plugin — `formal.toml` over its Lean workspace, the manifest generator in the workspace, the prover session's standing instructions, the flow's declaration evidence, the `formal-check` hook — and checks an existing setup. Use as `/formal:formal-init`, or when asked to set up the prover side, the formal plugin or the handoff and landing of Lean work in a project. Probes the workspace, the project and the machine with `formal probe`, proposes what is missing and installs it only on the person's word, writes what is absent and nothing that exists, and reports. Needs the research plugin's setup first.
license: Apache-2.0
compatibility: Python 3.11 or later for `scripts/formal.py` of the `land` skill; git; the prover, its build and `lake` are the project's, proposed when absent.
metadata:
  version: "0.1.0"
  requires: land
---

# Setting the prover side up

The prover side is what the `handoff` and `land` skills need: a workspace the probe can name, `formal.toml` binding it, a declaration manifest the flow and the landing read, the standing instructions the prover session reads first, and the check as a hook.
`formal probe` (the `land` skill's `scripts/formal.py`) is the evidence; it writes nothing and installs nothing.

## What a setup is

Required, since a handoff or a landing does not run without it:

- the research plugin's setup, since the findings and the records are the flow's; `/research:research-init` comes first;
- a Lean workspace under the project root with its lakefile, `lean` and `lake` on PATH;
- `formal.toml`, written by `formal init --workspace DIR`, its `[packages]` naming each library root the probe found and `[manifest] generate` the command that writes the manifest;
- `DeclManifest.lean` in the workspace, copied from the `land` skill's `scripts/`, and the manifest it writes after a build, since `formal check`, the landing and the flow's declaration evidence read it;
- the prover session's standing instructions at the path `formal.toml` names, from `references/workspace-instructions.md` of the `handoff` skill, its angle-bracket slots filled;
- `flow.toml`'s `[evidence]` bound to the manifest, with `manifest_roots` and `manifest_extension = "lean"`;
- the `formal-check` hook beside the flow's and the library's.

Recommended: the prover's language server registered in the project's `.mcp.json`, since the prover agent uses whatever prover tools are registered and works blind without them; `elan`, which installs `lean` and `lake` at the workspace's pin.

## The procedure

1. Probe.
   Run `formal probe` from the project root (`--root DIR` for another; `--json` for the same as data) and read the whole report: the tools, each workspace with its package, roots, toolchain and generator, the project's bindings, the proposals, the coverage line.
2. Plan, in one message.
   Say which workspace the setup binds (ask when the probe found several), what exists and is left alone, what will be written, and what is missing with the proposal for each; ask the person once, in one question: which proposals to install, and the slots of the instructions the probe cannot fill (the exact commands that re-verify a module, the build time, where the audit modules live).
   Install nothing and register nothing before the answer; in a run nobody can answer, write what the defaults allow and list the rest as left to the person.
3. Install what was chosen, with the proposal's command as shown, then run the probe again.
4. Write the bindings.
   `formal init --workspace DIR` where `formal.toml` is absent; then fill `[packages]` with the roots the probe read from the lakefile, each at its package directory, and `[manifest] generate` with those roots; `--force` only when the person asks for the file to be rewritten.
5. Place the generator.
   Copy `scripts/DeclManifest.lean` of the `land` skill into the workspace where it is absent, and leave the manifest to the prover's first run after a genuine build, as the report says.
6. Write the instructions.
   Where the file `formal.toml` names is absent, write it from `references/workspace-instructions.md` of the `handoff` skill with the slots filled from the probe and the answers; where it exists, leave it and say so.
7. Bind the flow's evidence and the hook.
   In `flow.toml`, set `[evidence] manifest`, `manifest_roots` (the workspace's package directories) and `manifest_extension = "lean"`; add `formal-check` to the kit's block in `.pre-commit-config.yaml`.
8. Verify and report.
   `formal check` and `flow check`; a manifest not yet generated is a problem both report, named in the report as the prover's first move with the generate command; then what was written, installed and declined, and the first handoff as the next step.

## Rules

- Nothing is installed or registered without the person's word; a proposal is shown as the command or the entry that would be written.
- Nothing that exists is overwritten: `formal.toml`, the instructions file, the generator, a hook block naming `formal-check`.
- The probe is the evidence: a root it did not read from the lakefile is not invented, and a slot it cannot fill is asked, never guessed.
- A workspace never learns of the project's records through this setup: the instructions file carries the prover session's rules and nothing of the records or the documents beyond the bans `formal.toml` names.
