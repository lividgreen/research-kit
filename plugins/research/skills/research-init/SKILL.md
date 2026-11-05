---
name: research-init
description: Sets a project up for the research plugin — the flow, the reference library, the instructions paragraphs and the pre-commit hooks — and checks an existing setup. Use as `/research:research-init`, or when asked to set up research-kit, the flow, the library or the records in a project, or to check what the setup is missing, or to bring a project's existing notes, plans and bibliography into the records and the cards. Probes the project and the machine with `scripts/setup.py probe`, which also compares the pins and names the pending upgrade steps, proposes what is missing and installs it only on the person's word, writes what the probe says is absent and nothing that exists, offers the project a runner script, and reports what was written, installed and declined. The project's own instructions bind the names afterwards; this skill writes them once.
license: Apache-2.0
compatibility: Python 3.11 or later, standard library only, for `scripts/setup.py`; git for the project; a pre-commit runner (`prek` or `pre-commit`) for the hooks, proposed when absent; the `flow` and `library` skills beside this one, whose scripts the setup runs.
metadata:
  version: "0.4.3"
  script: scripts/setup.py
---

# Setting a project up

The setup is what the flow needs to run as the skills describe it, and the probe says which parts the project has.
`scripts/setup.py` beside this file is the probe, the writer of the project's runner script and their selftest; the probe writes nothing and installs nothing.
The writes are the `flow` and `library` skills' own `init` commands, run through their scripts (`scripts/flow.py` and `scripts/library.py` beside those skills), the edits below, and the runner script where the person says yes to it.

## What a setup is

Required, each for the reason it gives (the flow itself runs without a library, but a research project cites works):

- a git repository, since the records are tracked and the checks are commit hooks;
- `flow.toml`, the records directory and a bound log, written by `flow init --log FILE`;
- `library.toml` and the cards directory, written by `library init`, since a research project cites works and the flow's check asks the library for every cited key;
- the paragraphs both inits print, in the project's instructions file (`CLAUDE.md`, `AGENTS.md` or the agent's own), since they are what makes the next session read the records through the tool;
- the hooks `flow-check` and `library-check`, through `prek` or `pre-commit`, since a check that runs only when remembered is not a gate.

Recommended: `markdownlint` on PATH, so a record write that adds a violation is reverted.
Optional, by what the project does: the `markdown` package for the dashboard's rendered bodies, `pdftotext` for the text of a kept PDF, and the `formal` plugin for a project with a Lean workspace.
The probe labels each item of the machine with one of these words, ok or MISSING beside it, and each of the project's with what it found, present or absent, found or none: a machine's item is installed, a project's is written by the setup where it is absent, so an absent one is no failure.

The project's last item, `pins at one tag`, reads the places a project pins the kit: the hooks' `rev` in `.pre-commit-config.yaml`, the marketplace's `ref` in `.claude/settings.json`, and the version of each plugin of the research-kit marketplace Claude Code installed for the project, from its install record `~/.claude/plugins/installed_plugins.json` (`CLAUDE_CONFIG_DIR` moves `~/.claude`; the project's own entry, of scope local or project, stands over a user one), beside the version of the plugin the probe runs from.
It names each one that differs from the newest of them, and a plugin the settings enable that is not installed; where the install record is absent, another agent's runtime or no install, it says so and compares the rest.

The report's `upgrade` section names the steps a move to another release still asks, each with its command, in the order an upgrade takes them:

- `pins`: where the pins differ, the releases between them whose **Upgrading** paragraphs to read in the kit's changelog (by tag and its URL, since the changelog is not inside the plugin), then the steps of a move: the `ref` edited, `claude plugin marketplace add 'lividgreen/research-kit#<tag>' --scope project`, `claude plugin update research@research-kit --scope project` for each plugin behind, the hooks' `rev` set, the restart;
- `records`: what `flow doctor` of the `flow` skill beside this one finds an older model wrote, as the count of mechanical edits `flow doctor --fix` writes and of the things for the hand `flow doctor` lists;
- `index`: a stale index, which `flow index` rewrites.

The probe runs `flow doctor` and `flow index --check`, which write nothing; a step it could not check reads NOT RUN with the reason, and one with no `flow.toml` to read reads `--`.

## The procedure

