# The formal setup

`/formal:formal-init` sets the prover side up for a project with a Lean 4 workspace and checks an existing setup: it probes the workspaces, the project and the machine with `formal probe`, proposes what is missing, installs nothing without your word, re-checks what exists against the workspace as it stands and adds what is missing, rewriting nothing without your word, and reports.
It runs on its own: with no research setup the handoff and the landing work from the document rows and the commit, and where the `research` plugin is set up ([The research setup](../research/research-init.md)) the setup reads its bindings to fill its own; the probe and `formal init` are commands of the `formal` script, which lives in the `land` skill, and the [`formal-init`](../../plugins/formal/skills/formal-init/SKILL.md) skill is the procedure around them.

## What a setup is

Required, since a handoff or a landing does not run without it:

- a Lean workspace under the project root with its lakefile, `lean` and `lake` on PATH;
- `formal.toml`, written by `formal init --workspace DIR`, its `[packages]` naming each library root the probe found, one manifest per package and `[manifest] generate` the command that writes each;
- `DeclManifest.lean` in the workspace, copied from the `land` skill's `scripts/`, and the manifest it writes after a build, since `formal check` and the landing read it, and `formal resolve`, which the flow asks, answers from it ([The landing](land.md) has the generator and the manifest's grammar);
- the prover session's standing instructions at the path `formal.toml` names, written from the `handoff` skill's template with its slots filled ([The handoff](handoff.md));
- the `formal-check` hook beside the flow's and the library's, and `formal-cite`, `formal-anchors` and `formal-register` where their bindings are filled.

Recommended: the prover's language server registered in the project's `.mcp.json`, since the prover agent uses whatever prover tools are registered and works blind without them; `elan`, which installs `lean` and `lake` at the workspace's pin.

## What it does

