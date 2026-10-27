#!/usr/bin/env python3
"""The kit's tests: each script's selftest, the duplicated helpers held identical, the manifests
held in step, every skill's frontmatter in the standard's form and every CLI subcommand named in
its skill, Getting started's shell blocks run in order, the documentation is true of the tools and its links resolve, and the plugin
validator where the Claude CLI is on PATH.  Exit 0 when everything passes."""

import ast
import datetime
import json
import re
import shutil
import subprocess
import os
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = {n: ROOT / "plugins" / n for n in ("research", "formal")}
SKILLS = PLUGINS["research"] / "skills"
SKILL_DIRS = [d for pl in PLUGINS.values() if (pl / "skills").is_dir() for d in sorted(p for p in (pl / "skills").iterdir() if p.is_dir())]
SCRIPTS = {"flow": SKILLS / "flow/scripts/flow.py", "library": SKILLS / "library/scripts/library.py",
           "dashboard": SKILLS / "dashboard/scripts/dashboard.py", "formal": PLUGINS["formal"] / "skills/land/scripts/formal.py",
           "setup": SKILLS / "research-init/scripts/setup.py"}
SHARED = ("_SENT", "FENCE_RUN", "fence_after", "_builtin_reflow", "project_lock")  # the helpers duplicated into each single-file script
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok ' if cond else 'BAD'} {name}" + (f": {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def source_of(path, names):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        key = node.name if isinstance(node, (ast.FunctionDef, ast.ClassDef)) else \
            node.targets[0].id if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) else None
        if key in names:
            out[key] = ast.get_source_segment(path.read_text(encoding="utf-8"), node)
    return out


