# Documentation

- [Why research-kit](why.md) — the failures in one research project each piece of the kit replaced
- [How to use](how-to-use.md) — a research thread as you say it to the agent, and the commands underneath
- [Getting started](getting-started.md) — the records as written, a failed check, a card, the dashboard
- [Scope](scope.md) — what the kit assumes, what the agent does without asking, what it is not
- [Install](install.md) — the routes, the supported agents, the optional tools, updating
- [What goes online, and what runs](network.md) — the online commands, the hosts they call, the environment variables they read
- [Glossary](glossary.md) — every word the skills use, one line each
- [The bindings files](bindings.md) — `flow.toml`, `library.toml` and `formal.toml` as `init` writes them, every binding explained
- [The checks](checks.md) — every code `flow check` and `library check` can report, what the `formal` checks verify, the exit codes
- [Development](development.md) — the layout, the tests, how a release is cut; the [CHANGELOG](../CHANGELOG.md) beside the README

Each skill is documented by its own `SKILL.md` under [`plugins/`](../plugins), which is also what the agent reads.
