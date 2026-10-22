#!/usr/bin/env python3
"""setup — the probe behind the `research-init` skill: what the project and the machine have, and what
the kit's setup needs that is missing.

  setup probe [--root DIR] [--json]   the report the skill's procedure reads
  setup --selftest

The probe writes nothing and installs nothing; it reports, the agent proposes, the person
decides.  Standard library only.
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_MD = HERE.parent / "SKILL.md"
REQUIRED, RECOMMENDED, OPTIONAL = "required", "recommended", "optional"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".lake", "build", "dist"}
INSTRUCTION_FILES = ("CLAUDE.md", ".claude/CLAUDE.md", "AGENTS.md", ".github/copilot-instructions.md", "GEMINI.md")
LOG_NAMES = ("WORKLOG.md", "LOG.md", "worklog.md", "log.md")


def kit_version():
    """The version in this skill's SKILL.md frontmatter (the plugin's; the release tag is `v` + it)."""
    try:
        fm = SKILL_MD.read_text(encoding="utf-8").split("---")[1]
    except (OSError, IndexError):
        return None
    m = re.search(r'^\s+version: "([^"]+)"', fm, re.M)
    return m.group(1) if m else None


def layout():
    """How these skills are installed: a Claude Code plugin (skills/<name> under a plugin with its
    manifest), a flat agent directory (.agents/skills, .claude/skills), or a checkout."""
    skills = HERE.parent.parent
    plugin = skills.parent
    if (plugin / ".claude-plugin" / "plugin.json").is_file():
        return "plugin", str(plugin)
    if skills.name == "skills":
        return "skills directory", str(skills)
    return "copy", str(HERE.parent)


def fts5():
    try:
        con = sqlite3.connect(":memory:")
        con.execute("create virtual table t using fts5(x)")
        return True
    except sqlite3.Error:
        return False


def module(name):
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def python_version_line():
    return subprocess.run([sys.executable, "--version"], capture_output=True, text=True).stdout.strip() or sys.version.split()[0]


def environment():
    """The machine: the interpreter, the tools on PATH, the installers at hand."""
    items = []
    v = sys.version_info
    items.append({"item": "python", "need": REQUIRED, "ok": v >= (3, 11),
                  "detail": f"{sys.executable} is {v.major}.{v.minor}.{v.micro}" + ("" if v >= (3, 11) else "; 3.11 or later is needed")})
    items.append({"item": "git", "need": REQUIRED, "ok": shutil.which("git") is not None, "detail": shutil.which("git") or "not on PATH"})
    hook_runner = next((t for t in ("prek", "pre-commit") if shutil.which(t)), None)
    items.append({"item": "pre-commit runner", "need": REQUIRED, "ok": hook_runner is not None,
                  "detail": shutil.which(hook_runner) if hook_runner else "neither prek nor pre-commit is on PATH; the checks run as hooks through one of them"})
    items.append({"item": "markdownlint", "need": RECOMMENDED, "ok": shutil.which("markdownlint") is not None,
                  "detail": shutil.which("markdownlint") or "not on PATH; a record write that adds a violation is reverted only where it is"})
    items.append({"item": "markdown package", "need": OPTIONAL, "ok": module("markdown"),
                  "detail": "importable" if module("markdown") else "not importable by this interpreter; the dashboard shows bodies as paragraphs without it"})
    items.append({"item": "pdftotext", "need": OPTIONAL, "ok": shutil.which("pdftotext") is not None,
                  "detail": shutil.which("pdftotext") or "not on PATH; needed only for the text of a kept PDF"})
    items.append({"item": "sqlite fts5", "need": OPTIONAL, "ok": fts5(), "detail": "stemmed search" if fts5() else "whole-word search only; this is the interpreter's SQLite build, not installable apart"})
    installers = [t for t in ("uv", "pipx", "npm", "brew", "apt-get") if shutil.which(t)]
    items.append({"item": "installers", "need": OPTIONAL, "ok": True, "detail": ", ".join(installers) or "none of uv, pipx, npm, brew, apt-get"})
    return items, hook_runner, installers


def md_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for f in sorted(filenames):
            if f.endswith(".md"):
                yield Path(dirpath) / f


def project(root):
    """The project: its repository, its bindings files, its instructions, its documents, a prover."""
    items = []
    git_root = None
    for cand in (root, *root.parents):
        if (cand / ".git").exists():
            git_root = cand
            break
    items.append({"item": "git repository", "need": REQUIRED, "ok": git_root is not None,
                  "detail": f"root {git_root}" + ("" if git_root == root else f"; the project root {root} is inside it") if git_root else "none above the root; the records are tracked and the checks are commit hooks"})
    for name, tool in (("flow.toml", "flow"), ("library.toml", "library"), ("formal.toml", "formal")):
        present = (root / name).is_file()
        items.append({"item": name, "need": "present" if present else "absent", "ok": True,
                      "detail": f"{tool} is set up; `{tool} init` would refuse without --force" if present else f"not written yet; `{tool} init` writes it"})
    found = [f for f in INSTRUCTION_FILES if (root / f).is_file()]
    items.append({"item": "instructions file", "need": REQUIRED, "ok": bool(found),
                  "detail": ", ".join(found) if found else "none of " + ", ".join(INSTRUCTION_FILES) + "; the paragraphs `init` prints go into one"})
    logs = [f for f in LOG_NAMES if (root / f).is_file()]
    items.append({"item": "log", "need": REQUIRED, "ok": True,
                  "detail": f"{logs[0]} exists and would be bound as the log" if logs else "none of " + ", ".join(LOG_NAMES[:2]) + "; `flow init --log WORKLOG.md` starts one"})
    refs = {}
    for f in md_files(root):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if re.search(r"^## References\s*$", text, re.M):
            refs.setdefault(f.parent.relative_to(root).as_posix(), []).append(f.name)
    globs = [f"{d}/*.md" if d != "." else "*.md" for d in sorted(refs)]
    items.append({"item": "documents with a References section", "need": "found" if refs else "none", "ok": True,
                  "detail": "; ".join(f"{g} ({len(refs[d])} file(s))" for g, d in zip(globs, sorted(refs))) if refs else "none; `library init --documents` binds them when they exist"})
    lake = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        if Path(dirpath).relative_to(root).parts.__len__() > 2:
            dirnames[:] = []
        if "lakefile.toml" in filenames or "lakefile.lean" in filenames:
            lake.append(Path(dirpath).relative_to(root).as_posix())
    items.append({"item": "Lean workspace", "need": "found" if lake else "none", "ok": True,
                  "detail": ", ".join(lake) + "; the formal plugin's init sets the prover side up" if lake else "no lakefile under the root; the formal plugin is not needed"})
    pc = root / ".pre-commit-config.yaml"
    if pc.is_file():
        try:
            text = pc.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        # the kit's repository by its name, or by its hooks where the repo is a checkout's path
        has = "research-kit" in text or re.search(r"\bid:\s*['\"]?(?:flow|library)-check\b", text) is not None
        items.append({"item": ".pre-commit-config.yaml", "need": "present", "ok": True,
                      "detail": "names research-kit already" if has else "exists without the kit's hooks; the block is added to it"})
    else:
        items.append({"item": ".pre-commit-config.yaml", "need": "absent", "ok": True, "detail": "not written yet; the init writes it with the kit's hooks"})
    items.append({"item": "Makefile", "need": "present" if (root / "Makefile").is_file() else "absent", "ok": True,
                  "detail": "a `check` target runs the checks through the hooks (`prek run --all-files` or `pre-commit run --all-files`)" if (root / "Makefile").is_file() else "none"})
    return items, {"globs": globs, "logs": logs, "instructions": found, "lake": lake, "git_root": str(git_root) if git_root else None}


def externally_managed():
    """Whether this interpreter refuses `pip install --user` (PEP 668): a system's Python its packages manage."""
    return sys.prefix == sys.base_prefix and Path(sysconfig.get_path("stdlib"), "EXTERNALLY-MANAGED").is_file()


