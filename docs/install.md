# Install

Installing takes three steps: add the plugins or the skills to your agent, ask the agent to set the project up, and let the pre-commit hooks run the checks at each commit.
The agent runs each skill's script from the skill's own directory, so nothing is installed for it; the hooks install their own copy; the requirements below are what the machine needs.

## Requirements

### The `research` plugin

- **Required**: Python 3.11 or later, standard library only, for every script; git for the project; a pre-commit runner, `prek` or `pre-commit`, for the hooks (the setup proposes one where none is on PATH).
- **Recommended**: `markdownlint` (markdownlint-cli) on PATH, in which case a record write that adds a violation is reverted — with the project's configuration where one is bound or kept at the root, else a built-in one that lets a record's `summary:` stand as its title (the kit bundles no linter).
- **Optional**: `pdftotext` (poppler), or any command the project names in `library.toml`, for a kept PDF's text; the `markdown` package for the dashboard's rendered bodies (paragraphs otherwise); SQLite built with FTS5 for stemmed search (whole words otherwise).
- **Three optional environment variables** the library's online commands read: `LIBRARY_MAILTO`, a contact address sent in the User-Agent of every request the library makes, so every host called sees it; `OPENALEX_API_KEY` and `SEMANTIC_SCHOLAR_API_KEY`, each sent to its own interface alone; see [What goes online](network.md).

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

Add this repository as a marketplace, then install `research`, and `formal` where the project has a prover:

```text
/plugin marketplace add lividgreen/research-kit
/plugin install research@research-kit
/plugin install formal@research-kit
```

A repository enables it for everyone in its committed `.claude/settings.json`; each collaborator still installs it once, `claude plugin install research@research-kit --scope project`:

```json
{
  "extraKnownMarketplaces": {
    "research-kit": { "source": { "source": "github", "repo": "lividgreen/research-kit" } }
  },
  "enabledPlugins": { "research@research-kit": true, "formal@research-kit": true }
}
```

The skills are then `/research:flow`, `/research:library`, `/research:dashboard`, `/research:method`, `/formal:handoff`, `/formal:land` and so on, the prover agent `formal:prover`, and a skill runs its script by the path its text gives.
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
droid plugin marketplace add lividgreen/research-kit
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
codex plugin marketplace add lividgreen/research-kit
codex plugin add research@research-kit
codex plugin add formal@research-kit
```

Each plugin's `plugin.json` (under `plugins/<plugin>/`) is its Agent Plugins manifest, and `.agents/plugins/marketplace.json` lists both; `codex plugin marketplace upgrade` refreshes the marketplace for a new release.

#### GitHub Copilot

The Copilot CLI reads the same marketplace as Claude Code:

```sh
copilot plugin marketplace add lividgreen/research-kit
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

### A copy

Copy a skill directory into the project; the script inside it is self-contained, and the skill's `SKILL.md` is the whole of what the agent reads.
A copy is the one route that does not update itself.

## 2. The setup, by the agent

In Claude Code say `/research:research-init`; with another agent, ask it to set research-kit up in the project.
The [research-init](../plugins/research/skills/research-init/SKILL.md) skill probes the project and the machine, proposes what is missing and installs it only on your word, writes `flow.toml` and the records, `library.toml` and the cards, the log, the paragraphs for the instructions file and the hooks' block, runs the checks and reports.
The research-init skill lists what a setup requires, recommends and leaves optional.
With a Lean workspace, `/formal:formal-init` ([formal-init](../plugins/formal/skills/formal-init/SKILL.md)) follows the same way for the prover side.
[Getting started](getting-started.md) shows what the setup writes, command by command.

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

