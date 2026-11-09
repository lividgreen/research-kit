# The attribution check

`/research:attribution` holds every sentence that credits the project with proving, settling, bypassing, re-deriving or being first at a named external result to what that result's primary source states.
[`library check`](library.md) confirms that a cited work exists and is tied to its reference entry; this check confirms that what a sentence says of the work is what the work says.
It is the [`attribution`](../../plugins/research/skills/attribution/SKILL.md) skill, which runs the library's commands and has no script of its own; with another agent, ask it to check the attributions.
This page is what it does, what the project tells it, and its words.

## What it does

1. The worklist starts from `library claims`, the claim-shaped sentences of the bound documents that name a carded work with the extracts the card carries, and `library claims --uncovered`, those whose card carries none; since that list sees a work only by its first author's surname and year, the documents are also read for the shapes it misses: a verb of settling on a named result, a change of resource, an identification, a first, a re-derivation whose direction is checked; a document `library.toml` does not bind lists nothing there and is read by hand.
2. Each sentence is compared with an extract on the work's card where one covers it; where none does, the primary source is read (`library fetch`, `library page`, `library find --text`) and the extract written in the same pass, the card's grade raised where the reading went further, never lowered.
   A report or a summary that quotes the result is a lead, never the source, and a source that cannot be obtained makes the verdict UNVERIFIABLE, never faithful.
   The comparison is on four axes: the resource measured, the quantifiers, the scope, and the caveats the author states.
3. The report is a table of verdicts, faithful, OVERCLAIM (with the axis and what the source does state) or UNVERIFIABLE, each with a reframe that claims what was established and names the gap; the documents themselves are not edited while it is drawn up.
4. Every verdict is written on the work's card: faithful or OVERCLAIM as the extract it was compared with or that was written for it, UNVERIFIABLE as a dated note, since no place was read; a re-check replaces the extract and a dated note says what changed.
   `library claims --uncovered` lists only the works whose card carries no extract, so a sentence at a work with one is still compared with it.
5. Then each overclaim is corrected in the same session at its own size, at every summary site that restates it, and the check runs again over the corrected sentences, with `library check`; the [audit](audit.md) runs too where the reframe changed a statement other documents cite.
   A document the project's part names as one a review reports and asks you about first gets the sentence, its evidence and the reframe put to you instead.

Where the works are many, they may be checked in parallel, each by one fresh subagent reading its own primary source, whose verdict returns with the place and the quotation; the session sees them in the kept copy before the extract is written, since a subagent's report is never a read.
A claim that a result is absent from an upstream library, or present in it, is checked at the upstream's committed state (`git show HEAD:<path>`, or the tag the document cites) or at the live upstream, never at a working tree, which may carry the project's own uncommitted patch and read the claim's negation.

## What the project tells it

The shapes `library claims` matches are `[claims] shapes` in `library.toml`, where a project with a prover adds its own words, such as `first formalization` or `machine-checked`.
[The research setup](research-init.md) forms with you the documents a reader sees that `library.toml` does not bind, a blog or a front page, and which documents a review may correct in the session and which it reports and asks you about first, and writes them into the instructions file under a `### Reviews` heading, inside its `## Records and method` section.
Where it is missing, or does not say what the review needs, the review says so and advises the [setup](research-init.md), which forms it in a project set up before as well; where only this review's part is missing and a full setup is not needed, it asks you for that part in place and, on your word, writes it where the setup would.
A run takes the documents you give with the command, and otherwise the bound ones with those, and says which it took.

## Words

- **primary source** — the work that states the result, in the edition cited, as against a report, a summary or a citing work that restates it.
- **overclaim** — a sentence that credits the project with more of a named result than its primary source states, on one of the four axes.
- **resource, currency** — the quantity a result is measured in, a time, a space, a size or a count.
- **reframe** — the sentence an overclaim becomes: the premise, the special case or the one direction established, with the gap named.
- **extract** — what a work states at a named place, with its author's caveat and the rule on what may be claimed; [Library cards](library-cards.md) has its form.