def proposals(env, hook_runner, installers, managed=None):
    """What to install for each missing item, one command per installer at hand; the person picks."""
    managed = externally_managed() if managed is None else managed
    out = []
    for it in env:
        if it["ok"]:
            continue
        cmds = []
        if it["item"] == "pre-commit runner":
            if "uv" in installers:
                cmds.append("uv tool install prek")
            if "pipx" in installers:
                cmds.append("pipx install pre-commit")
            if not managed:
                cmds.append(f"{sys.executable} -m pip install --user pre-commit")
            elif not cmds:
                cmds.append("pipx from the system's packages, then `pipx install pre-commit` (this Python's packages are the system's: pip refuses)")
        elif it["item"] == "markdownlint":
            if "npm" in installers:
                cmds.append("npm install -g markdownlint-cli")
            if "brew" in installers:
                cmds.append("brew install markdownlint-cli")
            if not cmds:
                cmds.append("npm install -g markdownlint-cli   # needs Node")
        elif it["item"] == "markdown package":
            if not managed:
                cmds.append(f"{sys.executable} -m pip install --user markdown   # or the distribution's python3-markdown")
            elif "apt-get" in installers:
                cmds.append("sudo apt-get install python3-markdown")
            else:
                cmds.append("the system's python3-markdown package (this Python's packages are the system's: pip refuses)")
        elif it["item"] == "pdftotext":
            if "apt-get" in installers:
                cmds.append("sudo apt-get install poppler-utils")
            if "brew" in installers:
                cmds.append("brew install poppler")
            if not cmds:
                cmds.append("poppler (poppler-utils) from the system's packages")
        elif it["item"] == "python":
            cmds.append("Python 3.11 or later from python.org or the system's packages; `uv python install 3.12` where uv is present")
        elif it["item"] == "git":
            cmds.append("git from the system's packages")
        else:
            continue
        out.append({"item": it["item"], "need": it["need"], "commands": cmds})
    return out


