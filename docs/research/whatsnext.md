# What is next

`/research:whatsnext` starts a session: it reviews the cards the agent's hand holds, reads what you left in the inbox, refreshes the ranked list under the focus you give, and refills the agent's hand by rank to its limit.
It is the [`whatsnext`](../../plugins/research/skills/whatsnext/SKILL.md) skill, which runs the [flow](flow.md)'s commands and has no script of its own; with another agent, ask it what is next.
When you say "what's next" or "whatsnext" you mean the skill: it is called every time, even if it ran earlier in the session, and every step is taken. ("What's on the table" asks for a report of what is current and pending, not a re-rank.)
This page is what it does, what it reads and writes, and its words.

## What it does

You run it at a session's start, when you ask what is on the table, or when the ranked list is empty; never on a cadence.
A focus may follow the command, `/research:whatsnext let's focus on the proofs`, and biases the ranking as a direction does without ordering it.

1. The review: each card the agent's hand holds is kept, returned with a note (`flow return ID --note "…"`) or passed to another deck with one (`flow pass ID --to OWNER --note "…"`), the log entry naming each; a task handed to a prover session stays held, since its handoff's landing closes it, and a card that stalled is returned or passed here.
2. The inbox: for each item you left, the agent proposes what it becomes, an idea, a question, a task, a goal or a direction you open, an act done in the turn or nothing, makes the records you agree to, and removes the item; a directive the last freeze left is the first move.
3. The inventory: the ready cards, the open questions and ideas, the parked, blocked and held cards, each deck, the open goals with the questions serving each and the open directions, read through `flow find`, `flow show` and `flow directions`, never by opening the record directories; `flow find --state ready` and `--state active` are refused, a task's state being `open`.
4. The ranking: ideas, questions and tasks in one list across the decks, toward a goal where one is set, toward the directions where there are some, never so far that the rest is not seen; nothing is ranked down for lacking a route, a parked or blocked card keeps its rank with its wait shown, and a due date never moves a rank.
5. The ranks written with `flow rank`, a number alone, or the whole order at once with `flow rank --set`, which only orders and refreshes no question's checked date; why each item stands where it does and its first move go in the log entry, and the questions the agent opened are recorded as read by `flow checked`.
   A list whose ranked records have not changed since its last refresh is left as it is, the log entry saying so with that refresh's date.
6. The intake: residues minted as ideas or questions, each into a deck and never into the hand, parks with a dated reason for a card set down by decision, a card waiting on your decision passed to your deck with the decision named, and the questions a goal or a direction you closed named in its notice decided on one by one.
7. The refill: `flow draw --refill --owner agent` draws by rank from the top every ready card of the common deck and the agent's own, of the three kinds, until the hand's limit, and prints each card drawn, each ranked card it passed over with why, and the hand as `3 of 4` with the room left; a card is worked as it stands, a question or an idea included, and a hand left under its limit is explained in the log entry from those lines.
8. Your side: your deck named in rank order, what your hand holds, and the cards the agent proposes for your hand in one multi-select question, asked with the agent's question tool where it has one and in the turn otherwise; a card is drawn into your hand only on your answer.

It ends with what each inbox item became, what each held card became, the refreshed ranks and both hands after the refill, `flow check` green, a log entry and a commit.

## What it reads and writes

- `INBOX.md` at the project root, or the file `flow.toml`'s `[paths] inbox` names: it reads it, and removes each item it acted on.
- The records, through the flow's transitions only: `idea`, `question`, `task`, `rank`, `serves`, `park`, `unpark`, `block`, `unblock`, `draw`, `return`, `pass`, `checked`; `goal`, `reach`, `giveup`, `direction` and `drop` on your word alone.
- The log, one entry through `flow log add`; the goals and the directions are read, and minted or closed only when you say so.

## Words

- **inbox** — the file where you leave items between sessions and a freeze leaves one directive for the next; no rule empties it at a freeze.
- **focus** — what you ask the session to lean toward, a bias like a direction and never an order.
- **goal, direction** — the records you form and set: a goal is a destination, its body saying what reached means, the stronger pull where one is set; a direction is the way the research moves, a lean on the next moves; the session proposes them and mints none unasked.
- **hand** — what an owner is working on now, within a limit: the agent's, across its sessions, and yours; a card waits in its owner's deck until a draw puts it in the hand.
- **refill** — `flow draw --refill`: the hand filled by rank from the top of the list, every ready card of the common deck and the owner's own, until its limit.
