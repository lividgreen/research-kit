# research

The record side of research-kit: what a research project keeps in its own repository so that a coding agent works from it instead of from memory.
Ideas, questions, tasks and findings are Markdown records the `flow` command moves through their states; the works the project cites are cards in a library that records how far each was read; a dashboard shows both; three working rules say how the agent reviews, designs and debugs.
It needs nothing else, and the [`formal` plugin](../formal/README.md) builds on it for a project with a Lean 4 library.

In Claude Code 2.1.275 or later it installs in one step; [Install](../../docs/install.md) covers every other agent:

```text
/plugin install research --marketplace lividgreen/research-kit
```

Nine skills: four over a script each, two over the flow for a session's start and its freeze, three with no script behind them; the sections below take them one by one, and each tool has a page of its own in the documentation with its commands, the files it keeps, its bindings, its check and its words.

## Records that hold

Ideas, questions, tasks and findings are Markdown files, one per item, that the `flow` command creates and moves through their states.
You capture an idea, frame it as a question with a criterion (what would answer it, or show it wrong or impossible), split the question into tasks, close each task, and mint the finding that answers the question.
A finding names its evidence, such as a proved declaration or a script that asserts the result, and the check confirms that the evidence exists.

`flow check` fails when a hand-edited state leaves a record inconsistent, when a record points to an id that does not exist, when a finding's evidence does not resolve, when a rank has no reason, or when the index is out of date; it checks that the records hold together, not who wrote them, runs offline as a pre-commit hook, and its last line lists what it did not look at.
A generated index keeps a ranked list of open work with a reason for each rank, and `flow state` prints the summary a new session reads first, so the agent continues from the top of the list instead of asking where things stand.

The [`flow`](skills/flow/SKILL.md) skill, `/research:flow` in Claude Code; [The flow](../../docs/research/flow.md) is its page, and [Flow cards](../../docs/research/flow-cards.md) the specification of the records.

## A session's start and its freeze

A session starts with `/research:whatsnext`: what you left in the inbox is read and a record proposed for each item, the ranked list is refreshed under the focus you give, and the top work is drawn into the agent's hand.
It ends with `/research:freeze`: what the conversation found and no record holds is saved, `flow state --check` and the gates run, and the work is committed, so a cold session on another machine continues without asking.

The [`whatsnext`](skills/whatsnext/SKILL.md) and [`freeze`](skills/freeze/SKILL.md) skills; [What is next](../../docs/research/whatsnext.md) and [The freeze](../../docs/research/freeze.md) are their pages.

## A reference library that refuses an unread citation

`library` keeps one card per work the project refers to: a paper, a book, a preprint, a dataset, a piece of software.
A card records how far the work was actually read, what may be claimed from it and at which page, and what the project noted about it.
The reference list of each bound document is tied to the cards, so citing a work that has no card, or one marked unread without naming the source it is known through, fails the check.
Optional online lookups (arXiv, Crossref, OpenAlex and others) fill in the metadata, find open copies and watch for new citing work.

The [`library`](skills/library/SKILL.md) skill, `/research:library` in Claude Code; [The library](../../docs/research/library.md) is its page, and [Library cards](../../docs/research/library-cards.md) the specification of a card.

## A dashboard

`dashboard` serves the records and the cards as a read-only page on localhost: the ranked list, each record with its links and back-references, each card with its notes and extracts, and the verdicts of `flow check` and `library check`.
Every page is the answer of a command with `--json`, so the page and the command line cannot disagree.

The [`dashboard`](skills/dashboard/SKILL.md) skill, `/research:dashboard` in Claude Code; [The dashboard](../../docs/research/dashboard.md) is its page.

## A setup the agent proposes and you approve

`/research:research-init` inspects the project and the machine, proposes what is missing, and installs nothing without your confirmation.
It writes the bindings files, the records and the cards directories, the paragraphs for the agent's instructions file and the pre-commit hooks, then runs the checks and reports.

The [`research-init`](skills/research-init/SKILL.md) skill, `/research:research-init` in Claude Code; with another agent, ask it to set research-kit up in the project; [The research setup](../../docs/research/research-init.md) is its page.

## Working rules for the agent

Three skills with no script behind them, each triggered by the conversation itself.
`method` says how to review, what to call things, what a document holds and when a landed result enters one, what counts as evidence, what to check before pricing a piece of work, how to change a target honestly when a wall is hit, and how to work with the project's owner.
`design` runs a design pass before anything new is built, whenever you say "let's add X" or "what about Y".
`debug` insists on the root cause before a fix, and again before anything is called fixed.
They came out of one research project and are optional; the tools work without them.

[`method`](skills/method/SKILL.md), [`design`](skills/design/SKILL.md) and [`debug`](skills/debug/SKILL.md), as `/research:method`, `/research:design` and `/research:debug` in Claude Code; [The working rules](../../docs/research/working-rules.md) is their page.

## The scripts

The four scripts are single Python 3.11 files in their skills' `scripts/` directories, standard library only; the agent runs them through their skills, and the pre-commit hooks run `flow check` and `library check` from a copy of their own.
A project binds them in `flow.toml` and `library.toml` at its root, which [The flow](../../docs/research/flow.md) and [The library](../../docs/research/library.md) show whole; the skills name no project path themselves.
