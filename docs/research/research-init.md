# The research setup

`/research:research-init` sets a project up for the `research` plugin and checks an existing setup: it probes the project and the machine, proposes what is missing, installs nothing without your word, writes what is absent and nothing that exists, and reports.
The probe is `scripts/setup.py probe` of the [`research-init`](../../plugins/research/skills/research-init/SKILL.md) skill, which writes nothing; the writes are `flow init` and `library init`, run through their own scripts, and the edits below.
With another agent, ask it to set research-kit up in the project; [Getting started](getting-started.md) shows what the setup writes, command by command.

## What a setup is

Required, each for the reason it gives:

- a git repository, since the records are tracked and the checks are commit hooks;
- `flow.toml`, the records directory and a bound log, written by `flow init --log FILE` ([The flow](flow.md));
- `library.toml` and the cards directory, written by `library init`, since a research project cites works and the flow's check asks the library for every cited key ([The library](library.md));
- the paragraphs both inits print, in the project's instructions file (`CLAUDE.md`, `AGENTS.md` or the agent's own), since they are what makes the next session read the records through the tool;
- the hooks `flow-check` and `library-check`, through `prek` or `pre-commit`, since a check that runs only when remembered is not a gate.

Recommended: `markdownlint` on PATH, so a record write that adds a violation is reverted.
Optional, by what the project does: the `markdown` package for the dashboard's rendered bodies, `pdftotext` for the text of a kept PDF, and the `formal` plugin for a project with a Lean workspace.
The probe labels every item with one of these three words, and compares the hooks' `rev`, the marketplace's `ref` in the project's settings and the installed plugin's version, so the three pins are seen to name one tag.

## What it does

1. Probes, and reads the whole report: the environment, the project, the kit's version and layout, the proposals, the coverage line.
2. Plans in one message and asks once: which proposals to install, the log's name where none exists (`WORKLOG.md` unless you say otherwise), and whether copies the project keeps by hand may be redistributed with the repository (`library init --kept`, no unless you say so).
3. Installs what was chosen, with the proposal's command as shown, and probes again.
4. Writes the bindings where they are absent: `flow init --log LOG`, then `library init --scan RECORDS --scan LOG --documents GLOB…` with the globs the probe found with a References section; an `init` refuses over an existing file, and `--force` is used only when you ask for a rewrite.
5. Appends a section `## Research records` to the instructions file, holding the paragraphs both inits printed in the project's words: where the records are and that they are read through the tool, that a state changes only through a transition, that the check runs before a commit, that the ranked list is the schedule, where the log is; a file that has the section is left as it is.
6. Adds the kit's block to `.pre-commit-config.yaml` — `repo: https://github.com/lividgreen/research-kit`, `rev:` the tag the probe prints, the hooks `flow-check` and `library-check` — installs the runner's hook and runs it once over all files; [Install](../install.md) has the block and the pins.
7. Runs `flow check`, `library check` and `flow state`, and fixes or names any problem.
8. Reports what was written, installed and declined, each declined item with the command to do it later, the first move, and `/formal:formal-init` as the next step where the probe found a Lean workspace.

A project that already keeps its research elsewhere — notes, a roadmap, a to-do list, a bibliography — is set up the same way first; its material is then brought into the records and the cards as a step of its own, by the skill's [`references/migration.md`](../../plugins/research/skills/research-init/references/migration.md): survey and propose before writing, classify by the kinds' own tests, carry the live front and point at the settled, go through the commands wherever one exists, remove nothing, and end with the checks.

## Words

- **research-init** — the skill that sets a project up: it probes, proposes, writes what is absent and nothing that exists, and reports; `/research:research-init`.
- **probe** — the report `setup probe` prints: the environment, the project, the kit's version, the proposals and a coverage line; it writes and installs nothing.
- **required, recommended, optional** — the probe's three words for an item: without a required one the flow does not run; a recommended one is proposed; an optional one serves what the project does.
