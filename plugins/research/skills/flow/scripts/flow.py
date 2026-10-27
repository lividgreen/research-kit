#!/usr/bin/env python3
"""flow — the CLI, validator and index for a typed flow of work.

Records live as one Markdown file each, front matter plus a prose body, under the
directory `flow.toml` names.  Four kinds:

  idea      a raw signal; open | consumed | abandoned
  task      a unit of work; ready | active | done | abandoned  (closed tasks move to the archive)
  question  a precisely stated question or conjecture; open | decomposed | answered | abandoned
  finding   a CHECKABLE claim: its evidence resolves against a declaration manifest, a
            document's numbered statement or table row, or a self-asserting probe

Transitions (the only writers of state and provenance):

  flow capture SUMMARY [--source S] [--tag T]... [--body FILE]
  flow task SUMMARY --kind K [--question Q] [--size s] [--dod D] [--source S] [--tag T]...
             [--body FILE]                                     a standalone task; without --question
                                                               only a question-optional kind
  flow frame ID... --summary S --kill K [--size s] [--kind question|conjecture] [--parent Q]
             [--direction D] [--tag T]... [--body FILE]        ideas -> consumed, or one finding
  flow refine Q --task SUMMARY [KIND] ... [--subq SUMMARY KILL]... [--idea SUMMARY]...
             [--kind K] [--size s] [--dod D] [--requires F]... [--body FILE]
                                                               Q -> decomposed, tasks ready
  flow draw T --owner O          ready -> active (hand limit from flow.toml)
  flow return T [--note N]       active -> ready
  flow make T [--finding SUMMARY STATUS EVIDENCE...]... [--paper P] [--depends-on F]...
             [--task SUMMARY [KIND]]... [--question SUMMARY KILL]... [--idea SUMMARY]...
             [--resolution FILE]                              active -> done, archived
  flow abort T --reason R [--resolution FILE] [--finding SUMMARY refuted EVIDENCE...] [--paper P]
  flow answer Q --by F [--by F]  open|decomposed -> answered (F a finding, or a done task drawn under Q)
  flow kill ID --reason R        idea | question(open|decomposed) | task(ready) -> abandoned
  flow park Q --reason R [--revival V]      an open question gains a parked block
  flow unpark Q [--note N]
  flow rank ID N [--insert] [--why W] [--first-move M] [--direction D]   |  rank --set ID...  |  rank ID --clear
  flow checked ID...             refresh the last-checked date
  flow set ID FIELD VALUE        one hand-editable field: summary, kill (question), size,
                                 dod (task), rider on|off (ready or active task),
                                 depends_on "F F…"|none (finding; a cycle is refused)

Views: find, show, graph, state (the cold-start bundle), directions, index [--check | --print], check;
`pages` (the dashboard's page manifest); `--json` on every command.

  flow state --check --owner O   a session's close, as far as a machine sees it: the inbox empty, every
                                 active task in O's hand, the log's top entry today's where the tree changed
                                 since the newest committed entry, every record changed since then named
  flow log add FILE              one entry at the top of the log, reflowed and linted as a record is
  flow log archive --before DATE the older entries moved verbatim, one file per month, into `[paths] log_archive`
  flow reflow --check PATH...    the lines of the project's other prose that are not one sentence per line
  flow reflow --as DEST DRAFT    a draft checked as if appended to DEST: the reflow, then markdownlint
`flow init [--records DIR] [--log FILE] [--owner O]... [--force]` writes a project's `flow.toml` and its
directories, and prints the paragraph the project's instructions should carry.
A referred work is not a record: it is a card in the reference library the project binds
(`[library] command` in `flow.toml`).  A record cites one by the library's cite prefix and the
card's key, and `check` asks the library whether each cited key exists and how it was read.
Exit 0 applied / 1 refused or a violation / 2 could not run.  `--selftest` builds a
temporary tree, runs the happy path and then plants one defect per invariant.

Standard library only (Python 3.11 or later).  Front matter is the YAML subset this file reads
and writes itself — `field: scalar`, a block list of scalars, a one-level block map, scalars
plain or quoted as PyYAML writes them — so a record written by an older PyYAML build reads back.
Bodies are reflowed to one sentence per line through the project's reflow module when
`flow.toml` names one (a built-in splitter otherwise), and every write is followed by a
markdownlint delta check when markdownlint is on PATH: a NEW violation reverts the write.
The index is a pure function of the records; `check` fails when the committed copy drifts.
"""

import argparse
import contextlib
import datetime as dt
import difflib
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import traceback
from collections import Counter, defaultdict
from pathlib import Path

TYPES = ("idea", "question", "task", "finding")
STATES = {
    "idea": ("open", "consumed", "abandoned"),
    "question": ("open", "decomposed", "answered", "abandoned"),
    "task": ("ready", "active", "done", "abandoned"),
    "finding": (),
}
CLOSED_TASK = ("done", "abandoned")
SCHEMA = {
    "idea": ("id", "type", "state", "summary", "source", "consumed_by", "abandoned",
             "origin", "created", "tags"),
    "question": ("id", "type", "kind", "state", "summary", "derived_from", "parent", "size",
                 "kill", "checked", "parked", "rank", "why_now", "first_move", "direction",
                 "answered_by", "abandoned", "origin", "source", "created", "tags"),
    "task": ("id", "type", "kind", "state", "summary", "question", "derived_from", "requires",
             "size", "owner", "drawn", "dod", "rank", "why_now", "first_move", "rider",
             "abandoned", "origin", "source", "created", "tags"),
    "finding": ("id", "type", "summary", "status", "evidence", "derived_from", "question",
                "depends_on", "paper", "origin", "source", "created", "tags"),
}
LIST_FIELDS = ("derived_from", "requires", "evidence", "depends_on", "answered_by", "tags")
CLI_ONLY = ("id", "type", "state", "derived_from", "consumed_by", "owner", "drawn",
            "answered_by", "rank", "parked", "abandoned", "question", "origin", "created")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FENCE = "---"


class Refused(Exception):
    pass


class NotRun(Refused):
    """A check that could not run — a file it was given is missing, an owner not named — exits 2, never 1."""


# --- configuration -----------------------------------------------------------

def find_root(start):
    p = Path(start).resolve()
    for cand in (p, *p.parents):
        if (cand / "flow.toml").is_file():
            return cand
    raise Refused(f"no flow.toml found above {start}")


def find_library(root):
    """The library command when flow.toml binds none: the library skill installed beside this one,
    else `library` on PATH (the hooks' environment, where no skill stands beside), either only where
    a library.toml stands at the root.  Returns the command and the words the coverage line says."""
    if not (root / "library.toml").is_file():
        return [], "no library.toml at the root"
    sibling = Path(__file__).resolve().parent.parent.parent / "library" / "scripts" / "library.py"
    if sibling.is_file():
        return [sys.executable, str(sibling)], "the library skill beside this one"
    on_path = shutil.which("library")
    if on_path:
        return [on_path], "the library command on PATH"
    return [], "library.toml at the root but no library skill beside this one or command on PATH"


