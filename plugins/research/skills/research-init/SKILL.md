---
name: research-init
description: Sets a project up for the research plugin — the flow, the reference library, the instructions paragraphs and the pre-commit hooks — and checks an existing setup. Use as `/research:research-init`, or when asked to set up research-kit, the flow, the library or the records in a project, or to check what the setup is missing, or to bring a project's existing notes, plans and bibliography into the records and the cards. Probes the project and the machine with `scripts/setup.py probe`, which also holds the pins to the kit's latest release and names the pending upgrade steps, proposes what is missing and installs it only on the person's word, re-checks on every run what exists against the project as it stands, adds what is missing on the person's word and rewrites nothing without it, and reports what was written, installed and declined. The project's own instructions bind the names afterwards; this skill writes them once.
license: Apache-2.0
compatibility: Python 3.11 or later, standard library only, for `scripts/setup.py`; git for the project; a pre-commit runner (`prek` or `pre-commit`) for the hooks, proposed when absent; the `flow` and `library` skills beside this one, whose scripts the setup runs.
metadata:
  version: "0.6.1"
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
- where the project has documents, what its reviews hold them to, in the same section, since the `audit`, `scrutinize` and `attribution` skills read it there and no script does;
- the hooks `flow-check` and `library-check`, through `prek` or `pre-commit`, since a check that runs only when remembered is not a gate.

Recommended: `markdownlint` on PATH, so a record write that adds a violation is reverted.
Optional, by what the project does: the `markdown` package for the dashboard's rendered bodies, `pdftotext` for the text of a kept PDF, and the `formal` plugin for a project with a Lean workspace.
The probe labels each item of the machine with one of these words, ok or MISSING beside it, and each of the project's with what it found, present or absent, found or none: a machine's item is installed, a project's is written by the setup where it is absent, so an absent one is no failure.

The project's last item, `pins at one tag`, reads the places a project pins the kit: the hooks' `rev` in `.pre-commit-config.yaml`, the marketplace's `ref` in `.claude/settings.json`, which is to be `latest`, the branch each release moves to its tag, and the version of each plugin of the research-kit marketplace Claude Code installed for the project, from its install record `~/.claude/plugins/installed_plugins.json` (`CLAUDE_CONFIG_DIR` moves `~/.claude`; the project's own entry, of scope local or project, stands over a user one), beside the version of the plugin the probe runs from.
The probe asks GitHub for the kit's latest release (`tag_name` of `https://api.github.com/repos/lividgreen/research-kit/releases/latest`), and the item names each pin that differs from it, a marketplace at a tag or at no ref (the default branch) with the move to `latest`, and a plugin the settings enable that is not installed; where the install record is absent, another agent's runtime or no install, it says so and compares the rest.
Where the latest release cannot be read, offline, refused or with `RESEARCH_KIT_OFFLINE=1` set, the item says so and why, and holds the pins to the newest of them instead.

The report's `upgrade` section names the steps a move to another release still asks, each with its command, in the order an upgrade takes them:

- `pins`: where a pin is off the latest release, the releases from the oldest pin up to it whose **Upgrading** paragraphs to read in the kit's changelog (by tag and its URL, since the changelog is not inside the plugin), then the steps that move every pin to it: where the marketplace is not at `latest`, the `ref` edited to `latest` and `claude plugin marketplace add 'lividgreen/research-kit#latest' --scope project`, else `claude plugin marketplace update research-kit`; `claude plugin update research@research-kit --scope project` for each plugin off it; the hooks' `rev` set (`prek autoupdate` or `pre-commit autoupdate`) where the hooks are remote; the restart;
- `records`: what `flow doctor` of the `flow` skill beside this one finds an older model wrote, as the count of mechanical edits `flow doctor --fix` writes and of the things for the hand `flow doctor` lists;
- `index`: a stale index, which `flow index` rewrites.

The probe runs `flow doctor` and `flow index --check`, which write nothing; a step it could not check reads NOT RUN with the reason, and one with no `flow.toml` to read reads `--`.

## The procedure

