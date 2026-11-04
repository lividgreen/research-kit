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
  The agent frames the idea as a question and fixes what would settle it before any work starts, say a finite counterexample or a proof, then proposes the split into tasks: design the route, prove the lemma.
  You see the split before it is written, because anything ready may be drawn without asking again.
- **"What's next?"**, **"What's on the table?"** or `/research:whatsnext let's focus on the proofs`
  The agent reads what you left in the inbox and proposes a record for each item, refreshes the ranked list under your focus with a reason for each rank, draws the top task into its hand and runs a design pass before building anything.
- **"Continue."** or **"Go on with task-0007 in autonomous mode."**
  The agent works down the list.
  A work it reads gets a card with how far it was read; a task is made, and its result minted as a finding naming its evidence, a script that asserts it or a proved declaration; residue sharp enough to name becomes a task or a question of its own rather than prose; the log entry lands in the same commit as the transition.
- **"Let's re-rank so the split work finishes first."**
  The order changes with its reasons, and the index regenerates.
  A rank without a reason fails the check at commit, and so does a state edited by hand that leaves the records inconsistent.
- **"Let's freeze here."** or `/research:freeze`
  The agent saves what the conversation found and no record holds, sweeps what the session made stale, runs the checks and commits, and leaves one directive for the next session in the inbox.
- **Next week: "Where were we?"**
  The agent prints the session summary and continues from the top of the list.
  Nothing settled last week is asked again, and a question shown wrong or impossible is listed as settled.

With the `formal` plugin and a Lean 4 library, the proof step changes hands without you saying anything new.
When the task drawn is a Lean target, the agent mints it, keeps it in its own hand while the prover works on it, composes the handoff statement-first from your document's text with the declarations quoted, passes it through the check, commits the records and dispatches it to the prover subagent as the last act of its turn.
When the report comes back, the agent lands it: the manifest diff and a cold read-back of every landed statement are read from the built tree, the document's rows are written from the landed proof, the task is made, the finding minted from the landed proof with the declaration itself as its evidence, and the question it settles closes.
Say **"Give me a prompt for the prover"** and the handoff is printed for a session of your own instead; paste the report back and the landing runs the same way.

Underneath, each skill is also a slash command in Claude Code (`/research:whatsnext`, `/research:freeze`, `/research:flow`, `/research:library`, `/formal:land` and so on), and every step is one command line of a skill's script (`flow`, `library`, `dashboard`, `formal` and the setup's probe), which the agent runs for you.
[Getting started](research/getting-started.md) shows the first steps as those commands, with the files they write and what a failed check looks like; [Install](install.md) has the plugins, the skills for other agents and the hooks.
