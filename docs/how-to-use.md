# How to use

You do not learn a tool first.
You talk to the agent as you already do, and the skills fold the kit into that conversation.
A research thread, from a remark at a talk to a result, looks like this:

- **"Set up research-kit in this project."**
  The agent probes the project, proposes what is missing and, on your word, writes the records and library directories, the paragraphs for its own instructions file and the pre-commit hooks.
- **"At yesterday's talk someone claimed A might imply B. Keep that."**
  An idea record appears with its source.
  Capturing costs nothing, and most ideas are removed as ideas, each with its reason.
- **"Let's look into it."**
  The agent draws the idea into its hand and works it: the questions and tasks it holds are minted from it, each question saying what would settle it, say a finite counterexample or a proof, and a task naming a unit of work such as designing the route or proving the lemma.
  A goal or a direction the idea holds is put to you, and the idea is closed once it is folded into what it produced.
  The cards it minted stand unranked until the next "What's next?".
- **"What's next?"** or `/research:whatsnext let's focus on the proofs`
  The agent reads what you left in the inbox and proposes a record for each item, refreshes the ranked list under your focus, the reason for each rank going in the log entry, and refills its hand from the top of it.
- **"Show me the dashboard."** or **"What's on the table?"**
  The table of hands, goals and directions, decks and piles opens as a read-only page on localhost, the records laid as cards.
- **"Work the hand."** or **"Continue."**
  The agent works the cards in its hand one by one.
  A work it reads gets a card with how far it was read; a task is made, and its result minted as a finding naming its evidence, a script that asserts it or a proved declaration; residue sharp enough to name becomes a task or a question of its own rather than prose; the log entry lands in the same commit as the transition.
  When the hand is worked it freezes and stops.
- **"Let's re-rank so the split work finishes first."**
  The order changes, a rank being a number and its reason going in the log entry, and the index regenerates.
  A state edited by hand that leaves the records inconsistent fails the check at commit.
- **"Do the two papers still agree?"**, `/research:audit`, `/research:scrutinize the main lemma` or `/research:attribution`
  The agent runs the checks first, then reads what no script sees: each import against the statement it comes from, one argument for its gaps, each claim about a named external result against its primary source.
  It reports before it edits, then corrects each sentence it found false of the work and asks you what is yours to decide.
- **"Let's freeze here."** or `/research:freeze`
  The agent saves what the conversation found and no record holds, sweeps what the session made stale, runs the checks and commits, and leaves one directive for the next session in the inbox.
- **Next week: "Where were we?"**
  The agent prints the session summary and continues with the cards in its hand.
  Nothing settled last week is asked again, and a question shown wrong or impossible is listed as settled.

With the `formal` plugin and a Lean 4 library, the proof step changes hands without you saying anything new.
For a Lean target, the agent holds the task in its hand while the prover works (a parallel draw is yours to rule), composes the handoff statement-first from your document's text with the declarations quoted, passes it through the check, commits the records and dispatches it to the prover subagent as the last act of its turn.
When the report comes back, the agent lands it: the manifest diff and a cold read-back of every landed statement are read from the built tree, the document's rows are written from the landed proof, the task is made, the finding minted from the landed proof with the declaration itself as its evidence, and the question it settles closes.
Say **"Give me a prompt for the prover"** and the handoff is printed for a session of your own instead; paste the report back and the landing runs the same way.

Underneath, each skill is also a slash command in Claude Code (`/research:whatsnext`, `/research:freeze`, `/research:flow`, `/research:library`, `/formal:land` and so on), and every step is one command line of a skill's script (`flow`, `library`, `dashboard`, `formal` and the setup's probe), which the agent runs for you.
[Getting started](research/getting-started.md) shows the first steps as those commands, with the files they write and what a failed check looks like; [Install](install.md) has the plugins, the skills for other agents and the hooks.