class Config:
    def __init__(self, root):
        self.root = Path(root)
        if not (self.root / "flow.toml").is_file():
            raise Refused(f"no flow.toml at {self.root}")
        try:
            raw = tomllib.loads((self.root / "flow.toml").read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
            raise Refused(f"{self.root / 'flow.toml'} does not parse: {e}")
        paths = raw.get("paths", {})
        self.kinds = TYPES
        rec_dir = paths.get("records", "records")
        self.research = self.root / rec_dir
        self.records_name = rec_dir
        self.index = self.root / paths.get("index", f"{rec_dir}/INDEX.md")
        self.archive = self.root / paths.get("archive", f"{rec_dir}/archive")
        if not self.archive.resolve().is_relative_to(self.research.resolve()):
            raise Refused(f"flow.toml: [paths] archive {paths.get('archive')!r} is not under the records directory "
                          f"{rec_dir!r}, where the records are read and their ids counted")
        self.directions = self.root / paths.get("directions", f"{rec_dir}/directions.md")
        self.log = self.root / paths["log"] if paths.get("log") else None
        # where `flow log archive` moves the log's old entries, one file per month: beside the log unless bound
        self.log_archive = self.root / paths["log_archive"] if paths.get("log_archive") else \
            self.log.with_name(self.log.stem + "-archive") if self.log else None
        self.reflow_module = paths.get("reflow_module")
        self.mdlint_config = paths.get("markdownlint_config")
        # Evidence resolvers ([evidence]).  The manifest lists declaration names, one per line, as
        # `Module.Path name`; it may be one file or a list, and every directory evidence paths are
        # looked up under (the first that holds the file wins).  A prover library's declaration
        # list is the instance.
        ev = raw.get("evidence", {})
        lm = ev.get("manifest")
        self.manifests = [lm] if isinstance(lm, str) else list(lm or [])
        self.manifest = ", ".join(self.manifests) or None
        lr = ev.get("manifest_roots", ".")
        self.manifest_roots = [lr] if isinstance(lr, str) else list(lr)
        self.manifest_root = " or ".join(self.manifest_roots)
        # The file extension declaration evidence carries (`Path.ext#name`): named beside the
        # manifest, since the kit knows no prover.  With no manifest bound any extension but a
        # document's or a probe's is read as one.
        ext = ev.get("manifest_extension")
        if self.manifests and ext is None:
            raise Refused("flow.toml: [evidence] manifest_extension is required beside manifest "
                          "(the file extension of the paths declaration evidence cites, e.g. \"lean\")")
        self.decl_ext = str(ext).lstrip(".") if ext else None
        ext_rx = re.escape(self.decl_ext) if self.decl_ext else r"(?!(?:md|py)(?:#|$))[A-Za-z0-9]+"
        self.probes = ev.get("probes")
        self.ev_decl = re.compile(r"^([A-Za-z0-9_/]+\.(?:%s))#([A-Za-z0-9_.'!?]+)$" % ext_rx)
        self.ev_declfile = re.compile(r"^([A-Za-z0-9_/]+\.(?:%s))$" % ext_rx)
        pre = raw.get("prefixes", {})
        self.prefix = {t: pre.get(t, t) for t in TYPES}
        self.id_width = int(pre.get("id_width", 4))
        self.hand = raw.get("hand", {})
        self.owners = tuple(self.hand.keys()) or ("agent",)
        task = raw.get("task", {})
        self.task_kinds = tuple(task.get("kinds", ("work", "design", "prose", "survey",
                                                   "upkeep", "community", "decision")))
        self.default_kind = task.get("default_kind", self.task_kinds[0])
        self.q_optional = tuple(task.get("question_optional_kinds", ("upkeep", "community", "decision")))
        # Owner-only work: a task of these kinds, or held by these owners, is never ranked —
        # it is what only the owner can do or should decide.
        self.decision_kinds = tuple(task.get("decision_kinds", ("decision",)))
        self.decision_owners = tuple(task.get("decision_owners", ()))
        if any(o not in self.owners for o in self.decision_owners):
            raise Refused(f"flow.toml: decision_owners {self.decision_owners} must be owners listed under [hand] {self.owners}")
        self.sizes = tuple(raw.get("question", {}).get("sizes", ("small", "medium", "large")))
        fnd = raw.get("finding", {})
        # A finding's status is one of four roles, named by the project: verified (a declaration
        # in the manifest), stated (a document's statement or row, no declaration), empirical (a
        # probe, no declaration), refuted (a guard declaration or a probe).  An older `statuses`
        # list names the four in that order.
        legacy = list(fnd.get("statuses", ()))
        self.role_name = {}
        for i, role in enumerate(("verified", "stated", "empirical", "refuted")):
            self.role_name[role] = str(fnd.get(role, legacy[i] if i < len(legacy) else role))
        self.statuses = tuple(self.role_name.values())
        self.role_of = {v: k for k, v in self.role_name.items()}
        self.shards = tuple(fnd.get("shards", ()))
        # The reference library, when the project has one: the command that answers `keys`
        # with its cite prefix and every card's state and grade.  The flow knows no more of it.
        lib_cmd = raw.get("library", {}).get("command")
        if lib_cmd is None:
            self.library_cmd, self.library_route = find_library(self.root)
        else:
            self.library_cmd = [lib_cmd] if isinstance(lib_cmd, str) else list(lib_cmd)
            self.library_route = "flow.toml's [library] command" if self.library_cmd else "disabled in flow.toml"
        idx = raw.get("index", {})
        self.recent_findings = int(idx.get("recent_findings", 10))
        self.oldest_ideas = int(idx.get("oldest_ideas", 5))
        # any run of digits: the records written before `id_width` was widened keep their narrower ids
        self.id_re = re.compile(r"^(%s)-(\d+)(?:-[a-z0-9-]+)?\.md$" % "|".join(re.escape(self.prefix[t]) for t in TYPES))
        self.type_of_prefix = {self.prefix[t]: t for t in TYPES}
        self._reflow = None
        self._manifest = None

    def has(self, type_):
        return type_ in self.kinds

    def dir_of(self, type_, paper=None):
        if type_ == "finding":
            return self.research / "findings" / paper if paper in self.shards else self.research / "findings"
        return self.research / (type_ + "s")

    # the project's reflow module, else the built-in splitter
    def reflow(self, text):
        if self._reflow is None:
            fn = None
            if self.reflow_module and (self.root / self.reflow_module).is_file():
                spec = importlib.util.spec_from_file_location("_reflow", self.root / self.reflow_module)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                fn = getattr(mod, "reflow_text", None)
            self._reflow = fn or _builtin_reflow
        return self._reflow(text)

    @property
    def reflow_source(self):
        return self.reflow_module if self.reflow_module and (self.root / self.reflow_module).is_file() else "built-in"

    def manifest_names(self):
        """Declaration names in the manifest (bare and qualified), or None when absent."""
        if self._manifest is None:
            files = [self.root / m for m in self.manifests]
            if not files or not all(f.is_file() for f in files):
                self._manifest = False
            else:
                names, modules, in_module = set(), set(), defaultdict(set)
                for line in (ln for f in files for ln in f.read_text(encoding="utf-8").splitlines()):
                    t = MANIFEST_FIELD.findall(line)  # a «…» name may hold spaces
                    if not t or t[0].startswith("#") or t[0] == "hypothesis":
                        continue
                    if len(t) < (3 if t[0] in ("private", "field", "instance") else 2):
                        continue
                    if t[0] == "module":
                        modules.add(t[1])
                        continue
                    module, name = t[1:3] if t[0] in ("private", "field", "instance") else t[:2]
                    parts = name.split(".")
                    for k in range(len(parts)):  # every dotted suffix resolves, as a module-scoped lookup
                        names.add(".".join(parts[k:]))
                        in_module[module].add(".".join(parts[k:]))
                self._manifest = names
                self._modules = modules
                self._in_module = in_module
        return None if self._manifest is False else self._manifest

    def manifest_modules(self):
        self.manifest_names()
        return None if self._manifest is False else self._modules


MANIFEST_FIELD = re.compile(r"(?:«[^»]*»|[^\s«])+")
_SENT = re.compile(r"([.?!])([\"”’')\]*`]*)[ \t]+(?=[A-Z0-9*`(\[“\"§_])")
FENCE_RUN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def fence_after(fence, line):
    """The code fence open after `line`, by CommonMark's rule, given `fence`, the one open before it (its opening
    run of backticks or tildes, or None): a fence closes only on a run of its own character at least as long,
    with nothing after it."""
    m = FENCE_RUN.match(line)
    if fence is None:
        return m.group(1) if m and not (m.group(1)[0] == "`" and "`" in m.group(2)) else None
    return None if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip() else fence


def _builtin_reflow(text):
    out, fence = [], None
    for line in text.split("\n"):
        was, fence = fence, fence_after(fence, line)
        if was or fence or not line.strip() or line.lstrip().startswith(("#", "|", ">")) or line.startswith("    "):
            out.append(line)
            continue
        m = re.match(r"^( *)([-*+] |\d+[.)] )?", line)
        indent, marker = m.group(1), m.group(2) or ""
        body, cont = line[m.end():], indent + " " * len(marker)
        parts, start = [], 0
        for b in _SENT.finditer(body):
            if body.count("`", 0, b.start()) % 2 == 1 or re.match(r"^(?:[-*+](?:[ \t]|$)|\d+[.)](?:[ \t]|$)|#|>|\|)", body[b.end():]) \
                    or re.fullmatch(r"(\*\*|__)(?:[^*_\s]+ ){0,3}[^*_\s]+(?: \([^()]*\))?\.\1", body[start:b.end(2)].strip()):  # a label, **State.**, **Lemma 2 (Jen 1990).**
                continue
            parts.append(body[start:b.end(2)].strip())
            start = b.end()
        parts.append(body[start:].strip())
        parts = [p for p in parts if p]
        if len(parts) < 2:  # a line not split is left as written, a hard break's two trailing spaces with it
            out.append(line)
            continue
        out.append(indent + marker + parts[0])
        out += [cont + p for p in parts[1:]]
        if line.endswith("  "):  # a hard break's two trailing spaces stay where the line ends
            out[-1] += "  "
    return "\n".join(out)


# --- front matter: a YAML subset, read and written here -------------------------------
#
# What a record carries: `field: scalar`, a block list of scalars, a one-level block map.
# Scalars are read as PyYAML writes them (plain, 'single-quoted' with '' doubled, "double-quoted",
# null, true/false, integers) and written back in the same style, so a tree written by an
# older PyYAML build round-trips and a diff shows the field that changed, not the quoting.

_PLAIN_FORBID = re.compile(r"^[-?:,\[\]{}#&*!|>'\"%@`\s]|: | #|:$|\s$|[\x00-\x1f]")
_LOOKS_TYPED = re.compile(r"^(?:[-+]?(?:\d[\d_]*|0x[0-9a-fA-F_]+|0o?[0-7_]+|0b[01_]+)|[-+]?(?:\d[\d_]*)?\.\d+(?:[eE][-+]?\d+)?"
                          r"|[-+]?\d[\d_]*[eE][-+]?\d+|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN)|\d{4}-\d{1,2}-\d{1,2}(?:[Tt ].*)?"
                          r"|\d[\d_]*(?::[0-5]?\d)+(?:\.\d*)?|[-+]?[0-9][0-9_]*:[0-5]?[0-9](?::[0-5]?[0-9])*)$")
_KEYWORDS = {"null", "~", "true", "false", "yes", "no", "on", "off", "y", "n"}


def scalar(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    sv = str(v)
    if sv == "":
        return "''"
    if not _PLAIN_FORBID.search(sv) and not _LOOKS_TYPED.match(sv) and sv.lower() not in _KEYWORDS and "\n" not in sv:
        return sv
    if "\n" in sv or re.search(r"[\x00-\x1f\x7f]", sv):
        return json.dumps(sv, ensure_ascii=False)
    return "'" + sv.replace("'", "''") + "'"


def _unescape_double(s, where):
    try:
        v = json.loads(s)
    except ValueError:
        v = None
    if isinstance(v, str):
        return v
    # PyYAML's double-quoted escapes that JSON does not take
    body = s[1:-1]
    out, i = [], 0
    simple = {"0": "\0", "a": "\a", "b": "\b", "t": "\t", "n": "\n", "v": "\v", "f": "\f", "r": "\r",
              "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\", "N": "\u0085", "_": "\u00a0",
              "L": "\u2028", "P": "\u2029", "'": "'"}
    while i < len(body):
        c = body[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        i += 1
        if i >= len(body):
            raise Refused(f"{where}: bad escape")
        c = body[i]
        if c in simple:
            out.append(simple[c])
            i += 1
        elif c in "xuU":
            n = {"x": 2, "u": 4, "U": 8}[c]
            digits = body[i + 1:i + 1 + n]
            if not re.fullmatch(r"[0-9A-Fa-f]{%d}" % n, digits) or int(digits, 16) > 0x10FFFF:
                raise Refused(f"{where}: bad escape \\{c}{digits}")
            out.append(chr(int(digits, 16)))
            i += 1 + n
        else:
            raise Refused(f"{where}: bad escape \\{c}")
    return "".join(out)


def unscalar(s, where):
    s = s.strip()
    if s in ("null", "~", ""):
        return None
    if s == "true":
        return True
    if s == "false":
        return False
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if s.startswith('"'):
        if not s.endswith('"') or len(s) < 2:
            raise Refused(f"{where}: unterminated double-quoted string")
        return _unescape_double(s, where)
    if s.startswith("'"):
        if not s.endswith("'") or len(s) < 2 or not re.fullmatch(r"'(?:[^']|'')*'", s):
            raise Refused(f"{where}: unterminated single-quoted string")
        return s[1:-1].replace("''", "'")
    if s.startswith(("[", "{")):
        if s in ("[]", "{}"):
            return [] if s == "[]" else {}
        raise Refused(f"{where}: a flow collection is not written here; use the block form")
    return s


def _continued(lines, i, indent):
    """The lines from i on that continue a scalar begun on the line before (PyYAML folds a long
    value at 80 columns): every line indented past `indent` columns, with the blank lines between."""
    more, pad = [], " " * (indent + 1)
    while i < len(lines):
        if not lines[i].strip():
            k = i
            while k < len(lines) and not lines[k].strip():
                k += 1
            if k == len(lines) or not lines[k].startswith(pad):
                break
            more += [""] * (k - i)
            i = k
        elif lines[i].startswith(pad):
            more.append(lines[i])
            i += 1
        else:
            break
    return more, i


def _fold(first, more):
    """A scalar continued on the next lines, folded as YAML folds it: a line break is a space, each
    blank line a newline, and a break escaped in a double-quoted scalar joins with nothing."""
    out, blanks = first.rstrip(), 0
    for seg in more:
        seg = seg.strip()
        if not seg:
            blanks += 1
            continue
        if blanks:
            out += "\n" * blanks
        elif first.lstrip().startswith('"') and (len(out) - len(out.rstrip("\\"))) % 2:
            out = out[:-1]
        else:
            out += " "
        out, blanks = out + seg, 0
    return out


def dump_front(fm):
    out = []
    for k, v in fm.items():
        if isinstance(v, list):
            out += [f"{k}:"] + [f"- {scalar(x)}" for x in v] if v else [f"{k}: []"]
        elif isinstance(v, dict):
            out += [f"{k}:"] + [f"  {sk}: {scalar(sv)}" for sk, sv in v.items()] if v else [f"{k}: {{}}"]
        else:
            out.append(f"{k}: {scalar(v)}")
    return "\n".join(out)


def load_front(text, name):
    fm, lines, i = {}, text.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):(?: (.*))?$", line)
        if not m:
            raise Refused(f"{name}: front matter line {i + 2} is not `field: value`")
        k, rest = m.group(1), (m.group(2) or "").strip()
        if k in fm:
            raise Refused(f"{name}: field {k} twice")
        i += 1
        if rest.startswith("'") and not re.fullmatch(r"'(?:[^']|'')*'", rest):
            # a single-quoted scalar continued on the next lines: a line break folds to a space
            # and a blank line to a newline, as YAML folds it
            parts = [rest]
            while i < len(lines):
                if len(parts) == 1 and re.fullmatch(r"(?:[^']|'')*'", parts[-1]):
                    break
                if len(parts) > 1 and parts[-1] != "" and re.search(r"(?<!')'(?:'')*$", parts[-1]):
                    break
                parts.append(lines[i].strip())
                i += 1
                if re.fullmatch(r"(?:[^']|'')*'", parts[-1]) and parts[-1] != "":
                    break
            folded, buf = [], []
            for seg in parts:
                if seg == "":
                    folded.append(" ".join(buf))
                    buf = []
                else:
                    buf.append(seg)
            folded.append(" ".join(buf))
            text_ = "\n".join(folded)
            if not re.search(r"(?<!')'(?:'')*$", text_):
                raise Refused(f"{name}: the single-quoted value of {k} never closes")
            fm[k] = unscalar(text_, f"{name}: {k}")
            continue
        if rest:
            more, i = _continued(lines, i, 0)
            fm[k] = unscalar(_fold(rest, more), f"{name}: {k}")
            continue
        items, sub = [], {}
        while i < len(lines) and lines[i].startswith(("- ", "  ")):
            if lines[i].startswith("- "):
                more, j = _continued(lines, i + 1, 1)
                items.append(unscalar(_fold(lines[i][2:], more), f"{name}: {k}"))
            else:
                sm = re.match(r"^  ([A-Za-z_][A-Za-z0-9_]*):(?: (.*))?$", lines[i])
                if not sm:
                    raise Refused(f"{name}: front matter line {i + 2} is not `  field: value`")
                more, j = _continued(lines, i + 1, 2)
                sub[sm.group(1)] = unscalar(_fold(sm.group(2) or "", more), f"{name}: {k}.{sm.group(1)}")
            i = j
        if items and sub:
            raise Refused(f"{name}: field {k} mixes a list and a map")
        fm[k] = items if items else (sub if sub else None)
    return fm


# --- records -----------------------------------------------------------------

class Record:
    __slots__ = ("path", "fm", "body")

    def __init__(self, path, fm, body):
        self.path, self.fm, self.body = path, fm, body

    @property
    def id(self):
        return self.fm.get("id")

    @property
    def type(self):
        return self.fm.get("type")

    def __getitem__(self, k):
        return self.fm.get(k)


def parse(path):
    try:
        text = path.read_text(encoding="utf-8-sig")  # an editor's byte-order mark is not part of the record
    except UnicodeDecodeError as e:
        raise Refused(f"{path}: not UTF-8 ({e.reason} at byte {e.start})")
    if not text.startswith(FENCE + "\n"):
        raise Refused(f"{path}: no frontmatter")
    end = text.find("\n" + FENCE + "\n", len(FENCE))
    if end < 0 and text.endswith("\n" + FENCE):  # a record that is front matter alone, its last newline dropped
        end = len(text) - len(FENCE) - 1
    if end < 0:
        raise Refused(f"{path}: unterminated frontmatter")
    fm = load_front(text[len(FENCE) + 1:end], path.name)
    body = text[end + len(FENCE) + 2:]
    return Record(path, fm, body.lstrip("\n"))


def render(fm, body):
    front = dump_front(fm)
    body = body.rstrip("\n")
    return f"{FENCE}\n{front}\n{FENCE}\n" + (f"\n{body}\n" if body else "")


def load_all(cfg, broken=None):
    """Every record; a file that does not read is a refusal, or, when `broken` is a list (the check's
    way), one V0 problem appended to it so that the check can diagnose the rest of the tree."""
    recs = {}
    if not cfg.research.is_dir():
        return recs
    for p in sorted(cfg.research.rglob("*.md")):
        if not cfg.id_re.match(p.name):
            continue
        try:
            r = parse(p)
            if r.id in recs:
                raise Refused(f"duplicate id {r.id}: {recs[r.id].path} and {p}")
        except Refused as e:
            if broken is None:
                raise
            broken.append({"code": "V0", "id": None, "path": rel(cfg, p), "msg": f"the record cannot be read: {e}"})
            continue
        recs[r.id] = r
    return recs


def slugify(summary):
    s = re.sub(r"[^a-z0-9]+", "-", summary.lower()).strip("-")
    return s[:40].rstrip("-") or "record"


def next_id(cfg, type_):
    prefix = cfg.prefix[type_]
    n = 0
    if cfg.research.is_dir():
        for p in cfg.research.rglob(f"{prefix}-*.md"):
            m = cfg.id_re.match(p.name)
            if m and m.group(1) == prefix:
                n = max(n, int(m.group(2)))
    if n + 1 >= 10 ** cfg.id_width:
        raise Refused(f"the {type_} ids have reached the width [prefixes] id_width = {cfg.id_width} allows; widen it (the records written so far keep their ids)")
    return f"{prefix}-{n + 1:0{cfg.id_width}d}"


# The configuration markdownlint runs with when the project binds none and keeps none at its
# root: a record's `summary:` is its title, so MD041 (first line a heading) does not fire on
# every body, and a record is one sentence per line, so MD013 (line length) is off; everything else
# is markdownlint's default.
MDLINT_DEFAULT = '{"MD013": false, "MD041": {"front_matter_title": "^\\\\s*summary\\\\s*:"}}\n'
_MDLINT_ROOT_CONFIGS = (".markdownlint.jsonc", ".markdownlint.json", ".markdownlint.yaml", ".markdownlint.yml",
                        ".markdownlint-cli2.jsonc", ".markdownlint-cli2.yaml", ".markdownlint-cli2.cjs", ".markdownlint-cli2.mjs")


_MDLINT_TEMP = [None]


def mdlint(cfg, path):
    exe = shutil.which("markdownlint")  # the path itself, so a Windows `markdownlint.cmd` runs too
    if not exe:
        return None
    cmd = [exe]
    if cfg.mdlint_config and (cfg.root / cfg.mdlint_config).is_file():
        cmd += ["-c", str(cfg.root / cfg.mdlint_config)]
    elif not any((cfg.root / c).is_file() for c in _MDLINT_ROOT_CONFIGS):
        if _MDLINT_TEMP[0] is None or not _MDLINT_TEMP[0].is_file():
            fd, name = tempfile.mkstemp(prefix="flow-markdownlint-", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(MDLINT_DEFAULT)
            _MDLINT_TEMP[0] = Path(name)
        cmd += ["-c", str(_MDLINT_TEMP[0])]
    try:
        r = subprocess.run(cmd + [str(path)], capture_output=True, text=True, cwd=cfg.root)
    except OSError:  # on PATH and yet not runnable: as absent
        return None
    return Counter(re.findall(r"\b(MD\d{3})\b", r.stdout + r.stderr)), (r.stdout + r.stderr).strip()


# The files one transition has touched, oldest first, so a transition refused halfway is undone whole:
# ("file", path, its text before or None where it did not exist) and ("move", source, destination).
_JOURNAL = []


def rollback():
    """Undo what the journal records, newest first, and empty it."""
    while _JOURNAL:
        entry = _JOURNAL.pop()
        if entry[0] == "file":
            _, path, old = entry
            if old is None:
                path.unlink(missing_ok=True)
            else:
                write_whole(path, old)
        else:
            _, src, dest = entry
            if dest.exists() and not src.exists():
                shutil.move(str(dest), str(src))


def write_record(cfg, rec, reflow=True):
    """Write `rec` to its path: reflow the body, then refuse (and revert) on a NEW markdownlint code."""
    for f in LIST_FIELDS:
        if f in rec.fm and rec.fm[f] is None:
            rec.fm[f] = []
    body = cfg.reflow(rec.body) if reflow and rec.body else rec.body
    rec.body = body
    write_linted(cfg, {rec.path: render(rec.fm, body)})
    return rec.path


def write_linted(cfg, texts):
    """Write each path's text, journaled, then refuse (and revert every one) when markdownlint reports more of
    a code over the files together than before: a violation moved verbatim from one to another is not new."""
    before, after, olds, reports = Counter(), Counter(), {}, []
    for path in texts:
        b = mdlint(cfg, path) if path.is_file() else (Counter(), "")
        before = None if b is None or before is None else before + b[0]
    for path, text in texts.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        olds[path] = path.read_text(encoding="utf-8") if path.is_file() else None
        _JOURNAL.append(("file", path, olds[path]))
        write_whole(path, text)
    for path in texts:
        r = mdlint(cfg, path)
        after = None if r is None or after is None else after + r[0]
        if r and r[1]:
            reports.append(r[1])
    if after is not None and before is not None and any(v > before.get(k, 0) for k, v in after.items()):
        for path, old in olds.items():
            if old is None:
                path.unlink()
            else:
                write_whole(path, old)
        raise Refused(f"markdownlint reports NEW violations in {', '.join(rel(cfg, p) for p in texts)} — reverted:\n" + "\n".join(reports))


def write_whole(path, text):
    """The file replaced in one step: a reader never sees it half-written, and a failure leaves the old file."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def rel(cfg, path):
    try:
        return str(Path(path).resolve().relative_to(cfg.root))
    except ValueError:
        return str(path)


def new_record(cfg, type_, fields, body="", today=None):
    if fields.get("size") not in (None, *cfg.sizes):
        raise Refused(f"size {fields['size']!r} is not one of {', '.join(cfg.sizes)}")
    fm = {k: None for k in SCHEMA[type_]}
    for f in LIST_FIELDS:
        if f in fm:
            fm[f] = []
    fm.update({"id": next_id(cfg, type_), "type": type_, "origin": "current", "created": today})
    if type_ == "idea":
        fm["state"] = "open"
    elif type_ == "question":
        fm.update({"kind": "question", "state": "open", "checked": today})
    elif type_ == "task":
        fm.update({"state": "ready", "rider": False})
    for k, v in fields.items():
        if k not in fm:
            raise Refused(f"{type_} has no field {k}")
        fm[k] = v
    if not fm.get("summary"):
        raise Refused(f"a {type_} needs a summary")
    paper = fm.get("paper") if type_ == "finding" else None
    path = cfg.dir_of(type_, paper) / f"{fm['id']}-{slugify(fm['summary'])}.md"
    rec = Record(path, fm, body)
    write_record(cfg, rec)
    return rec


def move_to_archive(cfg, rec):
    dest = cfg.archive / rec.path.name
    if rec.path.resolve().parent == cfg.archive.resolve():
        return
    cfg.archive.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise Refused(f"{rel(cfg, dest)} already exists: the archive holds a file of that name")
    _JOURNAL.append(("move", rec.path, dest))
    shutil.move(str(rec.path), str(dest))
    rec.path = dest


def read_body(path):
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        raise Refused(f"body file not found: {path}")
    return p.read_text(encoding="utf-8")


def append_note(rec, today, text, block=""):
    """A dated note at the end of the body; a file's text after it is set apart by one blank line, so a heading
    or a list it opens with stays a block of its own."""
    note = f"{today} — {text}" + (f"\n\n{block.strip(chr(10))}" if block.strip() else "")
    rec.body = (rec.body.rstrip("\n") + f"\n\n{note}\n") if rec.body.strip() else f"{note}\n"


# --- evidence ----------------------------------------------------------------

EV_ROW = re.compile(r"^([^#\s]+\.md)#([A-Z]{2,3}-[A-Za-z0-9]+)$")
STMT_WORDS = ("Theorem", "Proposition", "Lemma", "Corollary", "Definition", "Remark", "Fact", "Conjecture", "Example")
EV_STMT = re.compile(r"^([^#\s]+\.md)#(" + "|".join(STMT_WORDS) + r") (\d+(?:\.\d+)*)$")
EV_PROBE = re.compile(r"^([^#\s]+/[^/#\s]+\.py)$")


def evidence_kind(cfg, item):
    """declaration (a `Path.ext#name` or a whole module), row, statement or probe; None otherwise."""
    for kind, rx in (("declaration", cfg.ev_decl), ("declaration", cfg.ev_declfile), ("row", EV_ROW),
                     ("statement", EV_STMT), ("probe", EV_PROBE)):
        if rx.match(item):
            return kind
    return None


def resolve_evidence(cfg, item, cache):
    """Return None when the item resolves, else a reason; 'unchecked: …' when no resolver is configured."""
    kind = evidence_kind(cfg, item)
    if kind is None:
        return f"not an evidence form (Path.{cfg.decl_ext or 'ext'}#decl, doc.md#ROW, doc.md#Theorem N[.M] (or {', '.join(STMT_WORDS[1:])}), or a probe .py)"
    if kind == "declaration":
        m = cfg.ev_decl.match(item) or cfg.ev_declfile.match(item)
        names = cfg.manifest_names()
        if names is None:
            return "unchecked: no declaration manifest configured"
        decl_file = next((cfg.root / r / m.group(1) for r in cfg.manifest_roots
                          if (cfg.root / r / m.group(1)).is_file()), None)
        if decl_file is None:
            return f"{m.group(1)} is not a file under {cfg.manifest_root}/"
        if m.re is cfg.ev_declfile:  # a whole module as evidence: it must be a manifest module
            module = m.group(1).rsplit(".", 1)[0].replace("/", ".")
            if module not in cfg.manifest_modules():
                return f"module {module} is not in the manifest"
            return None
        if m.group(2) not in names:
            return f"`{m.group(2)}` is not in the manifest"
        module = m.group(1).rsplit(".", 1)[0].replace("/", ".")
        if module in cfg.manifest_modules() and m.group(2) not in cfg._in_module[module]:
            return f"`{m.group(2)}` is not declared in {module}, the module of {m.group(1)}"
        return None
    if kind in ("row", "statement"):
        m = (EV_ROW if kind == "row" else EV_STMT).match(item)
        f = cfg.root / m.group(1)
        if not f.is_file():
            return f"{m.group(1)} is not a file"
        text = cache.setdefault(f, f.read_text(encoding="utf-8"))
        if kind == "row":
            if not re.search(r"^\| %s \|" % re.escape(m.group(2)), text, re.M):
                return f"row {m.group(2)} is not in {m.group(1)}"
        else:
            if not re.search(r"(^|\*\*|#+ )%s %s\b" % (m.group(2), re.escape(m.group(3))), text, re.M):
                return f"{m.group(2)} {m.group(3)} is not in {m.group(1)}"
        return None
    m = EV_PROBE.match(item)
    if not (cfg.root / m.group(1)).is_file():
        return f"{m.group(1)} is not a file"
    if not cfg.probes or not (cfg.root / cfg.probes).is_file():
        return "unchecked: no probes register bound ([evidence] probes)"
    text = cache.setdefault(cfg.root / cfg.probes, (cfg.root / cfg.probes).read_text(encoding="utf-8"))
    name = Path(m.group(1)).name
    listed = {mm.group(1) for line in text.splitlines() if line.startswith("|")
              for mm in [re.fullmatch(r"`([^`]+\.py)`", line.split("|")[1].strip())] if mm}
    return None if name in listed else f"{name} is not listed in the probes register"


def status_for_kinds(cfg, status, kinds):
    """The status a finding may carry given its evidence kinds; None when consistent."""
    k, role, N = set(kinds), cfg.role_of.get(status), cfg.role_name
    if role == "verified" and "declaration" not in k:
        return f"{N['verified']} needs a declaration of the manifest among its evidence"
    if role == "stated" and ("declaration" in k or not (k & {"row", "statement"})):
        return f"{N['stated']} is document-level: a statement or row, and no declaration (use {N['verified']})"
    if role == "empirical" and ("declaration" in k or "probe" not in k):
        return f"{N['empirical']} needs a probe and no declaration (use {N['verified']})"
    if role == "refuted" and not (k & {"declaration", "probe"}):
        return f"{N['refuted']} needs a guard declaration or a probe as the counterexample"
    return None


# --- validation --------------------------------------------------------------

def index_form(text):
    """An index with its form set aside — a table's delimiter row — so an index that differs from the render
    only in how a version of the flow lays it out is told from a stale one."""
    return "\n".join("|-|" if re.fullmatch(r"\|(?: ?:?-+:? ?\|)+", l.strip()) else l.rstrip() for l in text.split("\n"))


def validate(cfg, recs, today):
    problems, warnings = [], []
    cache = {}
    coverage = {"records": len(recs), "kinds": list(cfg.kinds), "manifest": cfg.manifest_names() is not None,
                "probes": bool(cfg.probes and (cfg.root / cfg.probes).is_file()),
                "reflow": cfg.reflow_source, "markdownlint": bool(shutil.which("markdownlint"))}

    def bad(code, r, msg):
        problems.append({"code": code, "id": r.id if r else None,
                         "path": rel(cfg, r.path) if r else None, "msg": msg})

    by_owner = Counter()
    tasks_of = defaultdict(list)
    for r in recs.values():
        if r.type == "task" and r["question"]:
            tasks_of[r["question"]].append(r)
    ranks = defaultdict(list)
    lib = library_keys(cfg)
    cited, citers = Counter(), set()
    if lib is not None and lib.get("error"):
        problems.append({"code": "V23", "id": None, "path": None, "msg": f"the library did not answer: {lib['error']}"})
    directions = directions_of(cfg)

    for r in recs.values():
        t = r.type
        stem = r.path.name.split("-")
        if t not in TYPES:
            bad("V1", r, f"type {t!r} is not one of {TYPES}")
            continue
        if not isinstance(r.id, str) or not r.id:
            bad("V1", r, "the record has no id")
            continue
        if not r.path.name.startswith(r.id + "-") and r.path.name != r.id + ".md":
            bad("V1", r, "id does not match the filename prefix")
        if cfg.type_of_prefix.get(r.id.rsplit("-", 1)[0]) != t:
            bad("V1", r, f"prefix does not match type {t}")
        expected_dir = cfg.dir_of(t, r["paper"] if t == "finding" else None)
        in_archive = r.path.parent.resolve() == cfg.archive.resolve()
        if t == "task" and r["state"] in CLOSED_TASK and not in_archive:
            bad("V21", r, "a closed task must live in the archive")
        elif (t != "task" or r["state"] not in CLOSED_TASK) and r.path.parent.resolve() != expected_dir.resolve():
            bad("V21", r, f"expected under {rel(cfg, expected_dir)}")
        for k in SCHEMA[t]:
            if k not in r.fm:
                bad("V3", r, f"missing field {k}")
        for k in r.fm:
            if k not in SCHEMA[t]:
                bad("V3", r, f"unknown field {k}")
        if STATES[t] and r["state"] not in STATES[t]:
            bad("V3", r, f"state {r['state']!r} not in {STATES[t]}")
        if t == "task" and r["kind"] not in cfg.task_kinds:
            bad("V3", r, f"kind {r['kind']!r} not in {cfg.task_kinds}")
        if t == "question" and r["kind"] not in ("question", "conjecture"):
            bad("V3", r, f"kind {r['kind']!r}")
        if t in ("question", "task") and r["size"] not in (None, *cfg.sizes):
            bad("V3", r, f"size {r['size']!r} not in {cfg.sizes}")
        if t == "task" and r["owner"] not in (None, *cfg.owners):
            bad("V3", r, f"owner {r['owner']!r} not in {cfg.owners}")
        if t == "finding" and r["status"] not in cfg.statuses:
            bad("V3", r, f"status {r['status']!r} not in {cfg.statuses}")
        if r["origin"] not in ("current", "legacy"):
            bad("V3", r, f"origin {r['origin']!r}")
        for f in ("created", "checked", "drawn"):
            v = r[f] if f in SCHEMA[t] else None
            if v is not None and not ISO.match(str(v)):
                bad("V20", r, f"{f} is not an ISO date")
            elif v is not None and str(v) > today:
                bad("V20", r, f"{f} is in the future")
        for f in ("parked", "abandoned"):
            block = r[f] if f in SCHEMA[t] else None
            d = block.get("date") if isinstance(block, dict) else None
            if d is not None and not ISO.match(str(d)):
                bad("V20", r, f"{f}.date is not an ISO date")
            elif d is not None and str(d) > today:
                bad("V20", r, f"{f}.date is in the future")
        # references
        refs = {"derived_from": None, "requires": "finding", "depends_on": "finding",
                "answered_by": ("finding", "task"), "question": "question", "parent": "question",
                "consumed_by": "question"}
        for f, want in refs.items():
            if f not in SCHEMA[t]:
                continue
            vals = r[f] if isinstance(r[f], list) else ([r[f]] if r[f] else [])
            for v in vals:
                if v not in recs:
                    bad("V2", r, f"{f} names {v}, which does not exist")
                elif want and recs[v].type not in (want if isinstance(want, tuple) else (want,)):
                    bad("V2", r, f"{f} names {v}, a {recs[v].type}, not a {want if isinstance(want, str) else ' or '.join(want)}")
                elif f == "answered_by" and recs[v].type == "task" and (recs[v]["state"] != "done" or recs[v]["question"] != r.id):
                    bad("V18", r, f"answered by {v}, which is not a done task drawn under it")
        if t == "task":
            if not r["question"] and r["kind"] not in cfg.q_optional and r["origin"] != "legacy":
                bad("V4", r, f"a {r['kind']} task needs a question")  # legacy work has no invented provenance
            if r["state"] == "ready":
                for f in r["requires"] or []:
                    if f not in recs:
                        bad("V5", r, f"ready with unmet requires {f}")
            if r["state"] == "active":
                if r["owner"]:
                    by_owner[r["owner"]] += 1
                else:
                    bad("V9", r, "active without an owner")
            if r["state"] in ("ready", "active") and r["question"] in recs \
                    and recs[r["question"]]["state"] not in ("open", "decomposed"):
                bad("V13", r, f"open task on a question that is {recs[r['question']]['state']}")
            if r["state"] == "done" and r["owner"]:  # a rank on it is V14's, as on any closed record
                bad("V20", r, "a done task carries an owner")
            if r["state"] == "abandoned" and not (isinstance(r["abandoned"], dict) and r["abandoned"].get("reason")):
                bad("V17", r, "abandoned without a dated reason")
        if t == "finding":
            if not r["evidence"]:
                bad("V6", r, "no evidence")
            kinds = []
            for e in r["evidence"] or []:
                why = resolve_evidence(cfg, str(e), cache)
                if why and why.startswith("unchecked"):
                    warnings.append(f"{r.id}: {e}: {why}")
                    kinds.append(evidence_kind(cfg, str(e)))
                elif why:
                    bad("V6", r, f"evidence {e}: {why}")
                else:
                    kinds.append(evidence_kind(cfg, str(e)))
            msg = status_for_kinds(cfg, r["status"], kinds) if r["evidence"] else None
            if msg:
                bad("V6", r, msg)
        if t == "question":
            if r["state"] in ("open", "decomposed") and not r["checked"]:
                bad("V12", r, f"{r['state']} without a checked date")
            if r["parked"] is not None:
                p = r["parked"]
                if r["state"] != "open" or not isinstance(p, dict) or not p.get("date") or not p.get("reason"):
                    bad("V15", r, "parked needs an open question with a date and a reason")
                if r["rank"] is not None:
                    bad("V14", r, "a parked question is never ranked")
            if r["origin"] == "current" and not r["kill"]:
                bad("V16", r, "a current question needs kill criteria")
            if r["state"] == "answered" and not r["answered_by"] and r["origin"] == "current":
                bad("V18", r, "answered without a finding or a done task")
            if r["state"] == "abandoned" and not (isinstance(r["abandoned"], dict) and r["abandoned"].get("reason")):
                bad("V17", r, "abandoned without a dated reason")
            if r["state"] == "decomposed":
                ts = tasks_of.get(r.id, [])
                if not ts:
                    bad("V10", r, "decomposed with no task")
                elif all(x["state"] in CLOSED_TASK for x in ts):
                    warnings.append(f"{r.id}: needs refine or answer (every task closed)")
            if r["direction"] and directions is not None and r["direction"] not in directions:
                bad("V22", r, f"direction {r['direction']!r} is not in {rel(cfg, cfg.directions)}")
        if t == "idea":
            if r["state"] == "consumed":
                q = recs.get(r["consumed_by"])
                if not q or r.id not in (q["derived_from"] or []):
                    bad("V17", r, "consumed without a question deriving from it")
            if r["state"] == "abandoned" and not (isinstance(r["abandoned"], dict) and r["abandoned"].get("reason")):
                bad("V17", r, "abandoned without a dated reason")
        if lib is not None and not lib.get("error"):
            for k in sorted(set(lib["cite_re"].findall(render(r.fm, r.body)))):
                cited[k] += 1
                citers.add(r.id)
                if k not in lib["cards"]:
                    bad("V23", r, f"cites {lib['cite_prefix']}{k}, which the library does not hold")
            for k, i in sorted(set(lib["cite_ex_re"].findall(render(r.fm, r.body)))):
                held = (lib["cards"].get(k) or {}).get("extracts")
                if held is not None and i not in held:
                    bad("V23", r, f"cites {lib['cite_prefix']}{k}#{i}, and the library's card {k} carries no extract {i}")
        if t in ("question", "task") and r["rank"] is not None:
            live = (t == "question" and r["state"] in ("open", "decomposed")) or \
                   (t == "task" and r["state"] in ("ready", "active"))
            if not live:
                bad("V14", r, "rank on a closed record")
            if t == "task" and (r["kind"] in cfg.decision_kinds or r["owner"] in cfg.decision_owners):
                bad("V14", r, "owner-only work is never ranked")
            if not r["why_now"] or not r["first_move"]:
                bad("V14", r, "a ranked record needs why_now and first_move")
            if isinstance(r["rank"], int) and not isinstance(r["rank"], bool):
                ranks[r["rank"]].append(r.id)
            else:
                bad("V3", r, f"rank {r['rank']!r} is not a whole number")
        if cfg.reflow_source and r.body and cfg.reflow(r.body) != r.body:
            bad("V19", r, "body is not one sentence per line (reflow changes it)")
    for n, ids in ranks.items():
        if len(ids) > 1:
            problems.append({"code": "V14", "id": None, "path": None, "msg": f"rank {n} on {', '.join(ids)}"})
    if ranks and sorted(ranks) != list(range(1, len(ranks) + 1)):
        problems.append({"code": "V14", "id": None, "path": None, "msg": f"ranks are not 1..n: {sorted(ranks)}"})
    if lib is None or lib.get("error"):
        coverage["library"] = None
    else:
        held = [k for k in cited if k in lib["cards"]]
        coverage["library"] = {"cited": len(cited), "records": len(citers),
                               "grades": dict(Counter(str(lib["cards"][k].get("grade")) for k in held)),
                               "excluded": sum(1 for k in held if lib["cards"][k].get("state") == "excluded")}
    for o, n in by_owner.items():
        lim = int(cfg.hand.get(o, 0) or 0)
        if lim and n > lim:
            problems.append({"code": "V9", "id": None, "path": None, "msg": f"{o} holds {n} active tasks; limit {lim}"})
    # cycles
    for f in ("derived_from", "depends_on", "parent"):
        for start in recs:
            seen, stack = set(), [start]
            while stack:
                x = stack.pop()
                ys = recs[x][f] if x in recs and f in SCHEMA.get(recs[x].type, ()) else None
                for y in [ys] if isinstance(ys, str) else ys or []:
                    if y == start:
                        problems.append({"code": "V8", "id": start, "path": None, "msg": f"{f} cycle through {start}"})
                        stack = []
                        break
                    if y not in seen and y in recs:
                        seen.add(y)
                        stack.append(y)
    # index freshness
    if cfg.index.is_file():
        have, want = cfg.index.read_text(encoding="utf-8"), render_index(cfg, recs)
        if have != want:
            problems.append({"code": "V11", "id": None, "path": rel(cfg, cfg.index),
                             "msg": f"{rel(cfg, cfg.index)} is in another version's form, its records unchanged — run `flow index` once after an upgrade"
                             if index_form(have) == index_form(want) else f"{rel(cfg, cfg.index)} is stale — run `flow index`"})
    else:
        problems.append({"code": "V11", "id": None, "path": rel(cfg, cfg.index), "msg": "index missing — run `flow index`"})
    return problems, warnings, coverage


# --- index -------------------------------------------------------------------

def _line(r, extra=""):
    return f"- `{r.id}` — {r['summary']}" + (f" [{extra}]" if extra else "")


def render_index(cfg, recs):
    R = list(recs.values())
    out = ["# Records index", "",
           "*Generated by `flow index`; never hand-edited; `flow check` fails when it is stale.",
           "Start with `flow state`, then this file; open a record by its ID (`flow show ID`); never glob the record directories.*", ""]
    out += ["## Counts", "", "| type | state | n |", "| --- | --- | --- |"]
    counts = Counter((r.type, stat(r)) for r in R)
    for (t, s), n in sorted(counts.items()):
        out.append(f"| {t} | {s} | {n} |")
    out.append("")

    def section(title, rows):
        out.extend([f"## {title}", ""])
        out.extend(rows if rows else ["none"])
        out.append("")

    ranked = sorted((r for r in R if r["rank"] is not None), key=lambda r: (0, r["rank"], "") if isinstance(r["rank"], int) else (1, 0, str(r["rank"])))
    rows = []
    for r in ranked:
        bits = [f"why now: {r['why_now']}", f"first move: {r['first_move']}"]
        if r["direction"]:
            bits.insert(0, f"direction: {r['direction']}")
        rows.append(f"{r['rank']}. `{r.id}` — {r['summary']}")
        rows += [f"   {b}" for b in bits]
    riders = [r for r in R if r.type == "task" and r["rider"] and r["state"] in ("ready", "active")]
    if not rows:
        rows.append("none")
    if riders or cfg.has("question"):
        rows.append("")
        rows.append("Rider for the next hand-over: " + ("; ".join(f"`{r.id}` — {r['summary']}" for r in riders) if riders else "none"))
    section("Next (ranked)", rows)

    rows = []
    for o in cfg.owners:
        rows.append(f"### {o}")
        rows.append("")
        held = [r for r in R if r.type == "task" and r["state"] == "active" and r["owner"] == o]
        rows += [_line(r, f"{r['kind']}, drawn {r['drawn']}" + (f", {r['question']}" if r["question"] else "")) for r in held] or ["none"]
        rows.append("")
    section("Hand", rows[:-1])

    order = {s: i for i, s in enumerate(cfg.sizes)}
    ready = [r for r in R if r.type == "task" and r["state"] == "ready" and r["kind"] not in cfg.decision_kinds and r["owner"] not in cfg.decision_owners]
    ready.sort(key=lambda r: (order.get(r["size"], len(order)), r.id))
    section("Ready", [_line(r, ", ".join(x for x in (r["kind"], r["size"], r["question"]) if x)) for r in ready])

    if cfg.has("question"):
        opn = [r for r in R if r.type == "question" and r["state"] == "open" and r["parked"] is None]
        opn.sort(key=lambda r: (str(r["checked"]), r.id))
        section("Open questions", [_line(r, ", ".join(x for x in (r["size"], f"checked {r['checked']}", r["direction"]) if x)) for r in opn])

        parked = [r for r in R if r.type == "question" and r["parked"] is not None]
        _pk = lambda r: r["parked"] if isinstance(r["parked"], dict) else {}
        parked.sort(key=lambda r: (str(_pk(r).get("date")), r.id))
        section("Parked questions", [_line(r, f"parked {_pk(r).get('date')} — {str(_pk(r).get('reason', '')).split('. ')[0]}") for r in parked])

        dec = [r for r in R if r.type == "question" and r["state"] == "decomposed"]
        tasks_of = defaultdict(list)
        for r in R:
            if r.type == "task" and r["question"]:
                tasks_of[r["question"]].append(r)
        need = [r for r in dec if not tasks_of[r.id] or all(x["state"] in CLOSED_TASK for x in tasks_of[r.id])]
        section("Needs refine or answer", [_line(r, f"{len(tasks_of[r.id])} tasks, all closed" if tasks_of[r.id] else "no tasks") for r in sorted(need, key=lambda r: r.id)])

    if cfg.has("finding"):
        fnd = sorted((r for r in R if r.type == "finding"), key=lambda r: r.id, reverse=True)[:cfg.recent_findings]
        section("Recent findings", [_line(r, ", ".join(x for x in (r["paper"], r["status"]) if x)) for r in fnd])

    auth = [r for r in R if r.type == "task" and r["state"] in ("ready", "active") and (r["kind"] in cfg.decision_kinds or r["owner"] in cfg.decision_owners)]
    section("Owner-only", [_line(r, r["kind"]) for r in sorted(auth, key=lambda r: r.id)])

    if cfg.has("question"):
        settled = [r for r in R if r.type == "question" and "do-not-reopen" in (r["tags"] or [])]
        section("Settled, do not re-open", [_line(r, r["state"]) for r in sorted(settled, key=lambda r: r.id)])

    ideas = [r for r in R if r.type == "idea" and r["state"] == "open"]
    ideas.sort(key=lambda r: (str(r["created"]), r.id))
    rows = [f"{len(ideas)} open ideas; oldest:", ""] + [_line(r, f"{r['created']}, {r['source'] or 'no source'}") for r in ideas[:cfg.oldest_ideas]]
    section("Heap", rows if ideas else [])
    return "\n".join(out).rstrip("\n") + "\n"


# --- transitions -------------------------------------------------------------

def get(recs, id_, type_=None, states=None):
    r = recs.get(id_)
    if not r:
        raise Refused(f"{id_} does not exist")
    if type_ and r.type != type_:
        raise Refused(f"{id_} is a {r.type}, not a {type_}")
    if states and r["state"] not in states:
        raise Refused(f"{id_} is {r['state']}, not {' or '.join(states)}")
    return r


def close_ranks(cfg, recs):
    """The ranked records renumbered 1..n in their order, after a transition cleared one of them:
    the list stays contiguous without a hand on it.  Returns the records whose rank changed."""
    ranked = sorted((r for r in recs.values() if r.type in ("question", "task") and r["rank"] is not None),
                    key=lambda r: (r["rank"] if isinstance(r["rank"], int) else 10**9, r.id))
    changed = []
    for n, r in enumerate(ranked, 1):
        if r["rank"] != n:
            r.fm["rank"] = n
            save(cfg, r)
            changed.append(r)
    return changed


def save(cfg, rec):
    write_record(cfg, rec)


def cmd_capture(cfg, recs, a, today):
    r = new_record(cfg, "idea", {"summary": a.summary, "source": a.source, "tags": a.tag or []},
                   read_body(a.body), today)
    return [r], []


def directions_of(cfg):
    """The bold names of the directions file's bullets, or None where the project keeps no such file."""
    if not cfg.directions.is_file():
        return None
    text = re.sub(r"<!--.*?-->", "", cfg.directions.read_text(encoding="utf-8"), flags=re.S)  # the form init writes in a comment
    return set(re.findall(r"^- \*\*(.+?)\*\*", text, re.M))


def check_direction(cfg, direction):
    names = directions_of(cfg)
    if direction and names is not None and direction not in names:
        raise Refused(f"direction {direction!r} is not in {rel(cfg, cfg.directions)}, which names "
                      f"{', '.join(sorted(names)) or 'none yet'}; the owner writes a direction there")


def decision_owner(cfg, kind):
    """The owner a task of a decision kind is minted under, the first of `decision_owners`; None otherwise."""
    return cfg.decision_owners[0] if kind in cfg.decision_kinds and cfg.decision_owners else None


def cmd_task(cfg, recs, a, today):
    if a.kind not in cfg.task_kinds:
        raise Refused(f"task kind {a.kind!r} not in {cfg.task_kinds}")
    if a.question:
        get(recs, a.question, "question", ("open", "decomposed"))
    elif a.kind not in cfg.q_optional:
        raise Refused(f"a {a.kind} task needs --question (only {cfg.q_optional} stand alone)")
    r = new_record(cfg, "task", {"summary": a.summary, "kind": a.kind, "question": a.question, "size": a.size,
                                 "dod": a.dod, "owner": decision_owner(cfg, a.kind),
                                 "derived_from": [a.question] if a.question else [], "source": a.source,
                                 "tags": a.tag or []}, read_body(a.body), today)
    return [r], []


def cmd_frame(cfg, recs, a, today):
    srcs = [get(recs, i) for i in a.ids]
    ideas = [s for s in srcs if s.type == "idea"]
    finds = [s for s in srcs if s.type == "finding"]
    if len(finds) > 1 or (finds and ideas) or any(s.type not in ("idea", "finding") for s in srcs):
        raise Refused("frame takes ideas, or exactly one finding")
    for s in ideas:
        if s["state"] != "open":
            raise Refused(f"{s.id} is {s['state']}")
    if a.parent:
        get(recs, a.parent, "question")
    check_direction(cfg, a.direction)
    q = new_record(cfg, "question", {
        "summary": a.summary, "kill": a.kill, "size": a.size, "kind": a.kind, "parent": a.parent,
        "direction": a.direction, "derived_from": [s.id for s in srcs], "tags": a.tag or [],
        "source": a.source}, read_body(a.body), today)
    for s in ideas:
        s.fm["state"], s.fm["consumed_by"] = "consumed", q.id
        save(cfg, s)
    return [q], ideas


def _mk_tasks(cfg, recs, specs, q, derived, today, kind=None, size=None, dod=None, requires=None):
    out = []
    for spec in specs or []:
        summary, k = spec[0], (spec[1] if len(spec) > 1 else (kind or cfg.default_kind))
        if len(spec) > 2:
            raise Refused(f"--task takes SUMMARY [KIND]: {spec}")
        if k not in cfg.task_kinds:
            raise Refused(f"task kind {k!r} not in {cfg.task_kinds}")
        if q is None and k not in cfg.q_optional:
            raise Refused(f"a {k} task needs a question")
        out.append(new_record(cfg, "task", {"summary": summary, "kind": k, "question": q, "derived_from": derived,
                                            "size": size, "dod": dod, "requires": requires or [],
                                            "owner": decision_owner(cfg, k)}, "", today))
    return out


def _mk_questions(cfg, specs, derived, parent, today):
    out = []
    for spec in specs or []:
        if len(spec) != 2:
            raise Refused(f"--question/--subq takes SUMMARY KILL: {spec}")
        out.append(new_record(cfg, "question", {"summary": spec[0], "kill": spec[1], "derived_from": derived,
                                                "parent": parent}, "", today))
    return out


def _mk_ideas(cfg, specs, source, today):
    return [new_record(cfg, "idea", {"summary": s, "source": source}, "", today) for s in specs or []]


def cmd_refine(cfg, recs, a, today):
    q = get(recs, a.question, "question", ("open", "decomposed"))
    if q["parked"] is not None:
        raise Refused(f"{q.id} is parked: unpark it first")
    if not a.task:
        raise Refused("refine produces at least one task")
    for f in a.requires or []:
        get(recs, f, "finding")
    made = _mk_tasks(cfg, recs, a.task, q.id, [q.id], today, a.kind, a.size, a.dod, a.requires)
    made += _mk_questions(cfg, a.subq, [q.id], q.id, today)
    made += _mk_ideas(cfg, a.idea, f"refine {q.id}", today)
    q.fm["state"] = "decomposed"
    if a.body:
        append_note(q, today, "refined:", read_body(a.body))
    save(cfg, q)
    return made, [q]


def cmd_draw(cfg, recs, a, today):
    t = get(recs, a.task, "task", ("ready",))
    if a.owner not in cfg.owners:
        raise Refused(f"owner {a.owner!r} not in {cfg.owners}")
    lim = int(cfg.hand.get(a.owner, 0) or 0)
    held = sum(1 for r in recs.values() if r.type == "task" and r["state"] == "active" and r["owner"] == a.owner)
    if lim and held >= lim:
        raise Refused(f"{a.owner}'s hand is full ({held} of {lim}); return or close a task first")
    t.fm.update({"state": "active", "owner": a.owner, "drawn": today})
    save(cfg, t)
    return [], [t]


def cmd_return(cfg, recs, a, today):
    t = get(recs, a.task, "task", ("active",))
    t.fm.update({"state": "ready", "owner": None, "drawn": None})
    if a.note:
        append_note(t, today, "returned: " + a.note)
    save(cfg, t)
    return [], [t]


def _findings(cfg, recs, specs, task, paper, depends, today, force_status=None):
    out = []
    for spec in specs or []:
        if len(spec) < 3:
            raise Refused(f"--finding takes SUMMARY STATUS EVIDENCE...: {spec}")
        summary, status, ev = spec[0], spec[1], list(spec[2:])
        if force_status and status != cfg.role_name[force_status]:
            raise Refused(f"a finding here is {cfg.role_name[force_status]}")
        if status not in cfg.statuses:
            raise Refused(f"status {status!r} not in {cfg.statuses}")
        cache = {}
        kinds = []
        for e in ev:
            why = resolve_evidence(cfg, e, cache)
            if why and not why.startswith("unchecked"):
                raise Refused(f"evidence {e}: {why}")
            kinds.append(evidence_kind(cfg, e))
        msg = status_for_kinds(cfg, status, kinds)
        if msg:
            raise Refused(msg)
        p = paper
        if not p:
            for e in ev:
                m = EV_ROW.match(e) or EV_STMT.match(e)
                if m:
                    p = Path(m.group(1)).stem
                    break
        for d in depends or []:
            get(recs, d, "finding")
        out.append(new_record(cfg, "finding", {"summary": summary, "status": status, "evidence": ev,
                                               "derived_from": [task.id], "question": task["question"],
                                               "depends_on": depends or [], "paper": p}, "", today))
    return out


def cmd_make(cfg, recs, a, today):
    t = get(recs, a.task, "task", ("active",))
    made = _findings(cfg, recs, a.finding, t, a.paper, a.depends_on, today)
    made += _mk_tasks(cfg, recs, a.task_out, t["question"], [t.id], today)
    made += _mk_questions(cfg, a.question, [t.id], None, today)
    made += _mk_ideas(cfg, a.idea, f"make {t.id}", today)
    if a.resolution:
        append_note(t, today, "resolution:", read_body(a.resolution))
    had_rank = t["rank"] is not None
    t.fm.update({"state": "done", "owner": None, "rank": None, "why_now": None, "first_move": None, "rider": False})
    save(cfg, t)
    move_to_archive(cfg, t)
    return made, [t] + (close_ranks(cfg, recs) if had_rank else [])


def cmd_abort(cfg, recs, a, today):
    t = get(recs, a.task, "task", ("active",))
    made = _findings(cfg, recs, a.finding, t, a.paper, None, today, force_status="refuted")
    if a.resolution:
        append_note(t, today, "resolution:", read_body(a.resolution))
    had_rank = t["rank"] is not None
    t.fm.update({"state": "abandoned", "owner": None, "rank": None, "why_now": None, "first_move": None,
                 "rider": False, "abandoned": {"date": today, "reason": a.reason}})
    save(cfg, t)
    move_to_archive(cfg, t)
    return made, [t] + (close_ranks(cfg, recs) if had_rank else [])


def cmd_answer(cfg, recs, a, today):
    q = get(recs, a.question, "question", ("open", "decomposed"))
    fs = []
    for ref in a.by:
        r = get(recs, ref)
        if r.type == "task":
            # a question whose kill names work rather than a result is answered by the
            # done tasks drawn under it — never by a finding that is an artifact record,
            # and never killed, which would record finished work as abandoned
            if r["state"] != "done":
                raise Refused(f"{r.id} is {r['state']}, not done — a question is answered by done tasks")
            if r["question"] != q.id:
                raise Refused(f"{r.id} was not drawn under {q.id}")
        elif r.type != "finding":
            raise Refused(f"answer takes findings or done tasks, not {r.id}, a {r.type}")
        fs.append(r)
    live = [r.id for r in recs.values() if r.type == "task" and r["question"] == q.id and r["state"] in ("ready", "active")]
    if live:
        raise Refused(f"{q.id} still has open tasks: {', '.join(live)} — finish, kill or abort them first")
    had_rank = q["rank"] is not None
    q.fm.update({"state": "answered", "answered_by": [f.id for f in fs], "rank": None, "why_now": None,
                 "first_move": None, "parked": None})
    save(cfg, q)
    return [], [q] + (close_ranks(cfg, recs) if had_rank else [])


def cmd_kill(cfg, recs, a, today):
    r = get(recs, a.id)
    if r.type == "finding":
        raise Refused("a finding is never killed; refute it with a finding")
    if r.type == "task" and r["state"] != "ready":
        raise Refused("kill takes a ready task; abort an active one")
    if r["state"] in ("abandoned", "answered", "consumed", "done"):
        raise Refused(f"{r.id} is already {r['state']}")
    if r.type == "question":
        live = [x.id for x in recs.values() if x.type == "task" and x["question"] == r.id and x["state"] in ("ready", "active")]
        if live:
            raise Refused(f"{r.id} still has open tasks: {', '.join(live)} — kill or abort them first")
    had_rank = r.fm.get("rank") is not None
    r.fm.update({"state": "abandoned", "abandoned": {"date": today, "reason": a.reason}})
    for k in ("rank", "why_now", "first_move", "parked", "owner"):
        if k in r.fm:
            r.fm[k] = None
    save(cfg, r)
    if r.type == "task":
        move_to_archive(cfg, r)
    return [], [r] + (close_ranks(cfg, recs) if had_rank else [])


def cmd_park(cfg, recs, a, today):
    q = get(recs, a.question, "question", ("open",))
    if q["parked"] is not None:
        since = q["parked"].get("date") if isinstance(q["parked"], dict) else q["parked"]
        raise Refused(f"{q.id} is parked already, since {since}: unpark it first")
    had_rank = q["rank"] is not None
    q.fm.update({"parked": {"date": today, "reason": a.reason, "revival": a.revival},
                 "rank": None, "why_now": None, "first_move": None})
    save(cfg, q)
    return [], [q] + (close_ranks(cfg, recs) if had_rank else [])


def cmd_unpark(cfg, recs, a, today):
    q = get(recs, a.question, "question", ("open",))
    if q["parked"] is None:
        raise Refused(f"{q.id} is not parked")
    q.fm.update({"parked": None, "checked": today})
    if a.note:
        append_note(q, today, "unparked: " + a.note)
    save(cfg, q)
    return [], [q]


def _rankable(cfg, r):
    return (r.type == "question" and r["state"] in ("open", "decomposed") and r["parked"] is None) or \
           (r.type == "task" and r["state"] in ("ready", "active") and r["kind"] not in cfg.decision_kinds
            and r["owner"] not in cfg.decision_owners)


def cmd_rank(cfg, recs, a, today):
    changed = []
    if a.insert and (a.set or a.clear):
        raise Refused("--insert takes a rank: flow rank ID N --insert")
    if a.set:
        if len(set(a.set)) != len(a.set):
            raise Refused(f"--set names a record twice: {' '.join(a.set)}")
        rs = [get(recs, i) for i in a.set]
        for r in rs:
            if not _rankable(cfg, r):
                raise Refused(f"{r.id} cannot be ranked (closed, parked or owner-only)")
            if not r["why_now"] or not r["first_move"]:
                raise Refused(f"{r.id} needs why_now and first_move first (flow rank {r.id} N --why … --first-move …)")
        for r in recs.values():
            if r.type in ("question", "task") and r["rank"] is not None and r not in rs:
                r.fm["rank"] = None
                save(cfg, r)
                changed.append(r)
        for n, r in enumerate(rs, 1):
            r.fm["rank"] = n
            if r.type == "question":
                r.fm["checked"] = today
            save(cfg, r)
            changed.append(r)
        return [], changed
    r = get(recs, a.id)
    if r.type not in ("question", "task"):
        raise Refused(f"{r.id} is a {r.type}: only questions and tasks are ranked")
    if a.clear:
        had_rank = r["rank"] is not None
        r.fm["rank"] = None
        save(cfg, r)
        return [], [r] + (close_ranks(cfg, recs) if had_rank else [])
    if a.n is None:
        raise Refused("rank takes ID N, --set ID..., or ID --clear")
    if not _rankable(cfg, r):
        raise Refused(f"{r.id} cannot be ranked (closed, parked or owner-only)")
    n = int(a.n)
    others = sorted((o for o in recs.values() if o is not r and o.type in ("question", "task") and o["rank"] is not None),
                    key=lambda o: o["rank"])
    if not 1 <= n <= len(others) + 1:
        raise Refused(f"rank {n} would leave a gap: the ranks run 1..{len(others) + 1} with {r.id} among them")
    if not a.insert:
        for o in others:
            if o["rank"] == n:
                raise Refused(f"rank {n} is held by {o.id} (--insert puts {r.id} there and moves the rest down)")
    r.fm["rank"] = n
    if a.why:
        r.fm["why_now"] = a.why
    if a.first_move:
        r.fm["first_move"] = a.first_move
    if a.direction:
        if r.type != "question":
            raise Refused(f"a direction is a question's; {r.id} is a {r.type}")
        check_direction(cfg, a.direction)
        r.fm["direction"] = a.direction
    if r.type == "question":
        r.fm["checked"] = today
    if not r["why_now"] or not r["first_move"]:
        raise Refused("a ranked record needs --why and --first-move")
    save(cfg, r)
    changed = [r]
    if a.insert:  # the others keep their order around it, renumbered from 1
        for i, o in enumerate(others[:n - 1] + [None] + others[n - 1:], 1):
            if o is not None and o["rank"] != i:
                o.fm["rank"] = i
                save(cfg, o)
                changed.append(o)
    return [], changed


def cmd_checked(cfg, recs, a, today):
    out = []
    for i in a.ids:
        q = get(recs, i, "question")
        q.fm["checked"] = today
        save(cfg, q)
        out.append(q)
    return [], out


# The fields a record's prose owner may change at any time, through the CLI rather than by hand:
# which record types carry each, and what a value must be.  State, provenance and rank stay with
# their transitions.
SETTABLE = {"summary": ("idea", "question", "task", "finding"), "kill": ("question",),
            "size": ("question", "task"), "dod": ("task",), "rider": ("task",),
            "depends_on": ("finding",)}


def cmd_set(cfg, recs, a, today):
    r = get(recs, a.id)
    if a.field not in SETTABLE:
        raise Refused(f"set takes one of {', '.join(SETTABLE)}; {a.field!r} is a transition's or no field")
    if r.type not in SETTABLE[a.field]:
        raise Refused(f"{r.id} is a {r.type}; {a.field} is a field of {', '.join(SETTABLE[a.field])}")
    v = a.value.strip()
    if a.field == "rider":
        if v not in ("on", "off"):
            raise Refused("rider takes on or off")
        if v == "on" and r["state"] not in ("ready", "active"):
            raise Refused(f"{r.id} is {r['state']}; only a ready or active task rides a hand-over")
        value = v == "on"
    elif a.field == "depends_on":
        # the curated edges between findings (the design's curated edges): a comma- or space-separated list
        # of findings, `none` clearing it; a cycle is refused here as the validator refuses it
        ids = [] if v == "none" else [x for x in re.split(r"[,\s]+", v) if x]
        for x in ids:
            get(recs, x, "finding")
        if r.id in ids:
            raise Refused(f"{r.id} cannot depend on itself")
        seen, stack = set(), list(ids)
        while stack:
            x = stack.pop()
            if x == r.id:
                raise Refused(f"depends_on would close a cycle through {r.id}")
            if x not in seen:
                seen.add(x)
                stack.extend((recs[x]["depends_on"] or []) if x in recs else [])
        value = list(dict.fromkeys(ids))
    elif a.field == "size":
        if v not in (*cfg.sizes, "none"):
            raise Refused(f"size takes one of {', '.join(cfg.sizes)} or none")
        value = None if v == "none" else v
    else:
        if not v:
            raise Refused(f"{a.field} cannot be empty")
        value = v
    r.fm[a.field] = value
    save(cfg, r)
    return [], [r]


# --- the reference library, asked and never read ----------------------------------

def stat(r):
    """The one word a listing shows after a record's id: its state, or a finding's status."""
    return r["status"] if r.type == "finding" else r["state"]


def library_keys(cfg):
    """What the bound library answers to `keys`: its cite prefix and each card's state and grade.
    None when the project binds no library; `{"error": …}` when the command does not answer."""
    if not cfg.library_cmd:
        return None
    try:
        r = subprocess.run(cfg.library_cmd + ["keys"], capture_output=True, text=True, cwd=cfg.root, timeout=60)
        ans = json.loads(r.stdout)
        ans["cite_re"] = re.compile(r"(?<![A-Za-z0-9])%s([a-z0-9][a-z0-9-]*)" % re.escape(ans["cite_prefix"]))
        ans["cite_ex_re"] = re.compile(r"(?<![A-Za-z0-9])%s([a-z0-9][a-z0-9-]*)#([a-z0-9][a-z0-9-]*)" % re.escape(ans["cite_prefix"]))
        if not isinstance(ans["cards"], dict):
            raise ValueError("no cards")
        if r.returncode != 0:
            return {"error": "; ".join(str(p.get("msg")) for p in ans.get("problems") or []) or f"exit {r.returncode}"}
        return ans
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as e:
        return {"error": f"{' '.join(cfg.library_cmd)} keys: {e}"}


# --- views -------------------------------------------------------------------

def cmd_find(cfg, recs, a, today):
    hits = []
    try:
        grep = re.compile(a.grep, re.I) if a.grep else None
    except re.error as e:
        raise Refused(f"--grep {a.grep!r} is not a regular expression: {e}")
    for r in recs.values():
        if a.type and r.type != a.type:
            continue
        if a.state and r["state"] != a.state:
            continue
        if a.kind and r["kind"] != a.kind:
            continue
        if a.status and r["status"] != a.status:
            continue
        if a.tag and a.tag not in (r["tags"] or []):
            continue
        if a.owner and r["owner"] != a.owner:
            continue
        if a.question and r["question"] != a.question:
            continue
        if a.paper and r["paper"] != a.paper:
            continue
        if a.requires and a.requires not in (r["requires"] or []):
            continue
        if a.depends_on and a.depends_on not in (r["depends_on"] or []):
            continue
        if a.parked and (r.type != "question" or r["parked"] is None):
            continue
        if a.ranked and r["rank"] is None:
            continue
        if a.grep and not grep.search(render(r.fm, r.body)):
            continue
        hits.append(r)
    return hits


def backlinks(recs, id_):
    out = defaultdict(list)
    for r in recs.values():
        for f in ("derived_from", "requires", "depends_on", "answered_by"):
            if f in r.fm and id_ in (r[f] or []):
                out[f].append(r.id)
        for f in ("question", "parent", "consumed_by"):
            if f in r.fm and r[f] == id_:
                out[f].append(r.id)
    return dict(out)


def links(r):
    out = {}
    for f in ("derived_from", "requires", "depends_on", "answered_by", "question", "parent", "consumed_by"):
        if f in r.fm and r[f]:
            out[f] = list(r[f]) if isinstance(r[f], list) else [r[f]]
    return out


def refs(recs, ids):
    return [{"id": i, "summary": recs[i]["summary"] if i in recs else None} for i in ids]


def show_text(cfg, recs, r):
    lines = [f"{rel(cfg, r.path)}", render(r.fm, r.body).rstrip("\n"), "", "links:"]
    for f in ("derived_from", "requires", "depends_on", "answered_by", "question", "parent", "consumed_by"):
        if f in r.fm and r[f]:
            vals = r[f] if isinstance(r[f], list) else [r[f]]
            for v in vals:
                lines.append(f"  {f}: {v} — {recs[v]['summary'] if v in recs else 'MISSING'}")
    bl = backlinks(recs, r.id)
    if bl:
        lines.append("back-references:")
        for f, ids in bl.items():
            for i in ids:
                lines.append(f"  {f} ← {i} — {recs[i]['summary']}")
    return "\n".join(lines)


def cmd_graph(cfg, recs, a, today):
    edges = []
    for r in recs.values():
        for f in ("depends_on", "derived_from"):
            for v in (r[f] or []) if f in r.fm else []:
                edges.append((r.id, v, f))
    if a.frm:
        keep, frontier = {a.frm}, [a.frm]
        while frontier:
            x = frontier.pop()
            for s, d, _ in edges:
                for y in ((d,) if s == x else ()) + ((s,) if d == x else ()):
                    if y not in keep:
                        keep.add(y)
                        frontier.append(y)
        edges = [e for e in edges if e[0] in keep and e[1] in keep]
    if a.dot:
        body = "\n".join(f'  "{s}" -> "{d}" [label="{f}"];' for s, d, f in edges)
        return f"digraph flow {{\n{body}\n}}"
    return "\n".join(f"{s} --{f}--> {d}" for s, d, f in edges) or "no edges"


# --- the cold-start bundle -------------------------------------------------------

def _section(lines, heading):
    """(start, end) of a `## heading` body, the heading line included; None when absent."""
    for i, l in enumerate(lines):
        m = re.match(r"^(#{1,6}) (.*?)\s*$", l)
        if m and m.group(2) == heading:
            lv = len(m.group(1))
            j = i + 1
            while j < len(lines) and not re.match(r"^#{1,%d} " % lv, lines[j]):
                j += 1
            return i, j
    return None


def state_lines(cfg, skip=0, budget=14000):
    """The inbox slot of the directions file, the index's ranked list and the log's top entry,
    every line carrying its FILE:LINE, under a byte budget; returns (lines, next_from)."""
    out = []
    if cfg.directions.is_file():
        ls = cfg.directions.read_text(encoding="utf-8").split("\n")
        sec = _section(ls, "Inbox")
        if sec:
            out += [f"{rel(cfg, cfg.directions)}:{i + 1}: {ls[i]}" for i in range(*sec)] + [""]
    if cfg.index.is_file():
        ls = cfg.index.read_text(encoding="utf-8").split("\n")
        sec = _section(ls, "Next (ranked)")
        if sec:
            out += [f"{rel(cfg, cfg.index)}:{i + 1}: {ls[i]}" for i in range(*sec)] + [""]
    else:
        out += [f"{rel(cfg, cfg.index)}: missing — run `flow index`", ""]
    if cfg.log and cfg.log.is_file():
        ls = cfg.log.read_text(encoding="utf-8").split("\n")
        entries = log_entries(ls)
        if entries:
            out += [f"{rel(cfg, cfg.log)}:{i + 1}: {ls[i]}" for i in range(*entries[0][:2])]
        else:
            out.append(f"{rel(cfg, cfg.log)}: no `## ` entry")
    elif cfg.log:
        out.append(f"{rel(cfg, cfg.log)}: missing")
    while out and not out[-1]:
        out.pop()
    kept, size = [], 0
    for n, line in enumerate(out):
        if n < skip:
            continue
        size += len(line.encode("utf-8")) + 1
        if size > budget and kept:  # a line longer than the budget is printed alone, so --from moves on
            return kept, n
        kept.append(line)
    return kept, None


# --- the close: what a machine can see of a session's end --------------------------
#
# `flow state --check` decides what it can of a close and says what it could not: the
# conversation's inventory and the sweep by meaning stay the session's own.

def git(cfg, *args):
    """A git command's output at the project root; None where git is absent or the command fails."""
    exe = shutil.which("git")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, *args], capture_output=True, text=True, cwd=cfg.root, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def inbox_items(cfg):
    """(line number, line) of every line the directions file's inbox holds outside a comment; None where there
    is no directions file or no `## Inbox` section in it."""
    if not cfg.directions.is_file():
        return None
    ls = cfg.directions.read_text(encoding="utf-8").split("\n")
    sec = _section(ls, "Inbox")
    if sec is None:
        return None
    out, comment = [], False
    for i in range(sec[0] + 1, sec[1]):
        text = ls[i]
        if comment:
            if "-->" not in text:
                continue
            text, comment = text.split("-->", 1)[1], False
        text = re.sub(r"<!--.*?-->", "", text)
        if "<!--" in text:
            text, comment = text.split("<!--", 1)[0], True
        if text.strip():
            out.append((i + 1, ls[i]))
    return out


def close_check(cfg, recs, owner, today):
    """What a machine can see of a session's close, as (failures, what was checked, what could not be): the
    inbox emptied; every active task in the working session's hand or a decision owner's; the log's top entry dated today where the
    tree changed since the commit of the newest committed entry; every record changed since that commit named
    by an entry from the top down to it."""
    fails, checked, undecided = [], [], []

    def fail(path, msg):
        fails.append({"code": "STATE", "id": None, "path": path, "msg": msg})

    items = inbox_items(cfg)
    if items is None:
        undecided.append(f"the inbox: no `## Inbox` section in {rel(cfg, cfg.directions)}" if cfg.directions.is_file()
                         else f"the inbox: no directions file at {rel(cfg, cfg.directions)}")
    else:
        checked.append("the inbox")
        if items:
            fail(f"{rel(cfg, cfg.directions)}:{items[0][0]}", f"the inbox holds {len(items)} line(s), from {items[0][1].strip()!r}: "
                 "each item is turned into a record or acted on, named in the log, and removed")
    checked.append("the hand")
    for r in sorted(recs.values(), key=lambda r: r.id):
        if r.type == "task" and r["state"] == "active" and r["owner"] != owner and r["owner"] not in cfg.decision_owners:
            fail(rel(cfg, r.path), f"{r.id} is active under {r['owner']}, not under {owner}, the working session")
    why = None if cfg.log and cfg.log.is_file() else ("none is bound (`[paths] log`)" if not cfg.log else f"{rel(cfg, cfg.log)} does not exist")
    ls = cfg.log.read_text(encoding="utf-8").split("\n") if why is None else []
    entries = log_entries(ls)
    if why is None and not entries:
        why = f"{rel(cfg, cfg.log)} has no `## ` entry"
    if why is None and git(cfg, "rev-parse", "--is-inside-work-tree") is None:
        why = f"git is absent, or {cfg.root} is not in a work tree"
    if why is None and not (git(cfg, "log", "-n", "1", "--format=%H", "--", rel(cfg, cfg.log)) or "").strip():
        why = f"{rel(cfg, cfg.log)} has never been committed"
    base, named = None, []
    for s, e, d in entries if why is None else []:
        named.append("\n".join(ls[s:e]))
        base = (git(cfg, "log", "-n", "1", "--format=%H", "-S", ls[s], "--", rel(cfg, cfg.log)) or "").strip()
        if base:
            base_date = d
            break
    if why is None and not base:
        why = f"no entry of {rel(cfg, cfg.log)} is committed"
    if why is not None:
        undecided.append(f"the log's date and the records it names: {why}")
        return fails, checked, undecided
    checked += ["the log's date", "the records the log names"]
    changed = set((git(cfg, "diff", "--name-only", "--relative", base) or "").split("\n")) \
        | set((git(cfg, "ls-files", "--others", "--exclude-standard") or "").split("\n"))
    changed.discard("")
    top, _, top_date = entries[0]
    if top_date != today and changed:
        fail(f"{rel(cfg, cfg.log)}:{top + 1}", f"the top entry is dated {top_date or 'nothing'}, not today ({today}), and {len(changed)} "
             f"file(s) changed since {base[:12]}, the commit of the entry of {base_date}: today's entry is written (`flow log add FILE`)")
    ids = {}
    for p in sorted(changed):
        m = cfg.id_re.match(Path(p).name)
        if m and (cfg.root / p).resolve().is_relative_to(cfg.research.resolve()):
            ids.setdefault(f"{m.group(1)}-{m.group(2)}", p)
    text = "\n".join(named)
    for i, p in sorted(ids.items()):
        if not re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(i), text):
            fail(p, f"{i} changed since {base[:12]}, the commit of the log's entry of {base_date}, and no entry since names it")
    return fails, checked, undecided


# --- the log: an entry written at its top, the old ones archived by month ------------
#
# Dated entries, newest first, each a `## YYYY-MM-DD — headline` opening with a `**State.**`
# paragraph.  `flow log add` writes one at the top, reflowed and linted as a record is;
# `flow log archive` moves the old ones verbatim into one file per month beside the log.

LOG_ENTRY = re.compile(r"^## (\d{4}-\d{2}-\d{2}) — \S")
LOG_POINTER = re.compile(r"^Entries dated before (\d{4}-\d{2}-\d{2}) are archived ")
LINK_DEF = re.compile(r"^ {0,3}\[([^\]]+)\]:\s*\S")


def front_end(lines):
    """The index of the first line after a leading front matter block; 0 where there is none."""
    if lines and lines[0] == FENCE:
        end = next((i for i in range(1, len(lines)) if lines[i] == FENCE), None)
        return end + 1 if end is not None else 0
    return 0


def log_entries(lines):
    """(start, end, date) of every `## ` entry of a log's lines, after a front matter block and outside code fences;
    the date None where the heading opens with none.  The last entry ends before a block of link reference
    definitions closing the file, which is the file's rather than the entry's."""
    heads, fence, fenced = [], None, set()
    for i in range(front_end(lines), len(lines)):
        was, fence = fence, fence_after(fence, lines[i])
        if was or fence:
            fenced.add(i)
        elif lines[i].startswith("## "):
            m = re.match(r"^## (\d{4}-\d{2}-\d{2})\b", lines[i])
            heads.append((i, m.group(1) if m else None))
    end = len(lines)
    if heads:
        j = end
        while j > heads[-1][0] + 1 and j - 1 not in fenced and (not lines[j - 1].strip() or LINK_DEF.match(lines[j - 1])):
            j -= 1
        end = next((k for k in range(j, end) if LINK_DEF.match(lines[k])), end)  # the blank lines before it the entry's
    return [(i, heads[k + 1][0] if k + 1 < len(heads) else end, d) for k, (i, d) in enumerate(heads)]


def is_date(s):
    try:
        return bool(ISO.match(s)) and bool(dt.date.fromisoformat(s))
    except ValueError:
        return False


def bound_log(cfg):
    if not cfg.log:
        raise Refused("no log is bound: `[paths] log` in flow.toml names it")
    if not cfg.log.is_file():
        raise Refused(f"the log {rel(cfg, cfg.log)} does not exist")
    return cfg.log


def entry_lines(lines, start, end):
    """An entry's lines, verbatim but for the blank lines after it."""
    out = lines[start:end]
    while out and not out[-1].strip():
        out.pop()
    return out


def link_label(text):
    """A link label as CommonMark matches one: case and runs of white space aside."""
    return " ".join(text.split()).casefold()


def link_uses(lines):
    """The labels `lines` use as link references, `[text][label]`, `[label][]` or `[label]`, outside code fences
    and code spans; a definition line and an inline link's text are none."""
    out, fence = set(), None
    for line in lines:
        was, fence = fence, fence_after(fence, line)
        if not was and not fence and not LINK_DEF.match(line):
            out.update(link_label(x) for x in re.findall(r"\[([^\[\]]+)\](?!\()", re.sub(r"`[^`]*`", "", line)))
    return out


def cmd_log_add(cfg, a, today):
    """The entry FILE holds, reflowed, at the top of the log: refused when it does not open with its dated
    heading and its State paragraph, or is older than the top entry.  Returns (files written, what was done)."""
    log = bound_log(cfg)
    lines = read_body(a.file).strip("\n").split("\n")
    m = LOG_ENTRY.match(lines[0])
    if not m or not is_date(m.group(1)):
        raise Refused(f"{a.file}: an entry opens with its heading, `## YYYY-MM-DD — headline`, not {lines[0]!r}")
    if m.group(1) > today:
        raise Refused(f"{a.file}: the entry is dated {m.group(1)}, after today ({today})")
    if not "\n".join(lines[1:]).strip().startswith("**State.**"):
        raise Refused(f"{a.file}: an entry's first paragraph is its `**State.**` paragraph, the one a cold session trusts")
    if len(log_entries(lines)) > 1:
        raise Refused(f"{a.file} holds more than one entry; the log takes one at a time")
    ls = log.read_text(encoding="utf-8").split("\n")
    entries = log_entries(ls)
    if entries and entries[0][2] and m.group(1) < entries[0][2]:
        raise Refused(f"the log runs newest first, and its top entry is dated {entries[0][2]}, after {m.group(1)}")
    at = entries[0][0] if entries else len(ls)
    parts = ("\n".join(ls[:at]).rstrip("\n"), cfg.reflow("\n".join(lines)).rstrip("\n"), "\n".join(ls[at:]).rstrip("\n"))
    write_linted(cfg, {log: "\n\n".join(x for x in parts if x) + "\n"})
    return [log], f"added {lines[0][3:]} at the top of {rel(cfg, log)}"


def cmd_log_archive(cfg, a, today):
    """Every entry dated before --before moved verbatim, newest first, into one file per month in the log's
    archive directory, and a pointer to it under the log's title; the top entry always stays.  A link definition
    closing the log goes to every file whose text uses its label, and stays in the log where the log's own text
    uses it too or no file does."""
    log = bound_log(cfg)
    if not is_date(a.before):
        raise Refused(f"--before {a.before!r} is not a date")
    ls = log.read_text(encoding="utf-8").split("\n")
    entries = log_entries(ls)
    undated = [s for s, _, d in entries if d is None]
    if undated:
        raise Refused(f"{rel(cfg, log)}:{undated[0] + 1}: {ls[undated[0]]!r} opens with no date, and the archive files an entry by its date")
    old = [e for e in entries if e[2] < a.before]
    if not old:
        raise Refused(f"no entry of {rel(cfg, log)} is dated before {a.before}")
    if entries[0][2] < a.before:
        raise Refused(f"the top entry is dated {entries[0][2]}, before {a.before}: it stays, the one a cold session trusts")
    fm = front_end(ls)  # a `# comment` of the front matter is no title
    title = next((l[2:].strip() for l in ls[fm:entries[0][0]] if l.startswith("# ")), "Log")
    months = defaultdict(list)
    for s, e, d in old:
        months[d[:7]].append((d, entry_lines(ls, s, e)))
    drop = {i for s, e, _ in old for i in range(s, e)}
    foot = entries[-1][1]  # the link definitions closing the log start here, where it has any
    defs = {i: link_label(LINK_DEF.match(ls[i]).group(1)) for i in range(foot, len(ls)) if LINK_DEF.match(ls[i])}
    texts, used = {}, link_uses(l for i, l in enumerate(ls[:foot]) if i not in drop)
    gone = set()
    for month, moved in sorted(months.items()):
        path = cfg.log_archive / f"{month}.md"
        had = path.read_text(encoding="utf-8").split("\n") if path.is_file() else None
        held = log_entries(had) if had else []
        head = entry_lines(had, 0, held[0][0] if held else len(had)) if had else [f"# {title} — {month}"]
        tail = entry_lines(had, held[-1][1], len(had)) if held else []  # the link definitions closing it, kept
        merged = sorted(moved + [(d or "", entry_lines(had, s, e)) for s, e, d in held], key=lambda x: x[0], reverse=True)
        blocks = ["\n".join(head)] + ["\n".join(b) for _, b in merged]
        uses = link_uses("\n".join(blocks).split("\n"))
        own = {link_label(m.group(1)) for l in had or [] for m in [LINK_DEF.match(l)] if m}
        tail += [ls[i] for i, lab in defs.items() if lab in uses and lab not in own]
        gone.update(i for i, lab in defs.items() if lab in uses and lab not in used)
        texts[path] = "\n\n".join(blocks + (["\n".join(tail)] if tail else [])) + "\n"
    rest = [l for i, l in enumerate(ls[:foot]) if i not in drop]
    left = [l for i, l in enumerate(ls) if i >= foot and i not in gone]
    rest += [l for k, l in enumerate(left) if l.strip() or k and left[k - 1].strip()]  # no blank line doubled
    above = range(fm, log_entries(rest)[0][0])  # the pointer stands above the entries, never inside one
    since = max([a.before] + [m.group(1) for i in above for m in [LOG_POINTER.match(rest[i])] if m])
    link = Path(os.path.relpath(cfg.log_archive, log.parent)).as_posix()
    pointer = f"Entries dated before {since} are archived verbatim, newest first, one file per month in [{link}/]({link}/)."
    at = next((i for i in above if LOG_POINTER.match(rest[i])), None)
    if at is not None:
        rest[at] = pointer
    else:
        h = next((i for i in above if rest[i].startswith("# ")), None)
        at = h + 1 if h is not None else fm  # under the title, else under the front matter
        rest[at:at] = ([""] if at else []) + [pointer] + ([] if at < len(rest) and not rest[at].strip() else [""])
    texts[log] = "\n".join(rest).rstrip("\n") + "\n"
    write_linted(cfg, texts)
    return list(texts), (f"moved {len(old)} entr{'y' if len(old) == 1 else 'ies'} dated before {a.before} into "
                         f"{', '.join(rel(cfg, p) for p in texts if p != log)}; a pointer under the title of {rel(cfg, log)}")


# --- the reflow of the project's other prose ----------------------------------------

def reflow_misses(cfg, text):
    """(line number, line) of every line of `text` the reflow changes; a leading front matter block is not prose."""
    lines = text.split("\n")
    skip = 0
    if lines[0] == FENCE:
        end = next((i for i in range(1, len(lines)) if lines[i] == FENCE), None)
        skip = end + 1 if end is not None else 0
    body = lines[skip:]
    new = cfg.reflow("\n".join(body)).split("\n")
    out = set()
    for tag, i1, i2, _, _ in difflib.SequenceMatcher(None, body, new, autojunk=False).get_opcodes():
        if tag != "equal":
            out.update((skip + i + 1, body[i]) for i in range(i1, min(max(i2, i1 + 1), len(body))))
    return sorted(out)


def cmd_reflow(cfg, a):
    """`--check PATH…`: the lines of each file (a directory's Markdown files) the reflow changes.  `--as DEST
    DRAFT`: the draft's lines the reflow changes, and the markdownlint violations the draft adds appended to
    DEST, under the configuration a record's write runs with; nothing is written.  Returns (problems, coverage)."""
    problems = []
    if a.check:
        files = []
        for p in map(Path, a.check):
            if not p.exists():
                raise NotRun(f"{p}: no such file or directory")
            files += sorted(p.rglob("*.md")) if p.is_dir() else [p]
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
            except UnicodeDecodeError as e:
                raise Refused(f"{f}: not UTF-8 ({e.reason} at byte {e.start})")
            problems += [{"code": "REFLOW", "id": None, "path": f"{rel(cfg, f)}:{n}", "msg": line} for n, line in reflow_misses(cfg, text)]
        return problems, f"{len(files)} file(s) read; reflow via {cfg.reflow_source}"
    dest, draft = map(Path, a.as_)
    if not draft.is_file():
        raise NotRun(f"{draft}: no such file")
    text = read_body(draft).strip("\n")
    problems += [{"code": "REFLOW", "id": None, "path": f"{draft}:{n}", "msg": line} for n, line in reflow_misses(cfg, text)]
    had = dest.read_text(encoding="utf-8").rstrip("\n") if dest.is_file() else ""
    fd, name = tempfile.mkstemp(prefix=f".{dest.stem}.", suffix=".flow-draft.md", dir=dest.parent if dest.parent.is_dir() else cfg.root)
    os.close(fd)
    tmp = Path(name)
    try:
        tmp.write_text(had + "\n" if had else "", encoding="utf-8")
        before = mdlint(cfg, tmp)
        tmp.write_text(had + "\n\n" + text + "\n" if had else text + "\n", encoding="utf-8")
        after = mdlint(cfg, tmp)
    finally:
        tmp.unlink(missing_ok=True)
    if after is None:
        return problems, f"reflow via {cfg.reflow_source}; markdownlint ABSENT, so the draft is not linted"
    # DEST's own lines keep their numbers with the draft appended, so a violation reported in both runs, at its
    # line and with its words, is DEST's and not the draft's
    had_already = set(before[1].splitlines())
    off = len(had.split("\n")) + 1 if had else 0  # the draft's first line is the file's line off + 1
    for ln in after[1].splitlines():
        m = re.search(r":(\d+)(?::\d+)?\s+(?:[a-z]+\s+)?(MD\d{3})", ln)  # `file:line[:column] [severity] MDnnn/name …`
        if m and ln not in had_already:
            n = int(m.group(1))
            where = f"{draft}:{n - off}" if n > off else f"{dest}:{n}"
            problems.append({"code": "MARKDOWNLINT", "id": None, "path": where, "msg": ln[m.start(2):]})
    return problems, f"reflow via {cfg.reflow_source}; markdownlint as at {dest}, the draft appended to it"


# --- the dashboard's page manifest ------------------------------------------------
#
# A dashboard host asks `flow --json pages` for this and renders every page from the
# command each route names, with `--json`; it reads no record file itself.

def pages_manifest(cfg):
    ids = r"\b(?:%s)-\d+\b" % "|".join(re.escape(cfg.prefix[t]) for t in cfg.kinds)
    nav = [{"label": "Records", "path": "/flow"}]
    for t in cfg.kinds:
        live = {"idea": "open", "question": "open", "task": "ready"}.get(t)
        nav.append({"label": t.capitalize() + "s", "path": f"/flow/list?type={t}" + (f"&state={live}" if live else "")})
    if cfg.directions.is_file():
        nav.append({"label": "Directions", "path": "/flow/directions"})
    nav.append({"label": "Check", "path": "/flow/check"})
    columns = ["id", "type", "state"] + (["status"] if cfg.has("finding") else []) + ["kind", "owner", "rank", "summary"]
    params = ["type", "state", "kind", "tag", "owner", "grep"] + (["status", "paper"] if cfg.has("finding") else []) \
        + (["question"] if cfg.has("question") else [])
    flags = ["ranked"] + (["parked"] if cfg.has("question") else [])
    return {
        "component": "flow", "title": "Records", "mount": "/flow", "nav": nav,
        "links": [{"pattern": ids, "path": "/flow/r/{0}"}],
        "routes": [
            {"path": "/flow", "view": "markdown", "run": ["index", "--print"], "field": "text", "title": "Records"},
            {"path": "/flow/list", "view": "list", "run": ["find"], "params": params, "flags": flags,
             "columns": columns, "link": {"column": "id", "path": "/flow/r/{id}"}, "title": "Records"},
            {"path": "/flow/r/{id}", "view": "record", "run": ["show", "{id}"], "title": "{id}",
             "fields": "records.0", "body": "body", "hide": ["id"],
             "sections": [{"field": "links", "title": "Links", "as": "refs"},
                          {"field": "backlinks", "title": "Back-references", "as": "refs"}]},
            {"path": "/flow/directions", "view": "markdown", "run": ["directions"], "field": "text", "title": "Directions"},
            {"path": "/flow/state", "view": "lines", "run": ["state"], "field": "lines", "title": "State"},
            {"path": "/flow/check", "view": "check", "run": ["check"], "title": "Check"},
        ],
    }


# --- init --------------------------------------------------------------------------

INIT_TOML = """# flow.toml — the flow's bindings for THIS project.  Every path is relative to this file's
# directory.  The `flow` skill reads it; the project's own instructions name the log, the
# gates and the rest.

[paths]
records = "{dir}"                 # one file per record: ideas/ tasks/ questions/ findings/ archive/
index = "{dir}/INDEX.md"          # generated by `flow index`; `flow check` fails on drift
archive = "{dir}/archive"         # closed tasks move here at their closing transition
{directions}{log}# reflow_module = "scripts/reflow.py"   # exports reflow_text(text): one sentence per line; built-in otherwise
# markdownlint_config = ".markdownlint.jsonc"  # a NEW violation after a write reverts it

[prefixes]
idea = "idea"
question = "question"
task = "task"
finding = "finding"
id_width = 4

[hand]
# Active tasks an owner may hold; 0 = unlimited.  `init` made the last owner named here the
# decision owner — the person the owner-only tasks go to, never ranked — but what binds is
# `decision_owners` under [task] below.
{owners}

[task]
kinds = [{kinds}]
default_kind = "{default_kind}"
question_optional_kinds = ["upkeep", "community", "decision"]   # the kinds a task may be minted in with no question
decision_kinds = ["decision"]     # owner-only work: never ranked; a decision gates a landing, never a start
decision_owners = ["{decision_owner}"]   # a task of a decision kind is minted under this owner's hand; empty for none
{research}[index]
recent_findings = 10
oldest_ideas = 5
"""

INIT_RESEARCH = """[question]
sizes = ["small", "medium", "large"]

[finding]
# The four status roles, named as the project says them: verified needs a declaration of the
# manifest, stated a document's statement or row, empirical a probe, refuted a guard or a probe.
verified = "verified"
stated = "stated"
empirical = "empirical"
refuted = "refuted"
# Findings shard by the document that registers them ({dir}/findings/<paper>/).
shards = []

[evidence]
# A declaration manifest: a text file listing `Module.Path name` per line (a prover library's
# declaration list is the instance); `manifest_roots` are the directories a `Path.ext#name`
# item is looked up under.  Absent, declaration evidence is unchecked and the check says so.
# manifest = ["scripts/decls.txt"]
# manifest_roots = ["src"]
# manifest_extension = "lean"   # required beside manifest: the extension the cited paths carry
# A probes register: a Markdown table whose first column names each self-asserting script.
# probes = "probes/README.md"

[library]
# The reference library, when the project has one: the command that answers `keys`.  Unset, the
# flow asks the library skill installed beside the flow skill, else `library` on PATH, either only
# where a library.toml stands at the root; `command = []` asks none.
# command = ["library"]

"""

INSTRUCTIONS = """What the project's instructions (CLAUDE.md, AGENTS.md) should now carry, in their words:

- The records are `{records}/`, one file each, read through `flow find`, `flow show ID`
  and `flow state`, never by a glob; `flow.toml` binds the names.
- A record's state changes only through a `flow` transition; bodies are edited by hand,
  one sentence per line; `flow check` runs before a commit (a hook where the project has them).
- The ranked list in `{records}/INDEX.md` is the schedule: a session works from the top.
{log_line}- Where the project keeps a registry of its deliverables — what it produces and in what order —
  that file is named here and nowhere else; none is needed to start.
- `flow state` prints the cold-start bundle: the inbox slot, the ranked list and the log's top entry.
The `flow` skill is installed for the project's agent as well (the `research` plugin, or `npx skills add`).
"""

LOG_BOUND = """- The log is `{log}`: dated entries, newest first, each `## YYYY-MM-DD — headline` opening with a
  `**State.**` paragraph, the top one the paragraph a cold session trusts; an entry is written by
  `flow log add FILE` in the same change as the transition it records.
"""
LOG_UNBOUND = """- The log is not bound yet: `[paths] log` in `flow.toml` names it (dated entries, newest first,
  each `## YYYY-MM-DD — headline` opening with a `**State.**` paragraph, the top one authoritative).
"""


def do_init(root, a):
    """Write flow.toml, the record directories and the index; refuse over an existing flow.toml."""
    toml = root / "flow.toml"
    if toml.is_file() and not a.force:
        raise Refused(f"{toml} exists (use --force to overwrite the bindings file alone)")
    kinds = list(TYPES)
    owners = a.owner or ["agent", "owner"]
    for o in owners:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", o):
            raise Refused(f"--owner {o!r}: an owner is one word of letters, digits, `_` and `-` (it is a key of flow.toml)")
    task_kinds = ["work", "design", "prose", "survey", "upkeep", "community", "decision"]
    text = INIT_TOML.format(
        dir=a.records,
        directions=f'directions = "{a.records}/directions.md" # owner-owned: an `## Inbox` slot and `## Directions`\n',
        log=(f'log = "{a.log}"                 # the dated log whose top entry `flow state` prints\n'
             f'log_archive = "{Path(a.log).with_name(Path(a.log).stem + "-archive").as_posix()}"   '
             '# `flow log archive` moves the old entries here verbatim, one file per month\n') if a.log else
            '# log = "WORKLOG.md"             # the dated log whose top entry `flow state` prints\n'
            '# log_archive = "WORKLOG-archive"   # `flow log archive` moves the old entries here verbatim, one file per month\n',
        owners="\n".join(f"{o} = {0 if o == owners[-1] and len(owners) > 1 else 2}" for o in owners),
        kinds=", ".join(f'"{k}"' for k in task_kinds), default_kind=task_kinds[0],
        decision_owner=owners[-1] if len(owners) > 1 else owners[0],
        research=INIT_RESEARCH.format(dir=a.records))
    written = []
    toml.write_text(text, encoding="utf-8")
    written.append("flow.toml")
    for d in [f"{a.records}/{t}s" for t in kinds] + [f"{a.records}/archive"]:
        (root / d).mkdir(parents=True, exist_ok=True)
        keep = root / d / ".gitkeep"
        if not any((root / d).iterdir()):
            keep.write_text("")
            written.append(f"{d}/.gitkeep")
    cfg = Config(root)
    if not cfg.directions.is_file():
        cfg.directions.write_text(
            "# The owner's directions\n\n## Inbox\n\n## Directions\n\n"
            "<!-- one bullet per direction, in this form; a question's `direction` names one by its bold name:\n"
            "- **Name** (YYYY-MM-DD) — what interests the owner, in a sentence.\n-->\n", encoding="utf-8")
        written.append(rel(cfg, cfg.directions))
    if cfg.log and not cfg.log.is_file():
        cfg.log.parent.mkdir(parents=True, exist_ok=True)
        cfg.log.write_text(f"# Log\n\n## {dt.date.today().isoformat()} — the flow set up\n\n"
                           "**State.** Nothing is in flight; the records are empty.\n", encoding="utf-8")
        written.append(rel(cfg, cfg.log))
    cfg.index.write_text(render_index(cfg, load_all(cfg)), encoding="utf-8")
    written.append(rel(cfg, cfg.index))
    return written


# --- selftest ----------------------------------------------------------------

SELFTEST_TOML = """
[paths]
records = "research"
index = "research/INDEX.md"
archive = "research/archive"
directions = "research/directions.md"
[evidence]
manifest = "decls.txt"
manifest_roots = "lean"
manifest_extension = "lean"
probes = "probes/README.md"
[prefixes]
idea = "idea"
question = "question"
task = "task"
finding = "finding"
id_width = 4
[hand]
root = 2
prover = 1
author = 0
[task]
kinds = ["lean", "design", "prose", "survey", "upkeep", "community", "decision"]
[finding]
verified = "lean-verified"
stated = "proven"
empirical = "empirical"
refuted = "refuted"
shards = ["alpha"]
"""

SOURCE = Path(__file__).read_text(encoding="utf-8")


def selftest():
    failures = []

    def expect(name, cond):
        print(f"  {'ok ' if cond else 'BAD'} {name}")
        if not cond:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "flow.toml").write_text(SELFTEST_TOML)
        (root / "decls.txt").write_text("module Lib.Foo 1\nmodule Lib.Bar 1\nLib.Foo lemma_L\nLib.Bar lemma_B\nprivate Lib.Foo helper\n")
        (root / "lean" / "Lib").mkdir(parents=True)
        (root / "lean" / "Lib" / "Foo.lean").write_text("theorem lemma_L : True := trivial\n")
        (root / "lean" / "Lib" / "Bar.lean").write_text("theorem lemma_B : True := trivial\n")
        (root / "papers").mkdir()
        (root / "papers" / "alpha.md").write_text("# Alpha\n\n**Theorem 2.1.** Something.\n\n| ID | Claim |\n|---|---|\n| FV-1 | the claim |\n")
        (root / "probes").mkdir()
        (root / "probes" / "p.py").write_text("print('ok')\n")
        (root / "probes" / "README.md").write_text("| file | claim |\n|---|---|\n| `p.py` | it |\n")
        (root / "research").mkdir()
        (root / "research" / "directions.md").write_text("# Directions\n\n- **Bridge** (minted today) — the words.\n")
        cfg = Config(root)
        today = "2026-09-25"

        def run(argv, ok=True):
            rc, payload = dispatch(cfg, argv, today=today, as_json=True, quiet=True)
            expect(" ".join(argv[:2]) + (" refused" if not ok else ""), (rc == 0) == ok)
            if (rc == 0) != ok:
                for pr in payload["problems"]:
                    print("      ", pr["code"], pr.get("path") or pr.get("id"), pr["msg"])
            return payload

        p = run(["capture", "an idea", "--source", "test"])
        idea = p["created"][0]
        p = run(["frame", idea, "--summary", "Does A imply B?", "--kill", "a finite counterexample", "--direction", "Bridge"])
        q = p["created"][0]
        run(["rank", q, "1", "--why", "w", "--first-move", "m", "--direction", "Nowhere"], ok=False)  # not in the directions file
        p = run(["refine", q, "--task", "prove L", "lean", "--task", "design the route", "design", "--subq", "sub question", "kill it"])
        t1, t2 = p["created"][0], p["created"][1]
        run(["rank", t1, "1", "--why", "w", "--first-move", "m", "--direction", "Bridge"], ok=False)  # a direction is a question's
        run(["draw", t1, "--owner", "root"])
        run(["draw", t2, "--owner", "root"])
        p = run(["refine", p["created"][2], "--task", "third", "lean"])
        t3 = p["created"][0]
        run(["draw", t3, "--owner", "root"], ok=False)  # hand full
        run(["return", t2, "--note", "later"])
        tree = lambda: {x: x.read_text(encoding="utf-8") for x in sorted((root / "research").rglob("*.md"))}
        before = tree()
        run(["make", t1, "--finding", "L holds", "lean-verified", "Lib/Foo.lean#lemma_L", "--task", "after", "lean",
             "--idea", "aside", "--resolution", "missing.md"], ok=False)
        expect("a make refused after its finding is minted leaves the tree as it was", tree() == before)
        p = run(["make", t1, "--finding", "L holds", "lean-verified", "Lib/Foo.lean#lemma_L", "papers/alpha.md#FV-1"])
        f = p["created"][0]
        expect("finding sharded by paper", "findings/alpha/" in p["records"][0]["path"])
        expect("done task archived", "research/archive/" in p["records"][-1]["path"])
        run(["make", t1], ok=False)  # already done
        run(["answer", q, "--by", f], ok=False)  # t2 is still open on q
        run(["draw", t2, "--owner", "root"])
        (root / "wall.md").write_text("The route hits a wall.\n")
        p = run(["abort", t2, "--reason", "wall", "--finding", "the route fails", "refuted", "probes/p.py", "--resolution", str(root / "wall.md")])
        body = Path(root / p["records"][-1]["path"]).read_text(encoding="utf-8")
        expect("a resolution is appended under its date, and the task's notes stay",
               "returned: later" in body and body.rstrip().endswith(f"{today} — resolution:\n\nThe route hits a wall."))
        for had in ("", "A note.\n"):  # a resolution opening with a heading, on an empty body and after a note
            r = type("R", (), {"body": had})()
            append_note(r, today, "resolution:", "\n## Result\n\nIt is done.\n\n")
            expect("a resolution file's text is set apart from its dated line by one blank line" + (", after a note" if had else ", on an empty body"),
                   render({"id": "task-0001"}, r.body).endswith(f"---\n\n{had and had + chr(10)}{today} — resolution:\n\n## Result\n\nIt is done.\n"))
        run(["answer", q, "--by", f])
        run(["kill", t3, "--reason", "not needed"])
        run(["capture", "a second idea"])
        run(["frame", "idea-0002", "--summary", "Q2", "--kill", "k", "--direction", "Nowhere"], ok=False)
        run(["frame", "idea-0002", "--summary", "Q2", "--kill", "k"])
        run(["rank", "question-0003", "1", "--why", "now", "--first-move", "none yet"])
        run(["set", "question-0003", "kill", "a sharper kill"])
        run(["set", "question-0003", "rider", "on"], ok=False)  # a question carries no rider
        run(["set", "question-0003", "size", "huge"], ok=False)  # not a size
        run(["set", "question-0003", "state", "answered"], ok=False)  # a transition's field
        run(["capture", "an idea to park"])
        run(["frame", "idea-0003", "--summary", "Q to park", "--kill", "k"])
        run(["park", "question-0004", "--reason", "waiting"])
        run(["rank", "question-0004", "2", "--why", "x", "--first-move", "y"], ok=False)  # parked
        run(["park", "question-0004", "--reason", "again"], ok=False)  # parked already
        run(["index"])
        p = run(["check"])
        expect("check green on the happy path", not p["problems"])
        run(["draw", "task-0004", "--owner", "prover"], ok=False)  # does not exist yet
        run(["capture", "idea four"])
        run(["frame", "idea-0004", "--summary", "Q4", "--kill", "k"])
        p = run(["refine", "question-0005", "--task", "t", "lean"])
        t4 = p["created"][0]
        run(["draw", t4, "--owner", "prover"])
        run(["make", t4, "--finding", "bad", "lean-verified", "Lib/Foo.lean#nope"], ok=False)
        run(["make", t4, "--finding", "bad", "lean-verified", "Lib/Bar.lean#lemma_L"], ok=False)  # declared in Lib.Foo
        run(["make", t4, "--finding", "bad", "proven", "Lib/Foo.lean#lemma_L"], ok=False)
        run(["make", t4, "--finding", "bad", "empirical", "papers/alpha.md#Theorem 2.1"], ok=False)
        run(["make", t4, "--finding", "fine", "proven", "papers/alpha.md#Theorem 2.1"])
        # a question whose kill names work is answered by the done tasks drawn under it
        run(["answer", "question-0005", "--by", t1], ok=False)  # done, but drawn under another question
        run(["answer", "question-0005", "--by", t4])
        run(["index"])
        p = run(["task", "an upkeep chore", "--kind", "upkeep"])
        rt = p["created"][0]
        run(["set", rt, "rider", "on"])
        run(["set", rt, "kill", "k"], ok=False)  # a task carries no kill
        run(["set", t4, "rider", "on"], ok=False)  # a done task rides nothing
        recs = load_all(cfg)
        expect("set wrote the rider and the kill", recs[rt]["rider"] is True
               and recs["question-0003"]["kill"] == "a sharper kill")
        run(["set", rt, "rider", "off"])
        fs = [r.id for r in load_all(cfg).values() if r.type == "finding"]
        run(["set", fs[1], "depends_on", fs[0]])
        run(["set", fs[0], "depends_on", fs[1]], ok=False)  # would close a cycle
        run(["set", fs[0], "depends_on", fs[0]], ok=False)  # itself
        run(["set", fs[0], "depends_on", "question-0003"], ok=False)  # not a finding
        run(["set", fs[1], "depends_on", "none"])
        run(["task", "a lean task with no question", "--kind", "lean"], ok=False)
        cfg.decision_owners = ("author",)  # refine and make mint a decision task as `flow task` does
        _JOURNAL.clear()
        minted = _mk_tasks(cfg, load_all(cfg), [["decide the route", "decision"]], None, [], today)
        rollback()
        cfg.decision_owners = ()
        expect("a decision task refine or make mints is under the decision owner's hand", minted[0]["owner"] == "author")
        # the reference library, asked through its `keys` answer (a stub stands for it here)
        stub = root / "lib_stub.py"
        stub.write_text('import json\nprint(json.dumps({"ok": True, "cite_prefix": "lib:", "cards": '
                        '{"jen1990": {"state": "registered", "grade": "parts", "extracts": ["lemma"]}, '
                        '"aside": {"state": "excluded", "grade": "unread"}}, "problems": []}))\n')
        cfg.library_cmd = [sys.executable, str(stub)]
        run(["capture", "an idea citing lib:jen1990 twice over, lib:jen1990, and lib:aside"])
        run(["index"])
        p = run(["check"])
        expect("check green with a cited key the library holds", not p["problems"])
        expect("the coverage counts the cited keys by grade and the excluded ones",
               p["coverage"]["library"] == {"cited": 2, "records": 1, "grades": {"parts": 1, "unread": 1}, "excluded": 1})

        # a closing transition closes the ranks up (question-0003 holds rank 1; a second ranked record closes)
        run(["capture", "an idea to rank and close"])
        run(["frame", "idea-0005", "--summary", "Q to close", "--kill", "k"])
        run(["rank", "question-0006", "2", "--why", "w", "--first-move", "m"])
        run(["rank", "question-0003", "--clear"])
        expect("clearing a rank closes the ranks up", load_all(cfg)["question-0006"]["rank"] == 1)
        run(["rank", "question-0003", "2", "--why", "now", "--first-move", "none yet"])
        p = run(["kill", "question-0006", "--reason", "closed to test the ranks"])
        expect("killing a ranked question renumbers the rest and reports them", "question-0003" in p["changed"]
               and load_all(cfg)["question-0003"]["rank"] == 1 and not validate(cfg, load_all(cfg), today)[0])
        run(["rank", "question-0002", "1", "--why", "w", "--first-move", "m"], ok=False)  # rank 1 is held
        p = run(["rank", "question-0002", "1", "--insert", "--why", "w", "--first-move", "m"])
        expect("rank --insert puts a new record at N in one step and moves the rest down, reporting them",
               [load_all(cfg)[i]["rank"] for i in ("question-0002", "question-0003")] == [1, 2] and "question-0003" in p["changed"])
        run(["rank", "question-0003", "1", "--insert"])
        expect("rank --insert moves a ranked record up, the rest closing round it",
               [load_all(cfg)[i]["rank"] for i in ("question-0002", "question-0003")] == [2, 1] and not validate(cfg, load_all(cfg), today)[0])
        run(["rank", "question-0002", "3", "--insert"], ok=False)  # past the end of the ranks
        run(["rank", "question-0002", "--clear", "--insert"], ok=False)  # --insert takes a rank
        run(["rank", "question-0002", "--clear"])
        run(["rank", "idea-0001", "1", "--why", "w", "--first-move", "m"], ok=False)  # an idea is never ranked
        run(["rank", "idea-0001", "--clear"], ok=False)
        # refine reaches a decomposed question; a parked one is unparked first; kill refuses live tasks
        run(["capture", "an idea to refine twice"])
        run(["frame", "idea-0006", "--summary", "Q refined twice", "--kill", "k"])
        run(["refine", "question-0007", "--task", "first", "lean"])
        p = run(["refine", "question-0007", "--task", "second", "lean"])
        expect("refine adds a task to a decomposed question", p["created"] and load_all(cfg)["question-0007"]["state"] == "decomposed")
        run(["kill", "question-0007", "--reason", "x"], ok=False)  # two ready tasks under it
        run(["refine", "question-0004", "--task", "t", "lean"], ok=False)  # parked
        (root / "refined.md").write_text("Split by the size of the case.\n")
        p = run(["refine", "question-0007", "--task", "third", "lean", "--body", str(root / "refined.md")])
        recs = load_all(cfg)
        expect("refine's body is appended to the question under its date, the answer names it, and the task minted carries none",
               recs["question-0007"].body.rstrip().endswith(f"{today} — refined:\n\nSplit by the size of the case.")
               and p["body_appended_to"] == "question-0007" and recs[p["created"][0]].body == "")
        run(["find", "--grep", "["], ok=False)
        run(["index"])
        p = run(["check"])
        expect("check green after the rank and refine round", not p["problems"])

        # planted defects: each must be caught by the validator with its code
        planted = set()

        def plant(name, code, mutate):
            recs = load_all(cfg)
            saved = {r.id: (r.path, r.path.read_text()) for r in recs.values()}
            idx = cfg.index.read_text()
            mutate(recs)
            broken = []
            problems, _, _ = validate(cfg, load_all(cfg, broken), today)
            problems = broken + problems
            planted.add(code)
            expect(f"planted: {name} → {code}", any(p["code"] == code for p in problems))
            for stray in list(cfg.research.rglob("*.md")):
                if cfg.id_re.match(stray.name):
                    stray.unlink()
            for path, text in saved.values():
                path.write_text(text)
            cfg.index.write_text(idx)

        def raw_edit(recs, id_, fn):
            r = recs[id_]
            fn(r.fm)
            r.path.write_text(render(r.fm, r.body))

        plant("bogus state", "V3", lambda R: raw_edit(R, q, lambda fm: fm.update(state="bogus")))
        plant("a record with no id", "V1", lambda R: raw_edit(R, q, lambda fm: fm.update(id=None)))
        plant("a record whose id names another prefix", "V1", lambda R: raw_edit(R, q, lambda fm: fm.update(id="task-9998")))
        plant("a record that does not read", "V0", lambda R: R[q].path.write_text("---\nid: 'unterminated\n---\n"))
        plant("a record that is not UTF-8", "V0", lambda R: R[q].path.write_bytes(b"---\nid: " + q.encode() + b"\nsummary: \xff\n---\n"))
        plant("a lean task with no question", "V4", lambda R: raw_edit(R, "task-0004", lambda fm: fm.update(question=None, derived_from=[])))
        plant("a ready task whose requires is missing", "V5", lambda R: raw_edit(R, rt, lambda fm: fm.update(requires=["finding-9999"])))
        plant("a decomposed question with no task", "V10", lambda R: raw_edit(R, "question-0003", lambda fm: fm.update(state="decomposed")))
        plant("a parking block that is not a map", "V15", lambda R: raw_edit(R, "question-0004", lambda fm: fm.update(parked="later")))
        plant("a parking block with no reason", "V15", lambda R: raw_edit(R, "question-0004", lambda fm: fm.update(parked={"date": today})))
        plant("a parking date that is not a date", "V20", lambda R: raw_edit(R, "question-0004", lambda fm: fm.update(parked={"date": "soon", "reason": "r"})))
        plant("an abandoned record with no reason", "V17", lambda R: raw_edit(R, t3, lambda fm: fm.update(abandoned={"date": today})))
        plant("an abandonment dated in the future", "V20", lambda R: raw_edit(R, t3, lambda fm: fm.update(abandoned={"date": "2999-01-01", "reason": "r"})))
        plant("a consumed idea no question derives from", "V17", lambda R: raw_edit(R, "idea-0002", lambda fm: fm.update(state="consumed", consumed_by="question-0005")))
        plant("a question answered by nothing", "V18", lambda R: raw_edit(R, q, lambda fm: fm.update(answered_by=[])))
        plant("a question answered by a task not drawn under it", "V18", lambda R: raw_edit(R, q, lambda fm: fm.update(answered_by=[t4])))
        plant("a created date that is not a date", "V20", lambda R: raw_edit(R, q, lambda fm: fm.update(created="yesterday")))
        plant("dangling question ref", "V2", lambda R: raw_edit(R, "task-0004", lambda fm: fm.update(question="question-9999")))
        plant("duplicate rank", "V14", lambda R: raw_edit(R, "question-0005", lambda fm: fm.update(rank=1, why_now="w", first_move="m")))
        plant("rank on a parked question", "V14", lambda R: raw_edit(R, "question-0004", lambda fm: fm.update(rank=2, why_now="w", first_move="m")))
        plant("stale index", "V11", lambda R: cfg.index.write_text(cfg.index.read_text() + "x\n"))
        idx = cfg.index.read_text()
        cfg.index.write_text(idx.replace("| --- | --- | --- |", "|---|---|---|"))
        msgs = [p["msg"] for p in validate(cfg, load_all(cfg), today)[0] if p["code"] == "V11"]
        cfg.index.write_text(idx + "x\n")
        msgs += [p["msg"] for p in validate(cfg, load_all(cfg), today)[0] if p["code"] == "V11"]
        cfg.index.write_text(idx)
        expect("an index differing from the render only in its form says so, and a stale one does not",
               len(msgs) == 2 and "another version's form" in msgs[0] and "is stale" in msgs[1])
        plant("open question without checked", "V12", lambda R: raw_edit(R, "question-0003", lambda fm: fm.update(checked=None)))
        plant("open task on an answered question", "V13", lambda R: (raw_edit(R, "task-0004", lambda fm: fm.update(state="ready", owner=None))
                                                                  , raw_edit(R, "question-0005", lambda fm: fm.update(state="answered", answered_by=[f]))))
        plant("kill criteria blanked", "V16", lambda R: raw_edit(R, "question-0003", lambda fm: fm.update(kill=None)))
        plant("derived_from cycle", "V8", lambda R: raw_edit(R, idea, lambda fm: fm.update(state="open", consumed_by=None)) or
              raw_edit(R, "idea-0001", lambda fm: fm.setdefault("tags", [])) or
              raw_edit(R, f, lambda fm: fm.update(derived_from=[f])))
        plant("parent cycle", "V8", lambda R: raw_edit(R, "question-0003", lambda fm: fm.update(parent="question-0003")))
        plant("closed task outside the archive", "V21", lambda R: shutil.move(str(R[t1].path), str(cfg.research / "tasks" / R[t1].path.name)))
        plant("finding without evidence", "V6", lambda R: raw_edit(R, f, lambda fm: fm.update(evidence=[])))
        plant("finding whose declaration left the manifest", "V6",
              lambda R: ((root / "decls.txt").write_text("module Lib.Foo 0\n"), setattr(cfg, "_manifest", None)))
        (root / "decls.txt").write_text("module Lib.Foo 1\nLib.Foo lemma_L\n")
        cfg._manifest = None
        plant("hand over limit", "V9", lambda R: (raw_edit(R, "task-0002", lambda fm: fm.update(state="active", owner="prover", drawn=today)),
                                                  raw_edit(R, "task-0004", lambda fm: fm.update(state="active", owner="prover", drawn=today))))
        plant("unknown direction", "V22", lambda R: raw_edit(R, "question-0003", lambda fm: fm.update(direction="Nowhere")))
        plant("body not one sentence per line", "V19", lambda R: R[q].path.write_text(render(R[q].fm, "One sentence. Two sentences on a line.\n")))
        plant("a citation of a key the library does not hold", "V23",
              lambda R: R[q].path.write_text(render(R[q].fm, "As lib:nobody2000 states.\n")))
        plant("a citation of an extract the library's card does not carry", "V23",
              lambda R: R[q].path.write_text(render(R[q].fm, "As lib:jen1990#lemma states, and lib:jen1990#theorem9 does not.\n")))
        stub.write_text("raise SystemExit(3)\n")
        plant("a library that does not answer", "V23", lambda R: None)
        cfg.library_cmd = []
        # the library found with no command bound: by library.toml at the root, then the sibling skill or PATH
        with tempfile.TemporaryDirectory() as t2:
            r2 = Path(t2)
            do_init(r2, build_parser().parse_args(["init", "--log", "LOG.md"]))
            c2 = Config(r2)
            expect("the directions file init writes names no direction; the form in its comment is not one", directions_of(c2) == set())
            mdl = shutil.which("markdownlint")
            if mdl:  # init's files and the flow's writes, under the built-in configuration (no project one here)
                (r2 / "body.md").write_text("A sentence well past eighty characters, " + "and on " * 12 + "until it ends.\n", encoding="utf-8")
                rc, _ = dispatch(c2, ["capture", "A long sentence", "--source", "t", "--body", str(r2 / "body.md")], today=today, as_json=True, quiet=True)
                expect("a body sentence longer than 80 characters is written under the built-in configuration", rc == 0)
                dispatch(c2, ["task", "An upkeep", "--kind", "upkeep"], today=today, as_json=True, quiet=True)
                (r2 / "body.md").write_text("A line.\n## A heading with no blank line above it\n", encoding="utf-8")
                rc, _ = dispatch(c2, ["capture", "A violation", "--source", "t", "--body", str(r2 / "body.md")], today=today, as_json=True, quiet=True)
                expect("a write adding a violation of the built-in configuration is refused and reverted",
                       rc == 1 and len(list((r2 / "records" / "ideas").glob("*.md"))) == 1)
                (r2 / "body.md").unlink()
                (r2 / "mdl.json").write_text(MDLINT_DEFAULT, encoding="utf-8")
                r = subprocess.run([mdl, "-c", str(r2 / "mdl.json")] + [str(f) for f in sorted(r2.rglob("*.md"))], capture_output=True, text=True)
                expect("the files init writes, and an index with records, pass the built-in configuration", r.returncode == 0)
                if r.returncode:
                    print("      ", (r.stdout + r.stderr).strip())
                (r2 / "mdl.json").unlink()
            elif os.environ.get("CI"):
                expect("markdownlint is on PATH in CI, where the built-in configuration is tested", False)
            else:
                print("  --  the built-in markdownlint configuration not tested: no markdownlint on PATH")
            expect("with no library.toml the flow asks no library and says why", c2.library_cmd == [] and "no library.toml" in c2.library_route)
            (r2 / "library.toml").write_text("", encoding="utf-8")
            c2 = Config(r2)
            sibling = Path(__file__).resolve().parent.parent.parent / "library" / "scripts" / "library.py"
            expect("with library.toml at the root the library skill beside this one comes first, else PATH",
                   c2.library_cmd == ([sys.executable, str(sibling)] if sibling.is_file() else [shutil.which("library")] if shutil.which("library") else []))
            (r2 / "flow.toml").write_text((r2 / "flow.toml").read_text(encoding="utf-8").replace('# command = ["library"]', 'command = []'), encoding="utf-8")
            c2 = Config(r2)
            expect("command = [] asks no library", c2.library_cmd == [] and c2.library_route == "disabled in flow.toml")
        reportable = set(re.findall(r'bad\("(V\d+)"', SOURCE)) | set(re.findall(r'"code": "(V\d+)"', SOURCE))
        expect(f"every code the check can report is planted ({', '.join(sorted(reportable - planted)) or 'none missing'})",
               reportable <= planted)
        _, _, cov = validate(cfg, load_all(cfg), today)
        expect("with no library bound the coverage says so", cov["library"] is None)
        # the cold-start bundle and the page manifest
        (root / "WORKLOG.md").write_text("# Log\n\n## 2026-09-25 — the top entry\n\n**State.** All is well.\n\n## 2026-09-24 — older\n\nx\n")
        cfg.log = root / "WORKLOG.md"
        (root / "research" / "directions.md").write_text("# Directions\n\n## Inbox\n\n- one item\n\n## Directions\n\n- **Bridge** (minted today) — the words.\n")
        lines, more = state_lines(cfg)
        expect("state prints the inbox, the ranked list and the top log entry with FILE:LINE",
               any(l.startswith("research/directions.md:") and "one item" in l for l in lines)
               and any("## Next (ranked)" in l for l in lines)
               and any(l.startswith("WORKLOG.md:") and "the top entry" in l for l in lines)
               and not any("older" in l for l in lines) and more is None)
        lines, more = state_lines(cfg, 0, 200)
        expect("state stops at the budget and names the continuation", more is not None and len(lines) < 10)
        lines, more = state_lines(cfg, 0, 5)
        expect("a line longer than the budget is printed alone, and the continuation moves past it", len(lines) == 1 and more == 1)
        pm = pages_manifest(cfg)
        expect("the page manifest names a mount, routes and an id pattern",
               pm["mount"] == "/flow" and any(r["view"] == "record" for r in pm["routes"])
               and re.search(pm["links"][0]["pattern"], "see question-0003 here"))

    # front matter: what PyYAML wrote reads back, and what is written reads back unchanged
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "flow.toml").write_text(SELFTEST_TOML)
        (root / "research" / "questions").mkdir(parents=True)
        pyyaml_text = (
            "---\nid: question-0001\ntype: question\nkind: question\nstate: open\n"
            "summary: 'Design round: the split, with a ''quoted'' word'\nderived_from:\n- idea-0001\nparent: null\nsize: medium\n"
            "kill: the author's words, and lib:jen1990 cited\nchecked: '2026-10-22'\nparked:\n  date: '2026-10-01'\n  reason: waiting\n"
            "  revival: null\nrank: 2\nwhy_now: x\nfirst_move: a \"double\" one\ndirection: null\nanswered_by: []\nabandoned: null\n"
            "origin: current\nsource: null\ncreated: '2026-10-05'\ntags: []\n---\n\nA body.\n")
        path = root / "research" / "questions" / "question-0001-x.md"
        path.write_text(pyyaml_text)
        r = parse(path)
        expect("PyYAML's single quotes, doubled quotes, plain scalars, ints and maps read back",
               r["summary"] == "Design round: the split, with a 'quoted' word" and r["kill"] == "the author's words, and lib:jen1990 cited"
               and r["checked"] == "2026-10-22" and r["rank"] == 2 and r["parked"] == {"date": "2026-10-01", "reason": "waiting", "revival": None}
               and r["first_move"] == 'a "double" one' and r["answered_by"] == [] and r["parent"] is None)
        expect("the record renders back byte for byte", render(r.fm, r.body) == pyyaml_text)
        path.write_text("\ufeff" + pyyaml_text.split("\n---\n\n")[0] + "\n---")
        expect("a byte-order mark and a closing fence with no newline after it read", parse(path)["rank"] == 2 and parse(path).body == "")
        d = load_front('a: "tab\\there \\"q\\""\nb: \'two\n\n  lines\'\nc: \'one\n  folded\'\nd: x', "t")
        expect("PyYAML's double-quoted escapes and multi-line single-quoted scalars read back",
               d == {"a": 'tab\there "q"', "b": "two\nlines", "c": "one folded", "d": "x"})
        d = load_front('a: plain words\n  folded\nb: "tab\\there\\\n  \\ next"\nc:\n- an item\n  folded\n- \'two\n\n  lines\'\n'
                       'd:\n  reason: a reason\n    folded\ne: x', "t")
        expect("PyYAML's values folded at 80 columns read back: plain, double-quoted, list items and map values",
               d == {"a": "plain words folded", "b": "tab\there next", "c": ["an item folded", "two\nlines"],
                     "d": {"reason": "a reason folded"}, "e": "x"})
        fm = {"a": "plain words, with a comma", "b": "with: a colon", "c": "2026-01-01", "d": "yes", "e": 7, "f": "", "g": "- leading",
              "h": "ends with colon:", "i": "has # hash", "j": "a\nnewline", "k": "it's", "l": "lib:key#ex", "m": True, "n": None, "o": "1.5"}
        back = load_front(dump_front(fm), "t")
        expect("every scalar shape round-trips", back == fm)
        expect("plain where PyYAML is plain, quoted where it quotes",
               dump_front({"a": fm["a"], "k": fm["k"], "l": fm["l"]}) == "a: plain words, with a comma\nk: it's\nl: lib:key#ex"
               and dump_front({"b": fm["b"], "c": fm["c"], "d": fm["d"], "o": fm["o"]}) == "b: 'with: a colon'\nc: '2026-01-01'\nd: 'yes'\no: '1.5'")

    # init: a fresh project, checked green at once
    for _ in (0,):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = argparse.Namespace(records="records", log=None, owner=None, force=False)
            written = do_init(root, a)
            cfg = Config(root)
            problems, _, cov = validate(cfg, load_all(cfg), "2026-10-23")
            expect("init: a tree that checks green",
                   not problems and cfg.kinds == TYPES and "flow.toml" in written
                   and (cfg.research / "archive").is_dir() and (cfg.research / "findings").is_dir())
            rc, payload = dispatch(cfg, ["capture", "the first idea"], today="2026-10-23", as_json=True, quiet=True)
            expect("init: the first capture lands", rc == 0 and payload["created"] == ["idea-0001"])
            try:
                do_init(root, a)
                expect("init refuses over an existing flow.toml", False)
            except Refused:
                expect("init refuses over an existing flow.toml", True)

    # the bindings a hand writes: the defaults the kit knows no prover by, and the refusals
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "flow.toml").write_text("[hand]\nroot = 2\n")
        cfg = Config(root)
        expect("a bare flow.toml: records/ and no decision owner", cfg.records_name == "records" and cfg.decision_owners == ()
               and cfg.decl_ext is None and cfg.ev_decl.match("src/Foo.agda#bar") and not cfg.ev_decl.match("papers/a.md#x"))
        (root / "records").mkdir()
        rc, pl = dispatch(cfg, ["task", "a decision with no decision owner", "--kind", "decision"], today="2026-10-23", as_json=True, quiet=True)
        problems, _, _ = validate(cfg, load_all(cfg), "2026-10-23")
        expect("a decision task minted with no decision owner checks green", rc == 0 and not problems)
        expect("declaration evidence with no manifest is unchecked, not failed",
               resolve_evidence(cfg, "src/Foo.agda#bar", {}).startswith("unchecked"))
        (root / "flow.toml").write_text("[hand]\nroot = 2\n[task]\ndecision_owners = [\"nobody\"]\n")
        try:
            Config(root)
            expect("a decision owner not under [hand] is refused", False)
        except Refused:
            expect("a decision owner not under [hand] is refused", True)
        (root / "flow.toml").write_text("[evidence]\nmanifest = \"decls.txt\"\n")
        try:
            Config(root)
            expect("a manifest with no manifest_extension is refused", False)
        except Refused as e:
            expect("a manifest with no manifest_extension is refused", "manifest_extension" in str(e))
        a = argparse.Namespace(records="records", log="LOG.md", owner=["me"], force=True)
        written = do_init(root, a)
        cfg = Config(root)
        expect("init --log writes the log with a State paragraph, --owner the owner, and a research kind list with no prover word",
               "LOG.md" in written and "**State.**" in (root / "LOG.md").read_text() and cfg.owners == ("me",)
               and cfg.decision_owners == ("me",) and "lean" not in cfg.task_kinds and "work" in cfg.task_kinds)
        lines, _ = state_lines(cfg)
        expect("flow state prints the new log's top entry", any("the flow set up" in ln for ln in lines))
        r = subprocess.run([sys.executable, __file__, "--help"], capture_output=True, text=True, cwd=tempfile.gettempdir())
        expect("--help works with no bindings file", r.returncode == 0 and "capture" in r.stdout and "init" in r.stdout)

    # the log written at its top and archived by month, a session's close checked, the other prose reflowed
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        do_init(root, build_parser().parse_args(["init", "--log", "LOG.md"]))
        cfg = Config(root)
        today = "2026-10-27"
        mdl = shutil.which("markdownlint")
        (root / "LOG.md").write_text("# Log\n\n## 2026-10-20 — set up\n\n**State.** Nothing is in flight.\n\n## 2026-09-30 — late\n\n"
                                     "**State.** Late.\n\n```text\n## 2026-01-01 — in a fence, no entry\n```\n\n## 2026-09-02 — early\n\n"
                                     "**State.** Early.\n\n## 2026-08-15 — august\n\n**State.** August.\n", encoding="utf-8")

        def go(argv, ok=True, day=today):
            rc, payload = dispatch(cfg, argv, today=day, as_json=True, quiet=True)
            expect(" ".join(argv[:2]) + (" refused" if not ok else ""), (rc == 0) == ok)
            if (rc == 0) != ok:
                for pr in payload["problems"]:
                    print("      ", pr["code"], pr.get("path") or pr.get("id"), pr["msg"])
            return payload

        entry = root / "entry.md"
        for text in ("**State.** No heading.\n", "## 2026-10-27 — no State paragraph\n\nA paragraph.\n",
                     "## 2026-10-19 — older than the top entry\n\n**State.** Old.\n", "## 2026-10-28 — tomorrow\n\n**State.** Not yet.\n",
                     "## 2026-10-27 — two\n\n**State.** One.\n\n## 2026-10-27 — entries\n\n**State.** Two.\n"):
            entry.write_text(text, encoding="utf-8")
            go(["log", "add", str(entry)], ok=False)
        before = (root / "LOG.md").read_text(encoding="utf-8")
        if mdl:
            entry.write_text("## 2026-10-27 — glued\n**State.** A heading with no blank line below it.\n", encoding="utf-8")
            go(["log", "add", str(entry)], ok=False)
            expect("a log entry adding a markdownlint violation is refused and the log left as it was", (root / "LOG.md").read_text(encoding="utf-8") == before)
        entry.write_text("## 2026-10-27 — the round closed\n\n**State.** The round closed. Nothing is in flight.\n", encoding="utf-8")
        go(["log", "add", str(entry)])
        log = (root / "LOG.md").read_text(encoding="utf-8")
        expect("log add writes the entry at the top under the title, reflowed, a bold label kept with its sentence",
               log.startswith("# Log\n\n## 2026-10-27 — the round closed\n\n**State.** The round closed.\nNothing is in flight.\n\n## 2026-10-20 — set up\n")
               and log.endswith(before.split("\n\n", 1)[1]))
        go(["log", "archive", "--before", "2026-10-28"], ok=False)  # the top entry stays
        go(["log", "archive", "--before", "2026-08-01"], ok=False)  # nothing older
        go(["log", "archive", "--before", "soon"], ok=False)
        go(["log", "archive", "--before", "2026-09-15"])
        go(["log", "archive", "--before", "2026-10-01"])
        arch, log = root / "LOG-archive", (root / "LOG.md").read_text(encoding="utf-8")
        expect("log archive moves the older entries verbatim, newest first, one file per month, a second run merged into its month",
               sorted(p.name for p in arch.iterdir()) == ["2026-08.md", "2026-09.md"]
               and (arch / "2026-09.md").read_text(encoding="utf-8") == "# Log — 2026-09\n\n## 2026-09-30 — late\n\n**State.** Late.\n\n"
               "```text\n## 2026-01-01 — in a fence, no entry\n```\n\n## 2026-09-02 — early\n\n**State.** Early.\n")
        expect("and leaves one pointer under the log's title, dated by the latest run",
               log.startswith("# Log\n\nEntries dated before 2026-10-01 are archived verbatim, newest first, one file per month in "
                              "[LOG-archive/](LOG-archive/).\n\n## 2026-10-27 — the round closed\n")
               and log.count("Entries dated before") == 1 and "## 2026-09" not in log)
        (root / "LOG.md").write_text(log + "\n## Notes\n\nAn undated heading.\n", encoding="utf-8")
        go(["log", "archive", "--before", "2026-10-25"], ok=False)  # an entry with no date
        (root / "LOG.md").write_text(log, encoding="utf-8")
        cfg.log = None
        go(["log", "add", str(entry)], ok=False)  # no log bound
        # a log with front matter, a four-backtick fence holding a shorter one, and link definitions closing it
        cfg.log, cfg.log_archive = root / "L2.md", root / "L2-archive"
        cfg.log.write_text("---\n# a YAML comment, no title\nkind: log\n---\n\n## 2026-10-20 — kept\n\n**State.** Kept.\n\n"
                           "## 2026-09-10 — moved\n\n**State.** Moved.\n\n````text\n```\n## 2026-01-01 — inside the fence\n````\n\n"
                           "[ref]: https://example.org\n", encoding="utf-8")
        go(["log", "archive", "--before", "2026-10-01"])
        expect("planted: log archive reads a log's front matter as none of its title, puts the pointer under it, keeps a fence "
               "open until a run as long closes it, and leaves the link definitions closing the log in it",
               cfg.log.read_text(encoding="utf-8") == "---\n# a YAML comment, no title\nkind: log\n---\n\nEntries dated before 2026-10-01 "
               "are archived verbatim, newest first, one file per month in [L2-archive/](L2-archive/).\n\n## 2026-10-20 — kept\n\n"
               "**State.** Kept.\n\n[ref]: https://example.org\n"
               and (cfg.log_archive / "2026-09.md").read_text(encoding="utf-8") == "# Log — 2026-09\n\n## 2026-09-10 — moved\n\n"
               "**State.** Moved.\n\n````text\n```\n## 2026-01-01 — inside the fence\n````\n")
        # the link definitions closing the log given to the files that use them, into a month's file closed by its own
        cfg.log, cfg.log_archive = root / "L4.md", root / "L4-archive"
        cfg.log.write_text("# Log\n\n## 2026-10-20 — kept\n\n**State.** Kept, as [both] say.\n\n## 2026-09-10 — moved\n\n"
                           "**State.** Moved, as [Both] and [the spec] say.\n\n[both]: https://example.org/both\n"
                           "[the spec]: https://example.org/spec\n[unused]: https://example.org/unused\n", encoding="utf-8")
        cfg.log_archive.mkdir()
        (cfg.log_archive / "2026-09.md").write_text("# Log — 2026-09\n\n## 2026-09-05 — earlier\n\n**State.** See [old].\n\n"
                                                    "[old]: https://example.org/old\n", encoding="utf-8")
        go(["log", "archive", "--before", "2026-10-01"])
        expect("planted: log archive keeps the link definitions closing a month's file it merges into, moves to it a definition "
               "only an archived entry uses, copies one the log uses too, and leaves an unused one in the log",
               cfg.log.read_text(encoding="utf-8") == "# Log\n\nEntries dated before 2026-10-01 are archived verbatim, newest first, "
               "one file per month in [L4-archive/](L4-archive/).\n\n## 2026-10-20 — kept\n\n**State.** Kept, as [both] say.\n\n"
               "[both]: https://example.org/both\n[unused]: https://example.org/unused\n"
               and (cfg.log_archive / "2026-09.md").read_text(encoding="utf-8") == "# Log — 2026-09\n\n## 2026-09-10 — moved\n\n"
               "**State.** Moved, as [Both] and [the spec] say.\n\n## 2026-09-05 — earlier\n\n**State.** See [old].\n\n"
               "[old]: https://example.org/old\n[both]: https://example.org/both\n[the spec]: https://example.org/spec\n")
        if mdl:  # a violation the archive file alone would have: both files stay as they were
            cfg.log, cfg.log_archive = root / "L3.md", root / "L3-archive"
            cfg.log.write_text("# Log\n\n## 2026-10-20 — kept\n\n**State.** Kept.\n\n## 2026-09-12 — twice\n\n**State.** Moved.\n", encoding="utf-8")
            cfg.log_archive.mkdir()
            (cfg.log_archive / "2026-09.md").write_text("# Log — 2026-09\n\n## 2026-09-12 — twice\n\n**State.** An earlier copy.\n", encoding="utf-8")
            files = lambda: (cfg.log.read_text(encoding="utf-8"), (cfg.log_archive / "2026-09.md").read_text(encoding="utf-8"))
            had = files()
            go(["log", "archive", "--before", "2026-10-01"], ok=False)
            expect("planted: a log archive whose archive file alone trips markdownlint (MD024) leaves the log and the file as they were",
                   files() == had)
        cfg.log, cfg.log_archive = root / "LOG.md", root / "LOG-archive"

        # the close: decided where git and the log can say, and said where they cannot
        with tempfile.TemporaryDirectory() as t2:
            do_init(Path(t2), build_parser().parse_args(["init", "--log", "LOG.md"]))
            c2 = Config(Path(t2))
            if git(c2, "rev-parse", "--is-inside-work-tree") is None:
                rc, pl = dispatch(c2, ["state", "--check", "--owner", "agent"], today=today, as_json=True, quiet=True)
                expect("state --check outside a work tree says the log's part is not decided and exits 2, passing the rest",
                       rc == 2 and any("git is absent" in u for u in pl["undecided"]) and pl["checked"] == ["the inbox", "the hand"]
                       and not pl["problems"])
        if shutil.which("git"):
            gitc = ["git", "-c", "user.name=flow", "-c", "user.email=flow@selftest", "-c", "commit.gpgsign=false"]
            for argv in (["init", "-q"], ["add", "-A"], ["commit", "-q", "--no-verify", "-m", "the log"]):
                subprocess.run(gitc + argv, cwd=root, capture_output=True, text=True)
            p = go(["state", "--check", "--owner", "agent"])
            expect("state --check passes a clean close and says what it checked", not p["problems"] and len(p["checked"]) == 4 and not p["undecided"])
            expect("state --check with no owner, or one flow.toml does not list, could not run: exit 2",
                   [dispatch(cfg, argv, today=today, as_json=True, quiet=True)[0] for argv in
                    (["state", "--check"], ["state", "--check", "--owner", "nobody"])] == [2, 2])
            go(["state", "--owner", "agent"], ok=False)  # --owner is the close's
            idea = go(["capture", "an idea"])["records"][0]["path"]
            p = go(["state", "--check", "--owner", "agent"], ok=False)
            expect("planted: a record changed since the top entry's commit that no entry names fails the close",
                   [x["path"] for x in p["problems"]] == [idea])
            p = go(["state", "--check", "--owner", "agent"], ok=False, day="2026-10-30")
            expect("planted: a top entry not dated today, the tree changed since its commit, fails the close",
                   any("not today (2026-10-30)" in x["msg"] for x in p["problems"]))
            entry.write_text("## 2026-10-27 — an idea\n\n**State.** The idea idea-0001 is captured.\n", encoding="utf-8")
            go(["log", "add", str(entry)])
            p = go(["state", "--check", "--owner", "agent"])
            expect("an entry above the committed one naming the changed record passes the close", not p["problems"])
            keep = cfg.directions.read_text(encoding="utf-8")
            cfg.directions.write_text(keep.replace("## Inbox\n", "## Inbox\n\n<!-- a comment is no item -->\n- look at the bound\n"), encoding="utf-8")
            p = go(["state", "--check", "--owner", "agent"], ok=False)
            expect("planted: an inbox not emptied fails the close, a comment in it no item",
                   [x["path"] for x in p["problems"]] == [f"{rel(cfg, cfg.directions)}:6"])
            cfg.directions.write_text(keep, encoding="utf-8")
            t = go(["task", "an upkeep chore", "--kind", "upkeep"])["created"][0]
            go(["draw", t, "--owner", "owner"])
            p = go(["state", "--check", "--owner", "agent"], ok=False)  # the task is named by no entry
            expect("an active task under a decision owner is not the close's", not any("is active under" in x["msg"] for x in p["problems"]))
            cfg.decision_owners = ()
            p = go(["state", "--check", "--owner", "agent"], ok=False)
            cfg.decision_owners = ("owner",)
            expect("planted: an active task under another owner than the working session's, no decision owner, fails the close",
                   any(f"{t} is active under owner" in x["msg"] for x in p["problems"]))
        elif os.environ.get("CI"):
            expect("git is on PATH in CI, where the close's log part is tested", False)
        else:
            print("  --  the close's log part not tested: no git on PATH")

        # the reflow offered for the project's other prose
        (root / "prose.md").write_text("---\ntitle: A. B on one line\n---\n\n# Prose\n\nOne. Two on a line.\n\n**Theorem 1.** It holds.\n\n"
                                       "A line ending in a hard break.  \nIts next line.\n\n**Do not merge this branch yet.** The tests fail.\n\n"
                                       "**Proposition 5.3 (see Smith 2001).** It holds.\n\n````text\n```\nOne. Two in code.\n````\n", encoding="utf-8")
        p = go(["reflow", "--check", str(root / "prose.md")], ok=False)
        expect("planted: reflow --check names each line not one sentence per line, a bold sentence among them; "
               "its front matter, a short bold label, one with a parenthetical, a hard break and a fence a shorter run does not close aside",
               [(x["path"], x["msg"]) for x in p["problems"]] == [("prose.md:7", "One. Two on a line."),
                                                                  ("prose.md:14", "**Do not merge this branch yet.** The tests fail.")])
        expect("planted: a line the reflow splits keeps its hard break on its last part",
               cfg.reflow("One. Two.  \nThree.\n- A. B.  \n  C.") == "One.\nTwo.  \nThree.\n- A.\n  B.  \n  C.")
        (root / "docs").mkdir()
        (root / "docs" / "a.md").write_text("# A\n\nIt is fine.\n", encoding="utf-8")
        go(["reflow", "--check", str(root / "docs"), str(root / "LOG.md")])
        expect("reflow --check on a file that is not there could not run: exit 2",
               dispatch(cfg, ["reflow", "--check", str(root / "absent.md")], today=today, as_json=True, quiet=True)[0] == 2)
        draft = root / "draft.md"
        draft.write_text("A draft. Two sentences on a line.\n", encoding="utf-8")
        p = go(["reflow", "--as", str(root / "docs" / "a.md"), str(draft)], ok=False)
        expect("planted: reflow --as names a draft's line not one sentence per line", [x["code"] for x in p["problems"]] == ["REFLOW"])
        if mdl:
            draft.write_text("A line.\n## A heading glued to it\n", encoding="utf-8")
            p = go(["reflow", "--as", str(root / "docs" / "a.md"), str(draft)], ok=False)
            expect("planted: reflow --as names the markdownlint violation the draft adds at DEST, at the draft's own line",
                   [(x["code"], x["path"]) for x in p["problems"]] == [("MARKDOWNLINT", f"{draft}:2")])
            (root / "docs" / "b.md").write_text("# B\n## Glued in DEST already\n\nIt is not fine.\n", encoding="utf-8")
            p = go(["reflow", "--as", str(root / "docs" / "b.md"), str(draft)], ok=False)
            expect("planted: reflow --as names only the violations the draft adds, never DEST's own of the same rule",
                   [(x["code"], x["path"]) for x in p["problems"]] == [("MARKDOWNLINT", f"{draft}:2")])
            (root / "docs" / "b.md").unlink()
        draft.write_text("A clean draft.\n", encoding="utf-8")
        go(["reflow", "--as", str(root / "docs" / "a.md"), str(draft)])
        expect("reflow --as writes nothing", (root / "docs" / "a.md").read_text(encoding="utf-8") == "# A\n\nIt is fine.\n"
               and sorted(p.name for p in (root / "docs").iterdir()) == ["a.md"])
    print(f"flow selftest: {'OK' if not failures else str(len(failures)) + ' FAILED: ' + '; '.join(failures)}")
    return 0 if not failures else 1


