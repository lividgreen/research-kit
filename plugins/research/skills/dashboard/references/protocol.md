# The component protocol

A component is a command.
The dashboard asks it two things and nothing else: its page manifest, once, as `<command> --json pages`, and then each page as `<command> --json <subcommand> …`, exactly as the manifest said.
Every answer is one JSON object; an answer with `"ok": false` carries `problems`, a list of objects with a `msg`, which the dashboard shows (as a 404 when the message says the thing does not exist).

## The manifest

```json
{"component": "flow", "title": "Records", "mount": "/flow", "home": "/flow",
 "nav": [{"label": "Table", "path": "/flow"}, {"label": "Check", "path": "/flow/check"}],
 "card": { … },
 "links": [{"pattern": "\\b(?:idea|task)-\\d{4}\\b", "path": "/flow/r/{0}"}],
 "routes": [ … ]}
```

- `mount` is the path prefix every route of the component lives under; two components never share one.
- `nav` is what the header shows for the component, in order; the entry of the page being read is marked.
- `home` is the component's home page, a path under its mount.
  `/` goes to the home of the first mounted component that names one; where none does, `/` goes to the mount of a lone component and is a page listing the components otherwise.
- `card` says how one of the component's records is laid on a card's face, below; a component with no `card` has its records shown as rows and fields.
- `links` are regular expressions applied to the text of every page of every component; a match becomes a link to `path`, with `{0}` the whole match and `{1}`, `{2}` its groups (an unmatched group is empty, and a trailing `#` is dropped).
  So a record citing a card links to the card, and a card's citing site links to the record, whichever component rendered the page.

## The card

`card` is a map of paths into a record (dotted, `a.b`), and the dashboard lays every record of a `list` or a `record` page, and every card of a `table` page, on one face from it:

```json
"card": {"id": "id", "title": "title", "summary": "summary", "tags": "tags", "rank": "rank",
         "label": "type", "faces": {"idea": "idea", "question": "question", "task": "task",
                                    "finding": "finding", "goal": "goal", "direction": "direction"},
         "standing": ["standing", "state"], "place": "place", "lines": "lines", "link": "/flow/r/{id}",
         "meters": [{"label": "value", "field": "value", "scale": ["low", "medium", "high"],
                     "kinds": ["idea", "question", "task"], "frame": true},
                    {"label": "effort", "field": "size", "scale": ["small", "medium", "large"],
                     "kinds": ["question", "task"]}]}
```

A library's, whose works are all one face:

```json
"card": {"id": "key", "title": "title", "tags": "tags", "label": "kind", "face": "work",
         "standing": ["read.grade"], "lines": "lines", "link": "/library/{key}"}
```

Every value is a path into a record, but these:

- `faces` maps the value of `label` to one of the dashboard's seven faces, `idea`, `question`, `task`, `finding`, `goal`, `direction` and `work`; `face` instead gives one face to every record.
  A record whose face is none of the seven, or has none, is laid on a neutral grey face with no sign.
  The `label`'s value is also the kind's word on the card (`Idea`, `Article`).
- `standing` is a list of paths, the first that holds something being the standing: a badge, `ready`, `held`, `parked`, `blocked` coloured and any other word grey; a card parked or blocked lies on greyer paper (a standing `parked, blocked` is two badges).
- `place` is the line after the badge at the card's foot; `lines` is a list of `{"label", "text"}`, of which the card shows the first two at the foot of its text box, one line each, cut with an ellipsis.
- `link` is the record's page, filled from the record's scalar fields (`{id}`); the whole card is one link to it.
- `summary`, where the component has one: the card shows it folded to six lines, and `no summary yet` where the record's is empty; a component with no `summary` path shows no such words.
- `meters` are the parameters, each `{"label", "field", "scale", "kinds"}` with `scale` the levels in rising order and `kinds` the values of `label` the meter is shown on (every kind where it is left out).
  The meter with `"frame": true` is drawn as three gems and decides the card's frame, the others as three bars; a field that holds none of the levels is not judged, three empty outlines in grey.
  The frame is none for a card not judged, a plain one for the first level, gold for the last and silver for those between, and the gems or bars fill in proportion where the scale is not three levels long.

The face is 240 px wide, from the top: the band (the rank in a white pip where there is one, the kind's sign, the id), the title, whole and never cut, the type line (the kind's word and the tags), the text box, the parameters, and the foot.
The dashboard prints what the record holds and calculates nothing: a record is named in `lines` by the component's own words, and where a card is, its `place`, is the component's own sentence.

## Routes

