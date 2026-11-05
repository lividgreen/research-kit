#!/usr/bin/env python3
"""flow — the CLI, validator and index for a typed flow of work.

Records live as one Markdown file each, front matter plus a prose body, under the
directory `flow.toml` names.  Four kinds:

  idea      a thought not yet a question; open | consumed | removed  (drawn into a hand like a task)
  task      a unit of work; ready | active | done | aborted | removed  (closed tasks move to the archive)
  question  what we have to answer to move the research; open | answered | wrong | impossible | removed
  finding   a CHECKABLE claim: its evidence resolves against a declaration manifest, a
            document's numbered statement or table row, or a self-asserting probe; it never closes

A ready task or an open question may be parked (by decision) and blocked (by something it waits on),
both at once; it keeps its rank, and the lists mark the wait.

Transitions (the only writers of state and provenance):

  flow capture SUMMARY [--source S] [--from ID]... [--tag T]... [--body FILE]
  flow task SUMMARY --kind K [--from ID]... [--size s] [--dod D] [--source S] [--tag T]...
             [--body FILE]                                     a task, named after what it came from, if anything
  flow frame ID... --summary S --criterion C [--size s] [--kind question|conjecture] [--parent Q]
             [--direction D] [--tag T]... [--body FILE]        ideas -> consumed, or one finding
  flow refine Q --task SUMMARY [KIND] ... [--subq SUMMARY CRITERION]... [--idea SUMMARY]...
             [--kind K] [--size s] [--dod D] [--requires F]... [--body FILE]
  flow draw ID --owner O         a ready task -> active, or an open idea into the hand (hand limit from flow.toml)
  flow return ID [--note N]      active -> ready, or an idea out of the hand
  flow make T [--task SUMMARY [KIND]]... [--question SUMMARY CRITERION]... [--idea SUMMARY]...
             [--resolution FILE]                              active -> done, archived
  flow abort T --reason R [--resolution FILE]                 active -> aborted, archived
  flow finding SUMMARY STATUS EVIDENCE... [--from ID]... [--answers Q] [--depends-on F]... [--paper P]
             [--body FILE]                                     the one mint of a finding; --answers Q
                                                               closes Q answered by it
  flow consume IDEA              an open idea -> consumed into every card that names it in derived_from
  flow remove ID --reason R      idea(open) | question(open) | task(ready) -> removed
  flow wrong Q --reason R        question(open) -> wrong
  flow impossible Q --by F       question(open) -> impossible, F the finding that shows it
  flow park ID --reason R [--revival V]  |  flow unpark ID [--note N]     an open question or a ready task
  flow block ID --on X --reason R        |  flow unblock ID [--note N]    X a task, a question or a condition
  flow rank ID N [--insert] [--why W] [--first-move M] [--direction D]   |  rank --set ID...  |  rank ID --clear
  flow checked ID...             refresh the last-checked date
  flow set ID FIELD VALUE        one hand-editable field: summary, criterion (question), size,
                                 dod (task), rider on|off (ready or active task),
                                 depends_on "F F…"|none (finding; a cycle is refused)

Views: find, show, graph, state (the cold-start bundle), directions, index [--check | --print], check;
`pages` (the dashboard's page manifest); `--json` on every command.

  flow state --check             what a machine sees of a freeze: the log's top entry today's where the tree
                                 changed since the newest committed entry, every record changed since then named;
                                 the hands' active tasks and drawn ideas printed
  flow doctor                    every record and binding written in an older model's words, and what it reads now
  flow log add FILE              one entry at the top of the log, reflowed and linted as a record is
  flow log archive --before DATE the older entries moved verbatim, one file per month, into `[paths] log_archive`
  flow reflow --check PATH...    the lines of the project's other prose that are not one sentence per line
  flow reflow --as DEST DRAFT    a draft checked as if appended to DEST: the reflow, then markdownlint
`flow init [--records DIR] [--log FILE] [--owner O]... [--force]` writes a project's `flow.toml`, its
directories and its inbox, and prints the paragraph the project's instructions should carry.
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
import posixpath
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

TYPES = ("idea", "question", "task", "finding", "goal", "direction")
STATES = {
    "idea": ("open", "consumed", "removed"),
    "question": ("open", "answered", "wrong", "impossible", "removed"),
    "task": ("ready", "active", "done", "aborted", "removed"),
    "finding": (),
    "goal": ("open", "reached", "given_up"),
    "direction": ("open", "closed"),
}
CLOSED_TASK = ("done", "aborted", "removed")
SCHEMA = {
    "idea": ("id", "type", "state", "summary", "source", "derived_from", "owner", "drawn", "consumed_by",
             "closed", "origin", "created", "tags"),
    "question": ("id", "type", "kind", "state", "summary", "derived_from", "parent", "size",
                 "criterion", "checked", "parked", "blocked", "rank", "why_now", "first_move", "direction", "serves",
                 "answered_by", "closed", "origin", "source", "created", "tags"),
    "task": ("id", "type", "state", "summary", "derived_from", "requires",
             "size", "owner", "drawn", "dod", "due", "after", "rank", "why_now", "first_move", "rider",
             "parked", "blocked", "closed", "origin", "source", "created", "tags"),
    "finding": ("id", "type", "summary", "evidence", "derived_from",
                "depends_on", "origin", "source", "created", "tags"),
    "goal": ("id", "type", "state", "summary", "criterion", "horizon", "derived_from",
             "closed", "origin", "source", "created", "tags"),
    "direction": ("id", "type", "state", "summary", "derived_from", "closed", "origin", "source", "created", "tags"),
}
LIST_FIELDS = ("derived_from", "requires", "evidence", "depends_on", "consumed_by", "tags")
CLI_ONLY = ("id", "type", "state", "derived_from", "consumed_by", "owner", "drawn",
            "answered_by", "direction", "serves", "rank", "parked", "blocked", "closed", "origin", "created")
# The five evidence forms the kit ships, the words a finding's trust is read from; a project picks the ones it
# accepts in [evidence] forms and adds its own.
SHIPPED_FORMS = ("formal", "statistical", "peer-reviewed", "stated", "reference")
# The words of the models before this one, which `flow doctor` names and the check refuses: states and fields
# renamed, and fields dropped (a task or a finding no longer belongs to a question; a task's kind is a tag; a
# finding's status is read from the forms of its evidence, and its paper is a reference like any other).
OLD_STATES = {"abandoned", "decomposed"}
OLD_FIELDS = {"abandoned": "closed", "kill": "criterion"}
DROPPED_FIELDS = {"task": ("question", "kind"), "finding": ("question", "status", "paper")}
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
    def __init__(self, root, bare=False):
        """The bindings of the project at `root`; `bare`, the defaults alone where no flow.toml stands there,
        for the commands that read prose and no record (`flow reflow`)."""
        self.root = Path(root)
        if not (self.root / "flow.toml").is_file():
            if not bare:
                raise Refused(f"no flow.toml at {self.root}")
            raw = {}
        else:
            try:
                raw = tomllib.loads((self.root / "flow.toml").read_text(encoding="utf-8"))
            except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
                raise Refused(f"{self.root / 'flow.toml'} does not parse: {e}")
        self.raw = raw
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
        # the directions file of the models before this one, read by `flow doctor` alone: directions are records
        self.directions_file = self.root / paths.get("directions", f"{rec_dir}/directions.md")
        # what the person drops between sessions, read at the start of the next one (the `whatsnext` skill)
        self.inbox = self.root / paths.get("inbox", "INBOX.md")
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
        # The evidence forms the project accepts: of the five the kit ships, and its own words; an item of a
        # form not listed is refused.  Unbound, the five shipped forms.
        forms = ev.get("forms", SHIPPED_FORMS)
        self.forms = tuple(str(f) for f in ([forms] if isinstance(forms, str) else forms))
        for f in self.forms:
            if not re.fullmatch(r"[a-z][a-z0-9-]*", f):
                raise Refused(f"flow.toml: [evidence] forms names {f!r}: a form is one lowercase word (letters, digits, hyphens)")
        pre = raw.get("prefixes", {})
        self.prefix = {t: pre.get(t, t) for t in TYPES}
        self.id_width = int(pre.get("id_width", 4))
        self.hand = raw.get("hand", {})
        self.owners = tuple(self.hand.keys()) or ("agent",)
        self.sizes = tuple(raw.get("question", {}).get("sizes", ("small", "medium", "large")))
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

    def dir_of(self, type_):
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
    elif type_ in ("goal", "direction"):
        fm["state"] = "open"
    for k, v in fields.items():
        if k not in fm:
            raise Refused(f"{type_} has no field {k}")
        fm[k] = v
    if not fm.get("summary"):
        raise Refused(f"a {type_} needs a summary")
    path = cfg.dir_of(type_) / f"{fm['id']}-{slugify(fm['summary'])}.md"
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
EV_URL = re.compile(r"^[a-z][a-z0-9+.-]*://|^(?:mailto|doi|urn):", re.I)  # a scheme: the target is no repository path
EV_KEY = re.compile(r"^([a-z0-9][a-z0-9-]*)(?:#([a-z0-9][a-z0-9-]*))?$")  # a library key, with an extract after `#`
FORM_WORD = re.compile(r"^[a-z][a-z0-9-]*$")
LINK = re.compile(r"\]\((?:<([^>]+)>|([^)\s]+))\)")  # a Markdown link's target, in angle brackets where it holds a space


def split_evidence(item):
    """(form, target) of an evidence item `form:target`; None where it carries no form."""
    form, sep, target = str(item).partition(":")
    if not sep or not target or not FORM_WORD.match(form):
        return None
    return form, target


def evidence_form(item):
    s = split_evidence(item)
    return s[0] if s else None


def forms_of(r):
    """The forms a finding's evidence carries, sorted: its trust, as words."""
    return sorted({f for f in (evidence_form(e) for e in r["evidence"] or []) if f})


def norm_path(target):
    """A repository path as the records compare it: the part before any anchor, root-relative, `./` and doubled
    slashes folded, so `./papers//alpha.md` and `papers/alpha.md` are one path."""
    return posixpath.normpath(target.split("#", 1)[0]) if target else target


def evidence_path(item):
    """The repository path an evidence item names, before any anchor: a probe, a result, a document; None for a
    declaration (the manifest's, under its own roots), a library key or a URL."""
    s = split_evidence(item)
    if s is None or s[0] in ("formal", "peer-reviewed") or EV_URL.match(s[1]):
        return None
    return norm_path(s[1])


def body_links(body):
    """The repository paths a body links, root-relative, each before its anchor: a Markdown link's target that is
    neither a URL nor a bare anchor; a path in backticks is prose."""
    out = []
    for m in LINK.finditer(body or ""):
        t = (m.group(1) or m.group(2) or "").strip()
        if not t or t.startswith("#") or EV_URL.match(t):
            continue
        out.append(norm_path(t))
    return out


def _resolve_declaration(cfg, target):
    m = cfg.ev_decl.match(target) or cfg.ev_declfile.match(target)
    if not m:
        return f"formal takes a declaration (Path.{cfg.decl_ext or 'ext'}#name) or a whole module (Path.{cfg.decl_ext or 'ext'})"
    names = cfg.manifest_names()
    if names is None:
        return "unchecked: no declaration manifest configured"
    decl_file = next((cfg.root / r / m.group(1) for r in cfg.manifest_roots
                      if (cfg.root / r / m.group(1)).is_file()), None)
    if decl_file is None:
        return f"{m.group(1)} is not a file under {cfg.manifest_root}/"
    module = m.group(1).rsplit(".", 1)[0].replace("/", ".")
    if m.re is cfg.ev_declfile:  # a whole module as evidence: it must be a manifest module
        return None if module in cfg.manifest_modules() else f"module {module} is not in the manifest"
    if m.group(2) not in names:
        return f"`{m.group(2)}` is not in the manifest"
    if module in cfg.manifest_modules() and m.group(2) not in cfg._in_module[module]:
        return f"`{m.group(2)}` is not declared in {module}, the module of {m.group(1)}"
    return None


def _resolve_document(cfg, target, cache):
    """A statement or a row of a document of the project: the file, then the anchor in it."""
    m = EV_ROW.match(target) or EV_STMT.match(target)
    if not m:
        return f"stated takes a document's statement (doc.md#Theorem N[.M], or {', '.join(STMT_WORDS[1:])}) or row (doc.md#ROW)"
    f = cfg.root / m.group(1)
    if not f.is_file():
        return f"{m.group(1)} is not a file"
    text = cache.setdefault(f, f.read_text(encoding="utf-8"))
    if m.re is EV_ROW:
        return None if re.search(r"^\| %s \|" % re.escape(m.group(2)), text, re.M) else f"row {m.group(2)} is not in {m.group(1)}"
    if not re.search(r"(^|\*\*|#+ )%s %s\b" % (m.group(2), re.escape(m.group(3))), text, re.M):
        return f"{m.group(2)} {m.group(3)} is not in {m.group(1)}"
    return None


def _resolve_probe(cfg, target, cache):
    if not (cfg.root / target).is_file():
        return f"{target} is not a file"
    if not cfg.probes or not (cfg.root / cfg.probes).is_file():
        return "unchecked: no probes register bound ([evidence] probes)"
    text = cache.setdefault(cfg.root / cfg.probes, (cfg.root / cfg.probes).read_text(encoding="utf-8"))
    name = Path(target).name
    listed = {mm.group(1) for line in text.splitlines() if line.startswith("|")
              for mm in [re.fullmatch(r"`([^`]+\.py)`", line.split("|")[1].strip())] if mm}
    return None if name in listed else f"{name} is not listed in the probes register"


def resolve_evidence(cfg, item, cache, lib=None):
    """None when the item resolves; 'unchecked: …' where no resolver is bound for it; else the reason.  The form is
    held to [evidence] forms, the target to the shape its form takes: `formal` a declaration of the manifest,
    `statistical` a probe of the register or a committed result by its path (a row anchor checked), `peer-reviewed`
    a card of the library (`lib` its `keys` answer, asked where None), `stated` a statement or row of a document of
    the project, `reference` a URL for its form alone or a path for its existence; a form of the project's own, a
    path for its existence and anything else unchecked."""
    s = split_evidence(item)
    if s is None:
        return (f"no form: an item is form:target, the form one of {', '.join(cfg.forms)} "
                "(`flow doctor` names the prefix an older item takes)")
    form, target = s
    if form not in cfg.forms:
        return f"form {form!r} is not one [evidence] forms lists ({', '.join(cfg.forms)})"
    if form == "formal":
        return _resolve_declaration(cfg, target)
    if form == "stated":
        return _resolve_document(cfg, target, cache)
    if form == "peer-reviewed":
        m = EV_KEY.match(target)
        if not m:
            return "peer-reviewed takes a library key (key, or key#extract)"
        lib = library_keys(cfg) if lib is None else lib
        if lib is None:
            return "unchecked: no library bound"
        if lib.get("error"):
            return f"unchecked: the library did not answer ({lib['error']})"
        if m.group(1) not in lib["cards"]:
            return f"the library holds no card {m.group(1)}"
        held = (lib["cards"][m.group(1)] or {}).get("extracts")
        if m.group(2) and held is not None and m.group(2) not in held:
            return f"the library's card {m.group(1)} carries no extract {m.group(2)}"
        return None
    if form == "statistical" and EV_PROBE.match(target):
        return _resolve_probe(cfg, target, cache)
    if EV_URL.match(target):
        return None if form == "reference" else f"unchecked: a form of the project's ({form}), its target no path"
    path = target.split("#", 1)[0]
    if form in ("statistical", "reference"):
        if not (cfg.root / path).exists():
            return f"{path} is not in the tree"
        if form == "statistical" and EV_ROW.match(target):  # a result's row: checked as a document's is
            return _resolve_document(cfg, target, cache)
        return None
    if (cfg.root / path).exists():
        return None
    if "/" in path or re.search(r"\.\w+$", path):
        return f"{path} is not in the tree"
    return f"unchecked: a form of the project's ({form})"


def resolve_items(cfg, items, have=()):
    """Every item of a mint or an append resolved, or the first reason refused; an item already held refused."""
    cache, seen = {}, set(have)
    lib = library_keys(cfg) if any(evidence_form(e) == "peer-reviewed" for e in items) else None
    for e in items:
        if e in seen:
            raise Refused(f"evidence {e} is there already")
        seen.add(e)
        why = resolve_evidence(cfg, e, cache, lib)
        if why and not why.startswith("unchecked"):
            raise Refused(f"evidence {e}: {why}")


# --- validation --------------------------------------------------------------

def index_form(text):
    """An index with its form set aside — a table's delimiter row — so an index that differs from the render
    only in how a version of the flow lays it out is told from a stale one."""
    return "\n".join("|-|" if re.fullmatch(r"\|(?: ?:?-+:? ?\|)+", l.strip()) else l.rstrip() for l in text.split("\n"))


def waits(r):
    """The waits a record carries, as words for a list: parked by decision, blocked by what it names."""
    out = []
    p, b = r["parked"] if "parked" in r.fm else None, r["blocked"] if "blocked" in r.fm else None
    if isinstance(p, dict):
        out.append(f"parked {p.get('date')} — {str(p.get('reason', '')).split('. ')[0]}")
    if isinstance(b, dict):
        out.append(f"blocked on {b.get('on')} {b.get('date')} — {str(b.get('reason', '')).split('. ')[0]}")
    return out


def came_from(r, id_):
    """Whether record r names id_ as what it came from."""
    return isinstance(r["derived_from"], list) and id_ in r["derived_from"]


LIVE = {"idea": ("open",), "question": ("open",), "task": ("ready", "active"), "goal": ("open",), "direction": ("open",)}


def live(r):
    """Whether a record is at the front of work: open, ready or active; a finding always, since it accumulates."""
    return r.type == "finding" or r["state"] in LIVE.get(r.type, ())


def passed_date(text, today):
    """The first ISO date in a condition's words that is today or earlier, else None: a block `--on "2026-12-01"`."""
    for d in re.findall(r"\d{4}-\d{2}-\d{2}", str(text or "")):
        if d <= today:
            return d
    return None


def live_tasks(recs, qid):
    """The open tasks that came from a question, which its closing waits on."""
    return [x.id for x in recs.values() if x.type == "task" and came_from(x, qid) and x["state"] in ("ready", "active")]


