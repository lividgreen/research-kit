# Scrutiny

`/research:scrutinize TARGET` reads one argument — a proof, a section, a statement — for where it is weak: the claims and their status, the gaps, the steps it leans on hardest.
It is checking, not verification: it certifies nothing, and a machine-checked proof is what validates an argument in the strong sense.
It is the [`scrutinize`](../../plugins/research/skills/scrutinize/SKILL.md) skill, which has no script behind it; with another agent, ask it to scrutinize the argument.
This page is what it does, what the project tells it, and its words.

## What it does

The target is read whole, with every section, lemma or assumption it invokes opened, and the report lists, in order:

1. every non-trivial claim with its asserted status (proved here, proved elsewhere, assumed, conditional, open), and the ones whose status looks wrong, such as a claim stated as proved that rests on an unproved step;
2. each inference gap, and whether it is a missing result or a missing method;
3. the one to three steps the rest depends on most and the most appealing claim, read hardest, each with what breaks if it fails;
4. any assumption buried rather than named, and any regime condition not written as the project writes it;
5. any claim about a class that uses a fact about one instance, or the reverse.

The report is a numbered list with the caveat that it is checking; the target is not edited, and an uncertain gap is marked as needing your judgment rather than guessed.
Then a sentence found false of the artifact is corrected in the same session at its own size, at every summary site that restates it; a gap is not a false sentence, and what to do about one is yours, asked with a recommendation or captured as a record on your word.
A document the project's part names as one a review reports and asks you about first gets the sentence, its evidence and the correction put to you instead.

## What the project tells it

[The research setup](research-init.md) forms with you the conventions an argument is held to and writes them into the instructions file under a `### Reviews` heading, inside its `## Records and method` section, since no script reads them: how a regime condition is written, which objects form an abstract class and which are its instances, the status labels the project uses, and which documents a review may correct in the session and which it reports and asks you about first.
Where it is missing, or does not say what the review needs, the review says so and advises the [setup](research-init.md), which forms it in a project set up before as well; where only this review's part is missing and a full setup is not needed, it asks you for that part in place and, on your word, writes it where the setup would.

## Words

- **missing result** — a step that may be true and is not shown.
- **missing method** — a step the present apparatus cannot express.
- **load-bearing step** — a step the rest of the argument depends on, read hardest because the argument needs it.
- **class claim, instance claim** — a statement about every member of a class, and one about a named member; [The working rules](working-rules.md) has the method's other words.