1. Probe.
   Run the probe with the project root as the working directory: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/research-init/scripts/setup.py probe` under Claude Code, this skill's own `scripts/setup.py` by its full path under any other agent (`--root DIR` for another project; `--json` for the same as data) and read the whole report: the environment, the project with its pins, the kit's version and layout, the proposals, the upgrade steps, the coverage line.
2. Plan, in one message.
   Say what exists and is left alone, what will be written, what is missing with the proposal's command for each, and, in a project set up before, each pending upgrade step with its commands and the releases whose **Upgrading** paragraphs to read first.
   Ask the person once, in one question: which proposals to install; the log's name where none exists (`WORKLOG.md` unless they say otherwise); which evidence forms the project accepts, of the five the flow ships and its own words (step 4); whether copies the project keeps by hand may be redistributed with the repository (`--kept`), no unless they say so; whether to write the runner script (step 8), no unless they say so; and, where an upgrade step is pending, whether to take it now.
   Install nothing before the answer.
   In a run nobody can answer, write the project files with the defaults and list every proposal as left to the person.
3. Install what was chosen, with the proposal's command as shown, then run the probe again.
4. Write the bindings.
   `flow init --log LOG` where `flow.toml` is absent; `library init --scan RECORDS --scan LOG --documents GLOB…` where `library.toml` is absent, RECORDS the records directory `flow init` named, the globs those the probe found with a References section, `--kept` only when ruled.
   An `init` refuses over an existing bindings file; `--force` is used only when the person asks for the file to be rewritten.
   `flow init` writes the five evidence forms the kit ships in `[evidence] forms` (`formal`, `statistical`, `peer-reviewed`, `stated`, `reference`): ask the person, in the one question of step 2, which the project accepts and which words of its own to add (a project with a prover keeps `formal`, one with datasets `statistical`, one with a library `peer-reviewed`; `stated` is the project's own word and the trust to raise), edit the list, and put what each form means for the project into the instructions section of step 5.
5. Write the instructions.
   Append a section `## Research records` to the instructions file the probe found, or where none exists to `CLAUDE.md` under Claude Code and `AGENTS.md` under any other agent, holding the paragraphs both inits printed, in the project's words where its names differ; a file that already has the section is left as it is.
6. Write the hooks.
   Add to `.pre-commit-config.yaml`, created or extended, the block `repo: https://github.com/lividgreen/research-kit`, `rev:` the tag the probe prints, hooks `flow-check` and `library-check`; a project working from a checkout of the kit names the checkout's path as the repo and its commit as the rev; a file already naming research-kit is left as it is.
   Then `prek install` or `pre-commit install`, and once `prek run --all-files` or `pre-commit run --all-files`.
   Where the agent's harness refuses the write, the block is shown in the report for the person to paste.
7. Verify.
   `flow check`, `library check`, `flow state`; a problem either reports is fixed before the report, or named in it.
8. Write the runner script, only on the person's yes.
   `setup runner` (this skill's `scripts/setup.py runner`, `--root DIR` for another project) writes `kit.py` into the project's `scripts/` directory, or at the path `--out PATH` names under the root, and refuses an existing file unless `--force` is given at the person's word.
   The script is the project's own from then on and installs nothing: `python3 scripts/kit.py run SKILL ARGS…` runs a skill's script (`flow`, `library`, `dashboard` and `setup` of the research plugin, `formal` of the formal plugin) by the path Claude Code installed it at, `python3 scripts/kit.py path SKILL` prints that path, and `python3 scripts/kit.py check` prints the pins and exits 1 where they disagree; `run` and `path` refuse while the pins disagree.
   It serves a Makefile target or a script on a machine where Claude Code installed the plugins, calling a skill's script for anything the hooks do not run; where no install record exists it refuses and says so.
9. Report.
   What was written, file by file; what was installed; what was declined, with the command to do it later; the upgrade steps left pending, with their commands; the first move — capture an idea, mint a task, rank — and, where the probe found a Lean workspace, `/formal:formal-init` as the next step.

A project that already keeps its research elsewhere — notes, a roadmap, a to-do list, a bibliography — is set up the same way first; its material is then brought into the records and the cards by `references/migration.md`, as its own step with its own plan and the person's word.

## Rules

- Nothing is installed without the person's word, and a proposal or an upgrade step is shown as the command that would run.
- Nothing that exists is overwritten: a bindings file, an instructions section, a hook block naming the kit, a runner script.
- The probe is the evidence: a step it reports done is not redone, and a required item it reports missing is not talked around.
- The setup ends with the two checks green or the report saying which problem stands.