def validate(cfg, recs, today):
    problems, warnings = [], []
    cache = {}
    coverage = {"records": len(recs), "kinds": list(cfg.kinds), "forms": list(cfg.forms), "manifest": cfg.manifest_names() is not None,
                "probes": bool(cfg.probes and (cfg.root / cfg.probes).is_file()),
                "reflow": cfg.reflow_source, "markdownlint": bool(shutil.which("markdownlint"))}

    def bad(code, r, msg):
        problems.append({"code": code, "id": r.id if r else None,
                         "path": rel(cfg, r.path) if r else None, "msg": msg})

    by_owner = Counter()
    tasks_of = defaultdict(list)
    derived_from_ = defaultdict(set)
    for r in recs.values():
        for x in r["derived_from"] if isinstance(r["derived_from"], list) else []:
            derived_from_[x].add(r.id)
            if r.type == "task":
                tasks_of[x].append(r)
    ranks = defaultdict(list)
    lib = library_keys(cfg)
    cited, citers = Counter(), set()
    if lib is not None and lib.get("error"):
        problems.append({"code": "V23", "id": None, "path": None, "msg": f"the library did not answer: {lib['error']}"})

    for r in recs.values():
        t = r.type
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
        expected_dir = cfg.dir_of(t)
        in_archive = r.path.parent.resolve() == cfg.archive.resolve()
        if t == "task" and r["state"] in CLOSED_TASK and not in_archive:
            bad("V21", r, "a closed task must live in the archive")
        elif (t != "task" or r["state"] not in CLOSED_TASK) and r.path.parent.resolve() != expected_dir.resolve():
            bad("V21", r, f"expected under {rel(cfg, expected_dir)}")
        for k in SCHEMA[t]:
            if k not in r.fm:
                bad("V3", r, f"missing field {k}" + (" (`flow doctor` names the records of an older model)"
                                                     if any(o in r.fm for o in OLD_FIELDS) else ""))
        for k in r.fm:
            if k not in SCHEMA[t]:
                bad("V3", r, f"unknown field {k}" + (f": it reads {OLD_FIELDS[k]} now (`flow doctor`)" if k in OLD_FIELDS else
                                                     " of an older model (`flow doctor`)" if k in DROPPED_FIELDS.get(t, ()) else ""))
        if STATES[t] and r["state"] not in STATES[t]:
            bad("V3", r, f"state {r['state']!r} not in {STATES[t]}" + (" (`flow doctor`)" if r["state"] in OLD_STATES else ""))
        if t == "question" and r["kind"] not in ("question", "conjecture"):
            bad("V3", r, f"kind {r['kind']!r}")
        if t in ("question", "task") and r["size"] not in (None, *cfg.sizes):
            bad("V3", r, f"size {r['size']!r} not in {cfg.sizes}")
        if t in ("task", "idea") and r["owner"] not in (None, *cfg.owners):
            bad("V3", r, f"owner {r['owner']!r} not in {cfg.owners}")
        if r["origin"] not in ("current", "legacy"):
            bad("V3", r, f"origin {r['origin']!r}")
        for f in ("created", "checked", "drawn"):
            v = r[f] if f in SCHEMA[t] else None
            if v is not None and not ISO.match(str(v)):
                bad("V20", r, f"{f} is not an ISO date")
            elif v is not None and str(v) > today:
                bad("V20", r, f"{f} is in the future")
        if t == "task" and r["due"] is not None and not ISO.match(str(r["due"])):
            bad("V20", r, "due is not an ISO date")  # a due date lies ahead as a rule, so it is never held to today
        for f in ("parked", "blocked", "closed"):
            block = r[f] if f in SCHEMA[t] else None
            d = block.get("date") if isinstance(block, dict) else None
            if d is not None and not ISO.match(str(d)):
                bad("V20", r, f"{f}.date is not an ISO date")
            elif d is not None and str(d) > today:
                bad("V20", r, f"{f}.date is in the future")
        # references
        refs = {"derived_from": None, "requires": "finding", "depends_on": "finding", "answered_by": None,
                "parent": "question", "consumed_by": None, "direction": "direction", "serves": "goal"}
        for f, want in refs.items():
            if f not in SCHEMA[t]:
                continue
            vals = r[f] if isinstance(r[f], list) else ([r[f]] if r[f] else [])
            for v in vals:
                if v not in recs:
                    bad("V2", r, f"{f} names {v}, which does not exist"
                        + (" (a direction is a record now, named by its id: `flow doctor`)" if f == "direction" else ""))
                elif want and recs[v].type != want:
                    bad("V2", r, f"{f} names {v}, a {recs[v].type}, not a {want}")
        # the closing: a dated reason where the closing has one, and none on an open record
        closing = {"idea": ("removed",), "question": ("wrong", "removed"), "task": ("aborted", "removed"),
                   "goal": ("reached", "given_up"), "direction": ("closed",)}.get(t, ())
        c = r["closed"] if "closed" in SCHEMA[t] else None
        if r["state"] in closing and not (isinstance(c, dict) and c.get("date") and c.get("reason")):
            bad("V17", r, f"{r['state']} without a dated reason (`closed`: date, reason)")
        elif c is not None and r["state"] not in closing:
            bad("V17", r, f"a dated closing reason on a record that is {r['state']}")
        # the positions: parked and blocked on an open question or a ready task, either or both
        if t in ("question", "task"):
            where = "an open question" if t == "question" else "a ready task"
            ok_state = r["state"] == ("open" if t == "question" else "ready")
            p, b = r["parked"], r["blocked"]
            if p is not None and (not ok_state or not isinstance(p, dict) or not p.get("date") or not p.get("reason")):
                bad("V15", r, f"parked needs {where} with a date and a reason")
            if b is not None and (not ok_state or not isinstance(b, dict) or not b.get("date") or not b.get("on") or not b.get("reason")):
                bad("V15", r, f"blocked needs {where} with a date, what it waits on and a reason")
            if isinstance(b, dict) and b.get("on") in recs and stat(recs[b["on"]]) in (*CLOSED_TASK, "answered", "wrong", "impossible"):
                warnings.append(f"{r.id}: blocked on {b['on']}, which is {stat(recs[b['on']])}: unblock it, or say what it waits on now")
            elif isinstance(b, dict) and ok_state and b.get("on") not in recs and passed_date(b.get("on"), today):
                warnings.append(f"{r.id}: blocked on {b['on']}, whose date has passed: unblock it, or say what it waits on now")
        if t == "task":
            if r["state"] in ("ready", "active") and r["due"] is not None and ISO.match(str(r["due"])) and str(r["due"]) <= today:
                warnings.append(f"{r.id}: due {r['due']} has passed")
            if r["state"] == "ready":
                for f in r["requires"] or []:
                    if f not in recs:
                        bad("V5", r, f"ready with unmet requires {f}")
            if r["state"] == "active":
                if r["owner"]:
                    by_owner[r["owner"]] += 1
                else:
                    bad("V9", r, "active without an owner")
            elif r["state"] in CLOSED_TASK and r["owner"]:
                bad("V20", r, f"a {r['state']} task carries an owner")  # its drawn date stays, the day its work began
            elif r["state"] == "ready" and (r["owner"] or r["drawn"]):
                bad("V9", r, "a ready task carries an owner or a drawn date: it is in no hand")
            if r["state"] in ("ready", "active"):
                for x in r["derived_from"] or []:
                    if x in recs and recs[x].type == "question" and recs[x]["state"] != "open":
                        bad("V13", r, f"open task that came from {x}, a question that is {recs[x]['state']}")
        if t == "finding":
            if not r["evidence"]:
                bad("V6", r, "no evidence")
            seen = set()
            for e in r["evidence"] or []:
                if str(e) in seen:
                    bad("V6", r, f"evidence {e} twice")
                seen.add(str(e))
                why = resolve_evidence(cfg, str(e), cache, lib)
                if why and why.startswith("unchecked"):
                    warnings.append(f"{r.id}: {e}: {why}")
                elif why:
                    bad("V6", r, f"evidence {e}: {why}")
        if t == "question":
            if r["state"] == "open" and not r["checked"]:
                bad("V12", r, "open without a checked date")
            if r["origin"] == "current" and not r["criterion"]:
                bad("V16", r, "a current question needs a criterion: what would answer it, or show it wrong or impossible")
            by = r["answered_by"]
            if isinstance(by, list):
                bad("V18", r, "answered_by is one finding, not a list (`flow doctor`)")
            elif r["state"] in ("answered", "impossible"):
                if by is None and r["origin"] != "legacy":
                    bad("V18", r, f"{r['state']} needs the one finding that settles it in answered_by")
                elif by in recs and recs[by].type == "task":
                    bad("V18", r, f"{r['state']} by {by}, a task: a finding settles a question "
                                  f"(`flow finding … --from TASK`), or the question reads as removed")
                elif by in recs and recs[by].type != "finding":
                    bad("V18", r, f"{r['state']} by {by}, a {recs[by].type}, not a finding")
            elif by is not None:
                bad("V18", r, f"answered_by on a question that is {r['state']}")
            if r["state"] == "open":
                ts = tasks_of.get(r.id, [])
                if ts and all(x["state"] in CLOSED_TASK for x in ts):
                    warnings.append(f"{r.id}: needs refine or answer (every task closed)")
            for f, want in (("direction", "direction"), ("serves", "goal")):
                v = r[f]
                if v in recs and recs[v].type == want and r["state"] == "open" and recs[v]["state"] != "open":
                    bad("V22", r, f"{f} names {v}, a {want} that is {recs[v]['state']}: an open question names an open one, or none")
        if t == "idea":
            if r["state"] == "consumed":
                into = r["consumed_by"] if isinstance(r["consumed_by"], list) else [r["consumed_by"]] if r["consumed_by"] else []
                if not isinstance(r["consumed_by"], list) and r["consumed_by"]:
                    bad("V17", r, "consumed_by lists the cards it was folded into, not one id (`flow doctor`)")
                elif not into or any(x not in derived_from_.get(r.id, set()) for x in into):
                    bad("V17", r, "consumed without the cards it was folded into, each naming it in derived_from")
            elif r["consumed_by"]:
                bad("V17", r, f"consumed_by on an idea that is {r['state']}")
            if r["owner"]:
                if r["state"] != "open" or not r["drawn"]:
                    bad("V9", r, "an idea in a hand is open and carries its drawn date")
                else:
                    by_owner[r["owner"]] += 1
            elif r["drawn"]:
                bad("V9", r, "a drawn date on an idea in no hand")
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
            if not _rankable(cfg, r):
                bad("V14", r, "rank on a closed record")
            if not r["why_now"] or not r["first_move"]:
                bad("V14", r, "a ranked record needs why_now and first_move")
            if isinstance(r["rank"], int) and not isinstance(r["rank"], bool):
                ranks[r["rank"]].append(r.id)
            else:
                bad("V3", r, f"rank {r['rank']!r} is not a whole number")
        if cfg.reflow_source and r.body and cfg.reflow(r.body) != r.body:
            bad("V19", r, "body is not one sentence per line (reflow changes it)")
        # the artifacts a body links: a path that is gone fails a live record and is warned of on a closed one
        for p in sorted(set(body_links(r.body))):
            if not (cfg.root / p).exists():
                if live(r):
                    bad("V24", r, f"the body links {p}, which is not in the tree")
                else:
                    warnings.append(f"{r.id}: the body links {p}, which is not in the tree")
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
            problems.append({"code": "V9", "id": None, "path": None, "msg": f"{o} holds {n} records; limit {lim}"})
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
    counts = Counter((r.type, stat(r)) for r in R if r["state"] != "removed")  # a removed record is in no list and no count
    for (t, s), n in sorted(counts.items()):
        out.append(f"| {t} | {s} | {n} |")
    out.append("")

    def section(title, rows):
        out.extend([f"## {title}", ""])
        out.extend(rows if rows else ["none"])
        out.append("")

    # the due dates, soonest first: a date never moves a rank, and the index never reads the day, so a passed
    # one is marked by `flow state` and warned of by `flow check`, not here
    due = sorted((r for r in R if r.type == "task" and r["state"] in ("ready", "active") and r["due"] is not None),
                 key=lambda r: (str(r["due"]), r.id))
    if due:
        section("Due", [_line(r, f"due {r['due']}" + (", active" if r["state"] == "active" else "")) for r in due])

    ranked = sorted((r for r in R if r["rank"] is not None), key=lambda r: (0, r["rank"], "") if isinstance(r["rank"], int) else (1, 0, str(r["rank"])))
    rows = []
    for r in ranked:
        bits = [f"why now: {r['why_now']}", f"first move: {r['first_move']}"]
        if r.type == "question" and r["serves"]:
            bits.insert(0, f"serves: {r['serves']}")
        if r.type == "question" and r["direction"]:
            bits.insert(0, f"direction: {r['direction']}")
        bits += [f"waits: {w}" for w in waits(r)]
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
        held += [r for r in R if r.type == "idea" and r["state"] == "open" and r["owner"] == o]
        lim = int(cfg.hand.get(o, 0) or 0)

        def what(r):
            if r.type == "idea":
                return f"idea, drawn {r['drawn']}"
            return ", ".join([*(str(t) for t in r["tags"] or []), f"drawn {r['drawn']}"] + list(r["derived_from"] or []))
        rows += ([f"{len(held)} of {lim}", ""] if lim and held else []) + ([_line(r, what(r)) for r in held] or ["none"])
        rows.append("")
    section("Hand", rows[:-1])

    # the goals and the directions, the pulls on the ranking: each open goal with what reached means, its horizon
    # and the open questions serving it; each open direction with its date
    goals = sorted((r for r in R if r.type == "goal" and r["state"] == "open"), key=lambda r: r.id)
    if goals:
        rows = []
        for g in goals:
            rows.append(_line(g, "; ".join(x for x in (f"reached: {g['criterion']}", f"horizon: {g['horizon']}" if g["horizon"] else "") if x)))
            served = sorted((q for q in R if q.type == "question" and q["state"] == "open" and q["serves"] == g.id), key=lambda q: q.id)
            rows += [f"  - `{q.id}` — {q['summary']}" for q in served] or ["  - no open question serves it"]
        section("Goals", rows)
    dirs = sorted((r for r in R if r.type == "direction" and r["state"] == "open"), key=lambda r: r.id)
    if dirs:
        section("Directions", [_line(r, str(r["created"])) for r in dirs])

    order = {s: i for i, s in enumerate(cfg.sizes)}
    ready = [r for r in R if r.type == "task" and r["state"] == "ready"]
    ready.sort(key=lambda r: (order.get(r["size"], len(order)), r.id))
    section("Ready", [_line(r, "; ".join([", ".join(x for x in (*(str(t) for t in r["tags"] or []), r["size"], *(r["derived_from"] or [])) if x)] + waits(r))) for r in ready])

    if cfg.has("question"):
        opn = [r for r in R if r.type == "question" and r["state"] == "open" and r["parked"] is None and r["blocked"] is None]
        opn.sort(key=lambda r: (str(r["checked"]), r.id))
        section("Open questions", [_line(r, ", ".join(x for x in (r["size"], f"checked {r['checked']}", r["direction"], r["serves"]) if x)) for r in opn])

        wait = [r for r in R if r.type == "question" and r["state"] == "open" and (r["parked"] is not None or r["blocked"] is not None)]
        wait.sort(key=lambda r: r.id)
        section("Parked or blocked questions", [_line(r, "; ".join(waits(r))) for r in wait])

        tasks_of = defaultdict(list)
        for r in R:
            for x in (r["derived_from"] or []) if r.type == "task" else []:
                tasks_of[x].append(r)
        need = [r for r in R if r.type == "question" and r["state"] == "open" and tasks_of[r.id]
                and all(x["state"] in CLOSED_TASK for x in tasks_of[r.id])]
        section("Needs refine or answer", [_line(r, f"{len(tasks_of[r.id])} tasks, all closed") for r in sorted(need, key=lambda r: r.id)])

    if cfg.has("finding"):
        fnd = sorted((r for r in R if r.type == "finding"), key=lambda r: r.id, reverse=True)[:cfg.recent_findings]
        section("Recent findings", [_line(r, stat(r)) for r in fnd])

    if cfg.has("question"):
        settled = [r for r in R if r.type == "question" and (r["state"] in ("wrong", "impossible")
                                                              or (r["state"] != "removed" and "do-not-reopen" in (r["tags"] or [])))]
        section("Settled, do not re-open", [_line(r, r["state"]) for r in sorted(settled, key=lambda r: r.id)])

    ideas = [r for r in R if r.type == "idea" and r["state"] == "open" and not r["owner"]]
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


# The ranks a transition renumbered without being asked, (id, from, to): reported as re-ranks, not as changes.
_RERANKED = []


def close_ranks(cfg, recs):
    """The ranked records renumbered 1..n in their order, after a transition cleared one of them:
    the list stays contiguous without a hand on it.  Each move is recorded in _RERANKED."""
    ranked = sorted((r for r in recs.values() if r.type in ("question", "task") and r["rank"] is not None),
                    key=lambda r: (r["rank"] if isinstance(r["rank"], int) else 10**9, r.id))
    for n, r in enumerate(ranked, 1):
        if r["rank"] != n:
            _RERANKED.append((r.id, r["rank"], n))
            r.fm["rank"] = n
            save(cfg, r)


def save(cfg, rec):
    write_record(cfg, rec)


def sources(recs, ids, what):
    """The records a new card names as what it came from: each exists and none is removed."""
    out = []
    for i in ids or []:
        r = get(recs, i)
        if r["state"] == "removed":
            raise Refused(f"{i} is removed: a removed record produces nothing")
        out.append(r)
    return [r.id for r in out]


def cmd_capture(cfg, recs, a, today):
    r = new_record(cfg, "idea", {"summary": a.summary, "source": a.source, "tags": a.tag or [],
                                 "derived_from": sources(recs, a.from_, "capture")}, read_body(a.body), today)
    return [r], []


def check_direction(recs, direction):
    """A question's direction is an open direction record, named by its id."""
    if direction:
        get(recs, direction, "direction", ("open",))


def check_goal(recs, goal):
    """A question serves an open goal, named by its id."""
    if goal:
        get(recs, goal, "goal", ("open",))


