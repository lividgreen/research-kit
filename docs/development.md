# Development

## Layout

```text
.claude-plugin/marketplace.json   the repository as its own marketplace, listing the two plugins
.agents/plugins/marketplace.json  the same for Codex
.cursor-plugin/marketplace.json   the same for Cursor's team marketplaces (GitHub Copilot and VS Code read Claude Code's)
plugins/<plugin>/                 one plugin each: research and formal
  .claude-plugin/plugin.json      its Claude Code plugin manifest
  plugin.json                     its Agent Plugins manifest (Codex and others)
  skills/<name>/SKILL.md          one skill each; scripts/ and references/ beside it; component.toml where the
                                  skill adds pages to the dashboard
  skills/*-init/                  each plugin's setup skill: research's over scripts/setup.py, formal's over `formal probe`
  agents/<name>.md                the plugin's agents (formal: the prover session), on the session's own model
  claude-agents/<name>.md         Claude Code's copy, which its manifest names: the same text, on a model it picks
  com.github.copilot/, dev.openhands/, com.google.antigravity/
                                  the agents' copies for the Agent Plugins clients that read agents, each from its
                                  own directory (Antigravity's through agents.json, with the tools it must list)
docs/                             this documentation; CHANGELOG.md beside the README
.markdownlint.jsonc               the Markdown rules the repository's own files are held to
packaging/                        the package stub the console scripts import through
tests/run.py                      the tests
tools/release.py                  cuts a release: the version fields, the changelog, the commit and the tag
.github/workflows/tests.yml       the same tests on every push, on three Python versions, plus a wheel build
.github/workflows/changelog.yml   every pull request adds a line under the changelog's `## Unreleased`
.github/workflows/release.yml     a pushed tag v*: the tests, the GitHub Release from the changelog, the website told
pyproject.toml, .pre-commit-hooks.yaml, CITATION.cff, LICENSE, NOTICE
CONTRIBUTING.md, SECURITY.md      what a change carries; how a vulnerability is reported
```

Each script is one file on purpose: a per-skill install carries the skill directory and nothing beside it.
The helpers the scripts share (the sentence splitter) are duplicated and held byte-identical by the tests.
The package build carries the four command scripts, `flow`, `library`, `dashboard` and `formal`, from their skill directories into one package (`pyproject.toml`'s force-include), so the scripts stay where the skills are.

A change is welcome as an issue or a pull request; [CONTRIBUTING.md](../CONTRIBUTING.md) says what a pull request carries, and [SECURITY.md](../SECURITY.md) how a vulnerability is reported privately.

## Tests

```sh
python3 tests/run.py
```

runs each script's `--selftest` (one planted defect per rule; `formal`'s over a synthetic workspace) and checks that:

- the duplicated helpers agree;
- the three marketplaces list the two plugins, and each plugin's manifests agree on name, version and description;
- every `SKILL.md` has the frontmatter the standard asks for and names a script that exists;
- every subcommand of each CLI and every flag it takes is named in its skill, and every skill's `metadata.version` is its plugin's;
- the shell blocks of [Getting started](getting-started.md) run in order in one fresh directory;
- the README's *How to use* table is the [site home page](index.md)'s *Try it* table row for row;
- every relative link of the README, `CONTRIBUTING.md`, `SECURITY.md`, this documentation and the plugins' READMEs resolves, and every repository path their prose names in backticks exists;
- [The bindings files](bindings.md) equals what each `init` writes, and [The checks](checks.md) names every code the scripts can report.

It also runs `markdownlint` over the repository's Markdown with `.markdownlint.jsonc` where it is on PATH, and `claude plugin validate --strict` where the Claude CLI is on PATH.
The flow's selftest writes records under its built-in markdownlint configuration where `markdownlint` is on PATH, and fails without it in CI (`CI` set), where the workflows install it.
The workflow in `.github/workflows/tests.yml` runs the same on every push and pull request, on Python 3.11, 3.13 and 3.14, then builds the wheel the hooks install and runs each of its four console scripts.
A checkout's hooks are tried in a project with `prek try-repo /path/to/research-kit flow-check --all-files` (or `pre-commit try-repo`); the package is the hooks' alone, and its console scripts import the skills' scripts the wheel build carries into it, so an editable install does not work.
A checkout's plugins are tried in Claude Code by adding the checkout as a marketplace by its path, `/plugin marketplace add /path/to/research-kit`, which takes the name `research-kit` the released marketplace has.
A trial install can stay in `~/.claude/plugins/cache/research-kit/<plugin>/<version>/`, and Claude Code reuses a cached copy whose version matches, so a release carrying the version the trial carried would run the trial's files: after a trial, remove the marketplace (`/plugin marketplace remove research-kit`) and delete `~/.claude/plugins/cache/research-kit` before adding the released one.

## Releases

A release is a tag, cut on a clean `main` by one command:

```sh
python3 tools/release.py 0.2.0            # --date YYYY-MM-DD for another day than today, --dry-run to see the files first
git push --atomic origin main v0.2.0
```

The script writes the version into each plugin's `.claude-plugin/plugin.json` and `plugin.json`, the `metadata.version` of each of its skills, and research-kit's `pyproject.toml`; Claude Code refreshes an installed plugin only when the manifest's `version` changes.
It turns the changelog's `## Unreleased` heading into the tag and the date (`## v0.2.0 — 2026-11-30`, the heading opening with the tag), runs the tests, commits and tags.
Then it opens a fresh `## Unreleased` in a second commit, after the tag, so the changelog the website publishes at the tag carries no empty heading.
It refuses an empty `## Unreleased`, a version not above the last release, an existing tag, a dirty tree or another branch, and a failed test leaves nothing committed; it pushes nothing, and the atomic push sends both commits and the tag or none of them.
The tests hold the version fields equal to each other and to the changelog's last release, and every changelog heading to `## Unreleased` or `## vX.Y.Z — YYYY-MM-DD`.
The marketplace entry carries no version of its own.
The tag is what a project's hooks pin (pre-commit's `rev`) and what Zenodo archives; no file in the repository names a version other than those version fields and the changelog's headings.

