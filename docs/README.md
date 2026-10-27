# Documentation

The kit first — what it is, how it is used and installed, what it assumes — then one section per plugin: one page per tool, each with the tool's commands, the files it keeps, its bindings, its check and its words, and a specification of its cards where it has them.

## The kit

- [Why research-kit](why.md) — the failures in one research project each piece of the kit replaced
- [How to use](how-to-use.md) — a research thread as you say it to the agent, and the commands underneath
- [Scope](scope.md) — what the kit assumes, what the agent does without asking, where each kind of fact lives, what it is not
- [Install](install.md) — the routes, the supported agents, the optional tools, updating
- [What goes online, and what runs](network.md) — the online commands, the hosts they call, the environment variables they read
- [Development](development.md) — the layout, the tests, how a release is cut; the [CHANGELOG](../CHANGELOG.md) beside the README

## The `research` plugin

The [plugin's page](../plugins/research/README.md) says what each of its seven skills is for.

- [Getting started](research/getting-started.md) — a first project step by step: the records as written, a failed check, a card, the dashboard
- [The research setup](research/research-init.md) — what a setup is, what `/research:research-init` probes, asks, writes and installs
- [The flow](research/flow.md) — the records' tool: the commands, the index, the directions and the log, `flow.toml`, every code `flow check` reports, its words
- [Flow cards](research/flow-cards.md) — the specification of a record: the files, the form, every field of the four kinds, the states and the transitions
- [The library](research/library.md) — the cards' tool: the commands, the store and the kept directory, `library.toml`, every code `library check` reports, its words
- [Library cards](research/library-cards.md) — the specification of a card: the file and the key, the form, every field, the states and the grades, an extract, a copy
- [The dashboard](research/dashboard.md) — the read-only page over the records and the cards: the flags, what it mounts, the component protocol
- [The working rules](research/working-rules.md) — `method`, `design` and `debug`, and the method's words

## The `formal` plugin

The [plugin's page](../plugins/formal/README.md) says what its three skills, the prover agent and the manifest generator are for.

- [The formal setup](formal/formal-init.md) — what a setup is, what `/formal:formal-init` probes, writes and installs, `formal.toml`
- [The handoff](formal/handoff.md) — what a prover prompt carries, the prover agent, `formal handoffcheck`
- [The landing](formal/land.md) — the `formal` commands, the manifest and its grammar, `formal check` and the three gates, its words

Each skill is documented by its own `SKILL.md` under [`plugins/`](../plugins), which is also what the agent reads.