def probe(root):
    env, hook_runner, installers = environment()
    proj, facts = project(root)
    version = kit_version()
    kind, where = layout()
    return {"root": str(root), "environment": env, "project": proj, "facts": facts,
            "kit": {"version": version, "tag": f"v{version}" if version else None, "layout": kind, "path": where},
            "proposals": proposals(env, hook_runner, installers)}


def render(rep):
    lines = [f"setup probe at {rep['root']}", "", "environment (required, recommended, optional)"]
    for it in rep["environment"]:
        lines.append(f"  {'ok     ' if it['ok'] else 'MISSING'}  {it['item']} [{it['need']}]: {it['detail']}")
    lines += ["", "project"]
    for it in rep["project"]:
        lines.append(f"  {'ok     ' if it['ok'] else 'MISSING'}  {it['item']} [{it['need']}]: {it['detail']}")
    k = rep["kit"]
    lines += ["", f"kit: version {k['version'] or 'UNKNOWN'} (the hooks pin rev {k['tag'] or '<tag>'}), installed as a {k['layout']} at {k['path']}"]
    lines += ["", "proposals (nothing is installed by this probe)"]
    if not rep["proposals"]:
        lines.append("  nothing is missing")
    for p in rep["proposals"]:
        lines.append(f"  {p['item']} [{p['need']}]:")
        for c in p["commands"]:
            lines.append(f"    {c}")
    missing_req = [it["item"] for it in rep["environment"] + rep["project"] if not it["ok"] and it["need"] == REQUIRED]
    lines += ["", "setup probe: " + (f"{len(missing_req)} required item(s) missing: {', '.join(missing_req)}" if missing_req else "every required item is present")
              + f"; {len(rep['proposals'])} proposal(s); the probe read the root and PATH and wrote nothing"]
    return "\n".join(lines)