1. Probes: `formal probe` reports the tools on PATH, each workspace with its package, roots, toolchain and generator (`DeclManifest.lean` present, absent, or stale where it differs from the skill's copy, with the copy as a proposal), the project's bindings, the pins, the proposals and a coverage line, and writes nothing.
   The pins are the hooks' `rev`, the marketplace's `ref` in `.claude/settings.json`, to be `latest` ([Install](../install.md#following-the-releases)), the version of each research-kit plugin Claude Code installed for the project and the `formal` plugin's own version, held to the kit's latest release, which the probe asks GitHub for, as [The research setup](../research/research-init.md#the-pins-and-the-upgrade-steps) says; where one is off, the proposal `pins` names the releases from the oldest pin up to the latest whose **Upgrading** paragraphs to read and the steps that move every pin to it.
   It asks with one retry after a timeout; where the latest release cannot be read, offline or refused, the item says so and compares the pins among themselves, against the newest of them; a pin file with uncommitted changes is named, since a clone reads its committed pin.
   The item `flow.toml` appears where the research setup is absent, as information and never a refusal; the marker `[kit] release` is the research setup's, read by its own probe, and the two plugins are kept at one version by the pins.
   A lakefile under a workspace's directory, or one it requires by path, is a package of that workspace and never a workspace of its own: the generator goes into the workspace once and runs there for every package.
2. Plans in one message and asks once: which workspace to bind where the probe found several, which proposals to install, and the slots of the instructions the probe cannot fill (the commands that re-verify a module, the build time, where the audit modules live).
3. Installs what was chosen and probes again.
4. Writes `formal.toml` where it is absent, `[packages]` and the package order filled from the lakefiles, the instructions file, the manifests and the handoff's record bindings taken from the workspace, `flow.toml` and `library.toml` only where they exist and say them (left empty otherwise, and proposed for filling on a later run when the files have come), and binds `[documents]`, `[anchors]` and `[register]` from the project's own gates where it has them.
5. Places the generator in the workspace where it is absent, never into a package inside it, and leaves the manifests to the prover's first run after a genuine build.
6. Writes the instructions file from the template where the file `formal.toml` names is absent, and where it exists re-reads it against the template, adding what it lacks on your word; the paragraphs for the project's own instructions file are compared with what `formal init --print-instructions` prints for `formal.toml` as it stands, which writes nothing.
7. Adds the hooks to the kit's block; the flow, finding `formal.toml` at the root, asks `formal resolve` for its formal evidence, with nothing to bind in `flow.toml`.
8. Runs `formal check`, and `flow check` where the research plugin is set up, and reports what was written, installed and declined, with the first handoff as the next step; a manifest not yet generated is named as the prover's first move with its generate command, and leaves the flow's formal items unchecked.
   Where the plugin was installed in the same session, the report says the `formal:prover` agent type appears after a restart, since an agent type is loaded when a session starts.

A workspace never learns of the project's records through the setup: the instructions file carries the prover session's rules and nothing of the records or the documents beyond the bans `formal.toml` names.

## `formal.toml`

`formal init --workspace lean` writes the bindings file at the project root, with the bindings filled in and the optional ones commented; it is the schema, with every binding explained where it stands, and the kit's tests hold this page to what `init` writes.
The file below is written for a workspace `lean/` with no lakefile yet, in a project whose `flow.toml` and `library.toml` are as their own `init` writes them with the log `WORKLOG.md`.
Where the workspace has its lakefiles, `init` fills `[packages]` with every root of the workspace and of each package under it or required by path, one manifest and one command per package, and the package order from the requirements.
It takes what the project already says rather than a default: the instructions file the workspace has (`AGENTS.md`, else `CLAUDE.md`), the manifests, `scripts/decls.txt` for one package and `scripts/<package>-decls.txt` for several, with the generate commands writing them, and `[handoff]`'s `records`, `id_prefixes` and `meta_names` from `flow.toml`'s `[paths]` and `[prefixes]` and `key_patterns` from `library.toml`'s cite prefix, each only where that file exists and binds it, and empty otherwise.

```toml
# formal.toml — the prover side's bindings for THIS project.  Every path is relative to this
# file's directory.  The `formal` plugin's skills read it; the project's own instructions
# name the documents' gates and the rest.

[workspace]
dir = "lean"                 # the prover workspace: the Lake package (or packages) the prover session works in
instructions = "lean/AGENTS.md"   # the prover session's standing rules, read first by the agent whatever its runtime; a template is the handoff skill's references/workspace-instructions.md
# The package directories (relative to the workspace) from the lowest, the workspace's own last: no
# module of a package imports a module of a package after it.  Empty: the direction is not checked.
package_order = []
# Each root's `<Root>.lean` imports every module under `<Root>/`, the umbrella `formal check` reads.
umbrellas = true

[manifest]
# The declaration manifests, one per package, in the row grammar `formal --help` prints; this
# is the one place they are bound.  The research flow resolves declaration evidence by asking
# `formal resolve --protocol`, never by reading them.  Regenerated by the prover session after
# the last declaration change, with the commands below run in the workspace.
files = ["scripts/decls.txt"]
generate = "lake env lean --run DeclManifest.lean --roots <Root> --out ../scripts/decls.txt"

[packages]
# library root = the package directory it sits in, relative to the workspace: `<Root>.lean`
# and `<Root>/` are there.  One line per root.
# Lib = "."

[documents]
# The documents whose cited declaration names (backticked) are read at a landing and by
# `formal cite`, as globs from the project root.
scan = ["papers/*.md"]
# What `formal cite` accepts beside the manifests: names of an upstream library shaped like a
# declaration, the documents' notation shaped like a name, declarations retired on purpose (which
# must be absent from the manifests), named targets not yet in the tree, and namespaces shared
# with an upstream library (a qualified name under one is not checked).
upstream = []
notation = []
retired = []
open_targets = []
ambiguous_namespaces = []
# A regular expression for a link to the API docs, its first group the module's path with `/`
# for `.` (as '/docs/([\w/]+)\.html', a literal string); empty: links are not read.
docs_url = ""

[anchors]
# `formal anchors`: a citation key = the document it names, as `Key = "papers/x.md"`; a
# `[Key] §N`, `[Key] Theorem N.M` or `[Key] Appendix A` in the files below must resolve there.
scan = ["lean/**/*.lean"]
# Key = "papers/x.md"

[register]
# `formal register`: what ships (tracked files under these paths, minus `exclude`) carries none
# of the pattern classes below, matched after the `sanctioned` expressions are cut from a line,
# and names no file its file classes do not allow.
ship = ["lean"]
exclude = ["lean/AGENTS.md"]
sanctioned = []
# One table per class; `case = "sensitive"` for a tag, `scope` narrowing it to a subtree (a
# package that names nothing above it), `strip = false` to match before the sanctioned cut.
# [[register.class]]
# name = "internal vocabulary"
# patterns = ['\bworklog\b', '\bhandoff\b']   # literal strings: a backslash is the regex's
# A file class: every `X.lean` its `scope` names is a module (a tracked `.lean` file) of its
# `packages`, directories as in package_order (omitted: each file's own package and those before
# it), or a file of another project an `allow` expression matches as the mention is written
# ('^Average\.lean$' allows a bare `Average.lean`, not `ALT/Ergodic/Average.lean`).
# [[register.files]]
# name = "the lower package names only its own files"
# scope = ["lean/lower/**/*.lean"]
# packages = ["lower"]
# allow = ['^Mathlib/', '^Average\.lean$']

[handoff]
# The project's own directories (its documents, its scripts) a handoff may name: a path into one
# arrives `../`-prefixed, since the prover session runs from the workspace.
root_dirs = ["papers", "docs"]
# Phrases a handoff never carries (material the prover session must not learn of).
banned = []
# What names a record as a source, so the prompt must carry the docstring-register warning, since
# a docstring renders into the public artifact: the records' path prefixes, the id prefixes, the
# file names of the log and the registry, and regular expressions for reference keys; `init` takes
# them from flow.toml's [paths] and [prefixes] and library.toml's cite prefix where those exist, and
# leaves them empty where the project has neither (the formal plugin works without the research setup).
records = ["records", "WORKLOG-archive"]
id_prefixes = ["idea", "question", "task", "finding"]
meta_names = ["WORKLOG.md"]
key_patterns = ['lib:[a-z0-9][a-z0-9-]*']
```

`[register]` binds two kinds of class.
A pattern class (`[[register.class]]`) is a set of regular expressions that no line of a shipped file in its `scope` may match.
A file class (`[[register.files]]`) holds a package to the files a public reader can follow: every file name with the `.lean` extension that a shipped file of its `scope` mentions, bare (`Foo.lean`) or with a path (`Lib/Foo.lean`), is a module of one of its `packages` or matches one of its `allow` expressions.
A module of a package is a tracked `.lean` file under its directory and not under a package directory inside it, the build's `.lake` left out; a bare name is matched by the file name, a name with a path as the end of the module's path from the project root, a leading `./` or `../` dropped.
`packages` lists package directories relative to the workspace, as `package_order` does, and an entry that is no directory of `package_order` or `[packages]` is refused when `formal.toml` is read; omitted, each file's own package and every package before it in `package_order` count.
`allow` takes regular expressions for the files of other projects (an upstream library, a vendored port named as attribution), each tried against the mention as written and nothing else: `^Average\.lean$` allows a bare `Average.lean` and not `ALT/Ergodic/Average.lean`, so a path-qualified mention of another project's file needs an expression of its own, as `^Mathlib/`.
Either kind of class whose scope reaches no shipped file fails as rot, and so does a file class naming a package that holds no tracked `.lean` file.

## Words

- **formal-init** — the skill that sets the prover side up: it probes, proposes, re-checks what exists and adds what is missing, rewriting nothing without your word, and reports; `/formal:formal-init`, after the `research` plugin's setup.
- **probe** — the report `formal probe` prints: the workspaces with their roots and toolchains, the tools, the pins and what the setup is missing; it writes and installs nothing.
