---
name: freeze
description: Freeze a session so a cold one can continue it — save what the work needs that the conversation alone holds, check the records with `flow state --check`, sweep what the session made stale, run the gates and commit, then report item by item. Use as `/research:freeze`, when the person says to freeze, wrap up, stop for now or save the session, and before a session ends that changed the records or the documents. Ranks nothing; the next list is the `whatsnext` skill's.
license: Apache-2.0
compatibility: The `flow` skill beside this one, whose script it runs; git for the check, the commit and the push.
metadata:
  version: "0.5.0"
  requires: flow
---

# The freeze

A session is frozen when a clone of the repository on another computer could continue from it: could a cold session, reading only the inbox, the ranked list and the log's top State paragraph, go on without asking?
That clone test rules out whatever does not travel: the agent's memory, the scratchpad, an untracked store, a subagent still running, a local tool's state.
The one rule is to save what is important for the work, anything useful the session found and did not record.
`flow …` below is the `flow` skill's `scripts/flow.py`, run by its path from the project root as that skill says.

1. **The records say what the session knows.**
   The log's top State paragraph is current and its next action names the fresh session's first move; where work happened after the entry, it is extended or a new entry added with `flow log add FILE`.
   `flow touched --unnamed` lists the records changed since the newest committed entry that no entry names yet, the ids the entry is to name; `--ids` prints them on one line.
   At the month's first freeze, `flow log archive --before DATE` moves the older entries.
2. **Flush what only the context holds.**
   Inventory the conversation turn by turn, the person's messages and the replies both, under the test: if the transcript were deleted now, would anything the person said, or anything the person was told, be lost?
   Each item goes to its home by kind: an idea in the person's words, verbatim and dated (`flow capture`); a ruling where the project keeps its rules; a reading given in a reply into the body of the record it is about, with its standing; a correction as a dated line in the record; an unanswered question as a question or an idea; a preference about the process to the agent's memory.
   Then close the lifecycle of everything the session created: a task made, aborted or returned with a note, an idea consumed or left in the heap.
   A freeze ranks nothing: a question framed is named unranked, and the list is the `whatsnext` skill's.
   A directive the next session should start from goes to the inbox, one directive, never a summary of the session.
3. **Sweep by meaning.**
   Search the surfaces a reader sees, the documents and the published pages, for the claims this session made stale, by the claims' own words, not only the files the session already touched.
4. **The checks and the gates, by exit code.**
   `flow state --check` decides what a machine can see: the log's top entry dated today where the tree changed since the newest committed entry, and every record changed since then named by an entry; it prints each hand's active tasks and drawn ideas for the State paragraph and fails on none.
   It exits 1 on a failure, 2 where a part could not be decided, never read as clean; `flow check` and the project's other checks run beside it.
5. **A commit with named paths, then the push as the backup.**
   Steps 2 to 5 run even on a clean tree: a clean tree says nothing about what the conversation still holds.
   A push stops on a non-fast-forward rather than forcing.
6. **Report, as the turn's final output.**
   The tree, the gates by exit code, the inbox directive or "none", and the inventory item by item with where each went.

## The agent's memory

The agent's memory is per machine and fails the clone test, so nothing a continuation needs lives there alone.
It holds a fact about the process that no record owns — a trap paid for, a tool's behaviour, a preference of the person — and never what the repository records, and never a tree-derived figure.
An incident goes to the log, the rule it earned to the skill or the instructions that own it, the agent's own trap to its memory; a lesson that holds for every project moves from the memory into a skill.
