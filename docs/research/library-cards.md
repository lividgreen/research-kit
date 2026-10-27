# Library cards

A card is one Markdown file per work the project refers to: YAML front matter the `library` command owns, and a body of two sections, the project's notes and the work's extracts.
This page is the card's specification: its file and key, the front matter's form, every field and who writes it, the states and the read grades with the commands that move them, and the forms of a note, an extract and a copy.
[The library](library.md) is the tool: its commands, the index, the store and the kept directory, `library.toml` and the check that refuses a card that does not hold together.
Everything here is what `library.py` does, and the kit's tests hold the field list below to the script's schema.

## The file

A card is `cards/<key>.md` under the directory `library.toml` binds (`library/` by default), and the key is the file's name: lowercase letters, digits and hyphens, opening with a letter or a digit.
The key is pinned when the card is registered and never regenerated: the first author's surname and the year by default (`stuart1996`), a letter added on a clash (`jen1990b`); an internal document's key is its file's stem (`reports/review-1.md` is `review-1`), since a project's reports share their author and carry no year; `--key` pins another.
A record, a log entry or another card cites the work as the cite prefix and the key, `lib:jen1990`, and an extract as `lib:jen1990#thm4`.
A card is read alone: nothing on it names a record of the flow or of any other system.

## The form

The front matter stands between two `---` lines and is the subset of YAML the script writes: a field name in lowercase letters and underscores; a value that is a plain word, an integer, `null`, `true` or `false`, or a double-quoted string (a single-quoted one is read too); a block list (`- item`); a one-level map.
Every field of the schema is present, in the order below, `null` where it is empty and `[]` for an empty list, and a hand edit stays inside that subset, since `library check` reads every card back and fails one it cannot read.

The body is `## Notes`, then `## Extracts`, with nothing before them and no other section; it is one sentence per line, which the check enforces.
Notes are ours, in our words — what the work is, what we use it for, what we concluded about it, the history of a verdict — and each note `library note` writes is dated, `YYYY-MM-DD — the words`; a quotation is never a note.
Extracts are what the work states at a named place, one addressed block each, written by `library extract` in the form given below.

## The fields

The front matter carries, in this order: `key`, `state`, `excluded`, `kind`, `title`, `authors`, `year`, `venue`, `doi`, `arxiv`, `openalex`, `zbmath`, `isbn`, `url`, `metadata`, `verified`, `read`, `via`, `copy`, `related`, `tags`, `seeded`, `created`; and `file`, on an internal document alone.
*Register* is `library register`, or `library resolve --register`, which fills the same fields from a resolver's answer; *hand* is a field the project may edit in the file, where the check re-reads it.
Everything else is written by the command named and never by hand.

