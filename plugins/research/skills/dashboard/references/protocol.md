# The component protocol

A component is a command.
The dashboard asks it two things and nothing else: its page manifest, once, as `<command> --json pages`, and then each page as `<command> --json <subcommand> …`, exactly as the manifest said.
Every answer is one JSON object; an answer with `"ok": false` carries `problems`, a list of objects with a `msg`, which the dashboard shows (as a 404 when the message says the thing does not exist).

## The manifest

```json
{"component": "flow", "title": "Records", "mount": "/flow",
 "nav": [{"label": "Records", "path": "/flow"}, {"label": "Check", "path": "/flow/check"}],
 "links": [{"pattern": "\\b(?:idea|task)-\\d{4}\\b", "path": "/flow/r/{0}"}],
 "routes": [ … ]}
```

- `mount` is the path prefix every route of the component lives under; two components never share one.
- `nav` is what the header shows for the component, in order.
- `links` are regular expressions applied to the text of every page of every component; a match becomes a link to `path`, with `{0}` the whole match and `{1}`, `{2}` its groups (an unmatched group is empty, and a trailing `#` is dropped).
  So a record citing a card links to the card, and a card's citing site links to the record, whichever component rendered the page.

## Routes

A route is `{"path": …, "view": …, "run": […], "title": …}` plus the keys its view takes.
`path` may carry `{name}` segments, bound from the request and substituted into `run` and `title`; fixed paths are matched before templated ones.
`run` is the subcommand and its arguments, to which the view adds what the query string gives.

| View | Reads from the answer | Keys |
| --- | --- | --- |
| `markdown` | `field` (default `text`), a Markdown string | `field` |
| `lines` | `field` (default `lines`), a list of lines, shown in a block with links | `field` |
| `list` | `records`, a list of objects; `total`, `next`, `rankers` when present | `columns` (dotted paths into a record), `link` (`{"column": "id", "path": "/flow/r/{id}"}`, the path filled from the record's own scalar fields), `words` (the query parameter whose words become positional arguments), `params` (query parameters passed as `--name value`), `flags` (passed as `--name` when set), `note` |
| `record` | `fields` (default `records.0`), `body` (a Markdown string), and each section's `field` | `fields`, `body`, `heading` (the field shown as the page heading), `hide` (fields never shown, `a.b` for a key inside a map), `hrefs` (`{"doi": "https://doi.org/{}"}`), `sections` (`{"field": …, "title": …, "as": "refs" \| "sites" \| "lines"}`) |
| `tables` | one answer per table | `tables` (`{"title": …, "run": […], "field": …, "columns": […]}`), `note` |
| `check` | `problems`, `warnings`, `coverage` | — |

A `refs` section is `{field: [{"id": …, "summary": …}]}`; a `sites` section is `[{"path": …, "line": …, "text": …}]`.
A `state`, `status` or `grade` value is shown as a badge wherever it appears.
A `list` answer carrying `next` (an offset) gets a next-page link that passes it as `--from`.

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