# --- dispatch ----------------------------------------------------------------

def build_parser():
    ap = argparse.ArgumentParser(prog="flow", description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root")
    ap.add_argument("--today")
    ap.add_argument("--selftest", action="store_true")
    sp = ap.add_subparsers(dest="cmd")

    p = sp.add_parser("capture"); p.add_argument("summary"); p.add_argument("--source"); p.add_argument("--tag", action="append", help="repeatable"); p.add_argument("--body")
    p = sp.add_parser("task"); p.add_argument("summary"); p.add_argument("--kind", required=True); p.add_argument("--question")
    p.add_argument("--size"); p.add_argument("--dod"); p.add_argument("--source"); p.add_argument("--tag", action="append", help="repeatable"); p.add_argument("--body")
    p = sp.add_parser("frame"); p.add_argument("ids", nargs="+"); p.add_argument("--summary", required=True); p.add_argument("--kill", required=True)
    p.add_argument("--size"); p.add_argument("--kind", default="question", choices=("question", "conjecture")); p.add_argument("--parent")
    p.add_argument("--direction"); p.add_argument("--tag", action="append", help="repeatable"); p.add_argument("--body"); p.add_argument("--source")
    p = sp.add_parser("refine"); p.add_argument("question"); p.add_argument("--task", action="append", help="a summary, then optionally a kind; repeatable", nargs="+", metavar=("SUMMARY", "KIND"))
    p.add_argument("--subq", action="append", nargs=2, metavar=("SUMMARY", "KILL"), help="repeatable"); p.add_argument("--idea", action="append", help="repeatable")
    p.add_argument("--kind"); p.add_argument("--size"); p.add_argument("--dod"); p.add_argument("--requires", action="append", help="repeatable")
    p.add_argument("--body", help="appended to the question's body under the date, never to a task's: a task's own body is "
                                  "`flow task SUMMARY --question Q --body FILE`")
    p = sp.add_parser("draw"); p.add_argument("task"); p.add_argument("--owner", required=True)
    p = sp.add_parser("return"); p.add_argument("task"); p.add_argument("--note")
    p = sp.add_parser("make"); p.add_argument("task"); p.add_argument("--finding", action="append", help="a summary, a status, then one or more evidence items; repeatable", nargs="+", metavar=("SUMMARY", "STATUS EVIDENCE"))
    p.add_argument("--paper"); p.add_argument("--depends-on", action="append", help="repeatable", dest="depends_on")
    p.add_argument("--task", action="append", help="a summary, then optionally a kind; repeatable", nargs="+", dest="task_out", metavar=("SUMMARY", "KIND"))
    p.add_argument("--question", action="append", nargs=2, metavar=("SUMMARY", "KILL"), help="repeatable"); p.add_argument("--idea", action="append", help="repeatable"); p.add_argument("--resolution")
    p = sp.add_parser("abort"); p.add_argument("task"); p.add_argument("--reason", required=True); p.add_argument("--resolution")
    p.add_argument("--finding", action="append", help="a summary, a status, then one or more evidence items; repeatable", nargs="+", metavar=("SUMMARY", "STATUS EVIDENCE")); p.add_argument("--paper")
    p = sp.add_parser("answer"); p.add_argument("question"); p.add_argument("--by", action="append", help="repeatable", required=True)
    p = sp.add_parser("kill"); p.add_argument("id"); p.add_argument("--reason", required=True)
    p = sp.add_parser("park"); p.add_argument("question"); p.add_argument("--reason", required=True); p.add_argument("--revival")
    p = sp.add_parser("unpark"); p.add_argument("question"); p.add_argument("--note")
    p = sp.add_parser("rank"); p.add_argument("id", nargs="?"); p.add_argument("n", nargs="?", type=int); p.add_argument("--set", nargs="+")
    p.add_argument("--clear", action="store_true"); p.add_argument("--insert", action="store_true"); p.add_argument("--why"); p.add_argument("--first-move", dest="first_move"); p.add_argument("--direction")
    p = sp.add_parser("checked"); p.add_argument("ids", nargs="+")
    p = sp.add_parser("set"); p.add_argument("id"); p.add_argument("field"); p.add_argument("value")
    p = sp.add_parser("find")
    for f in ("type", "state", "kind", "status", "tag", "owner", "question", "paper", "requires", "grep"):
        p.add_argument("--" + f)
    p.add_argument("--depends-on", dest="depends_on"); p.add_argument("--parked", action="store_true"); p.add_argument("--ranked", action="store_true")
    p = sp.add_parser("show"); p.add_argument("id")
    p = sp.add_parser("graph"); p.add_argument("--from", dest="frm"); p.add_argument("--dot", action="store_true")
    p = sp.add_parser("index"); p.add_argument("--check", action="store_true"); p.add_argument("--print", action="store_true", dest="print_")
    sp.add_parser("check")
    p = sp.add_parser("state"); p.add_argument("--from", dest="frm", type=int, default=0); p.add_argument("--budget", type=int, default=14000)
    p.add_argument("--check", action="store_true", help="what a machine can see of a session's close; exit 1 on a failure")
    p.add_argument("--owner", help="the working session's owner, which --check holds the active tasks to")
    p = sp.add_parser("log"); lp = p.add_subparsers(dest="log_cmd", required=True, metavar="{add,archive}")
    lp.add_parser("add", help="FILE: one entry, written at the top of the log").add_argument("file")
    lp.add_parser("archive", help="--before DATE: the older entries moved, one file per month").add_argument("--before", required=True)
    p = sp.add_parser("reflow"); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", nargs="+", metavar="PATH", help="exit 1 on a line the reflow changes, each printed")
    g.add_argument("--as", nargs=2, metavar=("DEST", "DRAFT"), dest="as_", help="the draft checked as if appended to DEST: the reflow and markdownlint")
    sp.add_parser("directions")
    sp.add_parser("pages")
    p = sp.add_parser("init"); p.add_argument("--records", default="records")
    p.add_argument("--log"); p.add_argument("--owner", action="append", help="repeatable"); p.add_argument("--force", action="store_true")
    return ap


TRANSITIONS = {"capture": cmd_capture, "task": cmd_task, "frame": cmd_frame, "refine": cmd_refine, "draw": cmd_draw,
               "return": cmd_return, "make": cmd_make, "abort": cmd_abort, "answer": cmd_answer,
               "kill": cmd_kill, "park": cmd_park, "unpark": cmd_unpark, "rank": cmd_rank, "checked": cmd_checked, "set": cmd_set}


def summary_of(cfg, r):
    d = dict(r.fm)
    d["path"] = rel(cfg, r.path)
    return d


@contextlib.contextmanager
def project_lock(cfg, directory, tool):
    """One writer at a time: two writes at once would mint one id or key twice, or lose one of two edits
    to a file.  An OS lock, released by the OS when the process ends, so a crash leaves none behind: on
    the directory itself, or on Windows on a file outside the project named by it.  A writer that finds
    it held says so once and waits."""
    if not directory.is_dir():
        yield
        return
    waiting = f"{tool}: another {tool} command is writing {rel(cfg, directory)}; waiting for it to finish"
    if os.name != "nt":
        import fcntl
        try:
            fd = os.open(directory, os.O_RDONLY)
        except OSError as e:
            raise Refused(f"cannot lock {rel(cfg, directory)} for this write: {e}")
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print(waiting, file=sys.stderr)
                fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)
        return
    import msvcrt
    name = f"{tool}-" + hashlib.sha256(str(directory.resolve()).lower().encode()).hexdigest()[:16] + ".lock"
    try:
        f = open(Path(tempfile.gettempdir()) / name, "a+")
    except OSError as e:
        raise Refused(f"cannot lock {rel(cfg, directory)} for this write: {e}")
    with f:
        said = False
        while True:
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if not said:
                    print(waiting, file=sys.stderr)
                    said = True
                time.sleep(0.05)
        try:
            yield
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


