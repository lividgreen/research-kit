# The library

The library is the registry of everything a project refers to: one card per work — a paper, a book, a preprint, a dataset, a piece of software, a report of the project's own — recording how far it was actually read, what may be claimed from it and at which page, and what the project noted about it.
It is a component of its own, with its own directory, tool, check and lifecycle: a card names no record of any other system, and whoever cites a work writes the cite prefix and the card's key (`lib:jen1990`) and asks the library whether the key exists and how the work was read.
The tool is `scripts/library.py` of the [`library`](../../plugins/research/skills/library/SKILL.md) skill (`/research:library` in Claude Code), one Python 3.11 file with no dependencies: the CLI, the check, the index generator and the selftest; this page is the tool — its commands, the files it keeps, its bindings, its check and its words — and [Library cards](library-cards.md) is the specification of a card.

## What it does

A work is registered when it is first read or first cited, and its card records the reading: a grade that is a claim about the reader, never about the work, so a resolver's answer, a search engine's snippet or a subagent's report moves no grade.
The reference list of each document the project binds is tied to the cards, so citing a work that has no card, or one graded unread without naming the work it is known through, fails the check; `library citecheck` ties the document's text to its own reference entries, closing the chain from a sentence to a card.
An extract records what a work states at a named place, with the rule on what may be claimed of it, and is held to the kept copy's text where one is kept.
Online lookups — arXiv, Crossref, OpenAlex and others — fill in a card's fields, find open copies and watch for new citing works; they run on demand and never from the check.

## The commands

| Offline | Command |
| --- | --- |
| a new card | `library register "Title" --kind article --author "…" --year 1990 --doi …` |
| how far it was read | `library read KEY --grade parts --what "sections 1 to 3"` |
| a dated note, an addressed extract | `library note KEY --note "…"`, `library extract KEY ID --at "Theorem 4" --quote "…"` |
| a field corrected by hand, a link, a work set aside | `library type KEY --title "…"`, `library relate KEY KEY`, `library exclude KEY --reason "…"` |
| a copy obtained by hand, its pages, its text searched | `library keep KEY FILE`, `library page KEY`, `library find --text WORDS` |
| search, links, citing sites | `library find WORDS`, `library show REF`, `library related KEY`, `library cited KEY`, `library claims`, `library entries` |
| a document's citations against its own references | `library citecheck DOC` |
| the check and the index | `library check`, `library index`; `library keys` is what a consumer's check reads |

| Online | Command |
| --- | --- |
| a card from a reference entry, an identifier or a URL | `library resolve "ENTRY" --register`, `library resolve --url URL --register` |
| a copy, a re-check, a lost copy back | `library fetch KEY`, `library verify KEY`, `library restore` |
| works citing a card, a saved query | `library watch --add NAME --citing KEY`, `library watch`, `library candidates` |

A card is named by its key or by any of its identifiers wherever a command takes `REF`; every command takes `--json`; `library init` is the write behind the setup; `library --help` lists every command and `library <command> --help` its flags, and neither needs a bindings file.
The [skill](../../plugins/research/skills/library/SKILL.md) names every flag, and the kit's tests hold it to the script.

## The files it keeps

- The cards, `cards/<key>.md` under the library's directory, one per work; [Library cards](library-cards.md) specifies them.
- The index, `INDEX.md` beside them, written by `library index` and never by hand, one line per card.
- The store, ignored by version control, holding the copies that can be fetched again with the address each came from and the derived full-text index; and the kept directory, tracked, holding the copies nothing can fetch again, which `library keep` writes only with `--redistributable`, since a copy there is redistributed with the repository.
- The watches file and the candidates file, written by `library watch` and `library candidates`: what each watch has already seen, and the works surfaced that nobody has registered.
- The documents the project binds are read and never written: each entry of their `## References` section is tied to exactly one card at every check.

Where a key is cited is computed from the files `[cite] scan` names and never stored.

## `library.toml`

`library init --kept --scan records --scan WORKLOG.md` writes the bindings file at the project root, with the bindings filled in and the optional ones commented; it is the schema, with every binding explained where it stands, and the kit's tests hold this page to what `init` writes.
A project whose documents cite by key alone binds no `[entries] documents`; a project with no reports binds no internal directories; both halves of the check then say they looked at nothing there.

```toml
# library.toml — the reference library's bindings for THIS project.  Every path is relative
# to this file's directory.  The `library` skill reads it.

[paths]
library = "library"                 # cards/<key>.md, one per work; INDEX.md, generated by `library index`
store = "library/.store"            # IGNORED by version control: fetched copies and the derived full-text index
kept = "library/kept"             # TRACKED: copies nothing can fetch again
# reflow_module = "scripts/reflow.py"   # exports reflow_text(text): one sentence per line; built-in otherwise

[card]
kinds = ["article", "book", "chapter", "preprint", "thesis", "report", "document", "web", "repository", "dataset"]

[cite]
# A work is cited by this prefix and its card's key, `lib:jen1990`.  `library cited` and
# `library related` compute the citing sites from these files and directories (*.md under a
# directory) and store nothing.
prefix = "lib:"
scan = ["records", "WORKLOG.md"]

[entries]
# The documents whose `## References` entries are tied to cards; each entry must agree with exactly
# one card.  Empty where the documents cite by key.
documents = []
heading = "References"

[internal]
# A card naming a tracked file of the project (`file`) is an internal document — a report, a survey,
# anything made here or handed in.  Every file under these directories has its card; no bound
# document's reference entry may be tied to one.
kinds = ["report", "document"]
directories = []