def check_due(due):
    if due is not None and not ISO.match(str(due)):
        raise Refused("--due takes a date, YYYY-MM-DD")
    return due


def cmd_task(cfg, recs, a, today):
    derived = sources(recs, a.from_, "task")
    for i in derived:
        if recs[i].type == "question" and recs[i]["state"] != "open":
            raise Refused(f"{i} is {recs[i]['state']}: an open task comes from an open question")
    r = new_record(cfg, "task", {"summary": a.summary, "size": a.size, "dod": a.dod, "due": check_due(a.due), "after": a.after,
                                 "derived_from": derived, "source": a.source, "tags": a.tag or []}, read_body(a.body), today)
    return [r], []


def consume(recs, rec, also=()):
    """The idea consumed into every card that names it in derived_from, `also` the ones a transition is minting."""
    into = sorted({r.id for r in recs.values() if came_from(r, rec.id)} | set(also))
    if not into:
        raise Refused(f"no card names {rec.id} in derived_from: an idea is consumed into the cards it was folded into; "
                      f"name it with `--from {rec.id}` as each is minted, or remove the idea")
    rec.fm.update({"state": "consumed", "consumed_by": into, "owner": None, "drawn": None})


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
    check_direction(recs, a.direction)
    check_goal(recs, a.serves)
    q = new_record(cfg, "question", {
        "summary": a.summary, "criterion": a.criterion, "size": a.size, "kind": a.kind, "parent": a.parent,
        "direction": a.direction, "serves": a.serves, "derived_from": [s.id for s in srcs], "tags": a.tag or [],
        "source": a.source}, read_body(a.body), today)
    for s in ideas:
        consume(recs, s, [q.id])
        save(cfg, s)
    return [q], ideas


def _mk_tasks(cfg, recs, specs, derived, today, size=None, dod=None, requires=None, tags=None):
    return [new_record(cfg, "task", {"summary": summary, "derived_from": derived, "size": size, "dod": dod,
                                     "requires": requires or [], "tags": list(tags or [])}, "", today) for summary in specs or []]


def _mk_questions(cfg, specs, derived, parent, today):
    out = []
    for spec in specs or []:
        if len(spec) != 2:
            raise Refused(f"--question/--subq takes SUMMARY CRITERION: {spec}")
        out.append(new_record(cfg, "question", {"summary": spec[0], "criterion": spec[1], "derived_from": derived,
                                                "parent": parent}, "", today))
    return out


def _mk_ideas(cfg, specs, source, derived, today):
    return [new_record(cfg, "idea", {"summary": s, "source": source, "derived_from": derived}, "", today) for s in specs or []]


def cmd_refine(cfg, recs, a, today):
    q = get(recs, a.question, "question", ("open",))
    if q["parked"] is not None:
        raise Refused(f"{q.id} is parked: unpark it first")
    if not a.task:
        raise Refused("refine produces at least one task")
    for f in a.requires or []:
        get(recs, f, "finding")
    made = _mk_tasks(cfg, recs, a.task, [q.id], today, a.size, a.dod, a.requires, a.tag)
    made += _mk_questions(cfg, a.subq, [q.id], q.id, today)
    made += _mk_ideas(cfg, a.idea, f"refine {q.id}", [q.id], today)
    if a.body:
        append_note(q, today, "refined:", read_body(a.body))
        save(cfg, q)
        return made, [q]
    return made, []


def held_by(recs, owner):
    """What an owner's hand holds: the active tasks drawn into it and the ideas drawn."""
    return [r for r in recs.values() if r["owner"] == owner and
            ((r.type == "task" and r["state"] == "active") or (r.type == "idea" and r["state"] == "open"))]


def cmd_draw(cfg, recs, a, today):
    r = get(recs, a.id)
    if r.type == "task":
        if r["state"] != "ready":
            raise Refused(f"{r.id} is {r['state']}, not ready")
        waiting = [w for w in ("parked", "blocked") if r[w] is not None]
        if waiting:
            raise Refused(f"{r.id} is {' and '.join(waiting)}: {' and '.join('un' + w[:-2] for w in waiting)} it first")
    elif r.type == "idea":
        if r["state"] != "open":
            raise Refused(f"{r.id} is {r['state']}, not open")
        if r["owner"]:
            raise Refused(f"{r.id} is in {r['owner']}'s hand already")
    else:
        raise Refused(f"{r.id} is a {r.type}: a task or an idea is drawn into a hand")
    if a.owner not in cfg.owners:
        raise Refused(f"owner {a.owner!r} not in {cfg.owners}")
    lim = int(cfg.hand.get(a.owner, 0) or 0)
    held = len(held_by(recs, a.owner))
    if lim and held >= lim:
        raise Refused(f"{a.owner}'s hand is full ({held} of {lim}); return or close a record first")
    r.fm.update({"owner": a.owner, "drawn": today})
    if r.type == "task":
        r.fm["state"] = "active"
    save(cfg, r)
    return [], [r]


def cmd_return(cfg, recs, a, today):
    r = get(recs, a.id)
    if r.type == "task":
        get(recs, a.id, "task", ("active",))
        r.fm.update({"state": "ready", "owner": None, "drawn": None})
    elif r.type == "idea" and r["state"] == "open" and r["owner"]:
        r.fm.update({"owner": None, "drawn": None})
    else:
        raise Refused(f"{r.id} is in no hand")
    made = sorted(x.id for x in recs.values() if came_from(x, r.id)) if r.type == "idea" else []
    if a.note or made:  # an idea put back partly worked lists what it produced so far
        append_note(r, today, "returned" + (f": {a.note}" if a.note else "") + (f"; produced so far: {', '.join(made)}" if made else ""))
    save(cfg, r)
    return [], [r]


def close_task(cfg, recs, t, state, today, reason=None):
    had_rank = t["rank"] is not None
    t.fm.update({"state": state, "owner": None, "rank": None, "why_now": None,
                 "first_move": None, "rider": False, "parked": None, "blocked": None,
                 "closed": {"date": today, "reason": reason} if reason else None})
    save(cfg, t)
    move_to_archive(cfg, t)
    if had_rank:
        close_ranks(cfg, recs)


def cmd_make(cfg, recs, a, today):
    t = get(recs, a.task, "task", ("active",))
    made = _mk_tasks(cfg, recs, a.task_out, [t.id], today, tags=a.tag)
    made += _mk_questions(cfg, a.question, [t.id], None, today)
    made += _mk_ideas(cfg, a.idea, f"make {t.id}", [t.id], today)
    if a.resolution:
        append_note(t, today, "resolution:", read_body(a.resolution))
    close_task(cfg, recs, t, "done", today)
    return made, [t]


def cmd_abort(cfg, recs, a, today):
    t = get(recs, a.task, "task", ("active",))
    if a.resolution:
        append_note(t, today, "resolution:", read_body(a.resolution))
    close_task(cfg, recs, t, "aborted", today, a.reason)
    return [], [t]


def check_closable(recs, q):
    live = live_tasks(recs, q.id)
    if live:
        raise Refused(f"{q.id} still has open tasks that came from it: {', '.join(live)} — make, abort or remove them first")


def close_question(cfg, recs, q, state, today, reason=None, by=None):
    had_rank = q["rank"] is not None
    q.fm.update({"state": state, "answered_by": by, "rank": None, "why_now": None, "first_move": None,
                 "parked": None, "blocked": None, "closed": {"date": today, "reason": reason} if reason else None})
    save(cfg, q)
    if had_rank:
        close_ranks(cfg, recs)


def cmd_finding(cfg, recs, a, today):
    """The one mint of a finding, whatever produced it; --from names what it came from (a done or aborted task,
    an idea, a question), --answers the one question it settles, which closes answered."""
    srcs = [get(recs, i) for i in a.from_ or []]
    for r in srcs:
        if r.type == "task" and r["state"] not in ("done", "aborted"):
            raise Refused(f"{r.id} is {r['state']}: a task's finding is minted after it is made or aborted")
        if r.type == "finding":
            raise Refused(f"{r.id} is a finding: what a finding rests on is --depends-on")
        if r["state"] == "removed":
            raise Refused(f"{r.id} is removed: a removed record produces nothing")
    q = None
    if a.answers:
        q = get(recs, a.answers, "question")
        if q["state"] != "open":
            by = q["answered_by"]
            if isinstance(by, list) or (by in recs and recs[by].type == "task"):
                raise Refused(f"{q.id} is {q['state']} in an older model's words (answered_by {by}): mint the finding "
                              f"without --answers and write it into answered_by by hand, as `flow doctor` says")
            raise Refused(f"{q.id} is {q['state']}" + (f", by {by}: one finding answers a question, "
                                                        f"and a later one names it with --from {q.id}" if q["state"] == "answered" else ""))
        check_closable(recs, q)
    resolve_items(cfg, a.evidence)
    for d in a.depends_on or []:
        get(recs, d, "finding")
    f = new_record(cfg, "finding", {"summary": a.summary, "evidence": list(a.evidence), "derived_from": [r.id for r in srcs],
                                    "depends_on": a.depends_on or [], "tags": a.tag or []}, read_body(a.body), today)
    if q is None:
        return [f], []
    close_question(cfg, recs, q, "answered", today, by=f.id)
    return [f], [q]


def cmd_evidence(cfg, recs, a, today):
    """Evidence added to a finding, never removed: the way its trust is raised, a proof formalized, a probe run,
    a work cited; each item resolved as at the mint."""
    f = get(recs, a.finding, "finding")
    resolve_items(cfg, a.evidence, have=f["evidence"] or [])
    f.fm["evidence"] = list(f["evidence"] or []) + list(a.evidence)
    save(cfg, f)
    return [], [f]


def cmd_goal(cfg, recs, a, today):
    """A goal the owner forms: an outcome with what reached means and a horizon; --from names the direction it was
    produced along, which stays open, or the idea it came from."""
    derived = sources(recs, a.from_, "goal")
    for i in derived:
        if recs[i].type == "direction" and recs[i]["state"] != "open":
            raise Refused(f"{i} is {recs[i]['state']}: a goal comes along an open direction")
    r = new_record(cfg, "goal", {"summary": a.summary, "criterion": a.criterion, "horizon": a.horizon, "derived_from": derived,
                                 "source": a.source, "tags": a.tag or []}, read_body(a.body), today)
    return [r], []


def cmd_reach(cfg, recs, a, today):
    g = get(recs, a.goal, "goal", ("open",))
    g.fm.update({"state": "reached", "closed": {"date": today, "reason": a.reason}})
    save(cfg, g)
    return [], [g]


def cmd_giveup(cfg, recs, a, today):
    """A goal given up releases its open questions: they stay open, serve nothing and keep their ranks, for
    `whatsnext` to re-rank; a closed question keeps what it served as history."""
    g = get(recs, a.goal, "goal", ("open",))
    g.fm.update({"state": "given_up", "closed": {"date": today, "reason": a.reason}})
    save(cfg, g)
    released = sorted((q for q in recs.values() if q.type == "question" and q["state"] == "open" and q["serves"] == g.id), key=lambda q: q.id)
    for q in released:
        q.fm["serves"] = None
        save(cfg, q)
    return [], [g] + released


def cmd_direction(cfg, recs, a, today):
    """A direction the owner opens: its name the summary, the owner's words its body, dated by `created`."""
    r = new_record(cfg, "direction", {"summary": a.summary, "derived_from": sources(recs, a.from_, "direction"),
                                      "source": a.source, "tags": a.tag or []}, read_body(a.body), today)
    return [r], []


def cmd_drop(cfg, recs, a, today):
    """A direction dropped releases its open questions, their `direction` cleared; a closed question keeps its as history."""
    d = get(recs, a.direction, "direction", ("open",))
    d.fm.update({"state": "closed", "closed": {"date": today, "reason": a.reason}})
    save(cfg, d)
    released = sorted((q for q in recs.values() if q.type == "question" and q["state"] == "open" and q["direction"] == d.id), key=lambda q: q.id)
    for q in released:
        q.fm["direction"] = None
        save(cfg, q)
    return [], [d] + released


def cmd_consume(cfg, recs, a, today):
    """An idea whose whole content is folded into other cards, one or many of any kind, each naming it in derived_from."""
    i = get(recs, a.idea, "idea", ("open",))
    consume(recs, i)
    save(cfg, i)
    return [], [i]


def cmd_remove(cfg, recs, a, today):
    r = get(recs, a.id)
    if r.type == "finding":
        raise Refused("a finding is never removed; refute it with a finding")
    if r.type == "task":
        if r["state"] != "ready":
            raise Refused(f"{r.id} is {r['state']}: remove takes a ready task; abort an active one" if r["state"] == "active"
                          else f"{r.id} is {r['state']} already")
        close_task(cfg, recs, r, "removed", today, a.reason)
        return [], [r]
    if r["state"] != "open":
        raise Refused(f"{r.id} is {r['state']} already")
    if r.type == "idea":
        r.fm.update({"state": "removed", "owner": None, "drawn": None, "closed": {"date": today, "reason": a.reason}})
        save(cfg, r)
        return [], [r]
    check_closable(recs, r)
    close_question(cfg, recs, r, "removed", today, reason=a.reason)
    return [], [r]


def cmd_wrong(cfg, recs, a, today):
    q = get(recs, a.question, "question", ("open",))
    check_closable(recs, q)
    close_question(cfg, recs, q, "wrong", today, reason=a.reason)
    return [], [q]


def cmd_impossible(cfg, recs, a, today):
    q = get(recs, a.question, "question", ("open",))
    f = get(recs, a.by, "finding")
    check_closable(recs, q)
    close_question(cfg, recs, q, "impossible", today, by=f.id)
    return [], [q]


def waitable(recs, id_):
    r = get(recs, id_)
    if r.type == "question" and r["state"] == "open":
        return r
    if r.type == "task" and r["state"] == "ready":
        return r
    if r.type == "task" and r["state"] == "active":
        raise Refused(f"{r.id} is active: return it first (`flow return {r.id} --note …`), then park or block it")
    raise Refused(f"{r.id} is a {r['state'] or ''} {r.type}: an open question or a ready task waits")


def cmd_park(cfg, recs, a, today):
    r = waitable(recs, a.id)
    if r["parked"] is not None:
        since = r["parked"].get("date") if isinstance(r["parked"], dict) else r["parked"]
        raise Refused(f"{r.id} is parked already, since {since}: unpark it first")
    r.fm["parked"] = {"date": today, "reason": a.reason, "revival": a.revival}
    save(cfg, r)
    return [], [r]


def cmd_unpark(cfg, recs, a, today):
    r = get(recs, a.id)
    if r.type not in ("question", "task") or r["parked"] is None:
        raise Refused(f"{r.id} is not parked")
    r.fm["parked"] = None
    if r.type == "question":
        r.fm["checked"] = today
    if a.note:
        append_note(r, today, "unparked: " + a.note)
    save(cfg, r)
    return [], [r]


def cmd_block(cfg, recs, a, today):
    r = waitable(recs, a.id)
    if r["blocked"] is not None:
        raise Refused(f"{r.id} is blocked already, on {r['blocked'].get('on')}: unblock it first")
    on = a.on.strip()
    if cfg.id_re.match(on + ".md") or on in recs:  # a record's id: a task or a question that exists
        w = get(recs, on)
        if w.type not in ("task", "question"):
            raise Refused(f"{on} is a {w.type}: a record waits on a task or a question, or on a condition in words")
        if w.id == r.id:
            raise Refused(f"{r.id} cannot wait on itself")
    if not on:
        raise Refused("block takes --on: a task, a question or a condition in words")
    r.fm["blocked"] = {"date": today, "on": on, "reason": a.reason}
    save(cfg, r)
    return [], [r]


def cmd_unblock(cfg, recs, a, today):
    r = get(recs, a.id)
    if r.type not in ("question", "task") or r["blocked"] is None:
        raise Refused(f"{r.id} is not blocked")
    r.fm["blocked"] = None
    if r.type == "question":
        r.fm["checked"] = today
    if a.note:
        append_note(r, today, "unblocked: " + a.note)
    save(cfg, r)
    return [], [r]


def _rankable(cfg, r):
    return (r.type == "question" and r["state"] == "open") or (r.type == "task" and r["state"] in ("ready", "active"))


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
                raise Refused(f"{r.id} cannot be ranked: it is {r['state'] or 'a ' + r.type}")
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
        if had_rank:
            close_ranks(cfg, recs)
        return [], [r]
    if a.n is None:
        raise Refused("rank takes ID N, --set ID..., or ID --clear")
    if not _rankable(cfg, r):
        raise Refused(f"{r.id} cannot be ranked: it is {r['state']}")
    n = int(a.n)
    others = sorted((o for o in recs.values() if o is not r and o.type in ("question", "task") and o["rank"] is not None),
                    key=lambda o: o["rank"])
    if not 1 <= n <= len(others) + 1:
        raise Refused(f"rank {n} would leave a gap: the ranks run 1..{len(others) + 1} with {r.id} among them")
    if not a.insert:
        for o in others:
            if o["rank"] == n:
                raise Refused(f"rank {n} is held by {o.id}: --insert puts {r.id} there and moves the rest down, "
                              f"and `flow rank --set ID…` writes the whole order at once")
    r.fm["rank"] = n
    if a.why:
        r.fm["why_now"] = a.why
    if a.first_move:
        r.fm["first_move"] = a.first_move
    for f, v, chk in (("direction", a.direction, check_direction), ("serves", a.serves, check_goal)):
        if v:
            if r.type != "question":
                raise Refused(f"a {f.replace('serves', 'goal')} is a question's; {r.id} is a {r.type}")
            chk(recs, v)
            r.fm[f] = v
    if r.type == "question":
        r.fm["checked"] = today
    if not r["why_now"] or not r["first_move"]:
        raise Refused("a ranked record needs --why and --first-move")
    save(cfg, r)
    if a.insert:  # the others keep their order around it, renumbered from 1
        for i, o in enumerate(others[:n - 1] + [None] + others[n - 1:], 1):
            if o is not None and o["rank"] != i:
                _RERANKED.append((o.id, o["rank"], i))
                o.fm["rank"] = i
                save(cfg, o)
    return [], [r]


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
SETTABLE = {"summary": ("idea", "question", "task", "finding", "goal", "direction"), "criterion": ("question", "goal"),
            "size": ("question", "task"), "dod": ("task",), "due": ("task",), "after": ("task",), "rider": ("task",),
            "serves": ("question",), "horizon": ("goal",), "depends_on": ("finding",)}


