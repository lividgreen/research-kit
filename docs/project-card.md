---
title: research-kit
summary: A kit for doing research with a coding agent — a project's ideas, questions, tasks, findings and cited works kept as checked Markdown in its own repository.
tags: [coding-agents, agent-skills, research, lean4]
status: active
---

## What it is

research-kit keeps a research project's ideas, questions, tasks, findings and cited works as checked Markdown files in the project's own repository.
It ships as two plugins for coding agents and is built for one person working with one coding agent.
The documentation, install instructions and changelog are on the [project site](index.md).

A coding agent starts every session cold.
It asks again about things that were settled, a notes file drifts away from what the project did, and a paper cites a work nobody read past the abstract.
The kit is what replaced each of those failures in one research project: a series of papers with a Lean 4 library, written over months with one coding agent.

## What is in the kit

The **`research` plugin**, for any research project:

- **Research records.** Ideas, questions with kill criteria, tasks and findings, one Markdown file each, moved through their states by the `flow` command, with a ranked list of what to do next and a log a cold session starts from.
- **A reference library.** One card per cited work, recording how far it was read and what may be claimed from it, and each document's citations checked against its own reference list.
- **Checks on every commit.** A hand-edited state, a broken link, a reference to a work with no card or to one nobody read: each fails the commit.
- **A dashboard.** The records and the cards as a read-only page on localhost.
- **Working rules.** Review, terminology, documents and evidence, working with the project's owner, design before building, and debugging to the root cause.

The **`formal` plugin**, for a project with a Lean 4 library:

- **A checked handoff.** The prompt a prover session gets is checked before it is sent.
- **A verified landing.** What the session reports is checked against the built library before any document changes.
- **Checks on the documents.** Every Lean name a document cites resolves, every section a Lean file cites exists, and what ships carries none of the project's internal vocabulary.

[The checks](checks.md) lists everything the checks verify.

## How it works

You talk to the agent as you already do, and the skills fold the kit into that conversation: "Where were we?" prints the session summary and the work goes on from the top of the ranked list; "Add this book to the library; I read chapter 2" writes a card, and a citation of that book is then checked against how far it was read.
[How to use it](how-to-use.md) has more.

Every tool is a single Python 3.11 script with no dependencies, and all the data is plain Markdown that can be read without the kit.

## Where it runs

Claude Code, Grok Build and Factory Droid load the plugins natively; Codex, GitHub Copilot, Cursor and other agents load them as Agent Plugins, and any agent that reads Agent Skills can use the skills alone.
[Install](install.md) has each agent's commands.
The kit is licensed under Apache-2.0.