[claims]
# The shapes of a sentence that credits a document against a named work, as regular expressions;
# the defaults are generic — a project with a prover adds its own words (`first formalization`,
# `machine-checked`, `in any prover`).
# shapes = []

[copy]
# Prints a PDF's text with a form feed between pages; `{file}` stands for the kept copy.
text_command = ["pdftotext", "-layout", "{file}", "-"]

[find]
limit = 10
```

## The check

Every check exits 0 when clean, 1 when it found problems, each printed with its place, and 2 when it could not run: no bindings file at the root, or one that does not parse.
The 2 is its own code so that a hook or a CI job never reads "did not run" as "clean".
`library citecheck` given a file that is not there, or with no document given and none bound, exits 2 as well.
`library check` ends with six coverage lines — the cards by grade and the copies by state, the cards a resolver wrote and the verify stamps, the internal documents, the extracts and how many a kept copy bears out, the watches, the reference entries read — so a green says what it did not look at, and that it asked no resolver; `library.py --selftest` plants one defect per code and fails when a code it can report is planted nowhere, and the kit's tests hold the table below to the script.

### `library check`

| Code | What it says |
| --- | --- |
| L0 | a card's front matter cannot be read: it is outside the subset the tool writes |
| L1 | the file's name is not lowercase letters, digits and hyphens, or the key is not the file's name |
| L2 | a field is missing, unknown or of the wrong shape, a kind the project does not list, a title missing, a year that is not a number, `metadata` or `verified` incomplete |
| L3 | two cards carry the same identifier |
| L4 | a read grade is not one of the four, a read without its date or, for a work read in parts, without which parts; an ungraded card that is not seeded |
| L5 | `via`, `related` or a body citation names a card that does not exist, a related card that does not name this one back, or an extract the cited card does not carry |
| L6 | a copy without a path and a hash, outside the store or the kept directory, or not matching its recorded hash |
| L7 | a state not among the legal ones, an excluded card without its reason and date, a registered card with an exclusion |
| L8 | a date that is not an ISO date or is in the future, or a card without its created date |
| L9 | a body is not one sentence per line |
| L10 | a body that is not `## Notes` then `## Extracts` with nothing before them |
| L11 | the index is missing or stale — run `library index` |
| L12 | a reference entry of a bound document that no card agrees with, that two cards agree with, or that names an internal document |
| L13 | a work a bound document cites is graded unread and names no `via` |
| L14 | the watch file or the candidates file cannot be read |
| L15 | an extract the kept copy does not bear out: its quotation is not in the kept text, or its locator names a section, page or statement that is not |
| L16 | an extract is malformed — its id, locator, words, caveat, rule or date — or its `checked` date is not a date or is in the future, or an unread card with no `via` carries an extract |
| L17 | a card naming a project file whose file is not in the tree or whose kind is not internal, an internal document recording another copy, or a card of an internal kind naming no file |

### `library citecheck`

`library citecheck [DOC…]` reads each document's text against its own `## References` section, the bound documents where none is given, and prints, as file and line:

- an author-year citation that no entry answers: none whose first author is the cited name, with the cited date, a letter suffix included;
- an entry the text never cites;
- a line under the heading written like an entry and not read as one, which no citation can reach.

Under `--json` each is a problem of code `CITE`; the last line counts the documents, the citations and the entries read.
It ties no entry to a card, which is `library check`'s L12.

## What goes online

`resolve`, `verify`, `fetch`, `restore` and `watch` call arXiv, doi.org, Crossref, OpenAlex, the OpenCitations index, GitHub's API and, when asked, zbMATH, Semantic Scholar and Unpaywall; they read three optional environment variables and never a file.
[What goes online, and what runs](../network.md) lists the hosts, the variables and the limits; nothing else in the kit leaves the machine.

## Words

- **card** — one file per referred work: its fields, how it was read, our notes, its extracts, its copy.
- **key** — a card's pinned name, the first author's surname and the year by default and an internal document's file stem, `--key` for another; a record cites a work as `lib:<key>`.
- **register (a work)** — `library register`: a new card for a work; distinct from registering a result, below.
- **read grade** — `unread`, `skimmed`, `parts`, `full`: a claim about the reader, not the work; a resolver's answer is never a read.
- **via** — the card a work is known through when it was not read itself.
- **extract** — what a work says at a place: a locator, the words quoted or restated, the author's caveat, the rule on what may be claimed; cited as `lib:<key>#<id>`.
- **copy, kept copy, the store** — a work's file: in the ignored store with the address it can be fetched from again, or in the tracked kept directory when nothing can, where it is redistributed with the repository, so `keep` writes there only with `--redistributable`.
- **resolver** — an online interface the library asks for a work's fields: arXiv, DOI, Crossref, OpenAlex and the others `docs/network.md` lists; never asked by a check.
- **watch** — a standing look for new works citing or related to a card, run by hand, keeping what it has seen and no clock.
- **candidate** — a work a watch surfaced and nobody has registered, kept in the candidates file until it is registered or set aside.
- **seeded** — a card loaded from an older list of works rather than registered for a citation, marked so.
- **internal document** — a document of the project itself with a card of an internal kind naming its tracked file; cited by key, never from a document's reference entries.
- **reference entry** — a line of a document's `## References` section, tied to exactly one card by title, first author and year.
- **author-year citation** — `Jen (1990)` or `(Jen, 1990)` in a document's text, answered by the entry of its references with that first author and date; `library citecheck` holds the two to each other.
