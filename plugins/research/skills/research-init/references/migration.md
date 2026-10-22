# Bringing an existing project in

A project that already keeps its research somewhere — notes, a roadmap, a to-do list, an issue list, a results table, a log, a bibliography — is set up as any other, then its material is brought into the records and the cards.
The `flow` and `library` skills define what the records and the cards are; this file says only how material that was not written for them is carried across, whatever shape it is in.

## Principles

1. **Survey before writing.**
   Read what the project keeps and where, and propose the mapping in one message: each source, what it becomes, what stays where it is.
   Nothing is written before the person's word, as with the rest of the setup.
2. **Classify by the kinds' own tests, not by the old file's labels.**
   A thing to do is a task, a thing to know is a question, a raw signal is an idea, a claim whose evidence a machine resolves is a finding.
   A claim with no such evidence is never a finding: it stays prose where it stands, or becomes the task that would earn it evidence.
   An item that fits no kind is left where it is and named in the report.
3. **Carry the live front, not the history.**
   What is open now becomes records; what is settled stays in the old files and in git, and a record points at it rather than copying it.
   A finding is minted only where its evidence resolves today.
4. **Through the tools wherever a command exists.**
   Records are made with `flow` and cards with `library`, so they are valid by construction.
   A record written by hand is only one the commands cannot express, with `origin: legacy`; an older list of works is loaded as seeded cards (`--seed`), ungraded, since no reading is claimed that nobody made.
5. **Point, never restate.**
   A record or a card names where its subject is stated — the document's section, the module, the old note — so the migration copies no statement.
6. **Remove nothing.**
   The old files stay until the person retires them, after the checks pass; the migration adds and never deletes.
7. **End with the checks.**
   `flow check` and `library check` pass, or the report names each problem that stands, beside the mapping that was applied and what was left out and why.
