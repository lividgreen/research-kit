---
name: research-init
description: Sets a project up for the research plugin — the flow, the reference library, the instructions paragraphs and the pre-commit hooks — and checks an existing setup. Use as `/research:research-init`, or when asked to set up research-kit, the flow, the library or the records in a project, or to check what the setup is missing, or to bring a project's existing notes, plans and bibliography into the records and the cards. Probes the project and the machine with `scripts/setup.py probe`, proposes what is missing and installs it only on the person's word, writes what the probe says is absent and nothing that exists, and reports what was written, installed and declined. The project's own instructions bind the names afterwards; this skill writes them once.
license: Apache-2.0
compatibility: Python 3.11 or later, standard library only, for `scripts/setup.py`; git for the project; a pre-commit runner (`prek` or `pre-commit`) for the hooks, proposed when absent; the `flow` and `library` skills beside this one, whose scripts the setup runs.
metadata:
  version: "0.2.0"
  script: scripts/setup.py
---

# Setting a project up

The setup is what the flow needs to run as the skills describe it, and the probe says which parts the project has.
`scripts/setup.py` beside this file is the probe and its selftest; it writes nothing and installs nothing.
The writes are the `flow` and `library` skills' own `init` commands, run through their scripts (`scripts/flow.py` and `scripts/library.py` beside those skills), and the edits below.

## What a setup is

Required, each for the reason it gives (the flow itself runs without a library, but a research project cites works):

- a git repository, since the records are tracked and the checks are commit hooks;
- `flow.toml`, the records directory and a bound log, written by `flow init --log FILE`;
- `library.toml` and the cards directory, written by `library init`, since a research project cites works and the flow's check asks the library for every cited key;
- the paragraphs both inits print, in the project's instructions file (`CLAUDE.md`, `AGENTS.md` or the agent's own), since they are what makes the next session read the records through the tool;
- the hooks `flow-check` and `library-check`, through `prek` or `pre-commit`, since a check that runs only when remembered is not a gate.

Recommended: `markdownlint` on PATH, so a record write that adds a violation is reverted.
Optional, by what the project does: the `markdown` package for the dashboard's rendered bodies, `pdftotext` for the text of a kept PDF, and the `formal` plugin for a project with a Lean workspace.
The probe labels every item with one of these words.

## The procedure

1. Probe.
   Run the probe with the project root as the working directory: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/research-init/scripts/setup.py probe` under Claude Code, this skill's own `scripts/setup.py` by its full path under any other agent (`--root DIR` for another project; `--json` for the same as data) and read the whole report: the environment, the project, the kit's version and layout, the proposals, the coverage line.
2. Plan, in one message.
   Say what exists and is left alone, what will be written, and what is missing with the proposal's command for each.
   Ask the person once, in one question: which proposals to install; the log's name where none exists (`WORKLOG.md` unless they say otherwise); whether copies the project keeps by hand may be redistributed with the repository (`--kept`), no unless they say so.
   Install nothing before the answer.
   In a run nobody can answer, write the project files with the defaults and list every proposal as left to the person.
3. Install what was chosen, with the proposal's command as shown, then run the probe again.
4. Write the bindings.
   `flow init --log LOG` where `flow.toml` is absent; `library init --scan RECORDS --scan LOG --documents GLOB…` where `library.toml` is absent, RECORDS the records directory `flow init` named, the globs those the probe found with a References section, `--kept` only when ruled.
   An `init` refuses over an existing bindings file; `--force` is used only when the person asks for the file to be rewritten.
5. Write the instructions.
   Append a section `## Research records` to the instructions file the probe found, or where none exists to `CLAUDE.md` under Claude Code and `AGENTS.md` under any other agent, holding the paragraphs both inits printed, in the project's words where its names differ; a file that already has the section is left as it is.
6. Write the hooks.
   Add to `.pre-commit-config.yaml`, created or extended, the block `repo: https://github.com/lividgreen/research-kit`, `rev:` the tag the probe prints, hooks `flow-check` and `library-check`; a project working from a checkout of the kit names the checkout's path as the repo and its commit as the rev; a file already naming research-kit is left as it is.
   Then `prek install` or `pre-commit install`, and once `prek run --all-files` or `pre-commit run --all-files`.
   Where the agent's harness refuses the write, the block is shown in the report for the person to paste.
7. Verify.
   `flow check`, `library check`, `flow state`; a problem either reports is fixed before the report, or named in it.
8. Report.
   What was written, file by file; what was installed; what was declined, with the command to do it later; the first move — capture an idea, mint a task, rank — and, where the probe found a Lean workspace, `/formal:formal-init` as the next step.

A project that already keeps its research elsewhere — notes, a roadmap, a to-do list, a bibliography — is set up the same way first; its material is then brought into the records and the cards by `references/migration.md`, as its own step with its own plan and the person's word.

## Rules

- Nothing is installed without the person's word, and a proposal is shown as the command that would run.
- Nothing that exists is overwritten: a bindings file, an instructions section, a hook block naming the kit.
- The probe is the evidence: a step it reports done is not redone, and a required item it reports missing is not talked around.
- The setup ends with the two checks green or the report saying which problem stands.