def dispatch(cfg, argv, today=None, as_json=False, quiet=False):
    a = build_parser().parse_args(argv)
    writes = a.cmd in TRANSITIONS or a.cmd == "log" or (a.cmd == "index" and not a.print_ and not a.check)
    with project_lock(cfg, cfg.research, "flow") if writes else contextlib.nullcontext():
        return _dispatch(cfg, a, today, as_json, quiet)


def _dispatch(cfg, a, today, as_json, quiet):
    today = today or a.today or dt.date.today().isoformat()
    as_json = as_json or a.json
    out = {"ok": True, "command": a.cmd, "created": [], "changed": [], "records": [], "problems": []}
    not_run = False  # exit 2: the check could not run, or could not decide a part

    def emit(text=""):
        if not quiet and not as_json and text:
            print(text)

    try:
        broken = []
        recs = load_all(cfg, broken) if a.cmd == "check" else {} if a.cmd in ("log", "reflow") else load_all(cfg)
        if a.cmd in TRANSITIONS:
            if a.cmd == "rank" and not a.set and not a.id:
                raise Refused("rank takes ID N, --set ID..., or ID --clear")
            _JOURNAL.clear()
            try:
                created, changed = TRANSITIONS[a.cmd](cfg, recs, a, today)
            except BaseException:
                rollback()  # a transition happens whole or not at all
                raise
            _JOURNAL.clear()
            out["created"] = [r.id for r in created]
            out["changed"] = [r.id for r in changed]
            out["records"] = [summary_of(cfg, r) for r in created + changed]
            for r in created:
                emit(f"created {r.id} — {r['summary']}  ({rel(cfg, r.path)})")
            for r in changed:
                emit(f"changed {r.id} — {stat(r) or ''} ({rel(cfg, r.path)})")
            if a.cmd == "refine" and a.body:  # the body is the question's, not a minted task's: said, so it is not looked for there
                out["body_appended_to"] = a.question
                emit(f"the body of {a.body} appended to {a.question} under {today}")
            recs = load_all(cfg)
            cfg.index.parent.mkdir(parents=True, exist_ok=True)
            write_whole(cfg.index, render_index(cfg, recs))
            emit(f"index refreshed: {rel(cfg, cfg.index)}")
        elif a.cmd == "find":
            hits = cmd_find(cfg, recs, a, today)
            out["records"] = [summary_of(cfg, r) for r in hits]
            for r in hits:
                emit(f"{r.id} | {stat(r)} | {r['summary']}")
            emit(f"{len(hits)} record(s)")
        elif a.cmd == "show":
            r = get(recs, a.id)
            out["records"] = [summary_of(cfg, r)]
            out["body"] = r.body
            out["links"] = {f: refs(recs, ids) for f, ids in links(r).items()}
            out["backlinks"] = {f: refs(recs, ids) for f, ids in backlinks(recs, r.id).items()}
            emit(show_text(cfg, recs, r))
        elif a.cmd == "state" and a.check:
            if a.owner not in cfg.owners:
                raise NotRun(f"state --check takes --owner, the working session's, one of {', '.join(cfg.owners)}" + (f", not {a.owner!r}" if a.owner else ""))
            problems, checked, undecided = close_check(cfg, recs, a.owner, today)
            out["problems"], out["checked"], out["undecided"] = problems, checked, undecided
            for p in problems:
                emit(f"{p['path']}: {p['msg']}")
            for u in undecided:
                emit(f"undecided: {u}")
            emit(f"flow state --check: {len(problems)} failure(s); checked {', '.join(checked)}"
                 + (f"; {len(undecided)} not decided" if undecided else "")
                 + "; the conversation's inventory and the sweep by meaning are the session's own")
            if problems or undecided:  # a failure exits 1; else a part not decided exits 2, never read as clean
                out["ok"], not_run = False, not problems
        elif a.cmd == "state":
            if a.owner:
                raise Refused("--owner names the working session for state --check")
            lines, more = state_lines(cfg, a.frm, a.budget)
            out["lines"], out["next_from"] = lines, more
            for ln in lines:
                emit(ln)
            if more is not None:
                emit(f"…output budget reached; continue with --from {more}")
        elif a.cmd == "log":
            _JOURNAL.clear()
            try:
                written, said = (cmd_log_add if a.log_cmd == "add" else cmd_log_archive)(cfg, a, today)
            except BaseException:
                rollback()  # the log and its archive files are written whole or not at all
                raise
            _JOURNAL.clear()
            out["written"] = [rel(cfg, p) for p in written]
            emit(said)
        elif a.cmd == "reflow":
            problems, said = cmd_reflow(cfg, a)
            out["problems"], out["coverage"] = problems, said
            for p in problems:
                emit(f"{p['path']}: {p['msg']}")
            emit(f"flow reflow: {sum(p['code'] == 'REFLOW' for p in problems)} line(s) not one sentence per line"
                 + (f", {sum(p['code'] == 'MARKDOWNLINT' for p in problems)} new markdownlint violation(s)" if a.as_ else "") + f"; {said}")
            if problems:
                out["ok"] = False
        elif a.cmd == "directions":
            if not cfg.directions.is_file():
                raise Refused(f"no directions file at {rel(cfg, cfg.directions)}")
            out["text"] = cfg.directions.read_text(encoding="utf-8")
            emit(out["text"].rstrip("\n"))
        elif a.cmd == "pages":
            out["pages"] = pages_manifest(cfg)
            if not as_json:
                print(json.dumps(out["pages"], ensure_ascii=False, indent=1))
        elif a.cmd == "graph":
            text = cmd_graph(cfg, recs, a, today)
            out["graph"] = text
            emit(text)
        elif a.cmd == "index":
            text = render_index(cfg, recs)
            out["text"] = text
            if a.print_:
                emit(text.rstrip("\n"))
            elif a.check:
                stale = not cfg.index.is_file() or cfg.index.read_text(encoding="utf-8") != text
                out["stale"] = stale
                emit(f"index {'STALE' if stale else 'fresh'}: {rel(cfg, cfg.index)}")
                if stale:
                    out["ok"] = False
            else:
                cfg.index.parent.mkdir(parents=True, exist_ok=True)
                write_whole(cfg.index, text)
                emit(f"wrote {rel(cfg, cfg.index)}")
        elif a.cmd == "check":
            problems, warnings, cov = validate(cfg, recs, today)
            problems = broken + problems
            out["problems"], out["warnings"], out["coverage"] = problems, warnings, cov
            for p in problems:
                emit(f"{p['path'] or p['id'] or '-'}: {p['code']} {p['msg']}")
            for w in warnings:
                emit(f"warning: {w}")
            emit(f"flow check: {len(recs)} records of the kinds {', '.join(cov['kinds'])}; {len(problems)} problem(s), {len(warnings)} warning(s); "
                 + (f"declaration evidence via {cfg.manifest if cov['manifest'] else 'NOT CONFIGURED'}; "
                    f"probe evidence via {cfg.probes if cov['probes'] else 'NOT CONFIGURED'}; " if cfg.has("finding") else "")
                 + f"reflow via {cov['reflow']}; markdownlint {'present' if cov['markdownlint'] else 'ABSENT'}")
            lc = cov["library"]
            emit("library: " + (f"NOT CONFIGURED ({cfg.library_route}) — a cited key is not checked" if not cfg.library_cmd else
                                f"DID NOT ANSWER ({cfg.library_route})" if lc is None else
                                f"{lc['cited']} key(s) cited from {lc['records']} record(s)"
                                + (", by read grade: " + ", ".join(f"{n} {g}" for g, n in sorted(lc["grades"].items())) if lc["grades"] else "")
                                + f"; {lc['excluded']} of them excluded cards; the papers' reference entries are not read here; asked through {cfg.library_route}"))
            if problems:
                out["ok"] = False
        else:
            raise Refused("no command (see --help)")
    except Refused as e:
        out["ok"], not_run = False, isinstance(e, NotRun)
        out["problems"].append({"code": "REFUSED", "id": None, "path": None, "msg": str(e)})
        if not quiet and not as_json:
            print(f"flow: {'could not run' if not_run else 'refused'} — {e}", file=sys.stderr)
    if as_json and not quiet:
        print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return (0 if out["ok"] else 2 if not_run else 1), out


