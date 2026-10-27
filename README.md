# research-kit

**A kit for doing research with a coding agent.**
It keeps a project's ideas, questions, tasks, findings and cited works as checked Markdown in the repository, and ships as two plugins for coding agents.

[![tests](https://github.com/lividgreen/research-kit/actions/workflows/tests.yml/badge.svg)](https://github.com/lividgreen/research-kit/actions/workflows/tests.yml)
[![release](https://img.shields.io/github/v/release/lividgreen/research-kit?display_name=tag)](https://github.com/lividgreen/research-kit/releases)
[![docs](https://img.shields.io/badge/docs-research--kit.livid.work-blue)](https://research-kit.livid.work)
[![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin-D97757?logo=claude&logoColor=white)](docs/install.md#claude-code)
[![Agent Plugins 1.0](https://img.shields.io/badge/Agent_Plugins-1.0-4B5563)](https://agent-plugins.org)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-compatible-4B5563)](https://agentskills.io)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)](docs/install.md#requirements)
[![licence Apache-2.0](https://img.shields.io/badge/licence-Apache--2.0-blue)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23664863.svg)](https://doi.org/10.5281/zenodo.23664863)

## What is in the kit

The [`research` plugin](plugins/research/README.md), for any research project:

- **Research records.** Ideas, questions with kill criteria, tasks and findings, one Markdown file each, moved through their states by the `flow` command, with a ranked list of what to do next.
- **A reference library.** One card per cited work, recording how far it was read and what may be claimed from it.
- **Checks on every commit.** A hand-edited state, a broken link, a reference to a work with no card or to one nobody read: each fails the commit.
- **A dashboard.** The records and the cards as a read-only page on localhost.
- **Working rules.** Review, terminology, documents, evidence and working with the owner (`method`), design before building (`design`) and debugging to the root cause (`debug`).

The [`formal` plugin](plugins/formal/README.md), for a project with a Lean 4 library:

- **A checked handoff.** The prompt a prover session gets is checked before it is sent.
- **A verified landing.** What the session reports is checked against the built library before any document changes.

Each plugin has a setup skill that proposes what the project needs and writes it on your word.
Every tool is a single Python 3.11 script with no dependencies, and all the data is plain Markdown you can read without the kit.

## Supported agents

- **Native plugins**, skills and the prover agent: Claude Code, Grok Build and Factory Droid, which read Claude Code's plugin format.
- **[Agent Plugins](https://agent-plugins.org)**, the skills, and the prover agent in GitHub Copilot, OpenHands and Antigravity: Codex, GitHub Copilot (CLI and VS Code), Cursor, Kiro, OpenHands, Devin, Cline, Goose and Antigravity CLI.
- **[Agent Skills](https://agentskills.io) only**: OpenCode, Pi, Amp, Zed, Warp, Kilo Code and any other agent that reads `.agents/skills/`.

The agent needs a shell, since each skill runs its script with Python; [Install](docs/install.md) has each agent's commands.

## Why

research-kit grew out of a research project, a series of papers with a Lean 4 library written over months with one coding agent.
Its pieces are known techniques: an issue tracker's states and work-in-progress limits, kill criteria fixed before the work, a reference manager's cards, and checks that run on every commit.
What the project added is how they fit together, learned from what failed there.

With the flow in place:

- a session starts from a ranked list with a reason for each item, not from questions settled weeks before;
- state changes only through the tool, so the records no longer drift from what the project did;
- the agent reads a short summary and records by id, not the whole directory;
- a citation stands on how far the work was actually read;
- a prover's report is checked against the built library before a document relies on it.

[Why research-kit](docs/why.md) tells the story behind each.

## Install

The `research` plugin needs Python 3.11 or later and git; the `formal` plugin needs a Lean 4 project with `lean` and `lake` as well.
[Requirements](docs/install.md#requirements) lists them with what else is worth installing.

In Claude Code:

```text
/plugin marketplace add lividgreen/research-kit
/plugin install research@research-kit
```

In Codex:

```sh
codex plugin marketplace add lividgreen/research-kit
codex plugin add research@research-kit
```

In the GitHub Copilot CLI:

```sh
copilot plugin marketplace add lividgreen/research-kit
copilot plugin install research@research-kit
```

Install `formal` the same way for a project with a Lean library.
[Install](docs/install.md) has every other agent and the pre-commit hooks.

Then ask the agent to set research-kit up in the project (`/research:research-init` in Claude Code).

## How to use

You talk to the agent as you already do, and the skills fold the kit into that conversation:

| You say | What happens |
| --- | --- |
| "Set up research-kit in this project." | The project is probed, what is missing proposed, and on your word the records, the library and the hooks are written. |
| "At yesterday's talk someone claimed A might imply B. Keep that." | An idea record appears, with its source. |
| "Let's look into it." | The idea becomes a question with what would settle it, split into tasks you see before they are written. |
| "What's next?" | The ranked list is refreshed, a reason for each rank, and the top task is drawn. |
| "Add Stuart and Humphries (1996) to the library; I read chapter 2." | A card for the book records how far it was read, and a citation of it is checked against that. |
| "Show me the dashboard." | The records and the cards open as a read-only page on localhost. |
| "Where were we?" | The session summary is printed, and the work goes on from the top of the list. |

In Claude Code each skill is also a slash command: `/research:research-init`, `/research:flow`, `/research:library` and the rest.
[How to use](docs/how-to-use.md) follows a whole research thread, the prover's part included, and [Getting started](docs/getting-started.md) shows the commands the agent runs and the files they write.

## Documentation

The full documentation and guides are at **[research-kit.livid.work](https://research-kit.livid.work)**:

- [Why research-kit](docs/why.md): the failures in one research project each piece of the kit replaced
- [How to use](docs/how-to-use.md): a research thread as you say it to the agent
- [Getting started](docs/getting-started.md): a first project, step by step
- [Scope](docs/scope.md): what the kit assumes, what the agent may do without asking, and how it compares with issue trackers, reference managers and notes vaults
- [Install](docs/install.md): every agent, the hooks, updating
- [What goes online](docs/network.md): the commands that use the network and the hosts they call
- [Glossary](docs/glossary.md), [configuration files](docs/bindings.md), [check codes](docs/checks.md)
- The [research plugin](plugins/research/README.md) and the [formal plugin](plugins/formal/README.md): each feature with its skill and its commands
- [Development](docs/development.md) and the [changelog](CHANGELOG.md)

## Contributing and security

Issues and pull requests are welcome; [CONTRIBUTING.md](CONTRIBUTING.md) says what a change carries and how it is tested.
A vulnerability is reported privately, as [SECURITY.md](SECURITY.md) says, never in a public issue.

## Licence and citation

Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
To cite the kit, use [CITATION.cff](CITATION.cff) or the concept DOI [10.5281/zenodo.23664863](https://doi.org/10.5281/zenodo.23664863), which resolves to the latest version; a paper on the method is in preparation.

research-kit is not related to Apple's ResearchKit, a framework for medical studies on iOS.
