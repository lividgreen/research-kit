# research-kit

![research-kit logo](docs/assets/logo/logo.svg)

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

A coding agent starts every session cold.
It asks again about things settled weeks before, a notes file drifts from what the project did, and a paper cites a work nobody read past the abstract.
With research-kit, a session starts from a ranked list, a record changes state only through the tool, and a citation stands on how far the work was read.
[Why research-kit](docs/why.md) tells how each failure became a check.

## How to use

You talk to the agent as you already do, and the skills fold the kit into that conversation:

| You say | What happens |
| --- | --- |
| "Set up research-kit in this project." | The project is probed, what is missing proposed, and on your word the records, the library and the hooks are written. |
| "At yesterday's talk someone claimed A might imply B. Keep that." | An idea record appears, with its source. |
| "Let's look into it." | The idea becomes a question with what would settle it, split into tasks you see before they are written. |
| "What's next? Let's focus on the proofs." | What you left in the inbox is read and a record proposed for each item, the ranked list is refreshed under that focus with a reason for each rank, and the top work is drawn. |
| "Add Stuart and Humphries (1996) to the library; I read chapter 2." | A card for the book records how far it was read, and a citation of it is checked against that. |
| "Show me the dashboard." | The records and the cards open as a read-only page on localhost. |
| "Where were we?" | The session summary is printed, and the work goes on from the top of the list. |
| "Let's freeze here." | What the session found and did not record is saved to the records, the checks run, and the work is committed for the next session. |

In Claude Code each skill is also a slash command: `/research:research-init`, `/research:whatsnext`, `/research:freeze`, `/research:flow`, `/research:library` and the rest.
[How to use](docs/how-to-use.md) follows a whole research thread, the prover's part included, and [Getting started](docs/research/getting-started.md) shows the commands the agent runs and the files they write.

## What is in the kit

The [`research` plugin](plugins/research/README.md), for any research project:

- **Research records.** Ideas, questions with a criterion of what would answer them, tasks and findings, one Markdown file each, moved through their states by the `flow` command, with a ranked list of what to do next.
- **A reference library.** One card per cited work, recording how far it was read and what may be claimed from it.
- **Checks on every commit.** A hand-edited state, a broken link, a reference to a work with no card or to one nobody read: each fails the commit.
- **A dashboard.** The records and the cards as a read-only page on localhost.
- **Reviews.** An audit of the documents against one another, scrutiny of one argument, and each claim about a named external result held to its primary source.
- **Working rules.** Review, terminology, documents, evidence and working with the owner, design before building, and debugging to the root cause.

The [`formal` plugin](plugins/formal/README.md), for a project with a Lean 4 library:

- **A checked handoff.** The prompt a prover session gets is checked before it is sent.
- **A verified landing.** What the session reports is checked against the built library before any document changes.
- **Checks on the documents.** Every Lean name a document cites resolves, every section a Lean file cites exists, and what ships carries none of the project's internal vocabulary, each a pre-commit hook.

Each plugin has a setup skill that proposes what the project needs and writes it on your word.
Every tool is a single Python 3.11 script with no dependencies, and all the data is plain Markdown you can read without the kit.

## Install

The `research` plugin needs Python 3.11 or later and git; the `formal` plugin needs a Lean 4 project with `lean` and `lake` as well.
[Requirements](docs/install.md#requirements) lists them with what else is worth installing.

In Claude Code:

```text
/plugin marketplace add lividgreen/research-kit#latest
/plugin install research@research-kit
```

In Codex:

```sh
codex plugin marketplace add lividgreen/research-kit --ref latest
codex plugin add research@research-kit
```

In the GitHub Copilot CLI:

```sh
copilot plugin marketplace add lividgreen/research-kit#latest
copilot plugin install research@research-kit
```

Install `formal` the same way for a project with a Lean library.
Then ask the agent to set research-kit up in the project (`/research:research-init` in Claude Code).

The agent needs a shell, since each skill runs its script with Python.
[Install](docs/install.md) has every other agent and the pre-commit hooks.

## Documentation

The full documentation is at **[research-kit.livid.work](https://research-kit.livid.work)**, and [every page](docs/README.md) is listed there.
[Scope](docs/scope.md) says what the kit assumes, what the agent may do without asking, and what it is not.
[What goes online](docs/network.md) names the commands that use the network and the hosts they call.

## Licence and citation

Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
To cite the kit, use [CITATION.cff](CITATION.cff) or the concept DOI [10.5281/zenodo.23664863](https://doi.org/10.5281/zenodo.23664863), which resolves to the latest version; a paper on the method is in preparation.
Issues and pull requests are welcome; [CONTRIBUTING.md](CONTRIBUTING.md) says what a change carries and how it is tested.
A vulnerability is reported privately, as [SECURITY.md](SECURITY.md) says, never in a public issue.

research-kit is not related to Apple's ResearchKit, a framework for medical studies on iOS.