1. Probe.
   Run the probe with the project root as the working directory: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/research-init/scripts/setup.py probe` under Claude Code, this skill's own `scripts/setup.py` by its full path under any other agent (`--root DIR` for another project; `--json` for the same as data) and read the whole report: the environment, the project with its pins, the kit's version and layout, the proposals, the upgrade steps, the coverage line.
2. Plan, in one message.
   Say what exists and is left alone, what will be written, what is missing with the proposal's command for each, and, in a project set up before, each pending upgrade step with its commands and the releases whose **Upgrading** paragraphs to read first.
   Ask the person once, in one question: which proposals to install; the log's name where none exists (`WORKLOG.md` unless they say otherwise); which evidence forms the project accepts, of the five the flow ships and its own words (step 4); whether copies the project keeps by hand may be redistributed with the repository (`--kept`), no unless they say so; where the project has documents, what its reviews hold them to (step 5), proposed from the documents, which the agent reads first; and, where an upgrade step is pending, whether to take it now.
   Install nothing before the answer.
   In a run nobody can answer, write the project files with the defaults and list every proposal as left to the person.
3. Install what was chosen, with the proposal's command as shown, then run the probe again.
4. Write the bindings.
   `flow init --log LOG` where `flow.toml` is absent; `library init --scan RECORDS --scan LOG --documents GLOB…` where `library.toml` is absent, RECORDS the records directory `flow init` named, the globs those the probe found with a References section, `--kept` only when ruled.
   An `init` refuses over an existing bindings file; `--force` is used only when the person asks for the file to be rewritten.
   `flow init` writes the five evidence forms the kit ships in `[evidence] forms` (`formal`, `statistical`, `peer-reviewed`, `stated`, `reference`): ask the person, in the one question of step 2, which the project accepts and which words of its own to add (a project with a prover keeps `formal`, one with datasets `statistical`, one with a library `peer-reviewed`; `stated` is the project's own word and the trust to raise), edit the list, and put what each form means for the project into the instructions section of step 5.
5. Write the instructions.
   Append a section `## Research records` to the instructions file the probe found, or where none exists to `CLAUDE.md` under Claude Code and `AGENTS.md` under any other agent, holding the paragraphs both inits printed, in the project's words where its names differ.
   Where the project has documents, the section ends with `### Reviews`, what the person answered in step 2: the documents that form the corpus, the draft and deferred ones among them, and those a reader sees beyond the ones `library.toml` binds; which document imports which; the regime conditions with their constants; the claims whose status is written in more than one document; the objects whose definitions are compared, and any two sharing a name on purpose; how a regime condition is written, and which objects form an abstract class and which its instances; the status labels the project uses; any rule of the project's own a document is held to.
   Where the section exists, it is re-read whole against the project as it stands: what it lacks — `### Reviews` where it has none, an item of it a document now needs — is added on the person's word, what it says that is stale is named with the edit proposed, and nothing in it is rewritten without their word; a project with no documents yet gets `### Reviews` from a later run.
6. Write the hooks.
   Add to `.pre-commit-config.yaml`, created or extended, the block `repo: https://github.com/lividgreen/research-kit`, `rev:` the tag the probe prints, hooks `flow-check` and `library-check`; a project working from a checkout of the kit names the checkout's path as the repo and its commit as the rev; a file already naming research-kit keeps its block, re-checked for a hook it lacks, which is added on the person's word, and so does one whose `repo: local` hooks run the kit's scripts (the probe's item says so), which carry no `rev` and follow the installed plugins.
   Then `prek install` or `pre-commit install`, and once `prek run --all-files` or `pre-commit run --all-files`.
   Where the agent's harness refuses the write, the block is shown in the report for the person to paste.
7. Verify.
   `flow check`, `library check`, `flow state`; a problem either reports is fixed before the report, or named in it.
8. Report.
   What was written, file by file; what was installed; what was declined, with the command to do it later; the upgrade steps left pending, with their commands; the first move — capture an idea, mint a task, rank — and, where the probe found a Lean workspace, `/formal:formal-init` as the next step.

A project that already keeps its research elsewhere — notes, a roadmap, a to-do list, a bibliography — is set up the same way first; its material is then brought into the records and the cards by `references/migration.md`, as its own step with its own plan and the person's word.

Where the person asks how to run a script outside the agent, from a Makefile target or a script of the project's: by its path from the project root where the skills are installed into the project, `python3 .agents/skills/flow/scripts/flow.py check` after `npx skills add` and `.claude/skills/…` likewise for Claude Code, since a plugin install's path in the agent's cache changes with each version; the checks themselves run through the hooks.

## Rules

- Nothing is installed without the person's word, and a proposal or an upgrade step is shown as the command that would run.
- Every run re-checks everything the setup covers that exists — the bindings files, the instructions section, the hook block — against the project as it stands, and adds what is missing; a project set up before is set up again the same way, never taken as done because its files are present.
- Nothing that exists is overwritten without the person's word: a bindings file (`--force` only when they ask), an instructions section, a hook block naming the kit; what is stale in one is named with the edit proposed.
- The probe is the evidence for what it reads — the machine, which files are present, the pins, the upgrade steps: a required item it reports missing is not talked around; a file it reports present is still read by the agent, since presence says nothing of what it holds.
- The setup ends with the two checks green or the report saying which problem stands.
