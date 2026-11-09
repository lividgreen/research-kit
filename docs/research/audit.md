# The audit

`/research:audit` checks that the project's documents agree with one another: a statement one document imports is the one the exporting document proves, with the same strength, conditions and scope.
It is the [`audit`](../../plugins/research/skills/audit/SKILL.md) skill, which has no script of its own and runs the project's checks; with another agent, ask it to audit the documents for consistency.
This page is what it does, what the project tells it, and its words.

## What it does

1. The mechanical checks run first, by their exit codes: the hooks of `.pre-commit-config.yaml` by default, as `prek run --all-files` or `pre-commit run --all-files`, and the gates the project's part names, `library check` and `formal cite` among them where they are bound, so the reading spends its effort on what no script sees.
2. Every exporting statement is opened and its hypotheses read before the sentence citing it is judged, and five things are checked across the documents: every import for its strength, its conditions and its scope; a regime condition stated with the same constants wherever it is load-bearing; a status labelled alike wherever the claim appears; definitional drift; and every negative-coverage sentence, held to the artifact at its committed state, each with the row, the statement or the declaration that would falsify it.
3. The report is a table of the discrepancies: the files and lines, which statement is correct, the severity; the audit itself edits nothing, and where the artifact settles a discrepancy the correct statement is the artifact's, never a choice put to you.
4. Then each sentence found false of the artifact is corrected in the same session at its own size, at every summary site that restates it; what is yours to decide is asked with a recommendation, and a discrepancy not corrected now is captured as a record on your word, so the report does not live in the conversation alone.
   A document the project's part names as one a review reports and asks you about first gets the sentence, its evidence and the correction put to you instead.

## What the project tells it

[The research setup](research-init.md) forms with you what the reviews hold the documents to, and writes it into the instructions file (`CLAUDE.md`, `AGENTS.md` or the agent's own) under a `### Reviews` heading, inside its `## Records and method` section, since no script reads it; the audit reads it there, each item a check of its own:

- the documents that form the corpus, the draft and deferred ones among them, which no gate reads and so go stale first;
- which document imports which;
- the regime conditions, each with its explicit constants;
- the claims whose status is written in more than one document;
- the objects whose definitions are compared, and any two that share a name on purpose;
- any rule of the project's own a document is held to, such as a result each document must own;
- which documents a review may correct in the session, and which it reports and asks you about first (an ADR, a contract, a history held as written at its date);
- the gates the audit runs first, by name, where they are more than the hooks.

Where it is missing, or does not say what the review needs, the review says so and advises the [setup](research-init.md), which forms it in a project set up before as well; where only this review's part is missing and a full setup is not needed, it asks you for that part in place and, on your word, writes it where the setup would.
A run takes the scope you give with the command, and otherwise the corpus, and says which it took.

## Words

- **import, exporting statement** — a result one document uses that another proves; the statement as the proving document gives it.
- **negative-coverage sentence** — a sentence saying what the documents do not have ("nothing here does X"), a claim about every document and every row of the artifact at once.
- **definitional drift** — one named object defined, or used, differently in two places.
- **summary sites** — the places a result is restated in short, which a correction must reach as well as the detailed site; [The working rules](working-rules.md) has the method's other words.
