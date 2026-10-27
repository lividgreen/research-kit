# research-kit

research-kit keeps a research project's ideas, open questions, tasks and results as checked Markdown files in its own repository.
It is built for one person working with one coding agent: Claude Code or Grok Build as plugins, Codex, GitHub Copilot, Cursor and the other [Agent Plugins](https://agent-plugins.org) clients, or any agent that reads [Agent Skills](https://agentskills.io).

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
| "What's next?" | The ranked list is refreshed, a reason for each rank, and the top task is drawn. |
| "Add Stuart and Humphries (1996) to the library; I read chapter 2." | A card for the book records how far it was read, and a citation of it is checked against that. |
| "Show me the dashboard." | The records and the cards open as a read-only page on localhost. |
| "Where were we?" | The session summary is printed, and the work goes on from the top of the list. |

In Claude Code each skill is also a slash command: `/research:research-init`, `/research:flow`, `/research:library` and the rest.

## Where next

- [Why research-kit](why.md): the failures in one research project each piece of the kit replaced, one story each
- [How to use](how-to-use.md): a research thread as you say it to the agent, from a remark at a talk to a result
- [Getting started](getting-started.md): a first project step by step, with the files it writes, a failed check, a library card and the dashboard
- [Install](install.md): the plugins for each agent that loads them, the skills for the others, the pre-commit hooks
- [Scope](scope.md): what the kit assumes, what the agent may do without asking, and how it compares with issue trackers, reference managers and notes vaults

## What is in the box

The [`research` plugin](../plugins/research/README.md):

- [flow](../plugins/research/skills/flow/SKILL.md): the records, their states, the check, the ranked index and the session summary
- [research-init](../plugins/research/skills/research-init/SKILL.md): the setup, run as `/research:research-init`
- [library](../plugins/research/skills/library/SKILL.md): one card per referred work, with how it was read and what it supports
- [dashboard](../plugins/research/skills/dashboard/SKILL.md): the records and the cards in a read-only local web page
- [method](../plugins/research/skills/method/SKILL.md), [design](../plugins/research/skills/design/SKILL.md) and [debug](../plugins/research/skills/debug/SKILL.md): optional working rules for review, terminology, documents and evidence, working with the owner, design and debugging

The [`formal` plugin](../plugins/formal/README.md), for a project that pairs its documents with a Lean 4 library:

- [handoff](../plugins/formal/skills/handoff/SKILL.md): writes and checks the prompt a prover session receives
- [land](../plugins/formal/skills/land/SKILL.md): checks what the session reports against the built tree before any document changes
- [formal-init](../plugins/formal/skills/formal-init/SKILL.md): the prover-side setup, run as `/formal:formal-init`