The pushed tag starts `.github/workflows/release.yml`, which does the rest: it runs the tests at the tag, refuses a tag that is not the version the manifests carry, creates the GitHub Release titled with the tag and with the tag's section of `CHANGELOG.md` as its notes (no section, no release), and tells the website's repository, which records the release on the project card and publishes the documentation at the tag.
Run by hand with a tag, the workflow creates a Release that is missing and resends the announcement for one that exists.
The announcement needs the repository secret `WWW_DISPATCH_TOKEN`, a fine-grained token with contents write on `lividgreen/www.livid.work` and nothing else.

## The website

[research-kit.livid.work](https://research-kit.livid.work) is this repository's Markdown at the latest tag, rendered by the [www.livid.work](https://github.com/lividgreen/www.livid.work) repository; nothing here builds or configures it.
What it renders:

| Repository path | Route | Notes |
| --- | --- | --- |
| `docs/index.md` | `/` | The site's home page |
| `docs/README.md` | `/docs/` | Also the navigation: its link list, one line per document with the title, the file and a description, gives the order and labels of the documentation |
| `docs/<name>.md` | `/docs/<name>/` | |
| `CHANGELOG.md` | `/changelog/` | Linked from the version in the header |
| `plugins/<plugin>/README.md` | `/plugins/<plugin>/` | |
| `plugins/<plugin>/skills/<skill>/SKILL.md` | `/plugins/<plugin>/skills/<skill>/` | The frontmatter's `name` and `description` feed the skills list of the navigation |
| anything else, `README.md` included | not rendered | A relative link to it is rewritten to the file on GitHub at the tag; an image to its raw URL |

On every page the first heading is the page title, removed from the body, and every page also exists as `<route>.md`, the source file as is.
`README.md` is GitHub's front page and is not rendered: it follows README conventions, with the badges and the install commands, and points at the site; `docs/index.md` is the site's home and carries no badges.
So the documents link each other by relative path only, as the tests already require (every relative link must resolve), and carry no HTML beyond the README's badges; `docs/README.md` does not list `index.md`, which the site's header links; a document is added to the site by a line in `docs/README.md`.
