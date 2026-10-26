# Filling or refreshing the next list

The ranked records — the index's `## Next (ranked)`, the records' `rank` fields — are the schedule a session works from the top of.
Run this when the owner asks or when the list is empty; never on a cadence, never as a per-landing triage.
The question is: what do we do next, for the whole project?

1. **Inventory from the CURRENT records, through the CLI.**
   `flow state` (the inbox, the ranked list, the log's top State); `flow find --type task --state ready`, `flow find --type question --state open` and `flow find --parked`; `flow show ID` for one record with its links and back-references; the directions file.
   Never glob or read a record directory.
   Before ranking a record, open what it points at — the document section, the module, the artifact — since records age.
2. **Rank.**
   Items toward a direction first; then whole-project value; then a fresh landing's cheap follow-on.
   Nothing is ranked down, parked or left off for lacking a route: a record with no known route is ranked with a first move of "none yet", and finding the route is its first round's job.
   The one gate: a task of a decision kind or held by a decision owner is never ranked; a question whose LANDING waits on such a decision says so in its first move and is ranked anyway.
   Where the project pairs documents with a machine-checked library, the `method` skill's rules under "With a prover" order ties among its formal targets.
3. **Write the ranks.**
   For each item `flow rank ID N --why "…" --first-move "…" [--direction "…"]` — a pointer by ID, never a restatement; why now, one clause; the first move, or "none yet".
   A rank another record holds is refused; `--insert` takes it, moving that record and the ones below it down by one, and puts a new item at the top in one step: `flow rank ID 1 --insert --why "…" --first-move "…"`.
   Then `flow rank --set ID …` fixes the whole order at once: it clears every other rank and refreshes the ranked questions' checked dates; every record it names already carries its why-now and first move.
   Draft long why-now or first-move text in a scratch file and pass it through the project's text gates before writing it.
4. **Intake.**
   Park or unpark only for a reason the record carries with a date — `flow park ID --reason "…" --revival "…"`, `flow unpark ID` — never "no route".
   Mint newly seen residues: `flow capture` for an idea, `flow frame IDEA… --summary "…" --kill "…"` for a question, or `flow frame FINDING …` from the finding that exposed it — a question of its own, never a line added to the question it came from.
   Refresh each touched question's checked date with `flow checked ID …`.
   Directions are the owner's: propose in the log entry, change nothing in the directions file.
5. **Prune.**
   An item whose work landed was closed by its own transition, which cleared its rank; an item that stalled is parked with a dated reason.

**On a wall**, in the round an item commissions: change whatever reaches the goal — the statement, the definition, the object or the currency — under the `method` skill's "Changing the target honestly" invariants, the statement before and after written in the round's resolution, the question's body and the log entry; a result about the changed statement is never registered as settling the original.

**Output.** The refreshed ranks with `flow check` green, a log entry, the project's offline gates by exit code, a commit.
The refresh commissions nothing: the top item's design round — a design task minted with `flow refine Q --task "…" design` or `flow task "…" --kind design` and drawn with `flow draw T --owner …` — is the next action.
