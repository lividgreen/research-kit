# The research setup

`/research:research-init` sets a project up for the `research` plugin and checks an existing setup: it probes the project and the machine, proposes what is missing, installs nothing without your word, re-checks what exists against the project as it stands and adds what is missing, rewriting nothing without your word, and reports.
The probe is `scripts/setup.py probe` of the [`research-init`](../../plugins/research/skills/research-init/SKILL.md) skill, which writes nothing; the writes are `flow init` and `library init`, run through their own scripts, and the edits below.
Every run re-checks the whole setup, so a project set up before is set up again the same way, its files read rather than taken as done because they are present, and what a later release or a new document asks is added.
With another agent, ask it to set research-kit up in the project; [Getting started](getting-started.md) shows what the setup writes, command by command.

## What a setup is

Required, each for the reason it gives:

- a git repository, since the records are tracked and the checks are commit hooks;
- `flow.toml`, the records directory and a bound log, written by `flow init --log FILE` ([The flow](flow.md));
- `library.toml` and the cards directory, written by `library init`, since a research project cites works and the flow's check asks the library for every cited key ([The library](library.md));
- the paragraphs both inits print, in the project's instructions file (`CLAUDE.md`, `AGENTS.md` or the agent's own), since they are what makes the next session read the records through the tool;
- where the project has documents, what its reviews hold them to, in the same section, since [the audit](audit.md), [scrutiny](scrutinize.md) and [the attribution check](attribution.md) read it there and no script does;
- the hooks `flow-check` and `library-check`, through `prek` or `pre-commit`, since a check that runs only when remembered is not a gate.

Recommended: `markdownlint` on PATH, so a record write that adds a violation is reverted.
Optional, by what the project does: the `markdown` package for the dashboard's rendered bodies, `pdftotext` for the text of a kept PDF, and the `formal` plugin for a project with a Lean workspace.
The probe labels the machine's items with one of these three words and the project's with `present`, `absent`, `found` or `none`.

## The pins and the upgrade steps

The project's item `pins at one tag` compares the places a project pins the kit: the hooks' `rev` in `.pre-commit-config.yaml`, the marketplace's `ref` in `.claude/settings.json`, which is to be `latest`, the branch each release moves to its tag ([Install](../install.md#following-the-releases)), and the version of each plugin of the research-kit marketplace that Claude Code installed for the project, beside the version of the plugin the probe runs from.
Where no hook names the kit's repository the item says that no hook pins the kit by `rev`, and, where the project's `repo: local` hooks run the kit's scripts, that the hooks are local and follow the plugins' pins; the report's `kit:` line gives the version and the release tag of the plugin the probe runs from, which are no pin of the hooks.
The installed versions come from Claude Code's install record, `~/.claude/plugins/installed_plugins.json` (`CLAUDE_CONFIG_DIR` moves `~/.claude`), where the project's own entry, of scope local or project, stands over a user one.
The probe asks GitHub for the kit's latest release, and the item names each pin that differs from it, a marketplace at a tag or at no ref with the move to `latest`, and a plugin the project's settings enable that is not installed; where the install record is absent, under another agent or with nothing installed, it says so and compares the hooks and the marketplace alone.
Where the latest release cannot be read, offline, refused or with `RESEARCH_KIT_OFFLINE=1` set, the item says so and why, and compares the pins among themselves, against the newest of them.

The report's `upgrade` section, in the text and under `--json`, names the steps a move to another release still asks, each with its command, in the order an upgrade takes them:

| Step | What the probe reads | What it names |
| --- | --- | --- |
| `pins` | the item above | the releases from the oldest pin up to the latest whose **Upgrading** paragraphs to read in the [changelog](https://github.com/lividgreen/research-kit/blob/main/CHANGELOG.md), then the steps of [Install](../install.md#following-the-releases): the `ref` edited to `latest` and the marketplace added at it where it is not there, else the marketplace updated; each plugin off the release updated; a remote hooks' `rev` set; the restart |
| `records` | `flow doctor` of the `flow` skill beside this one | the mechanical edits `flow doctor --fix` writes, counted by class, and the things for the hand `flow doctor` lists ([The flow](flow.md#flow-doctor)) |
| `index` | `flow index --check` | a stale index, which `flow index` rewrites |

The probe runs the two flow commands, which write nothing, and the probe still writes nothing; a step marked `PENDING` is to take, `NOT RUN` could not be checked and says why (no flow script beside the skill, a `flow.toml` the flow cannot read), and `--` has no `flow.toml` to read.
The pins move to the latest release, so a project whose pins agree on an older tag is shown the upgrade all the same; where the latest release cannot be read, they move to the newest tag among them.

## What it does

1. Probes, and reads the whole report: the environment, the project with its pins, the kit's version and layout, the proposals, the upgrade steps, the coverage line.
2. Plans in one message and asks once: which proposals to install, the log's name where none exists (`WORKLOG.md` unless you say otherwise), which evidence forms the project accepts, of the five the flow ships and your own words, whether copies the project keeps by hand may be redistributed with the repository (`library init --kept`, no unless you say so), where the project has documents, what its reviews hold them to, proposed from the documents for you to correct, and whether to take a pending upgrade step now.
3. Installs what was chosen, with the proposal's command as shown, and probes again.
4. Writes the bindings where they are absent: `flow init --log LOG`, then `library init --scan RECORDS --scan LOG --documents GLOB…` with the globs the probe found with a References section; an `init` refuses over an existing file, and `--force` is used only when you ask for a rewrite; `[evidence] forms` in `flow.toml` is edited to the forms you picked.
5. Appends a section `## Research records` to the instructions file, holding the paragraphs both inits printed in the project's words: where the records are and that they are read through the tool, that a state changes only through a transition, that the check runs before a commit, that the ranked list is the schedule, where the log is, what each evidence form means for the project; and, where the project has documents, a `### Reviews` part with your answers: the corpus and the documents a reader sees beyond the bound ones, which imports which, the regime conditions with their constants, the claims whose status recurs, the definitions compared, the class and its instances, the status labels, any rule of the project's own.
   Where the section exists it is re-read whole: what it lacks, `### Reviews` or an item of it, is added on your word, what is stale is named with the edit proposed, and nothing is rewritten without your word; a project with no documents yet gets `### Reviews` from a later run.
6. Adds the kit's block to `.pre-commit-config.yaml` — `repo: https://github.com/lividgreen/research-kit`, `rev:` the tag the probe prints, the hooks `flow-check` and `library-check` — installs the runner's hook and runs it once over all files; [Install](../install.md) has the block and the pins.
   The probe reads the file's lines, comments aside: a hook repo naming research-kit, or a checkout's path whose hooks are the kit's, is the kit's block already, re-checked for a hook it lacks, and a file whose `repo: local` hooks run the kit's scripts through a runner of the project's own is left as it is, since those hooks carry no `rev` and run the installed plugin's version; a file that only mentions research-kit in a comment gets the block.
7. Runs `flow check`, `library check` and `flow state`, and fixes or names any problem.
8. Reports what was written, installed and declined, each declined item with the command to do it later, the upgrade steps left pending, the first move, and `/formal:formal-init` as the next step where the probe found a Lean workspace.

A project that already keeps its research elsewhere — notes, a roadmap, a to-do list, a bibliography — is set up the same way first; its material is then brought into the records and the cards as a step of its own, by the skill's [`references/migration.md`](../../plugins/research/skills/research-init/references/migration.md): survey and propose before writing, classify by the kinds' own tests, carry the open work and every finding, the old measurements among them, and point at the settled, go through the commands wherever one exists, remove nothing, and end with the checks.

The agent runs each skill's script by its installed path; a Makefile target or a script outside the agent runs one by its path from the project root where the skills are installed into the project, as `python3 .agents/skills/flow/scripts/flow.py check` ([Install](../install.md#outside-the-agent)).

## Words

- **research-init** — the skill that sets a project up: it probes, proposes, re-checks what exists and adds what is missing, rewriting nothing without your word, and reports; `/research:research-init`.
- **probe** — the report `setup probe` prints: the environment, the project, the kit's version, the proposals, the upgrade steps and a coverage line; it writes and installs nothing.
- **pins** — the places a project pins the kit: the hooks' `rev`, the marketplace's `ref` and the version of each installed plugin; at the latest release, the skills' text and scripts are the checks' release and the newest.
- **`latest`** — the kit's branch that the release workflow moves to each release tag; a marketplace at it follows the releases and never the default branch's unreleased work.
- **required, recommended, optional** — the probe's three words for what the machine has: a required item is one the setup needs, a recommended one is proposed, an optional one serves what the project does; the project's own items read `present`, `absent`, `found` or `none`.