def main():
    print("selftests")
    for name, path in SCRIPTS.items():
        r = subprocess.run([sys.executable, str(path), "--selftest"], capture_output=True, text=True, timeout=600)
        check(f"{name} --selftest", r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")

    print("duplicated helpers")
    a, b = source_of(SCRIPTS["flow"], SHARED), source_of(SCRIPTS["library"], SHARED)
    for n in SHARED:
        check(f"{n} identical in flow.py and library.py", n in a and n in b and a[n] == b[n])

    print("manifests")
    market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    codex = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    cursor = json.loads((ROOT / ".cursor-plugin/marketplace.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    check("both marketplaces list the two plugins by name, each at its own directory",
          [e["name"] for e in market["plugins"]] == list(PLUGINS) == [e["name"] for e in codex["plugins"]]
          and all(e["source"] == f"./plugins/{e['name']}" for e in market["plugins"])
          and all(e["source"]["path"] == f"./plugins/{e['name']}" for e in codex["plugins"]))
    check("the marketplace entries carry no version (Claude Code would read plugin.json's over it without a word)",
          all("version" not in e for e in market["plugins"]) and "version" not in market.get("metadata", {}))
    check("Cursor's marketplace is Claude Code's: the same name, plugins, sources and descriptions, and no version",
          {k: cursor.get(k) for k in ("name", "owner")} == {k: market.get(k) for k in ("name", "owner")}
          and [(e["name"], e["source"], e["description"]) for e in cursor["plugins"]]
          == [(e["name"], e["source"], e["description"]) for e in market["plugins"]]
          and all("version" not in e for e in cursor["plugins"]) and "version" not in cursor.get("metadata", {}))
    manifests = {}
    for name, pl in PLUGINS.items():
        claude = json.loads((pl / ".claude-plugin/plugin.json").read_text())
        agent = json.loads((pl / "plugin.json").read_text())
        manifests[name] = (claude, agent)
        entry = next(e for e in market["plugins"] if e["name"] == name)
        check(f"{name}: name and description agree across its two manifests and its marketplace entry",
              claude.get("name") == agent.get("name") == name and claude.get("description") == agent.get("description") == entry.get("description"))
        check(f"{name}: version agrees across plugin.json and the Claude manifest", claude.get("version") == agent.get("version") and bool(claude.get("version")))
        check(f"{name}: the marketplace tags are among the keywords, and the keywords agree",
              set(entry.get("tags", [])) <= set(claude.get("keywords", [])) and claude.get("keywords") == agent.get("keywords"))
        check(f"{name}: the Agent Plugins manifest names its schema and no unknown field",
              agent.get("$schema") == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
              and set(agent) <= {"$schema", "name", "version", "description", "author", "homepage", "repository", "license", "keywords", "extensions"})
        check(f"{name}: the Codex extension carries an interface", "interface" in agent.get("extensions", {}).get("com.openai", {}))
        check(f"{name}: licensed Apache-2.0 in both manifests", claude.get("license") == agent.get("license") == "Apache-2.0")
    rk, fm = manifests["research"][0], manifests["formal"][0]
    check("pyproject names the package after the repository", project.get("name") == "research-kit")
    check("pyproject's version is the two plugins'", project.get("version") == rk.get("version") == fm.get("version"))
    check("pyproject's description names each console script it carries",
          all(f"{n} (" in project.get("description", "") for n in project["scripts"]))
    check("pyproject's keywords hold both plugins'", set(project.get("keywords", [])) >= set(rk.get("keywords", [])) | set(fm.get("keywords", [])))
    hooks = (ROOT / ".pre-commit-hooks.yaml").read_text()
    check("the pre-commit hooks call the console scripts pyproject declares",
          all(f"entry: {n} check" in hooks for n in ("flow", "library", "formal")) and set(project["scripts"]) == {"flow", "library", "dashboard", "formal"})
    forced = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    check("every console script's file is carried into the package (the setup probe is the skill's alone)",
          {ROOT / k for k in forced} == {SCRIPTS[n] for n in project["scripts"]})

    print("changelog")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    heads = re.findall(r"^## (.*)$", changelog, re.M)
    bodies = re.split(r"^## .*$", changelog, flags=re.M)[1:]
    released = [(re.fullmatch(r"v(\d+)\.(\d+)\.(\d+) — (\d{4}-\d{2}-\d{2})", h), b) for h, b in zip(heads, bodies) if h != "Unreleased"]
    check("every changelog heading is `## Unreleased` or `## vX.Y.Z — YYYY-MM-DD` (release.yml finds a release's notes by it)",
          all(m for m, _ in released), str([h for h in heads if h != "Unreleased" and not re.fullmatch(r"v\d+\.\d+\.\d+ — \d{4}-\d{2}-\d{2}", h)]))
    check("`## Unreleased` is at most one heading, above every release", "Unreleased" not in heads[1:])
    if all(m for m, _ in released):
        versions = [tuple(map(int, m.groups()[:3])) for m, _ in released]
        dates = [m.group(4) for m, _ in released]

        def is_date(s):
            try:
                return bool(datetime.date.fromisoformat(s))
            except ValueError:
                return False
        check("the releases run newest first, each with a real date and notes",
              versions == sorted(set(versions), reverse=True) and dates == sorted(dates, reverse=True)
              and all(map(is_date, dates)) and all(b.strip() for _, b in released))
        check("the last release in the changelog is the version the version fields carry (bumped at the release, by tools/release.py)",
              not released or ".".join(released[0][0].groups()[:3]) == project.get("version"))

    print("skills")
    for d in SKILL_DIRS:
        text = (d / "SKILL.md").read_text(encoding="utf-8") if (d / "SKILL.md").is_file() else ""
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        fm = {}
        if m:
            for line in m.group(1).split("\n"):
                km = re.match(r"^([a-z-]+):\s*(.*)$", line)
                if km:
                    fm[km.group(1)] = km.group(2)
        check(f"{d.name}: SKILL.md with name and description in the frontmatter", fm.get("name") == d.name and len(fm.get("description", "")) > 40)
        check(f"{d.name}: licensed Apache-2.0 in the frontmatter", fm.get("license") == "Apache-2.0")
        check(f"{d.name}: no unquoted colon-space inside a frontmatter value (the skills CLI reads it as a nested mapping)",
              all(": " not in v or v.startswith(("\"", "'")) for v in fm.values()), str([k for k, v in fm.items() if ": " in v and not v.startswith(("\"", "'"))]))
        check(f"{d.name}: only the standard's frontmatter keys",
              set(fm) <= {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}, str(set(fm)))
        for script in re.findall(r"`scripts/([\w.-]+\.py)`", text):
            # a skill may name another skill's script ("`scripts/flow.py` of the `flow` skill")
            check(f"{d.name}: names scripts/{script}, which exists in this or a sibling skill",
                  (d / "scripts" / script).is_file() or any((s_ / "scripts" / script).is_file() for s_ in SKILL_DIRS))
        for ref in sorted(set(re.findall(r"`references/([\w.-]+\.md)`", text))):
            # a skill may name another skill's reference ("`references/x.md` of the `handoff` skill")
            check(f"{d.name}: names references/{ref}, which exists in this or a sibling skill",
                  (d / "references" / ref).is_file() or any((s_ / "references" / ref).is_file() for s_ in SKILL_DIRS))
        ct = d / "component.toml"
        if ct.is_file():
            c = tomllib.loads(ct.read_text())
            check(f"{d.name}: component.toml names a script that exists and a bindings file",
                  (d / c["command"][-1]).is_file() and bool(c.get("bindings")))
    check("no bin/ directory (claude.ai and Cowork refuse a plugin that has one)", not (ROOT / "bin").exists())
    check("the formal plugin has its agent", (PLUGINS["formal"] / "agents/prover.md").is_file() and "name: prover" in (PLUGINS["formal"] / "agents/prover.md").read_text())
    # agents/ is the portable copy, on the session's own model (agents are outside the Agent Plugins 1.0 format);
    # Claude Code's manifest names its own copy (model: sonnet)
    portable, claude = ((PLUGINS["formal"] / d / "prover.md").read_text().splitlines() for d in ("agents", "claude-agents"))
    check("the prover's Claude Code copy is the portable one but for its model line",
          [ln for ln in portable if not ln.startswith("model:")] == [ln for ln in claude if not ln.startswith("model:")]
          and "model: inherit" in portable and "model: sonnet" in claude
          and json.loads((PLUGINS["formal"] / ".claude-plugin/plugin.json").read_text()).get("agents") == ["./claude-agents/prover.md"])
    # an Agent Plugins client reads agents only from its own extension directory of the plugin
    for copy in ("com.github.copilot/agents/prover.agent.md", "dev.openhands/agents/prover.md"):
        check(f"the prover's copy in {copy} is the portable one",
              (PLUGINS["formal"] / copy).is_file() and (PLUGINS["formal"] / copy).read_text().splitlines() == portable)
    # Antigravity reads it through the plugin's agents.json, and gives an agent no tools it does not list
    agy = (PLUGINS["formal"] / "com.google.antigravity/agents/prover.md").read_text().splitlines()
    agy_tools = ["view_file", "write_to_file", "replace_file_content", "grep_search", "find_by_name", "list_dir", "run_command"]
    check("the prover's Antigravity copy is the portable one with its tool list, and agents.json points at it",
          [ln for ln in agy if ln != "tools:" and ln.strip() not in {f"- {t}" for t in agy_tools}] == portable
          and [ln.strip()[2:] for ln in agy if ln.startswith("  - ")] == agy_tools
          and json.loads((PLUGINS["formal"] / "agents.json").read_text()) == {"entries": [{"path": "com.google.antigravity/agents"}]})
    check("the licence is Apache-2.0 in LICENSE, NOTICE, pyproject and CITATION.cff",
          (ROOT / "LICENSE").read_text().lstrip().startswith("Apache License") and "Apache" in (ROOT / "NOTICE").read_text()
          and project.get("license") == "Apache-2.0" and "license: Apache-2.0" in (ROOT / "CITATION.cff").read_text())
    requires = {d.name: re.search(r"^  requires: (.+)$", (d / "SKILL.md").read_text(encoding="utf-8"), re.M) for d in SKILL_DIRS}
    names = {d.name for d in SKILL_DIRS}
    check("every skill's requires names a skill of the repository", all(m.group(1).strip() in names for m in requires.values() if m))
    check("CITATION.cff and the tests workflow exist",
          (ROOT / "CITATION.cff").read_text().startswith("cff-version:") and (ROOT / ".github/workflows/tests.yml").is_file())

    print("subcommands named in the skills")
    FS = PLUGINS["formal"] / "skills"
    skill_text = {"flow": (SKILLS / "flow/SKILL.md").read_text(), "library": (SKILLS / "library/SKILL.md").read_text(),
                  "formal": (FS / "handoff/SKILL.md").read_text() + (FS / "land/SKILL.md").read_text() + (FS / "formal-init/SKILL.md").read_text(),
                  "setup": (SKILLS / "research-init/SKILL.md").read_text()}
    for name in ("flow", "library", "formal", "setup"):
        r = subprocess.run([sys.executable, str(SCRIPTS[name]), "--help"], capture_output=True, text=True, cwd=tempfile.gettempdir())
        m = re.search(r"\{([a-z,-]+)\}", r.stdout)
        check(f"{name} --help runs with no bindings file and lists its subcommands", r.returncode == 0 and bool(m))
        for sub in (m.group(1).split(",") if m else []):
            check(f"{name} {sub} is named in the skill", re.search(r"`(?:%s|scripts/%s\.py)(?: --json)? %s\b" % (name, name, re.escape(sub)), skill_text[name]) is not None)
            h = subprocess.run([sys.executable, str(SCRIPTS[name]), sub, "--help"], capture_output=True, text=True, cwd=tempfile.gettempdir())
            flags = sorted(set(re.findall(r"(--[a-z][a-z-]*)", h.stdout)) - {"--help"})
            missing = [f for f in flags if f"`{f}" not in skill_text[name] and f"{f} " not in skill_text[name] and f"{f}`" not in skill_text[name]]
            check(f"{name} {sub} --help runs outside a project and every flag it lists is named in the skill", h.returncode == 0 and not missing, ", ".join(missing))
    print("skill versions")
    for d in SKILL_DIRS:
        fm = (d / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
        plugin_version = json.loads((d.parent.parent / ".claude-plugin/plugin.json").read_text())["version"]
        m = re.search(r'^\s+version: "([^"]+)"', fm, re.M)
        check(f"{d.parent.parent.name}/{d.name}: metadata.version is the plugin's", bool(m) and m.group(1) == plugin_version)

    print("the shell blocks of docs/getting-started.md")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    blocks = [("getting-started", b) for b in re.findall(r"```sh\n(.*?)```", (ROOT / "docs/getting-started.md").read_text(encoding="utf-8"), re.S)]
    check("docs/getting-started.md has its shell blocks", bool(blocks))
    with tempfile.TemporaryDirectory() as tmp:
        bindir = Path(tmp) / "bin"
        bindir.mkdir()
        for name, path in SCRIPTS.items():
            shim = bindir / name
            shim.write_text(f"#!/bin/sh\nexec '{sys.executable}' '{path}' \"$@\"\n")
            shim.chmod(0o755)
        env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")
        for n, (where, block) in enumerate(blocks, 1):
            # the blocks go on from one another in one directory
            proj = Path(tmp) / where
            proj.mkdir(exist_ok=True)
            r = subprocess.run(["bash", "-e"], input=block, capture_output=True, text=True, cwd=proj, env=env, timeout=120)
            check(f"{where} block {n} runs after the ones before it", r.returncode == 0, (r.stdout + r.stderr).strip()[-300:])

    print("the README's How to use and the site's Try it agree")
    table = lambda text, heading: [l for l in text.split(heading, 1)[-1].split("\n## ", 1)[0].splitlines() if l.startswith("|")]
    shown = table(readme, "## How to use\n")
    check("the README's How to use table is the site home page's Try it table, row for row",
          len(shown) > 2 and shown == table((ROOT / "docs/index.md").read_text(encoding="utf-8"), "## Try it\n"))

    print("the project card www.livid.work copies at each release")
    card = (ROOT / "docs/project-card.md").read_text(encoding="utf-8")
    head = re.match(r"---\n(.*?)\n---\n(.*)", card, re.S)
    keys = dict(re.findall(r"^(\w+):[ \t]*(.*)$", head.group(1), re.M)) if head else {}
    summary = keys.get("summary", "").strip()
    check("docs/project-card.md opens with a front matter block", bool(head))
    check("the card's title is one line of 120 characters at most", 0 < len(keys.get("title", "").strip()) <= 120)
    check("the card's summary is one plain paragraph of 500 characters at most, quoted where it holds a colon and a space",
          0 < len(summary.strip("\"'")) <= 500 and (": " not in summary or summary[:1] in "\"'"))
    check("the card's tags are a list and its status is active, shipped or archived",
          re.fullmatch(r"\[[^\]]*\]", keys.get("tags", "[]").strip()) is not None and keys.get("status", "active").strip() in ("active", "shipped", "archived"))
    body = head.group(2) if head else ""
    first = re.search(r"^(#+) ", body, re.M)
    check("the card's body has no level-1 heading and starts at level 2",
          not re.search(r"^# ", body, re.M) and (first is None or first.group(1) == "##"))
    check("no link destination of the card holds a parenthesis", not re.search(r"\]\([^)\s]*\([^)]*\)", body))

    print("the documentation is true of the tools")
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "init"
        proj.mkdir()
        subprocess.run([sys.executable, str(SCRIPTS["flow"]), "init", "--log", "WORKLOG.md"], capture_output=True, text=True, cwd=proj, check=True)
        subprocess.run([sys.executable, str(SCRIPTS["library"]), "init", "--kept", "--scan", "records", "--scan", "WORKLOG.md"], capture_output=True, text=True, cwd=proj, check=True)
        subprocess.run([sys.executable, str(SCRIPTS["formal"]), "init", "--workspace", "lean"], capture_output=True, text=True, cwd=proj, check=True)
        bindings = (ROOT / "docs/bindings.md").read_text(encoding="utf-8")
        shown = re.findall(r"```toml\n(.*?)```", bindings, re.S)
        for i, name in enumerate(("flow.toml", "library.toml", "formal.toml")):
            check(f"docs/bindings.md shows {name} as init writes it", len(shown) == 3 and shown[i] == (proj / name).read_text(encoding="utf-8"))
        lite = Path(tmp) / "lite"
        lite.mkdir()
        for argv in (["init", "--log", "WORKLOG.md"], ["capture", "A might imply B", "--source", "a talk"],
                     ["frame", "idea-0001", "--summary", "Does A imply B?", "--kill", "a finite counterexample, or a proof"],
                     ["refine", "question-0001", "--task", "prove the lemma", "work", "--task", "design the route", "design"]):
            subprocess.run([sys.executable, str(SCRIPTS["flow"]), *argv], capture_output=True, text=True, cwd=lite, check=True)
        started = (ROOT / "docs/getting-started.md").read_text(encoding="utf-8")
        record = re.findall(r"```markdown\n(.*?)```", started, re.S)[0]
        task = next((lite / "records/tasks").glob("task-0001-*.md"))
        today = __import__("datetime").date.today().isoformat()
        check("docs/getting-started.md shows the task record as the tool writes it",
              task.name == "task-0001-prove-the-lemma.md" and task.read_text(encoding="utf-8").replace(today, "2026-10-23") == record)
        task.write_text(task.read_text(encoding="utf-8").replace("state: ready", "state: active"), encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPTS["flow"]), "check"], capture_output=True, text=True, cwd=lite)
        failed = re.findall(r"```text\n(.*?)```", started, re.S)[0]
        check("docs/getting-started.md shows the failed check as the tool reports it",
              r.returncode == 1 and r.stdout.splitlines()[:2] == failed.splitlines()[:2])
    checks = (ROOT / "docs/checks.md").read_text(encoding="utf-8")
    for name, script in (("flow", SCRIPTS["flow"]), ("library", SCRIPTS["library"])):
        codes = set(re.findall(r'"code": "([VL]\d+)"', script.read_text(encoding="utf-8"))) | set(re.findall(r'bad\("([VL]\d+)"', script.read_text(encoding="utf-8")))
        named = set(re.findall(r"^\| ([VL]\d+) \|", checks, re.M))
        check(f"docs/checks.md names every code {name} check can report", codes <= named, str(sorted(codes - named)))

    print("the documentation's links")
    for doc in [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "SECURITY.md", *sorted((ROOT / "docs").glob("*.md")), *sorted(ROOT.glob("plugins/*/README.md"))]:
        text = doc.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if re.match(r"^(https?:|mailto:|#)", target):
                continue
            path, _, anchor = target.partition("#")
            resolved = (doc.parent / path).resolve()
            ok = resolved.exists()
            if ok and anchor and resolved.suffix == ".md":
                slugs = {re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-") for h in re.findall(r"^#+ (.+)$", resolved.read_text(encoding="utf-8"), re.M)}
                ok = anchor in slugs
            check(f"{doc.relative_to(ROOT)} -> {target} resolves", ok)
    check("the README names no version where the tag is the pin", not re.search(r"@v\d|rev: v\d", readme + (ROOT / "docs/install.md").read_text()))

    print("the repository paths the documentation's prose names")
    for doc in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")), *sorted(ROOT.glob("plugins/*/README.md"))]:
        text = doc.read_text(encoding="utf-8")
        spans = re.findall(r"`([^`\n]+)`", text)  # a path inside any code span, `python3 plugins/…` included
        for token in sorted({m for s in spans for m in re.findall(r"(?<![\w/.-])((?:plugins|docs|tests|packaging|\.github)/[^\s`]+)", s)}):
            if re.search(r"[<>*{}]", token):
                continue
            check(f"{doc.relative_to(ROOT)} names `{token}`, which exists", (ROOT / token.rstrip(".,;:")).exists())

    print("markdownlint")
    if shutil.which("markdownlint"):
        files = [str(p.relative_to(ROOT)) for p in [ROOT / "README.md", ROOT / "CHANGELOG.md", ROOT / "CONTRIBUTING.md", ROOT / "SECURITY.md", *(ROOT / "docs").glob("*.md"), *ROOT.glob("plugins/**/*.md")]]
        r = subprocess.run(["markdownlint", "-c", ".markdownlint.jsonc", *files], capture_output=True, text=True, cwd=ROOT)
        check("markdownlint passes on the repository's Markdown with .markdownlint.jsonc", r.returncode == 0, (r.stdout + r.stderr).strip()[-300:])
    else:
        print("  -- markdownlint not on PATH; the Markdown lint did not run")

    print("plugin validator")
    if shutil.which("claude"):
        for target in [ROOT, *PLUGINS.values()]:
            r = subprocess.run(["claude", "plugin", "validate", "--strict", str(target)], capture_output=True, text=True, timeout=120)
            check(f"claude plugin validate --strict {target.relative_to(ROOT) if target != ROOT else 'the marketplace root'}", r.returncode == 0, (r.stdout + r.stderr).strip()[-400:])
    else:
        print("  -- claude not on PATH; the plugin validator did not run")
    print(f"tests: {'OK' if not failures else str(len(failures)) + ' FAILED: ' + '; '.join(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
