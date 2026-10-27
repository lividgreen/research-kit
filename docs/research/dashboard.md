# The dashboard

The dashboard serves the records and the cards as a read-only page on localhost: the ranked list, each record with its links and back-references, the directions file and the validator's verdict; each card with its notes, extracts and citing sites, the candidates and the watches and the check.
It is a renderer and nothing else: every page is the answer of a component's command with `--json`, so the page and the command line cannot disagree; it reads no record or card file itself, writes nothing, serves no path into the library's store, and re-asks on every request, so a transition run in another terminal shows on the next reload.
The tool is `scripts/dashboard.py` of the [`dashboard`](../../plugins/research/skills/dashboard/SKILL.md) skill (`/research:dashboard` in Claude Code), one Python 3.11 file on the standard library; the `markdown` package renders bodies where it is installed, paragraphs otherwise.

## The commands

`dashboard` serves on port 8765 and answers only a request addressed to it by name; its flags:

| Flag | What it does |
| --- | --- |
| `--port N`, `--host ADDR` | another port; `--host 0.0.0.0` serves other devices under this machine's names and addresses |
| `--allow-host NAME` | another name it answers to, behind a proxy or a tunnel |
| `--root DIR` | the project, found upward from the working directory otherwise |
| `--component CMD…` | a command mounted by hand |
| `--list` | what would be mounted, and nothing served |

`dashboard.py --selftest` mounts a stub component and renders every view.

## What it mounts

Components are found in this order, the first mount of a name winning: a `--component` on the command line; `dashboard.toml` at the project root, with `[[component]]` tables naming a `command` list; the skill directories beside the dashboard's whose `component.toml` names a `command` and a `bindings` file, mounted when the bindings file exists at the project root; the `flow` and `library` commands on PATH when their bindings file exists.
So a skill adds its pages to the one dashboard by being installed beside it — in the same skills directory, or as a sibling plugin of the same marketplace — and bound in the project: with `flow.toml` at the root the records are mounted, with `library.toml` the cards.

## Writing a component

A component is any command that answers `<command> --json pages` with a page manifest — its mount, its navigation entries, the link patterns that turn an id in any text into a link across components, and its routes with their views (`markdown`, `lines`, `list`, `record`, `tables`, `check`) — and every other page as `<command> --json <subcommand> …`.
The skill's [`references/protocol.md`](../../plugins/research/skills/dashboard/references/protocol.md) is the manifest's shape; a component ships a `component.toml` beside its `SKILL.md` naming its command relative to the skill directory and the project's bindings file.

## Words

- **component** — a skill whose CLI answers `--json pages`, which the dashboard mounts.