def refused(command, msg, as_json):
    """A refusal before any command ran, in the answer's own shape under --json."""
    if as_json:
        print(json.dumps({"ok": False, "command": command, "problems": [{"code": "REFUSED", "id": None, "path": None, "msg": msg}]},
                         ensure_ascii=False, indent=1))
    else:
        print(f"flow: {msg}", file=sys.stderr)


def main():
    """The command line; a crash exits 2, could not run, never 1, which says problems were found."""
    try:
        return _main()
    except Exception:
        traceback.print_exc()
        print("flow: could not run (the error above)", file=sys.stderr)
        return 2


def _main():
    if "--selftest" in sys.argv:
        return selftest()
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--root")
    pre.add_argument("--json", action="store_true")
    pre.add_argument("--today")
    known, rest = pre.parse_known_args()
    # the global flags are read wherever they stand (`flow check --json` as well as `flow --json check`)
    argv = (["--json"] if known.json else []) + (["--root", known.root] if known.root else []) \
        + (["--today", known.today] if known.today else []) + rest
    if not rest or rest[0] in ("-h", "--help"):  # the command list needs no bindings file
        build_parser().print_help()
        return 0
    if "-h" in rest or "--help" in rest:  # a subcommand's flags need none either
        build_parser().parse_args(rest)
        return 0
    if rest and rest[0] == "init":
        a = build_parser().parse_args(["init"] + rest[1:])
        try:
            root = Path(known.root).resolve() if known.root else Path(os.getcwd()).resolve()
            written = do_init(root, a)
        except Refused as e:
            refused("init", str(e), known.json)
            return 1
        if known.json:
            print(json.dumps({"ok": True, "command": "init", "written": written}, indent=1))
        else:
            for w in written:
                print(f"wrote {w}")
            print()
            print(INSTRUCTIONS.format(records=a.records, log_line=LOG_BOUND.format(log=a.log) if a.log else LOG_UNBOUND))
        return 0
    try:
        root = Path(known.root).resolve() if known.root else find_root(os.getcwd())
        cfg = Config(root)
    except Refused as e:
        refused(rest[0], str(e), known.json)
        return 2
    rc, _ = dispatch(cfg, argv)
    return rc


if __name__ == "__main__":
    sys.exit(main())
