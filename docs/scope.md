# Scope

What the kit assumes of a project, what its agent does without asking, and what it is not.

## What it assumes

- One person and one working agent.
  `flow.toml` names more owners, each with a hand limit, but two people cannot review or merge each other's work through it.
- One agent works a project's records at a time.
  Each file is written whole, and `flow` and `library` each take one write at a time on a local disk, so two sessions' writes queue rather than collide; beyond that, two sessions are not coordinated.
- Records are prose at one sentence per line, which the check enforces because diffs and the index depend on it.
- A document whose reference entries the library checks writes them one per line under a `## References` heading, authors and year first.
  A project with a BibTeX or numbered bibliography binds no documents and cites by key instead.
- The agent reads records by id through the tool, never the directory whole.
  The skills say so, and the check is what holds when the agent forgets.
- A kept copy of a work goes into a tracked directory only where the project may redistribute it, and `library keep` writes there only when told so (`--redistributable`).
  What can be fetched again lives in an ignored store.

## What the agent does without asking, and what it may not do

Without asking, the agent continues from the top of the ranked list when a session opens, and corrects a sentence it finds false of the project's artifact at the sentence's own size.
Both are the `method` and `flow` skills' defaults; a project that wants to be asked first says so in one sentence of its instructions file, and the skills yield.

What it may not do, and what fails when it does:

- write a record's state by hand (`flow check`, wherever the edit leaves the record without the fields, place or index line its transition writes);
- cite a work the library does not hold (`flow check`, where the library is bound);
- let a document's reference entry cite a work graded unread without naming the work it is known through (`library check`);
- read the records directory whole instead of a record by id;
- write a result's row from the design that commissioned it rather than from what landed;
- publish or send anything without the owner's word for that item, or schedule a publication.

The owner decides what a result means and where it is registered; the agent decides nothing about scope or significance.

## Compared with

- **An issue tracker** (a GitHub Project, Beads, a todo file) holds tasks.
  It does not validate that a result's evidence exists, that a question still has a reason to be open, or that the index the next session reads is current.
- **A reference manager** (Zotero, a BibTeX file) holds works.
  A card also holds how far the work was read and what may be claimed of it at which page, and the document's reference entries are tied to it at every commit.
- **A notes vault** (Obsidian, a wiki) holds prose anyone edits.
  Here a record's state and provenance are written by the tool, and the check fails on a hand edit that leaves them inconsistent.
- **A long `AGENTS.md` or `CLAUDE.md`** holds rules and rots.
  Here the state lives in records a check reads, and the instructions file carries one paragraph the tool prints at `init`.
- **A Lean blueprint** maps the statements to prove.
  The `formal` plugin is the other side, the prompt a prover session gets and the check of what it reports back, for a project that already has its library.
