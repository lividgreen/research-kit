#!/usr/bin/env python3
"""setup — the probe behind the `research-init` skill: what the project and the machine have, and what
the kit's setup needs that is missing.

  setup probe [--root DIR] [--json]   the report the skill's procedure reads
  setup --selftest

The probe writes nothing and installs nothing; it reports, the agent proposes, the person
decides.  It asks GitHub for the kit's latest release, which the pins are held to, and compares
the pins among themselves where it cannot (offline, or RESEARCH_KIT_OFFLINE set).  Standard
library only.
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
import urllib.error
import urllib.request
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
        # read by its lines, comments dropped: a repo naming the kit (or a checkout's path whose hooks are the kit's),
        # or local hooks running the kit's scripts, which carry no rev and which the init leaves as they are
        kind = hooks_kind(text)
        items.append({"item": ".pre-commit-config.yaml", "need": "present", "ok": True,
                      "detail": "names research-kit already" if kind == "kit" else
                      "its hooks are local (`repo: local`) and run the installed plugin's scripts, so they carry no `rev`; the init leaves the file as it is" if kind == "local" else
                      "exists without the kit's hooks; the block is added to it"})
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
# them so) -------------------------------------------------------------------------------------------------

KIT_REPO = "lividgreen/research-kit"
KIT_CHANGELOG = "https://github.com/lividgreen/research-kit/blob/main/CHANGELOG.md"
KIT_LATEST = "https://api.github.com/repos/lividgreen/research-kit/releases/latest"


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


KIT_ENTRY = re.compile(r"\b(?:flow|library|dashboard|formal)\.py\b|\b(?:flow|library|formal)\s+(?:check|cite|anchors|register|index|doctor)\b")


def hooks_kind(text):
    """How a .pre-commit-config.yaml's hooks reach the kit, read from its lines with the comments dropped: "kit"
    where a hook repo names research-kit, or any other repo but `local` carries the kit's hook ids (a checkout's
    path); "local" where a `repo: local` hook's `entry` runs the kit's scripts (`flow.py`, `library.py`,
    `dashboard.py` or `formal.py`, or `flow`, `library` or `formal` with a subcommand), so the installed plugin's
    version runs and no hook carries a `rev`; None where neither."""
    lines = [re.sub(r"(?:^|\s)#.*$", "", l).rstrip() for l in text.split("\n")]
    indent = lambda l: len(l) - len(l.lstrip())
    local = False
    for i, l in enumerate(lines):
        m = re.match(r"\s*(?:-\s+)?repo:\s*['\"]?([^\s'\"]+)", l)
        if not m:
            continue
        s = i  # the item, bounded as hooks_pin bounds it
        while s > 0 and not (re.match(r"\s*-\s", lines[s]) and (s == i or indent(lines[s]) < indent(l))):
            s -= 1
        d, e = indent(lines[s]), s + 1
        while e < len(lines) and not (lines[e].strip() and indent(lines[e]) <= d):
            e += 1
        item = lines[s:e]
        if m.group(1) == "local":
            entries = [re.match(r"\s*(?:-\s+)?entry:\s*(.*)", x) for x in item]
            local = local or any(r and KIT_ENTRY.search(r.group(1)) for r in entries)
        elif "research-kit" in m.group(1) or any(re.match(r"\s*(?:-\s+)?id:\s*['\"]?(?:flow|library|formal)-(?:check|cite|anchors|register)\b", x) for x in item):
            return "kit"
    return "local" if local else None


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


def kit_latest():
    """The tag of the kit's latest release, asked of GitHub's API (`tag_name`, 5 s at most): (tag, None), or
    (None, why) where it could not be read — offline, a refusal, an answer naming no release tag, or
    `RESEARCH_KIT_OFFLINE` set, which skips the request (the kit's tests set it)."""
    if os.environ.get("RESEARCH_KIT_OFFLINE", "") not in ("", "0"):
        return None, "RESEARCH_KIT_OFFLINE is set"
    req = urllib.request.Request(KIT_LATEST, headers={"Accept": "application/vnd.github+json", "User-Agent": "research-kit-probe"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            tag = json.loads(r.read().decode("utf-8")).get("tag_name")
    except Exception as e:  # no network, a timeout, an HTTP refusal (a rate limit), an answer that is no JSON object
        why = e.reason if type(e) is urllib.error.URLError else e
        return None, str(why) or type(e).__name__
    return (tag, None) if kit_tag(tag) else (None, f"the latest release names no release tag ({tag!r})")


def kit_pins(root, version, record=None, latest=None):
    """The places a project pins the kit — the hooks' `rev`, the Claude Code marketplace's `ref` in the project's
    settings, the version of each plugin of the marketplace Claude Code installed for the project (`record`, the
    install record, defaults to Claude Code's) — beside the version of the plugin this script runs from (None for
    a script outside the kit), held to the kit's latest release (`latest`, a callable answering (tag, why),
    defaults to `kit_latest`), or, where that could not be read, to the newest of them: whether every pin is at
    that tag and, where one is not, the steps that move every pin to it and the releases whose upgrading
    paragraphs lie between.  It writes nothing."""
    root = Path(root).resolve()
    record = Path(record) if record else install_record()
    newest, unread = (latest or kit_latest)()
    said, tags = [f"the latest release is {newest}" if newest else
                  f"the latest release could not be read ({unread}), so the pins are compared among themselves"], {}
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
    if not repo:
        said.append("no hook pins the kit by `rev`" + ("; the hooks are local and run the installed plugin's scripts, so they follow the plugins' pins"
                                                      if hooks_kind(pc) == "local" else ""))
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
        said.insert(1, f"the plugin this runs from is v{version}")
        tags["the plugin this runs from"] = f"v{version}"
    ordered = all(kit_tag(t) for t in tags.values())
    target = newest or ((max(tags.values(), key=kit_tag) if ordered else tags.get("the hooks' rev") or next(iter(tags.values()))) if tags else None)
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
        oldest = min((t for t in tags.values() if kit_tag(t)), key=kit_tag, default=None)
        if oldest and kit_tag(T) and kit_tag(oldest) < kit_tag(T):
            releases = f"read the Upgrading paragraph of each release after {oldest} up to {T}, in {KIT_CHANGELOG}"
    named = off[0] if len(off) == 1 else ", ".join(off[:-1]) + " and " + off[-1] if off else ""
    which = ", the latest release" if newest else ", the newest of them" if ordered and len(tags) > 1 else ""
    detail = "; ".join(said) + (f" — {named} {'differ' if len(off) > 1 else 'differs'} from {T}{which}: move every pin to it" if off else "")
    return {"item": "pins at one tag", "need": "recommended", "ok": not off, "detail": detail, "target": target,
            "latest": newest, "latest_unread": unread, "commands": steps, "releases": releases}


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
    latest = ", the latest release" if pins["latest"] else ""
    unread = "" if pins["latest"] else "; the latest release could not be read, so this is the newest the pins name"
    steps = [{"item": "pins", "state": "ok" if pins["ok"] else "pending",
              "detail": f"at one tag, {pins['target']}{latest or unread}" if pins["ok"] and pins["target"] else "nothing pins the kit yet" if pins["ok"] else
              f"every pin moves to {pins['target'] or '<tag>'}{latest}, in the order of the steps below",
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
    lines += ["", f"kit: version {k['version'] or 'UNKNOWN'} (release tag {k['tag'] or '<tag>'}), {where}"]
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
              + "; the probe read the root, PATH" + (" and GitHub's latest release" if any(it.get("latest") for it in rep["project"]) else "") + " and wrote nothing"]
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


def latest_scenarios(tmp, v, expect):
    """The pins held to the latest release, the request answered by stand-ins: never the network."""
    p = tmp / "latest"
    p.mkdir()
    kit_hooks(p, f"v{v}")
    kit_settings(p, f"v{v}")
    rec = tmp / "latest_plugins.json"
    rec.write_text(json.dumps({"version": 2, "plugins": {"research@research-kit": [
        {"scope": "project", "projectPath": str(p), "installPath": str(tmp / "cache" / v), "version": v}]}}), encoding="utf-8")
    r = kit_pins(p, v, rec, latest=lambda: ("v99.0.0", None))
    expect("a latest release newer than every pin moves every pin to it, with the releases between to read",
           not r["ok"] and r["target"] == "v99.0.0" and r["latest"] == "v99.0.0" and r["detail"].startswith("the latest release is v99.0.0;")
           and "from v99.0.0, the latest release: move every pin to it" in r["detail"]
           and [c.split(" ")[0] for c in r["commands"]] == ["edit", "claude", "claude", "set", "move", "restart"]
           and f"claude plugin marketplace add '{KIT_REPO}#v99.0.0' --scope project" in r["commands"]
           and f"after v{v} up to v99.0.0" in str(r["releases"]), f"{r['detail']} {r['commands']} {r['releases']}")
    s = {x["item"]: x for x in upgrade(p, r)}
    expect("the upgrade's pins step names the latest release", s["pins"]["state"] == "pending" and "moves to v99.0.0, the latest release" in s["pins"]["detail"])
    r = kit_pins(p, v, rec, latest=lambda: (f"v{v}", None))
    expect("pins agreeing at the latest release are ok", r["ok"] and r["target"] == f"v{v}" and r["detail"].startswith(f"the latest release is v{v};"), r["detail"])
    expect("the upgrade's pins step says the pins are at the latest release", upgrade(p, r)[0]["detail"] == f"at one tag, v{v}, the latest release")
    kit_hooks(p, "v0.0.1")
    r = kit_pins(p, v, rec, latest=lambda: (None, "no network"))
    expect("where the latest release could not be read the pins are compared among themselves, against the newest of them, and it is said so",
           not r["ok"] and r["target"] == f"v{v}" and r["latest"] is None and r["latest_unread"] == "no network"
           and r["detail"].startswith("the latest release could not be read (no network), so the pins are compared among themselves;")
           and f"the hooks' rev differs from v{v}, the newest of them" in r["detail"], r["detail"])
    kit_hooks(p, f"v{v}")
    expect("pins at one tag where the latest release could not be read say so in the upgrade step",
           "could not be read" in upgrade(p, kit_pins(p, v, rec, latest=lambda: (None, "no network")))[0]["detail"])
    # kit_latest itself, its request answered by stand-ins for urlopen
    saved_env, saved_open = os.environ.pop("RESEARCH_KIT_OFFLINE", None), urllib.request.urlopen
    asked = []

    class Answer:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self.body

    def answering(body=None, error=None):
        def fake(req, timeout=None):
            asked.append((req.full_url, req.get_header("User-agent"), timeout))
            if error:
                raise error
            return Answer(body)
        return fake
    try:
        urllib.request.urlopen = answering(b'{"tag_name": "v1.2.3", "name": "v1.2.3"}')
        expect("the latest release is read from GitHub's API, its tag_name, with a generic User-Agent and a short timeout",
               kit_latest() == ("v1.2.3", None) and asked == [(KIT_LATEST, "research-kit-probe", 5)], str(asked))
        urllib.request.urlopen = answering(error=urllib.error.URLError("[Errno -3] Temporary failure in name resolution"))
        expect("no network is said by its reason", kit_latest() == (None, "[Errno -3] Temporary failure in name resolution"))
        urllib.request.urlopen = answering(error=urllib.error.HTTPError(KIT_LATEST, 403, "rate limit exceeded", {}, None))
        expect("an HTTP refusal is said with its code", kit_latest()[1] == "HTTP Error 403: rate limit exceeded")
        urllib.request.urlopen = answering(b'{"message": "Not Found"}')
        expect("an answer naming no release tag is no latest release", kit_latest() == (None, "the latest release names no release tag (None)"))
        urllib.request.urlopen = answering(b"<html>")
        expect("an answer that is no JSON is no latest release", kit_latest()[0] is None)
        os.environ["RESEARCH_KIT_OFFLINE"] = "1"
        asked.clear()
        expect("RESEARCH_KIT_OFFLINE skips the request", kit_latest() == (None, "RESEARCH_KIT_OFFLINE is set") and asked == [])
    finally:
        urllib.request.urlopen = saved_open
        os.environ["RESEARCH_KIT_OFFLINE"] = saved_env or "1"


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


def selftest():
    bad = []

    def expect(name, cond, detail=""):
        print(f"  {'ok ' if cond else 'BAD'} {name}" + (f" — {detail}" if detail and not cond else ""))
        if not cond:
            bad.append(name)

    saved = {k: os.environ.get(k) for k in ("CLAUDE_CONFIG_DIR", "RESEARCH_KIT_OFFLINE")}
    with tempfile.TemporaryDirectory() as tmp:
        # Claude Code's install record is read under CLAUDE_CONFIG_DIR: the machine's own is never read here;
        # and the latest release is never asked of the network, here or in a script this runs
        os.environ["CLAUDE_CONFIG_DIR"] = str(Path(tmp) / "claude")
        os.environ["RESEARCH_KIT_OFFLINE"] = "1"
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
        pcdetail = lambda text: ((root / ".pre-commit-config.yaml").write_text(text, encoding="utf-8"),
                                 next(it for it in project(root)[0] if it["item"] == ".pre-commit-config.yaml")["detail"])[1]
        expect("a pre-commit config that only mentions research-kit in a comment is not the kit's",
               "without the kit's hooks" in pcdetail("# the hooks of research-kit go below\nrepos:\n- repo: https://example.org/x  # not research-kit\n  rev: v1\n  hooks:\n  - id: x\n"))
        local = "repos:\n- repo: local\n  hooks:\n  - id: flow-check\n    name: flow check\n    language: system\n    entry: scripts/kit.py flow check\n    pass_filenames: false\n"
        expect("local hooks running the kit's scripts through a runner are reported as local, with no rev, and left as they are",
               "hooks are local" in pcdetail(local) and "no `rev`" in pcdetail(local) and "leaves the file as it is" in pcdetail(local)
               and "hooks are local" in pcdetail(local.replace("scripts/kit.py flow check", "python3 tools/run.py library.py check")))
        expect("local hooks that run something else are not the kit's", "without the kit's hooks" in pcdetail(local.replace("scripts/kit.py flow check", "make lint")))
        expect("a remote repo naming the kit, and a checkout's path with the kit's hook ids, are named as before",
               pcdetail("repos:\n- repo: https://github.com/lividgreen/research-kit\n  rev: v1\n") == "names research-kit already"
               and pcdetail("repos:\n- repo: ../kit\n  rev: 0123abcd\n  hooks:\n  - id: library-check\n") == "names research-kit already")
        (root / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
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
        (bare / ".pre-commit-config.yaml").write_text("repos:\n- repo: local\n  hooks:\n  - id: flow-check\n    language: system\n    entry: scripts/kit.py flow check\n", encoding="utf-8")
        expect("local hooks running the kit's scripts are said to carry no rev and to follow the plugins' pins, and `repo: local` is no local repository",
               pins(bare, v)["ok"] and "no hook pins the kit by `rev`; the hooks are local and run the installed plugin's scripts, so they follow the plugins' pins" in pins(bare, v)["detail"]
               and "local repository" not in pins(bare, v)["detail"] and "the hooks' rev" not in pins(bare, v)["detail"], pins(bare, v)["detail"])
        (bare / ".pre-commit-config.yaml").write_text("# research-kit\nrepos: []\n", encoding="utf-8")
        expect("a config naming the kit only in a comment pins nothing, and claims no local hooks",
               "no hook pins the kit by `rev`" in pins(bare, v)["detail"] and "hooks are local" not in pins(bare, v)["detail"])
        (bare / ".pre-commit-config.yaml").write_text(f"repos:\n- repo: https://github.com/lividgreen/research-kit\n  rev: v{v}\n", encoding="utf-8")
        expect("a hooks' rev is stated and no rev-less claim made", f"the hooks pin rev v{v}" in pins(bare, v)["detail"] and "no hook pins" not in pins(bare, v)["detail"])
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
        latest_scenarios(Path(tmp), v, expect)
    for k, was in saved.items():
        if was is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = was
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
