# Why research-kit

research-kit came out of one research project, a series of papers with a Lean 4 library written over months with one coding agent, and every piece of it replaced something that had failed there.

- **The agent started every session cold.**
  It asked again about matters settled weeks before, and a roadmap written by hand was where answers went to drift.
  One parked item collected forty-two dated re-test lines before a ranked list replaced the triage, with a reason for each rank and a kill criterion fixed before the work.
- **Hand-edited state was the single largest source of drift.**
  A pool of ideas, a brainstorming file and a table of results each lagged behind what the project had actually done, and one entry cited a declaration the library did not have.
  Now a record changes state through the tool, which writes everything the new state needs, a finding must name evidence that a machine can resolve, and the check fails on a record that does not hold together.
- **Reading the records cost more than the research.**
  In eight of ten measured sessions the records were the largest thing the agent read.
  Now a session starts from a short generated summary and reads records by id, never the directory whole.
- **A citation stood on a paraphrase.**
  A subagent's retrieval report is testimony, not a read, and two "recent results" turned out to be withdrawn preprints.
  Now a card grades how far a work was read, a read a subagent made alone counts as unread, and a reference entry with no card fails the check.
- **A prover's report is a claim about the tree, not the tree.**
  One handback said nothing about two commissioned declarations that had not landed.
  Now the landing reads the built library first, and a document row is written from the landed proof, never from the plan that commissioned it.

Each of these became a check rather than a lesson.
The checks run offline as pre-commit hooks, each ends with a line saying what it did not look at, and the whole record is plain Markdown in git that you can read, grep and diff without the kit.