def cmd_set(cfg, recs, a, today):
    r = get(recs, a.id)
    if a.field not in SETTABLE:
        raise Refused(f"set takes one of {', '.join(SETTABLE)}; {a.field!r} is a transition's or no field"
                      + ("; `kill` reads `criterion` now" if a.field == "kill" else
                         "; a task names the question it came from in derived_from" if a.field == "question" else ""))
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
    elif a.field == "due":
        value = None if v == "none" else check_due(v)
    elif a.field == "serves":
        if r["state"] != "open":
            raise Refused(f"{r.id} is {r['state']}: what a closed question served stays as history")
        check_goal(recs, None if v == "none" else v)
        value = None if v == "none" else v
    elif a.field in ("after", "horizon"):
        value = None if v == "none" else v
        if value == "":
            raise Refused(f"{a.field} takes words, or none")
    else:
        if not v:
            raise Refused(f"{a.field} cannot be empty")
        value = v
    r.fm[a.field] = value
    save(cfg, r)
    return [], [r]


# --- the reference library, asked and never read ----------------------------------

def stat(r):
    """What a listing shows after a record's id: its state, or the forms a finding's evidence carries, its trust."""
    return (", ".join(forms_of(r)) or "no evidence") if r.type == "finding" else r["state"]


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

def refers_to(r, target):
    """Whether record r names `target`, a record's id or a repository path, in a reference field (`derived_from`,
    `requires`, `depends_on`, `consumed_by`, `answered_by`, `parent`, `direction`, `serves`, `blocked.on`), an
    evidence item or a body link."""
    for f in ("derived_from", "requires", "depends_on", "consumed_by"):
        if f in r.fm and isinstance(r[f], list) and target in r[f]:
            return True
    for f in ("answered_by", "parent", "direction", "serves"):
        if f in r.fm and r[f] == target:
            return True
    b = r["blocked"] if "blocked" in r.fm else None
    if isinstance(b, dict) and b.get("on") == target:
        return True
    if "evidence" in r.fm and any(evidence_path(e) == target for e in r["evidence"] or []):
        return True
    return target in body_links(r.body)


def referrers(recs, target, deep=False):
    """The ids of the records naming `target`; with `deep`, of those naming them, and so on."""
    found, frontier = set(), [target]
    while frontier:
        x = frontier.pop()
        for r in recs.values():
            if r.id not in found and r.id != target and refers_to(r, x):
                found.add(r.id)
                if deep:
                    frontier.append(r.id)
    return found


def cmd_find(cfg, recs, a, today):
    hits = []
    try:
        grep = re.compile(a.grep, re.I) if a.grep else None
    except re.error as e:
        raise Refused(f"--grep {a.grep!r} is not a regular expression: {e}")
    if a.deep and not a.refers:
        raise Refused("--deep follows --refers: flow find --refers ID --deep")
    target = a.refers if not a.refers or a.refers in recs else norm_path(a.refers)  # a path is compared as the records carry it
    naming = referrers(recs, target, a.deep) if a.refers else None
    for r in recs.values():
        if a.type and r.type != a.type:
            continue
        if a.state and r["state"] != a.state:
            continue
        if not a.state and r["state"] == "removed" and not a.id_:  # a removed record opens by its id, and is listed when asked by its state
            continue
        if a.id_ and r.id not in a.id_:
            continue
        if a.kind and r["kind"] != a.kind:
            continue
        if a.form and (r.type != "finding" or a.form not in forms_of(r)):
            continue
        if a.tag and a.tag not in (r["tags"] or []):
            continue
        if a.owner and r["owner"] != a.owner:
            continue
        if a.from_ and not came_from(r, a.from_):
            continue
        if naming is not None and r.id not in naming:
            continue
        if a.requires and a.requires not in (r["requires"] or []):
            continue
        if a.depends_on and a.depends_on not in (r["depends_on"] or []):
            continue
        if a.parked and (r.type not in ("question", "task") or r["parked"] is None):
            continue
        if a.blocked and (r.type not in ("question", "task") or r["blocked"] is None):
            continue
        if a.held and not ((r.type == "task" and r["state"] == "active") or (r.type == "idea" and r["owner"])):
            continue
        if a.ranked and r["rank"] is None:
            continue
        if a.grep and not grep.search(render(r.fm, r.body)):
            continue
        hits.append(r)
    return hits


REF_LISTS = ("derived_from", "requires", "depends_on", "consumed_by")
REF_ONES = ("answered_by", "parent", "direction", "serves")


def backlinks(recs, id_):
    out = defaultdict(list)
    for r in recs.values():
        for f in REF_LISTS:
            if f in r.fm and isinstance(r[f], list) and id_ in r[f]:
                out[f].append(r.id)
        for f in REF_ONES:
            if f in r.fm and r[f] == id_:
                out[f].append(r.id)
    return dict(out)


def links(r):
    out = {}
    for f in REF_LISTS + REF_ONES:
        if f in r.fm and r[f]:
            out[f] = list(r[f]) if isinstance(r[f], list) else [r[f]]
    return out


def cmd_tags(cfg, recs, a, today):
    """Every tag in use with the records carrying it, and the records carrying none; a removed record is in neither."""
    tags, untagged = defaultdict(list), []
    for r in sorted(recs.values(), key=lambda r: r.id):
        if r["state"] == "removed" or (a.type and r.type != a.type):
            continue
        if r["tags"]:
            for t in r["tags"]:
                tags[str(t)].append(r.id)
        else:
            untagged.append(r.id)
    return {t: tags[t] for t in sorted(tags)}, untagged


def cmd_artifacts(cfg, recs, a, today):
    """Every repository path a record refers to, by an evidence item or a body link, with the records naming it and
    whether it is in the tree: the artifacts index, a pure function of the records."""
    paths = defaultdict(list)
    for r in sorted(recs.values(), key=lambda r: r.id):
        if r["state"] == "removed":
            continue
        for e in (r["evidence"] or []) if "evidence" in r.fm else []:
            p = evidence_path(e)
            if p:
                paths[p].append({"id": r.id, "via": "evidence"})
        for p in sorted(set(body_links(r.body))):
            paths[p].append({"id": r.id, "via": "body"})
    return [{"path": p, "exists": (cfg.root / p).exists(), "records": paths[p]} for p in sorted(paths)]


def render_directions(recs):
    """The open directions as the owner's list: the name, the date, the id and the words."""
    opn = sorted((r for r in recs.values() if r.type == "direction" and r["state"] == "open"), key=lambda r: r.id)
    out = ["# Directions", ""]
    for r in opn:
        words = " ".join(r.body.split())
        out.append(f"- **{r['summary']}** ({r['created']}, `{r.id}`)" + (f" — {words}" if words else ""))
    return "\n".join(out + (["none"] if not opn else [])) + "\n"


def refs(recs, ids):
    return [{"id": i, "summary": recs[i]["summary"] if i in recs else None} for i in ids]


def show_text(cfg, recs, r):
    lines = [f"{rel(cfg, r.path)}", render(r.fm, r.body).rstrip("\n"), "", "links:"]
    for f in REF_LISTS + REF_ONES:
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


def passed_dates(cfg, recs, today):
    """The dates that have passed, as lines: a due date on an open task, a block on a condition carrying one."""
    out = []
    for r in sorted(recs.values(), key=lambda r: r.id):
        if r.type == "task" and r["state"] in ("ready", "active") and r["due"] is not None and str(r["due"]) <= today:
            out.append(f"{rel(cfg, cfg.index)}: due {r['due']} has passed: {r.id} — {r['summary']}")
        b = r["blocked"] if r.type in ("question", "task") else None
        if isinstance(b, dict) and r["state"] in ("open", "ready") and b.get("on") not in recs and passed_date(b.get("on"), today):
            out.append(f"{rel(cfg, cfg.index)}: the block's date has passed: {r.id} waits on {b['on']}")
    return out


def state_lines(cfg, skip=0, budget=14000, recs=None, today=None):
    """The inbox, the index's due list, ranked list and hands, the dates that have passed, and the log's top
    entry, every line carrying its FILE:LINE, under a byte budget; returns (lines, next_from)."""
    out = []
    if cfg.inbox.is_file():
        ls = cfg.inbox.read_text(encoding="utf-8").rstrip("\n").split("\n")
        out += [f"{rel(cfg, cfg.inbox)}:{i + 1}: {ls[i]}" for i in range(len(ls))] + [""]
    else:
        out += [f"{rel(cfg, cfg.inbox)}: missing — the person's inbox (`[paths] inbox`)", ""]
    if cfg.index.is_file():
        ls = cfg.index.read_text(encoding="utf-8").split("\n")
        for heading in ("Due", "Next (ranked)", "Hand"):
            sec = _section(ls, heading)
            if sec:
                out += [f"{rel(cfg, cfg.index)}:{i + 1}: {ls[i]}" for i in range(*sec)]
        if recs is not None and today:
            out += passed_dates(cfg, recs, today)
        out.append("")
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


# --- the freeze: what a machine can see of a session's end --------------------------
#
# `flow state --check` decides what it can of a freeze and says what it could not: the
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


def hands(cfg, recs):
    """Each owner's hand as lines for the State paragraph: the active tasks and the ideas drawn."""
    out = []
    for o in cfg.owners:
        for r in sorted(held_by(recs, o), key=lambda r: r.id):
            out.append(f"{o}: {r.id} — {r['summary']} ({r.type}, drawn {r['drawn']})")
    return out


def close_check(cfg, recs, today):
    """What a machine can see of a freeze, as (failures, what was checked, what could not be): the log's top entry
    dated today where the tree changed since the commit of the newest committed entry; every record changed since
    that commit named by an entry from the top down to it.  The hands are printed, never failed: each hand
    continues its own work."""
    fails, checked, undecided = [], [], []

    def fail(path, msg):
        fails.append({"code": "STATE", "id": None, "path": path, "msg": msg})

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
STATE_LABEL = re.compile(r"^\*\*State(?: \([^()\n]*\))?\.\*\*")  # **State.**, or **State (…).** with a parenthesis of the project's
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
    if not STATE_LABEL.match("\n".join(lines[1:]).strip()):
        raise Refused(f"{a.file}: an entry's first paragraph is its State paragraph, the one a cold session trusts, "
                      "labelled `**State.**` or `**State (…).**`")
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
        if t == "direction":  # rendered as the owner's list below
            continue
        live_state = {"idea": "open", "question": "open", "task": "ready", "goal": "open"}.get(t)
        nav.append({"label": t.capitalize() + "s", "path": f"/flow/list?type={t}" + (f"&state={live_state}" if live_state else "")})
    nav.append({"label": "Directions", "path": "/flow/directions"})
    nav.append({"label": "Artifacts", "path": "/flow/artifacts"})
    nav.append({"label": "Tags", "path": "/flow/tags"})
    nav.append({"label": "Check", "path": "/flow/check"})
    columns = ["id", "type", "state"] + (["forms"] if cfg.has("finding") else []) + ["owner", "rank", "summary"]
    params = ["type", "state", "kind", "tag", "owner", "grep"] + (["form"] if cfg.has("finding") else []) + ["from", "refers"]
    flags = ["ranked", "held", "parked", "blocked", "deep"]
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
            {"path": "/flow/artifacts", "view": "lines", "run": ["artifacts"], "field": "lines", "title": "Artifacts"},
            {"path": "/flow/tags", "view": "lines", "run": ["tags"], "field": "lines", "title": "Tags"},
            {"path": "/flow/state", "view": "lines", "run": ["state"], "field": "lines", "title": "State"},
            {"path": "/flow/check", "view": "check", "run": ["check"], "title": "Check"},
        ],
    }


# --- the doctor: the records and bindings an older model wrote ----------------------
#
# No migration logic before v1.0: the doctor names what an older model wrote and what it reads now,
# and the agent edits the files by hand, then runs `flow index` and `flow check`.

def doctor(cfg, today):
    """(path, what is written, what it reads now) for every record and binding in an older model's words."""
    out = []
    raw, task, fnd, ev = cfg.raw, cfg.raw.get("task", {}), cfg.raw.get("finding", {}), cfg.raw.get("evidence", {})
    for k in ("decision_kinds", "decision_owners"):
        if k in task:
            out.append(("flow.toml", f"[task] {k}", "goes: a decision is no card and no owner's work; delete the line"))
    if "question_optional_kinds" in task:
        out.append(("flow.toml", "[task] question_optional_kinds", "goes: any task may stand alone; delete the line"))
    for k in ("kinds", "default_kind"):
        if k in task:
            out.append(("flow.toml", f"[task] {k}", "goes: a task's kind is a tag now, written with --tag; delete the line, and the section once empty"))
    if fnd:
        out.append(("flow.toml", "[finding]", "goes: a finding's status is read from the forms of its evidence, which [evidence] forms lists; delete the section"))
    if "forms" not in ev:
        out.append(("flow.toml", "no [evidence] forms", f"forms = [{', '.join(json.dumps(f) for f in SHIPPED_FORMS)}]: "
                    "the forms the project accepts, of the five the kit ships and its own"))
    if len(cfg.hand) > 2:
        out.append(("flow.toml", f"[hand] names {len(cfg.hand)} owners ({', '.join(cfg.hand)})",
                    "two hands, the agent's and the person's: a prover's task stays in the agent's hand, marked out "
                    "(`flow out T --to prover`), so its owner goes and its limit folds into the agent's (4 by default)"))
    legacy = list(fnd.get("statuses", ()))
    refuted = str(fnd.get("refuted", legacy[3] if len(legacy) > 3 else "refuted"))
    if "directions" in raw.get("paths", {}) or cfg.directions_file.is_file():
        dfile = cfg.directions_file.is_file()
        dpath = rel(cfg, cfg.directions_file)
        out.append((dpath if dfile else "flow.toml", "the directions file" if dfile else "[paths] directions",
                    "directions are records now: `flow direction NAME --body FILE` for each bullet, its words in FILE; a question's "
                    "`direction` becomes the record's id; then delete the file and the binding"))
        if dfile:
            ls = cfg.directions_file.read_text(encoding="utf-8").split("\n")
            sec = _section(ls, "Inbox")
            if sec:
                out.append((f"{dpath}:{sec[0] + 1}", "an `## Inbox` section",
                            f"the inbox is a file of its own: move its items to {rel(cfg, cfg.inbox)} and delete the section"))
            text = re.sub(r"<!--.*?-->", "", "\n".join(ls), flags=re.S)
            for name in re.findall(r"^- \*\*(.+?)\*\*", text, re.M):
                out.append((dpath, f"- **{name}**", f"`flow direction {json.dumps(name)} --body FILE`, the bullet's words in FILE"))
    if not cfg.inbox.is_file():
        out.append((rel(cfg, cfg.inbox), "absent", "the person's inbox: create it, a `# Inbox` title and nothing else"))
    recs = load_all(cfg, broken := [])
    for b in broken:
        out.append((b["path"], "a record that does not read", b["msg"]))
    for r in sorted(recs.values(), key=lambda r: r.id or ""):
        t, path = r.type, rel(cfg, r.path)
        if t not in SCHEMA:
            continue
        st = r["state"]
        if "kill" in r.fm:
            out.append((path, "kill", "criterion: rename the field, its text unchanged"))
        if "abandoned" in r.fm:
            out.append((path, "abandoned", "closed: rename the field, its date and reason unchanged"
                        + ("" if st == "abandoned" else "; null where the record is not closed")))
        if st == "abandoned":
            word = "aborted" if t == "task" and r["drawn"] else "removed"
            out.append((path, "state: abandoned", f"state: {word}" + (" (it was drawn, then given up)" if word == "aborted" else
                                                                       " (dropped while ready)" if t == "task" else "")))
        if st == "decomposed":
            out.append((path, "state: decomposed", "state: open (that it was refined is read from its tasks)"))
        if t == "task" and r["kind"] == "decision" and st in ("ready", "active"):
            out.append((path, "kind: decision", "a task waiting on a decision is parked with a reason naming it "
                        "(`flow park T --reason …`, returned first if active); or removed"))
        by = r["answered_by"] if t == "question" and isinstance(r["answered_by"], list) else []
        tasks = [x for x in by if x in recs and recs[x].type == "task"]
        if tasks:
            out.append((path, f"answered_by: {', '.join(tasks)}", "a finding settles a question: mint it with "
                        f"`flow finding SUMMARY STATUS EVIDENCE… --from {tasks[0]}` and write its id in answered_by in place of "
                        "the task; or, where no finding is to be had, read the question as removed (state, closed with the reason)"))
        finds = [x for x in by if x in recs and recs[x].type == "finding"]
        if len(finds) > 1:
            out.append((path, f"answered_by: {', '.join(finds)}", "one finding answers a question: keep the one that settles "
                        "it, as one value; each other names the question in its derived_from"))
        elif t == "question" and isinstance(r["answered_by"], list) and not tasks:
            out.append((path, "answered_by as a list", f"answered_by: {finds[0] if finds else 'null'} (one value, not a list)"))
        if t == "idea" and r["consumed_by"] and not isinstance(r["consumed_by"], list):
            out.append((path, f"consumed_by: {r['consumed_by']}", f"consumed_by as a list, `- {r['consumed_by']}` (every card it was folded into)"))
        for k in DROPPED_FIELDS.get(t, ()):
            if k not in r.fm:
                continue
            if k == "question":
                q = r[k]
                answers = q in recs and r.id in (recs[q]["answered_by"] if isinstance(recs[q]["answered_by"], list) else [recs[q]["answered_by"]])
                out.append((path, f"{k}: {q or 'null'}", "goes: a task or a finding no longer belongs to a question; delete the field"
                            + (f", and name {q} in derived_from, where it is not yet" if q and not answers and not came_from(r, q) else "")))
            elif k == "kind":
                out.append((path, f"kind: {r[k]}", f"goes: a kind is a tag now; add {json.dumps(str(r[k]))} to tags where it says something, and delete the field"))
            elif k == "status":
                out.append((path, f"status: {r[k]}", "goes: the forms of the evidence stand for it; delete the field"
                            + (", and add the tag `refuted`" if str(r[k]) == refuted else "")))
            elif k == "paper":
                out.append((path, f"paper: {r[k]}", "goes: delete the field; the document is a reference `flow find --refers PATH` groups by"))
        if t == "finding":
            for e in r["evidence"] or []:
                e = str(e)
                if split_evidence(e) is None:
                    prefix = ("formal" if cfg.ev_decl.match(e) or cfg.ev_declfile.match(e) else "statistical" if EV_PROBE.match(e)
                              else "stated" if EV_ROW.match(e) or EV_STMT.match(e) else None)
                    out.append((path, f"evidence {e}", f"{prefix}:{e} (its form as a prefix)" if prefix else "form:TARGET, the form one of [evidence] forms"))
            if r.path.parent.resolve() != cfg.dir_of("finding").resolve():
                out.append((path, f"under {rel(cfg, r.path.parent)}/", f"move to {rel(cfg, cfg.dir_of('finding'))}/: findings no longer shard by document"))
        if t == "question" and r["direction"] and r["direction"] not in recs and not cfg.id_re.match(f"{r['direction']}.md"):
            out.append((path, f"direction: {r['direction']}", "the id of the direction record minted from that bullet (`direction-0001`)"))
        owner = r["owner"] if t in ("task", "idea") else None
        held = (t == "task" and st == "active") or (t == "idea" and st == "open")
        if t == "task" and st == "ready" and (owner or r["drawn"]):
            out.append((path, f"owner: {owner or 'null'}, drawn: {r['drawn'] or 'null'} on a ready task", "owner: null and drawn: null (a ready task "
                        "is in no hand; a decision owner's task was minted into that hand)"))
        elif owner and owner not in cfg.owners:
            out.append((path, f"owner: {owner}", f"an owner [hand] does not list ({', '.join(cfg.owners)}): "
                        + (f"`flow return {r.id}`, then draw it into a listed hand where it is still worked" if held
                           else "owner: null (a closed record is in no hand)")))
        renamed = {OLD_FIELDS.get(k, k) for k in r.fm}  # a dropped field is named above, a missing one below
        for k in SCHEMA[t]:
            if k not in renamed:
                out.append((path, f"no {k}", f"{k}: {'[]' if k in LIST_FIELDS else 'null'} (a field of this model)"))
    return out