| Field | Holds | Written by |
| --- | --- | --- |
| `key` | the pinned key, the file's name | register |
| `state` | `registered`, or `excluded` for a work looked at and set aside | register; `exclude`, `exclude --undo` |
| `excluded` | `null`, or a map of `on` and `reason` while the card is excluded | `exclude` |
| `kind` | one of `[card] kinds`: `article`, `book`, `chapter`, `preprint`, `thesis`, `report`, `document`, `web`, `repository`, `dataset` by default; a kind of `[internal] kinds` is an internal document's | register |
| `title` | the work's title | register; `type --title`; `verify --take title` |
| `authors` | a list, each `Surname, I.` | register (`--author`, repeated); `type --author`; `verify --take authors` |
| `year` | an integer, or `null` | register; `type --year`; `verify --take year` |
| `venue` | where it appeared | register; `type --venue`; `verify --take venue` |
| `doi`, `arxiv`, `openalex`, `zbmath`, `isbn` | the work's identifiers, each normalized; no two cards share one; a preprint and its published version are one card carrying both | register; hand |
| `url` | the work's address, a repository's or a page's | register; hand |
| `metadata` | a map of `from` (`hand`, or the resolver that wrote the fields), `on` (the date) and `typed` (the fields a hand wrote over the resolver's, comma-separated, or `null`) | register; `type` and `verify --take` keep `typed` |
| `verified` | `null` until a resolver has been asked; then a map of `on` and `by`, the interfaces that answered | `verify` |
| `read` | a map of `grade` (`unread`, `skimmed`, `parts`, `full`; `ungraded` on a seeded card alone), `on` (the date of the reading, `null` for unread or an undated seeded reading) and `what` (the parts read, required for `parts`) | register (`--read`, `--read-on`, `--read-what`); `read` |
| `via` | the key of the card the work is known through when it was not opened itself | register (`--via`); `read --via` |
| `copy` | `null`, or a map of `path`, `sha256`, `fetched` (the date), `version`, `from` (the address it can be fetched from again, `null` for a copy obtained by hand), `pages` and `text` (whether it has text) | `fetch`, `keep`, `restore` |
| `related` | the keys of the cards linked to this one; every link is named back | `relate`, `relate --drop` |
| `tags` | free words | register (`--tag`); `note --tag`; hand |
| `seeded` | `true` for a card loaded from an older list of works rather than registered for a citation | register (`--seed`) |
| `created` | the ISO date the card was written | register |
| `file` | on an internal document, the tracked file of the project the card stands for; the file is its copy | register (`--file`) |

## The states, the grades and the transitions

A card has one state, and its reading has one grade; each moves through one command.

| What | From | To | Command | What else it writes |
| --- | --- | --- | --- | --- |
| a card | — | `registered`, graded `unread` | `register`, `resolve --register` | every field above from the arguments or the resolver's answer, `metadata.from` saying which; `--read GRADE` records a reading at once, `--seed` marks the card seeded and leaves it `ungraded` where no grade is given |
| a card | `registered` | `excluded` | `exclude --reason "…"` | `excluded` with its date and reason; the card stays findable so the work is not looked at twice |
| a card | `excluded` | `registered` | `exclude --undo` | `excluded` cleared |
| the reading | any grade | `unread`, `skimmed`, `parts` or `full` | `read --grade G` | `read.on` set to today or `--on DATE`, and to `null` for `unread`; `--undated` leaves it `null` on a seeded card alone; `read.what` names the parts for `parts`; `--via KEY` sets `via`; `--note` adds a dated note |
| the reading | `ungraded` | a grade | `read --grade G` | as above; no card returns to `ungraded`, which only `register --seed` writes |

The grade is a claim about the reader: a reading done now is dated today, a date is never guessed, and a resolver's answer or a subagent's report is a candidate for the fields and the notes, never a read.

The other commands change a card without moving its state or grade:

| Command | What it writes |
| --- | --- |
| `type --title/--author/--year/--venue` | the work's own fields corrected by hand over what a resolver wrote; each field is added to `metadata.typed` where the card was written by a resolver |
| `verify KEY` | re-resolves the card at its own identifiers; where every answer is the card's work, stamps `verified` with the date and the interfaces, prints each field that differs and writes it only where `--take FIELD` names it |
| `relate KEY KEY`, `--drop` | the symmetric link on both cards |
| `note --note "…" --notes FILE --tag T` | a dated note under `## Notes`, and the new tags |
| `extract ID --at "…" --quote "…"` | an extract block under `## Extracts`; `--replace` rewrites the one with that id |
| `fetch`, `keep FILE`, `restore` | the `copy` map and the file it names; `--replace` takes a new copy over a recorded one |

## An extract

An extract is one block under `## Extracts`, a blank line between blocks:

```markdown
**thm4** — Theorem 4 — checked 2026-10-23, 2nd edition
Quote: "the work's own words"
Restated: what it says there, in ours
Caveat: the author's own caveat
Rule: what may be claimed of it
Unanchored: why the kept copy cannot bear it out
```

The head line is the id in bold — lowercase letters, digits and hyphens, once per card — the locator, the date it was checked and, after a comma, the edition where it is not the kept one; a locator is one line and holds no long dash set off by spaces.
An extract says something: it carries a `Quote:` or a `Restated:` line, and the other labels are optional; a line opening with no label continues the field above it.
It is written by `library extract`, which refuses a block that does not read back as written, and refuses an extract on a card graded `unread` that names no `via`.
Where the card's copy is kept and has text, every quotation must stand in that text and a numbered locator — a theorem, a proposition, an equation, a section — must occur in it, unless the extract says under `Unanchored:` why the copy cannot bear it out; an extract with no copy, no text or another edition is counted unanchored with the reason and never passes silently.

## A copy

A copy is one file per card, `<key>/copy.<ext>`, recorded on the card with the hash of its bytes.
A copy with an address — fetched by `library fetch`, or taken in by `library keep --from URL` — lives in the store, which version control ignores, since it can be fetched again; `library restore` fetches every recorded copy the store has lost and checks it against its hash.
A copy with no address lives in the kept directory, which is tracked and travels with the repository, so `library keep` writes there only with `--redistributable`, the project's word that it may redistribute the file.
A recorded copy that is not on disk is counted by the check and never fails it; one that is on disk must match its hash.
An internal document's copy is its tracked file: nothing is fetched, kept or hashed, and `library page` and `library find --text` read it as they read a kept copy.