pre-commit, or `prek`, installs the kit at the pinned tag in an environment of its own at the first run, so the hooks need no other install; the runner itself comes from `pipx install pre-commit`, `uv tool install prek` or the system's packages, and the init proposes one where none is on PATH.
Each check reads its bindings file at the project root; a project with no `flow.toml`, `library.toml` or `formal.toml` leaves that hook out.
A bindings file names code that runs — the reflow module, the library's command and the command for a PDF's text, which the checks run, and `formal.toml`'s `[manifest] generate`, which the prover session runs — so a project's bindings are trusted as its hooks are: read them before running a check in a repository you did not write; [What runs](network.md#what-runs) lists all of it.
pre-commit and prek stash the unstaged changes while the hooks run and restore them after, so in a repository where several agent sessions work in one tree, one session's commit briefly reverts the files another is editing or reading; there, each session commits from a `git worktree` of its own and the main tree takes the commit with `git merge --ff-only`.
To update the hooks, set `rev` to the next tag from [Releases](https://github.com/lividgreen/research-kit/releases) (`pre-commit autoupdate` or `prek autoupdate` does it).

### The plugins at the hooks' tag

A marketplace added as `lividgreen/research-kit` follows the repository's default branch, while the hooks pin a tag, so between a push to `main` and a project's own bump its skills' text and scripts can be newer than its checks.
A project keeps the two at one tag by pinning the marketplace to the tag its `rev` names, in the form each agent documents:

| Agent | The marketplace at a tag |
| --- | --- |
| Claude Code | `/plugin marketplace add lividgreen/research-kit#v0.2.0`; in `.claude/settings.json`, `"ref": "v0.2.0"` beside `"repo"` in the source |
| Codex | `codex plugin marketplace add lividgreen/research-kit --ref v0.2.0` |
| GitHub Copilot | `copilot plugin marketplace add lividgreen/research-kit#v0.2.0`; in VS Code, `"lividgreen/research-kit#v0.2.0"` in `chat.plugins.marketplaces` |
| Factory Droid | `droid plugin marketplace add 'lividgreen/research-kit#v0.2.0'` |

A pinned marketplace updates to its tag and no further; the project moves it and the hooks' `rev` to the next tag together, in one commit where the pin is in a committed settings file.
In Claude Code the marketplace is one per machine, known by its name to every project on it, so a project moves its pin by adding it again at the next tag, `claude plugin marketplace add 'lividgreen/research-kit#<tag>' --scope project`, which points the marketplace at the tag in place and writes the `ref` into the project's settings, then `claude plugin update research@research-kit --scope project` (and `formal@research-kit`); every other project keeps the version it installed until it runs the update itself.
Editing the `ref` in `.claude/settings.json` alone moves nothing, since `claude plugin marketplace update` refreshes the tag the machine knows.
Never remove the marketplace to upgrade: `claude plugin marketplace remove research-kit` uninstalls the plugins installed from it for every project on the machine, whose settings still enable them, and deletes the project's own entry from `.claude/settings.json`.
Claude Code 2.1.310 behaves so.
Grok Build documents no ref for a marketplace, and an agent that installs from a clone or a copy holds whatever was checked out; there the plugin and the hooks move together by hand.
The setup probe, run from the installed plugin, says whether the hooks' `rev`, the marketplace's `ref` in the project's `.claude/settings.json` and the plugin's own version name one tag.

### Outside the agent

A Makefile target or a CI job runs the checks through the hooks, `prek run --all-files` or `pre-commit run --all-files`, which pin the tag and need no path to the kit.
A script that calls a skill's script for anything else runs it from the installed plugin, whose path moves with every version: Claude Code keeps it under `~/.claude/plugins/cache/research-kit/research/<version>/` (`CLAUDE_CODE_PLUGIN_CACHE_DIR` moves that root) and records each install, with its scope, project and `installPath`, in `~/.claude/plugins/installed_plugins.json`, where the `research@research-kit` entry of scope `local`, else `project`, for the repository, else the `user` one, names it (`CLAUDE_CONFIG_DIR` moves `~/.claude`).
Such a script checks that the entry's `version` is the tag the hooks pin before it runs anything.

research-kit installs no command and is not published to PyPI: the agent runs the scripts from their skills, and the pre-commit hooks build their own environment from this repository at the pinned tag; the `research-kit` project on PyPI is an unrelated one.