def selftest():
    bad = []

    def expect(name, cond, detail=""):
        print(f"  {'ok ' if cond else 'BAD'} {name}" + (f" — {detail}" if detail and not cond else ""))
        if not cond:
            bad.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "proj"
        (root / "papers").mkdir(parents=True)
        (root / "notes").mkdir()
        (root / "formal").mkdir()
        (root / ".git").mkdir()
        (root / "node_modules" / "x").mkdir(parents=True)
        (root / "papers" / "a.md").write_text("# A\n\n## References\n\n- X (2000).\n", encoding="utf-8")
        (root / "papers" / "b.md").write_text("# B\n\nno references\n", encoding="utf-8")
        (root / "notes" / "n.md").write_text("## References\n", encoding="utf-8")
        (root / "node_modules" / "x" / "r.md").write_text("## References\n", encoding="utf-8")
        (root / "formal" / "lakefile.toml").write_text('name = "x"\n', encoding="utf-8")
        (root / "CLAUDE.md").write_text("# Project\n", encoding="utf-8")
        (root / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
        rep = probe(root)
        by = {it["item"]: it for it in rep["project"]}
        expect("a git repository is found at the root", by["git repository"]["ok"] and rep["facts"]["git_root"] == str(root))
        expect("the documents with a References section are reported as globs, node_modules skipped",
               rep["facts"]["globs"] == ["notes/*.md", "papers/*.md"] and "papers/*.md (1 file(s))" in by["documents with a References section"]["detail"])
        expect("the Lean workspace is found", rep["facts"]["lake"] == ["formal"] and "formal plugin" in by["Lean workspace"]["detail"])
        expect("the instructions file is found", rep["facts"]["instructions"] == ["CLAUDE.md"] and by["instructions file"]["ok"])
        expect("no log is found and the init's start is proposed", rep["facts"]["logs"] == [] and "flow init --log" in by["log"]["detail"])
        expect("a pre-commit config without the kit is reported as such", "without the kit's hooks" in by[".pre-commit-config.yaml"]["detail"])
        expect("the bindings files are reported absent", all(by[n]["need"] == "absent" for n in ("flow.toml", "library.toml", "formal.toml")))
        (root / "flow.toml").write_text("", encoding="utf-8")
        (root / "WORKLOG.md").write_text("# Worklog\n", encoding="utf-8")
        rep2 = probe(root)
        by2 = {it["item"]: it for it in rep2["project"]}
        expect("an existing flow.toml and log are reported present", by2["flow.toml"]["need"] == "present" and rep2["facts"]["logs"] == ["WORKLOG.md"])
        bare = Path(tmp) / "bare"
        bare.mkdir()
        rep3 = probe(bare)
        by3 = {it["item"]: it for it in rep3["project"]}
        expect("a directory outside any repository fails the repository item", not by3["git repository"]["ok"])
        text = render(rep3)
        expect("the report ends with its coverage line", text.splitlines()[-1].startswith("setup probe: ") and "wrote nothing" in text)
        expect("the environment names the required items", {it["item"] for it in rep3["environment"] if it["need"] == REQUIRED} == {"python", "git", "pre-commit runner"})
        expect("this skill's version is read and the tag derived", rep3["kit"]["version"] is not None and rep3["kit"]["tag"] == "v" + rep3["kit"]["version"])
        fake_env = [{"item": "pre-commit runner", "need": REQUIRED, "ok": False, "detail": ""}, {"item": "markdownlint", "need": RECOMMENDED, "ok": False, "detail": ""}]
        props = proposals(fake_env, None, ["uv", "npm"])
        expect("a proposal per missing item, one command per installer at hand",
               [p["item"] for p in props] == ["pre-commit runner", "markdownlint"] and props[0]["commands"][0] == "uv tool install prek" and props[1]["commands"] == ["npm install -g markdownlint-cli"])
        md = [{"item": "markdown package", "need": OPTIONAL, "ok": False, "detail": ""}]
        expect("a Python the system's packages manage is offered no `pip install --user` (PEP 668)",
               proposals(fake_env + md, None, ["apt-get"], managed=True)[0]["commands"][0].startswith("pipx from")
               and proposals(md, None, ["apt-get"], managed=True)[0]["commands"] == ["sudo apt-get install python3-markdown"]
               and "pip install --user markdown" in proposals(md, None, [], managed=False)[0]["commands"][0])
        r = subprocess.run([sys.executable, __file__, "probe", "--root", str(bare), "--json"], capture_output=True, text=True)
        expect("probe --json is one JSON document", r.returncode == 0 and json.loads(r.stdout)["root"] == str(bare))
    print(f"setup selftest: {'OK' if not bad else str(len(bad)) + ' FAILED: ' + '; '.join(bad)}")
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="setup", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sp = ap.add_subparsers(dest="cmd")
    p = sp.add_parser("probe", help="report the project and the machine against the kit's setup")
    p.add_argument("--root", help="the project root (default: the current directory)")
    p.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd != "probe":
        ap.print_help()
        return 0
    root = Path(a.root).resolve() if a.root else Path(os.getcwd()).resolve()
    if not root.is_dir():
        print(f"setup: {root} is not a directory", file=sys.stderr)
        return 2
    rep = probe(root)
    sys.stdout.reconfigure(errors="backslashreplace")  # a file name that is not UTF-8 is shown, not a crash
    print(json.dumps(rep, indent=1) if a.json else render(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
