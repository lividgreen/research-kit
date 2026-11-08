# Install

Installing takes three steps: add the plugins or the skills to your agent, ask the agent to set the project up, and let the pre-commit hooks run the checks at each commit.
The agent runs each skill's script from the skill's own directory, so nothing is installed for it; the hooks install their own copy; the requirements below are what the machine needs.

## Requirements

### The `research` plugin

- **Required**: Python 3.11 or later, standard library only, for every script; git for the project; a pre-commit runner, `prek` or `pre-commit`, for the hooks (the setup proposes one where none is on PATH).
- **Recommended**: `markdownlint` (markdownlint-cli) on PATH, in which case a record write that adds a violation is reverted — with the project's configuration where one is bound or kept at the root, else a built-in one that lets a record's `summary:` stand as its title (the kit bundles no linter).
- **Optional**: `pdftotext` (poppler), or any command the project names in `library.toml`, for a kept PDF's text; the `markdown` package for the dashboard's rendered bodies (paragraphs otherwise); SQLite built with FTS5 for stemmed search (whole words otherwise).
- **Optional environment variables** for the library's online commands: `LIBRARY_MAILTO`, `OPENALEX_API_KEY` and `SEMANTIC_SCHOLAR_API_KEY`; [What goes online](network.md) says where each is sent.

Lean, a prover or a build are never needed by the `research` plugin; the declaration manifest the flow reads is the project's.

### The `formal` plugin

Everything the `research` plugin needs, with its setup done first, and:

- **Required**: a Lean 4 project (a Lake workspace with its lakefile) under the project root, with `lean` and `lake` on PATH; the manifest generator, `DeclManifest.lean`, is copied into it by `/formal:formal-init` and run there after a build.
- **Recommended**: [`elan`](https://github.com/leanprover/elan), which installs `lean` and `lake` at the toolchain the workspace pins; a Lean language server registered for the agent in the project's `.mcp.json`, such as [lean-lsp-mcp](https://github.com/oOo0oOo/lean-lsp-mcp), since the prover agent works with whatever prover tools are registered and is blind without them.

## 1. The plugins or the skills, by agent

An agent takes the kit in one of three ways: as a plugin in its own format, as an [Agent Plugins](https://agent-plugins.org) 1.0 package, or as bare [Agent Skills](https://agentskills.io).
Every route needs an agent that can run shell commands, since each skill runs its script with Python.

### Native plugins: Claude Code's format

Claude Code, Grok Build and Factory Droid read Claude Code's marketplace and plugin manifests, `.claude-plugin/marketplace.json` and each plugin's `.claude-plugin/plugin.json`, and load the whole plugin: the skills and the `formal` plugin's `prover` agent.

#### Claude Code

Add this repository as a marketplace at `latest`, the branch each release moves to its tag ([Following the releases](#following-the-releases)), then install `research`, and `formal` where the project has a prover:

```text
/plugin marketplace add lividgreen/research-kit#latest
/plugin install research@research-kit
/plugin install formal@research-kit
```

A repository enables it for everyone in its committed `.claude/settings.json`; each collaborator still installs it once, `claude plugin install research@research-kit --scope project`:

```json
{
  "extraKnownMarketplaces": {
    "research-kit": { "source": { "source": "github", "repo": "lividgreen/research-kit", "ref": "latest" } }
  },
  "enabledPlugins": { "research@research-kit": true, "formal@research-kit": true }
}
```

From Claude Code 2.1.275, `/plugin install research --marketplace lividgreen/research-kit` adds the marketplace and installs in one step.
A marketplace added so follows the default branch; the setup probe names the move to `latest`.
The skills are then `/research:flow`, `/research:library`, `/research:dashboard`, `/research:method`, `/formal:handoff`, `/formal:land` and so on, the prover agent `formal:prover`, and a skill runs its script by the path its text gives.
A plugin's skills and agents load when a session starts, so restart the session after an install or an update, before the next handoff or transition; in the session that installed `formal`, the `formal:prover` agent type is not loaded yet and the `handoff` skill takes its general-purpose fallback.
The repository has no `bin/` directory on purpose: claude.ai and Cowork refuse a plugin that has one.
A plugin is updated only when its `version` changes, so every release bumps every plugin's version (see [Development](development.md#releases)), and a user runs `/plugin marketplace update research-kit` or turns auto-update on.

#### Grok Build

Grok asks to trust a plugin whose skills run code, which `--trust` grants; it loads the `prover` agent from the plugin's `agents/`, on the session's own model:

```sh
grok plugin marketplace add lividgreen/research-kit
grok plugin install research@research-kit --trust
grok plugin install formal@research-kit --trust
```

#### Factory Droid

```sh
droid plugin marketplace add 'lividgreen/research-kit#latest'
droid plugin install research@research-kit
droid plugin install formal@research-kit
```

### Agent Plugins

Each plugin's `plugin.json` and its `skills/` make an Agent Plugins 1.0 package, which the agents below read.
The format carries skills and MCP servers, so these agents load the skills; agents are outside it, and a client reads one only from a directory of its own in the plugin.
The `formal` plugin carries the `prover` there for GitHub Copilot (`com.github.copilot/agents/`), OpenHands (`dev.openhands/agents/`) and Antigravity (`com.google.antigravity/agents/`, named in its `agents.json`, with the tools Antigravity otherwise withholds from an agent); in the other agents you open the prover session yourself and give it the checked prompt.

#### Codex

Add this repository as a marketplace, then install `research`, and `formal` where the project has a prover:

```sh
codex plugin marketplace add lividgreen/research-kit --ref latest
codex plugin add research@research-kit
codex plugin add formal@research-kit
```

Each plugin's `plugin.json` (under `plugins/<plugin>/`) is its Agent Plugins manifest, and `.agents/plugins/marketplace.json` lists both; `codex plugin marketplace upgrade` refreshes the marketplace for a new release.

#### GitHub Copilot

The Copilot CLI reads the same marketplace as Claude Code:

```sh
copilot plugin marketplace add lividgreen/research-kit#latest
copilot plugin install research@research-kit
copilot plugin install formal@research-kit
```

In VS Code, add the repository to the `chat.plugins.marketplaces` setting, then install `research` and `formal` from the Extensions view (search `@agentPlugins`):

```json
{ "chat.plugins.marketplaces": ["lividgreen/research-kit"] }
```

#### Cursor

A team imports the repository as a marketplace: Dashboard, Plugins & MCPs, Team Marketplaces, Import from Repo, with `https://github.com/lividgreen/research-kit`; Cursor reads `.cursor-plugin/marketplace.json`.
On your own, copy `plugins/research`, and `plugins/formal` where the project has a prover, from a clone into `~/.cursor/plugins/local/` and run *Developer: Reload Window*; `npx skills add lividgreen/research-kit -a cursor` installs the same skills.

#### Kiro

Clone the repository, then in the Powers panel choose *Add Custom Power*, *Import power from a folder*, and select `plugins/research`, and `plugins/formal` where the project has a prover.

#### OpenHands

OpenHands, from `openhands-sdk` 1.49.2, loads a plugin from a directory of a repository: `github:lividgreen/research-kit/plugins/research`, and `github:lividgreen/research-kit/plugins/formal` where the project has a prover.

#### Devin

Devin Desktop, which was Windsurf, and the Devin CLI install a plugin from a directory of a repository:

```sh
devin plugins install lividgreen/research-kit#plugins/research
devin plugins install lividgreen/research-kit#plugins/formal
```

#### Cline and Goose

Both load plugins from `~/.agents/plugins/`: copy `plugins/research`, and `plugins/formal` where the project has a prover, from a clone into that directory.
Cline reads nothing else, so that a repository it opens cannot load a plugin; Goose also reads a project's `.agents/plugins/`.

#### Antigravity CLI

Google's Antigravity CLI installs a plugin from a local directory: from a clone, `agy plugin install ./research-kit/plugins/research`, and `./research-kit/plugins/formal` where the project has a prover.

### Agent Skills only

OpenCode, Pi, Amp, Zed, Warp and Kilo Code read skills, not plugins.
Every one of them reads `.agents/skills/` in the project and `~/.agents/skills/`, which is where the [`skills`](https://skills.sh) CLI installs them, symlinked to one canonical copy by default (`--copy` copies instead):

```sh
npx skills add lividgreen/research-kit                    # interactive: pick skills and agents
npx skills add lividgreen/research-kit --skill flow --skill library
npx skills add lividgreen/research-kit -a opencode -a pi  # the agents to install for
npx skills add lividgreen/research-kit -g -y               # every project, no prompts
```

The scripts need Python 3.11 and run by path; this route installs no command, and the agent needs none.
The `skills` CLI's [agents table](https://github.com/vercel-labs/skills/blob/main/docs/agents.md) lists some seventy agents with their project and global directories; `npx skills add … -a <agent>` names any of them.
The `handoff` skill calls the `land` skill's script, so the two are installed together (`--skill handoff --skill land`).
The `whatsnext` and `freeze` skills run the `flow` skill's script, so they are installed with it (`--skill flow --skill whatsnext --skill freeze`), and the `attribution` skill runs the `library` skill's (`--skill library --skill attribution`).

### A copy

Copy a skill directory into the project; the script inside it is self-contained, and the skill's `SKILL.md` is the whole of what the agent reads.
A copy is the one route that does not update itself.

## 2. The setup, by the agent

In Claude Code say `/research:research-init`; with another agent, ask it to set research-kit up in the project.
The setup probes the project and the machine, proposes what is missing, installs it only on your word, writes the bindings files, the paragraphs for the instructions file and the hooks' block, runs the checks and reports.
[The research setup](research/research-init.md) says what it requires, recommends and leaves optional, and [Getting started](research/getting-started.md) shows what it writes, command by command.
With a Lean workspace, `/formal:formal-init` follows for the prover side ([The formal setup](formal/formal-init.md)).

## 3. The hooks

`.pre-commit-hooks.yaml` exposes `flow-check`, `library-check` and `formal-check`, and with a prover's documents and register bound in `formal.toml`, `formal-cite`, `formal-anchors` and `formal-register`; a project pins them by `rev` and keeps no copy of the scripts:

```yaml
- repo: https://github.com/lividgreen/research-kit
  rev: <tag>
  hooks:
    - id: flow-check
    - id: library-check
    - id: formal-check   # with a prover
    - id: formal-cite    # with [documents] bound
    - id: formal-anchors # with [anchors] keys bound
    - id: formal-register # with [[register.class]] bound
```

pre-commit, or `prek`, installs the kit at the pinned tag in an environment of its own at the first run, so the hooks need no other install; the runner itself comes from `pipx install pre-commit`, `uv tool install prek` or the system's packages, and the setup proposes one where none is on PATH.
Each check reads its bindings file at the project root; a project with no `flow.toml`, `library.toml` or `formal.toml` leaves that hook out.
A bindings file names code that runs — the reflow module, the library's command and the command for a PDF's text, which the checks run, and `formal.toml`'s `[manifest] generate`, which the prover session runs — so a project's bindings are trusted as its hooks are: read them before running a check in a repository you did not write; [What runs](network.md#what-runs) lists all of it.
To update the hooks, set `rev` to the latest tag from [Releases](https://github.com/lividgreen/research-kit/releases) (`pre-commit autoupdate` or `prek autoupdate` does it); the plugins follow the releases through the marketplace's `latest`, as the next section says.

A plugin-install project that wants one version everywhere may write its hooks the other way, as `repo: local` hooks with `language: system`, each `entry` a runner of the project's own followed by the script's command, so the hooks run the installed plugin's scripts and the marketplace's `ref` is the one pin; the kit ships no such runner, and the project's finds the script under the agent's plugin cache (see *Outside the agent* below).

```yaml
- repo: local
  hooks:
    - id: flow-check
      name: flow check
      language: system
      entry: scripts/kit.py flow check   # the project's own runner, then the script's command
      pass_filenames: false
```

The setup probe then reads the hooks as local, running the installed plugin's scripts, and holds the plugins' pins alone, saying that no hook pins the kit by `rev`.

### Following the releases

A marketplace added as `lividgreen/research-kit` follows the repository's default branch, which carries merged work before its release under the last release's version, so a plugin updated from it can run text and scripts no release has, and the cache may keep an older copy of the same version.
The kit keeps a branch `latest` that the release workflow moves to each release tag, so a marketplace at `latest` follows the releases and nothing else; a project declares it once, in the form each agent documents:

| Agent | The marketplace following the releases |
| --- | --- |
| Claude Code | `claude plugin marketplace add 'lividgreen/research-kit#latest' --scope project`, which writes `"ref": "latest"` beside `"repo"` in the source of `.claude/settings.json` |
| Codex | `codex plugin marketplace add lividgreen/research-kit --ref latest` |
| GitHub Copilot | `copilot plugin marketplace add lividgreen/research-kit#latest`; in VS Code, `"lividgreen/research-kit#latest"` in `chat.plugins.marketplaces` |
| Factory Droid | `droid plugin marketplace add 'lividgreen/research-kit#latest'` |

A release then reaches the project by updating the marketplace and the plugins: in Claude Code `claude plugin marketplace update research-kit` (or auto-update turned on for the marketplace), then `claude plugin update research@research-kit --scope project` and the same for `formal@research-kit`, then a restart.
The restart is literal: until it, the session runs the old skills' text against the new scripts; a session that must mint a record before its restart runs the new version's script by its cache path, as the skills say to anyway, and the records it writes pass the new check.
Local hooks running the installed plugin's scripts follow the plugins with nothing to move; remote hooks pin a tag by `rev`, since pre-commit takes no branch as a pin, and `prek autoupdate` or `pre-commit autoupdate` moves it to the latest release in the project's next commit.
Where the release changes the records' model, `flow-check` at the new version fails every commit that touches a record until the records are in the new form, so the project's next commit carries the migration; a project that must commit before it runs that commit with `SKIP=flow-check` (prek and pre-commit read it) and says so in the log entry.
`flow task`, `flow state` and `flow show` run on an unmigrated tree at the new version, so the migration task is minted first; `flow doctor --fix` then writes the mechanical part of the migration and lists the rest ([The flow](research/flow.md#flow-doctor)).
Grok Build documents no ref for a marketplace, and an agent that installs from a clone or a copy holds whatever was checked out; there the plugin and the hooks move by hand.
The setup probe, run from the installed plugin, asks GitHub for the kit's latest release and says whether the marketplace follows `latest`, and whether the hooks' `rev`, the version of each plugin Claude Code installed for the project and the plugin's own version are at the latest release.
A marketplace at a tag, or at no ref, is named as off with the move to `latest`, and each other pin that is off with its step, beside the releases from the oldest pin up to the latest whose **Upgrading** paragraphs to read.
Where the latest release cannot be read, offline or refused, the probe says so and compares the pins among themselves, against the newest of them; `formal probe` says the same of the `formal` plugin ([The research setup](research/research-init.md#the-pins-and-the-upgrade-steps)).

In Claude Code the marketplace is one per machine, known by its name to every project on it, and a project pinned to a tag moves to `latest` in four steps:

1. Edit the `ref` to `latest` in every settings file that holds the marketplace's entry: the project's `.claude/settings.json`, and the user's `~/.claude/settings.json` where the user's settings declare it too.
   The `add` of the next step refuses while an entry elsewhere names another ref (`its source doesn't match its extraKnownMarketplaces entry in user or managed settings`), and writes the `ref` itself only where no other settings file carries one.
2. `claude plugin marketplace add 'lividgreen/research-kit#latest' --scope project` points the marketplace at `latest` in place, re-cloning it there.
   It answers `Marketplace 'research-kit' already on disk — declared in project settings`, which reads as a no-op while it has moved the clone.
3. `claude plugin update research@research-kit --scope project`, and the same for `formal@research-kit`, moves the project's plugins to the latest release; every other project on the machine keeps the version it installed until it runs the update itself.
4. Run the setup probe, which says whether the pins are at the latest release and what of the migration is left (`flow doctor`'s count and a stale index), and restart the session before the next transition.

Editing the `ref` in `.claude/settings.json` alone moves nothing, since `claude plugin marketplace update` refreshes the ref the machine knows.
Never remove the marketplace to upgrade: `claude plugin marketplace remove research-kit` uninstalls the plugins installed from it for every project on the machine, whose settings still enable them, and deletes the project's own entry from `.claude/settings.json`.
Claude Code 2.1.318 behaves so.

### Several sessions in one tree

pre-commit and prek stash the unstaged changes while the hooks run and restore them after, so where several agent sessions work in one tree, one session's commit briefly reverts the files another is editing or reading; there, each session commits from a `git worktree` of its own and the main tree takes the commit with `git merge --ff-only`.
A session opened in a subdirectory of the repository, in its own directory with its own `.claude` settings, is gated by the same hooks at its commits, while the plugins the root's settings enable are disabled for it, since Claude Code reads a project's settings from the directory the session opened in; `claude plugin list` there shows them so.
Such a session runs the checks as the hooks do, from the root: `prek run flow-check --all-files` and `prek run library-check --all-files` (or `pre-commit run …`), and reads a failure by its code on [The flow](research/flow.md) or [The library](research/library.md) page; a transition is run by the session that holds the plugins, which draws and makes the task for the one that did the work.

### Outside the agent

A Makefile target or a CI job runs the checks through the hooks, `prek run --all-files` or `pre-commit run --all-files`, which pin the tag and need no path to the kit.
For anything else, a skill's script runs by its path from the project root where the skills are installed into the project directory: `npx skills add` puts them in `.agents/skills/`, and Claude Code reads a project's `.claude/skills/`.

```sh
python3 .agents/skills/flow/scripts/flow.py check
python3 .claude/skills/flow/scripts/flow.py check
```

The other scripts lie under their skills the same way: `library/scripts/library.py`, `dashboard/scripts/dashboard.py`, and the `formal` plugin's `land/scripts/formal.py`.
Under a plugin install a script sits in the agent's plugin cache instead, Claude Code's `~/.claude/plugins/cache/research-kit/<plugin>/<version>/skills/…` (`CLAUDE_CODE_PLUGIN_CACHE_DIR` moves that root), a path that changes with each version; so a project that runs the scripts outside the agent installs the skills into the project directory.
A project that stays on the plugin install and wants a Makefile target writes its own small runner, which finds the script under the plugin cache at the pinned version, the probe's `pins at one tag` holding the pins together; the kit ships no runner.

research-kit installs no command and is not published to PyPI: the agent runs the scripts from their skills, and the pre-commit hooks build their own environment from this repository at the pinned tag; the `research-kit` project on PyPI is an unrelated one.
