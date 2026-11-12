---
name: whatsnext
description: What we do next, for the whole project — read the inbox and propose what to make of each item, rank the next list under the focus the person gives, draw the top work into the agent's hand under its limit and return what no longer fits, and write the log entry. Use as `/research:whatsnext`, optionally with a focus (`/research:whatsnext let's focus on the research tasks`), at a session's start, or when the ranked list is empty. Runs the `flow` skill's commands and decides nothing the person has not. When the person says 'what's next' or 'whatsnext', they mean this skill — call it every time, even if it ran earlier in the session, and take every step.
license: Apache-2.0
compatibility: The `flow` skill beside this one, whose script it runs; git for the commit.
metadata:
  version: "0.8.0"
  requires: flow
---

# What is next

The ranked records are the schedule a session works from the top of, and this is how they are filled or refreshed: at a session's start, when the person asks, or when the list is empty; never on a cadence, never as a per-landing triage.
The question is: what do we do next, for the whole project?
`flow …` below is the `flow` skill's `scripts/flow.py`, run by its path from the project root as that skill says.
A focus the person gives with the command, "let's focus on the research tasks", biases the ranking as a direction does and never orders it.

1. **Read the inbox.**
   `flow state` prints it first, then the ranked list, the hands and the log's top State paragraph.
   For each item the person left, propose what it becomes: an idea, a question or a task minted, a goal or a direction the person opens (`flow goal`, `flow direction`, minted on their word alone), an act done in the turn, or nothing, with the reason.
   Make the records the person agrees to, name each item in the log entry, and remove it from the inbox; an item the person has not answered stays.
   A directive a freeze left for this session is the first move, unless the person says otherwise.
2. **Inventory from the CURRENT records, through the CLI.**
   `flow find --type task --state ready`, `flow find --type question --state open`, `flow find --parked`, `flow find --blocked`, `flow find --held`; `flow show ID` for one record with its links and back-references; the open goals and directions, `flow find --type goal --state open` and `flow directions`, which the index lists under `Goals`, each with the questions serving it, and `Directions`.
   Never glob or read a record directory.
   Before ranking a record, open what it points at — the document section, the module, the artifact — since records age.
   A block is calculated, so one on a record that has settled holds no more and needs no hand; a block on words is unblocked by hand once the words no longer hold (`flow unblock ID --on "…" --note "…"`).
3. **Rank.**
   With no goal and no direction, the cards are worked as the person says; with directions, the moves lean toward them without being bound, since a new direction may come; with a goal, reaching it is the main direction and the moves go there as fast as they can, the questions serving it (`serves`) first among them.
   Never so biased toward a direction or a goal that the rest is not seen: then whole-project value, then a fresh landing's cheap follow-on; a task's due date never moves a rank, but the `Due` list is read first and a passed date is named.
   A finding resting on `stated` evidence alone (`flow find --form stated --only`) is work waiting, a proof to formalize, a probe to run, a work to cite, and a candidate task.
   Nothing is ranked down, parked or left off for lacking a route: a record with no known route is ranked, and finding the route is its first round's job.
   A parked or blocked record keeps its rank, and the list shows the wait; a question whose landing waits on the person's decision says so in the log entry and is ranked anyway.
   Where the project pairs documents with a machine-checked library, the `method` skill's rules under "With a prover" order ties among its formal targets.
4. **Write the ranks.**
   A rank is a number alone: `flow rank ID N` for one item, `flow rank ID 1 --insert` to take a rank another record holds, moving that record and the ones below it down by one, or `flow rank --set ID …` for the whole order at once, which clears every other rank, writes an order only, refreshing no question's checked date, and prints each record as `ranked ID N` or `unranked ID (was N)`.
   Why each item stands where it does, and its first move, or "none yet", go in the log entry for this ranking, one clause each, a pointer by ID and never a restatement.
   A goal or a direction a question serves is given with `flow serves Q +G`, on any open question, ranked or not.
   A list whose ranked records have not changed since its last refresh is left as it is, and the log entry says so with that refresh's date.
   Draft the entry in a scratch file and pass it through the project's text gates before writing it.
5. **Intake.**
   Park or unpark only for a reason the record carries with a date — `flow park ID --reason "…" --revival "…"`, `flow unpark ID` — never "no route"; a task waiting on the person's decision is parked with a reason naming the decision.
   Mint newly seen residues: `flow idea "…"` for an idea, `flow question "…" --ref IDEA` for a question from one (`flow consume IDEA` once the idea is fully processed), or `flow question "…" --ref FINDING` from the finding that exposed it — a question of its own, its body saying what counts as an answer, never a line added to the question it came from.
   Record the read of each question the session opened in step 2 or touched here with `flow checked ID …`, where no `flow rank ID N` refreshed it already; `--set` asserts no read.
   Goals and directions are the person's: propose in the log entry, and mint or close one (`flow goal`, `flow reach`, `flow giveup`, `flow direction`, `flow drop`) only on their word; a goal reached or given up, or a direction dropped, clears nothing on its questions, and the notice it prints names them: each is decided on here, re-ranked, given another goal or direction with `flow serves`, or left.
6. **Draw.**
   Draw the top work into the agent's hand under its limit, `flow draw ID --owner agent` (`agent` is the agent's name as `[hand]` names it by default, and a project that names its hands otherwise uses its own name here and below), a task or an idea; a parked or blocked one is refused, and is unparked or unblocked first only with a reason.
   Where the top of the ranked list is a question, nothing is drawn from it directly: the agent mints the task that is its first move, `flow task "…" --ref Q`, the log entry's first move saying what, and draws that; a question waiting on something the hand cannot do leaves the hand as it is.
   Return, with a note, what the agent's hand holds that the new order no longer puts first: `flow return ID --note "…"`; a task handed to a prover session stays, since its handoff's landing closes it.
   The person's hand is the person's: propose, never draw into it or return from it.
7. **Prune.**
   An item whose work landed was closed by its own transition, which cleared its rank; an item that stalled is parked with a dated reason.

**On a wall**, in the round an item commissions: change whatever reaches the goal — the statement, the definition, the object or the currency — under the `method` skill's "Changing the target honestly" invariants, the statement before and after written in the round's resolution, the question's body and the log entry; a result about the changed statement is never registered as settling the original.

**Output.** The inbox items with what each became, the refreshed ranks, the hands, `flow check` green, a log entry (`flow log add FILE`), the project's offline gates by exit code, a commit.
