# The prover workspace's standing instructions — a template

`formal.toml`'s `instructions` names the file the prover session reads first; this is the shape one project's file took, section by section, with the words a project replaces in angle brackets.
A handoff restates none of it, which is what keeps a prompt short and the rules in one maintained place.

## Scope — what this session owns

You own the library development and nothing else.
Write: the library modules, the package files (`lakefile.toml`, `lake-manifest.json`), the manifest generator and the generated declaration manifests `formal.toml` names.
Read freely: anything in the project — reading the documents is MANDATORY for statement-first work, since a statement is designed against the document's actual text, never a paraphrase; running the root's read-only checks is expected, since you must detect drift.
Never write: the documents, the records, the project's README and packaging — unless a handoff names a file explicitly.
Report drift; do not fix it: when a check names document sites, quote the list in your report; editing them is the root session's job.
Never commit: the root session sweeps the documents and commits the Lean with them as one change set.

## Verification — the gate

The build is the ONLY pass/fail gate; the language server's feedback is for iteration and has produced false passes.
A plain build replays cached artifacts and skips the guards' re-execution: to genuinely re-verify, delete the touched modules' artifacts first (<the project's exact commands>).
The final build shows ALL diagnostics, never a success-only grep: a filter that only looks for `error` reads a warning-clean and a warning-dirty build identically.
Bar: no `sorry`/`admit`/`native_decide`; the standard axioms only; statement-first (statement → fidelity review against the document's text → prove → build → guard).
Refute first: the opening move on any commissioned statement is a bounded refutation attempt, COMPUTED at the parameters the handoff's `Refute first:` line names, in a scratch file, within a fixed budget; reported either way; a refutation is a guard-family candidate, restated as a checked guard, and no proof work is done on the statement.
A joint-satisfiability witness is commissioned beside any theorem with two or more hypotheses (`<theorem>_nonvacuous`); if none can be built, say so in the report — a finding about the theorem, not a step to skip.
A predecessor's statement is fixed by the sink: proving a predecessor of a landed sink theorem, its statement is the sink's hypothesis VERBATIM; if the proof needs the statement changed, report the change and stop.

## Workspace facts

<the toolchain and its pin; how the dependency cache is fetched; the build time; where the audit modules live>

## New module checklist

<the module docstring's form; the import discipline; the guard the module carries; the manifest regeneration; the public README's module table, which is the root's to edit>

A docstring renders verbatim into the public API docs, so it carries no internal register: no record id, no stage label, no name of a private document; the root's `formal register` reads what ships.
A public package follows its community's standard as the libraries downstream of it adopt it: the standard linter set, a warning fixed and never suppressed at file level, warnings as errors in the build that gates a release, the naming conventions, a module docstring in every file.

## After ANY declaration change

Regenerate the manifests with the command `formal.toml` names, run the root's read-only checks from the project root, and quote their drift lists in the report.

## Known traps

<each one in two lines: the symptom, the rule it earned; the incidents stay in the project's log>

Where the workspace holds several packages, one required by another by path: Lake, or a language server, started inside a nested package resolves that package alone and can fetch its path dependencies into a private `.lake/packages` there, which is deleted, never used.
Lake runs from the workspace, and the manifest generator lives there, once.

## Bumping a dependency or the toolchain

1. Save the sorted warning lines of a clean build on the old pins.
2. Edit the nested packages' own manifests before the update, so their transitive pins follow the workspace's.
3. Run the update; a cache fetch that stalls after writing the manifest is killed and the build run.
4. Fix the renamed names in waves, one search per renamed family.
5. Clear the deprecations that are renames only; report the ones that change a statement's shape.
6. After a clean rebuild, diff the warning lists: one instance and a count per new class.
7. Run the whole-library axiom audit and report its summary line.
8. The handoff for a bump carries `Refute first: not applicable — bump`.

## When a result flips to machine-checked

Say so; do not edit the document.
State precisely what became machine-checked and what did not: the declarations, the row they belong to, every hypothesis still imported or assumed.
The root session writes the prose from that.

## Report back — end of a handoff

What landed (declarations and files) · the guard count if it moved · the manifests regenerated, yes or no · build evidence (exit code, job count, which guard modules re-elaborated) · anything statement-first REJECTED and why · the refute-first attempt (parameters, outcome) · the `_nonvacuous` witness landed, or why none could be · for a predecessor of a sink-first bundle, that its statement is the sink's hypothesis verbatim · the verbatim drift list of the root's checks · any boundary that moved · confirmation that nothing outside the workspace and the manifests was written.
On a `session=continue` handoff, your own earlier record of what was tried and rejected is authoritative — do not re-derive it.
