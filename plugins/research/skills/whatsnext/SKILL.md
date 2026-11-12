---
name: whatsnext
description: What we do next, for the whole project — review the cards the agent's hand holds, read the inbox and propose what to make of each item, rank the next list under the focus the person gives, refill the agent's hand by rank to its limit, propose additions to the person's hand, and write the log entry. Use as `/research:whatsnext`, optionally with a focus (`/research:whatsnext let's focus on the research tasks`), at a session's start, or when the ranked list is empty. Runs the `flow` skill's commands and decides nothing the person has not. When the person says 'what's next' or 'whatsnext', they mean this skill — call it every time, even if it ran earlier in the session, and take every step.
license: Apache-2.0
compatibility: The `flow` skill beside this one, whose script it runs; git for the commit.
metadata:
  version: "0.8.0"
  requires: flow
---

# What is next

The ranked records are the schedule the agent's hand is filled from, and this is how they are filled or refreshed: at a session's start, when the person asks, or when the list is empty; never on a cadence, never as a per-landing triage.
The question is: what do we do next, for the whole project?
`flow …` below is the `flow` skill's `scripts/flow.py`, run by its path from the project root as that skill says.
A focus the person gives with the command, "let's focus on the research tasks", biases the ranking as a direction does and never orders it.

1. **Review the agent's hand.**
   `flow state` prints each hand's held cards with their drawn dates and ages.
   For each card the agent's hand holds, decide with a note: keep it, where its work goes on and the focus does not put it behind; return it, `flow return ID --note "…"`, where nothing is under way on it; pass it, `flow pass ID --to OWNER --note "…"`, where its remaining steps belong to another deck, the person's among them.
   The note says what was done on the card and why it goes, and the log entry names each card kept, returned or passed, one clause each.
   A task handed to a prover session stays held, since its handoff's landing closes it.
   A card whose work landed was closed by its own transition, which cleared its rank and took it out of the hand; one that stalled is returned or passed here, and parked only where it is set down by decision.
2. **Read the inbox.**
   `flow state` prints it first, then the ranked list, the hands, the decks and the log's top State paragraph.
   For each item the person left, propose what it becomes: an idea, a question or a task minted, a goal or a direction the person opens (`flow goal`, `flow direction`, minted on their word alone), an act done in the turn, or nothing, with the reason.
   Make the records the person agrees to, name each item in the log entry, and remove it from the inbox; an item the person has not answered stays.
   A directive a freeze left for this session is the first move, unless the person says otherwise.
3. **Inventory from the CURRENT records, through the CLI.**
   `flow find --ready` for the cards a refill may draw, of the three kinds, `flow find --type question --state open`, `flow find --type idea --state open`, `flow find --parked`, `flow find --blocked`, `flow find --held`, `flow find --deck NAME` for what an owner's deck holds beside the hand; `flow show ID` for one record with its links and back-references; the open goals and directions, `flow find --type goal --state open` and `flow directions`, which the index lists under `Goals`, each with the questions serving it, and `Directions`.
   A task's state is `open` and its standing is calculated, so `flow find --state ready` and `--state active` are refused.
   Never glob or read a record directory.
   Before ranking a record, open what it points at — the document section, the module, the artifact — since records age.
   A block is calculated, so one on a record that has settled holds no more and needs no hand; a block on words is unblocked by hand once the words no longer hold (`flow unblock ID --on "…" --note "…"`).
4. **Rank.**
   The cards of the three kinds, an idea beside a question and a task, stand in one list for the whole project, across the decks, the person's cards among them.
   With no goal and no direction, the cards are worked as the person says; with directions, the moves lean toward them without being bound, since a new direction may come; with a goal, reaching it is the main direction and the moves go there as fast as they can, the questions serving it (`serves`) first among them.
   Never so biased toward a direction or a goal that the rest is not seen: then whole-project value, then a fresh landing's cheap follow-on; a task's due date never moves a rank, but the `Due` list is read first and a passed date is named.
   A finding resting on `stated` evidence alone (`flow find --form stated --only`) is work waiting, a proof to formalize, a probe to run, a work to cite, and a candidate task.
   Nothing is ranked down, parked or left off for lacking a route: a card with no known route is ranked, and finding the route is its first round's job.
   A parked or blocked card keeps its rank, and the list shows the wait; a card whose remaining steps wait on the person's decision is passed to the person's deck and keeps its rank, and the refill of the agent's hand passes over it.
   Where the project pairs documents with a machine-checked library, the `method` skill's rules under "With a prover" order ties among its formal targets.
5. **Write the ranks.**
   A rank is a number alone: `flow rank ID N` for one item, `flow rank ID 1 --insert` to take a rank another record holds, moving that record and the ones below it down by one, or `flow rank --set ID …` for the whole order at once, which clears every other rank, writes an order only, refreshing no question's checked date, and prints each record as `ranked ID N` or `unranked ID (was N)`.
   Why each item stands where it does, and its first move, or "none yet", go in the log entry for this ranking, one clause each, a pointer by ID and never a restatement.
   A goal or a direction a question serves is given with `flow serves Q +G`, on any open question, ranked or not.
   A list whose ranked records have not changed since its last refresh is left as it is, and the log entry says so with that refresh's date.
   Draft the entry in a scratch file and pass it through the project's text gates before writing it.
6. **Intake.**
   Park or unpark only for a card set down by decision, with a reason the record carries with a date — `flow park ID --reason "…" --revival "…"`, `flow unpark ID` — never "no route"; a card waiting on the person's decision is passed, `flow pass ID --to owner --note "…"` with the decision named, and never parked for it.
   Mint newly seen residues, each into a deck and never into the hand: `flow idea "…"` for an idea, `flow question "…" --ref IDEA` for a question from one (`flow consume IDEA` once the idea is fully processed), or `flow question "…" --ref FINDING` from the finding that exposed it — a question of its own, its body saying what counts as an answer, never a line added to the question it came from — and the ones that are plainly the person's or the agent's `--for` that owner.
   Record the read of each question the session opened in step 3 or touched here with `flow checked ID …`, where no `flow rank ID N` refreshed it already; `--set` asserts no read.
   Goals and directions are the person's: propose in the log entry, and mint or close one (`flow goal`, `flow reach`, `flow giveup`, `flow direction`, `flow drop`) only on their word; a goal reached or given up, or a direction dropped, clears nothing on its questions, and the notice it prints names them: each is decided on here, re-ranked, given another goal or direction with `flow serves`, or left.
7. **Refill the agent's hand.**
   `flow draw --refill --owner agent` (`agent` is the agent's name as `[hand]` names it by default, and a project that names its hands otherwise uses its own name here and below) draws by rank from the top every ready card of the common deck and the agent's own, ideas, questions and tasks alike, until the hand's limit.
   It prints each card drawn, each ranked card it passed over with why, and the hand as `3 of 4` with the room left; an unranked card is never drawn by it, and a card parked or blocked is unparked or unblocked first only with a reason.
   A card drawn is worked as it stands, a question or an idea included: no task is minted to hold its place.
   A hand left under its limit is explained in the log entry for the ranking, from the lines the command printed: which cards it passed over and why, and the ready cards that stand unranked.
8. **The person's side.**
   Name the person's deck in rank order and what the person's hand holds, both printed by `flow state`.
   Propose which cards of the deck go into the person's hand in one multi-select question, asked with the agent's question tool where it has one and in the turn otherwise.
   A draw into the person's hand, `flow draw ID --owner owner`, is made only on that answer.

**On a wall**, in the round an item commissions: change whatever reaches the goal — the statement, the definition, the object or the currency — under the `method` skill's "Changing the target honestly" invariants, the statement before and after written in the round's record, the question's body and the log entry; a result about the changed statement is never registered as settling the original.

**Output.** The inbox items with what each became, what each held card became, the refreshed ranks, both hands after the refill, the agent's as `3 of 4` and the person's, `flow check` green, a log entry (`flow log add FILE`), the project's offline gates by exit code, a commit.
