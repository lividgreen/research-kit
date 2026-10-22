# Kept copies

A copy is one file per card, `<key>/copy.<ext>`, and the card records it: the path, the hash of its bytes, the date it was obtained, the version, the address it came from, the count of its pages and whether it has text.
A copy with an address lives in the store, which version control ignores: it is re-fetchable, so it is not committed.
A copy with no address lives in the kept directory, which is tracked: nothing can fetch it again, so version control is its backup — and whoever receives the repository receives the copy, so a work goes there only where the project may redistribute it; the store, which version control ignores, holds what can be fetched again.
The project names both directories; where it names no kept directory, a copy obtained by hand goes to the store and the check names it as needing a backup.
`library fetch` takes the copy by the card's identifiers: for an arXiv work the TeX source of its latest version, whose formulas read as written where a PDF's text garbles them, and the PDF where there is no source; otherwise the card's own address where it answers a file; or the address given with `--url`.
The open-access lookup for a DOI needs a contact address and runs only when the environment sets one.
An address that answers a page and not a file keeps nothing.
`library keep` takes in a file obtained by hand — a scan, a book, a report handed in, a download a site refuses to a program; with `--from` it goes to the store as a fetched copy would, and with no address it goes to the kept directory only with `--redistributable`, since that directory travels with the repository: the command refuses without one of the two, and writes nothing.
The text is derived from the copy and never recorded: a PDF's pages through the command the project names, a TeX source cut at its sections with its inputs put in and its comments dropped, each unit kept as one file under the store, whichever directory holds the copy.
A PDF with no text in it is recorded as such and read as page images; `library page` prints the command for one page.
`library restore` is for a reinstalled machine or an emptied store: each recorded copy that is not on disk is fetched from its recorded address and written only if its bytes have the recorded hash, an address that now answers other bytes writing nothing and saying so; a copy with no address is named, to be restored from version control.
`library fetch` and `library restore` are online, on demand, and never part of `library check`; so is a run of `library watch`.
`fetch --url` and `resolve --url` fetch the address given, whatever it is, and the text of a kept PDF is produced by the command the project binds (`[copy] text_command`, `pdftotext` by default), run over the kept file.
