# The freeze

`/research:freeze` ends a session so that a cold one, on another machine, can continue it without asking: what the conversation found and no record holds is saved, the records are checked, and the work is committed.
It is the [`freeze`](../../plugins/research/skills/freeze/SKILL.md) skill, which runs the [flow](flow.md)'s commands and has no script of its own; with another agent, ask it to freeze the session.
A freeze is a request of its own: when you say "freeze", "save the session" or "park the session" you mean the skill, called every time, even if it ran earlier in the session, with every step taken, so "… and freeze" at the end of another request is two requests, the work and then the skill.
This page is what it does, the check under it, and its words.

## What it does

Its one rule is to save what is important for the work; its test is the clone: could a session reading only the inbox, the ranked list and the log's top State paragraph go on without asking?

1. The records say what the session knows: the log's top State paragraph is current, and its next action names the next session's first move.
   The State paragraph says where the work stands and the next move, and never the gates' result or the push, which are facts about the commit and go in the turn's report, step 6.
2. What only the conversation holds is flushed, turn by turn, your messages and the replies both: an idea in your words, a ruling where the rules live, a reading into the record it is about, a correction as a dated line, an open question as a question or an idea; then everything the session created is closed or left with a note, and each card the session's hand holds is named in the log entry with what the session did on it, one left untouched being returned or passed with a note.
   A freeze ranks nothing; a directive for the next session goes to the inbox, one directive, never a summary.
3. The surfaces a reader sees are swept for what the session made stale, by meaning, not only in the files it touched; a stale claim the session may not correct, in a document only you change, goes to an idea or a task with the place and the proposed edit, and is named in the log entry.
4. `flow state --check`, `flow check` and the project's gates run, read by their exit codes.
5. A commit with named paths, and the push as the backup; steps 2 to 5 run on a clean tree too.
   Where the tree holds unstaged changes outside those paths, another session's in a shared tree, the commit is made from a `git worktree` of its own and taken in with `git merge --ff-only` ([Install](../install.md#several-sessions-in-one-tree)), since the hook runner stashes them while the hooks run, or the turn says it is about to.
6. The report answers the checklist `flow state --check` prints: the inventory item by item with where each went, the sweep, the agent's memory checked, the gates by exit code; then the tree and the inbox directive or "none".

## The check under it

`flow state --check` decides what a machine can see of a freeze and fails on two things: the log's top entry not dated today while the tree changed since the newest committed entry, and a record changed since then that no entry names.
A record whose only change is its rank, which one renumbering gives every record below the one inserted, is not asked to be named, and an entry may name a range of ids written `finding-0015…0035` where it would otherwise write each out.
`flow touched --unnamed` lists those records before the entry is written, so it names them without the ids gathered by hand.
It prints each held card, a task handed to a prover session among them, with its drawn date and its age in days, for the State paragraph, and fails on none, since each hand continues its own work.
An inbox holding items is no failure: the next session reads it.
It prints the steps that are the session's own as a checklist the report answers, since a freeze run from memory still calls this command and so still meets the current steps.
It exits 1 on a failure and 2 where git or a committed log is missing and a part could not be decided, so a freeze it could not see whole is never read as clean.

## Words

- **freeze** — a session's end, as far as the work is concerned: everything a continuation needs is in the repository.
- **clone test** — whether a clone of the repository on another computer could continue; the agent's memory, the scratchpad and a running subagent fail it.
- **inventory** — the conversation read turn by turn for what was said or found and recorded nowhere.
