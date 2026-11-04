# What is next

`/research:whatsnext` starts a session: it reads what you left in the inbox, refreshes the ranked list under the focus you give, and draws the top work into the agent's hand.
It is the [`whatsnext`](../../plugins/research/skills/whatsnext/SKILL.md) skill, which runs the [flow](flow.md)'s commands and has no script of its own; with another agent, ask it what is next.
This page is what it does, what it reads and writes, and its words.

## What it does

You run it at a session's start, when you ask what is on the table, or when the ranked list is empty; never on a cadence.
A focus may follow the command, `/research:whatsnext let's focus on the proofs`, and biases the ranking as a direction does without ordering it.

1. The inbox: for each item you left, the agent proposes what it becomes, an idea, a question, a task, a direction for you to write, an act done in the turn or nothing, makes the records you agree to, and removes the item; a directive the last freeze left is the first move.
2. The inventory: the ready tasks, the open questions, the parked, blocked and held records, read through `flow find` and `flow show`, never by opening the record directories.
3. The ranking: toward a goal where one is set, toward the directions where there are some, never so far that the rest is not seen; nothing is ranked down for lacking a route, and a parked or blocked record keeps its rank with its wait shown.
4. The ranks written with `flow rank`, each with why now and its first move, or the whole order at once with `flow rank --set`.
5. The intake: residues captured or framed, parks with a dated reason, and a task waiting on your decision parked with a reason naming it.
6. The draw: the top work drawn into the agent's hand under its limit, and what the new order no longer puts first returned with a note; your hand is yours, and the agent only proposes for it.

It ends with what each inbox item became, the refreshed ranks and the hands, `flow check` green, a log entry and a commit.

## What it reads and writes

- `INBOX.md` at the project root, or the file `flow.toml`'s `[paths] inbox` names: it reads it, and removes each item it acted on.
- The records, through the flow's transitions only: `capture`, `frame`, `rank`, `park`, `unpark`, `block`, `unblock`, `draw`, `return`, `checked`.
- The log, one entry through `flow log add`; the directions file is read and never written.

## Words

- **inbox** — the file where you leave items between sessions and a freeze leaves one directive for the next; no rule empties it at a freeze.
- **focus** — what you ask the session to lean toward, a bias like a direction and never an order.
- **hand** — what an owner holds: the agent's, across its sessions, and yours.