A route is `{"path": …, "view": …, "run": […], "title": …}` plus the keys its view takes.
`path` may carry `{name}` segments, bound from the request and substituted into `run` and `title`; fixed paths are matched before templated ones.
`run` is the subcommand and its arguments, to which the view adds what the query string gives.

| View | Reads from the answer | Keys |
| --- | --- | --- |
| `markdown` | `field` (default `text`), a Markdown string | `field` |
| `lines` | `field` (default `lines`), a list of lines, shown in a block with links | `field` |
| `list` | `records`, a list of objects; `total`, `next`, `rankers` when present | `words` (the query parameter whose words become positional arguments), `params` (query parameters passed as `--name value`, each a name or `{"name", "choices"}`), `flags` (passed as `--name` when set), `note`; with no `card` in the manifest also `columns` (dotted paths into a record) and `link` (`{"column": "id", "path": "/flow/r/{id}"}`, the path filled from the record's own scalar fields) |
| `table` | `field` (default `zones`), a list of zones, below | `field`, `list` (the route's list path, which a zone's link is made from), `params` |
| `record` | `fields` (default `records.0`), `body` (a Markdown string), and each section's `field` | `fields`, `body`, `heading` (the field shown as the page heading; where the route names none, the card's title heads the page), `hide` (fields never shown, `a.b` for a key inside a map), `hrefs` (`{"doi": "https://doi.org/{}"}`), `sections` (`{"field": …, "title": …, "as": "refs" \| "sites" \| "lines"}`) |
| `tables` | one answer per table | `tables` (`{"title": …, "run": […], "field": …, "columns": […]}`), `note` |
| `check` | `problems`, `warnings`, `coverage` | — |

A `refs` section is `{field: [{"id": …, "title": …}]}`; a `sites` section is `[{"path": …, "line": …, "text": …}]`.
A `state`, `status` or `grade` value is shown as a badge wherever it appears.

**The `list` view** lays each record as a card where the manifest has `card`, and as a row of `columns` where it has none, with its filter form and its paging as they are: a `params` entry given as `{"name": "type", "choices": ["idea", "task"]}` is a select (with `any`), a name alone a text input, each flag a checkbox, and an answer carrying `next` (an offset) gets a next-page link that passes it as `--from`.
The filter's query is what a zone's link carries: `/flow/list?held=1&owner=ann` runs the route's command with `--held --owner ann`.

**The `table` view** renders a list of zones, `{"kind", "owner", "title", "count", "note", "room", "find", "cards"}`, in the answer's order, each card of `cards` laid on the face as the `list` view lays it:

- a `hand` (`kind`): its heading with its `note` beside it, its cards, and one dashed empty place for each of `room` (`null`, no limit, for none);
- a `deck`: its heading, then a stack of card backs carrying `count`, the `note` under it and a link `The whole deck`, then its cards face up; an empty deck (a `count` of 0) is its heading and `no cards`;
- a `pile`: the piles together in one row under the heading `Piles`, each a small stack with its `count`, its `title` and its `note`, the whole a link.

A zone's link is the route's `list` path with `find` as its query: a key with a `true` value is a flag set (`held=1`), any other value a parameter.
The page has no link where the route names no `list`.
A component with no `card` has its zones' cards laid on the neutral face from the fields `id` and `title`.

**The `record` view** puts the record's card at the left, enlarged 1.6 times, and beside it a paper panel: the title as its heading (the route's `heading` field where it names one), the summary whole, the body, and under them the fields the face does not carry, which are every field but the ones the `card` paths name (the standing's first path that held something, and the meters that apply to the card's kind) and those `hide` names.
A `refs` section is a row of small cards, each the band with the id and the name of the link's field and the title under it; the band takes a face's colour where the id opens with a value of `faces`' keys followed by a hyphen (`task-0004`), a neutral one otherwise, and the card is a link where a pattern of `links` matches the whole id.
That is a heuristic on the id, the items being `{"id", "title"}` only: an id with another prefix, as a project that sets its own prefixes has, gets the neutral band.
A `sites` section stays a list of lines.
A route of a component with no `card` renders its record as it always did, a table of the fields under the page's title, with its `refs` as small cards.

The dashboard serves one stylesheet in each page and no script, and fetches nothing from another host.
Its ground follows the browser's light or dark setting and a card's paper is the same in both.

## Mounting

A component skill carries `component.toml` beside its `SKILL.md`:

```toml
command = ["python3", "scripts/flow.py"]   # relative to this directory; python3 is the dashboard's own interpreter
bindings = "flow.toml"                     # the file whose presence at the project root mounts the component
```

A project may instead list components in `dashboard.toml` at its root:

```toml
[[component]]
name = "flow"
command = ["flow"]
```

The dashboard never reads the files behind a component; a component that wants a page to exist answers it.
