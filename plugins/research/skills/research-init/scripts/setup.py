#!/usr/bin/env python3
"""setup — the probe behind the `research-init` skill: what the project and the machine have, and what
the kit's setup needs that is missing.

  setup probe [--root DIR] [--json]   the report the skill's procedure reads
  setup runner [--root DIR] [--out PATH] [--force]
                                      write the project's runner (default scripts/kit.py), which runs a
                                      skill's script by its installed path and refuses while the pins disagree
  setup --selftest

The probe writes nothing and installs nothing; it reports, the agent proposes, the person
decides.  The runner is written only where the person said yes.  Standard library only.
"""
import argparse
import ast
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
FLOW = HERE.parent.parent / "flow" / "scripts" / "flow.py"  # the flow skill's script, beside this skill in the plugin
REQUIRED, RECOMMENDED, OPTIONAL = "required", "recommended", "optional"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".lake", "build", "dist"}
INSTRUCTION_FILES = ("CLAUDE.md", ".claude/CLAUDE.md", "AGENTS.md", ".github/copilot-instructions.md", "GEMINI.md")
LOG_NAMES = ("WORKLOG.md", "LOG.md", "worklog.md", "log.md")


def kit_version():
    """The version in this skill's SKILL.md frontmatter (the plugin's; the release tag is `v` + it)."""
    return skill_version(SKILL_MD)


def layout(here=HERE):
    """How these skills are laid out: a plugin in a git clone of the kit (under the repository's own
    marketplace: a checkout, or a clone an agent loads in place), a plugin (skills/<name> under a plugin with
    its manifest), a flat agent directory (.agents/skills, .claude/skills), or a copy."""
    skills = here.parent.parent
    plugin = skills.parent
    repo = plugin.parent.parent
    if (plugin / ".claude-plugin" / "plugin.json").is_file():
        if (repo / ".git").exists() and (repo / ".claude-plugin" / "marketplace.json").is_file():
            return "clone", str(repo)
        return "plugin", str(plugin)
    if skills.name == "skills":
        return "skills directory", str(skills)
    return "copy", str(here.parent)


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


def walk(root):
    """os.walk over the project's own tree: no tool or hidden directory, and no nested repository — a git
    submodule or a vendored clone, whose `.git` marks it — since its files are another project's."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
                             and not (Path(dirpath) / d / ".git").exists())
        yield dirpath, dirnames, filenames


def md_files(root):
    for dirpath, dirnames, filenames in walk(root):
        for f in sorted(filenames):
            if f.endswith(".md"):
                yield Path(dirpath) / f


def rules(make):
    """A Makefile's rules, target -> (prerequisites, recipe lines): a rule may name several targets and carry
    an inline recipe after `;`; a recipe line is tab-indented, a commented one is dropped, and a conditional
    at the margin does not end the recipe."""
    out, cur = {}, []
    for line in make.split("\n"):
        if line.startswith("\t"):
            if not line.strip().startswith("#"):
                cur.append(line.strip())
        elif re.match(r"(?:ifn?eq|ifn?def|else|endif)\b", line):
            continue
        elif line.strip() and not line.startswith("#"):
            m = re.match(r"([^:=#\t][^:=#]*?)\s*::?(?!=)\s*([^;#]*)(?:;(.*))?$", line)
            cur = []
            if m:
                cur = [m.group(3).strip()] if m.group(3) and m.group(3).strip() else []
                for t in m.group(1).split():
                    out[t] = (m.group(2).split(), cur)
    return out


def runs_hooks(make, target="check"):
    """Whether a Makefile's target runs the hooks, in its recipe or in a prerequisite's, one level down."""
    rs = rules(make)
    hooks = lambda t: any(re.search(r"\b(?:prek|pre-commit) run\b", l) for l in rs.get(t, ([], []))[1])
    return target in rs and (hooks(target) or any(hooks(t) for t in rs[target][0]))


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
    items.append({"item": "instructions file", "need": "present" if found else "absent", "ok": True,
                  "detail": ", ".join(found) if found else "none of " + ", ".join(INSTRUCTION_FILES) + "; the paragraphs `init` prints go into a new one"})
    logs = [f for f in LOG_NAMES if (root / f).is_file()]
    items.append({"item": "log", "need": "present" if logs else "absent", "ok": True,
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
    for dirpath, dirnames, filenames in walk(root):
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
    mk = root / "Makefile"
    try:
        make = mk.read_text(encoding="utf-8", errors="replace") if mk.is_file() else None
    except OSError:
        make = None
    runs = make is not None and runs_hooks(make)
    could = "a `check` target can run the checks through the hooks (`prek run --all-files` or `pre-commit run --all-files`)"
    items.append({"item": "Makefile", "need": "present" if make is not None else "absent", "ok": True,
                  "detail": "its `check` target runs the hooks" if runs else f"found no `check` target running the hooks; {could}" if make is not None else f"none; {could}"})
    items.append(kit_pins(root, kit_version()))
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


# --- the pins: duplicated byte-identical in research's setup.py and formal's formal.py (tests/run.py holds
# them so), and copied into the runner `setup runner` writes -------------------------------------------------

KIT_REPO = "lividgreen/research-kit"
KIT_CHANGELOG = "https://github.com/lividgreen/research-kit/blob/main/CHANGELOG.md"


def skill_version(skill_md):
    """The `metadata.version` of a SKILL.md's frontmatter: its plugin's version, whose release tag is `v` + it."""
    try:
        fm = Path(skill_md).read_text(encoding="utf-8").split("---")[1]
    except (OSError, IndexError):
        return None
    m = re.search(r'^\s+version: "([^"]+)"', fm, re.M)
    return m.group(1) if m else None


def hooks_pin(text):
    """The kit's entry of a .pre-commit-config.yaml: its repo and its rev, read from the list item that names
    research-kit wherever its keys stand and with comments allowed; a rev frozen to a commit by
    `autoupdate --freeze` is read as the tag its `# frozen:` comment names.  (None, None) where none names it."""
    lines = text.split("\n")
    indent = lambda l: len(l) - len(l.lstrip())
    for i, l in enumerate(lines):
        m = re.match(r"\s*(?:-\s+)?repo:\s*['\"]?([^\s'\"#]+)", l)
        if not m or "research-kit" not in m.group(1):
            continue
        s = i  # the item's dash: on this line, or the nearest above it less indented than the key
        while s > 0 and not (re.match(r"\s*-\s", lines[s]) and (s == i or indent(lines[s]) < indent(l))):
            s -= 1
        d, e = indent(lines[s]), s + 1
        while e < len(lines) and not (lines[e].strip() and not lines[e].lstrip().startswith("#") and indent(lines[e]) <= d):
            e += 1
        for item in lines[s:e]:
            r = re.match(r"\s*(?:-\s+)?rev:\s*['\"]?([^\s'\"#]+)['\"]?\s*(?:#\s*frozen:\s*(\S+))?", item)
            if r:
                return m.group(1), r.group(2) or r.group(1)
        return m.group(1), None
    return None, None


def install_record():
    """Claude Code's install record, `~/.claude/plugins/installed_plugins.json`; `CLAUDE_CONFIG_DIR` moves `~/.claude`."""
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "plugins" / "installed_plugins.json"


