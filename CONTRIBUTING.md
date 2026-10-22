# Contributing

Issues and pull requests are welcome at [github.com/lividgreen/research-kit](https://github.com/lividgreen/research-kit).
A security problem is not an issue: [SECURITY.md](SECURITY.md) says how to report it privately.

## An issue

Say what you ran, what it printed and what you expected, with the tag or commit of the kit and the agent it ran under.
A wrong check is easiest to fix with the smallest record, card or bindings file that shows it.

## A pull request

[Development](docs/development.md) is the layout, the tests and how a release is cut; what a change carries follows from it.

- `python3 tests/run.py` passes; it runs every script's selftest and holds the documentation to the tools, with `markdownlint` and the Claude CLI on PATH where you have them.
- A script stays one file on the standard library of Python 3.11, and a helper the scripts share stays byte-identical in each.
- A new check code is named in [The checks](docs/checks.md) and planted by the script's selftest; a new subcommand or flag is named in its skill's `SKILL.md`.
- The change has a line under `## Unreleased` in [CHANGELOG.md](CHANGELOG.md), which the pull request's `changelog` check requires; the version fields are bumped at the release, not in the pull request.
- Markdown is one sentence per line and passes `.markdownlint.jsonc`.

Contributions are licensed under the [Apache License 2.0](LICENSE), as the rest of the repository.
