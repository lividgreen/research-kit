# The landing

The prover session left its work uncommitted and handed back a report; the report is a claim about the tree, and the landing reads the tree: the declaration manifest's diff, a cold read-back of every landed statement, the binders and the guards.
Then the document's rows are written from the landed proof, the summary sites swept, the records closed and the commit made with named paths.
The tool is `scripts/formal.py` of the [`land`](../../plugins/formal/skills/land/SKILL.md) skill (`/formal:land` in Claude Code), the one CLI of the `formal` plugin: the handback diff, the read-back packet, the check, the three gates over the documents and what ships, the hypotheses ratchet and the witnesses report, beside `formal probe`, `formal init` and `formal handoffcheck`, which [The formal setup](formal-init.md) and [The handoff](handoff.md) use.
This page is the tool — its commands, the generator and the manifest it reads, its checks and its words — and the skill is the procedure of a landing.

## What it does

1. `formal handback` first, and the whole diff is read, not the names the report lists: everything the report names must be there, and everything the diff shows that the report omits is the surplus that makes a document boundary stale; each absent commissioned declaration is named in the log entry.
   It reads no proof: a `sorry`, an `admit`, a `native_decide` or a new `axiom` is the build's warnings and the project's `#print axioms` guards to catch.
2. A read-back before anything is read at the binders: `formal readback` builds the packet, one fresh subagent given the packet and nothing else writes out what each declaration literally asserts, and that prose is compared to the document's statement quantifier by quantifier; a mismatch changes the row or sends the statement back, never reads the document into the Lean.
3. Every commissioned declaration is opened at its binders in the source, and every binder is tiered VERBATIM, ADAPTER, IMPLIED or UNANCHORED against the document's statement; guards commissioned together are read one by one.
4. `formal check`, then the three gates over what the landing touched, and the project's own figure check where it states tree-derived figures, the new total written and never a delta.
5. The result is registered by the project's rule, else the `method` skill's register test, and the rows and the boundary paragraph are written from the landed proof, each ADAPTER binder named as such and each UNANCHORED one with its reason.
6. The summary sites are swept — the status label, the abstract, the contributions, the settled-and-open lists, an earlier row's boundary, every negative-coverage sentence about the result's kind — found by the claims' own words.
7. The flow closes the prover's task with `flow make`, then each finding is minted from the landed proof with `flow finding … --from TASK`, the declaration among its evidence as `formal:Path.lean#decl`, the one that settles the question with `--answers Q`; a failed handoff is `flow abort`, its refuting finding minted after it, tagged `refuted`; and the commit names its paths.

## The commands

| Command | What it does |
| --- | --- |
| `formal handback [--base REV] [--handoff DRAFT]` | the manifest diff against HEAD: the new public and private declarations, the removals, the visibility flips, the field changes and the per-module counts; the instantiations of an existing generic; the joint-satisfiability witnesses owed; the guards added and removed in the workspace diff with the live total after the change; every document site citing a declaration of a touched module; and the commission, every name of the handoff's `Commissioned:` line sorted into four classes, landed, private (in the tree, not citable), already at base and absent; exit 1 on a document citing a name now private or removed |
| `formal readback NAME… [-o FILE] [--depth N]` | the packet a cold reader writes each landed statement out from: the statement with its modifiers and scope lines, every project-local definition it names to depth two, docstrings and comments stripped |
| `formal check` | the manifests parse and are the tree's, each read its named conditions under the project's own roots, the umbrellas import their modules, the packages import in order, the bindings resolve |
| `formal cite`, `formal anchors`, `formal register` | the three gates over the documents and what ships, each a pre-commit hook |
| `formal hypotheses [--base REV \| --baseline FILE [--update]]` | no public theorem shipped at the base gained a named condition |
| `formal witnesses [--base REV]` | the public theorems with two or more named conditions and no `_nonvacuous` witness, by module; a report |

Every command reads `formal.toml` at the project root (`--root DIR` for another, before the command or after it); `formal --help` prints every command and the manifest's row grammar, and needs no bindings file.
The [skill](../../plugins/formal/skills/land/SKILL.md) names every flag, and the kit's tests hold it to the script.

## The manifest

`scripts/DeclManifest.lean` beside the CLI generates a Lean package's declaration manifest after a genuine build: from the workspace, `lake env lean --run DeclManifest.lean --roots Root1,Root2 --out ../scripts/decls.txt`, with `--own` naming the roots whose Prop-valued definitions count as named conditions, by default every root built in the workspace's own packages; the roots taken are printed and written as the manifest's second line, `# own roots: A,B`, which `formal check` holds against `[packages]`, so a generate command passes `--own` only where the default is not the project's.
The setup copies the file into the workspace once and binds one command per package in `formal.toml`'s `[manifest] generate`; the prover session regenerates the manifests after the last declaration change, and the [flow](../research/flow.md) resolves declaration evidence against the same files.
A manifest is a text file in a row grammar any prover's declaration list may follow, six row kinds:

```text
module <module> <count>                a module and how many declarations it counts
<module> <name>                        a public declaration
private <module> <name>                a private one (counted, not citable from outside)
field <module> <name>                  a structure projection (citable, not counted)
hypothesis <module> <theorem> <cond>   a public theorem's named condition
instance <module> <theorem> <class>    a class one of its instance binders carries
```

The generator walks the compiled environment, so it needs the build current, and its counting rule is stated in its own header; another prover writes the same six row kinds with its own tool.

## The checks

The `formal` plugin's checks report in words rather than codes.
Each exits 0 when clean, 1 when it found problems, each printed with its place, and 2 when it could not run, so a hook or a CI job never reads "did not run" as "clean"; each ends with a coverage line saying what it looked at.

### `formal check`

`formal check` reads `formal.toml` and reports:

- a workspace that is not a directory, or the prover session's instructions file missing;
- a package root with neither `<Root>.lean` nor `<Root>/` under its package directory;
- a declaration manifest missing, with the command that regenerates it, or a row outside the grammar `formal --help` prints;
- with `[packages]` bound: the manifests' modules not the tree's (the files on disk under each root, those git ignores left out), the missing and the extra named with the command that regenerates them, and a module counted under a root `[packages]` does not bind;
- with `[packages]` bound, each manifest's `# own roots:` line, the roots whose Prop-valued definitions the generator read as named conditions, against `[packages]`: a manifest without the line (an older generator's, to copy over and regenerate), a root `[packages]` does not bind (a library required by path from outside the project), and a bound root the package's modules import, directly or through another module, left out (a package required by git, under `.lake/packages/`, or an explicit `--own` that misses it);
- a root's umbrella `<Root>.lean` not importing a module under `<Root>/`, or importing one not in the tree (`umbrellas = false` turns this off; a module the package's lakefile declares as a library root of its own stands outside the umbrella);
- a module importing a module of a later package of `[workspace] package_order`.

Its coverage line names the manifests with their row counts by kind, the packages bound and the documents scanned, and says the prover tree itself is not built.

### `formal cite`, `formal anchors`, `formal register`

Three gates over the documents and what ships, each bound in `formal.toml`, each exiting 1 with every site named and 2 when it could not run:

- `formal cite`: no document matching `[documents] scan`; a declaration name a document cites that resolves nowhere, resolves only to private declarations, or is qualified under a namespace of the manifests and names no declaration; a cited `X.lean` that is not a module; an API-docs link to a module not in the tree; a name bound as retired that the manifests still hold.
  Its coverage lines count the resolutions by kind and the allowlisted names by list;
- `formal anchors`: no file matching `[anchors] scan`; a `[Key] §N`, `[Key] Theorem N.M` or `[Key] Appendix X` naming no heading, statement of that kind or appendix of the key's document, or a statement riding a section it is not in; the bare keys and the § lines with no key are counted, not checked;
- `formal register`: a line of a shipped file matching a bound pattern class after the sanctioned expressions are cut; a `.lean` file name a shipped file in a file class's scope mentions that is no module of the class's packages and that no `allow` expression matches as written (a bare-name expression lets no path-qualified mention through); a class reaching no file, a file class naming a package with no tracked `.lean` file, or an empty scope.
  Its coverage line counts the files each class reads, and the modules of each package where a file class is bound.

`formal hypotheses` exits 1 where a public theorem shipped at the base, or listed in a baseline, gained a named condition, and says INERT, exiting 0, where the manifests carry no `hypothesis` row; `formal witnesses` is a report and exits 0.

## Words

- **guard, guard family** — a checked expectation beside a theorem (`#guard_msgs` over `#print axioms` in Lean) that a declaration's axioms, or a named instance's value, are as stated; a family is the set of instances that pin a theorem's hypotheses as load-bearing.
- **instantiation of an existing generic** — a landed declaration that is an existing generic theorem at one instance (`mul_comm_int` under `mul_comm`), the shape a report compresses into a clause.
- **drift, drift list** — the document sites a landing makes false or stale — figures, boundaries, citations — reported verbatim by the prover session and swept by the root session.
- **read-back packet** — a landed statement with the project-local definitions it names, docstrings and comments stripped, for a reader who has not seen the document.
- **binder tiers** — VERBATIM, ADAPTER, IMPLIED, UNANCHORED: what each binder of a landed declaration is against the document's statement.
- **umbrella** — a library root's file `<Root>.lean`, importing every module under `<Root>/`; `formal check` reads it.
- **named condition** — a binder of a public theorem whose type is one of the workspace's own Prop-valued definitions, applied in full; the manifest's `hypothesis` rows, which `formal hypotheses` ratchets.
- **internal register** — the words of the project's own process (record ids, stage labels, private paths), which a docstring never carries since it renders into the public API docs; `formal register` reads what ships for them.