def kit_installed(root, record):
    """The plugins of the research-kit marketplace Claude Code installed for the project, name -> entry (its
    `version`, `scope` and `installPath`), from the install record (`plugins` -> name -> entries): the entry of
    scope local, else project, whose `projectPath` is the root, else the user one.  None where the record is
    absent or unreadable."""
    try:
        raw = json.loads(Path(record).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    plugins = raw.get("plugins") if isinstance(raw, dict) else None
    if not isinstance(plugins, dict):
        return None
    root, out = Path(root).resolve(), {}
    for name, entries in sorted(plugins.items()):
        if not name.endswith("@research-kit"):
            continue
        entries = [e for e in (entries if isinstance(entries, list) else [entries]) if isinstance(e, dict)]
        for scope in ("local", "project", "user"):
            hit = [e for e in entries if e.get("scope") == scope
                   and (scope == "user" or bool(e.get("projectPath")) and Path(str(e["projectPath"])).resolve() == root)]
            if hit:
                out[name] = hit[0]
                break
    return out


def kit_tag(tag):
    """A release tag as a tuple to order by (`v0.4.3` -> (0, 4, 3)); None for anything else, a commit or a branch."""
    m = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", str(tag or ""))
    return tuple(int(g) for g in m.groups()) if m else None


def kit_pins(root, version, record=None):
    """The places a project pins the kit — the hooks' `rev`, the Claude Code marketplace's `ref` in the project's
    settings, the version of each plugin of the marketplace Claude Code installed for the project (`record`, the
    install record, defaults to Claude Code's) — beside the version of the plugin this script runs from (None for
    a script outside the kit): whether they name one tag and, where they do not, the steps that move every pin
    to the newest of them and the releases whose upgrading paragraphs lie between.  It writes nothing."""
    root = Path(root).resolve()
    record = Path(record) if record else install_record()
    said, tags = [], {}
    try:
        pc = (root / ".pre-commit-config.yaml").read_text(encoding="utf-8", errors="replace")
    except OSError:
        pc = ""
    repo, rev = hooks_pin(pc)
    if repo and not re.match(r"(?:https?|ssh|git)://|[\w.-]+@", repo):
        said.append(f"the hooks run from the local repository {repo}, whose rev is not compared")
    elif rev:
        said.append(f"the hooks pin rev {rev}")
        tags["the hooks' rev"] = rev
    try:
        st = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = None
    st = st if isinstance(st, dict) else {}
    markets = st.get("extraKnownMarketplaces") if isinstance(st.get("extraKnownMarketplaces"), dict) else {}
    src = markets["research-kit"].get("source") if isinstance(markets.get("research-kit"), dict) else None
    unpinned = False
    if isinstance(src, dict):
        ref = src.get("ref") or (str(src.get("url") or "").partition("#")[2] or None)
        if src.get("source") in ("directory", "file"):
            said.append(f"the marketplace in .claude/settings.json is a local {src['source']}, which no ref pins")
        elif ref:
            said.append(f"the marketplace in .claude/settings.json pins ref {ref}")
            tags["the marketplace's ref"] = str(ref)
        else:
            said.append("the marketplace in .claude/settings.json pins no ref and follows the default branch")
            unpinned = True
    if not repo and not isinstance(src, dict):
        said.append("nothing in the project pins the kit yet")
    enabled = st.get("enabledPlugins") if isinstance(st.get("enabledPlugins"), dict) else {}
    inst, me, runs_installed = kit_installed(root, record), Path(__file__).resolve(), False
    if inst is None:
        said.append(f"Claude Code's install record {record} is absent or unreadable, so no installed plugin is compared (another agent, or no install)")
    else:
        for name, e in inst.items():
            mine = bool(e.get("installPath")) and me.is_relative_to(Path(str(e["installPath"])).resolve())
            runs_installed = runs_installed or mine
            said.append(f"{name} is installed at v{e.get('version')} ({e.get('scope')} scope)" + (", which this runs from" if mine else ""))
            tags[name] = f"v{e.get('version')}"
        if not inst:
            said.append(f"no plugin of research-kit is installed for this project in {record}")
    missing = sorted(n for n, on in enabled.items() if on is True and n.endswith("@research-kit") and inst is not None and n not in inst)
    said += [f"{n} is enabled in .claude/settings.json and not installed for this project" for n in missing]
    if version and not runs_installed:
        said.insert(0, f"the plugin this runs from is v{version}")
        tags["the plugin this runs from"] = f"v{version}"
    ordered = all(kit_tag(t) for t in tags.values())
    target = (max(tags.values(), key=kit_tag) if ordered else tags.get("the hooks' rev") or next(iter(tags.values()))) if tags else None
    T = target or "<tag>"
    off = [w for w, t in tags.items() if t != T] + (["the marketplace's ref"] if unpinned else []) + [f"{n} (not installed)" for n in missing]
    steps, releases = [], None
    if off:
        if unpinned or tags.get("the marketplace's ref", T) != T:
            steps.append(f"edit the `ref` of `extraKnownMarketplaces.research-kit` to {T} in .claude/settings.json, "
                         "and in ~/.claude/settings.json where another project on the machine pinned it there")
        lag = [n for n in (inst or {}) if tags.get(n) != T]
        if steps or lag or missing:
            steps.append(f"claude plugin marketplace add '{KIT_REPO}#{T}' --scope project")
        steps += [f"claude plugin update {n} --scope {inst[n].get('scope') or 'project'}" for n in lag]
        steps += [f"claude plugin install {n} --scope project" for n in missing]
        if tags.get("the hooks' rev", T) != T:
            steps.append(f"set the hooks' `rev` to {T} in .pre-commit-config.yaml, in the commit that moves the settings file")
        if tags.get("the plugin this runs from", T) != T:
            steps.append(f"move the plugin this runs from to {T}: its agent's marketplace pin, or by hand for a clone or a copy")
        steps.append("restart the session, then read the pins again")
        seen = sorted({t for t in tags.values() if kit_tag(t)}, key=kit_tag)
        if len(seen) > 1:
            releases = f"read the Upgrading paragraph of each release after {seen[0]} up to {seen[-1]}, in {KIT_CHANGELOG}"
    named = off[0] if len(off) == 1 else ", ".join(off[:-1]) + " and " + off[-1] if off else ""
    detail = "; ".join(said) + (f" — {named} {'differ' if len(off) > 1 else 'differs'} from {T}"
                                + (", the newest of them" if ordered and len(tags) > 1 else "") + ": move the pins together" if off else "")
    return {"item": "pins at one tag", "need": "recommended", "ok": not off, "detail": detail, "target": target,
            "commands": steps, "releases": releases}


def flow_answer(flow, root, *argv):
    """The flow script's `--json` answer to a command that writes nothing, or (None, why) where it gave none:
    a refusal (a flow.toml it cannot read), a crash, no answer in time."""
    try:
        r = subprocess.run([sys.executable, str(flow), "--json", "--root", str(root), *argv], capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    try:
        out = json.loads(r.stdout)
    except ValueError:  # a crash: the exception's line, above the script's own "could not run"
        said = [l for l in (r.stderr or r.stdout).strip().splitlines() if l.strip() and "could not run" not in l]
        return None, said[-1].strip() if said else f"exit {r.returncode}"
    refused = [str(p.get("msg")) for p in out.get("problems") or [] if p.get("code") == "REFUSED"]
    return (None, "; ".join(refused)) if refused else (out, None)


def upgrade(root, pins, flow=FLOW):
    """The upgrade steps the probe can see, each with its command, in the order an upgrade takes them: the pins
    off one tag, with the releases between whose upgrading paragraphs to read; the records and bindings an older
    model wrote, which the flow skill's `flow doctor` beside this skill names; a stale index, which `flow index
    --check` names.  The two flow commands write nothing; a step is `pending`, `ok`, `none` (no flow.toml) or
    `not run` (it could not be checked)."""
    steps = [{"item": "pins", "state": "ok" if pins["ok"] else "pending",
              "detail": f"at one tag, {pins['target']}" if pins["ok"] and pins["target"] else "nothing pins the kit yet" if pins["ok"] else
              f"every pin moves to {pins['target'] or '<tag>'}, in the order of the steps below",
              "commands": ([pins["releases"]] if pins["releases"] else []) + pins["commands"]}]
    if not (root / "flow.toml").is_file():
        return steps + [{"item": "records", "state": "none", "detail": "no flow.toml; `flow init` writes the current model", "commands": []}]
    if not Path(flow).is_file():
        why = f"the flow skill's script is not beside this skill ({flow}), so the records' model could not be checked"
        return steps + [{"item": "records", "state": "not run", "detail": why, "commands": ["flow doctor", "flow index --check"]}]
    doc, why = flow_answer(flow, root, "doctor")
    mech = []
    if doc is None:
        steps.append({"item": "records", "state": "not run", "detail": f"`flow doctor` gave no answer: {why}", "commands": ["flow doctor"]})
    else:
        mech, hand = doc.get("mechanical") or [], doc.get("problems") or []
        by = ", ".join(f"{n} {c}" for c, n in sorted((doc.get("summary") or {}).items(), key=lambda x: (-x[1], x[0])))
        steps.append({"item": "records", "state": "pending" if mech or hand else "ok",
                      "detail": f"`flow doctor` names {len(mech)} mechanical edit(s)" + (f" ({by})" if by else "") + f" and {len(hand)} thing(s) for the hand"
                      if mech or hand else "`flow doctor` finds nothing an older model wrote",
                      "commands": ([f"flow doctor --fix   # writes the {len(mech)} mechanical edit(s) in place and refreshes the index"] if mech else [])
                      + ([f"flow doctor   # lists the {len(hand)} thing(s) for the hand, each settled from its line"] if hand else [])})
    idx, why = flow_answer(flow, root, "index", "--check")
    if idx is None:
        steps.append({"item": "index", "state": "not run", "detail": f"`flow index --check` gave no answer: {why}", "commands": ["flow index --check"]})
    else:
        stale = bool(idx.get("stale"))
        steps.append({"item": "index", "state": "pending" if stale else "ok",
                      "detail": "stale: it is not what this release renders" + ("; `flow doctor --fix` refreshes it" if mech else "") if stale else "fresh",
                      "commands": ["flow index"] if stale else []})
    return steps


def probe(root, flow=FLOW):
    env, hook_runner, installers = environment()
    proj, facts = project(root)
    version = kit_version()
    kind, where = layout()
    pins = next(it for it in proj if it["item"] == "pins at one tag")
    return {"root": str(root), "environment": env, "project": proj, "facts": facts,
            "kit": {"version": version, "tag": f"v{version}" if version else None, "layout": kind, "path": where},
            "proposals": proposals(env, hook_runner, installers),
            "upgrade": {"flow": str(flow), "steps": upgrade(root, pins, flow)}}


def mark(it):
    """The status column: MISSING for a needed item the machine or the project lacks, `--` for one that is
    not there and is not needed (an init writes it, or the project has none), ok otherwise."""
    return "MISSING" if not it["ok"] else "--     " if it["need"] in ("absent", "none") else "ok     "


RUNNER = '''#!/usr/bin/env python3
"""kit — run a research-kit skill's script from the plugin Claude Code installed for this project.

Written by research-kit's `setup runner` at @@TAG@@; the project's file from then on, to keep or edit.
research-kit installs no command: its scripts live in the `research` and `formal` plugins' skills
and run by their installed path, which moves with every version.  This reads that path from Claude
Code's install record (`~/.claude/plugins/installed_plugins.json`, `CLAUDE_CONFIG_DIR` moving
`~/.claude`) and refuses while the pins disagree: the hooks' `rev` in .pre-commit-config.yaml, the
marketplace's `ref` in .claude/settings.json, the version of each research-kit plugin installed for
this project.  It installs nothing and writes nothing.

  kit.py run SKILL [ARGS...]   run the skill's script with ARGS: flow, library, dashboard, setup, formal
  kit.py path SKILL            print the script's path
  kit.py check                 print the pins, and the steps that move them where they disagree (exit 1)

A refusal exits 2; `run` exits with the script's own code.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = (Path(__file__).resolve().parent / "@@UP@@").resolve()
SCRIPTS = {"flow": ("research@research-kit", "flow/scripts/flow.py"),
           "library": ("research@research-kit", "library/scripts/library.py"),
           "dashboard": ("research@research-kit", "dashboard/scripts/dashboard.py"),
           "setup": ("research@research-kit", "research-init/scripts/setup.py"),
           "formal": ("formal@research-kit", "land/scripts/formal.py")}


@@HELPERS@@


def script(skill):
    """(the installed path of a skill's script, None), or (None, the refusal)."""
    if skill not in SCRIPTS:
        return None, f"no skill {skill!r}; one of {', '.join(SCRIPTS)}"
    pins = kit_pins(ROOT, None)
    if not pins["ok"]:
        return None, "the pins disagree: " + pins["detail"] + "".join(f"\\n  {c}" for c in pins["commands"])
    inst = kit_installed(ROOT, install_record())
    if inst is None:
        return None, f"no install record at {install_record()}; this runner finds the scripts where Claude Code installed them"
    plugin, rel = SCRIPTS[skill]
    if plugin not in inst:
        return None, f"{plugin} is not installed for this project: claude plugin install {plugin} --scope project"
    path = Path(str(inst[plugin].get("installPath"))) / "skills" / rel
    return (path, None) if path.is_file() else (None, f"{path} is missing from the installed {plugin}")


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if argv[1:] == ["check"]:
        pins = kit_pins(ROOT, None)
        print(("pins at one tag: " if pins["ok"] else "PINS DISAGREE: ") + pins["detail"])
        for c in ([pins["releases"]] if pins["releases"] else []) + pins["commands"]:
            print(f"  {c}")
        return 0 if pins["ok"] else 1
    if (argv[1] == "path" and len(argv) == 3) or (argv[1] == "run" and len(argv) >= 3):
        path, why = script(argv[2])
        if why:
            print(f"kit: {why}", file=sys.stderr)
            return 2
        if argv[1] == "path":
            print(path)
            return 0
        return subprocess.run([sys.executable, str(path), *argv[3:]]).returncode
    print("kit: usage: kit.py run SKILL [ARGS...] | path SKILL | check", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
'''
RUNNER_HELPERS = ("KIT_REPO", "KIT_CHANGELOG", "hooks_pin", "install_record", "kit_installed", "kit_tag", "kit_pins")


def runner_text(up):
    """The runner's text: RUNNER with the pins' helpers copied from this file, the root `up` from the runner's directory."""
    src = Path(__file__).read_text(encoding="utf-8")
    named = lambda n: n.name if isinstance(n, ast.FunctionDef) else n.targets[0].id if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) else None
    helpers = [ast.get_source_segment(src, n) for n in ast.parse(src).body if named(n) in RUNNER_HELPERS]
    consts = "\n".join(h for h in helpers if not h.startswith("def "))
    funcs = "\n\n\n".join(h for h in helpers if h.startswith("def "))
    return RUNNER.replace("@@TAG@@", f"v{kit_version()}").replace("@@UP@@", up).replace("@@HELPERS@@", consts + "\n\n\n" + funcs)


def write_runner(root, out, force):
    """`setup runner`: the runner written at `out` under the root; an existing file refused without --force."""
    out = (root / out).resolve() if not Path(out).is_absolute() else Path(out).resolve()
    if not out.is_relative_to(root):
        return 2, f"setup: {out} is outside the project root {root}; the runner is the project's file"
    if out.exists() and not force:
        return 1, f"setup: {out.relative_to(root)} exists; `--force` rewrites it"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(runner_text(Path(os.path.relpath(root, out.parent)).as_posix()), encoding="utf-8")
    out.chmod(out.stat().st_mode | 0o111)
    rel = out.relative_to(root).as_posix()
    return 0, (f"wrote {rel}: `python3 {rel} check` prints the pins, `python3 {rel} run flow state` runs a skill's script by its installed path, "
               "refusing while the pins disagree; it installs nothing and is the project's file")


UPGRADE_MARK = {"pending": "PENDING", "ok": "ok     ", "none": "--     ", "not run": "NOT RUN"}


def render(rep):
    lines = [f"setup probe at {rep['root']}", "", "environment (required, recommended, optional)"]
    for it in rep["environment"]:
        lines.append(f"  {mark(it)}  {it['item']} [{it['need']}]: {it['detail']}")
    lines += ["", "project"]
    for it in rep["project"]:
        lines.append(f"  {mark(it)}  {it['item']} [{it['need']}]: {it['detail']}")
    k = rep["kit"]
    where = f"laid out as a plugin in a git clone of the kit at {k['path']}" if k["layout"] == "clone" else f"laid out as a {k['layout']} at {k['path']}"
    lines += ["", f"kit: version {k['version'] or 'UNKNOWN'} (the hooks pin rev {k['tag'] or '<tag>'}), {where}"]
    lines += ["", "proposals (nothing is installed by this probe)"]
    if not rep["proposals"]:
        lines.append("  nothing is missing")
    for p in rep["proposals"]:
        lines.append(f"  {p['item']} [{p['need']}]:")
        for c in p["commands"]:
            lines.append(f"    {c}")
    up = rep["upgrade"]
    lines += ["", f"upgrade (the steps a move to another release still asks, in their order; `flow` is {up['flow']}, "
              "whose `doctor` and `index --check` the probe ran, which write nothing)"]
    for s in up["steps"]:
        lines.append(f"  {UPGRADE_MARK[s['state']]}  {s['item']}: {s['detail']}")
        for c in s["commands"]:
            lines.append(f"    {c}")
    missing_req = [it["item"] for it in rep["environment"] + rep["project"] if not it["ok"] and it["need"] == REQUIRED]
    pending = [s["item"] for s in up["steps"] if s["state"] == "pending"]
    lines += ["", "setup probe: " + (f"{len(missing_req)} required item(s) missing: {', '.join(missing_req)}" if missing_req else "every required item is present")
              + f"; {len(rep['proposals'])} proposal(s); " + (f"{len(pending)} upgrade step(s) pending: {', '.join(pending)}" if pending else "no upgrade step pending")
              + "; the probe read the root and PATH and wrote nothing"]
    return "\n".join(lines)


def kit_settings(p, ref, enabled=("research@research-kit",)):
    """A project's .claude/settings.json with the kit's marketplace at `ref` and the plugins enabled."""
    (p / ".claude").mkdir(parents=True, exist_ok=True)
    (p / ".claude" / "settings.json").write_text(json.dumps({
        "extraKnownMarketplaces": {"research-kit": {"source": {"source": "github", "repo": KIT_REPO, "ref": ref}}},
        "enabledPlugins": {n: True for n in enabled}}), encoding="utf-8")


def kit_hooks(p, rev):
    (p / ".pre-commit-config.yaml").write_text(f"repos:\n- repo: https://github.com/lividgreen/research-kit\n  rev: {rev}\n  hooks:\n  - id: flow-check\n", encoding="utf-8")


def installed_scenarios(tmp, v, expect):
    """The pins against an install record: which entry is the project's, and the steps and releases each case names."""
    p = tmp / "pinned"
    p.mkdir()
    kit_hooks(p, f"v{v}")
    kit_settings(p, f"v{v}")
    rec = tmp / "installed_plugins.json"
    entry = lambda scope, version, project=p: {"scope": scope, **({"projectPath": str(project)} if scope != "user" else {}),
                                               "installPath": str(tmp / "cache" / version), "version": version}

    def against(plugins):
        rec.write_text(json.dumps({"version": 2, "plugins": plugins}), encoding="utf-8")
        return kit_pins(p, v, rec)
    r = against({"research@research-kit": [entry("project", "0.0.1", tmp / "elsewhere"), entry("user", "0.0.2"), entry("project", v)],
                 "other@elsewhere": [entry("project", "9.9.9")]})
    expect("the project's own entry is read over a user one and another project's, and another marketplace's plugin is not",
           r["ok"] and f"research@research-kit is installed at v{v} (project scope)" in r["detail"] and "other@elsewhere" not in r["detail"], r["detail"])
    r = against({"research@research-kit": [entry("project", v), entry("local", "0.0.1")]})
    expect("a local entry for the project stands over its project one", not r["ok"] and "(local scope)" in r["detail"]
           and "claude plugin update research@research-kit --scope local" in r["commands"], r["detail"])
    r = against({"research@research-kit": [entry("user", v)]})
    expect("a user entry stands where the project has none", r["ok"] and "(user scope)" in r["detail"], r["detail"])
    kit_settings(p, f"v{v}", ("research@research-kit", "formal@research-kit"))
    r = against({"research@research-kit": [entry("project", v)], "formal@research-kit": [entry("project", "0.0.1")]})
    expect("an installed plugin behind the pins is named, with the update that moves it and the releases between to read",
           not r["ok"] and "formal@research-kit differs from" in r["detail"]
           and r["commands"][:2] == [f"claude plugin marketplace add '{KIT_REPO}#v{v}' --scope project", "claude plugin update formal@research-kit --scope project"]
           and "update research@" not in " ".join(r["commands"]) and f"after v0.0.1 up to v{v}" in str(r["releases"]) and KIT_CHANGELOG in str(r["releases"]),
           f"{r['detail']} {r['commands']} {r['releases']}")
    r = against({"research@research-kit": [entry("project", v)]})
    expect("a plugin the settings enable and the record lacks is named with its install",
           not r["ok"] and "formal@research-kit (not installed)" in r["detail"] and "claude plugin install formal@research-kit --scope project" in r["commands"])
    kit_settings(p, "v0.0.1")
    kit_hooks(p, "v0.0.1")
    r = against({"research@research-kit": [entry("project", v)]})
    expect("pins behind the installed plugin move to its tag: the ref edited, the marketplace added at it, the hooks' rev set, the restart",
           not r["ok"] and r["target"] == f"v{v}" and [c.split(" ")[0] for c in r["commands"]] == ["edit", "claude", "set", "restart"]
           and "the hooks' rev and the marketplace's ref differ" in r["detail"] and f"after v0.0.1 up to v{v}" in str(r["releases"]), str(r["commands"]))
    kit_settings(p, "v99.0.0")
    kit_hooks(p, "v99.0.0")
    r = against({"research@research-kit": [entry("project", v)]})
    expect("pins ahead of the installed plugin move the plugin, and the plugin this runs from is named; the hooks stay",
           not r["ok"] and r["target"] == "v99.0.0" and "claude plugin update research@research-kit --scope project" in r["commands"]
           and any(c.startswith("move the plugin this runs from to v99.0.0") for c in r["commands"]) and not any(c.startswith("set the hooks") for c in r["commands"]),
           str(r["commands"]))
    kit_settings(p, "main")
    kit_hooks(p, "0123abcd")
    r = against({"research@research-kit": [entry("project", v)]})
    expect("a rev that is no release tag is the target as it stands, and no releases are named",
           not r["ok"] and r["target"] == "0123abcd" and r["releases"] is None and "the newest" not in r["detail"])
    rec.write_text("{", encoding="utf-8")
    expect("an unreadable install record is said so and compares no plugin", "absent or unreadable" in kit_pins(p, v, rec)["detail"])


def upgrade_scenarios(tmp, v, expect):
    """The upgrade section over a tree the sibling flow script wrote: nothing pending, then an older model's field and
    binding, a stale index, an unreadable flow.toml, a flow script that is not there; the probe writes nothing."""
    u = tmp / "upgrade"
    u.mkdir()
    steps = lambda flow=FLOW: {s["item"]: s for s in upgrade(u, kit_pins(u, v), flow)}
    expect("with no flow.toml there are no records to migrate", steps()["records"]["state"] == "none")
    if not FLOW.is_file():
        print(f"  --  the upgrade's flow steps not tested: no flow skill beside this one ({FLOW})")
        return
    flow = lambda *a: subprocess.run([sys.executable, str(FLOW), *a], capture_output=True, text=True, cwd=u)
    flow("init", "--log", "WORKLOG.md")
    flow("task", "a chore", "--tag", "upkeep")
    s = steps()
    expect("a tree the flow wrote has no upgrade step pending", s["records"]["state"] == "ok" and s["index"]["state"] == "ok", str(s))
    task = next((u / "records").rglob("task-0001-*.md"))
    task.write_text("".join(l for l in task.read_text(encoding="utf-8").splitlines(True) if not l.startswith("rider:")), encoding="utf-8")
    with open(u / "flow.toml", "a", encoding="utf-8") as f:
        f.write('\n[task]\ndefault_kind = "work"\n')
    snapshot = lambda: {q: q.read_bytes() for q in sorted(u.rglob("*")) if q.is_file()}
    before = snapshot()
    rep = probe(u)
    s = {x["item"]: x for x in rep["upgrade"]["steps"]}
    expect("an older model's field and binding are counted, with `flow doctor --fix` and `flow doctor`",
           s["records"]["state"] == "pending" and "1 mechanical edit(s) (1 field) and 1 thing(s) for the hand" in s["records"]["detail"]
           and s["records"]["commands"][0].startswith("flow doctor --fix ") and s["records"]["commands"][1].startswith("flow doctor  "), str(s["records"]))
    expect("the probe ran the flow's doctor and index check and wrote nothing", snapshot() == before)
    expect("the report shows the upgrade section and counts what is pending",
           "\nupgrade (" in render(rep) and "PENDING  records:" in render(rep) and "upgrade step(s) pending: records" in render(rep).splitlines()[-1])
    (u / "records" / "INDEX.md").unlink()
    s = steps()
    expect("a stale index is named with `flow index`, and the doctor's fix as what refreshes it",
           s["index"]["state"] == "pending" and s["index"]["commands"] == ["flow index"] and "doctor --fix" in s["index"]["detail"])
    s = steps(tmp / "nowhere" / "flow.py")
    expect("where the flow skill's script is not beside this one, the records' step says it could not be checked",
           s["records"]["state"] == "not run" and "could not be checked" in s["records"]["detail"] and "index" not in s)
    (u / "flow.toml").write_text("[paths\n", encoding="utf-8")
    s = steps()
    expect("a flow.toml the flow cannot read leaves the steps not run, with the flow's words",
           s["records"]["state"] == "not run" and "gave no answer: " in s["records"]["detail"] and "could not run" not in s["records"]["detail"]
           and "NOT RUN" in render(probe(u)), s["records"]["detail"])


def runner_scenarios(tmp, v, expect):
    """`setup runner` end to end: the runner written, then run against a fake install record and fake plugin trees."""
    p = tmp / "consumer"
    p.mkdir()
    kit_hooks(p, f"v{v}")
    kit_settings(p, f"v{v}", ("research@research-kit", "formal@research-kit"))
    cache = tmp / "plugin-cache"
    fake = 'import json, os, sys\nprint(json.dumps({"script": __file__, "argv": sys.argv[1:], "cwd": os.getcwd()}))\nsys.exit(3 if "fail" in sys.argv else 0)\n'
    for plugin, rel in (("research", "flow/scripts/flow.py"), ("research", "research-init/scripts/setup.py"), ("formal", "land/scripts/formal.py")):
        f = cache / plugin / v / "skills" / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(fake, encoding="utf-8")
    rec = install_record()

    def record(formal=v):
        rec.parent.mkdir(parents=True, exist_ok=True)
        rec.write_text(json.dumps({"version": 2, "plugins": {
            "research@research-kit": [{"scope": "project", "projectPath": str(p), "installPath": str(cache / "research" / v), "version": v}],
            "formal@research-kit": [{"scope": "project", "projectPath": str(p), "installPath": str(cache / "formal" / formal), "version": formal}]}}),
            encoding="utf-8")
    record()
    kit = p / "scripts" / "kit.py"
    code, said = write_runner(p, "scripts/kit.py", False)
    expect("the runner is written at scripts/kit.py, executable, and the line says how it runs",
           code == 0 and kit.is_file() and os.access(kit, os.X_OK) and said.startswith("wrote scripts/kit.py: `python3 scripts/kit.py check`"), said)
    expect("an existing runner is refused without --force and rewritten with it",
           write_runner(p, "scripts/kit.py", False)[0] == 1 and write_runner(p, "scripts/kit.py", True)[0] == 0)
    expect("a runner path outside the project root is refused", write_runner(p, str(tmp / "kit.py"), False)[0] == 2 and not (tmp / "kit.py").exists())
    text = kit.read_text(encoding="utf-8")
    src = Path(__file__).read_text(encoding="utf-8")
    segs = [ast.get_source_segment(src, n) for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name in RUNNER_HELPERS]
    expect("the runner carries the pins' helpers as this script has them, at this release", all(s in text for s in segs) and f"at v{v};" in text)
    run = lambda k, *a: subprocess.run([sys.executable, str(k), *a], capture_output=True, text=True, cwd=tmp)
    r = run(kit, "check")
    expect("the runner's check passes pins at one tag and exits 0", r.returncode == 0 and r.stdout.startswith("pins at one tag: "), r.stdout + r.stderr)
    r = run(kit, "run", "flow", "state", "--json")
    out = json.loads(r.stdout) if r.returncode == 0 and r.stdout.startswith("{") else {}
    expect("run runs the installed skill's script with the arguments, in the caller's directory",
           out.get("script") == str(cache / "research" / v / "skills" / "flow" / "scripts" / "flow.py") and out.get("argv") == ["state", "--json"]
           and Path(out.get("cwd", "")).resolve() == tmp.resolve(), r.stdout + r.stderr)
    expect("run exits with the script's own code", run(kit, "run", "setup", "fail").returncode == 3)
    r = run(kit, "path", "formal")
    expect("path prints the installed script's path", r.returncode == 0 and r.stdout.strip() == str(cache / "formal" / v / "skills" / "land" / "scripts" / "formal.py"))
    r = run(kit, "run", "lean")
    expect("an unknown skill is refused, exit 2, with the skills named", r.returncode == 2 and "one of flow, library, dashboard, setup, formal" in r.stderr)
    deep = p / "tools" / "kit" / "run.py"
    expect("a runner written deeper finds the root from where it stands", write_runner(p, "tools/kit/run.py", False)[0] == 0 and run(deep, "check").returncode == 0)
    record(formal="0.0.1")
    r = run(kit, "check")
    expect("check names an installed plugin off the pins with the update that moves it, and exits 1",
           r.returncode == 1 and r.stdout.startswith("PINS DISAGREE: ") and "claude plugin update formal@research-kit --scope project" in r.stdout, r.stdout)
    r = run(kit, "run", "flow", "check")
    expect("run refuses while the pins disagree, exit 2, with the steps", r.returncode == 2 and "the pins disagree" in r.stderr and "claude plugin update formal@" in r.stderr)
    rec.unlink()
    r = run(kit, "path", "flow")
    expect("with no install record run and path are refused and say why", r.returncode == 2 and "no install record at" in r.stderr)
    r = subprocess.run([sys.executable, __file__, "runner", "--root", str(p)], capture_output=True, text=True)
    expect("`setup runner` refuses an existing file from the command line, exit 1", r.returncode == 1 and "--force" in r.stderr)


def selftest():
    bad = []

    def expect(name, cond, detail=""):
        print(f"  {'ok ' if cond else 'BAD'} {name}" + (f" — {detail}" if detail and not cond else ""))
        if not cond:
            bad.append(name)

    saved_config = os.environ.get("CLAUDE_CONFIG_DIR")
    with tempfile.TemporaryDirectory() as tmp:
        # Claude Code's install record is read under CLAUDE_CONFIG_DIR: the machine's own is never read here
        os.environ["CLAUDE_CONFIG_DIR"] = str(Path(tmp) / "claude")
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
        (root / "vendor" / "sub" / "docs").mkdir(parents=True)  # a submodule: its .git is a file naming the module's repository
        (root / "vendor" / "sub" / ".git").write_text("gitdir: ../../.git/modules/vendor/sub\n", encoding="utf-8")
        (root / "vendor" / "sub" / "docs" / "d.md").write_text("# D\n\n## References\n\nY, Z. (2001). A title.\n", encoding="utf-8")
        (root / "vendor" / "sub" / "lakefile.lean").write_text("import Lake\n", encoding="utf-8")
        (root / "CLAUDE.md").write_text("# Project\n", encoding="utf-8")
        (root / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
        rep = probe(root)
        by = {it["item"]: it for it in rep["project"]}
        expect("a git repository is found at the root", by["git repository"]["ok"] and rep["facts"]["git_root"] == str(root))
        expect("the documents with a References section are reported as globs, node_modules and a submodule skipped",
               rep["facts"]["globs"] == ["notes/*.md", "papers/*.md"] and "papers/*.md (1 file(s))" in by["documents with a References section"]["detail"])
        expect("the Lean workspace is found, and none inside a submodule", rep["facts"]["lake"] == ["formal"] and "formal plugin" in by["Lean workspace"]["detail"])
        expect("the instructions file is found", rep["facts"]["instructions"] == ["CLAUDE.md"] and by["instructions file"]["ok"])
        expect("no log is found and the init's start is proposed", rep["facts"]["logs"] == [] and "flow init --log" in by["log"]["detail"])
        log_line = next(l for l in render(rep).splitlines() if " log [" in l)
        summary = render(rep).splitlines()[-1]
        expect("a log not yet written is absent, marked neither ok nor missing, and not counted among the missing items",
               by["log"]["need"] == "absent" and log_line.lstrip().startswith("--") and " log" not in summary.split(";")[0])
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
        kit = Path(tmp) / "kit"
        here = kit / "plugins" / "research" / "skills" / "research-init" / "scripts"
        here.mkdir(parents=True)
        (kit / "plugins" / "research" / ".claude-plugin").mkdir()
        (kit / "plugins" / "research" / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
        expect("a plugin outside a checkout is laid out as a plugin", layout(here) == ("plugin", str(kit / "plugins" / "research")))
        (kit / ".claude-plugin").mkdir()
        (kit / ".claude-plugin" / "marketplace.json").write_text("{}", encoding="utf-8")
        (kit / ".git").mkdir()
        expect("a plugin in a git clone of the kit is said to be in one, and the report says so",
               layout(here) == ("clone", str(kit)) and "in a git clone of the kit at" in render(dict(rep3, kit=dict(rep3["kit"], layout="clone", path=str(kit)))))
        v = kit_version()
        pins = kit_pins
        expect("with nothing pinned the pins agree", pins(bare, v)["ok"] and "nothing in the project pins" in pins(bare, v)["detail"])
        expect("with no install record the plugins are not compared, and the report says so",
               "install record" in pins(bare, v)["detail"] and "is absent" in pins(bare, v)["detail"])
        (bare / ".pre-commit-config.yaml").write_text(f"repos:\n- repo: https://github.com/lividgreen/research-kit\n  rev: v{v}\n  hooks:\n  - id: flow-check\n", encoding="utf-8")
        (bare / ".claude").mkdir()
        settings = lambda src: (bare / ".claude" / "settings.json").write_text(json.dumps({"extraKnownMarketplaces": {"research-kit": {"source": src}}}), encoding="utf-8")
        settings({"source": "github", "repo": "lividgreen/research-kit", "ref": f"v{v}"})
        expect("the hooks' rev, the marketplace's ref and the plugin's version at one tag agree", pins(bare, v)["ok"])
        settings({"source": "github", "repo": "lividgreen/research-kit"})
        expect("a marketplace with no ref follows the default branch, and the pins do not agree",
               not pins(bare, v)["ok"] and "follows the default branch" in pins(bare, v)["detail"])
        settings({"source": "github", "repo": "lividgreen/research-kit", "ref": f"v{v}"})
        (bare / ".pre-commit-config.yaml").write_text("repos:\n- repo: https://github.com/lividgreen/research-kit\n  rev: v0.0.1\n", encoding="utf-8")
        expect("a hooks' rev at another tag is named", not pins(bare, v)["ok"] and "the hooks' rev differ" in pins(bare, v)["detail"])
        pin = lambda text: hooks_pin(text)
        expect("the hooks' pin is read with a comment after the repo, a comment line before the rev, the rev first, a frozen rev",
               pin("repos:\n- repo: https://github.com/lividgreen/research-kit  # the kit\n  # pinned\n  rev: v0.0.1\n")[1] == "v0.0.1"
               and pin("repos:\n  - rev: 'v0.0.2'\n    repo: https://github.com/lividgreen/research-kit\n    hooks:\n      - id: flow-check\n")[1] == "v0.0.2"
               and pin("repos:\n- repo: https://github.com/lividgreen/research-kit\n  rev: 0123abcd  # frozen: v0.0.3\n")[1] == "v0.0.3"
               and pin("repos:\n- repo: https://github.com/lividgreen/research-kit\n  hooks:\n  - id: flow-check\n- repo: x\n  rev: v9\n") == ("https://github.com/lividgreen/research-kit", None))
        (bare / ".pre-commit-config.yaml").write_text("repos:\n- repo: ../research-kit\n  rev: 0123abcd\n", encoding="utf-8")
        expect("hooks from a local checkout are named and their rev not compared", pins(bare, v)["ok"] and "local repository ../research-kit" in pins(bare, v)["detail"])
        settings({"source": "directory", "path": "/somewhere/research-kit"})
        (bare / ".pre-commit-config.yaml").write_text(f"repos:\n- repo: https://github.com/lividgreen/research-kit\n  rev: v{v}\n", encoding="utf-8")
        expect("a directory marketplace is named as one, not as following the default branch", pins(bare, v)["ok"] and "local directory" in pins(bare, v)["detail"])
        settings({"source": "git", "url": "https://github.com/lividgreen/research-kit.git#v0.0.1"})
        expect("a git url's #ref is read, and one pin off is said in the singular",
               not pins(bare, v)["ok"] and "the marketplace's ref differs from" in pins(bare, v)["detail"])
        mkfile = lambda text: (bare / "Makefile").write_text(text, encoding="utf-8")
        hooked = lambda: next(it for it in project(bare)[0] if it["item"] == "Makefile")["detail"] == "its `check` target runs the hooks"
        for text in ("lint check:\n\tprek run --all-files\n", "check: hooks\nhooks:\n\tpre-commit run --all-files\n",
                     "check: ; prek run --all-files\n", "check:\nifeq ($(CI),1)\n\tprek run --all-files\nendif\n"):
            mkfile(text)
            expect(f"a check target running the hooks is read: {text.splitlines()[0]!r}", hooked())
        mkfile("check:\n\t# prek run --all-files\n\techo nothing\n")
        expect("a commented recipe line does not run the hooks", not hooked())
        mkfile("all:\n\techo\n")
        expect("a Makefile with no check target is told so, with the target proposed",
               "found no `check` target" in next(it for it in project(bare)[0] if it["item"] == "Makefile")["detail"])
        mkfile("check: lint\n\t@echo checking\n\tprek run --all-files\n")
        expect("a Makefile whose check target runs the hooks is read as one",
               next(it for it in project(bare)[0] if it["item"] == "Makefile")["detail"] == "its `check` target runs the hooks")
        for f in (bare / "Makefile", bare / ".pre-commit-config.yaml", bare / ".claude" / "settings.json"):
            f.unlink()
        r = subprocess.run([sys.executable, __file__, "probe", "--root", str(bare), "--json"], capture_output=True, text=True)
        expect("probe --json is one JSON document", r.returncode == 0 and json.loads(r.stdout)["root"] == str(bare))
        expect("probe --json carries the upgrade steps", r.returncode == 0 and [s["item"] for s in json.loads(r.stdout)["upgrade"]["steps"]] == ["pins", "records"])
        installed_scenarios(Path(tmp), v, expect)
        upgrade_scenarios(Path(tmp), v, expect)
        runner_scenarios(Path(tmp), v, expect)
    if saved_config is None:
        os.environ.pop("CLAUDE_CONFIG_DIR", None)
    else:
        os.environ["CLAUDE_CONFIG_DIR"] = saved_config
    print(f"setup selftest: {'OK' if not bad else str(len(bad)) + ' FAILED: ' + '; '.join(bad)}")
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="setup", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sp = ap.add_subparsers(dest="cmd")
    p = sp.add_parser("probe", help="report the project and the machine against the kit's setup")
    p.add_argument("--root", help="the project root (default: the current directory)")
    p.add_argument("--json", action="store_true")
    p = sp.add_parser("runner", help="write the project's runner, which runs a skill's script by its installed path and checks the pins")
    p.add_argument("--root", help="the project root (default: the current directory)")
    p.add_argument("--out", default="scripts/kit.py", help="the runner's path under the root (default: scripts/kit.py)")
    p.add_argument("--force", action="store_true", help="rewrite an existing file")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd not in ("probe", "runner"):
        ap.print_help()
        return 0
    root = Path(a.root).resolve() if a.root else Path(os.getcwd()).resolve()
    if not root.is_dir():
        print(f"setup: {root} is not a directory", file=sys.stderr)
        return 2
    if a.cmd == "runner":
        code, said = write_runner(root, a.out, a.force)
        print(said, file=sys.stderr if code else sys.stdout)
        return code
    rep = probe(root)
    sys.stdout.reconfigure(errors="backslashreplace")  # a file name that is not UTF-8 is shown, not a crash
    print(json.dumps(rep, indent=1) if a.json else render(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
