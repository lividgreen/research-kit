# research-kit

research-kit keeps a research project's ideas, open questions, tasks and results as checked Markdown files in its own repository.
It is built for one person working with one coding agent: Claude Code, Grok Build or Factory Droid as plugins, Codex, GitHub Copilot, Cursor and the other [Agent Plugins](https://agent-plugins.org) clients, or any agent that reads [Agent Skills](https://agentskills.io).

A coding agent starts every session cold.
It asks again about things that were settled, a notes file drifts away from what the project did, and a paper cites a work nobody read past the abstract.
With research-kit, each idea, question, task and finding is one Markdown file, created and moved through its states by the `flow` command.
`flow check` runs on every commit and fails when a hand edit leaves a record inconsistent, a link points nowhere or the index is out of date.
A generated index ranks the open work, so the agent starts each session from the top of that list.
The `library` command keeps one card per cited work, recording how far it was read, and ties each document's reference list to those cards.
Everything is plain Markdown in git, and each tool is a single Python 3.11 script with no dependencies.

## Try it

Install the plugin ([Install](install.md)), open your agent in a project and talk to it; each line below is what you might say, and the skill it brings in does the rest:

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

## Where next

- [Why research-kit](why.md): the failures in one research project each piece of the kit replaced, one story each
- [How to use](how-to-use.md): a research thread as you say it to the agent, from a remark at a talk to a result
- [Getting started](research/getting-started.md): a first project step by step, with the files it writes, a failed check, a library card and the dashboard
- [Install](install.md): the plugins for each agent that loads them, the skills for the others, the pre-commit hooks
- [Scope](scope.md): what the kit assumes, what the agent may do without asking, and how it compares with issue trackers, reference managers and notes vaults

## What is in the box

- The [`research` plugin](../plugins/research/README.md), for any research project: the records and their flow, the reference library, the checks on every commit, the dashboard, a session's start and its freeze, three reviews, and three working rules, twelve skills in all.
  [Getting started](research/getting-started.md) walks through a first project, and each tool has its page: [the setup](research/research-init.md), [the flow](research/flow.md) and its [cards](research/flow-cards.md), [what is next](research/whatsnext.md) and [the freeze](research/freeze.md), [the audit](research/audit.md), [scrutiny](research/scrutinize.md) and [the attribution check](research/attribution.md), [the library](research/library.md) and its [cards](research/library-cards.md), [the dashboard](research/dashboard.md), [the working rules](research/working-rules.md).
- The [`formal` plugin](../plugins/formal/README.md), for a project that pairs its documents with a Lean 4 library: a handoff to a prover session that is checked before it is sent, a landing that reads the built tree before any document changes, and checks on the documents, three skills with the prover agent and the manifest generator.
  Its pages are [the setup](formal/formal-init.md), [the handoff](formal/handoff.md) and [the landing](formal/land.md).

Every page is listed in the [documentation](README.md), and each skill's own page is what the agent reads.
