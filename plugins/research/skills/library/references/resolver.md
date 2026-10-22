# Writing a card from a resolver

`library resolve` takes a reference entry as it is written — authors, year, title, venue — and asks the interfaces for the work.
An identifier inside the entry, or given with `--doi` or `--arxiv`, is resolved where it lives: an arXiv identifier at arXiv, a DOI by content negotiation.
An entry with no identifier, or whose identifier answered another work, goes to the search interfaces in order, Crossref and then OpenAlex, the next asked only while no candidate has passed; `--at zbmath` or `--at semantic-scholar` asks one optional interface by name.
Every answer is a candidate, and a candidate is accepted only past the identity check: its title against the entry's, its first author's surname and its year each found in the entry.
A candidate that fails is printed beside the entry and nothing is written.
A record that carries the year a work went online and the year of its printed issue has both as its years, and the one the entry gives is written.
A record's title with a damaged character is never written: the entry's own title is, and is marked as typed.
With `--register` the card is written from the first candidate that passes: the tool types the fields, and whoever runs it supplies at most the key, the tags and a note.
A field given on the command line (`--title`, `--author`, `--year`, `--venue`, `--kind`) is kept where the resolver's differs, the difference is printed, and `metadata.typed` names it.
The same work answered by a second interface lends the card its identifiers, so a preprint and its published version are one card.
`--pick N --override "reason"` takes a candidate that failed, the reason dated into the notes and `verified` left empty, since a failed identity check verifies nothing; it is for a later edition or a damaged record, never for a doubt.
A repository or a page is resolved at its address: `library resolve --url` asks the forge's API for a repository (GitHub today) and reads any other page's citation metadata — the `citation_*`, Dublin Core and Open Graph tags, then the title element — and the address itself passes as the entry when the page has a title.
A work no interface holds — an old book, a scan, a thing with no address — is registered by hand with `library register`, and the check counts the cards typed by hand.

`library verify` asks again at the card's own identifiers.
A card passes when every answer is its work by title and first author and one answer carries its year; it is then stamped with the date and the resolvers.
A field the resolver gives differently is printed and left as it is; `--take FIELD` writes the resolver's value for one card.
A card whose identifier answers another work fails, is not stamped, and is to be corrected by hand before anything cites it.

Both commands are online, on demand, and never part of `library check`.
The interfaces they call: arXiv, DOI content negotiation at doi.org, Crossref, OpenAlex, GitHub's API for a repository's address, the page itself for any other address, and on `--at` zbMATH or Semantic Scholar; `fetch` also asks Unpaywall for an open-access copy of a DOI when a contact address is set.
They need no key: a contact address (`LIBRARY_MAILTO`), an OpenAlex key (`OPENALEX_API_KEY`) and a Semantic Scholar key (`SEMANTIC_SCHOLAR_API_KEY`) are read from the environment when set and from no file, and the first line of either command says which were set and prints no value; the address is sent in the User-Agent of every request the library makes and as the polite-pool parameter where an interface takes one, so every host called sees it.
With no key OpenAlex meters a search, so it is asked second and only on a miss; Semantic Scholar refuses most calls made with no key.
A resolver's answer is a candidate for the card's fields and never a read: the grade does not move.