# --- init --------------------------------------------------------------------------

INIT_TOML = """# flow.toml — the flow's bindings for THIS project.  Every path is relative to this file's
# directory.  The `flow` skill reads it; the project's own instructions name the log, the
# gates and the rest.

[paths]
records = "{dir}"                 # one file per record: ideas/ tasks/ questions/ findings/ goals/ directions/ archive/
index = "{dir}/INDEX.md"          # generated by `flow index`; `flow check` fails on drift
archive = "{dir}/archive"         # closed tasks move here at their closing transition
inbox = "INBOX.md"                 # the person's inbox: dropped between sessions, read at the next one's start
{log}# reflow_module = "scripts/reflow.py"   # exports reflow_text(text): one sentence per line; built-in otherwise
# markdownlint_config = ".markdownlint.jsonc"  # a NEW violation after a write reverts it

[prefixes]
idea = "idea"
question = "question"
task = "task"
finding = "finding"
goal = "goal"
direction = "direction"
id_width = 4

[hand]
# The records an owner's hand may hold at once, active tasks and ideas drawn, 0 = unlimited: two hands,
# the agent's (across sessions; a subagent works on it) and the person's.
{owners}

{research}[index]
recent_findings = 10
oldest_ideas = 5
"""

INIT_RESEARCH = """[question]
sizes = ["small", "medium", "large"]

[evidence]
# The forms a finding's evidence takes, each item `form:target`, the finding's trust the forms it carries.
# The kit ships five: formal (a declaration of the manifest, machine-checked), statistical (a probe of the
# register, or a committed result by its path), peer-reviewed (a card of the library), stated (a statement
# or row of a document of the project: its own word, the trust to raise) and reference (any other source, a
# link).  Keep the ones the project accepts and add its own words; the instructions say what each means here.
forms = ["formal", "statistical", "peer-reviewed", "stated", "reference"]
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
- `INBOX.md` is where the person leaves items between sessions; a session reads it at its start.
- `flow state` prints the cold-start bundle: the inbox, the ranked list, the hands and the log's top entry.
- A session starts with the `whatsnext` skill (the inbox read, the list ranked, the top work drawn)
  and ends with the `freeze` skill (what the conversation holds saved, `flow state --check`, a commit).
The `flow`, `whatsnext` and `freeze` skills are installed for the project's agent as well (the `research`
plugin, or `npx skills add`).
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
    text = INIT_TOML.format(
        dir=a.records,
        log=(f'log = "{a.log}"                 # the dated log whose top entry `flow state` prints\n'
             f'log_archive = "{Path(a.log).with_name(Path(a.log).stem + "-archive").as_posix()}"   '
             '# `flow log archive` moves the old entries here verbatim, one file per month\n') if a.log else
            '# log = "WORKLOG.md"             # the dated log whose top entry `flow state` prints\n'
            '# log_archive = "WORKLOG-archive"   # `flow log archive` moves the old entries here verbatim, one file per month\n',
        owners="\n".join(f"{o} = {0 if o == owners[-1] and len(owners) > 1 else 4}" for o in owners),
        research=INIT_RESEARCH)
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
    if not cfg.inbox.is_file():
        cfg.inbox.parent.mkdir(parents=True, exist_ok=True)
        cfg.inbox.write_text("# Inbox\n\n<!-- what the person leaves between sessions, one item per line; "
                             "the next session's `whatsnext` skill reads it and proposes what to make of each -->\n", encoding="utf-8")
        written.append(rel(cfg, cfg.inbox))
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
[evidence]
forms = ["formal", "statistical", "peer-reviewed", "stated", "reference", "benchmark"]
manifest = "decls.txt"
manifest_roots = "lean"
manifest_extension = "lean"
probes = "probes/README.md"
[prefixes]
idea = "idea"
question = "question"
task = "task"
finding = "finding"
goal = "goal"
direction = "direction"
id_width = 4
[hand]
root = 2
author = 0
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
        (root / "results").mkdir()
        (root / "results" / "bench.md").write_text("# Bench\n\n| ID | rate |\n|---|---|\n| BR-1 | 0.9 |\n")
        (root / "research").mkdir()
        cfg = Config(root)
        today = "2026-09-25"

        def run(argv, ok=True):
            rc, payload = dispatch(cfg, argv, today=today, as_json=True, quiet=True)
            expect(" ".join(argv[:2]) + (" refused" if not ok else ""), (rc == 0) == ok)
            if (rc == 0) != ok:
                for pr in payload["problems"]:
                    print("      ", pr["code"], pr.get("path") or pr.get("id"), pr["msg"])
            return payload

        new = lambda argv: run(argv)["created"][0]
        ids = lambda argv: [r["id"] for r in run(argv)["records"]]
        (root / "bridge.md").write_text("The bridge between A and B.\n")
        d = new(["direction", "Bridge", "--body", str(root / "bridge.md")])
        expect("a direction is a record, open, the owner's words its body",
               load_all(cfg)[d]["state"] == "open" and load_all(cfg)[d].body == "The bridge between A and B.\n")
        idea = new(["capture", "an idea", "--source", "test"])
        q = new(["frame", idea, "--summary", "Does A imply B?", "--criterion", "a finite counterexample", "--direction", d])
        run(["rank", q, "1", "--why", "w", "--first-move", "m", "--direction", "direction-0099"], ok=False)  # no such direction
        p = run(["refine", q, "--task", "prove L", "--task", "design the route", "--subq", "sub question", "its criterion", "--tag", "research"])
        t1, t2, sq = p["created"]
        expect("refine leaves the question open, refined being read from its tasks, and tags the tasks it mints",
               load_all(cfg)[q]["state"] == "open" and p["changed"] == [] and load_all(cfg)[t1]["tags"] == ["research"] and "kind" not in load_all(cfg)[t1].fm)
        run(["rank", t1, "1", "--why", "w", "--first-move", "m", "--direction", d], ok=False)  # a direction is a question's
        run(["draw", t1, "--owner", "root"])
        run(["draw", t2, "--owner", "root"])
        t3 = new(["refine", sq, "--task", "third"])
        run(["draw", t3, "--owner", "root"], ok=False)  # hand full
        run(["return", t2, "--note", "later"])
        tree = lambda: {x: x.read_text(encoding="utf-8") for x in sorted((root / "research").rglob("*.md"))}
        before = tree()
        run(["make", t1, "--task", "after", "--idea", "aside", "--resolution", "missing.md"], ok=False)
        expect("a make refused after its follow-ups are minted leaves the tree as it was", tree() == before)
        run(["finding", "L holds", "formal:Lib/Foo.lean#lemma_L", "--from", t1], ok=False)  # active: make first, then mint
        p = run(["make", t1])
        expect("a made task is archived, its owner cleared and its drawn date kept",
               "research/archive/" in p["records"][-1]["path"] and load_all(cfg)[t1]["owner"] is None and load_all(cfg)[t1]["drawn"] == today)
        run(["make", t1], ok=False)  # done already
        run(["finding", "L holds", "formal:Lib/Foo.lean#lemma_L", "--from", t1, "--answers", q], ok=False)  # t2 is open on q
        p = run(["finding", "L holds", "formal:Lib/Foo.lean#lemma_L", "stated:papers/alpha.md#FV-1", "--from", t1])
        f = p["created"][0]
        expect("a finding minted from a done task lives under findings/, names the task it came from, and its trust is the forms it carries",
               "research/findings/" in p["records"][0]["path"] and load_all(cfg)[f]["derived_from"] == [t1]
               and not {"question", "status", "paper"} & set(load_all(cfg)[f].fm) and p["records"][0]["forms"] == "formal, stated")
        run(["draw", t2, "--owner", "root"])
        (root / "wall.md").write_text("The route hits a wall.\n")
        p = run(["abort", t2, "--reason", "wall", "--resolution", str(root / "wall.md")])
        body = Path(root / p["records"][-1]["path"]).read_text(encoding="utf-8")
        expect("a resolution is appended under its date, and the task's notes stay",
               "returned: later" in body and body.rstrip().endswith(f"{today} — resolution:\n\nThe route hits a wall."))
        recs = load_all(cfg)
        expect("an aborted task carries its state and its dated reason in closed",
               recs[t2]["state"] == "aborted" and recs[t2]["closed"] == {"date": today, "reason": "wall"})
        fr = new(["finding", "the route fails", "statistical:probes/p.py", "--from", t2, "--tag", "refuted"])
        for had in ("", "A note.\n"):  # a resolution opening with a heading, on an empty body and after a note
            r = type("R", (), {"body": had})()
            append_note(r, today, "resolution:", "\n## Result\n\nIt is done.\n\n")
            expect("a resolution file's text is set apart from its dated line by one blank line" + (", after a note" if had else ", on an empty body"),
                   render({"id": "task-0001"}, r.body).endswith(f"---\n\n{had and had + chr(10)}{today} — resolution:\n\n## Result\n\nIt is done.\n"))
        p = run(["finding", "B follows from L", "stated:papers/alpha.md#Theorem 2.1", "--from", t1, "--answers", q])
        fa = p["created"][0]
        recs = load_all(cfg)
        expect("a finding minted --answers Q closes Q answered by it alone", recs[q]["state"] == "answered" and recs[q]["answered_by"] == fa
               and p["changed"] == [q])
        run(["finding", "a second answer", "stated:papers/alpha.md#Theorem 2.1", "--answers", q], ok=False)  # one finding answers
        p = run(["finding", "a corollary", "stated:papers/alpha.md#Theorem 2.1", "--from", q])
        fc = p["created"][0]
        expect("a finding the answering produced names the question it came from", load_all(cfg)[fc]["derived_from"] == [q])
        # evidence is added and never removed: the trust raised, a proof formalized
        run(["evidence", fa, "stated:papers/alpha.md#Theorem 2.1"], ok=False)  # there already
        run(["evidence", fa, "formal:Lib/Foo.lean#nope"], ok=False)
        p = run(["evidence", fa, "formal:Lib/Foo.lean#lemma_L"])
        expect("evidence appends an item it resolves, and the finding's forms grow with it",
               load_all(cfg)[fa]["evidence"] == ["stated:papers/alpha.md#Theorem 2.1", "formal:Lib/Foo.lean#lemma_L"] and p["records"][0]["forms"] == "formal, stated")
        expect("find --form lists the findings carrying a form",
               fa in ids(["find", "--form", "formal"]) and fc in ids(["find", "--form", "stated"]) and f not in ids(["find", "--form", "statistical"]))
        run(["remove", t3, "--reason", "not needed"])
        i2 = new(["capture", "a second idea"])
        run(["frame", i2, "--summary", "Q2", "--criterion", "k", "--direction", "Nowhere"], ok=False)
        q3 = new(["frame", i2, "--summary", "Q2", "--criterion", "k"])
        run(["rank", q3, "1", "--why", "now", "--first-move", "none yet"])
        run(["set", q3, "criterion", "a sharper criterion"])
        run(["set", q3, "kill", "a criterion's old name"], ok=False)
        run(["set", q3, "rider", "on"], ok=False)  # a question carries no rider
        run(["set", q3, "size", "huge"], ok=False)  # not a size
        run(["set", q3, "state", "answered"], ok=False)  # a transition's field
        run(["set", q3, "serves", "goal-0099"], ok=False)  # no such goal
        q4 = new(["frame", new(["capture", "an idea to park"]), "--summary", "Q to park", "--criterion", "k"])
        run(["rank", q4, "2", "--why", "x", "--first-move", "y"])
        run(["park", q4, "--reason", "waiting"])
        run(["park", q4, "--reason", "again"], ok=False)  # parked already
        run(["block", q4, "--on", q3, "--reason", "needs its answer"])
        run(["block", q4, "--on", "the release", "--reason", "again"], ok=False)  # blocked already
        run(["block", q3, "--on", f, "--reason", "r"], ok=False)  # a finding is waited on by nothing
        run(["block", q3, "--on", q3, "--reason", "r"], ok=False)  # itself
        run(["refine", q4, "--task", "t"], ok=False)  # parked
        recs = load_all(cfg)
        expect("a parked and blocked question keeps its rank and both waits", recs[q4]["rank"] == 2
               and recs[q4]["parked"]["reason"] == "waiting" and recs[q4]["blocked"] == {"date": today, "on": q3, "reason": "needs its answer"})
        run(["index"])
        idx = cfg.index.read_text(encoding="utf-8")
        expect("the index marks the waits on the ranked list and lists the waiting question apart",
               f"   waits: parked {today} — waiting" in idx and f"   waits: blocked on {q3} {today} — needs its answer" in idx
               and "## Parked or blocked questions" in idx)
        p = run(["check"])
        expect("check green on the happy path", not p["problems"])
        q5 = new(["frame", new(["capture", "idea four"]), "--summary", "Q4", "--criterion", "k"])
        t4 = new(["refine", q5, "--task", "t"])
        run(["draw", t4, "--owner", "root"])
        run(["make", t4])
        run(["finding", "bad", "formal:Lib/Foo.lean#nope", "--from", t4], ok=False)
        run(["finding", "bad", "formal:Lib/Bar.lean#lemma_L", "--from", t4], ok=False)  # declared in Lib.Foo
        run(["finding", "bad", "stated:Lib/Foo.lean#lemma_L", "--from", t4], ok=False)  # stated takes a document
        run(["finding", "bad", "formal:papers/alpha.md#Theorem 2.1", "--from", t4], ok=False)  # formal takes a declaration
        run(["finding", "bad", "nonsense:papers/alpha.md#Theorem 2.1", "--from", t4], ok=False)  # not a form the project lists
        run(["finding", "bad", "papers/alpha.md#Theorem 2.1", "--from", t4], ok=False)  # no form
        run(["finding", "bad", "statistical:results/nope.md", "--from", t4], ok=False)  # no such result
        run(["finding", "bad", "statistical:results/bench.md#BR-9", "--from", t4], ok=False)  # no such row
        run(["finding", "bad", "stated:papers/alpha.md#Theorem 2.1", "stated:papers/alpha.md#Theorem 2.1", "--from", t4], ok=False)  # twice
        run(["finding", "bad", "benchmark:results/none.csv", "--from", t4], ok=False)  # a form of the project's, its path gone
        p = run(["finding", "fine", "stated:papers/alpha.md#Theorem 2.1", "statistical:results/bench.md#BR-1", "benchmark:results/bench.md",
                 "benchmark:the run of 2026-09", "reference:https://example.org/x", "--from", t4, "--answers", q5])
        fb = p["created"][0]
        expect("a finding carries a result's row, a form of the project's and a link, its forms the words it carries",
               p["records"][0]["forms"] == "benchmark, reference, stated, statistical")
        run(["index"])
        p = run(["check"])
        expect("a form of the project's with no path is reported unchecked, never failed",
               not p["problems"] and any(f"{fb}: benchmark:the run of 2026-09: unchecked" in w for w in p["warnings"]))
        rt = new(["task", "an upkeep chore", "--tag", "upkeep", "--due", "2026-10-01", "--after", "mint the same chore for the next month"])
        run(["task", "a chore due soon", "--due", "soon"], ok=False)
        run(["set", rt, "rider", "on"])
        run(["set", rt, "criterion", "k"], ok=False)  # a task carries no criterion
        run(["set", t4, "rider", "on"], ok=False)  # a done task rides nothing
        run(["set", rt, "due", "never"], ok=False)
        run(["set", rt, "due", "2026-10-02"])
        run(["set", rt, "after", ""], ok=False)
        recs = load_all(cfg)
        expect("set wrote the rider, the criterion and the due date",
               recs[rt]["rider"] is True and recs[q3]["criterion"] == "a sharper criterion" and recs[rt]["due"] == "2026-10-02")
        run(["set", rt, "rider", "off"])
        fs = sorted(r.id for r in load_all(cfg).values() if r.type == "finding")
        run(["set", fs[1], "depends_on", fs[0]])
        run(["set", fs[0], "depends_on", fs[1]], ok=False)  # would close a cycle
        run(["set", fs[0], "depends_on", fs[0]], ok=False)  # itself
        run(["set", fs[0], "depends_on", q3], ok=False)  # not a finding
        run(["set", fs[1], "depends_on", "none"])
        lt = new(["task", "a task with no question"])  # any task may stand alone
        run(["task", "a task from an answered question", "--from", q], ok=False)
        run(["remove", lt, "--reason", "it stood alone to test it"])
        # a ready task waits too: parked and blocked at once, and drawn only once both are cleared
        run(["park", rt, "--reason", "after the release"])
        run(["block", rt, "--on", "the next release", "--reason", "it needs the tag"])
        run(["draw", rt, "--owner", "root"], ok=False)
        run(["unpark", rt, "--note", "the release is out"])
        run(["draw", rt, "--owner", "root"], ok=False)  # still blocked
        run(["unblock", rt])
        run(["draw", rt, "--owner", "root"])
        run(["park", rt, "--reason", "r"], ok=False)  # active: returned first
        run(["return", rt])
        # a task that came from a question holds its closing back; none is re-bound, since none belongs to it
        run(["set", rt, "question", q3], ok=False)
        tq = new(["task", "a task from q3", "--from", q3])
        run(["remove", q3, "--reason", "r"], ok=False)  # a ready task came from it
        expect("find --from lists the records that came from a record", ids(["find", "--from", q3]) == [tq])
        shallow, deep = set(ids(["find", "--refers", q])), set(ids(["find", "--refers", q, "--deep"]))
        expect("find --refers lists who names a record in any reference field, the idea consumed into it included, and --deep who names those",
               shallow == {idea, t1, t2, sq, fc} and {f, fa, fr} <= deep and f not in shallow)
        expect("find --refers PATH lists the records whose evidence names a repository path", {f, fa, fc, fb} <= set(ids(["find", "--refers", "papers/alpha.md"])))
        run(["find", "--deep"], ok=False)  # --deep follows --refers
        run(["remove", tq, "--reason", "no longer needed"])
        # an idea drawn like a task, worked into other cards, consumed into one of them
        wi = new(["capture", "an idea to work"])
        run(["draw", wi, "--owner", "root"])
        run(["draw", wi, "--owner", "root"], ok=False)  # in hand already
        run(["consume", wi], ok=False)  # nothing came from it yet
        sub = new(["capture", "a narrower idea", "--from", wi])
        p = run(["return", wi, "--note", "half worked"])
        expect("an idea put back partly worked lists what it produced so far",
               load_all(cfg)[wi].body.rstrip().endswith(f"returned: half worked; produced so far: {sub}"))
        run(["draw", wi, "--owner", "root"])
        wt = new(["task", "a chore it shows", "--tag", "upkeep", "--from", wi])
        run(["consume", wi])
        recs = load_all(cfg)
        expect("an idea consumed is folded into every card that came from it, and leaves the hand",
               recs[wi]["state"] == "consumed" and recs[wi]["consumed_by"] == sorted([sub, wt]) and recs[wi]["owner"] is None)
        run(["draw", wi, "--owner", "root"], ok=False)  # consumed
        run(["capture", "from a removed one", "--from", sub])  # sub is open still
        run(["remove", sub, "--reason", "folded into the chore"])
        run(["capture", "from a removed one", "--from", sub], ok=False)
        run(["remove", sub, "--reason", "again"], ok=False)
        expect("find leaves a removed record out unless asked by its state or its id",
               sub not in ids(["find", "--type", "idea"]) and sub in ids(["find", "--state", "removed"]) and ids(["find", "--id", sub]) == [sub])
        # wrong and impossible, each a settled closing listed as such
        qw = new(["frame", new(["capture", "a badly put idea"]), "--summary", "Is the empty sum odd?", "--criterion", "its parity"])
        run(["wrong", qw, "--reason", "parity is not defined for it"])
        qi = new(["frame", new(["capture", "an idea past reach"]), "--summary", "Does it halt?", "--criterion", "a proof either way"])
        run(["impossible", qi, "--by", q], ok=False)  # not a finding
        run(["impossible", qi, "--by", fs[0]])
        run(["index"])
        idx = cfg.index.read_text(encoding="utf-8")
        expect("wrong and impossible are listed as settled, a removed record nowhere",
               f"`{qw}` — Is the empty sum odd? [wrong]" in idx and f"`{qi}` — Does it halt? [impossible]" in idx and sub not in idx)
        heap = new(["capture", "an idea for the heap"])
        # the reference library, asked through its `keys` answer (a stub stands for it here)
        stub = root / "lib_stub.py"
        stub.write_text('import json\nprint(json.dumps({"ok": True, "cite_prefix": "lib:", "cards": '
                        '{"jen1990": {"state": "registered", "grade": "parts", "extracts": ["lemma"]}, '
                        '"aside": {"state": "excluded", "grade": "unread"}}, "problems": []}))\n')
        cfg.library_cmd = [sys.executable, str(stub)]
        run(["capture", "an idea citing lib:jen1990 twice over, lib:jen1990, and lib:aside"])
        run(["finding", "bad", "peer-reviewed:nobody2000", "--from", t4], ok=False)  # the library holds no such card
        run(["finding", "bad", "peer-reviewed:jen1990#theorem9", "--from", t4], ok=False)  # no such extract
        run(["finding", "bad", "peer-reviewed:Jen 1990", "--from", t4], ok=False)  # a key, not words
        fp = new(["finding", "as Jen shows", "peer-reviewed:jen1990#lemma", "--from", t4])
        run(["index"])
        p = run(["check"])
        expect("check green with a cited key the library holds and a peer-reviewed item it holds", not p["problems"])
        expect("the coverage counts the cited keys by grade and the excluded ones",
               p["coverage"]["library"] == {"cited": 2, "records": 1, "grades": {"parts": 1, "unread": 1}, "excluded": 1})

        # goals: formed by the owner, served by questions, reached or given up
        g = new(["goal", "Reach B", "--criterion", "B is proved", "--horizon", "before the talk", "--from", d])
        recs = load_all(cfg)
        expect("a goal names the direction it was produced along, which stays open", recs[g]["derived_from"] == [d] and recs[d]["state"] == "open")
        qg = new(["frame", new(["capture", "an idea for the goal"]), "--summary", "Qg", "--criterion", "k", "--serves", g])
        run(["frame", new(["capture", "an idea for no goal"]), "--summary", "Qx", "--criterion", "k", "--serves", "goal-0099"], ok=False)
        run(["rank", qg, "3", "--why", "w", "--first-move", "m", "--serves", g])
        run(["rank", rt, "4", "--why", "w", "--first-move", "m", "--serves", g], ok=False)  # a goal is a question's
        run(["set", q4, "serves", g])
        run(["index"])
        idx = cfg.index.read_text(encoding="utf-8")
        expect("the index lists the due task first, the goal with what reached means, its horizon and the questions serving it, "
               "the direction with its date, and what a ranked question serves",
               idx.index("## Due") < idx.index("## Next (ranked)") and f"`{rt}` — an upkeep chore [due 2026-10-02]" in idx
               and "## Goals" in idx and f"`{g}` — Reach B [reached: B is proved; horizon: before the talk]" in idx and f"  - `{qg}` — Qg" in idx
               and "## Directions" in idx and f"`{d}` — Bridge [{today}]" in idx and f"   serves: {g}" in idx)
        expect("flow directions renders the open directions as the owner's list",
               f"- **Bridge** ({today}, `{d}`) — The bridge between A and B." in run(["directions"])["text"])
        p = run(["giveup", g, "--reason", "B is out of reach this year"])
        recs = load_all(cfg)
        expect("a goal given up releases its open questions, which keep their ranks, and names them",
               recs[g]["state"] == "given_up" and recs[g]["closed"] == {"date": today, "reason": "B is out of reach this year"}
               and recs[qg]["serves"] is None and recs[q4]["serves"] is None and recs[qg]["rank"] == 3 and sorted(p["released"]) == sorted([q4, qg]))
        run(["reach", g, "--reason", "r"], ok=False)  # given up already
        run(["set", qg, "serves", g], ok=False)  # not open
        g2 = new(["goal", "Reach C", "--criterion", "C is proved"])
        run(["set", qg, "serves", g2])
        run(["reach", g2, "--reason", f"C is proved, {fa}"])
        recs = load_all(cfg)
        expect("a goal reached carries its date and what shows it", recs[g2]["state"] == "reached" and recs[g2]["closed"]["reason"] == f"C is proved, {fa}")
        run(["set", qg, "serves", "none"])
        # a direction dropped by the owner releases its open questions; a closed question keeps its as history
        qd = new(["frame", new(["capture", "an idea for the bridge"]), "--summary", "Qd", "--criterion", "k", "--direction", d])
        p = run(["drop", d, "--reason", "the bridge is crossed"])
        recs = load_all(cfg)
        expect("a direction dropped releases its open questions and keeps a closed question's as history",
               recs[d]["state"] == "closed" and recs[qd]["direction"] is None and recs[q]["direction"] == d and p["released"] == [qd])
        run(["frame", new(["capture", "an idea for a closed direction"]), "--summary", "Qz", "--criterion", "k", "--direction", d], ok=False)
        d2 = new(["direction", "Second"])
        text = run(["directions"])["text"]
        expect("flow directions lists the open directions alone", d not in text and d2 in text)
        run(["goal", "along a closed direction", "--criterion", "k", "--from", d], ok=False)
        # the tag report and the artifacts index
        p = run(["tags"])
        expect("tags lists each tag with its records, then the untagged, a removed record in neither",
               p["tags"]["research"] == [t1, t2] and p["tags"]["refuted"] == [fr] and q in p["untagged"] and sub not in p["untagged"]
               and q not in run(["tags", "--type", "task"])["untagged"])
        (root / "linked.md").write_text("See [the paper](<./papers//alpha.md#Theorem 2.1>) and [the probe](probes/p.py), "
                                        "not <https://example.org/x> nor `papers/prose.md`.\n")
        li = new(["capture", "a linked idea", "--body", str(root / "linked.md")])
        p = run(["artifacts"])
        by = {x["path"]: x for x in p["artifacts"]}
        expect("artifacts lists every path the records refer to, with who names it and how, a `./` and a doubled slash folded; "
               "a URL, a backticked path and a declaration are not paths",
               by["papers/alpha.md"]["exists"] and {"id": li, "via": "body"} in by["papers/alpha.md"]["records"]
               and {"id": f, "via": "evidence"} in by["papers/alpha.md"]["records"] and by["probes/p.py"]["exists"] and "results/bench.md" in by
               and "Lib/Foo.lean" not in by and not any("example.org" in k or "prose" in k or k.startswith(".") for k in by))
        expect("find --refers PATH lists the records naming a path in a body link too, the path given in any spelling",
               li in ids(["find", "--refers", "papers/alpha.md"]) and li in ids(["find", "--refers", "./papers/alpha.md"]))

        # a closing transition closes the ranks up and reports the moves as re-ranks (q3 holds rank 1, q4 rank 2)
        run(["rank", qg, "--clear"])
        q6 = new(["frame", new(["capture", "an idea to rank and close"]), "--summary", "Q to close", "--criterion", "k"])
        run(["rank", q6, "3", "--why", "w", "--first-move", "m"])
        run(["rank", q3, "--clear"])
        expect("clearing a rank closes the ranks up", [load_all(cfg)[i]["rank"] for i in (q4, q6)] == [1, 2])
        run(["rank", q3, "3", "--why", "now", "--first-move", "none yet"])
        p = run(["remove", q6, "--reason", "closed to test the ranks"])
        expect("removing a ranked question renumbers the rest and reports them as re-ranked, not changed",
               p["changed"] == [q6] and p["reranked"] == [{"id": q3, "from": 3, "to": 2}]
               and load_all(cfg)[q3]["rank"] == 2 and not validate(cfg, load_all(cfg), today)[0])
        p = run(["rank", qw, "1", "--why", "w", "--first-move", "m"], ok=False)  # wrong is closed
        p = run(["rank", q5, "1", "--why", "w", "--first-move", "m"], ok=False)  # answered
        q7 = new(["frame", new(["capture", "a late idea"]), "--summary", "Q late", "--criterion", "k"])
        p = run(["rank", q7, "1", "--why", "w", "--first-move", "m"], ok=False)  # rank 1 is held
        expect("a rank refused as held names --insert and --set", "--insert" in p["problems"][0]["msg"] and "rank --set" in p["problems"][0]["msg"])
        p = run(["rank", q7, "1", "--insert", "--why", "w", "--first-move", "m"])
        expect("rank --insert puts a new record at N in one step and moves the rest down, reporting them as re-ranked",
               [load_all(cfg)[i]["rank"] for i in (q7, q4, q3)] == [1, 2, 3] and {x["id"] for x in p["reranked"]} == {q4, q3})
        run(["rank", q3, "1", "--insert"])
        expect("rank --insert moves a ranked record up, the rest closing round it",
               [load_all(cfg)[i]["rank"] for i in (q3, q7, q4)] == [1, 2, 3] and not validate(cfg, load_all(cfg), today)[0])
        run(["rank", q7, "4", "--insert"], ok=False)  # past the end of the ranks
        run(["rank", q7, "--clear", "--insert"], ok=False)  # --insert takes a rank
        run(["rank", q7, "--clear"])
        run(["rank", idea, "1", "--why", "w", "--first-move", "m"], ok=False)  # an idea is never ranked
        run(["rank", idea, "--clear"], ok=False)
        # refine adds to a refined question; a closing refuses open tasks
        q8 = new(["frame", new(["capture", "an idea to refine twice"]), "--summary", "Q refined twice", "--criterion", "k"])
        run(["refine", q8, "--task", "first"])
        p = run(["refine", q8, "--task", "second"])
        expect("refine adds a task to a refined question", p["created"] and load_all(cfg)[q8]["state"] == "open")
        for verb in (["remove", q8, "--reason", "x"], ["wrong", q8, "--reason", "x"], ["impossible", q8, "--by", fs[0]]):
            run(verb, ok=False)  # two ready tasks under it
        (root / "refined.md").write_text("Split by the size of the case.\n")
        p = run(["refine", q8, "--task", "third", "--body", str(root / "refined.md")])
        recs = load_all(cfg)
        expect("refine's body is appended to the question under its date, the answer names it, and the task minted carries none",
               recs[q8].body.rstrip().endswith(f"{today} — refined:\n\nSplit by the size of the case.")
               and p["body_appended_to"] == q8 and recs[p["created"][0]].body == "")
        run(["find", "--grep", "["], ok=False)
        run(["index"])
        p = run(["check"])
        expect("check green after the rank and refine round", not p["problems"])
        # the post-done instruction, printed at the close for the agent to follow
        run(["draw", rt, "--owner", "root"])
        p = run(["make", rt])
        expect("make prints the task's post-done instruction", p["after"] == "mint the same chore for the next month")
        run(["index"])

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
        plant("a state of the older model", "V3", lambda R: raw_edit(R, q3, lambda fm: fm.update(state="decomposed")))
        plant("a field of the older model", "V3", lambda R: raw_edit(R, q3, lambda fm: fm.update(kill=fm.pop("criterion"))))
        plant("a task's kind, an older model's field", "V3", lambda R: raw_edit(R, wt, lambda fm: fm.update(kind="upkeep")))
        plant("a finding's status, an older model's field", "V3", lambda R: raw_edit(R, f, lambda fm: fm.update(status="verified")))
        plant("a record with no id", "V1", lambda R: raw_edit(R, q, lambda fm: fm.update(id=None)))
        plant("a record whose id names another prefix", "V1", lambda R: raw_edit(R, q, lambda fm: fm.update(id="task-9998")))
        plant("a record that does not read", "V0", lambda R: R[q].path.write_text("---\nid: 'unterminated\n---\n"))
        plant("a record that is not UTF-8", "V0", lambda R: R[q].path.write_bytes(b"---\nid: " + q.encode() + b"\nsummary: \xff\n---\n"))
        plant("a ready task whose requires is missing", "V5", lambda R: raw_edit(R, wt, lambda fm: fm.update(requires=["finding-9999"])))
        plant("a parking block that is not a map", "V15", lambda R: raw_edit(R, q4, lambda fm: fm.update(parked="later")))
        plant("a parking block with no reason", "V15", lambda R: raw_edit(R, q4, lambda fm: fm.update(parked={"date": today})))
        plant("a block that names nothing it waits on", "V15", lambda R: raw_edit(R, q4, lambda fm: fm.update(blocked={"date": today, "reason": "r"})))
        plant("a done task parked", "V15", lambda R: raw_edit(R, t4, lambda fm: fm.update(parked={"date": today, "reason": "r"})))
        plant("a parking date that is not a date", "V20", lambda R: raw_edit(R, q4, lambda fm: fm.update(parked={"date": "soon", "reason": "r"})))
        plant("a due date that is not a date", "V20", lambda R: raw_edit(R, wt, lambda fm: fm.update(due="soon")))
        plant("a removed record with no reason", "V17", lambda R: raw_edit(R, t3, lambda fm: fm.update(closed={"date": today})))
        plant("a goal given up with no reason", "V17", lambda R: raw_edit(R, g, lambda fm: fm.update(closed=None)))
        plant("a closing dated in the future", "V20", lambda R: raw_edit(R, t3, lambda fm: fm.update(closed={"date": "2999-01-01", "reason": "r"})))
        plant("a closing reason on an open question", "V17", lambda R: raw_edit(R, q3, lambda fm: fm.update(closed={"date": today, "reason": "r"})))
        plant("a consumed idea naming a card that did not come from it", "V17", lambda R: raw_edit(R, i2, lambda fm: fm.update(consumed_by=[q5])))
        plant("a consumed idea naming its card as one id", "V17", lambda R: raw_edit(R, i2, lambda fm: fm.update(consumed_by=q3)))
        plant("a question answered by nothing", "V18", lambda R: raw_edit(R, q, lambda fm: fm.update(answered_by=None)))
        plant("a question answered by a task", "V18", lambda R: raw_edit(R, q, lambda fm: fm.update(answered_by=t1)))
        plant("a question answered by a list of findings", "V18", lambda R: raw_edit(R, q, lambda fm: fm.update(answered_by=[fa, f])))
        plant("an open question naming an answer", "V18", lambda R: raw_edit(R, q3, lambda fm: fm.update(answered_by=f)))
        plant("a task that names a question in an older model's field", "V3", lambda R: raw_edit(R, wt, lambda fm: fm.update(question=q3)))
        plant("a created date that is not a date", "V20", lambda R: raw_edit(R, q, lambda fm: fm.update(created="yesterday")))
        plant("dangling derived_from ref", "V2", lambda R: raw_edit(R, t4, lambda fm: fm.update(derived_from=["question-9999"])))
        plant("a direction of the directions file, by its bold name", "V2", lambda R: raw_edit(R, q3, lambda fm: fm.update(direction="Bridge")))
        plant("an open question leaning on a dropped direction", "V22", lambda R: raw_edit(R, q3, lambda fm: fm.update(direction=d)))
        plant("an open question serving a reached goal", "V22", lambda R: raw_edit(R, q3, lambda fm: fm.update(serves=g2)))
        plant("duplicate rank", "V14", lambda R: raw_edit(R, q8, lambda fm: fm.update(rank=1, why_now="w", first_move="m")))
        plant("rank on a closed question", "V14", lambda R: raw_edit(R, q5, lambda fm: fm.update(rank=4, why_now="w", first_move="m")))
        plant("stale index", "V11", lambda R: cfg.index.write_text(cfg.index.read_text() + "x\n"))
        idx = cfg.index.read_text()
        cfg.index.write_text(idx.replace("| --- | --- | --- |", "|---|---|---|"))
        msgs = [p["msg"] for p in validate(cfg, load_all(cfg), today)[0] if p["code"] == "V11"]
        cfg.index.write_text(idx + "x\n")
        msgs += [p["msg"] for p in validate(cfg, load_all(cfg), today)[0] if p["code"] == "V11"]
        cfg.index.write_text(idx)
        expect("an index differing from the render only in its form says so, and a stale one does not",
               len(msgs) == 2 and "another version's form" in msgs[0] and "is stale" in msgs[1])
        plant("open question without checked", "V12", lambda R: raw_edit(R, q3, lambda fm: fm.update(checked=None)))
        plant("open task that came from an answered question", "V13", lambda R: raw_edit(R, wt, lambda fm: fm.update(derived_from=[q5])))
        plant("criterion blanked", "V16", lambda R: raw_edit(R, q3, lambda fm: fm.update(criterion=None)))
        plant("derived_from cycle", "V8", lambda R: raw_edit(R, f, lambda fm: fm.update(derived_from=[f])))
        plant("parent cycle", "V8", lambda R: raw_edit(R, q3, lambda fm: fm.update(parent=q3)))
        plant("closed task outside the archive", "V21", lambda R: shutil.move(str(R[t1].path), str(cfg.research / "tasks" / R[t1].path.name)))
        plant("a finding under a shard of the older model", "V21",
              lambda R: ((cfg.research / "findings" / "alpha").mkdir(), shutil.move(str(R[f].path), str(cfg.research / "findings" / "alpha" / R[f].path.name))))
        shutil.rmtree(cfg.research / "findings" / "alpha", ignore_errors=True)
        plant("finding without evidence", "V6", lambda R: raw_edit(R, f, lambda fm: fm.update(evidence=[])))
        plant("an evidence item with no form", "V6", lambda R: raw_edit(R, f, lambda fm: fm.update(evidence=["Lib/Foo.lean#lemma_L"])))
        plant("an evidence item of a form the project does not list", "V6", lambda R: raw_edit(R, f, lambda fm: fm.update(evidence=["folklore:Lib/Foo.lean#lemma_L"])))
        plant("an evidence item twice", "V6", lambda R: raw_edit(R, f, lambda fm: fm.update(evidence=["formal:Lib/Foo.lean#lemma_L"] * 2)))
        plant("finding whose declaration left the manifest", "V6",
              lambda R: ((root / "decls.txt").write_text("module Lib.Foo 0\n"), setattr(cfg, "_manifest", None)))
        (root / "decls.txt").write_text("module Lib.Foo 1\nLib.Foo lemma_L\n")
        cfg._manifest = None
        plant("a body link to a path that is gone, on a live record", "V24",
              lambda R: R[li].path.write_text(render(R[li].fm, "See [gone](papers/gone.md).\n")))
        recs = load_all(cfg)
        recs[t1].path.write_text(render(recs[t1].fm, recs[t1].body + "\nSee [gone](papers/gone.md).\n"))
        problems, warnings, _ = validate(cfg, load_all(cfg), today)
        expect("a body link to a path that is gone, on an archived task, is warned of, never failed",
               not any(p["code"] == "V24" for p in problems) and any(f"{t1}: the body links papers/gone.md" in w for w in warnings))
        recs[t1].path.write_text(render(recs[t1].fm, recs[t1].body))
        plant("a hand over its limit, a drawn idea counted", "V9", lambda R: (
            raw_edit(R, wt, lambda fm: fm.update(state="active", owner="root", drawn=today)),
            raw_edit(R, tq, lambda fm: fm.update(state="active", owner="root", drawn=today)),
            raw_edit(R, heap, lambda fm: fm.update(owner="root", drawn=today))))
        plant("a consumed idea in a hand", "V9", lambda R: raw_edit(R, wi, lambda fm: fm.update(owner="root", drawn=today)))
        plant("body not one sentence per line", "V19", lambda R: R[q].path.write_text(render(R[q].fm, "One sentence. Two sentences on a line.\n")))
        plant("a citation of a key the library does not hold", "V23",
              lambda R: R[q].path.write_text(render(R[q].fm, "As lib:nobody2000 states.\n")))
        plant("a citation of an extract the library's card does not carry", "V23",
              lambda R: R[q].path.write_text(render(R[q].fm, "As lib:jen1990#lemma states, and lib:jen1990#theorem9 does not.\n")))
        stub.write_text("raise SystemExit(3)\n")
        plant("a library that does not answer", "V23", lambda R: None)
        _, warnings, _ = validate(cfg, load_all(cfg), today)
        expect("a peer-reviewed item is unchecked, never failed, while the library does not answer",
               any(f"{fp}: peer-reviewed:jen1990#lemma: unchecked" in w for w in warnings))
        cfg.library_cmd = []
        recs = load_all(cfg)
        raw_edit(recs, q4, lambda fm: fm.update(blocked={"date": today, "on": q5, "reason": "its answer"}))
        expect("a block on a record that has closed is warned of, never failed",
               any(f"blocked on {q5}, which is answered" in w for w in validate(cfg, load_all(cfg), today)[1]))
        raw_edit(load_all(cfg), q4, lambda fm: fm.update(blocked={"date": today, "on": "the release of 2026-09-01", "reason": "its tag"}))
        raw_edit(load_all(cfg), wt, lambda fm: fm.update(due="2026-09-01"))
        _, warnings, _ = validate(cfg, load_all(cfg), today)
        expect("a due date that has passed and a block whose date has passed are warned of, never failed",
               any(f"{wt}: due 2026-09-01 has passed" in w for w in warnings) and any(f"{q4}: blocked on the release of 2026-09-01, whose date has passed" in w for w in warnings))
        raw_edit(load_all(cfg), q4, lambda fm: fm.update(blocked={"date": today, "on": q3, "reason": "needs its answer"}))
        # the library found with no command bound: by library.toml at the root, then the sibling skill or PATH
        with tempfile.TemporaryDirectory() as t2:
            r2 = Path(t2)
            do_init(r2, build_parser().parse_args(["init", "--log", "LOG.md"]))
            c2 = Config(r2)
            expect("init writes no directions file: directions are records, with a directory of their own",
                   not (r2 / "records" / "directions.md").exists() and (r2 / "records" / "directions").is_dir() and (r2 / "records" / "goals").is_dir())
            mdl = shutil.which("markdownlint")
            if mdl:  # init's files and the flow's writes, under the built-in configuration (no project one here)
                (r2 / "body.md").write_text("A sentence well past eighty characters, " + "and on " * 12 + "until it ends.\n", encoding="utf-8")
                rc, _ = dispatch(c2, ["capture", "A long sentence", "--source", "t", "--body", str(r2 / "body.md")], today=today, as_json=True, quiet=True)
                expect("a body sentence longer than 80 characters is written under the built-in configuration", rc == 0)
                dispatch(c2, ["task", "An upkeep", "--tag", "upkeep", "--due", "2026-12-01"], today=today, as_json=True, quiet=True)
                dispatch(c2, ["goal", "A goal", "--criterion", "it is reached"], today=today, as_json=True, quiet=True)
                dispatch(c2, ["direction", "A direction"], today=today, as_json=True, quiet=True)
                (r2 / "body.md").write_text("A line.\n## A heading with no blank line above it\n", encoding="utf-8")
                rc, _ = dispatch(c2, ["capture", "A violation", "--source", "t", "--body", str(r2 / "body.md")], today=today, as_json=True, quiet=True)
                expect("a write adding a violation of the built-in configuration is refused and reverted",
                       rc == 1 and len(list((r2 / "records" / "ideas").glob("*.md"))) == 1)
                (r2 / "body.md").unlink()
                (r2 / "mdl.json").write_text(MDLINT_DEFAULT, encoding="utf-8")
                r = subprocess.run([mdl, "-c", str(r2 / "mdl.json")] + [str(f) for f in sorted(r2.rglob("*.md"))], capture_output=True, text=True)
                expect("the files init writes, and an index with records, a due task, a goal and a direction, pass the built-in configuration", r.returncode == 0)
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
        reportable = set(re.findall(r'bad\("(V\d+)"', SOURCE)) | set(re.findall(r'"code": "(V\d+)"', SOURCE)) \
            | set(re.findall(r'else "(V\d+)", r, f"a ', SOURCE))
        expect(f"every code the check can report is planted ({', '.join(sorted(reportable - planted)) or 'none missing'})",
               reportable <= planted)
        _, _, cov = validate(cfg, load_all(cfg), today)
        expect("with no library bound the coverage says so", cov["library"] is None)
        # the cold-start bundle and the page manifest
        (root / "WORKLOG.md").write_text("# Log\n\n## 2026-09-25 — the top entry\n\n**State.** All is well.\n\n## 2026-09-24 — older\n\nx\n")
        cfg.log = root / "WORKLOG.md"
        (root / "INBOX.md").write_text("# Inbox\n\n- one item\n")
        dispatch(cfg, ["draw", wt, "--owner", "root"], today=today, as_json=True, quiet=True)
        dispatch(cfg, ["index"], today=today, as_json=True, quiet=True)
        lines, more = state_lines(cfg, recs=load_all(cfg), today=today)
        expect("state prints the inbox, the due list, the ranked list, the hands, the dates that have passed and the top log entry with FILE:LINE",
               any(l.startswith("INBOX.md:3:") and "one item" in l for l in lines)
               and any("## Due" in l for l in lines) and any("## Next (ranked)" in l for l in lines) and any(wt in l and "## Hand" not in l for l in lines)
               and any(f"due 2026-09-01 has passed: {wt}" in l for l in lines)
               and any(l.startswith("WORKLOG.md:") and "the top entry" in l for l in lines)
               and not any("older" in l for l in lines) and more is None)
        lines, more = state_lines(cfg, 0, 200)
        expect("state stops at the budget and names the continuation", more is not None and len(lines) < 10)
        lines, more = state_lines(cfg, 0, 5)
        expect("a line longer than the budget is printed alone, and the continuation moves past it", len(lines) == 1 and more == 1)
        pm = pages_manifest(cfg)
        expect("the page manifest names a mount, routes and an id pattern",
               pm["mount"] == "/flow" and any(r["view"] == "record" for r in pm["routes"])
               and re.search(pm["links"][0]["pattern"], "see question-0003 here") and re.search(pm["links"][0]["pattern"], "goal-0001"))

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
                   and all((cfg.research / d).is_dir() for d in ("archive", "findings", "goals", "directions")))
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
        expect("a bare flow.toml: records/, INBOX.md at the root, the five shipped evidence forms",
               cfg.records_name == "records" and cfg.inbox == root / "INBOX.md" and cfg.forms == SHIPPED_FORMS
               and cfg.decl_ext is None and cfg.ev_decl.match("src/Foo.agda#bar") and not cfg.ev_decl.match("papers/a.md#x"))
        expect("declaration evidence with no manifest is unchecked, not failed",
               resolve_evidence(cfg, "formal:src/Foo.agda#bar", {}).startswith("unchecked"))
        (root / "flow.toml").write_text("[evidence]\nmanifest = \"decls.txt\"\n")
        try:
            Config(root)
            expect("a manifest with no manifest_extension is refused", False)
        except Refused as e:
            expect("a manifest with no manifest_extension is refused", "manifest_extension" in str(e))
        (root / "flow.toml").write_text("[evidence]\nforms = [\"Peer Reviewed\"]\n")
        try:
            Config(root)
            expect("a form that is not one lowercase word is refused", False)
        except Refused as e:
            expect("a form that is not one lowercase word is refused", "forms" in str(e))
        a = argparse.Namespace(records="records", log="LOG.md", owner=["me"], force=True)
        written = do_init(root, a)
        cfg = Config(root)
        expect("init --log writes the log with a State paragraph, --owner the owner with a hand of four, the inbox, "
               "and the five shipped evidence forms",
               "LOG.md" in written and "**State.**" in (root / "LOG.md").read_text() and cfg.owners == ("me",) and cfg.hand == {"me": 4}
               and "INBOX.md" in written and cfg.forms == SHIPPED_FORMS and "task" not in cfg.raw and "finding" not in cfg.raw)
        lines, _ = state_lines(cfg)
        expect("flow state prints the new log's top entry", any("the flow set up" in ln for ln in lines))
        r = subprocess.run([sys.executable, __file__, "--help"], capture_output=True, text=True, cwd=tempfile.gettempdir())
        expect("--help works with no bindings file", r.returncode == 0 and "capture" in r.stdout and "init" in r.stdout)
        with tempfile.TemporaryDirectory() as bare:
            (Path(bare) / "a.md").write_text("# A\n\nOne. Two on a line.\n", encoding="utf-8")
            r = subprocess.run([sys.executable, __file__, "reflow", "--check", "a.md"], capture_output=True, text=True, cwd=bare)
            expect("reflow --check runs where no flow.toml stands, with the built-in reflow", r.returncode == 1 and "a.md:3" in r.stdout)

    # the log written at its top and archived by month, a freeze checked, the other prose reflowed
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
        entry.write_text("## 2026-10-27 — a label of the project's\n\n**State (round 3).** Labelled as the project does.\n", encoding="utf-8")
        go(["log", "add", str(entry)])
        expect("log add takes a State label with a parenthesis of the project's", "**State (round 3).** Labelled" in (root / "LOG.md").read_text(encoding="utf-8"))
        (root / "LOG.md").write_text(before, encoding="utf-8")
        entry.write_text("## 2026-10-27 — a longer label\n\n**State of the art.** Not the label.\n", encoding="utf-8")
        go(["log", "add", str(entry)], ok=False)
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

        # the freeze: decided where git and the log can say, and said where they cannot
        with tempfile.TemporaryDirectory() as t2:
            do_init(Path(t2), build_parser().parse_args(["init", "--log", "LOG.md"]))
            c2 = Config(Path(t2))
            if git(c2, "rev-parse", "--is-inside-work-tree") is None:
                rc, pl = dispatch(c2, ["state", "--check"], today=today, as_json=True, quiet=True)
                expect("state --check outside a work tree says the log's part is not decided and exits 2",
                       rc == 2 and any("git is absent" in u for u in pl["undecided"]) and pl["checked"] == [] and not pl["problems"])
        if shutil.which("git"):
            gitc = ["git", "-c", "user.name=flow", "-c", "user.email=flow@selftest", "-c", "commit.gpgsign=false"]
            for argv in (["init", "-q"], ["add", "-A"], ["commit", "-q", "--no-verify", "-m", "the log"]):
                subprocess.run(gitc + argv, cwd=root, capture_output=True, text=True)
            p = go(["state", "--check"])
            expect("state --check passes a clean freeze and says what it checked", not p["problems"] and len(p["checked"]) == 2 and not p["undecided"])
            idea = go(["capture", "an idea"])["records"][0]["path"]
            p = go(["state", "--check"], ok=False)
            expect("planted: a record changed since the top entry's commit that no entry names fails the freeze",
                   [x["path"] for x in p["problems"]] == [idea])
            p = go(["state", "--check"], ok=False, day="2026-10-30")
            expect("planted: a top entry not dated today, the tree changed since its commit, fails the freeze",
                   any("not today (2026-10-30)" in x["msg"] for x in p["problems"]))
            entry.write_text("## 2026-10-27 — an idea\n\n**State.** The idea idea-0001 is captured.\n", encoding="utf-8")
            go(["log", "add", str(entry)])
            p = go(["state", "--check"])
            expect("an entry above the committed one naming the changed record passes the freeze", not p["problems"])
            cfg.inbox.write_text("# Inbox\n\n- look at the bound\n", encoding="utf-8")
            p = go(["state", "--check"])
            expect("an inbox holding items is no failure of the freeze: the next session reads it", not p["problems"])
            t = go(["task", "an upkeep chore", "--tag", "upkeep"])["created"][0]
            go(["draw", t, "--owner", "owner"])
            go(["draw", "idea-0001", "--owner", "agent"])
            entry.write_text(f"## 2026-10-27 — a chore\n\n**State.** The chore {t} is in the person's hand, idea-0001 in the agent's.\n", encoding="utf-8")
            go(["log", "add", str(entry)])
            p = go(["state", "--check"])
            expect("the hands' active tasks and ideas are printed for the State paragraph, and fail nothing, whoever holds them",
                   not p["problems"] and any(h.startswith(f"owner: {t}") for h in p["hands"]) and any(h.startswith("agent: idea-0001") for h in p["hands"]))
        elif os.environ.get("CI"):
            expect("git is on PATH in CI, where the freeze's log part is tested", False)
        else:
            print("  --  the freeze's log part not tested: no git on PATH")

        # the doctor: the words of the model before 0.3, named with what each reads now
        with tempfile.TemporaryDirectory() as t2:
            r2 = Path(t2)
            do_init(r2, build_parser().parse_args(["init", "--log", "LOG.md"]))
            c2 = Config(r2)
            rc, pl = dispatch(c2, ["doctor"], today=today, as_json=True, quiet=True)
            expect("the doctor finds nothing in a tree init wrote", rc == 0 and not pl["problems"])
            for argv in (["capture", "i"], ["frame", "idea-0001", "--summary", "Q", "--criterion", "k"],
                         ["refine", "question-0001", "--task", "t"], ["draw", "task-0001", "--owner", "agent"], ["make", "task-0001"],
                         ["task", "a chore", "--tag", "upkeep"], ["finding", "F", "reference:https://example.org/f", "--from", "task-0001"]):
                dispatch(c2, argv, today=today, as_json=True, quiet=True)
            recs = load_all(c2)

            def old(id_, fn):
                fm = dict(recs[id_].fm)
                fn(fm)
                recs[id_].path.write_text(render(fm, recs[id_].body))
            old("question-0001", lambda fm: (fm.update(state="decomposed", kill=fm.pop("criterion"), answered_by=[], direction="Bridge"), fm.pop("blocked")))
            old("task-0001", lambda fm: fm.update(abandoned={"date": today, "reason": "a wall"}, state="abandoned", drawn=today, owner="prover") or fm.pop("closed"))
            old("task-0002", lambda fm: fm.update(abandoned=None, drawn=today, question="question-0001", kind="work") or fm.pop("closed"))
            old("idea-0001", lambda fm: fm.update(consumed_by="question-0001"))
            old("finding-0001", lambda fm: fm.update(status="refuted", paper="alpha",
                                                     evidence=["papers/alpha.md#Theorem 2.1", "probes/p.py", "Lib/Foo.lean#lemma_L"]))
            (r2 / "flow.toml").write_text((r2 / "flow.toml").read_text(encoding="utf-8")
                                          + '\n[task]\ndefault_kind = "work"\ndecision_owners = ["owner"]\n[finding]\nstated = "proven"\n', encoding="utf-8")
            (r2 / "records" / "directions.md").write_text("# Directions\n\n## Inbox\n\n- an item\n\n## Directions\n\n- **Bridge** (2026-01-01) — the words.\n", encoding="utf-8")
            c2 = Config(r2)
            rc, pl = dispatch(c2, ["doctor"], today=today, as_json=True, quiet=True)
            said = [x["path"] + ": " + x["msg"] for x in pl["problems"]]
            want = ("decision_owners", "[task] default_kind — goes: a task's kind is a tag now", "[finding] — goes", "an `## Inbox` section",
                    "the directions file — directions are records now", '- **Bridge** — `flow direction "Bridge" --body FILE`',
                    "direction: Bridge — the id of the direction record",
                    "state: decomposed — state: open", "kill — criterion", "no blocked",
                    "state: abandoned — state: aborted", "abandoned — closed", f"drawn: {today} on a ready task",
                    "owner: prover — an owner [hand] does not list", "question: question-0001 — goes", "name question-0001 in derived_from",
                    "kind: work — goes: a kind is a tag now", "status: refuted — goes: the forms of the evidence stand for it; delete the field, and add the tag `refuted`",
                    "paper: alpha — goes", "evidence papers/alpha.md#Theorem 2.1 — stated:papers/alpha.md#Theorem 2.1",
                    "evidence probes/p.py — statistical:probes/p.py", "evidence Lib/Foo.lean#lemma_L — formal:Lib/Foo.lean#lemma_L",
                    "consumed_by: question-0001 — consumed_by as a list", "answered_by as a list — answered_by: null")
            expect("the doctor names each old word and field with what it reads now, and exits 1",
                   rc == 1 and all(any(w in x for x in said) for w in want))
            if rc != 1 or not all(any(w in x for x in said) for w in want):
                print("      ", "\n       ".join(said))

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
    p.add_argument("--from", action="append", dest="from_", metavar="ID", help="the record it came from, an idea worked for one; repeatable")
    p = sp.add_parser("task"); p.add_argument("summary")
    p.add_argument("--size"); p.add_argument("--dod"); p.add_argument("--due", metavar="YYYY-MM-DD", help="its due date: surfaced as it nears, never a rank")
    p.add_argument("--after", help="what follows its completion, in words; printed at the close")
    p.add_argument("--source"); p.add_argument("--tag", action="append", help="repeatable; the usual ones are research and upkeep"); p.add_argument("--body")
    p.add_argument("--from", action="append", dest="from_", metavar="ID", help="what it came from: a question, an idea, a task; repeatable")
    p = sp.add_parser("frame"); p.add_argument("ids", nargs="+"); p.add_argument("--summary", required=True); p.add_argument("--criterion", required=True)
    p.add_argument("--size"); p.add_argument("--kind", default="question", choices=("question", "conjecture")); p.add_argument("--parent")
    p.add_argument("--direction", metavar="D", help="the open direction it leans toward, by its id"); p.add_argument("--serves", metavar="G", help="the open goal it serves, by its id")
    p.add_argument("--tag", action="append", help="repeatable"); p.add_argument("--body"); p.add_argument("--source")
    p = sp.add_parser("refine"); p.add_argument("question"); p.add_argument("--task", action="append", metavar="SUMMARY", help="a task minted from the question; repeatable")
    p.add_argument("--subq", action="append", nargs=2, metavar=("SUMMARY", "CRITERION"), help="repeatable"); p.add_argument("--idea", action="append", help="repeatable")
    p.add_argument("--size"); p.add_argument("--dod"); p.add_argument("--requires", action="append", help="repeatable")
    p.add_argument("--tag", action="append", help="on every task minted; repeatable")
    p.add_argument("--body", help="appended to the question's body under the date, never to a task's: a task's own body is "
                                  "`flow task SUMMARY --from Q --body FILE`")
    p = sp.add_parser("draw"); p.add_argument("id"); p.add_argument("--owner", required=True)
    p = sp.add_parser("return"); p.add_argument("id"); p.add_argument("--note")
    p = sp.add_parser("make"); p.add_argument("task")
    p.add_argument("--task", action="append", metavar="SUMMARY", dest="task_out", help="a follow-up task; repeatable")
    p.add_argument("--question", action="append", nargs=2, metavar=("SUMMARY", "CRITERION"), help="repeatable"); p.add_argument("--idea", action="append", help="repeatable")
    p.add_argument("--tag", action="append", help="on every task minted; repeatable"); p.add_argument("--resolution")
    p = sp.add_parser("abort"); p.add_argument("task"); p.add_argument("--reason", required=True); p.add_argument("--resolution")
    p = sp.add_parser("finding"); p.add_argument("summary"); p.add_argument("evidence", nargs="+", metavar="FORM:TARGET")
    p.add_argument("--from", action="append", dest="from_", metavar="ID", help="what it came from: a done or aborted task, an idea, a question; repeatable")
    p.add_argument("--answers", metavar="Q", help="the one question it settles, which closes answered")
    p.add_argument("--depends-on", action="append", help="repeatable", dest="depends_on"); p.add_argument("--tag", action="append", help="repeatable; refuted for a disproof"); p.add_argument("--body")
    p = sp.add_parser("evidence"); p.add_argument("finding"); p.add_argument("evidence", nargs="+", metavar="FORM:TARGET", help="added, never removed: how a finding's trust is raised")
    p = sp.add_parser("goal"); p.add_argument("summary"); p.add_argument("--criterion", required=True, help="what reached means")
    p.add_argument("--horizon", help="how far out the destination lies, in words")
    p.add_argument("--from", action="append", dest="from_", metavar="ID", help="the direction it was produced along, which stays open, or the idea it came from; repeatable")
    p.add_argument("--source"); p.add_argument("--tag", action="append", help="repeatable"); p.add_argument("--body")
    p = sp.add_parser("reach"); p.add_argument("goal"); p.add_argument("--reason", required=True, help="what shows it reached")
    p = sp.add_parser("giveup"); p.add_argument("goal"); p.add_argument("--reason", required=True)
    p = sp.add_parser("direction"); p.add_argument("summary", help="its name")
    p.add_argument("--from", action="append", dest="from_", metavar="ID", help="the idea it came from; repeatable")
    p.add_argument("--source"); p.add_argument("--tag", action="append", help="repeatable"); p.add_argument("--body", help="the owner's words, a file")
    p = sp.add_parser("drop"); p.add_argument("direction"); p.add_argument("--reason", required=True)
    p = sp.add_parser("consume"); p.add_argument("idea")
    p = sp.add_parser("remove"); p.add_argument("id"); p.add_argument("--reason", required=True)
    p = sp.add_parser("wrong"); p.add_argument("question"); p.add_argument("--reason", required=True)
    p = sp.add_parser("impossible"); p.add_argument("question"); p.add_argument("--by", required=True, help="the finding that shows it")
    p = sp.add_parser("park"); p.add_argument("id"); p.add_argument("--reason", required=True); p.add_argument("--revival")
    p = sp.add_parser("unpark"); p.add_argument("id"); p.add_argument("--note")
    p = sp.add_parser("block"); p.add_argument("id"); p.add_argument("--on", required=True, help="a task, a question, or a condition in words")
    p.add_argument("--reason", required=True)
    p = sp.add_parser("unblock"); p.add_argument("id"); p.add_argument("--note")
    p = sp.add_parser("rank"); p.add_argument("id", nargs="?"); p.add_argument("n", nargs="?", type=int); p.add_argument("--set", nargs="+")
    p.add_argument("--clear", action="store_true"); p.add_argument("--insert", action="store_true"); p.add_argument("--why"); p.add_argument("--first-move", dest="first_move")
    p.add_argument("--direction", metavar="D", help="a question's, by its id"); p.add_argument("--serves", metavar="G", help="the goal a question serves, by its id")
    p = sp.add_parser("checked"); p.add_argument("ids", nargs="+")
    p = sp.add_parser("set"); p.add_argument("id"); p.add_argument("field"); p.add_argument("value")
    p = sp.add_parser("find")
    for f in ("type", "state", "kind", "form", "tag", "owner", "requires", "grep"):
        p.add_argument("--" + f)
    p.add_argument("--from", dest="from_", metavar="ID", help="the records that name ID in derived_from")
    p.add_argument("--refers", metavar="ID|PATH", help="the records naming ID or PATH in any reference field, an evidence item or a body link")
    p.add_argument("--deep", action="store_true", help="with --refers: the records naming those, and so on")
    p.add_argument("--depends-on", dest="depends_on"); p.add_argument("--parked", action="store_true"); p.add_argument("--ranked", action="store_true")
    p.add_argument("--blocked", action="store_true"); p.add_argument("--held", action="store_true", help="the active tasks and the ideas in a hand")
    p.add_argument("--id", action="append", dest="id_", metavar="ID", help="these records, a removed one among them; repeatable")
    p = sp.add_parser("show"); p.add_argument("id")
    p = sp.add_parser("graph"); p.add_argument("--from", dest="frm"); p.add_argument("--dot", action="store_true")
    p = sp.add_parser("index"); p.add_argument("--check", action="store_true"); p.add_argument("--print", action="store_true", dest="print_")
    sp.add_parser("check")
    p = sp.add_parser("state"); p.add_argument("--from", dest="frm", type=int, default=0); p.add_argument("--budget", type=int, default=14000)
    p.add_argument("--check", action="store_true", help="what a machine can see of a freeze; exit 1 on a failure, "
                                                         "2 where a part could not be decided")
    p = sp.add_parser("log"); lp = p.add_subparsers(dest="log_cmd", required=True, metavar="{add,archive}")
    lp.add_parser("add", help="FILE: one entry, written at the top of the log").add_argument("file")
    lp.add_parser("archive", help="--before DATE: the older entries moved, one file per month").add_argument("--before", required=True)
    p = sp.add_parser("reflow"); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", nargs="+", metavar="PATH", help="exit 1 on a line the reflow changes, each printed")
    g.add_argument("--as", nargs=2, metavar=("DEST", "DRAFT"), dest="as_", help="the draft checked as if appended to DEST: the reflow and markdownlint")
    sp.add_parser("doctor", help="the records and bindings an older model wrote, and what each reads now")
    sp.add_parser("directions", help="the open directions as the owner's list")
    p = sp.add_parser("tags", help="every tag in use with its records, then the untagged"); p.add_argument("--type")
    sp.add_parser("artifacts", help="every repository path a record refers to, with the records naming it")
    sp.add_parser("pages")
    p = sp.add_parser("init"); p.add_argument("--records", default="records")
    p.add_argument("--log"); p.add_argument("--owner", action="append", help="repeatable"); p.add_argument("--force", action="store_true")
    return ap


TRANSITIONS = {"capture": cmd_capture, "task": cmd_task, "frame": cmd_frame, "refine": cmd_refine, "draw": cmd_draw,
               "return": cmd_return, "make": cmd_make, "abort": cmd_abort, "finding": cmd_finding,
               "consume": cmd_consume, "remove": cmd_remove, "wrong": cmd_wrong, "impossible": cmd_impossible,
               "park": cmd_park, "unpark": cmd_unpark, "block": cmd_block, "unblock": cmd_unblock,
               "rank": cmd_rank, "checked": cmd_checked, "set": cmd_set, "evidence": cmd_evidence,
               "goal": cmd_goal, "reach": cmd_reach, "giveup": cmd_giveup, "direction": cmd_direction, "drop": cmd_drop}


def summary_of(cfg, r):
    d = dict(r.fm)
    d["path"] = rel(cfg, r.path)
    if r.type == "finding":
        d["forms"] = stat(r)
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
    out = {"ok": True, "command": a.cmd, "created": [], "changed": [], "reranked": [], "records": [], "problems": []}
    not_run = False  # exit 2: the check could not run, or could not decide a part

    def emit(text=""):
        if not quiet and not as_json and text:
            print(text)

    try:
        broken = []
        recs = load_all(cfg, broken) if a.cmd == "check" else {} if a.cmd in ("log", "reflow", "doctor") else load_all(cfg)
        if a.cmd in TRANSITIONS:
            if a.cmd == "rank" and not a.set and not a.id:
                raise Refused("rank takes ID N, --set ID..., or ID --clear")
            _JOURNAL.clear()
            _RERANKED.clear()
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
            out["reranked"] = [{"id": i, "from": f, "to": n} for i, f, n in _RERANKED]
            for i, f, n in _RERANKED:
                emit(f"re-ranked {i} {f} → {n}")
            if a.cmd in ("finding", "impossible") and changed:
                emit(f"{changed[0].id} closed {changed[0]['state']} by {changed[0]['answered_by']}")
            if a.cmd in ("make", "abort") and changed and changed[0]["after"]:  # the post-done instruction, for the agent to follow
                out["after"] = changed[0]["after"]
                emit(f"after {changed[0].id}: {changed[0]['after']}")
            if a.cmd in ("giveup", "drop") and len(changed) > 1:
                out["released"] = [r.id for r in changed[1:]]
                emit(f"released: {', '.join(r.id for r in changed[1:])} — "
                     + ("they serve nothing now and keep their ranks; re-rank them" if a.cmd == "giveup" else "they carry no direction now"))
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
            problems, checked, undecided = close_check(cfg, recs, today)
            out["problems"], out["checked"], out["undecided"] = problems, checked, undecided
            out["hands"] = hands(cfg, recs)
            for h in out["hands"]:
                emit(f"hand: {h}")
            for p in problems:
                emit(f"{p['path']}: {p['msg']}")
            for u in undecided:
                emit(f"undecided: {u}")
            emit(f"flow state --check: {len(problems)} failure(s); checked {', '.join(checked)}"
                 + (f"; {len(undecided)} not decided" if undecided else "")
                 + "; the conversation's inventory and the sweep by meaning are the session's own")
            if problems or undecided:  # a failure exits 1; else a part not decided exits 2, never read as clean
                out["ok"], not_run = False, not problems
        elif a.cmd == "doctor":
            found = doctor(cfg, today)
            out["problems"] = [{"code": "DOCTOR", "id": None, "path": p, "msg": f"{was} — {now}"} for p, was, now in found]
            for p, was, now in found:
                emit(f"{p}: {was} — {now}")
            emit(f"flow doctor: {len(found)} thing(s) written in an older model's words" + (
                "; edit each by hand, then `flow index` and `flow check`" if found else ""))
            if found:
                out["ok"] = False
        elif a.cmd == "state":
            lines, more = state_lines(cfg, a.frm, a.budget, recs, today)
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
            out["text"] = render_directions(recs)
            emit(out["text"].rstrip("\n"))
        elif a.cmd == "tags":
            tags, untagged = cmd_tags(cfg, recs, a, today)
            out["tags"], out["untagged"] = tags, untagged
            out["lines"] = [f"{t} ({len(ids)}): {', '.join(ids)}" for t, ids in tags.items()] + [f"(none) ({len(untagged)}): {', '.join(untagged) or '-'}"]
            for ln in out["lines"]:
                emit(ln)
        elif a.cmd == "artifacts":
            arts = cmd_artifacts(cfg, recs, a, today)
            out["artifacts"] = arts
            out["lines"] = [f"{x['path']}{'' if x['exists'] else '  MISSING'} — " + ", ".join(f"{y['id']} ({y['via']})" for y in x["records"]) for x in arts]
            for ln in out["lines"]:
                emit(ln)
            emit(f"{len(arts)} path(s) referred to, {sum(not x['exists'] for x in arts)} missing")
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
                 + (f"evidence forms {', '.join(cov['forms'])}; declaration evidence via {cfg.manifest if cov['manifest'] else 'NOT CONFIGURED'}; "
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
                emit("to reproduce: `flow check` at the project root, the flow skill's scripts/flow.py; "
                     "where no skill is loaded, `pre-commit run flow-check --all-files`")
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
        if rest[0] == "reflow" and not known.root:  # the prose check needs no bindings: the defaults where no flow.toml stands above
            try:
                root = find_root(os.getcwd())
            except Refused:
                root = Path(os.getcwd()).resolve()
            cfg = Config(root, bare=True)
        else:
            root = Path(known.root).resolve() if known.root else find_root(os.getcwd())
            cfg = Config(root)
    except Refused as e:
        refused(rest[0], str(e), known.json)
        return 2
    rc, _ = dispatch(cfg, argv)
    return rc


if __name__ == "__main__":
    sys.exit(main())
