#!/usr/bin/env python3
"""library — the reference library: one card per referred work, a check, a ranked find.

A card is one Markdown file, `cards/<key>.md` under the directory `library.toml`
names: front matter (the work's fields, how it was read, an optional kept copy,
links to other cards) and a body of two sections, `## Notes` (ours) and
`## Extracts` (what the work says at a place).  A card is read alone: nothing on
it names a record of any other system.  Whoever cites a work writes the cite
prefix and the key (`lib:jen1990` here), and asks this tool whether the key exists.

Writers (the only writers of key, state, read, related and copy):

  library register TITLE --kind K [--author "Surname, I."]... [--year Y] [--venue V]
             [--doi D] [--arxiv A] [--openalex W] [--zbmath Z] [--isbn I] [--url U]
             [--key KEY] [--read GRADE] [--read-on DATE] [--read-what W] [--via KEY]
             [--tag T]... [--note TEXT]... [--notes FILE] [--seed] [--file PATH]
                                       a new card; --file makes it an internal document, a tracked
                                       file of the project that is its own copy and that no bound
                                       document may cite
  library read KEY --grade GRADE [--what W] [--on DATE | --undated] [--via KEY] [--note TEXT]
  library note KEY [--note TEXT]... [--notes FILE] [--tag T]...
                                       a dated note, tags: the body's writer for a load
  library extract KEY ID --at LOCATOR [--quote TEXT]... [--says TEXT] [--caveat TEXT] [--rule TEXT]
             [--on DATE] [--edition TEXT] [--unanchored WHY] [--replace]
                                       an addressed extract, cited as key#id and anchored by `check`
                                       in the kept copy's text
  library type KEY [--title T] [--author A]... [--year Y] [--venue V]   a field corrected by the hand, and marked
  library relate KEY KEY [--drop]      a symmetric, non-transitive link
  library exclude KEY --reason R | --undo
  library keep KEY FILE [--from URL | --redistributable] [--on DATE] [--version V] [--move] [--replace]
                                       a file obtained by hand taken in as the card's copy: under the tracked
                                       kept directory when the project names one, else in the store

Online, on demand and never part of `check` (no key needed; `LIBRARY_MAILTO`, `OPENALEX_API_KEY`
and `SEMANTIC_SCHOLAR_API_KEY` are read from the environment when set, never from a file):

  library resolve ENTRY [--doi D] [--arxiv A] [--openalex W] [--title T] [--at NAME] [--register]
             [--pick N] [--override REASON] [--key KEY] [--kind K] [--author A]... [--year Y]
             [--venue V] [--tag T]... [--note TEXT]... [--seed]
                                       candidates for a reference entry, each put to an identity
                                       check against it; --register writes the card from the one
                                       that passes, the tool typing the fields; a field given here
                                       by the hand is kept where the resolver's differs
  library verify REF... [--take FIELD]...   re-resolve a card's identifiers, compare, stamp `verified`
  library fetch KEY [--url U] [--version V] [--pdf] [--replace]
                                       a copy by the card's identifiers — arXiv's TeX source, else its
                                       PDF, else the card's address — kept in the store with its hash,
                                       date, version, address and page count, its text beside it by page
  library restore [KEY...]             every recorded copy the store has lost, fetched from its recorded
                                       address and checked against its hash; a copy obtained by hand named,
                                       restored from version control where the project keeps it tracked
  library watch [NAME...]              each watch looks once: the newest works citing a card, the works
                                       OpenAlex relates to it, the newest answers to a saved arXiv or GitHub
                                       query; what no run has seen and no card or candidate names is proposed.
                                       A check, not a schedule: it keeps what it has seen and no clock
  library watch --add NAME (--citing KEY | --related KEY | --arxiv QUERY | --github QUERY)
             [--since DATE] [--why TEXT]     a watch; --drop NAME, --list (both offline)
  library candidates [--excluded]      the works the watches surfaced (offline); --exclude ID... --reason R
                                       sets some aside for good

`library init [--dir library] [--kept] [--scan PATH]... [--documents GLOB]... [--internal DIR]...
[--force]` writes a project's `library.toml` and its directories; `library pages` prints the dashboard's page manifest.
`library resolve --url URL` takes a repository through its forge's API and any other page through
its citation metadata, for a project that cards tools and pages more than papers.

Views (one line per card; a card is named by its key or by any of its identifiers):

  library show REF                     the card, its links resolved, its citing sites counted
  library find [WORDS...] [--tag T] [--grade G] [--state S] [--kind K] [--id V]
             [--limit N] [--from N]    ranked full-text search; its first line names the rankers
  library find --text WORDS...         the kept text searched: one line per page holding every word
  library page REF [N]                 the units of a kept copy — a PDF's pages, a TeX source's sections —
                                       or the text of one
  library related REF                  other cards by link, known-through, tags, cited together
  library cited REF                    where the key is cited, computed from the configured paths
  library entries [--untied]           the documents' reference entries, each with the card it is tied to
  library claims [DOC...] [--uncovered]   the documents' claim-shaped sentences naming a carded work,
                                       each with the extracts its card carries
  library keys                         every key with its state and grade, as JSON (the consumer's contract)
  library index [--check]              the generated INDEX.md
  library check                        every rule, and a coverage line saying what was not looked at

`--json` on every command.  Exit 0 applied / 1 refused or a violation / 2 could not run.
`--selftest` builds a temporary tree, runs the happy path and plants one defect per rule.

Standard library only.  Front matter is a small YAML subset this file reads and
writes itself: `field: scalar`, a block list of scalars, a one-level block map; a
string that is not a plain word is written in double quotes, JSON's escapes.
"""

import argparse
import contextlib
import datetime as dt
import hashlib
import html
import http.client
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
import traceback
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

STATES = ("registered", "excluded")
# How a work was read: a claim about us, never about the work.  `ungraded` is a
# seeded card nobody has assessed.
GRADES = ("ungraded", "unread", "skimmed", "parts", "full")
IDENTS = ("doi", "arxiv", "openalex", "zbmath", "isbn")
FIELDS = ("key", "state", "excluded", "kind", "title", "authors", "year", "venue",
          "doi", "arxiv", "openalex", "zbmath", "isbn", "url",
          "metadata", "verified", "read", "via", "copy", "related", "tags", "seeded", "created")
# A card that names a tracked file of the project is an internal document — a report, a survey, a review:
# a work like any other, except that the file is its copy and no bound document may cite it.
OPTIONAL = ("file",)
LISTS = ("authors", "related", "tags")
MAPS = {"metadata": ("from", "on", "typed"), "verified": ("on", "by"), "read": ("grade", "on", "what"),
        "excluded": ("on", "reason"), "copy": ("path", "sha256", "fetched", "version", "from", "pages", "text")}
SECTIONS = ("Notes", "Extracts")
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FENCE = "---"
INDEX_VERSION = "2"


class Refused(Exception):
    pass


# --- configuration -----------------------------------------------------------

def find_root(start):
    p = Path(start).resolve()
    for cand in (p, *p.parents):
        if (cand / "library.toml").is_file():
            return cand
    raise Refused(f"no library.toml found above {start}")


class Config:
    def __init__(self, root):
        self.root = Path(root)
        try:
            raw = tomllib.loads((self.root / "library.toml").read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
            raise Refused(f"{self.root / 'library.toml'} does not parse: {e}")
        paths = raw.get("paths", {})
        self.dir_name = paths.get("library", "library")
        self.dir = self.root / self.dir_name
        self.cards = self.dir / "cards"
        self.index = self.dir / "INDEX.md"
        # The watches with what each has seen, and the works a watch surfaced: tracked, written by the tool.
        self.watch_file = self.dir / "watch.toml"
        self.cand_file = self.dir / "candidates.toml"
        # Kept copies and the derived full-text index; the project keeps it out of version control.
        self.store_name = paths.get("store")
        self.store = self.root / self.store_name if self.store_name else None
        # Copies nothing can fetch again — obtained by hand, with no address: a tracked directory when
        # the project names one ([paths] kept), the store otherwise; their text is derived under the store.
        self.kept_name = paths.get("kept")
        self.kept = self.root / self.kept_name if self.kept_name else None
        self.reflow_module = paths.get("reflow_module")
        self.kinds = as_tuple(raw.get("card", {}).get("kinds", (
            "article", "book", "chapter", "preprint", "thesis", "report", "document", "web", "repository", "dataset")))
        cite = raw.get("cite", {})
        self.cite_prefix = cite.get("prefix", "lib:")
        self.scan = as_tuple(cite.get("scan", ()))
        self.cite_re = re.compile(r"(?<![A-Za-z0-9])%s([a-z0-9][a-z0-9-]*)" % re.escape(self.cite_prefix))
        self.cite_ex_re = re.compile(r"(?<![A-Za-z0-9])%s([a-z0-9][a-z0-9-]*)#([a-z0-9][a-z0-9-]*)" % re.escape(self.cite_prefix))
        self.limit = int(raw.get("find", {}).get("limit", 10))
        # Internal documents: the kinds a card naming a tracked file takes, and the directories whose
        # every file has such a card.
        internal = raw.get("internal", {})
        self.internal_kinds = as_tuple(internal.get("kinds", ("report", "document")))
        self.internal_dirs = as_tuple(internal.get("directories", ()))
        # The shapes of a sentence that credits the document against a named work: regular expressions.
        self.claim_shapes = as_tuple(raw.get("claims", {}).get("shapes", CLAIM_SHAPES))
        # The command that prints a PDF's text with a form feed between pages; `{file}` stands for the copy.
        tc = raw.get("copy", {}).get("text_command", ())
        self.text_command = tuple(shlex.split(tc)) if isinstance(tc, str) else tuple(tc)
        # The documents whose reference entries are tied to cards, and the heading their entries stand under.
        ent = raw.get("entries", {})
        self.entry_docs = as_tuple(ent.get("documents", ()))
        self.entry_heading = ent.get("heading", "References")
        self._reflow = None

    def reflow(self, text):
        if self._reflow is None:
            fn = None
            if self.reflow_module and (self.root / self.reflow_module).is_file():
                spec = importlib.util.spec_from_file_location("_reflow", self.root / self.reflow_module)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                fn = getattr(mod, "reflow_text", None)
            self._reflow = fn or _builtin_reflow
        lines = text.split("\n")
        if not any(EX_HEAD_START.match(ln) for ln in lines):
            return self._reflow(text)
        # an extract's head line is structure, not prose: its locator ("p. 5") or edition is never split
        out, run = [], []
        for ln in lines + [None]:
            if ln is None or EX_HEAD_START.match(ln):
                if run:
                    out.append(self._reflow("\n".join(run)))
                    run = []
                if ln is not None:
                    out.append(ln)
            else:
                run.append(ln)
        return "\n".join(out)

    @property
    def reflow_source(self):
        return self.reflow_module if self.reflow_module and (self.root / self.reflow_module).is_file() else "built-in"

    def scan_files(self):
        out = []
        for s in self.scan:
            p = self.root / s
            if p.is_file():
                out.append(p)
            elif p.is_dir():
                out += sorted(p.rglob("*.md"))
        return out


def as_tuple(v):
    """A list binding; one string written where a list is meant is that one item, not its characters."""
    return (v,) if isinstance(v, str) else tuple(v)


_SENT = re.compile(r"([.?!])([\"”’')\]*`]*)[ \t]+(?=[A-Z0-9*`(\[“\"§_])")


def _builtin_reflow(text):
    out, fence = [], False
    for line in text.split("\n"):
        if line.startswith(("```", "~~~")):
            fence = not fence
        if fence or not line.strip() or line.lstrip().startswith(("#", "|", ">")) or line.startswith("    "):
            out.append(line)
            continue
        m = re.match(r"^( *)([-*+] |\d+[.)] )?", line)
        indent, marker = m.group(1), m.group(2) or ""
        body, cont = line[m.end():], indent + " " * len(marker)
        parts, start = [], 0
        for b in _SENT.finditer(body):
            if body.count("`", 0, b.start()) % 2 == 1 or re.match(r"^(?:[-*+](?:[ \t]|$)|\d+[.)](?:[ \t]|$)|#|>|\|)", body[b.end():]):
                continue
            parts.append(body[start:b.end(2)].strip())
            start = b.end()
        parts.append(body[start:].strip())
        parts = [p for p in parts if p]
        out.append(indent + marker + parts[0] if parts else line.rstrip())
        out += [cont + p for p in parts[1:]]
    return "\n".join(out)


# --- front matter: a YAML subset, read and written here ------------------------

BARE = re.compile(r"^[A-Za-z][A-Za-z0-9_./-]*$")
KEYWORDS = {"null", "true", "false", "yes", "no", "on", "off", "y", "n", "none"}


def scalar(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    s = str(v)
    return s if BARE.match(s) and s.lower() not in KEYWORDS else json.dumps(s, ensure_ascii=False)


def unscalar(s, where):
    s = s.strip()
    if s in ("null", "~"):
        return None
    if s in ("true", "false"):
        return s == "true"
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if s.startswith('"'):
        try:
            v = json.loads(s)
        except ValueError:
            v = None
        if isinstance(v, str):
            return v
        raise Refused(f"{where}: not a double-quoted string")
    if len(s) >= 2 and s[0] == s[-1] == "'" and "'" not in s[1:-1].replace("''", ""):
        return s[1:-1].replace("''", "'")  # read a single-quoted string; the tool writes double quotes
    if BARE.match(s) and s.lower() not in KEYWORDS:
        return s
    raise Refused(f"{where}: write the value in double quotes")


def dump_front(fm):
    out = []
    for k, v in fm.items():
        if isinstance(v, list):
            out += [f"{k}:"] + [f"- {scalar(x)}" for x in v] if v else [f"{k}: []"]
        elif isinstance(v, dict):
            out += [f"{k}:"] + [f"  {sk}: {scalar(sv)}" for sk, sv in v.items()]
        else:
            out.append(f"{k}: {scalar(v)}")
    return "\n".join(out)


def load_front(text, name):
    fm, lines, i = {}, text.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([a-z_]+):(?: (.*))?$", line)
        if not m:
            raise Refused(f"{name}: front matter line {i + 2} is not `field: value`")
        k, rest = m.group(1), (m.group(2) or "").strip()
        if k in fm:
            raise Refused(f"{name}: field {k} twice")
        i += 1
        if rest == "[]":
            fm[k] = []
        elif rest:
            fm[k] = unscalar(rest, f"{name}: {k}")
        else:
            items, sub = [], {}
            while i < len(lines) and lines[i].startswith(("- ", "  ")):
                if lines[i].startswith("- "):
                    items.append(unscalar(lines[i][2:], f"{name}: {k}"))
                else:
                    sm = re.match(r"^  ([a-z0-9_]+): (.*)$", lines[i])
                    if not sm:
                        raise Refused(f"{name}: front matter line {i + 2} is not `  field: value`")
                    sub[sm.group(1)] = unscalar(sm.group(2), f"{name}: {k}.{sm.group(1)}")
                i += 1
            if items and sub or not (items or sub):
                raise Refused(f"{name}: field {k} has no value (an empty one is written null or [])")
            fm[k] = items or sub
    return fm


# --- cards -------------------------------------------------------------------

class Card:
    __slots__ = ("path", "fm", "body")

    def __init__(self, path, fm, body):
        self.path, self.fm, self.body = path, fm, body

    @property
    def key(self):
        return self.path.stem

    def __getitem__(self, k):
        return self.fm.get(k)

    @property
    def grade(self):
        r = self.fm.get("read")
        return r.get("grade") if isinstance(r, dict) else None


def parse(path):
    try:
        text = path.read_text(encoding="utf-8-sig")  # an editor's byte-order mark is not part of the record
    except UnicodeDecodeError as e:
        raise Refused(f"{path.name}: not UTF-8 ({e.reason} at byte {e.start})")
    if not text.startswith(FENCE + "\n"):
        raise Refused(f"{path.name}: no front matter")
    end = text.find("\n" + FENCE + "\n", len(FENCE))
    if end < 0 and text.endswith("\n" + FENCE):  # a record that is front matter alone, its last newline dropped
        end = len(text) - len(FENCE) - 1
    if end < 0:
        raise Refused(f"{path.name}: unterminated front matter")
    fm = load_front(text[len(FENCE) + 1:end], path.name)
    return Card(path, fm, text[end + len(FENCE) + 2:].lstrip("\n"))


def render(fm, body):
    body = body.rstrip("\n")
    return f"{FENCE}\n{dump_front(fm)}\n{FENCE}\n" + (f"\n{body}\n" if body else "")


def load_all(cfg):
    """Every card that parses, and one problem per card that does not."""
    cards, broken = {}, []
    if cfg.cards.is_dir():
        for p in sorted(cfg.cards.glob("*.md")):
            try:
                cards[p.stem] = parse(p)
            except Refused as e:
                broken.append({"code": "L0", "key": p.stem, "path": rel(cfg, p), "msg": str(e)})
    return cards, broken


def rel(cfg, path):
    try:
        return str(Path(path).resolve().relative_to(cfg.root.resolve()))
    except ValueError:
        return str(path)


def sections(body):
    """The body as {heading: text}, in order; text before the first heading is under ''."""
    out, cur = {"": []}, ""
    for line in body.split("\n"):
        m = re.match(r"^## (.+?)\s*$", line)
        if m:
            cur = m.group(1)
            out.setdefault(cur, [])
        else:
            out[cur].append(line)
    return {k: "\n".join(v).strip("\n") for k, v in out.items()}


def body_of(notes="", extracts="", sec=None):
    """The body: `## Notes`, `## Extracts`, and — so that a writer never drops a word it did not write —
    whatever else `sec` (the body's sections as read) carried before or after them, as it stood."""
    rest = {k: v for k, v in (sec or {}).items() if k not in ("Notes", "Extracts")}
    head = (rest.pop("", "").strip() + "\n\n") if rest.get("", "").strip() else ""
    tail = "".join(f"\n## {k}\n" + (f"\n{v.strip()}\n" if v.strip() else "") for k, v in rest.items() if k)
    return head + "## Notes\n" + (f"\n{notes.strip()}\n" if notes.strip() else "") + \
           "\n## Extracts\n" + (f"\n{extracts.strip()}\n" if extracts.strip() else "") + tail


def add_note(card, today, text):
    sec = sections(card.body)
    notes = (sec.get("Notes", "") + f"\n\n{today} — {text}").strip()
    card.body = body_of(notes, sec.get("Extracts", ""), sec)


def write_whole(path, text):
    """The file replaced in one step: a reader never sees it half-written, and a failure leaves the old file."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


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


def write_card(cfg, card):
    card.body = cfg.reflow(card.body) if card.body else card.body
    card.path.parent.mkdir(parents=True, exist_ok=True)
    write_whole(card.path, render(card.fm, card.body))


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text)) if not unicodedata.combining(c)).lower()


def surname(author):
    """`Surname, I.` gives the surname; a name with no comma gives its last word."""
    a = str(author).strip()
    return a.split(",")[0].strip() if "," in a else (a.split()[-1] if a.split() else "")


def label(fm):
    names = [surname(a) if "," in str(a) else str(a).strip() for a in fm.get("authors") or []]  # a body's name stands whole
    who = names[0] if len(names) == 1 else " & ".join(names) if len(names) == 2 else f"{names[0]} et al." if names else ""
    year = f" ({fm['year']})" if fm.get("year") else ""
    return f"{who}{year} — {fm.get('title')}" if who else f"{fm.get('title')}{year}"


def make_key(cards, authors, year, title):
    """The pinned key: first surname and year, a letter added on a clash; never regenerated afterwards."""
    stem = authors and surname(authors[0]) or (str(title).split() or ["work"])[0]
    letters = re.sub(r"[^a-z0-9]+", "-", fold(stem).encode("ascii", "ignore").decode()).strip("-")
    if not letters:
        raise Refused(f"no key can be made of {stem!r} in ASCII letters: give one with --key")
    base = letters + (str(year) if year else "")
    key, n = base, 1
    while key in cards:
        n += 1
        key = base + "abcdefghijklmnopqrstuvwxyz"[n - 1] if n <= 26 else f"{base}-{n}"
    return key


def norm_ident(field, value):
    """An identifier as stored: no resolver prefix, an arXiv identifier without its version."""
    v = str(value).strip()
    if field == "doi":
        v = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", v, flags=re.I)
    elif field == "arxiv":
        v = re.sub(r"v\d+$", "", re.sub(r"^(https?://arxiv\.org/abs/|arxiv:)", "", v, flags=re.I))
    elif field == "openalex":
        v = re.sub(r"^https?://openalex\.org/", "", v, flags=re.I)
    return v


def by_ref(cards, ref):
    """A card by its key, or by any of its identifiers."""
    if ref in cards:
        return cards[ref]
    for f in IDENTS + ("url",):
        want = norm_ident(f, ref).lower()
        for c in cards.values():
            if c[f] and str(c[f]).lower() == want:
                return c
    raise Refused(f"{ref} is neither a key nor an identifier of a card")


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --- reference entries of the configured documents ---------------------------------

# the date of an entry: a year (1990, 1990a, 1990/1991, 2005, March 3), or none yet (n.d., in press, forthcoming)
ENTRY_DATE = r"\((?:\d{4}[a-z]?(?:/\d{4})?(?:, [^()]{1,30}?)?|n\. ?d\.(?:-[a-z])?|in press|forthcoming)\)"
ENTRY_RE = re.compile(r"^(?:[-*+][ \t]+)?(?:\*\*?|__?)?((?:[a-z]+ ){0,2}[A-ZÀ-Ž](?:[^()]|\((?!\d{4}|n\. ?d\.|in press|forthcoming)[^()]{1,20}\)){0,300}?)(" + ENTRY_DATE + ")")


def year_in(year, words):
    """Whether a year stands in the normalized words of an entry, a letter suffix (1990a) allowed."""
    return re.search(rf" {re.escape(str(year))}[a-z]? ", words) is not None


def cut_entry(line):
    """A reference entry without its list marker and without the annotation that follows the work's own data."""
    text = re.sub(r"^[-*+][ \t]+", "", line)
    m = re.search(ENTRY_DATE, text)
    k = re.search(r"\.\*? \((?!\d{4}\))|\.\*? — ", text[m.end():] if m else text)
    return (text[:(m.end() if m else 0) + k.start() + 1] if k else text).strip(), (text[(m.end() if m else 0) + k.end() - 1:].strip() if k else "")


def reference_lines(cfg):
    """(file, line number, line) for every line under the bound heading of the configured documents, up to
    the next heading of its level or a rule."""
    for pattern in cfg.entry_docs:
        for f in sorted(cfg.root.glob(pattern)):
            on = False
            for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
                if re.match(r"^#{1,2} ", line) or re.match(r"^---\s*$", line):
                    on = bool(re.match(r"^## %s\s*$" % re.escape(cfg.entry_heading), line))
                elif on:
                    yield f, n, line


def unread_lines(cfg):
    """The lines under the bound heading written like an entry — a list item, or a year in parentheses —
    that are not read as one, so a document's reference the check cannot see is named, not skipped."""
    return [(rel(cfg, f), n, line) for f, n, line in reference_lines(cfg) if not ENTRY_RE.match(line)
            and re.search(r"^\s*(?:[-*+]|\d+[.)]|\[\d+\])\s|\(\d{4}|\(n\. ?d\.\)", line)]


def reference_entries(cfg):
    """Every reference entry of the configured documents: a line under the bound heading, up to the next
    heading of its level or a rule, that opens with its authors and a year in parentheses."""
    out = []
    for f, n, line in reference_lines(cfg):
        m = ENTRY_RE.match(line)
        if m:
            entry, note = cut_entry(line)
            out.append({"doc": rel(cfg, f), "line": n, "entry": entry, "annotation": note,
                        "authors": m.group(1).strip(" *_"), "year": int(m.group(2)[1:5]) if m.group(2)[1:5].isdigit() else None,
                        "raw": line})
    return out


# --- citing sites, computed and never stored -------------------------------------

def citing_sites(cfg, cards):
    """key -> [(file, line number, line)] over the configured paths; a card's own file never cites itself."""
    out = defaultdict(list)
    for e in tied_entries(cfg, cards):
        if len(e["keys"]) == 1:
            out[e["keys"][0]].append((e["doc"], e["line"], e["entry"]))
    for f in cfg.scan_files():
        own = f.stem if f.parent.resolve() == cfg.cards.resolve() else None
        try:
            lines = f.read_text(encoding="utf-8").split("\n")
        except (OSError, UnicodeDecodeError):
            continue
        for n, line in enumerate(lines, 1):
            for k in set(cfg.cite_re.findall(line)):
                if k != own:
                    out[k].append((rel(cfg, f), n, line.strip()))
    return out


def related_cards(cfg, cards, c):
    """Other cards ranked by an explicit link, known-through, tags in common and files citing both; each with its reasons."""
    sites = citing_sites(cfg, cards)
    files = {k: {s[0] for s in v} for k, v in sites.items()}
    mine, tags = files.get(c.key, set()), set(c["tags"] or [])
    rows = []
    for o in cards.values():
        if o.key == c.key:
            continue
        why, score = [], 0
        if o.key in (c["related"] or []):
            why.append("linked")
            score += 100
        if c["via"] == o.key or o["via"] == c.key:
            why.append("known through")
            score += 50
        common = sorted(tags & set(o["tags"] or []))
        if common:
            why.append("tags: " + ", ".join(common))
            score += 10 * len(common)
        both = sorted(mine & files.get(o.key, set()))
        if both:
            why.append("cited together in: " + ", ".join(both))
            score += 5 * len(both)
        if score:
            rows.append((score, o, why))
    rows.sort(key=lambda x: (-x[0], x[1].key))
    return rows


# --- find: ranked full-text search over the cards ---------------------------------

SEARCHED = ("key", "title", "authors", "venue", "ids", "tags", "notes", "extracts")
WEIGHTS = (6, 8, 4, 2, 4, 4, 1, 1)


def field_texts(c):
    sec = sections(c.body)
    return (c.key, str(c["title"] or ""), "; ".join(map(str, c["authors"] or [])), str(c["venue"] or ""),
            " ".join(str(c[f]) for f in IDENTS + ("url",) if c[f]), " ".join(map(str, c["tags"] or [])),
            sec.get("Notes", ""), sec.get("Extracts", ""))


def connect_index(cfg):
    """The derived index in the store, or one in memory where the store cannot be written."""
    con = None
    if cfg.store:
        try:
            cfg.store.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(cfg.store / "index.sqlite")
            con.execute("create table if not exists meta (k text primary key, v text)")
        except (OSError, sqlite3.Error):
            con = None
    if con is None:
        con = sqlite3.connect(":memory:")
        con.execute("create table meta (k text primary key, v text)")
    return con


def open_index(cfg, cards):
    """The full-text index over the cards, rebuilt when any card changed; None where SQLite has no FTS5."""
    sig = hashlib.sha256(json.dumps([INDEX_VERSION] + sorted(
        (k, c.path.stat().st_mtime_ns, c.path.stat().st_size) for k, c in cards.items())).encode()).hexdigest()
    con = connect_index(cfg)
    row = con.execute("select v from meta where k = 'sig'").fetchone()
    if row and row[0] == sig:
        return con
    try:
        con.execute("drop table if exists cards")
        con.execute("create virtual table cards using fts5(%s, tokenize = 'porter unicode61 remove_diacritics 2')"
                    % ", ".join(SEARCHED))
    except sqlite3.OperationalError:
        con.close()
        return None
    con.executemany("insert into cards values (?, ?, ?, ?, ?, ?, ?, ?)", [field_texts(c) for c in cards.values()])
    con.execute("insert or replace into meta values ('sig', ?)", (sig,))
    con.commit()
    return con


def rank_fts(con, terms):
    cols = ", ".join(f"highlight(cards, {i}, char(1), char(2))" for i in range(len(SEARCHED)))
    q = " OR ".join(f'"{t}"' for t in terms)
    rows = con.execute(f"select key, {cols} from cards where cards match ? order by bm25(cards, %s)"
                       % ", ".join(map(str, WEIGHTS)), (q,)).fetchall()
    return [(r[0], [SEARCHED[i] for i in range(len(SEARCHED)) if "\x01" in r[i + 1]]) for r in rows]


def rank_words(cards, terms):
    want, rows = [fold(t) for t in terms], []
    for c in cards.values():
        score, matched = 0, []
        for name, text, w in zip(SEARCHED, field_texts(c), WEIGHTS):
            toks = set(re.findall(r"\w+", fold(text)))
            n = sum(1 for t in want if t in toks)
            if n:
                score += w * n
                matched.append(name)
        if score:
            rows.append((score, c.key, matched))
    rows.sort(key=lambda x: (-x[0], x[1]))
    return [(k, m) for _, k, m in rows]


def find(cfg, cards, a):
    terms = [t for w in a.words for t in re.findall(r"\w+", w)]
    if terms:
        con = open_index(cfg, cards)
        if con is not None:
            rankers, hits = ["fts5 (stemmed, diacritics folded)"], rank_fts(con, terms)
            con.close()
        else:
            rankers, hits = ["words (this SQLite has no FTS5: whole words, diacritics folded, no stemming)"], rank_words(cards, terms)
    else:
        rankers, hits = ["none (no words: the cards by key)"], [(k, []) for k in sorted(cards)]
    state = a.state or "registered"
    want_id = a.id.lower() if a.id else None
    out = []
    for k, matched in hits:
        c = cards.get(k)
        if c is None or (state != "any" and c["state"] != state):
            continue
        if a.grade and c.grade != a.grade or a.kind and c["kind"] != a.kind or a.tag and a.tag not in (c["tags"] or []):
            continue
        if want_id and not any(c[f] and str(c[f]).lower() == norm_ident(f, want_id).lower() for f in IDENTS + ("url",)):
            continue
        out.append((c, matched))
    return rankers, out


# --- the generated index ----------------------------------------------------------

def render_index(cfg, cards):
    out = ["# Reference library", "",
           "*Generated by `library index`; never hand-edited; `library check` fails when it is stale.",
           "One line per card: the key, the label, how the work was read, its kind and its tags.",
           "Search with `library find`; past a few hundred cards this file is searched and not read.*", ""]
    reg = [c for _, c in sorted(cards.items()) if c["state"] != "excluded"]
    exc = [c for _, c in sorted(cards.items()) if c["state"] == "excluded"]
    out += ["## Registered", ""]
    out += [f"- `{c.key}` — {label(c.fm)} [{'; '.join(x for x in (str(c.grade), str(c['kind']), ', '.join(map(str, c['tags'] or []))) if x)}]"
            for c in reg] or ["none"]
    out += ["", "## Excluded", ""]
    out += [f"- `{c.key}` — {label(c.fm)} [{(c['excluded'] or {}).get('reason') if isinstance(c['excluded'], dict) else None}]"
            for c in exc] or ["none"]
    return "\n".join(out) + "\n"


# --- the check --------------------------------------------------------------------

def validate(cfg, cards, broken, today):
    problems = list(broken)
    grades, copies, origins = Counter(), Counter(), Counter()
    idents, stamps, by_hand, anchors = defaultdict(list), [], [], Counter()

    def bad(code, c, msg):
        problems.append({"code": code, "key": c.key if c else None, "path": rel(cfg, c.path) if c else None, "msg": msg})

    for c in cards.values():
        key = c["key"]
        if not KEY_RE.match(c.key):
            bad("L1", c, f"file name {c.path.name!r} is not lowercase letters, digits and hyphens")
        if key != c.key:
            bad("L1", c, f"key {key!r} is not the file's name")
        for k in FIELDS:
            if k not in c.fm:
                bad("L2", c, f"missing field {k}")
        for k in c.fm:
            if k not in FIELDS + OPTIONAL:
                bad("L2", c, f"unknown field {k}")
        for k in LISTS:
            if k in c.fm and not isinstance(c[k], list):
                bad("L2", c, f"{k} is not a list")
            elif k in c.fm and not all(isinstance(x, str) for x in c[k]):
                bad("L2", c, f"{k} holds an item that is not a string (quote it)")
        for k, subs in MAPS.items():
            v = c[k]
            if v is None and k in ("excluded", "copy", "verified"):
                continue
            if k in c.fm and (not isinstance(v, dict) or set(v) - set(subs)):
                bad("L2", c, f"{k} is not a block of {', '.join(subs)}")
        if c["kind"] not in cfg.kinds:
            bad("L2", c, f"kind {c['kind']!r} not in {cfg.kinds}")
        if not c["title"]:
            bad("L2", c, "a card needs a title")
        if c["year"] is not None and not isinstance(c["year"], int):
            bad("L2", c, f"year {c['year']!r} is not a number")
        if c["seeded"] not in (True, False):
            bad("L2", c, "seeded is true or false")
        for f in IDENTS:
            if c[f]:
                idents[(f, str(c[f]).lower())].append(c.key)
        md = c["metadata"] if isinstance(c["metadata"], dict) else {}
        if not md.get("from") or not md.get("on"):
            bad("L2", c, "metadata says where the fields came from and when (metadata.from, metadata.on)")
        origins["hand" if md.get("from") == "hand" else "resolver"] += 1
        if isinstance(c["verified"], dict):
            if not c["verified"].get("on") or not c["verified"].get("by"):
                bad("L2", c, "a verify stamp carries its date and the resolver that answered (verified.on, verified.by)")
            else:
                stamps.append(str(c["verified"]["on"]))
        r = c["read"] if isinstance(c["read"], dict) else {}
        g = r.get("grade")
        grades[(c["state"], g)] += 1
        if g not in GRADES:
            bad("L4", c, f"read grade {g!r} not in {GRADES}")
        elif g == "ungraded" and c["seeded"] is not True:
            bad("L4", c, "only a seeded card may be ungraded")
        elif g == "parts" and not r.get("what"):
            bad("L4", c, "a work read in parts says which parts (read.what)")
        elif g in ("skimmed", "parts", "full") and not r.get("on") and c["seeded"] is not True:
            bad("L4", c, "a read carries the date it was made (read.on); only a seeded card's read may be undated")
        if c["via"] is not None and (not isinstance(c["via"], str) or c["via"] == c.key or c["via"] not in cards):
            bad("L5", c, f"via names {c['via']!r}, which is not another card")
        for o in c["related"] if isinstance(c["related"], list) else []:
            if o == c.key or o not in cards:
                bad("L5", c, f"related names {o!r}, which is not another card")
            elif c.key not in (cards[o]["related"] or []):
                bad("L5", c, f"related to {o}, which does not name it back")
        for k in sorted(set(cfg.cite_re.findall(c.body))):
            if k not in cards:
                bad("L5", c, f"the body cites {cfg.cite_prefix}{k}, which is not a card")
        exs, wrong = parse_extracts(sections(c.body).get("Extracts", ""))
        for msg in wrong:
            bad("L16", c, msg)
        for e in exs:
            if not ISO.match(e["checked"]) or e["checked"] > today:
                bad("L16", c, f"extract {e['id']}: checked {e['checked']!r} is not a date, or is in the future")
            how, said = anchor(cfg, c, e)
            anchors[how if how != "unanchored" else "unanchored: " + said.split(":")[0]] += 1
            if how == "fail":
                bad("L15", c, f"extract {e['id']}: {said}")
        if exs and c.grade == "unread" and not c["via"]:
            bad("L16", c, "the card is graded unread and carries an extract: read the work, or name the card it is known through (via)")
        for k, i in sorted(set(cfg.cite_ex_re.findall(c.body))):
            if k in cards and i not in {e["id"] for e in parse_extracts(sections(cards[k].body).get("Extracts", ""))[0]}:
                bad("L5", c, f"the body cites {cfg.cite_prefix}{k}#{i}, and {k} has no extract {i}")
        cp = c["copy"]
        if isinstance(cp, dict):
            if not cp.get("path") or not cp.get("sha256"):
                bad("L6", c, "copy needs a path and a sha256")
            elif not cfg.store:
                bad("L6", c, "a copy is recorded and the project names no store")
            else:
                f = (cfg.root / str(cp["path"])).resolve()
                home = cfg.kept if cfg.kept and not cp.get("from") else cfg.store
                home_name = cfg.kept_name if home is cfg.kept else cfg.store_name
                if home.resolve() not in f.parents:
                    bad("L6", c, f"copy {cp['path']} is outside {home_name}"
                        + (" (a copy with no address is kept there, tracked)" if home is cfg.kept else " (a copy with an address is kept in the store)"))
                elif not f.is_file():
                    copies["absent"] += 1
                elif file_sha256(f) != cp["sha256"]:
                    bad("L6", c, f"copy {cp['path']} does not match its recorded hash")
                else:
                    copies["present"] += 1
                if not cp.get("from"):
                    by_hand.append(c.key)
                if cp.get("text") == "none":
                    copies["no_text"] += 1
        ex = c["excluded"]
        if c["state"] not in STATES:
            bad("L7", c, f"state {c['state']!r} not in {STATES}")
        elif c["state"] == "excluded" and not (isinstance(ex, dict) and ex.get("reason") and ex.get("on")):
            bad("L7", c, "an excluded card carries its reason and its date")
        elif c["state"] == "registered" and ex is not None:
            bad("L7", c, "a registered card carries no exclusion")
        dates = [("created", c["created"]), ("read.on", r.get("on"))]
        dates += [(f"{k}.{s}", c[k].get(s)) for k, s in (("metadata", "on"), ("verified", "on"), ("excluded", "on"), ("copy", "fetched"))
                  if isinstance(c[k], dict)]
        for name, v in dates:
            if v is not None and not ISO.match(str(v)):
                bad("L8", c, f"{name} is not an ISO date")
            elif v is not None and str(v) > today:
                bad("L8", c, f"{name} is in the future")
        if not c["created"]:
            bad("L8", c, "a card carries the date it was created")
        if c.body and cfg.reflow(c.body) != c.body:
            bad("L9", c, "body is not one sentence per line (reflow changes it)")
        heads = re.findall(r"^(#+) (.+?)\s*$", c.body, re.M)
        if [h for lvl, h in heads if lvl == "##"] != list(SECTIONS) or any(lvl in ("#",) for lvl, _ in heads) \
                or sections(c.body).get("", "").strip():
            bad("L10", c, "the body is `## Notes` then `## Extracts`, with nothing before them and no other heading at that level")
    for (f, v), ks in idents.items():
        if len(ks) > 1:
            problems.append({"code": "L3", "key": None, "path": None, "msg": f"{f} {v} on {', '.join(ks)}"})
    files = defaultdict(list)
    for c in cards.values():
        if c["file"]:
            files[Path(rel(cfg, cfg.root / str(c["file"]))).as_posix()].append(c.key)
            if not (cfg.root / str(c["file"])).is_file():
                bad("L17", c, f"the card names the file {c['file']}, which is not in the tree")
            if c["kind"] not in cfg.internal_kinds:
                bad("L17", c, f"a card naming a file of the project is of an internal kind, one of {cfg.internal_kinds}")
            if c["copy"] is not None:
                bad("L17", c, "an internal document's tracked file is its copy: it records no other")
        elif c["kind"] in cfg.internal_kinds:
            bad("L17", c, f"a card of kind {c['kind']} names the project's file it stands for (file)")
    for f, ks in files.items():
        if len(ks) > 1:
            problems.append({"code": "L17", "key": None, "path": f, "msg": f"the file has {len(ks)} cards: {', '.join(ks)}"})
    uncarded = []
    for d in cfg.internal_dirs:
        for f in sorted((cfg.root / d).rglob("*")) if (cfg.root / d).is_dir() else []:
            if f.is_file() and not any(part.startswith(".") for part in f.relative_to(cfg.root / d).parts) and Path(rel(cfg, f)).as_posix() not in files:
                uncarded.append(rel(cfg, f))
                problems.append({"code": "L17", "key": None, "path": rel(cfg, f),
                                 "msg": "a document of the project with no card: register it with its kind and --file"})
    tied, tied_grades = set(), Counter()
    ents = tied_entries(cfg, cards)
    for e in ents:
        where = f"{e['doc']}:{e['line']}"
        if not e["keys"]:
            inside = ties(cards, e, internal=True)
            problems.append({"code": "L12", "key": None, "path": where,
                             "msg": (f"this reference entry names an internal document ({', '.join(inside)}), which a bound document does not cite: "
                                     if inside else "no card agrees with this reference entry on title, first author and year: ") + e["entry"][:110]})
        elif len(e["keys"]) > 1:
            problems.append({"code": "L12", "key": None, "path": where,
                             "msg": f"this reference entry agrees with {len(e['keys'])} cards ({', '.join(e['keys'])}): {e['entry'][:90]}"})
        else:
            tied.add(e["keys"][0])
    for doc, n, line in unread_lines(cfg):
        problems.append({"code": "L12", "key": None, "path": f"{doc}:{n}",
                         "msg": "this line under the references heading is not read as an entry (authors, then the year in "
                                "parentheses, one entry per line): " + line.strip()[:90]})
    for k in sorted(tied):
        tied_grades[str(cards[k].grade)] += 1
        if cards[k].grade == "unread" and not cards[k]["via"]:
            bad("L13", cards[k], "a work a document cites is graded unread and is known through no other card (read it, or name `via`)")
    if not cfg.index.is_file():
        problems.append({"code": "L11", "key": None, "path": rel(cfg, cfg.index), "msg": "index missing — run `library index`"})
    elif cfg.index.read_text(encoding="utf-8") != render_index(cfg, cards):
        problems.append({"code": "L11", "key": None, "path": rel(cfg, cfg.index),
                         "msg": f"{rel(cfg, cfg.index)} is stale — run `library index`"})
    try:
        watches, cands = load_watch(cfg)
    except Refused as e:
        watches, cands = [], []
        problems.append({"code": "L14", "key": None, "path": rel(cfg, cfg.watch_file), "msg": str(e)})
    names = Counter(w.get("name") for w in watches)
    for w in watches:
        where = {"code": "L14", "key": None, "path": rel(cfg, cfg.watch_file)}
        if not w.get("name") or not KEY_RE.match(str(w["name"])) or names[w["name"]] > 1:
            problems.append(dict(where, msg=f"watch name {w.get('name')!r} is missing, repeated, or not lowercase letters, digits and hyphens"))
        if w.get("kind") not in WATCH_KINDS or set(w) - set(WATCH_FIELDS):
            problems.append(dict(where, msg=f"watch {w.get('name')}: kind {w.get('kind')!r} not in {WATCH_KINDS}, or a field that is not a watch's"))
        elif w["kind"] in ("citing", "related") and w.get("card") not in cards:
            problems.append(dict(where, msg=f"watch {w.get('name')} names the card {w.get('card')!r}, which is not a card"))
        elif w["kind"] in ("arxiv", "github") and not w.get("query"):
            problems.append(dict(where, msg=f"watch {w.get('name')} has no query"))
        if not ISO.match(str(w.get("since") or "")) or str(w["since"]) > today:
            problems.append(dict(where, msg=f"watch {w.get('name')}: since {w.get('since')!r} is not a date, or is in the future"))
    for c in cands:
        where = {"code": "L14", "key": None, "path": rel(cfg, cfg.cand_file)}
        if not c.get("ids") or c.get("state") not in CAND_STATES or set(c) - set(CAND_FIELDS):
            problems.append(dict(where, msg=f"candidate {c.get('ids')}: no identifier, a state not in {CAND_STATES}, or a field that is not a candidate's"))
        elif c["state"] == "excluded" and not c.get("reason"):
            problems.append(dict(where, msg=f"candidate {c['ids'][0]} is set aside and gives no reason"))
    coverage = {"cards": len(cards),
                "watches": len(watches), "watch_seen": sum(len(w.get("seen") or []) for w in watches),
                "watch_never_run": sum("seen" not in w for w in watches),
                "candidates": sum(c.get("state") == "proposed" for c in cands),
                "candidates_excluded": sum(c.get("state") == "excluded" for c in cands),
                "registered": {g: grades[("registered", g)] for g in GRADES if grades[("registered", g)]},
                "excluded": sum(n for (s, _), n in grades.items() if s == "excluded"),
                "copies_present": copies["present"], "copies_absent": copies["absent"],
                "copies_no_text": copies["no_text"], "copies_by_hand": sorted(by_hand),
                "internal": len(files), "internal_dirs": list(cfg.internal_dirs),
                "extracts": sum(anchors.values()), "extracts_anchored": anchors["anchored"],
                "extracts_unanchored": {k[len("unanchored: "):]: n for k, n in sorted(anchors.items()) if k.startswith("unanchored: ")},
                "store": cfg.store_name, "kept": cfg.kept_name, "reflow": cfg.reflow_source, "scan": list(cfg.scan),
                "from_resolver": origins["resolver"], "from_hand": origins["hand"],
                "verified": len(stamps), "verified_oldest": min(stamps) if stamps else None,
                "entries": len(ents), "entry_docs": len({e["doc"] for e in ents}), "entry_globs": list(cfg.entry_docs),
                "tied_cards": len(tied), "tied_grades": {g: tied_grades[g] for g in GRADES if tied_grades[g]},
                "untied_cards": sum(1 for k, c in cards.items() if c["state"] == "registered" and k not in tied)}
    return problems, coverage


# --- writers ----------------------------------------------------------------------

def cmd_register(cfg, cards, a, today):
    if a.kind not in cfg.kinds:
        raise Refused(f"kind {a.kind!r} not in {cfg.kinds}")
    grade = a.read or ("ungraded" if a.seed else "unread")
    if grade not in GRADES:
        raise Refused(f"read grade {grade!r} not in {GRADES}")
    if grade == "ungraded" and not a.seed:
        raise Refused("a new card is graded; `ungraded` is for a seeded card (--seed)")
    if grade == "parts" and not a.read_what:
        raise Refused("a work read in parts says which parts (--read-what)")
    if a.read_on and (not ISO.match(a.read_on) or a.read_on > today):
        raise Refused(f"--read-on {a.read_on!r} is not a date, or is in the future")
    try:
        year = int(a.year) if a.year else None
    except ValueError:
        raise Refused(f"year {a.year!r} is not a number")
    authors = [x.strip() for x in a.author or []]
    key = a.key or make_key(cards, authors, year, a.title)
    if not KEY_RE.match(key):
        raise Refused(f"key {key!r} is not lowercase letters, digits and hyphens")
    if key in cards or (cfg.cards / f"{key}.md").exists():
        raise Refused(f"key {key} is taken")
    ids = {f: norm_ident(f, getattr(a, f)) if getattr(a, f) else None for f in IDENTS}
    for c in cards.values():
        for f, v in ids.items():
            if v and c[f] and str(c[f]).lower() == v.lower():
                raise Refused(f"{f} {v} is already {c.key}")
    if a.via and (a.via not in cards):
        raise Refused(f"--via names {a.via}, which is not a card")
    if a.file:
        if not (cfg.root / a.file).is_file():
            raise Refused(f"--file {a.file}: no such file in the tree")
        a.file = Path(rel(cfg, cfg.root / a.file)).as_posix()
        if a.kind not in cfg.internal_kinds:
            raise Refused(f"a card naming a file of the project is of an internal kind, one of {cfg.internal_kinds}")
        if any(c["file"] and Path(rel(cfg, cfg.root / str(c["file"]))).as_posix() == a.file for c in cards.values()):
            raise Refused(f"{a.file} has a card already")
    elif a.kind in cfg.internal_kinds:
        raise Refused(f"a card of kind {a.kind} names the project's file it stands for (--file)")
    read = grade in ("skimmed", "parts", "full")
    fm = {"key": key, "state": "registered", "excluded": None, "kind": a.kind, "title": a.title,
          "authors": authors, "year": year, "venue": a.venue, **ids, "url": a.url,
          "metadata": {"from": "hand", "on": today, "typed": None}, "verified": None,
          "read": {"grade": grade, "on": (a.read_on or today) if read else None, "what": a.read_what},
          "via": a.via, "copy": None, "related": [], "tags": a.tag or [], "seeded": bool(a.seed), "created": today}
    if a.file:
        fm["file"] = a.file
    notes = "\n\n".join(([read_file(a.notes).strip()] if a.notes else []) + list(a.note or []))
    card = Card(cfg.cards / f"{key}.md", fm, body_of(notes))
    write_card(cfg, card)
    return [card], []


def read_file(path):
    p = Path(path)
    if not p.is_file():
        raise Refused(f"file not found: {path}")
    return p.read_text(encoding="utf-8")


def cmd_read(cfg, cards, a, today):
    c = by_ref(cards, a.ref)
    if a.grade not in GRADES or a.grade == "ungraded":
        raise Refused(f"read grade {a.grade!r} not in {GRADES[1:]}")
    old = c["read"] if isinstance(c["read"], dict) else {}
    what = a.what or (old.get("what") if a.grade == "parts" else None)
    if a.grade == "parts" and not what:
        raise Refused("a work read in parts says which parts (--what)")
    if a.undated and c["seeded"] is not True:
        raise Refused("only a seeded card's read may be undated: a read made now carries its date")
    if a.on and (not ISO.match(a.on) or a.on > today):
        raise Refused(f"--on {a.on!r} is not a date, or is in the future")
    c.fm["read"] = {"grade": a.grade, "on": None if a.grade == "unread" or a.undated else (a.on or today), "what": what}
    if a.via:
        via = by_ref(cards, a.via)
        if via.key == c.key:
            raise Refused("a work is not known through itself")
        c.fm["via"] = via.key
    if a.note:
        add_note(c, today, a.note)
    write_card(cfg, c)
    return [], [c]


def cmd_note(cfg, cards, a, today):
    """A dated note and tags added to a card: the body's own writer, so that a load never edits a card
    as text.  A note is ours and is dated."""
    c = by_ref(cards, a.ref)
    note = "\n\n".join(([read_file(a.notes).strip()] if a.notes else []) + [x.strip() for x in a.note or []])
    tags = [t for t in a.tag or [] if t not in (c["tags"] or [])]
    if not (note or tags):
        raise Refused("nothing to add: give a note (--note, --notes FILE) or a new tag (--tag); an extract is written by `library extract`")
    if note:
        add_note(c, today, note)
    if tags:
        c.fm["tags"] = list(c["tags"] or []) + tags
    write_card(cfg, c)
    return [], [c]


def cmd_relate(cfg, cards, a, today):
    x, y = by_ref(cards, a.a), by_ref(cards, a.b)
    if x.key == y.key:
        raise Refused("a card is not related to itself")
    for m, o in ((x, y), (y, x)):
        others = [k for k in (m["related"] or []) if k != o.key]
        m.fm["related"] = others if a.drop else sorted(others + [o.key])
        write_card(cfg, m)
    return [], [x, y]


def cmd_exclude(cfg, cards, a, today):
    c = by_ref(cards, a.ref)
    if a.undo:
        if c["state"] != "excluded":
            raise Refused(f"{c.key} is not excluded")
        c.fm.update({"state": "registered", "excluded": None})
    else:
        if not a.reason:
            raise Refused("an exclusion says why (--reason)")
        c.fm.update({"state": "excluded", "excluded": {"on": today, "reason": a.reason}})
    write_card(cfg, c)
    return [], [c]


# --- kept copies: a file in the store, its text by page, the search of that text -----

TEXT_FLOOR = 20  # the characters a page must average for a copy to count as having text
PDF_MAGIC, GZ_MAGIC = b"%PDF", b"\x1f\x8b"


def copy_file(cfg, c):
    """Where a card's text is read from: an internal document's own tracked file, else the kept copy."""
    if c["file"]:
        return cfg.root / str(c["file"])
    cp = c["copy"]
    return (cfg.root / str(cp["path"])) if isinstance(cp, dict) and cp.get("path") else None


def markdown_units(text):
    """A Markdown document as units: cut at its headings of the first two levels, each labelled by its heading."""
    units, label, cur, fence = [], "front matter", [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            fence = not fence
        m = None if fence else re.match(r"^#{1,2}\s+(.+?)\s*#*\s*$", line)
        if m:
            if "".join(cur).strip():
                units.append((label, "\n".join(cur)))
            label, cur = re.sub(r"[*_`\\]", "", m.group(1)).strip()[:80], [line]
        else:
            cur.append(line)
    if "".join(cur).strip():
        units.append((label, "\n".join(cur)))
    return units


def form_of(data, name=""):
    """What a file is, by its first bytes and then its name: `pdf`, `source` (a TeX file or an archive
    of them, as arXiv serves a work's source), `page` (an HTML page, never a copy), else `text`."""
    if data[:4] == PDF_MAGIC or PDF_MAGIC in data[:1024]:
        return "pdf"
    if data[:2] == GZ_MAGIC or data[257:262] == b"ustar" or name.lower().endswith((".tex", ".tar", ".tgz")):
        return "source"
    if data.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")):
        return "page"
    return "text"


def suffix_for(data, name):
    form = form_of(data, name)
    if form == "pdf":
        return ".pdf"
    if data[:2] == GZ_MAGIC:
        return ".gz"
    return "".join(Path(name).suffixes[-1:]) or (".tex" if form == "source" else ".txt")


def tex_files(data):
    """The TeX files of a source copy: a tar of them or one file, gzip'd or plain."""
    if data[:2] == GZ_MAGIC:
        try:
            gz = zlib.decompressobj(16 + zlib.MAX_WBITS)
            data = gz.decompress(data, MAX_BYTES)
        except zlib.error:
            return {}
        if gz.unconsumed_tail:  # it unpacks past the cap a download has: not a source anyone posted
            return {}
    if data[:4] == PDF_MAGIC:
        return {}
    try:
        files = {}
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            for m in tar.getmembers():
                if m.isfile() and m.name.lower().endswith(".tex") and m.size < 8_000_000:
                    files[m.name] = tar.extractfile(m).read().decode("utf-8", "replace")
        return files
    except tarfile.TarError:
        text = data.decode("utf-8", "replace")
        return {"main.tex": text} if "\\" in text else {}


def tex_units(files):
    r"""A TeX source as parts: the main file with its inputs put in and its comments dropped, cut at every
    \section, each part labelled by its section's title; with no main file, one part per file."""
    def clean(t):
        return re.sub(r"(?<!\\)%.*", "", t)

    mains = sorted((n for n, t in files.items() if "\\documentclass" in t or "\\documentstyle" in t),
                   key=lambda n: ("\\begin{document}" not in files[n], -len(files[n]), n))
    if not mains:
        return [(n, clean(t)) for n, t in sorted(files.items())]
    by_stem = {re.sub(r"\.tex$", "", n.lstrip("./")): n for n in files}

    def expand(text, depth=0):
        def put(m):
            n = by_stem.get(re.sub(r"\.tex$", "", m.group(1).strip().lstrip("./")))
            return expand(clean(files[n]), depth + 1) if n and depth < 6 else m.group(0)
        return re.sub(r"\\(?:input|include)\s*\{([^}]+)\}", put, text)

    body = expand(clean(files[mains[0]]))
    cuts = [(m.start(), m.end()) for m in re.finditer(r"\\section\*?\s*(?:\[[^\]]*\])?\s*\{", body)]
    if not cuts:
        return [("the whole source", body)]
    units = [("front matter", body[:cuts[0][0]])] if body[:cuts[0][0]].strip() else []
    for n, ((a, e), (b, _)) in enumerate(zip(cuts, cuts[1:] + [(len(body), 0)]), 1):
        depth, i = 1, e
        while i < b and depth:
            depth += {"{": 1, "}": -1}.get(body[i], 0)
            i += 1
        title = re.sub(r"\s+", " ", body[e:i - 1]).strip()[:80]
        units.append((f"§{n} {title}", body[a:b]))
    return units


def extract_units(cfg, path):
    """A copy's text as units — a PDF's pages through the command the project names, a TeX source's
    sections, any other file's pages at its form feeds — with the copy's form and whether it has text."""
    data = path.read_bytes()
    form = form_of(data, path.name)
    if form == "pdf":
        if not cfg.text_command:
            raise Refused("the project names no command that prints a PDF's text ([copy] text_command)")
        try:
            r = subprocess.run([x.replace("{file}", str(path)) for x in cfg.text_command], capture_output=True, timeout=900)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise Refused(f"the text command did not run: {e}")
        if r.returncode != 0:
            raise Refused(f"the text command failed on {path.name}: {r.stderr.decode('utf-8', 'replace').strip()[:200]}")
        pages = r.stdout.decode("utf-8", "replace").split("\f")
    elif form == "source":
        units = tex_units(tex_files(data))
        return form, units, bool(units)
    else:
        pages = data.decode("utf-8", "replace").split("\f")
    if len(pages) > 1 and not pages[-1].strip():
        pages.pop()
    units = [(f"p. {i}", t) for i, t in enumerate(pages, 1)]
    return form, units, sum(ch.isalnum() for _, t in units for ch in t) >= TEXT_FLOOR * len(units)


def write_text(cfg, key, units):
    d = cfg.store / key / "text"
    if d.is_dir():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for i, (_, t) in enumerate(units, 1):
        (d / f"{i:04d}.txt").write_text(t, encoding="utf-8")
    (d / "units.json").write_text(json.dumps([lab for lab, _ in units], ensure_ascii=False), encoding="utf-8")


def read_units(cfg, c):
    """The kept text of a card's copy, unit by unit; extracted now where the store holds the copy and
    not yet its text, the text being derived and never recorded."""
    f = copy_file(cfg, c)
    if f is None:
        raise Refused(f"{c.key} has no recorded copy")
    if c["file"]:
        if not f.is_file():
            raise Refused(f"{c.key}: its file {c['file']} is not in the tree")
        if f.suffix.lower() in (".md", ".markdown", ".qmd"):
            return markdown_units(f.read_text(encoding="utf-8", errors="replace"))
        return extract_units(cfg, f)[1]
    if not f.is_file():
        raise Refused(f"{c.key}: its copy {c['copy']['path']} is not on disk — `library restore {c.key}`")
    if not cfg.store:
        raise Refused(f"{c.key}: a copy is recorded and the project names no store ([paths] store)")
    d = cfg.store / c.key / "text"
    if not (d / "units.json").is_file():
        write_text(cfg, c.key, extract_units(cfg, f)[1])
    labels = json.loads((d / "units.json").read_text(encoding="utf-8"))
    return [(lab, (d / f"{i:04d}.txt").read_text(encoding="utf-8")) for i, lab in enumerate(labels, 1)]


def store_copy(cfg, c, data, name, today, source, version):
    """The bytes kept as the card's copy, their text extracted, the card's `copy` block written."""
    if not cfg.store:
        raise Refused("the project names no store ([paths] store): there is nowhere to keep a copy")
    if form_of(data, name) == "page":
        raise Refused("that is an HTML page, not a copy of the work")
    d, old = (cfg.kept if cfg.kept and not source else cfg.store) / c.key, copy_file(cfg, c)
    f = d / ("copy" + suffix_for(data, name))
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / ("copy.new" + suffix_for(data, name))
    tmp.write_bytes(data)
    try:
        form, units, has = extract_units(cfg, tmp)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    # the copy replaced goes only from the store or the kept directory: a recorded path elsewhere is a
    # problem the check reports, never a file this command deletes
    if (old is not None and old.is_file() and old.resolve() != f.resolve()
            and any(h and old.resolve().is_relative_to(h.resolve()) for h in (cfg.store, cfg.kept))):
        old.unlink()
    os.replace(tmp, f)
    write_text(cfg, c.key, units)
    c.fm["copy"] = {"path": rel(cfg, f), "sha256": hashlib.sha256(data).hexdigest(), "fetched": today, "version": version,
                    "from": source, "pages": len(units), "text": "yes" if has else "none"}
    write_card(cfg, c)
    return form, len(units), has


def copy_line(c, form, n, has):
    what = {"pdf": "page(s)", "source": "part(s) of TeX source", "text": "page(s) of text"}[form]
    return (f"{c.key}: kept {c['copy']['path']} — {n} {what}"
            + ("" if has else "; NO TEXT in it: read its pages as images")
            + ("" if c["copy"]["from"] else "; obtained by hand, with no address to fetch it from again"))


def cmd_keep(cfg, cards, a, today):
    """A file obtained by hand taken into the store as the card's copy."""
    c = by_ref(cards, a.ref)
    src = Path(a.file)
    if not src.is_file():
        raise Refused(f"file not found: {a.file}")
    if c["file"]:
        raise Refused(f"{c.key} is an internal document: its tracked file {c['file']} is its copy")
    if isinstance(c["copy"], dict) and not a.replace:
        raise Refused(f"{c.key} has a copy recorded ({c['copy']['path']}); --replace takes this file in its place")
    if cfg.kept and not a.source and not a.redistributable:
        # The kept directory is tracked, so whoever receives the repository receives the copy.
        raise Refused(f"a copy with no address goes into {cfg.kept_name}, which is tracked and travels with the "
                      "repository: pass --redistributable when the project may redistribute this file, or --from URL "
                      "to record where it can be fetched again and keep it in the store")
    if a.on and not ISO.match(a.on):
        raise Refused(f"--on {a.on!r} is not a date")
    store_copy(cfg, c, src.read_bytes(), src.name, a.on or today, a.source, a.version)
    if a.move and src.resolve() != copy_file(cfg, c).resolve():
        src.unlink(missing_ok=True)
    return [], [c]


def open_text_index(cfg, cards):
    """The full-text index over the kept text, one row per unit, rebuilt when any copy's text changed;
    the rows themselves where SQLite has no FTS5."""
    rows, held = [], []
    for k, c in sorted(cards.items()):
        f = copy_file(cfg, c)
        if f is None or not f.is_file():
            continue
        try:
            units = read_units(cfg, c)
        except Refused:
            continue
        u = f if c["file"] else cfg.store / c.key / "text" / "units.json"
        held.append((k, u.stat().st_mtime_ns, u.stat().st_size))
        rows += [(k, i, lab, t) for i, (lab, t) in enumerate(units, 1)]
    sig = hashlib.sha256(json.dumps([INDEX_VERSION] + held).encode()).hexdigest()
    con = connect_index(cfg)
    row = con.execute("select v from meta where k = 'textsig'").fetchone()
    if row and row[0] == sig:
        return con, rows
    try:
        con.execute("drop table if exists pages")
        con.execute("create virtual table pages using fts5(key unindexed, unit unindexed, label unindexed, text, "
                    "tokenize = 'porter unicode61 remove_diacritics 2')")
    except sqlite3.OperationalError:
        con.close()
        return None, rows
    con.executemany("insert into pages values (?, ?, ?, ?)", rows)
    con.execute("insert or replace into meta values ('textsig', ?)", (sig,))
    con.commit()
    return con, rows


def find_text(cfg, cards, words):
    """The units of kept text holding every word, best first: (key, unit number, label, snippet)."""
    terms = [t for w in words for t in re.findall(r"\w+", w)]
    if not terms:
        raise Refused("a search of the kept text needs words")
    con, rows = open_text_index(cfg, cards)
    if con is not None:
        hits = con.execute("select key, unit, label, snippet(pages, 3, '[', ']', ' … ', 24) from pages where pages match ? "
                           "order by bm25(pages)", (" ".join(f'"{t}"' for t in terms),)).fetchall()
        con.close()
        return "fts5 (stemmed, diacritics folded, every word on one page)", [(k, int(u), lab, re.sub(r"\s+", " ", sn)) for k, u, lab, sn in hits]
    want, hits = [fold(t) for t in terms], []
    for k, u, lab, t in rows:
        low = fold(t)
        if all(re.search(r"\b%s\b" % re.escape(w), low) for w in want):
            at = low.find(want[0])
            hits.append((k, u, lab, re.sub(r"\s+", " ", t[max(0, at - 80):at + 120])))
    return "words (this SQLite has no FTS5: whole words, diacritics folded, no stemming)", hits


# --- extracts: what a work says at a place, addressed and anchored in the kept text ---
#
#   **id** — locator — checked DATE, edition
#   Quote: "the work's own words"
#   Restated: what it says there, in ours
#   Caveat: the author's own caveat
#   Rule: what may be claimed of it
#   Unanchored: why the kept copy cannot bear it out
#
# One block to an extract, a blank line between blocks; a line that opens with no label continues the
# field above it.  An extract is cited as `key#id`.

EX_HEAD_START = re.compile(r"^\*\*[a-z0-9][a-z0-9-]*\*\* — ")
EX_HEAD = re.compile(r"^\*\*([a-z0-9][a-z0-9-]*)\*\* — (.+) — checked (\d{4}-\d{2}-\d{2})(?:, (.+))?$")
EX_FIELDS = ("Quote", "Restated", "Caveat", "Rule", "Unanchored")
EX_LABEL = re.compile(r"^(%s): (.*)$" % "|".join(EX_FIELDS))
LOC_NUM = re.compile(r"(theorem|proposition|lemma|corollary|definition|remark|equation|eq\.|section|§)\s*\(?(\d+(?:\.\d+)*)\)?", re.I)


def parse_extracts(text):
    """The extracts of a card's `## Extracts` section, and what is wrong with its form."""
    out, bad, cur, field = [], [], None, None
    for line in text.split("\n"):
        if not line.strip():
            field = None
            continue
        m = EX_HEAD.match(line)
        if m:
            cur = {"id": m.group(1), "at": m.group(2), "checked": m.group(3), "edition": m.group(4), "fields": []}
            out.append(cur)
            field = None
            continue
        if cur is None:
            bad.append(f"text before the first extract's head line: {line[:60]!r}")
            continue
        m = EX_LABEL.match(line)
        if m:
            field = [m.group(1), m.group(2)]
            cur["fields"].append(field)
        elif field is not None:
            field[1] += "\n" + line
        else:
            bad.append(f"extract {cur['id']}: a line with no label and no field above it: {line[:60]!r}")
    ids = Counter(e["id"] for e in out)
    bad += [f"extract id {i} twice" for i, n in ids.items() if n > 1]
    for e in out:
        names = [f for f, _ in e["fields"]]
        if "Quote" not in names and "Restated" not in names:
            bad.append(f"extract {e['id']} says nothing: it needs a Quote or a Restated line")
        for f in ("Restated", "Caveat", "Rule", "Unanchored"):
            if names.count(f) > 1:
                bad.append(f"extract {e['id']}: {f} twice")
    return out, bad


def ex_get(e, name):
    return [v for f, v in e["fields"] if f == name]


def render_extract(e):
    head = f"**{e['id']}** — {e['at']} — checked {e['checked']}" + (f", {e['edition']}" if e.get("edition") else "")
    return "\n".join([head] + [f"{f}: {v}" for f, v in e["fields"]])


def text_words(t, tex):
    """A text as the anchor check compares it: lowercase words, diacritics folded; a TeX source loses its
    mathematics, its commands and its braces first, and a PDF's line-end hyphens are closed."""
    if tex:
        # the source's own macros of no argument stand for words: they are put back before the commands go
        macros = dict(re.findall(r"\\(?:re)?newcommand\*?\{?\\([a-zA-Z]+)\}?\{((?:[^{}]|\{[^{}]*\})*)\}", t))
        macros.update(re.findall(r"\\def\\([a-zA-Z]+)\{((?:[^{}]|\{[^{}]*\})*)\}", t))
        for _ in range(2):
            for name, body in macros.items():
                t = re.sub(r"\\%s(?![a-zA-Z])" % name, lambda m: " " + body + " ", t)
        t = re.sub(r"\$[^$]*\$|\\\([^)]*\\\)|\\\[[^\]]*\\\]", " ", t)
        t = re.sub(r"\\[a-zA-Z]+\*?|\\.", "", t).replace("~", " ")
        t = re.sub(r"[{}]", "", t)
    else:
        t = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", t)
    return " " + " ".join(re.findall(r"[^\W_]+", fold(t))) + " "


def quote_pieces(q):
    """The stretches of a quotation that must stand whole in the text: it is cut at its mathematics, its
    ellipses and its brackets, and a stretch under three words is too short to look for."""
    q = re.sub(r"[{}]", "", re.sub(r"\\[a-zA-Z]+\*?", "", q.strip().strip('"“”')))  # a quotation typed from a TeX source
    parts = re.split(r"`[^`]*`|\$[^$]*\$|…|\.\.\.|\[[^\]]*\]|\*\*", q)
    pieces = [" ".join(re.findall(r"[^\W_]+", fold(x))) for x in parts]
    long = [x for x in pieces if len(x.split()) >= 3]
    return long or [x for x in [" ".join(w for x in pieces for w in x.split())] if x]


def anchor(cfg, c, e):
    """Whether the kept copy bears an extract out: ("anchored", how), ("unanchored", why), or
    ("fail", what is missing).  Every quotation must stand in the kept text, and a numbered locator must
    occur in it; a TeX source carries no numbers of its own, so there the quotation alone is checked."""
    why = ex_get(e, "Unanchored")
    if why:
        return "unanchored", "declared: " + why[0].split("\n")[0]
    f = copy_file(cfg, c)
    if f is None:
        return "unanchored", "no copy is kept"
    if not f.is_file():
        return "unanchored", "the copy is not on disk"
    if not c["file"] and c["copy"].get("text") == "none":
        return "unanchored", "the copy has no text in it"
    try:
        units = read_units(cfg, c)
    except Refused:
        return "unanchored", "the copy's text could not be read"
    tex = form_of(f.read_bytes()[:512], f.name) == "source"
    words = text_words("\n".join(t for _, t in units), tex)
    for q in ex_get(e, "Quote"):
        for piece in quote_pieces(q):
            if f" {piece} " not in words:
                return "fail", f"the quotation is not in the kept text: “{piece[:70]}”"
    unchecked = 0
    for kind, num in LOC_NUM.findall(e["at"]):
        kind = kind.lower().rstrip(".")
        if tex:
            unchecked += 1  # a TeX source carries its numbers nowhere: they are the typesetter's
        elif kind in ("§", "section"):
            if f" {' '.join(num.split('.'))} " not in words:
                return "fail", f"the locator names section {num}, which is not in the kept text"
        else:
            names = {"eq": ("eq", "equation"), "equation": ("eq", "equation")}.get(kind, (kind,))
            num_w = " ".join(num.split("."))
            if not any(f" {n} {num_w} " in words for n in names) and not (kind in ("eq", "equation") and f" {num_w} " in words):
                return "fail", f"the locator names {kind} {num}, which is not in the kept text"
    return "anchored", "the quotation" + ("" if not unchecked else "; a numbered locator cannot be checked in a TeX source") \
        if ex_get(e, "Quote") else ("the locator alone, nothing being quoted" if LOC_NUM.search(e["at"]) and not unchecked else "nothing to check: restated, and no number the copy can show")


def cmd_extract(cfg, cards, a, today):
    """An addressed extract written under a card's Extracts: its id, where the work says it, the words
    quoted or restated, the author's caveat, the rule on what may be claimed, the date and the edition."""
    c = by_ref(cards, a.ref)
    if not KEY_RE.match(a.id):
        raise Refused(f"extract id {a.id!r} is not lowercase letters, digits and hyphens")
    if " — " in a.at or "\n" in a.at:
        raise Refused("a locator is one line and holds no long dash set off by spaces")
    if not (a.quote or a.says):
        raise Refused("an extract says something: give --quote, the work's words, or --says, a restatement in ours")
    on = a.on or today
    if not ISO.match(on) or on > today:
        raise Refused(f"--on {on!r} is not a date, or is in the future")
    if c.grade == "unread" and not c["via"]:
        raise Refused(f"{c.key} is graded unread: read the work first (`library read`), "
                      "or name the card it is known through (`library read --grade unread --via KEY`)")
    sec = sections(c.body)
    have, _ = parse_extracts(sec.get("Extracts", ""))
    if any(e["id"] == a.id for e in have) and not a.replace:
        raise Refused(f"{c.key} has an extract {a.id}; --replace writes this one in its place")
    one = lambda v: " ".join(str(v).split())
    fields = [["Quote", one(q) if one(q).startswith(('"', "“")) else f'"{one(q)}"'] for q in a.quote or []]
    fields += [[n, one(v)] for n, v in (("Restated", a.says), ("Caveat", a.caveat), ("Rule", a.rule), ("Unanchored", a.unanchored)) if v]
    new = {"id": a.id, "at": one(a.at), "checked": on, "edition": one(a.edition) if a.edition else None, "fields": fields}
    kept = [e for e in have if e["id"] != a.id] + [new]
    c.body = cfg.reflow(body_of(sec.get("Notes", ""), "\n\n".join(render_extract(e) for e in kept), sec))
    back, bad = parse_extracts(sections(c.body).get("Extracts", ""))
    if bad or [e["id"] for e in back] != [e["id"] for e in kept]:
        raise Refused("the extract does not read back as written" + (": " + "; ".join(bad) if bad else "")
                      + " — a locator or an edition that reads as two sentences is the usual cause")
    write_card(cfg, c)
    return [], [c]


# --- claims: the sentences of the bound documents that credit themselves against a named work ---

CLAIM_SHAPES = (
    r"\b(?:prov(?:e|es|ed|ing)|resolv(?:e|es|ed|ing)|settl(?:e|es|ed|ing)|establish(?:es|ed|ing)?|clos(?:e|es|ed|ing)|answer(?:s|ed|ing)?"
    r"|bypass(?:es|ed|ing)?|refut(?:e|es|ed|ing)|re-?deriv(?:e|es|ed|ing)|recover(?:s|ed|ing)?|generali[sz](?:e|es|ed|ing)|strengthen(?:s|ed|ing)?"
    r"|sharpen(?:s|ed|ing)?|extend(?:s|ed|ing)?|discharg(?:e|es|ed|ing))\b",
    r"\bthe first\b|\bfor the first time\b|\bto our knowledge\b|\bno prior\b|\bunclaimed\b",
    r"\bis (?:exactly |precisely )?(?:our|this paper's)\b|\bis an instance of\b|\bis the special case\b",
)


def claims(cfg, cards, docs=None):
    """Every claim-shaped sentence of the bound documents that names a carded work, with the extracts
    that card carries: (document, line, key, extract ids, sentence).  A work is named when the first
    author's surname and the year of a card the document's references are tied to both stand in the
    sentence; the references section itself is not read.  A worklist, not a verdict: whether an extract
    bears the sentence out is read by a person."""
    shapes = [re.compile(x, re.I) for x in cfg.claim_shapes]
    by_doc = defaultdict(set)
    for e in tied_entries(cfg, cards):
        by_doc[e["doc"]].update(e["keys"])
    out = []
    for doc, keys in sorted(by_doc.items()):
        if docs and not any(doc == d or doc.endswith("/" + d) or Path(doc).stem == d for d in docs):
            continue
        named = [(k, norm(surname(cards[k]["authors"][0])), str(cards[k]["year"])) for k in sorted(keys)
                 if cards[k]["authors"] and cards[k]["year"]]
        for n, line in enumerate((cfg.root / doc).read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            if re.match(r"^#+\s+%s\s*$" % re.escape(cfg.entry_heading), line):
                break
            if not any(x.search(line) for x in shapes):
                continue
            words = f" {norm(line)} "
            for k, sur, year in named:
                if f" {sur} " in words and year_in(year, words):
                    ids = [e["id"] for e in parse_extracts(sections(cards[k].body).get("Extracts", ""))[0]]
                    out.append({"doc": doc, "line": n, "key": k, "extracts": ids, "sentence": line.strip()})
    return out


# --- online: resolvers answering candidates; nothing below is reached from `check` ---

TYPE_KINDS = {"journal-article": "article", "article-journal": "article", "article": "article",
              "proceedings-article": "article", "paper-conference": "article", "review": "article",
              "book": "book", "monograph": "book", "edited-book": "book", "reference-book": "book",
              "book-chapter": "chapter", "chapter": "chapter", "book-section": "chapter", "book-part": "chapter",
              "posted-content": "preprint", "preprint": "preprint", "dissertation": "thesis", "thesis": "thesis",
              "report": "report", "dataset": "dataset", "software": "repository", "webpage": "web"}
PARTICLES = {"van", "von", "de", "der", "den", "del", "della", "di", "da", "la", "le", "ten", "ter", "dos", "du"}
ARXIV_ID = r"(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})"
DEFAULT_ORDER = ("crossref", "openalex")
ADAPTERS = ("crossref", "openalex", "zbmath", "semantic-scholar")
_last_call = {}
_TIMEOUT = [25]  # seconds one call may take; a download raises it for its own duration


def setup():
    """The optional setup, read from the environment and from nowhere else."""
    return {"mailto": os.environ.get("LIBRARY_MAILTO"), "openalex_key": os.environ.get("OPENALEX_API_KEY"),
            "s2_key": os.environ.get("SEMANTIC_SCHOLAR_API_KEY")}


def setup_line():
    s = setup()
    on = [n for n, v in (("a contact address", s["mailto"]), ("an OpenAlex key", s["openalex_key"]),
                         ("a Semantic Scholar key", s["s2_key"])) if v]
    return "setup: " + (", ".join(on) + ", from the environment" if on else "none (no key, no contact address)")


MAX_BYTES = 256 * 2**20  # the most one answer may carry; a copy of a work is far smaller


class _WebOnly(urllib.request.HTTPRedirectHandler):
    """A redirect is followed only to another http or https address, never to a file or ftp one."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme.lower() not in ("http", "https"):
            raise urllib.error.HTTPError(newurl, code, "a redirect away from http(s) is not followed", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_WebOnly)


def http_get(url, headers):
    """One GET: (status, body); status 0 when nothing answered.  The selftest replaces FETCH."""
    if urllib.parse.urlsplit(url).scheme.lower() not in ("http", "https"):
        return 0, b"not an http or https address, so nothing is fetched"
    host = urllib.parse.urlsplit(url).netloc
    gap = 3.1 if "arxiv" in host else 1.1  # arXiv asks for three seconds between calls
    for attempt in (1, 2):  # one more try, after a pause, where the interface was busy or silent
        wait = (gap if attempt == 1 else 3 * gap) - (time.monotonic() - _last_call.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.monotonic()
        deadline = time.monotonic() + _TIMEOUT[0]  # for the whole answer: a socket's timeout bounds one read only
        try:
            with _OPENER.open(urllib.request.Request(url, headers=headers), timeout=_TIMEOUT[0]) as r:
                chunks, got = [], 0
                while got <= MAX_BYTES:
                    if time.monotonic() > deadline:
                        raise TimeoutError(f"the answer took longer than {_TIMEOUT[0]} s")
                    chunk = r.read1(min(1 << 16, MAX_BYTES + 1 - got))  # what one read brings, not a full block
                    if not chunk:
                        break
                    chunks.append(chunk)
                    got += len(chunk)
                body = b"".join(chunks)
                if len(body) > MAX_BYTES:
                    return 0, f"the answer runs past {MAX_BYTES // 2**20} MiB; nothing is kept".encode()
                if r.length:  # fewer bytes than the answer announced
                    raise http.client.IncompleteRead(body, r.length)
                return r.status, body
        except urllib.error.HTTPError as e:
            status, body = e.code, b""
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError, ValueError) as e:
            status, body = 0, str(e).encode()
        if status not in (0, 429, 503):
            break
    return status, body


FETCH = http_get


def silence(status, body):
    """Why nothing answered, where the call says: a status of 0 carries its reason as the body."""
    return f" — {body.decode('utf-8', 'replace')[:200]}" if status == 0 and body else ""


def get(url, params=None, accept=None, extra=None):
    s = setup()
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    headers = {"User-Agent": "research-kit library (python-urllib)" + (f" (mailto:{s['mailto']})" if s["mailto"] else "")}
    if accept:
        headers["Accept"] = accept
    headers.update(extra or {})
    status, body = FETCH(url, headers)
    _CALLS[0] += 1
    _CALLS[1] += bool(status)
    return status, body


_CALLS = [0, 0]  # the calls one online command made, and how many of them anything answered


def initials(given):
    return "-".join("".join(w[0].upper() + "." for w in re.split(r"[\s.]+", part) if w) for part in str(given).split("-") if part)


def name_of(family, given):
    """`Surname, I.`, the form a card's authors take."""
    family, given = str(family or "").strip(), str(given or "").strip()
    return f"{family}, {initials(given)}" if family and given else family or given


def split_name(full):
    """`Given Names Surname` as (surname, given): the last word, with the particles before it."""
    full = str(full or "").strip()
    if "," in full:
        fam, _, giv = full.partition(",")
        return fam.strip(), giv.strip()
    words = full.split()
    if len(words) < 2:
        return full, ""
    i = len(words) - 1
    while i > 1 and words[i - 1].lower() in PARTICLES:
        i -= 1
    return " ".join(words[i:]), " ".join(words[:i])


def _first(v):
    return (v[0] if v else None) if isinstance(v, list) else v


def clean(text):
    """A resolver's string without its markup: tags dropped, entities read (twice: some arrive escaped twice)."""
    if not text:
        return None
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(html.unescape(str(text))))).strip() or None


def _csl(item, origin):
    """A candidate from a CSL-shaped answer: DOI content negotiation and Crossref's items."""
    years = []  # a record may carry the year it went online and the year of its printed issue: both are its years
    for f in ("issued", "published-print", "published", "published-online"):
        parts = (item.get(f) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and parts[0][0] and int(parts[0][0]) not in years:
            years.append(int(parts[0][0]))
    year = years[0] if years else None
    authors = [a.get("literal") or a.get("name") or name_of(a.get("family"), a.get("given"))
               for a in item.get("author") or item.get("editor") or []]
    return {"from": origin, "kind": TYPE_KINDS.get(item.get("type")), "title": clean(_first(item.get("title"))),
            "authors": [a for a in authors if a], "year": year, "years": years,
            "venue": clean(_first(item.get("container-title")) or item.get("publisher")),
            "doi": item.get("DOI"), "isbn": _first(item.get("ISBN")), "score": item.get("score")}


def at_doi(doi):
    status, body = get("https://doi.org/" + urllib.parse.quote(doi, safe="/()"), accept="application/vnd.citationstyles.csl+json")
    if status != 200:
        return [], f"doi: no answer for {doi} (status {status})"
    try:
        return [dict(_csl(json.loads(body), "doi"), doi=doi)], "doi: 1 answer"
    except ValueError:
        return [], f"doi: the answer for {doi} is not the citation form asked for"


def at_arxiv(ident):
    status, body = get("https://export.arxiv.org/api/query", {"id_list": ident})
    if status != 200:
        return [], f"arxiv: no answer for {ident} (status {status})"
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    try:
        entries = ET.fromstring(body).findall("a:entry", ns)
    except ET.ParseError:
        return [], "arxiv: the answer is not a feed"
    out = []
    for e in entries:
        title = e.findtext("a:title", None, ns)
        if not title or not e.findtext("a:published", None, ns):
            continue
        names = [split_name(re.sub(r"\s+", " ", n.text or "").strip()) for n in e.findall("a:author/a:name", ns)]
        out.append({"from": "arxiv", "kind": "preprint", "title": re.sub(r"\s+", " ", title).strip(),
                    "authors": [name_of(f, g) for f, g in names], "year": int(e.findtext("a:published", "", ns)[:4]),
                    "years": sorted({int(e.findtext("a:published", "", ns)[:4]), int((e.findtext("a:updated", "", ns) or e.findtext("a:published", "", ns))[:4])}),
                    "venue": e.findtext("x:journal_ref", None, ns) or "arXiv", "arxiv": norm_ident("arxiv", ident),
                    "doi": e.findtext("x:doi", None, ns)})
    return out, f"arxiv: {len(out)} answer(s)"


def at_crossref(entry, title):
    status, body = get("https://api.crossref.org/works", {
        "query.bibliographic": entry, "rows": 3, "mailto": setup()["mailto"],
        "select": "DOI,title,author,editor,issued,published-print,published-online,container-title,publisher,type,ISBN,score"})
    if status != 200:
        return [], f"crossref: no answer (status {status})"
    try:
        items = json.loads(body)["message"]["items"]
    except (ValueError, KeyError):
        return [], "crossref: the answer is not a list of works"
    return [_csl(i, "crossref") for i in items], f"crossref: {len(items)} answer(s)"


def at_openalex(entry, title):
    s = setup()
    status, body = get("https://api.openalex.org/works", {
        "filter": "title.search:" + re.sub(r"[^\w\s-]", " ", title) if title else None, "search": None if title else entry,
        "per-page": 3, "mailto": s["mailto"], "api_key": s["openalex_key"],
        "select": "id,doi,title,publication_year,authorships,primary_location,locations,type"})
    if status != 200:
        return [], f"openalex: no answer (status {status})"
    try:
        items = json.loads(body)["results"]
    except (ValueError, KeyError):
        return [], "openalex: the answer is not a list of works"
    out = [_openalex(i) for i in items]
    return out, f"openalex: {len(out)} answer(s), by {'title' if title else 'the whole entry'}"


def _openalex(i):
    arx = None
    for loc in i.get("locations") or []:
        m = re.search(r"arxiv\.org/abs/" + ARXIV_ID, str(loc.get("landing_page_url") or ""))
        if m:
            arx = m.group(1)
    names = [split_name(a.get("author", {}).get("display_name")) for a in i.get("authorships") or []]
    return {"from": "openalex", "kind": TYPE_KINDS.get(i.get("type")), "title": clean(i.get("title")),
            "authors": [name_of(f, g) for f, g in names], "year": i.get("publication_year"),
            "venue": ((i.get("primary_location") or {}).get("source") or {}).get("display_name"),
            "doi": norm_ident("doi", i["doi"]) if i.get("doi") else None, "arxiv": arx,
            "openalex": norm_ident("openalex", i["id"]) if i.get("id") else None}


def at_openalex_id(ident):
    s = setup()
    status, body = get("https://api.openalex.org/works/" + urllib.parse.quote(ident), {
        "mailto": s["mailto"], "api_key": s["openalex_key"],
        "select": "id,doi,title,publication_year,authorships,primary_location,locations,type"})
    if status != 200:
        return [], f"openalex: no answer for {ident} (status {status})"
    try:
        return [_openalex(json.loads(body))], "openalex: 1 answer, by identifier"
    except (ValueError, KeyError, AttributeError):
        return [], "openalex: the answer is not a work"


def at_zbmath(entry, title):
    status, body = get("https://api.zbmath.org/v1/document/_search", {"search_string": title or entry, "results_per_page": 3})
    if status != 200:
        return [], f"zbmath: no answer (status {status})"
    try:
        items = json.loads(body).get("result") or []
    except ValueError:
        return [], "zbmath: the answer is not a list of works"
    out = []
    for i in items:
        links = {ln.get("type"): ln.get("identifier") for ln in i.get("links") or []}
        names = [split_name(a.get("name")) for a in (i.get("contributors") or {}).get("authors") or []]
        series = ((i.get("source") or {}).get("series") or [{}])[0]
        code = (i.get("document_type") or {}).get("code")
        out.append({"from": "zbmath", "kind": {"j": "article", "b": "book", "a": "chapter"}.get(code),
                    "title": (i.get("title") or {}).get("title"), "authors": [name_of(f, g) for f, g in names],
                    "year": int(i["year"]) if str(i.get("year") or "").isdigit() else None,
                    "venue": series.get("title") or (i.get("source") or {}).get("source"),
                    "doi": links.get("doi"), "arxiv": links.get("arxiv"), "zbmath": i.get("identifier") or None})
    return out, f"zbmath: {len(out)} answer(s)"


def at_semantic_scholar(entry, title):
    key = setup()["s2_key"]
    status, body = get("https://api.semanticscholar.org/graph/v1/paper/search", {
        "query": title or entry, "limit": 3, "fields": "title,authors,year,venue,externalIds,publicationTypes"},
        extra={"x-api-key": key} if key else None)
    if status != 200:
        return [], f"semantic-scholar: no answer (status {status})" + ("" if key else "; it refuses most calls made with no key")
    try:
        items = json.loads(body).get("data") or []
    except ValueError:
        return [], "semantic-scholar: the answer is not a list of works"
    out = []
    for i in items:
        ids = i.get("externalIds") or {}
        names = [split_name(a.get("name")) for a in i.get("authors") or []]
        out.append({"from": "semantic-scholar", "kind": None, "title": i.get("title"),
                    "authors": [name_of(f, g) for f, g in names], "year": i.get("year"), "venue": i.get("venue") or None,
                    "doi": ids.get("DOI"), "arxiv": ids.get("ArXiv")})
    return out, f"semantic-scholar: {len(out)} answer(s)"


SEARCHERS = {"crossref": at_crossref, "openalex": at_openalex, "zbmath": at_zbmath, "semantic-scholar": at_semantic_scholar}


def norm(text):
    return re.sub(r"[^a-z0-9]+", " ", fold(text)).strip()


def title_match(title, text):
    """How well `title` reads inside `text`, 0 to 1: 1 when it stands there, else the best window's likeness."""
    a, b = norm(title), norm(text)
    if not a or not b:
        return 0.0
    if re.search(rf"(?<!\w){re.escape(a)}(?!\w)", b) or (len(b.split()) >= 3 and re.search(rf"(?<!\w){re.escape(b)}(?!\w)", a)):
        return 1.0
    words, n, best = b.split(), len(a.split()), 0.0
    for i in range(max(1, len(words) - n + 2)):
        for m in (n - 1, n, n + 1):
            if m > 0:
                best = max(best, SequenceMatcher(None, a, " ".join(words[i:i + m])).ratio())
    return best


ROMAN = {r: n for n, r in enumerate(("", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii",
                                     "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx"))}
NUMBERED = {"part", "vol", "volume", "book", "chapter", "series", "no", "number"}


def numerals(words):
    """The part or volume numbers a normalized title carries, in order: Arabic, and Roman where a Roman
    numeral is a number (the title's last word, or after part, volume, book …), never a stray "i" or "x"."""
    ws, out = words.split(), []
    for k, w in enumerate(ws):
        if w.isdigit():
            out.append(int("".join(str(unicodedata.digit(ch)) for ch in w)))
        elif w in ROMAN and w and (k == len(ws) - 1 or (k and ws[k - 1] in NUMBERED)):
            out.append(ROMAN[w])
    return out


def title_same(a, b):
    """How alike two whole titles are, 0 to 1: a short title standing inside a longer one is not that title,
    though a title of four words or more that the other continues with a subtitle is."""
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    short, long_ = sorted((a, b), key=len)
    if len(short.split()) >= 4 and long_.startswith(short + " "):
        return 0.9
    na, nb = numerals(a), numerals(b)
    if na and nb and na != nb:  # "… graphs I" and "… graphs II", "volume 1" and "volume 2": two works
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def identity(cand, entry, title=None):
    """The check a candidate passes before it is accepted: its title, its first author's surname and its
    year, each against the entry.  Where the entry's title is known the two titles are compared whole;
    where it is not, the candidate's title is looked for inside the entry."""
    like = title_same(cand.get("title") or "", title) if title else title_match(cand.get("title") or "", entry)
    sur = norm(surname(cand["authors"][0])) if cand.get("authors") else ""
    words = f" {norm(entry)} "
    ok_sur = bool(sur) and f" {sur} " in words
    seen = [y for y in cand.get("years") or ([cand["year"]] if cand.get("year") else []) if year_in(y, words)]
    return {"title": round(like, 2), "surname": ok_sur, "year": bool(seen), "year_seen": seen[0] if seen else None,
            "same_work": like >= 0.85 and ok_sur, "pass": like >= 0.85 and ok_sur and bool(seen)}


def guess_title(entry):
    """The title of an entry written `Authors (Year). Title. Venue …`: the emphasized span where the title
    is set in one, else the first sentence after the year; None where the entry is not written so."""
    m = re.search(ENTRY_DATE + r"\.\s+\*([^*]+)\*", entry) or \
        re.search(ENTRY_DATE + r"\.\s+(.+?)(?:(?<=[.?!])\s|$)", entry.replace("*", ""))
    title = m.group(1).strip().rstrip(".") if m else ""
    return title if len(title.split()) >= 2 else None


def ties(cards, entry, internal=False):
    """The registered cards an entry agrees with: the card's title against the entry's, the card's first
    author's surname and the card's year each found in the entry.  Offline: the same check a candidate passes."""
    text = entry["entry"].replace("*", "")
    words, title = f" {norm(text)} ", guess_title(entry["entry"])
    out = []
    for c in cards.values():
        if c["state"] != "registered" or (c["file"] and not internal):
            continue
        if (c["year"] or entry.get("year")) and not (c["year"] and year_in(c["year"], words)):
            continue  # an entry with no year yet (n.d., in press) ties only a card with none
        sur = norm(surname(c["authors"][0])) if c["authors"] else ""
        if not sur or f" {sur} " not in words:
            continue
        like = title_same(c["title"] or "", title) if title else title_match(c["title"] or "", text)
        if like >= 0.85:
            out.append(c.key)
    return out


def tied_entries(cfg, cards):
    """Every reference entry with the keys it is tied to."""
    return [dict(e, keys=ties(cards, e)) for e in reference_entries(cfg)]


def idents_in(entry):
    arx = re.search(r"arxiv[: ]\s*" + ARXIV_ID, entry, re.I)
    doi = re.search(r"\b(10\.\d{4,9}/[^\s;,]+)", entry)
    d = doi.group(1).rstrip(".") if doi else None
    if d and d.endswith(")") and d.count("(") < d.count(")"):
        d = d[:-1]
    return (norm_ident("arxiv", arx.group(1)) if arx else None), d


_META = re.compile(r"<meta\s+[^>]*?(?:name|property)\s*=\s*[\"']([^\"']+)[\"'][^>]*?content\s*=\s*[\"']([^\"']*)[\"']|"
                   r"<meta\s+[^>]*?content\s*=\s*[\"']([^\"']*)[\"'][^>]*?(?:name|property)\s*=\s*[\"']([^\"']+)[\"']", re.I | re.S)


def page_metadata(text):
    """The citation, Dublin Core and Open Graph metadata of a page, each name to its values in order."""
    out = defaultdict(list)
    for m in _META.finditer(text):
        name, content = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        out[name.strip().lower()].append(html.unescape(content.strip()))
    t = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    if t:
        out["title"].append(html.unescape(re.sub(r"\s+", " ", t.group(1)).strip()))
    return out


def at_url(url):
    """A candidate from a web address: a repository through its forge's API, any other page through its
    citation metadata (Highwire `citation_*`, Dublin Core, Open Graph, the title element)."""
    m = re.match(r"https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?(?:[#?].*)?$", url)
    if m:
        status, body = get(f"https://api.github.com/repos/{m.group(1)}/{m.group(2)}", accept="application/vnd.github+json")
        if status != 200:
            return [], f"github: no answer for {m.group(1)}/{m.group(2)} (status {status})"
        try:
            d = json.loads(body)
            full = d["full_name"]
        except (ValueError, KeyError, TypeError):
            return [], "github: the answer is not a repository"
        year = int(str(d.get("created_at") or "")[:4] or 0) or None
        return [{"from": "github", "kind": "repository", "title": full, "authors": [str((d.get("owner") or {}).get("login") or m.group(1))],
                 "year": year, "years": [year] if year else [], "venue": "GitHub", "url": d.get("html_url") or url,
                 "description": d.get("description"), "license": (d.get("license") or {}).get("spdx_id"),
                 "pushed": str(d.get("pushed_at") or "")[:10] or None}], "github: 1 answer"
    status, body = get(url, accept="text/html,application/xhtml+xml")
    if status != 200:
        return [], f"web: no answer for {url} (status {status})"
    meta = page_metadata(body.decode("utf-8", "replace"))

    def first(*names):
        for n in names:
            if meta.get(n):
                return meta[n][0]
        return None

    title = first("citation_title", "dc.title", "dcterms.title", "og:title", "twitter:title", "title")
    if not title:
        return [], f"web: {url} names no title"
    authors = meta.get("citation_author") or meta.get("dc.creator") or meta.get("dcterms.creator") or meta.get("author") or []
    authors = [name_of(*split_name(x)) if "," not in x else x.strip() for x in authors if x.strip()]
    date = first("citation_publication_date", "citation_date", "citation_online_date", "dc.date", "dcterms.date",
                 "dcterms.issued", "article:published_time", "date") or ""
    ym = re.search(r"(\d{4})", date)
    year = int(ym.group(1)) if ym else None
    venue = first("citation_journal_title", "citation_conference_title", "citation_publisher", "dc.publisher", "og:site_name")
    doi, arx = first("citation_doi", "dc.identifier.doi"), first("citation_arxiv_id")
    kind = "article" if doi or first("citation_journal_title") else "preprint" if arx else "web"
    return [{"from": "web", "kind": kind, "title": re.sub(r"\s+", " ", title), "authors": authors, "year": year,
             "years": [year] if year else [], "venue": venue, "url": url,
             "doi": norm_ident("doi", doi) if doi else None, "arxiv": norm_ident("arxiv", arx) if arx else None}], "web: 1 answer"


def candidates_for(a):
    """Every candidate the resolvers answer for the entry, with the line each resolver's call earned.
    An identifier is resolved where it lives; a free-text entry goes to the search interfaces in
    order, the next one asked only while no candidate has passed the check."""
    url = getattr(a, "url", None)
    if not url and re.match(r"https?://\S+$", (a.entry or "").strip()):
        url = a.entry.strip()
    entry = (a.entry or "").replace("*", "")
    if not entry and not url:
        raise Refused("resolve takes a reference entry, or --url")
    title = a.title or guess_title(entry)
    arx, doi = idents_in(entry)
    arx, doi = (norm_ident("arxiv", a.arxiv) if a.arxiv else arx), (norm_ident("doi", a.doi) if a.doi else doi)
    cands, log = [], []

    def take(found, line):
        log.append(line)
        for c in found:
            c["check"] = identity(c, entry, title)
            if url and c["from"] in ("github", "web") and entry.strip() in ("", url):
                # the address IS the entry: the page's own fields are the candidate, and the check is that it has a title
                c["check"].update({"pass": bool(c.get("title")), "title": 1.0 if c.get("title") else 0.0})
            cands.append(c)

    if url:
        take(*at_url(url))
        if any(c["check"]["pass"] for c in cands):
            return cands, log
    if a.at:
        if a.at not in SEARCHERS:
            raise Refused(f"--at {a.at!r} is not one of {ADAPTERS}")
        take(*SEARCHERS[a.at](entry, title))
        return cands, log
    if arx:
        take(*at_arxiv(arx))
    if doi:
        take(*at_doi(doi))
    if a.openalex:
        take(*at_openalex_id(norm_ident("openalex", a.openalex)))
    for name in DEFAULT_ORDER:
        if any(c["check"]["pass"] for c in cands) or (a.pick and cands):
            break
        take(*SEARCHERS[name](entry, title))
    return cands, log


def cand_line(n, c):
    k = c["check"]
    ids = " ".join(f"{f}:{c[f]}" for f in IDENTS if c.get(f))
    return (f"{n}. {'PASS' if k['pass'] else 'FAIL'}  {c['from']}  {label(c)}  {ids}  "
            f"[title {k['title']:.2f}, surname {'yes' if k['surname'] else 'no'}, year {'yes' if k['year'] else 'no'}]")


def cmd_resolve(cfg, cards, a, today):
    cands, log = candidates_for(a)
    lines = [setup_line(), f"entry: {a.entry}"] + log + [cand_line(n, c) for n, c in enumerate(cands, 1)]
    passing = [c for c in cands if c["check"]["pass"]]
    if a.override and not a.pick:
        raise Refused("--override takes a candidate by --pick N: it writes over that one's failed identity check")
    if a.pick:
        if not 1 <= a.pick <= len(cands):
            raise Refused(f"--pick {a.pick}: there are {len(cands)} candidate(s)")
        chosen = cands[a.pick - 1]
        if not chosen["check"]["pass"] and not a.override:
            raise Refused(f"candidate {a.pick} fails the identity check; taking it needs --override with the reason")
    else:
        chosen = passing[0] if passing else None
    if chosen is None:
        lines.append("no candidate passes the identity check; nothing is written")
        return [], lines, False
    if not a.register:
        lines.append(f"candidate {cands.index(chosen) + 1} passes; --register writes its card")
        return [], lines, True
    ids = {f: chosen.get(f) for f in IDENTS}
    for c in cands:  # the same work at another interface lends its identifiers, never its fields
        if c is not chosen and c["check"]["same_work"]:
            for f in IDENTS:
                ids[f] = ids[f] or c.get(f)
    ids = {f: norm_ident(f, v) if v else None for f, v in ids.items()}
    for c in cards.values():
        for f, v in ids.items():
            if v and c[f] and str(c[f]).lower() == v.lower():
                raise Refused(f"{f} {v} is already {c.key}")
    title_typed = a.title
    if "\ufffd" in str(chosen.get("title") or "") and not title_typed:
        title_typed = guess_title(a.entry)  # a record's damaged character is never written: the entry's title stands
        if not title_typed:
            raise Refused("the record's title carries a damaged character and the entry's title cannot be read off it; give --title")
    typed = {"title": title_typed, "authors": [x.strip() for x in a.author] if a.author else None,
             "year": int(a.year) if a.year else None, "venue": a.venue}
    fields, hand = {}, []
    if chosen["check"].get("year_seen") and chosen["check"]["year_seen"] != chosen.get("year"):
        lines.append(f"year: the record carries {' and '.join(map(str, chosen['years']))}; the entry's {chosen['check']['year_seen']} is written")
        chosen = dict(chosen, year=chosen["check"]["year_seen"])
    for f, v in typed.items():  # a field typed by the hand is never written over: the difference is printed
        fields[f] = chosen.get(f) if v is None else v
        if v is not None and v != chosen.get(f):
            hand.append(f)
            lines.append(f"{f} is kept as typed — typed {v!r}, {chosen['from']} {chosen.get(f)!r}")
    kind = a.kind or chosen.get("kind")
    if kind not in cfg.kinds:
        raise Refused(f"the resolver names no kind the library has; give --kind, one of {cfg.kinds}")
    if not fields["title"]:
        raise Refused("the candidate has no title; give --title")
    key = a.key or make_key(cards, fields["authors"] or [], fields["year"], fields["title"])
    if not KEY_RE.match(key):
        raise Refused(f"key {key!r} is not lowercase letters, digits and hyphens")
    if key in cards or (cfg.cards / f"{key}.md").exists():
        raise Refused(f"key {key} is taken")
    if a.kind and a.kind != chosen.get("kind"):
        hand.append("kind")
    fm = {"key": key, "state": "registered", "excluded": None, "kind": kind, "title": fields["title"],
          "authors": fields["authors"] or [], "year": fields["year"], "venue": fields["venue"], **ids, "url": chosen.get("url"),
          "metadata": {"from": chosen["from"], "on": today, "typed": ", ".join(hand) or None},
          "verified": None if a.override else {"on": today, "by": chosen["from"]},
          "read": {"grade": "ungraded" if a.seed else "unread", "on": None, "what": None},
          "via": None, "copy": None, "related": [], "tags": a.tag or [], "seeded": bool(a.seed), "created": today}
    notes = list(a.note or [])
    if chosen["from"] == "github":
        notes.append(f"{today} — {chosen.get('description') or 'No description on the repository.'}"
                     + (f" Licence {chosen['license']}." if chosen.get("license") else "")
                     + (f" Last pushed {chosen['pushed']}." if chosen.get("pushed") else ""))
    if a.override:
        notes.append(f"{today} — Registered from a candidate that failed the identity check "
                     f"(title {chosen['check']['title']:.2f}, surname {'yes' if chosen['check']['surname'] else 'no'}, "
                     f"year {'yes' if chosen['check']['year'] else 'no'}): {a.override}")
    card = Card(cfg.cards / f"{key}.md", fm, body_of("\n\n".join(notes)))
    write_card(cfg, card)
    lines.append(f"registered {key}"
                 + (f"; typed by hand and not taken from the resolver: {', '.join(hand)}" if hand else ""))
    return [card], lines, True


def download(url):
    """One file by its address, with the time a large file needs: (status, bytes)."""
    _TIMEOUT[0] = 300
    try:
        return get(url)
    finally:
        _TIMEOUT[0] = 25


def arxiv_version(ident):
    """The latest version of an arXiv work, read off the address its own record gives."""
    status, body = get("https://export.arxiv.org/api/query", {"id_list": ident})
    m = re.search(rb"<id>\s*https?://arxiv\.org/abs/[^<\s]*?v(\d+)\s*</id>", body or b"") if status == 200 else None
    return f"v{int(m.group(1))}" if m else None


def addresses(c, a):
    """Where a copy of the work may be fetched, in order, each with the version it names: an address
    given on the command line; arXiv's source and then its PDF (the PDF alone with --pdf); the card's own
    address; and, only under the optional contact address, the open-access location Unpaywall names."""
    if a.url:
        return [(a.url, a.version)], []
    out, lines = [], []
    if c["arxiv"]:
        v = arxiv_version(c["arxiv"])
        if v is None:
            lines.append(f"arxiv: no version read for {c['arxiv']}; the latest is fetched and its version left unrecorded")
        vid = f"{c['arxiv']}{v or ''}"
        out += ([] if a.pdf else [(f"https://arxiv.org/e-print/{vid}", v)]) + [(f"https://arxiv.org/pdf/{vid}", v)]
    if c["url"]:
        out.append((str(c["url"]), a.version))
    if c["doi"] and setup()["mailto"]:
        status, body = get("https://api.unpaywall.org/v2/" + urllib.parse.quote(str(c["doi"]), safe="/()"), {"email": setup()["mailto"]})
        try:
            loc = (json.loads(body).get("best_oa_location") or {}).get("url_for_pdf") if status == 200 else None
        except ValueError:
            loc = None
        lines.append(f"unpaywall: {'an open-access copy at ' + loc if loc else 'no open-access copy named'}")
        if loc:
            out.append((loc, a.version))
    return out, lines


def cmd_fetch(cfg, cards, a, today):
    """A copy fetched by the card's identifiers or from a given address, kept in the store with its hash,
    date, version and page count; a TeX source where arXiv has one, a PDF otherwise."""
    c = by_ref(cards, a.ref)
    lines = [setup_line()]
    if c["file"]:
        raise Refused(f"{c.key} is an internal document: its tracked file {c['file']} is its copy")
    if isinstance(c["copy"], dict) and not a.replace:
        raise Refused(f"{c.key} has a copy recorded ({c['copy']['path']}); --replace fetches another in its place")
    tries, more = addresses(c, a)
    lines += more
    if not tries:
        raise Refused(f"no address to fetch {c.key} from: the card has no arXiv identifier and no address"
                      + (", and no contact address is set for the open-access lookup of its DOI" if c["doi"] and not setup()["mailto"] else "")
                      + "; give --url, or take in a file obtained by hand with `library keep`")
    for url, version in tries:
        status, data = download(url)
        if status != 200:
            lines.append(f"{url}: no answer (status {status}){silence(status, data)}")
            continue
        form = form_of(data, urllib.parse.urlsplit(url).path)
        if form == "page" or (form == "text" and not a.url):
            lines.append(f"{url}: answered a page, not a file")
            continue
        if form == "source" and not tex_files(data):
            lines.append(f"{url}: a source with no TeX file in it")
            continue
        form, n, has = store_copy(cfg, c, data, urllib.parse.urlsplit(url).path, today, url, version)
        lines.append(copy_line(c, form, n, has) + (f"; version {version}" if version else ""))
        return [c], lines, True
    lines.append(f"nothing fetched for {c.key}; nothing is written")
    return [], lines, False


def cmd_restore(cfg, cards, a, today):
    """Every recorded copy the store has lost, fetched again from the address its card records and
    checked against the recorded hash — the case of a reinstalled machine.  A copy obtained by hand has
    no address and is named as needing a backup; an address that now answers other bytes writes nothing."""
    lines, ok = [setup_line()], True
    want = [by_ref(cards, r) for r in a.refs] or [c for _, c in sorted(cards.items()) if isinstance(c["copy"], dict)]
    tally = Counter()
    for c in want:
        cp, f = c["copy"], copy_file(cfg, c)
        if not isinstance(cp, dict) or f is None:
            lines.append(f"{c.key}: no copy is recorded")
            continue
        if f.is_file():
            if file_sha256(f) != cp["sha256"]:
                lines.append(f"{c.key}: on disk and NOT matching its recorded hash")
                ok = False
            else:
                tally["on disk"] += 1
                if not (cfg.store / c.key / "text" / "units.json").is_file():
                    read_units(cfg, c)
            continue
        if not cp.get("from"):
            lines.append(f"{c.key}: obtained by hand, no address to fetch it from ({cp['path']}); "
                         + (f"it is tracked under {cfg.kept_name}: restore it from version control" if cfg.kept else "NEEDS A BACKUP"))
            tally["by hand and lost"] += 1
            continue
        status, data = download(str(cp["from"]))
        if status != 200:
            lines.append(f"{c.key}: {cp['from']} did not answer (status {status}){silence(status, data)}")
            ok = False
        elif hashlib.sha256(data).hexdigest() != cp["sha256"]:
            lines.append(f"{c.key}: {cp['from']} now answers other bytes than the recorded hash; nothing is written — "
                         f"`library fetch {c.key} --replace` records what it answers today")
            ok = False
        elif not any(h and f.resolve().is_relative_to(h.resolve()) for h in (cfg.store, cfg.kept)):
            lines.append(f"{c.key}: its recorded path {cp['path']} is outside the store and the kept directory; nothing is written")
            ok = False
        else:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
            write_text(cfg, c.key, extract_units(cfg, f)[1])
            lines.append(f"{c.key}: restored from {cp['from']}")
            tally["restored"] += 1
    lines.append("restore: " + (", ".join(f"{n} {k}" for k, n in tally.items()) or "nothing to do"))
    return [], lines, ok


# --- the watch: what is new since it last looked -----------------------------------
# A check and not a schedule.  It keeps what it has seen and no clock: a run right after a run
# reports nothing and changes no file, and when it runs is the business of whoever runs it.

WATCH_KINDS = ("citing", "related", "arxiv", "github")
WATCH_FIELDS = ("name", "kind", "card", "query", "since", "why", "openalex", "seen")
CAND_FIELDS = ("ids", "title", "authors", "date", "surfaced", "watch", "why", "state", "reason")
CAND_STATES = ("proposed", "excluded")
WINDOW = 200  # the newest works one look takes in
TITLES = 25   # the hits whose title is fetched one by one in a run, where an interface names a work by identifier alone
WATCH_HEAD = ("# The library's watches and what each has already seen.  Written by `library watch`;\n"
              "# a watch is added and dropped by the command, and its `seen` list is the tool's alone.")
CAND_HEAD = ("# Works a watch surfaced, not yet registered.  Written by `library watch` and `library candidates`;\n"
             "# a candidate registered as a card leaves this file, one set aside keeps its reason and is never proposed again.")


def toml_tables(head, table, rows, order):
    """A list of flat tables as TOML: a string, or a list of strings one to a line."""
    out = [head, ""]
    for r in rows:
        out.append(f"[[{table}]]")
        for k in order:
            v = r.get(k)
            if isinstance(v, list):
                out += [f"{k} = ["] + [f"  {json.dumps(str(x), ensure_ascii=False)}," for x in v] + ["]"] if v else [f"{k} = []"]
            elif v is not None:
                out.append(f"{k} = {json.dumps(str(v), ensure_ascii=False)}")
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def load_watch(cfg):
    """The watches and the candidates, each a list of tables; a file that is not there is an empty list."""
    def rows(path, table):
        if not path.is_file():
            return []
        try:
            return [dict(r) for r in tomllib.loads(path.read_text(encoding="utf-8")).get(table, [])]
        except (tomllib.TOMLDecodeError, TypeError, ValueError) as e:
            raise Refused(f"{rel(cfg, path)} does not parse: {e}")
    return rows(cfg.watch_file, "watch"), rows(cfg.cand_file, "candidate")


def save_watch(cfg, watches=None, cands=None):
    """Each file written only where its text changed, so a run that found nothing touches nothing."""
    for path, text in ((cfg.watch_file, None if watches is None else toml_tables(WATCH_HEAD, "watch", watches, WATCH_FIELDS)),
                       (cfg.cand_file, None if cands is None else toml_tables(CAND_HEAD, "candidate", cands, CAND_FIELDS))):
        if text is not None and (not path.is_file() or path.read_text(encoding="utf-8") != text):
            path.parent.mkdir(parents=True, exist_ok=True)
            write_whole(path, text)


def work_ids(doi=None, arxiv=None, openalex=None, github=None):
    """The names one work goes by, as the watch compares them; an arXiv DOI is also its arXiv identifier."""
    ids = []
    if doi:
        d = norm_ident("doi", doi).lower()
        ids.append("doi:" + d)
        m = re.match(r"10\.48550/arxiv\.(.+)$", d)
        arxiv = arxiv or (m.group(1) if m else None)
    if arxiv:
        ids.append("arxiv:" + norm_ident("arxiv", arxiv).lower())
    if openalex:
        ids.append("openalex:" + norm_ident("openalex", openalex).upper())
    if github:
        ids.append("github:" + str(github).lower())
    return ids


def card_ids(cards):
    """Every name a card's work goes by: its identifiers, and the repository its address names."""
    known = set()
    for c in cards.values():
        known.update(work_ids(doi=c["doi"], arxiv=c["arxiv"], openalex=c["openalex"]))
        m = re.search(r"github\.com/([^/\s]+/[^/\s#?]+)", str(c["url"] or ""))
        if m:
            known.add("github:" + re.sub(r"\.git$", "", m.group(1)).lower())
    return known


def sync_candidates(cfg, cards):
    """A candidate that has become a card leaves the list."""
    if not cfg.cand_file.is_file():
        return
    _, cands = load_watch(cfg)
    known = card_ids(cards)
    save_watch(cfg, cands=[c for c in cands if not set(c.get("ids") or []) & known])


def _names(people):
    people = [x for x in people if x]
    return people[0] if len(people) == 1 else " & ".join(people) if len(people) == 2 else f"{people[0]} et al." if people else None


def _oa_hit(w):
    return {"ids": work_ids(doi=w.get("doi"), openalex=w.get("id")), "title": clean(w.get("title") or ""),
            "authors": _names([surname(name_of(*split_name((a.get("author") or {}).get("display_name") or "")))
                               for a in w.get("authorships") or [] if (a.get("author") or {}).get("display_name")]),
            "date": w.get("publication_date")}


def _oa(path, params):
    st = setup()
    status, body = get("https://api.openalex.org/" + path, dict(params, mailto=st["mailto"], api_key=st["openalex_key"]))
    try:
        return (json.loads(body) if status == 200 else None), status
    except ValueError:
        return None, status


def _oa_id(w, c):
    """The work's OpenAlex identifier: the card's, the one the watch found before, or one lookup by its DOI."""
    if c["openalex"] or w.get("openalex"):
        return norm_ident("openalex", c["openalex"] or w["openalex"])
    doi = c["doi"] or (f"10.48550/arXiv.{c['arxiv']}" if c["arxiv"] else None)
    if not doi:
        return None
    data, _ = _oa("works/doi:" + urllib.parse.quote(str(doi), safe="/()"), {"select": "id"})
    if data and data.get("id"):
        w["openalex"] = norm_ident("openalex", data["id"])
    return w.get("openalex")


def look_citing(cfg, cards, w):
    """The newest works citing the card's work: OpenAlex's citing filter, and the OpenCitations index
    where OpenAlex does not answer.  The index names a citing work by identifier alone."""
    c = cards[w["card"]]
    oid = _oa_id(w, c)
    if oid:
        data, status = _oa("works", {"filter": f"cites:{oid}", "sort": "publication_date:desc", "per-page": WINDOW,
                                     "select": "id,doi,title,publication_date,authorships"})
        if data is not None:
            return [_oa_hit(x) for x in data.get("results") or []], f"OpenAlex, {(data.get('meta') or {}).get('count')} citing in all"
    if not c["doi"]:
        return None, "OpenAlex did not answer, and the card has no DOI to ask the OpenCitations index with"
    status, body = get("https://api.opencitations.net/index/v2/citations/doi:" + urllib.parse.quote(str(c["doi"]), safe="/()"))
    try:
        rows = json.loads(body) if status == 200 else None
    except ValueError:
        rows = None
    if not isinstance(rows, list):
        return None, f"neither OpenAlex nor the OpenCitations index answered (status {status})"
    hits = []
    for r in rows:
        named = dict(t.split(":", 1) for t in str(r.get("citing") or "").split() if ":" in t)
        ids = work_ids(doi=named.get("doi"), arxiv=named.get("arxiv"), openalex=named.get("openalex"))
        if ids:
            hits.append({"ids": ids, "title": None, "authors": None, "date": r.get("creation") or None})
    hits.sort(key=lambda h: h["date"] or "", reverse=True)
    return hits[:WINDOW], f"the OpenCitations index, {len(rows)} citing in all"


def look_related(cfg, cards, w):
    """The works OpenAlex calls related to the card's work."""
    oid = _oa_id(w, cards[w["card"]])
    data, status = _oa("works/" + oid, {"select": "related_works"}) if oid else (None, 0)
    if data is None:
        return None, f"OpenAlex did not answer (status {status})" if oid else "the card has no identifier OpenAlex can be asked by"
    rel_ids = [norm_ident("openalex", x) for x in data.get("related_works") or []][:50]
    if not rel_ids:
        return [], "OpenAlex, no related work named"
    data, status = _oa("works", {"filter": "openalex:" + "|".join(rel_ids), "per-page": 50,
                                 "select": "id,doi,title,publication_date,authorships"})
    if data is None:
        return None, f"OpenAlex did not answer (status {status})"
    return [_oa_hit(x) for x in data.get("results") or []], "OpenAlex's related works"


def look_arxiv(cfg, cards, w):
    """The newest arXiv entries answering a query written in arXiv's own syntax."""
    status, body = get("https://export.arxiv.org/api/query", {"search_query": w["query"], "sortBy": "submittedDate",
                                                             "sortOrder": "descending", "max_results": 50})
    ns = {"a": "http://www.w3.org/2005/Atom"}
    try:
        entries = ET.fromstring(body).findall("a:entry", ns) if status == 200 else None
    except ET.ParseError:
        entries = None
    if entries is None:
        return None, f"arXiv did not answer (status {status})"
    hits = []
    for e in entries:
        ident, title = e.findtext("a:id", "", ns), e.findtext("a:title", None, ns)
        if "/abs/" not in ident or not title:
            continue
        names = [split_name(re.sub(r"\s+", " ", n.text or "").strip()) for n in e.findall("a:author/a:name", ns)]
        hits.append({"ids": work_ids(arxiv=ident.split("/abs/", 1)[1]), "title": re.sub(r"\s+", " ", title).strip(),
                     "authors": _names([surname(name_of(f, g)) for f, g in names]), "date": (e.findtext("a:published", "", ns) or "")[:10] or None})
    return hits, "arXiv"


def look_github(cfg, cards, w):
    """The repositories answering a query written in GitHub's search syntax, the most recently updated first."""
    status, body = get("https://api.github.com/search/repositories", {"q": w["query"], "sort": "updated", "order": "desc", "per_page": 50},
                       accept="application/vnd.github+json")
    try:
        items = json.loads(body).get("items") if status == 200 else None
    except (ValueError, AttributeError):
        items = None
    if items is None:
        return None, f"GitHub did not answer (status {status})"
    return [{"ids": work_ids(github=r["full_name"]), "title": r["full_name"] + (f" — {r['description']}" if r.get("description") else ""),
             "authors": None, "date": (r.get("created_at") or "")[:10] or None} for r in items if r.get("full_name")], "GitHub"


LOOKS = {"citing": look_citing, "related": look_related, "arxiv": look_arxiv, "github": look_github}


def name_hit(h):
    """The title and authors of a hit an interface named by identifier alone, asked where the identifier lives."""
    for i in h["ids"]:
        kind, _, v = i.partition(":")
        found, _ = at_doi(v) if kind == "doi" else at_arxiv(v) if kind == "arxiv" else ([], "")
        if found:
            h["title"] = found[0].get("title")
            h["authors"] = _names([surname(a) for a in found[0].get("authors") or []])
            return


def watch_why(w):
    return {"citing": f"cites {w.get('card')}", "related": f"related to {w.get('card')}",
            "arxiv": f"answers the arXiv query {w.get('query')}",
            "github": f"answers the GitHub query {w.get('query')}"}.get(w.get("kind"), f"of the unknown kind {w.get('kind')!r}")


def candidate_line(c):
    who = " — ".join(x for x in (c.get("authors"), c.get("date")) if x)
    return (f"{(c.get('ids') or ['?'])[0]} | {c.get('title') or '(title not fetched)'}" + (f" | {who}" if who else "")
            + f" | {c.get('surfaced')}, {c.get('watch')}: {c.get('why')}"
            + (f" | excluded: {c.get('reason')}" if c.get("state") == "excluded" else ""))


def cmd_watch(cfg, cards, a, today):
    """Run the watches, or with --add, --drop or --list keep them.  A run asks each watch's interface for
    the newest works, proposes the ones no run has seen and no card or candidate already names, and records
    what it saw; at a watch's first run a work dated before the watch's `since` is recorded and not proposed."""
    watches, cands = load_watch(cfg)
    by_name = {w.get("name"): w for w in watches}
    if a.add:
        given = [(k, v) for k, v in (("citing", a.citing), ("related", a.related), ("arxiv", a.arxiv), ("github", a.github)) if v]
        if len(given) != 1:
            raise Refused("a watch is one of --citing KEY, --related KEY, --arxiv QUERY, --github QUERY")
        if not KEY_RE.match(a.add) or a.add in by_name:
            raise Refused(f"watch name {a.add!r} is taken, or is not lowercase letters, digits and hyphens")
        kind, v = given[0]
        since = a.since or today
        if not ISO.match(since):
            raise Refused(f"--since {since!r} is not a date")
        w = {"name": a.add, "kind": kind, "since": since, "why": a.why}
        if kind in ("citing", "related"):
            c = by_ref(cards, v)
            if not (c["doi"] or c["arxiv"] or c["openalex"]):
                raise Refused(f"{c.key} has no DOI, arXiv or OpenAlex identifier: nothing can be asked what cites it")
            w["card"] = c.key
        else:
            w["query"] = v
        save_watch(cfg, watches=watches + [w])
        return [], [f"watching {a.add}: {watch_why(w)}; a work dated before {since} is recorded at the first run and not proposed"], True
    if a.drop:
        if a.drop not in by_name:
            raise Refused(f"no watch named {a.drop}")
        save_watch(cfg, watches=[w for w in watches if w.get("name") != a.drop])
        return [], [f"dropped {a.drop}; what it surfaced stays among the candidates"], True
    if a.list:
        lines = [f"{w.get('name')} | {watch_why(w)} | since {w.get('since')} | "
                 + (f"{len(w['seen'])} seen" if "seen" in w else "never run") + (f" | {w['why']}" if w.get("why") else "") for w in watches]
        return [], lines + [f"{len(watches)} watch(es); {sum(c.get('state') == 'proposed' for c in cands)} candidate(s) proposed, "
                            f"{sum(c.get('state') == 'excluded' for c in cands)} set aside"], True
    for n in a.names:
        if n not in by_name:
            raise Refused(f"no watch named {n}")
    lines, ok, fresh, titles = [setup_line()], True, [], TITLES
    known = card_ids(cards) | {i for c in cands for i in c.get("ids") or []}
    for w in watches:
        if a.names and w.get("name") not in a.names:
            continue
        if w.get("kind") not in LOOKS or (w["kind"] in ("citing", "related") and w.get("card") not in cards):
            lines.append(f"{w.get('name')}: no look — {watch_why(w)}, which `library check` reports (L14); drop or fix the watch")
            ok = False
            continue
        hits, said = LOOKS[w["kind"]](cfg, cards, w)
        if hits is None:
            lines.append(f"{w['name']}: no look — {said}")
            ok = False
            continue
        first, seen = "seen" not in w, set(w.get("seen") or [])
        older = named = 0
        for h in hits:
            if set(h["ids"]) & seen:
                continue
            seen.update(h["ids"])
            if first and w["kind"] != "related" and h.get("date") and str(h["date"]) < str(w.get("since") or ""):
                older += 1
            elif set(h["ids"]) & known:
                named += 1
            else:
                if not h.get("title") and titles > 0:
                    titles -= 1
                    name_hit(h)
                known.update(h["ids"])
                fresh.append({"ids": h["ids"], "title": h.get("title"), "authors": h.get("authors"), "date": h.get("date"),
                              "surfaced": today, "watch": w["name"], "why": watch_why(w) + f", by {said.split(',')[0]}", "state": "proposed"})
        new = sum(c["watch"] == w["name"] for c in fresh)
        w["seen"] = sorted(seen)
        lines.append(f"{w['name']}: {said}; {len(hits)} looked at, {new} new"
                     + (f", {older} dated before {w.get('since')} and recorded unproposed" if older else "")
                     + (f", {named} already a card or a candidate" if named else ""))
    save_watch(cfg, watches=watches, cands=cands + fresh)
    lines += ["new: " + candidate_line(c) for c in fresh]
    lines.append(f"watch: {len(fresh)} new candidate(s)" + ("" if not fresh else "; `library candidates` lists them, "
                 "`library resolve … --register` makes one a card, `library candidates --exclude ID --reason …` sets one aside"))
    return [], lines, ok


def cmd_candidates(cfg, cards, a, today):
    """The works the watches surfaced; with --exclude, one set aside with its reason so that no watch proposes it again."""
    _, cands = load_watch(cfg)
    if a.exclude:
        hit = []
        for i in a.exclude:
            found = [c for c in cands if i in (c.get("ids") or [])]
            if not found:
                raise Refused(f"no candidate goes by {i}")
            hit.append(found[0])
        if not a.reason:
            raise Refused("a candidate set aside says why (--reason)")
        for c in hit:
            c.update({"state": "excluded", "reason": f"{today}: {a.reason}"})
        save_watch(cfg, cands=cands)
        return [], [f"set aside {candidate_line(c)}" for c in hit], True
    want = "excluded" if a.excluded else "proposed"
    shown = [c for c in cands if c.get("state") == want]
    return [], [candidate_line(c) for c in shown] + [f"{len(shown)} candidate(s) {want if want == 'proposed' else 'set aside'}"], True


def cmd_verify(cfg, cards, a, today):
    """Re-resolve each card at its own identifiers and compare.  A card passes when every answer is the
    card's work by title and first author and one of them carries its year; it is then stamped, and a
    differing field is printed and written only where --take names it."""
    if a.take and len(a.refs) != 1:
        raise Refused("--take corrects one card: name one")
    for f in a.take or []:
        if f not in ("title", "authors", "year", "venue"):
            raise Refused(f"--take {f}: one of title, authors, year, venue")
    lines, changed, ok = [setup_line()], [], True
    for ref in a.refs:
        c = by_ref(cards, ref)
        answers = []
        for f, at in (("arxiv", at_arxiv), ("doi", at_doi)):
            if c[f]:
                found, line = at(str(c[f]))
                answers.append((f, found[0] if found else None, line))
        if not answers:
            lines.append(f"{c.key}: FAIL — the card has no identifier a resolver is asked at (arxiv, doi)")
            ok = False
            continue
        entry = f"{'; '.join(c['authors'] or [])} {c['year']} {c['title']}"
        bad, year_seen, diffs = [], False, []
        for f, cand, line in answers:
            if cand is None:
                bad.append(line)
                continue
            k = identity(cand, entry, c["title"])
            year_seen = year_seen or k["year"]
            if not k["same_work"]:
                bad.append(f"{f} {c[f]} answers another work: {label(cand)} [title {k['title']:.2f}, surname {'yes' if k['surname'] else 'no'}]")
            for g in ("title", "authors", "year", "venue"):
                if cand.get(g) and cand.get(g) != c[g] and not (g == "year" and c[g] in (cand.get("years") or [])):
                    diffs.append((g, f, cand[g]))
        if not bad and c["year"] and not year_seen:
            bad.append(f"no answer carries the card's year {c['year']}: " + ", ".join(f"{f} says {cand['year']}" for f, cand, _ in answers))
        if bad:
            lines += [f"{c.key}: FAIL — {b}" for b in bad] + [f"{c.key}: not stamped; the card stands as it was"]
            ok = False
            continue
        typed = [x.strip() for x in str((c["metadata"] or {}).get("typed") or "").split(",") if x.strip()]
        for g, f, v in diffs:
            if g in (a.take or []) and c[g] != v:
                c.fm[g] = v
                typed = [x for x in typed if x != g]
                lines.append(f"{c.key}: {g} taken from {f}: {v!r}")
            elif c[g] != v:
                lines.append(f"{c.key}: {g} differs and is left as typed — card {c[g]!r}, {f} {v!r}")
        if isinstance(c["metadata"], dict) and c["metadata"].get("from") != "hand":
            c.fm["metadata"]["typed"] = ", ".join(typed) or None
        c.fm["verified"] = {"on": today, "by": ", ".join(f for f, _, _ in answers)}
        write_card(cfg, c)
        changed.append(c)
        lines.append(f"{c.key}: verified {today} at {c['verified']['by']}")
    return changed, lines, ok


def cmd_type(cfg, cards, a, today):
    """A work's own fields corrected by the hand over what a resolver wrote, and marked so."""
    c = by_ref(cards, a.ref)
    new = {"title": a.title, "authors": [x.strip() for x in a.author] if a.author else None,
           "year": int(a.year) if a.year else None, "venue": a.venue}
    changed = [f for f, v in new.items() if v is not None and v != c[f]]
    if not changed:
        raise Refused("nothing to type: give a field that differs (--title, --author, --year, --venue)")
    for f in changed:
        c.fm[f] = new[f]
    md = c["metadata"] if isinstance(c["metadata"], dict) else {"from": "hand", "on": today, "typed": None}
    if md.get("from") != "hand":
        was = [x.strip() for x in str(md.get("typed") or "").split(",") if x.strip()]
        md["typed"] = ", ".join(was + [f for f in changed if f not in was])
    c.fm["metadata"] = md
    write_card(cfg, c)
    return [], [c]


WRITERS = {"type": cmd_type, "register": cmd_register, "read": cmd_read, "note": cmd_note, "relate": cmd_relate,
           "exclude": cmd_exclude, "keep": cmd_keep, "extract": cmd_extract}
ONLINE = {"resolve": cmd_resolve, "verify": cmd_verify, "fetch": cmd_fetch, "restore": cmd_restore,
          "watch": cmd_watch, "candidates": cmd_candidates}


# --- selftest ---------------------------------------------------------------------

SELFTEST_TOML = """
[paths]
library = "library"
store = "library/.store"
[cite]
prefix = "lib:"
scan = ["records", "library/cards"]
[find]
limit = 10
[copy]
text_command = ["PYTHON", "-c", "import sys; sys.stdout.buffer.write(open(sys.argv[1], 'rb').read()[5:])", "{file}"]
""".replace('"PYTHON"', json.dumps(sys.executable))


# --- the dashboard's page manifest ------------------------------------------------
#
# A dashboard host asks `library --json pages` for this and renders every page from the
# command each route names, with `--json`; it reads no card file and serves no path into the store.

def pages_manifest(cfg):
    pre = re.escape(cfg.cite_prefix)
    return {
        "component": "library", "title": "Library", "mount": "/library",
        "nav": [{"label": "Library", "path": "/library"}, {"label": "Candidates", "path": "/library/candidates"},
                {"label": "Library check", "path": "/library/check"}],
        "links": [{"pattern": r"(?<![A-Za-z0-9])%s([a-z0-9][a-z0-9-]*)(?:#([a-z0-9][a-z0-9-]*))?" % pre, "path": "/library/{1}#{2}"}],
        "routes": [
            {"path": "/library", "view": "list", "run": ["find", "--limit", "100"], "words": "q",
             "params": ["tag", "grade", "kind", "state", "id", "from"], "flags": [],
             "columns": ["key", "label", "kind", "read.grade", "tags", "matched"],
             "link": {"column": "key", "path": "/library/{key}"}, "title": "Library",
             "note": "The command line's own answer, ranked as it ranks; no work is shown."},
            {"path": "/library/candidates", "view": "tables", "title": "Candidates and watches",
             "note": "A watch looks when it is run and keeps no clock; this page runs none.",
             "tables": [{"title": "Proposed", "run": ["candidates"], "field": "candidates",
                         "columns": ["ids", "title", "authors", "date", "surfaced", "watch", "why"]},
                        {"title": "Set aside", "run": ["candidates", "--excluded"], "field": "candidates",
                         "columns": ["ids", "title", "authors", "date", "surfaced", "reason"]},
                        {"title": "Watches", "run": ["watch", "--list"], "field": "watches",
                         "columns": ["name", "looks_at", "since", "seen", "why"]}]},
            {"path": "/library/check", "view": "check", "run": ["check"], "title": "Library check"},
            {"path": "/library/{key}", "view": "record", "run": ["show", "{key}"], "title": "{key}", "heading": "label",
             "fields": "records.0", "body": "body", "hide": ["key", "path", "label", "copy.path", "copy.sha256", "seeded"],
             "hrefs": {"doi": "https://doi.org/{}", "arxiv": "https://arxiv.org/abs/{}", "openalex": "https://openalex.org/{}", "url": "{}"},
             "sections": [{"field": "sites", "title": "Cited at", "as": "sites"}]},
        ],
    }


# --- init --------------------------------------------------------------------------

INIT_TOML = """# library.toml — the reference library's bindings for THIS project.  Every path is relative
# to this file's directory.  The `library` skill reads it.

[paths]
library = "{dir}"                 # cards/<key>.md, one per work; INDEX.md, generated by `library index`
store = "{dir}/.store"            # IGNORED by version control: fetched copies and the derived full-text index
{kept}# reflow_module = "scripts/reflow.py"   # exports reflow_text(text): one sentence per line; built-in otherwise

[card]
kinds = ["article", "book", "chapter", "preprint", "thesis", "report", "document", "web", "repository", "dataset"]

[cite]
# A work is cited by this prefix and its card's key, `lib:jen1990`.  `library cited` and
# `library related` compute the citing sites from these files and directories (*.md under a
# directory) and store nothing.
prefix = "lib:"
scan = [{scan}]

[entries]
# The documents whose `## References` entries are tied to cards; each entry must agree with exactly
# one card.  Empty where the documents cite by key.
documents = [{documents}]
heading = "References"

[internal]
# A card naming a tracked file of the project (`file`) is an internal document — a report, a survey,
# anything made here or handed in.  Every file under these directories has its card; no bound
# document's reference entry may be tied to one.
kinds = ["report", "document"]
directories = [{internal}]

[claims]
# The shapes of a sentence that credits a document against a named work, as regular expressions;
# the defaults are generic — a project with a prover adds its own words (`first formalization`,
# `machine-checked`, `in any prover`).
# shapes = []

[copy]
# Prints a PDF's text with a form feed between pages; `{{file}}` stands for the kept copy.
text_command = ["pdftotext", "-layout", "{{file}}", "-"]

[find]
limit = 10
"""

INSTRUCTIONS = """What the project's instructions (CLAUDE.md, AGENTS.md) should now carry, in their words:

- The reference library is `{dir}/`: one card per work, found with `library find WORDS` or
  `library show KEY`, never by a glob over the cards; `library.toml` binds the names.
- A work is cited as `lib:<key>`; a sentence that cites a work is written after `library show`
  and, where the claim needs it, an extract on the card.
- `library check` runs before a commit (a hook where the project has them); `resolve`, `verify`,
  `fetch`, `restore` and `watch` are online and on demand, never from a gate.
The `library` skill is installed for the project's agent as well (the `research` plugin, or `npx skills add`).
"""


def do_init(root, a):
    """Write library.toml and the library's directories; refuse over an existing library.toml."""
    toml = root / "library.toml"
    if toml.is_file() and not a.force:
        raise Refused(f"{toml} exists (use --force to overwrite the bindings file alone)")
    q = lambda xs: ", ".join(f'"{x}"' for x in xs)
    text = INIT_TOML.format(dir=a.dir, kept=f'kept = "{a.dir}/kept"             # TRACKED: copies nothing can fetch again\n' if a.kept else
                            f'# kept = "{a.dir}/kept"           # TRACKED: copies nothing can fetch again (obtained by hand, no address)\n',
                            scan=q(a.scan or [f"{a.dir}/cards"]), documents=q(a.documents or []), internal=q(a.internal or []))
    toml.write_text(text, encoding="utf-8")
    written = ["library.toml"]
    cfg = Config(root)
    cfg.cards.mkdir(parents=True, exist_ok=True)
    gi = cfg.dir / ".gitignore"
    if not gi.is_file():
        gi.write_text(".store/\n", encoding="utf-8")
        written.append(rel(cfg, gi))
    if a.kept:
        (root / a.dir / "kept").mkdir(parents=True, exist_ok=True)
        keep = root / a.dir / "kept" / ".gitkeep"
        keep.write_text("")
        written.append(rel(cfg, keep))
    for d in a.internal or []:
        (root / d).mkdir(parents=True, exist_ok=True)
    cards, _ = load_all(cfg)
    write_whole(cfg.index, render_index(cfg, cards))
    written.append(rel(cfg, cfg.index))
    return written


SOURCE = Path(__file__).read_text(encoding="utf-8")


def selftest():
    failures = []

    planted = set()

    def expect(name, cond):
        print(f"  {'ok ' if cond else 'BAD'} {name}")
        if not cond:
            failures.append(name)
        if name.startswith("planted:"):
            planted.update(re.findall(r"→ (L\d+)", name))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "library.toml").write_text(SELFTEST_TOML)
        (root / "records").mkdir()
        cfg = Config(root)
        today = "2026-10-13"

        def run(argv, ok=True):
            rc, payload = dispatch(cfg, argv, today=today, as_json=True, quiet=True)
            expect(" ".join(argv[:2]) + (" refused" if not ok else ""), (rc == 0) == ok)
            if (rc == 0) != ok:
                for pr in payload["problems"]:
                    print("      ", pr["code"], pr.get("path") or pr.get("key"), pr["msg"])
            return payload

        p = run(["register", "Aperiodicity in cellular automata", "--kind", "article", "--author", "Jen, E.",
                 "--year", "1990", "--doi", "https://doi.org/10.1/x", "--tag", "automata",
                 "--note", "States the lemma on columns. It is used in one section."])
        s1 = p["created"][0]
        expect("key is first surname and year", s1 == "jen1990")
        expect("a new card is unread, typed by hand", p["records"][0]["read"]["grade"] == "unread"
               and p["records"][0]["metadata"]["from"] == "hand")
        expect("an identifier is stored without its resolver prefix", p["records"][0]["doi"] == "10.1/x")
        expect("the card is cards/<key>.md", (cfg.cards / "jen1990.md").is_file())
        expect("a note is reflowed to one sentence per line",
               "columns.\nIt is used" in (cfg.cards / "jen1990.md").read_text())
        p = run(["register", "A second paper", "--kind", "article", "--author", "Jen, E.", "--year", "1990", "--tag", "automata"])
        s2 = p["created"][0]
        expect("a key clash gains a letter", s2 == "jen1990b")
        run(["register", "A duplicate", "--kind", "article", "--author", "Other, A.", "--year", "1991", "--doi", "10.1/X"], ok=False)
        run(["register", "Ungraded and new", "--kind", "book", "--read", "ungraded"], ok=False)
        run(["register", "Parts unnamed", "--kind", "book", "--read", "parts"], ok=False)
        run(["register", "Read tomorrow", "--kind", "book", "--read", "full", "--read-on", "2999-01-01"], ok=False)
        run(["register", "No such kind", "--kind", "scroll"], ok=False)
        run(["register", "A taken key", "--kind", "book", "--key", "jen1990"], ok=False)
        p = run(["register", "Étude sur les suites: substitutions", "--kind", "book", "--author", "Queffélec, M.",
                 "--year", "1987", "--arxiv", "arXiv:0903.1627v2", "--seed"])
        s3 = p["created"][0]
        expect("a seeded card is ungraded, its key folded to ascii",
               p["records"][0]["read"]["grade"] == "ungraded" and s3 == "queffelec1987")
        expect("an arXiv identifier is stored without prefix or version", p["records"][0]["arxiv"] == "0903.1627")
        c = parse(cfg.cards / "queffelec1987.md")
        expect("front matter round-trips a title with a colon, an accent and a numeric identifier",
               c["title"] == "Étude sur les suites: substitutions" and c["arxiv"] == "0903.1627" and c["year"] == 1987)
        run(["read", "jen1990", "--grade", "parts"], ok=False)
        p = run(["read", "jen1990", "--grade", "parts", "--what", "sections 1 to 3", "--note", "Lemma 2 read at the journal."])
        expect("read sets the grade and its date", p["records"][0]["read"] == {"grade": "parts", "on": today, "what": "sections 1 to 3"})
        expect("a read's note is dated under Notes", f"{today} — Lemma 2 read" in sections(parse(cfg.cards / "jen1990.md").body)["Notes"])
        run(["read", s3, "--grade", "unread", "--via", s1])
        run(["read", s3, "--grade", "unread", "--via", s3], ok=False)
        run(["note", s1, "--note", "A second remark. It is ours.", "--tag", "columns", "--tag", "automata"])
        t1 = (cfg.cards / "jen1990.md").read_text()
        expect("a note is dated, reflowed and lands under Notes",
               f"{today} — A second remark.\nIt is ours." in t1 and t1.index("A second remark") < t1.index("## Extracts"))
        expect("a tag is added once", parse(cfg.cards / "jen1990.md")["tags"] == ["automata", "columns"])
        (cfg.cards / "jen1990.md").write_text(t1.rstrip("\n") + "\n\n## By hand\n\nA section the tool did not write.\n")
        run(["note", s1, "--note", "A third remark."])
        t1 = (cfg.cards / "jen1990.md").read_text()
        expect("a note keeps a section the tool did not write, after Extracts, as it stood",
               "A third remark." in t1 and t1.endswith("## By hand\n\nA section the tool did not write.\n")
               and t1.index("## Extracts") < t1.index("## By hand"))
        (cfg.cards / "jen1990.md").write_text(t1[:t1.index("\n## By hand")] + "\n")
        run(["note", s1], ok=False)
        run(["relate", s1, s1], ok=False)
        run(["relate", s1, "jen1990b"])
        (root / "records" / "a.md").write_text("An idea citing lib:jen1990 and lib:queffelec1987 together.\n")
        rc, pl = dispatch(cfg, ["related", "jen1990"], today=today, as_json=True, quiet=True)
        why = {r["key"]: " ".join(r["why"]) for r in pl["records"]}
        expect("related ranks a linked card first, with its reasons",
               rc == 0 and pl["records"][0]["key"] == s2 and "linked" in why[s2] and "tags" in why[s2])
        expect("related finds a card cited in the same file", "cited together" in why.get(s3, "") and "known through" in why.get(s3, ""))
        rc, pl = dispatch(cfg, ["cited", "jen1990"], today=today, as_json=True, quiet=True)
        expect("cited computes the sites from the configured paths", rc == 0 and [s["path"] for s in pl["sites"]] == ["records/a.md"])
        rc, pl = dispatch(cfg, ["show", "10.1/X"], today=today, as_json=True, quiet=True)
        expect("show takes an identifier", rc == 0 and pl["records"][0]["key"] == "jen1990" and pl["cited"] == 1)
        rc, pl = dispatch(cfg, ["show", "nobody2000"], today=today, as_json=True, quiet=True)
        expect("show refuses a key that is no card", rc == 1)
        rc, pl = dispatch(cfg, ["find", "cellular", "lemma"], today=today, as_json=True, quiet=True)
        expect("find ranks the card matching in title and notes first, naming the fields",
               rc == 0 and pl["records"][0]["key"] == "jen1990" and {"title", "notes"} <= set(pl["records"][0]["matched"]))
        fts = pl["rankers"][0].startswith("fts5")
        expect("find's first line names the rankers that ran", bool(pl["rankers"]))
        rc, pl = dispatch(cfg, ["find", "etude"], today=today, as_json=True, quiet=True)
        expect("find folds diacritics", [r["key"] for r in pl["records"]] == [s3])
        if fts:
            rc, pl = dispatch(cfg, ["find", "aperiodic"], today=today, as_json=True, quiet=True)
            expect("find stems a word", [r["key"] for r in pl["records"]] == [s1])
            expect("the index is kept in the store", (cfg.store / "index.sqlite").is_file())
        else:
            print("  --  stemming not tested: this SQLite has no FTS5")
        rc, pl = dispatch(cfg, ["find", "--grade", "parts"], today=today, as_json=True, quiet=True)
        expect("find filters by read grade", [r["key"] for r in pl["records"]] == [s1])
        rc, pl = dispatch(cfg, ["find", "--tag", "automata", "--limit", "1"], today=today, as_json=True, quiet=True)
        expect("find is bounded and says where to continue", len(pl["records"]) == 1 and pl["total"] == 2 and pl["next"] == 1)
        rc, pl = dispatch(cfg, ["find", "--id", "arXiv:0903.1627"], today=today, as_json=True, quiet=True)
        expect("find filters by an identifier", [r["key"] for r in pl["records"]] == [s3])
        run(["register", "A work to set aside", "--kind", "web", "--key", "aside"])
        run(["exclude", "aside"], ok=False)
        run(["exclude", "aside", "--reason", "not the work the entry meant"])
        rc, pl = dispatch(cfg, ["find", "aside"], today=today, as_json=True, quiet=True)
        expect("an excluded card is not found unless asked for", pl["records"] == [])
        rc, pl = dispatch(cfg, ["find", "aside", "--state", "excluded"], today=today, as_json=True, quiet=True)
        expect("an excluded card is found by its state", [r["key"] for r in pl["records"]] == ["aside"])
        rc, pl = dispatch(cfg, ["keys"], today=today, as_json=True, quiet=True)
        expect("keys answers a consumer: the cite prefix, each key's state and grade",
               pl["cite_prefix"] == "lib:" and pl["cards"]["jen1990"] == {"state": "registered", "grade": "parts", "extracts": []}
               and pl["cards"]["aside"]["state"] == "excluded")
        (cfg.store / "jen1990").mkdir(parents=True, exist_ok=True)
        (cfg.store / "jen1990" / "copy.pdf").write_bytes(b"the copy")
        p = run(["check"])
        expect("check green on the happy path", not p["problems"])
        expect("a writer refreshes the index", "`jen1990` — Jen (1990) — Aperiodicity" in cfg.index.read_text())

        # planted defects: each must be caught by the check with its code
        def snapshot():
            return {p: p.read_bytes() for p in list(cfg.cards.glob("*.md")) + [cfg.index]}

        def plant(name, code, mutate):
            saved = snapshot()
            mutate()
            cards, broken = load_all(cfg)
            problems, _ = validate(cfg, cards, broken, today)
            expect(f"planted: {name} → {code}", any(p["code"] == code for p in problems))
            for stray in cfg.cards.glob("*.md"):
                if stray not in saved:
                    stray.unlink()
            for path, data in saved.items():
                path.write_bytes(data)

        def edit(key, fn):
            c = parse(cfg.cards / f"{key}.md")
            fn(c.fm)
            c.path.write_text(render(c.fm, c.body))

        def text_edit(key, fn):
            p = cfg.cards / f"{key}.md"
            p.write_text(fn(p.read_text()))

        plant("front matter outside the subset", "L0", lambda: text_edit(s2, lambda t: t.replace("title: \"A second paper\"", "title: A second: paper")))
        plant("two cards with one key", "L1", lambda: edit(s2, lambda fm: fm.update(key="jen1990")))
        plant("a file name outside the key's character set", "L1", lambda: (cfg.cards / "jen1990b.md").rename(cfg.cards / "Jen_1990.md"))
        plant("unknown field", "L2", lambda: edit(s2, lambda fm: fm.update(mood="good")))
        plant("unknown kind", "L2", lambda: edit(s2, lambda fm: fm.update(kind="scroll")))
        plant("two cards with one DOI", "L3", lambda: edit(s2, lambda fm: fm.update(doi="10.1/X")))
        plant("unknown read grade", "L4", lambda: edit(s2, lambda fm: fm["read"].update(grade="glanced")))
        plant("a card that was not seeded ungraded", "L4", lambda: edit(s2, lambda fm: fm["read"].update(grade="ungraded")))
        plant("read in parts with the parts unnamed", "L4", lambda: edit(s1, lambda fm: fm["read"].update(what=None)))
        plant("read with no date", "L4", lambda: edit(s1, lambda fm: fm["read"].update(on=None)))
        plant("a one-sided related link", "L5", lambda: edit(s2, lambda fm: fm.update(related=[])))
        plant("known through a card that does not exist", "L5", lambda: edit(s3, lambda fm: fm.update(via="nobody2000")))
        plant("known through something that is not a card", "L5", lambda: edit(s3, lambda fm: fm.update(via="question-0001")))
        plant("a body citing a key that is no card", "L5", lambda: text_edit(s2, lambda t: t.replace("## Notes\n", "## Notes\n\nSee lib:nobody2000.\n")))
        plant("a copy that does not match its hash", "L6",
              lambda: edit(s1, lambda fm: fm.update(copy={"path": "library/.store/jen1990/copy.pdf", "sha256": "0" * 64, "fetched": today, "version": None})))
        plant("a copy outside the store", "L6",
              lambda: edit(s1, lambda fm: fm.update(copy={"path": "records/a.md", "sha256": "0" * 64, "fetched": today, "version": None})))
        plant("excluded with no reason", "L7", lambda: edit(s2, lambda fm: fm.update(state="excluded")))
        plant("a date in the future", "L8", lambda: edit(s2, lambda fm: fm.update(created="2027-01-01")))
        plant("body not one sentence per line", "L9", lambda: text_edit(s2, lambda t: t.replace("## Notes\n", "## Notes\n\nOne sentence. Two sentences on a line.\n")))
        plant("a section that is neither Notes nor Extracts", "L10", lambda: text_edit(s2, lambda t: t + "\n## Verdict\n"))
        plant("a title changed with the index left as it was", "L11", lambda: edit(s1, lambda fm: fm.update(title="Another title")))
        plant("a hand-edited index", "L11", lambda: cfg.index.write_text(cfg.index.read_text() + "x\n"))
        good = {"path": "library/.store/jen1990/copy.pdf", "sha256": file_sha256(cfg.store / "jen1990" / "copy.pdf"),
                "fetched": today, "version": None}
        edit(s1, lambda fm: fm.update(copy=good))
        cards, broken = load_all(cfg)
        problems, cov = validate(cfg, cards, broken, today)
        expect("a copy matching its hash is counted as verified", not problems and cov["copies_present"] == 1)
        (cfg.store / "jen1990" / "copy.pdf").unlink()
        problems, cov = validate(cfg, cards, broken, today)
        expect("a recorded copy not on disk is counted, never failed", not problems and cov["copies_absent"] == 1)

        # kept copies: a file taken in by hand, its text by page, the search of that text
        hand = root / "scan.pdf"
        hand.write_bytes(b"%PDF\nthe first page states the lemma on columns\fthe second page proves aperiodicity\f")
        p = run(["keep", s2, str(hand)])
        cp = p["records"][0]["copy"] if p["records"] else {}
        expect("a file obtained by hand is kept in the store with its hash, date and page count",
               cp.get("path") == f"library/.store/{s2}/copy.pdf" and cp["pages"] == 2 and cp["text"] == "yes" and cp["from"] is None
               and cp["sha256"] == file_sha256(hand) and cp["fetched"] == today)
        run(["keep", s2, str(hand)], ok=False)
        run(["keep", s2, str(cfg.root / cp["path"]), "--replace", "--move"])
        expect("re-keeping the copy from its own path with --move leaves it on disk", (cfg.root / cp["path"]).is_file())
        run(["keep", s2, str(hand), "--on", "someday", "--replace"], ok=False)
        rc, pl = dispatch(cfg, ["page", s2, "2"], today=today, as_json=True, quiet=True)
        expect("one page of the kept text is printed", rc == 0 and pl["text"].strip() == "the second page proves aperiodicity")
        rc, pl = dispatch(cfg, ["find", "--text", "aperiodicity", "proves"], today=today, as_json=True, quiet=True)
        expect("a text query returns a snippet addressed by key and page",
               [(h["key"], h["unit"], h["label"]) for h in pl["hits"]] == [(s2, 2, "p. 2")] and "aperiodicity" in pl["hits"][0]["snippet"])
        tex = root / "paper.tex"
        tex.write_text("\\documentclass{article}\n\\begin{document}\nAn abstract. % a remark to ourselves\n"
                       "\\section{Preliminaries}\nWe fix notation.\n\\section*{The main theorem}\nEvery column is periodic.\n\\end{document}\n")
        p = run(["keep", s3, str(tex), "--from", "https://example.org/paper.tex", "--version", "v2", "--on", "2026-09-01"])
        cp = p["records"][0]["copy"] if p["records"] else {}
        rc, pl = dispatch(cfg, ["page", s3], today=today, as_json=True, quiet=True)
        expect("a TeX source is kept by section under each section's title, its comments dropped",
               cp.get("pages") == 3 and cp["version"] == "v2" and cp["fetched"] == "2026-09-01"
               and [u["label"] for u in pl["units"]] == ["front matter", "§1 Preliminaries", "§2 The main theorem"]
               and "remark to ourselves" not in (cfg.store / s3 / "text" / "0001.txt").read_text())
        blank = root / "image.pdf"
        blank.write_bytes(b"%PDF\n\f\f")
        p = run(["keep", "aside", str(blank), "--move"])
        expect("a copy with no text in it is recorded as such, and --move takes the file",
               p["records"] and p["records"][0]["copy"]["text"] == "none" and p["records"][0]["copy"]["pages"] == 2 and not blank.exists())
        cards, broken = load_all(cfg)
        problems, cov = validate(cfg, cards, broken, today)
        expect("the check names the copies obtained by hand and counts the ones with no text",
               not problems and cov["copies_by_hand"] == sorted(["aside", s1, s2]) and cov["copies_no_text"] == 1)
        kept = cfg.store / s2 / "copy.pdf"
        saved = kept.read_bytes()
        kept.write_bytes(saved + b" a later hand")
        problems, _ = validate(cfg, cards, broken, today)
        expect("planted: a kept copy changed on disk → L6", any(pr["code"] == "L6" and pr["key"] == s2 for pr in problems))
        kept.write_bytes(saved)
        # extracts: addressed, and borne out by the kept text where a copy is kept
        hand.write_bytes(b"%PDF\nTheorem 4. the first page states the lemma on columns\fthe second page proves aperi-\nodicity of every column\f")
        victim = cfg.root / "not-a-copy.txt"
        victim.write_text("the project's own file")
        edit(s2, lambda fm: fm["copy"].update(path="not-a-copy.txt"))
        run(["keep", s2, str(hand), "--replace"])
        expect("a replaced copy recorded outside the store and the kept directory is left on disk", victim.is_file())
        run(["read", s2, "--grade", "parts", "--what", "both pages"])
        run(["extract", s2, "thm4", "--at", "Theorem 4", "--says", "Later.", "--on", "2999-01-01"], ok=False)  # dated in the future
        p = run(["extract", s2, "thm4", "--at", "Theorem 4", "--quote", "the first page states the lemma on columns",
                 "--quote", "proves aperiodicity of `every` column", "--caveat", "On the line only.", "--rule", "Cite it for columns. Never for rows.",
                 "--edition", "the scan"])
        t2 = (cfg.cards / f"{s2}.md").read_text()
        exs, wrong = parse_extracts(sections(parse(cfg.cards / f"{s2}.md").body)["Extracts"])
        expect("an extract is written with its id, locator, date and edition, and reads back",
               not wrong and [(e["id"], e["at"], e["checked"], e["edition"]) for e in exs] == [("thm4", "Theorem 4", today, "the scan")]
               and f"**thm4** — Theorem 4 — checked {today}, the scan" in t2 and ex_get(exs[0], "Rule") == ["Cite it for columns.\nNever for rows."])
        cards, broken = load_all(cfg)
        problems, cov = validate(cfg, cards, broken, today)
        expect("a quotation and a numbered locator found in the kept text anchor the extract, a line-end hyphen closed",
               not problems and cov["extracts"] == 1 and cov["extracts_anchored"] == 1)
        run(["extract", s2, "thm4", "--at", "Theorem 4", "--says", "again"], ok=False)
        run(["extract", s2, "thm9", "--at", "Theorem 9", "--says", "It restates the lemma."])
        problems, _ = validate(cfg, *load_all(cfg), today)
        expect("planted: a theorem number absent from the kept text → L15",
               any(pr["code"] == "L15" and "theorem 9" in pr["msg"] for pr in problems))
        run(["extract", s2, "thm9", "--at", "Theorem 4", "--quote", "the second page disproves it", "--replace"])
        problems, _ = validate(cfg, *load_all(cfg), today)
        expect("planted: a quotation that is not in the kept text → L15",
               any(pr["code"] == "L15" and "quotation is not in the kept text" in pr["msg"] for pr in problems))
        run(["extract", s2, "thm9", "--at", "Theorem 9 of the journal version", "--says", "It restates the lemma.", "--replace",
             "--unanchored", "read in the journal's version; the kept copy is the scan of the preprint"])
        run(["extract", s3, "main", "--at", "§2, the main theorem", "--quote", "Every column is periodic."])
        run(["extract", s3, "none", "--at", "§5", "--says", "A fifth section."])
        run(["extract", s3, "wrong", "--at", "§2", "--quote", "Every column is aperiodic."])
        run(["read", "aside", "--grade", "skimmed"])
        run(["extract", "aside", "blank", "--at", "page 1", "--says", "Nothing can be read on it."])
        run(["extract", s1, "lemma", "--at", "§3", "--says", "Two periodic columns bound the columns between."])
        cards, broken = load_all(cfg)
        problems, cov = validate(cfg, cards, broken, today)
        expect("another edition, a copy with no text and a copy not on disk are counted unanchored with their reasons; in a TeX source a quotation is looked for and a number is not",
               [(pr["code"], "wrong" in pr["msg"]) for pr in problems] == [("L15", True)] and cov["extracts_anchored"] == 3
               and cov["extracts_unanchored"] == {"declared": 1, "the copy has no text in it": 1, "the copy is not on disk": 1})
        run(["extract", s3, "wrong", "--at", "§2", "--says", "The second section.", "--replace"])
        rc, pl = dispatch(cfg, ["keys"], today=today, as_json=True, quiet=True)
        expect("keys answers a consumer with each card's extract ids", pl["cards"][s3]["extracts"] == ["main", "none", "wrong"])
        (root / "records" / "r.md").write_text(f"As lib:{s3}#main states, and lib:{s3}#nowhere does not.\n")
        add = cfg.cards / "citer.md"
        run(["register", "A card citing an extract", "--kind", "web", "--key", "citer", "--note", f"See lib:{s3}#nowhere."])
        expect("planted: a card citing an extract that is not there → L5",
               any(pr["code"] == "L5" and "#nowhere" in pr["msg"] for pr in validate(cfg, *load_all(cfg), today)[0]))
        add.unlink()
        (root / "records" / "r.md").unlink()
        expect("an extract on an unread card known through another card is allowed", parse(cfg.cards / f"{s3}.md")["via"] == s1
               and not [pr for pr in validate(cfg, *load_all(cfg), today)[0] if pr["code"] == "L16"])
        run(["read", s2, "--grade", "unread"])
        run(["extract", s2, "late", "--at", "Theorem 5", "--says", "More."], ok=False)  # unread, known through no card
        expect("planted: an extract on a card graded unread and known through no card → L16",
               any(pr["code"] == "L16" and "unread" in pr["msg"] for pr in validate(cfg, *load_all(cfg), today)[0]))
        run(["read", s2, "--grade", "parts", "--what", "both pages"])
        body = parse(cfg.cards / f"{s3}.md")
        (cfg.cards / f"{s3}.md").write_text((cfg.cards / f"{s3}.md").read_text() + "\nA line with no head above it and no label.\n\n**bad** — nowhere\n")
        expect("planted: an extract section not in the addressed form → L16",
               any(pr["code"] == "L16" for pr in validate(cfg, *load_all(cfg), today)[0]))
        (cfg.cards / f"{s3}.md").write_text(render(body.fm, body.body))
        run(["index"])
        kept = cfg.store / s2 / "copy.pdf"
        saved = kept.read_bytes()
        page = root / "page.html"
        page.write_text("<!DOCTYPE html><html><body>a landing page</body></html>")
        run(["keep", s2, str(page), "--replace"], ok=False)
        expect("a refused replacement leaves the kept copy in place", kept.read_bytes() == saved)

        # online, against canned answers in each interface's own shape: no call leaves the machine
        global FETCH
        real, calls = FETCH, []
        csl = lambda **kw: json.dumps(kw).encode()
        kari = csl(type="journal-article", title="Reversibility of 2D cellular automata is undecidable",
                   author=[{"given": "Jarkko", "family": "Kari"}], issued={"date-parts": [[1990, 9]]},
                   **{"container-title": "Physica D: Nonlinear Phenomena", "DOI": "10.1016/0167-2789(90)90195-u"})
        soliton = {"DOI": "10.1016/0167-2789(90)90191-q", "type": "journal-article", "score": 46.8,
                   "title": ["Soliton turbulence in one-dimensional cellular automata"], "issued": {"date-parts": [[1990, 9]]},
                   "author": [{"family": "Aizawa", "given": "Y."}], "container-title": ["Physica D: Nonlinear Phenomena"]}
        brummitt = {"DOI": "10.25088/ComplexSystems.21.2.85", "type": "journal-article", "score": 71.0,
                    "title": ["Boundary Growth in One-Dimensional Cellular Automata"], "issued": {"date-parts": [[2012, 6, 15]]},
                    "author": [{"family": "Brummitt", "given": "Charles D."}, {"family": "Rowland", "given": "Eric"}],
                    "container-title": ["Complex Systems"]}
        barany = {"DOI": "10.1088/0951-7715/25/6/1753", "type": "journal-article", "score": 60.0,
                  "title": ["Slicing the Sierpiński gasket"], "issued": {"date-parts": [[2012, 5, 15]]},
                  "author": [{"family": "Bárány", "given": "Balázs"}, {"family": "Ferguson", "given": "Andrew"},
                             {"family": "Simon", "given": "Károly"}], "container-title": ["Nonlinearity"]}
        feed = ('<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom"><entry>'
                '<id>http://arxiv.org/abs/%sv3</id><title>%s</title><published>%s-08-08T19:59:11Z</published>'
                '%s</entry></feed>')
        name = "<author><name>%s</name></author>"
        net = [("doi.org/10.1016/0167-2789(90)90195-u", (200, kari)),
               ("doi.org/10.9/kneser", (200, csl(type="journal-article", title="Absch�tzung der asymptotischen Dichte von Summenmengen",
                                               author=[{"given": "Martin", "family": "Kneser"}], issued={"date-parts": [[1953]]},
                                               **{"container-title": "Mathematische Zeitschrift", "DOI": "10.9/kneser"}))),
               ("doi.org/10.9/gone", (404, b"")),
               ("doi.org/10.9/nipkow", (200, csl(type="journal-article", title="Amortized Complexity Verified",
                                               author=[{"given": "Tobias", "family": "Nipkow"}, {"given": "Hauke", "family": "Brinkop"}],
                                               issued={"date-parts": [[2018, 3, 15]]}, **{"published-print": {"date-parts": [[2019, 3]]},
                                               "container-title": "Journal of Automated Reasoning", "DOI": "10.9/nipkow"}))),
               ("crossref.org/works?query.bibliographic=Brummitt", (200, json.dumps({"message": {"items": [soliton, brummitt]}}).encode())),
               ("crossref.org/works?query.bibliographic=B%C3%A1r%C3%A1ny", (200, json.dumps({"message": {"items": [barany]}}).encode())),
               ("crossref.org/works?query.bibliographic=Ceccherini", (200, json.dumps({"message": {"items": [{
                   "DOI": "10.1007/978-3-642-14034-1_1", "type": "book-chapter", "title": ["Cellular Automata"],
                   "issued": {"date-parts": [[2010]]}, "container-title": ["Cellular Automata and Groups"],
                   "author": [{"family": "Ceccherini-Silberstein", "given": "Tullio"}, {"family": "Coornaert", "given": "Michel"}]}]}}).encode())),
               ("crossref.org/works?query.bibliographic=Turing", (200, json.dumps({"message": {"items": [{
                   "DOI": "10.1112/plms/s2-45.1.161", "type": "journal-article", "issued": {"date-parts": [[1939]]},
                   "title": ["Systems of Logic Based on Ordinals<sup>\u2020</sup> &amp;amp; more"],
                   "author": [{"family": "Turing", "given": "A. M."}],
                   "container-title": ["Proceedings of the London Mathematical Society"]}]}}).encode())),
               ("crossref.org/works", (200, json.dumps({"message": {"items": [soliton]}}).encode())),
               ("openalex.org/works", (200, json.dumps({"results": [{
                   "id": "https://openalex.org/W1974030502", "doi": "https://doi.org/10.1088/0951-7715/6/6/010",
                   "title": "Partially permutive cellular automata", "publication_year": 1993, "type": "article",
                   "authorships": [{"author": {"display_name": "Kari Eloranta"}}],
                   "primary_location": {"source": {"display_name": "Nonlinearity"}}, "locations": []}]}).encode())),
               ("id_list=1108.1791", (200, (feed % ("1108.1791", "Why Philosophers Should Care About\n  Computational Complexity",
                                                   "2011", name % "Scott Aaronson")).encode())),
               ("id_list=1301.7077", (200, (feed % ("1301.7077", "Slicing the Sierpiński gasket", "2013",
                                                   "".join(name % n for n in ("Balázs Bárány", "Andrew Ferguson", "Károly Simon")))).encode())),
               ("zbmath.org", (200, json.dumps({"result": [{
                   "identifier": "0729.68057", "title": {"title": "Aperiodicity in one-dimensional cellular automata"}, "year": "1990",
                   "document_type": {"code": "j"}, "contributors": {"authors": [{"name": "Jen, Erica"}]},
                   "source": {"series": [{"title": "Physica D"}]},
                   "links": [{"type": "doi", "identifier": "10.1016/0167-2789(90)90169-P"}]}]}).encode()))]

        def fake(url, headers):
            calls.append((url, headers))
            return next((ans for part, ans in net if part in url), (0, b"nothing answers"))

        FETCH = fake
        os.environ.pop("LIBRARY_MAILTO", None)
        before = set(cfg.cards.glob("*.md"))
        p = run(["resolve", "Kari, J. (1990). Reversibility of 2D cellular automata is undecidable. *Physica D* 45, 379–385. "
                            "doi:10.1016/0167-2789(90)90195-u.", "--register"])
        k = p["records"][0] if p["records"] else {}
        expect("an entry carrying a DOI is resolved at it and the tool types the card",
               p["created"] == ["kari1990"] and k["authors"] == ["Kari, J."] and k["kind"] == "article" and k["year"] == 1990
               and k["metadata"] == {"from": "doi", "on": today, "typed": None} and k["verified"] == {"on": today, "by": "doi"})
        expect("one call, no search made once a candidate has passed, no address sent with no setup",
               len(calls) == 1 and "csl+json" in calls[0][1]["Accept"] and "mailto" not in calls[0][1]["User-Agent"])
        calls.clear()
        p = run(["resolve", "Nobody, A. (2001). An unfindable work on nothing. Journal of Nothing 1.", "--register"], ok=False)
        expect("planted: a wrong-paper candidate at every interface → nothing written",
               set(cfg.cards.glob("*.md")) - before == {cfg.cards / "kari1990.md"} and sum("FAIL" in ln for ln in p["lines"]) == 2
               and ["crossref" in calls[0][0], "openalex" in calls[1][0]] == [True, True])
        jen = "Jen, E. (1990). Aperiodicity in one-dimensional cellular automata. Physica D 45, 3–18."
        p = run(["resolve", jen, "--doi", "10.1016/0167-2789(90)90195-u", "--pick", "1", "--register"], ok=False)
        expect("planted: a DOI that resolves to another work → refused, the candidate printed beside the entry",
               not p["created"] and any("needs --override" in pr["msg"] for pr in p["problems"]))
        nobody = "Nobody, A. (2001). An unfindable work on nothing. Journal of Nothing 1."
        run(["resolve", nobody, "--override", "a damaged record", "--register"], ok=False)  # --override takes --pick
        p = run(["resolve", nobody, "--pick", "1", "--override", "a damaged record", "--register", "--key", "nobody2001x"])
        ov = parse(cfg.cards / "nobody2001x.md")
        expect("an override registers the candidate with the reason in its notes and no verify stamp",
               p["created"] == ["nobody2001x"] and ov["verified"] is None and "a damaged record" in ov.body)
        (cfg.cards / "nobody2001x.md").unlink()
        calls.clear()
        p = run(["resolve", "Brummitt, C.D. & Rowland, E. (2012). Boundary growth in one-dimensional cellular automata. "
                            "*Complex Systems* 21, 85–116.", "--register", "--venue", "Complex Systems 21"])
        k = p["records"][0] if p["records"] else {}
        expect("a free-text entry: the second candidate passes, the first is printed as failing, the next interface is not asked",
               p["created"] == ["brummitt2012"] and k["authors"] == ["Brummitt, C.D.", "Rowland, E."] and len(calls) == 1
               and k["doi"] == "10.25088/ComplexSystems.21.2.85" and "1. FAIL" in "\n".join(p["lines"]))
        expect("a field typed by the hand is kept and marked, the difference printed",
               k.get("venue") == "Complex Systems 21" and k["metadata"]["typed"] == "venue"
               and any("venue is kept as typed" in ln for ln in p["lines"]))
        p = run(["resolve", "Bárány, B., Ferguson, A. & Simon, K. (2012). Slicing the Sierpiński gasket. *Nonlinearity* 25, "
                            "1753–1770; arXiv:1301.7077.", "--register"])
        k = p["records"][0] if p["records"] else {}
        expect("a preprint and its published version are one card carrying both identifiers",
               p["created"] == ["barany2012"] and k["doi"] == "10.1088/0951-7715/25/6/1753" and k["arxiv"] == "1301.7077"
               and k["metadata"]["from"] == "crossref" and k["year"] == 2012)
        p = run(["resolve", "Aaronson, S. (2011). Why philosophers should care about computational complexity. arXiv:1108.1791.",
                 "--register", "--seed"])
        k = p["records"][0] if p["records"] else {}
        expect("an arXiv identifier is resolved at arXiv; a seeded card is ungraded",
               p["created"] == ["aaronson2011"] and k["kind"] == "preprint" and k["authors"] == ["Aaronson, S."]
               and k["title"] == "Why Philosophers Should Care About Computational Complexity" and k["read"]["grade"] == "ungraded")
        run(["resolve", "Kari, J. (1990). Reversibility of 2D cellular automata is undecidable. doi:10.1016/0167-2789(90)90195-u.",
             "--register"], ok=False)  # the DOI is a card already
        p = run(["resolve", "Ceccherini-Silberstein, T. & Coornaert, M. (2010). *Cellular Automata and Groups.* Springer.", "--register"], ok=False)
        expect("planted: a chapter by the same authors whose short title stands inside the book's → fails the check",
               not p["created"] and "1. FAIL" in "\n".join(p["lines"]))
        p = run(["resolve", "Turing, A. M. (1939). *Systems of logic based on ordinals & more*. Proc. London Math. Soc. s2-45(1), 161–228."])
        expect("a resolver's markup is read out of a title before it is compared or written",
               any("Systems of Logic Based on Ordinals\u2020 & more" in ln and "PASS" in ln for ln in p["lines"]))
        p = run(["resolve", jen, "--at", "zbmath"])
        expect("an optional interface is asked only by name", "zbmath:0729.68057" in "\n".join(p["lines"]) and "1. PASS" in "\n".join(p["lines"]))
        run(["resolve", jen, "--at", "nowhere"], ok=False)
        p = run(["resolve", "Nipkow, T. & Brinkop, H. (2019). Amortized complexity verified. *Journal of Automated Reasoning* 62(3).",
                 "--doi", "10.9/nipkow", "--register"])
        expect("a record's print year is one of its years: the entry's is the one written, and verify does not call it a difference",
               p["records"] and p["records"][0]["year"] == 2019 and any("the entry's 2019 is written" in ln for ln in p["lines"]))
        p = run(["verify", "nipkow2019"])
        expect("verify accepts either year of the record", not any("year differs" in ln for ln in p["lines"]))
        os.environ["LIBRARY_MAILTO"] = "someone@example.org"
        calls.clear()
        p = run(["resolve", "Nobody, A. (2001). An unfindable work on nothing."], ok=False)
        expect("a contact address is sent only when the environment sets one",
               "mailto=someone%40example.org" in calls[0][0] and "mailto:someone@example.org" in calls[0][1]["User-Agent"]
               and "a contact address" in p["lines"][0])
        del os.environ["LIBRARY_MAILTO"]
        run(["register", "Abschätzung der asymptotischen Dichte von Summenmengen", "--kind", "article", "--author", "Kneser, M.",
             "--year", "1953", "--doi", "10.9/kneser"])
        p = run(["verify", "kneser1953"])
        c = parse(cfg.cards / "kneser1953.md")
        expect("planted: a resolver's damaged title → the hand-typed title is left unwritten, the difference printed, the card stamped",
               c["title"] == "Abschätzung der asymptotischen Dichte von Summenmengen" and c["verified"] == {"on": today, "by": "doi"}
               and any("title differs and is left as typed" in ln for ln in p["lines"]))
        (cfg.cards / "kneser1953.md").rename(root / "kneser-kept.md")
        p = run(["resolve", "Kneser, M. (1953). Abschätzung der asymptotischen Dichte von Summenmengen. *Math. Z.* 58, 459–484.",
                 "--doi", "10.9/kneser", "--register", "--key", "kneser-tool"])
        expect("planted: a record's damaged title on a card the tool types → the entry's title is written, and marked",
               p["records"] and p["records"][0]["title"] == "Abschätzung der asymptotischen Dichte von Summenmengen"
               and p["records"][0]["metadata"]["typed"] == "title")
        p = run(["type", "kneser-tool", "--author", "Kneser, Martin"])
        expect("type corrects a field over the resolver's and marks it", p["records"][0]["authors"] == ["Kneser, Martin"]
               and p["records"][0]["metadata"]["typed"] == "title, authors")
        run(["type", "kneser-tool", "--author", "Kneser, Martin"], ok=False)
        (cfg.cards / "kneser-tool.md").unlink()
        (root / "kneser-kept.md").rename(cfg.cards / "kneser1953.md")
        p = run(["verify", "kneser1953", "--take", "venue"])
        expect("verify writes a field only where it is told to", parse(cfg.cards / "kneser1953.md")["venue"] == "Mathematische Zeitschrift")
        run(["register", "Aperiodicity in one-dimensional cellular automata", "--kind", "article", "--author", "Jen, E.",
             "--year", "1990", "--doi", "10.1016/0167-2789(90)90195-U", "--key", "jenwrong"], ok=False)  # that DOI is kari1990's
        (cfg.cards / "kari1990.md").unlink()
        run(["register", "Aperiodicity in one-dimensional cellular automata", "--kind", "article", "--author", "Jen, E.",
             "--year", "1990", "--doi", "10.1016/0167-2789(90)90195-u", "--key", "jenwrong"])
        p = run(["verify", "jenwrong"], ok=False)
        expect("planted: a card whose DOI resolves to another title → verify fails and stamps nothing",
               parse(cfg.cards / "jenwrong.md")["verified"] is None and any("answers another work" in ln for ln in p["lines"]))
        run(["register", "A work whose DOI is gone", "--kind", "article", "--author", "Gone, A.", "--year", "2000", "--doi", "10.9/gone"])
        run(["verify", "gone2000"], ok=False)
        run(["verify", "jen1990b"], ok=False)  # no identifier to ask at
        expect("a card no resolver answered for is not stamped", parse(cfg.cards / "gone2000.md")["verified"] is None)
        p = run(["check"])
        cov = p["coverage"]
        expect("the check counts the cards by where their fields came from and by verify stamp, and asks no resolver",
               not p["problems"] and cov["from_resolver"] == 4 and cov["from_hand"] == 7 and cov["verified"] == 5
               and cov["verified_oldest"] == today)
        plant("a verify stamp that names no resolver", "L2", lambda: edit("kneser1953", lambda fm: fm.update(verified={"on": today, "by": None})))
        expect("a title is guessed only from an entry written in the usual form",
               guess_title("Jen, E. (1990). Aperiodicity in one-dimensional cellular automata. *Physica D* 45.") ==
               "Aperiodicity in one-dimensional cellular automata" and guess_title("some words with no year") is None
               and guess_title("Chalmers, D.J. (1996). Does a rock implement every automaton? *Synthese* 108.") ==
               "Does a rock implement every automaton?"
               and guess_title("Bauer, A. (2024). *Partial combinatory algebras* (Lean 4 development), `a/b`.") == "Partial combinatory algebras")
        expect("names take the card's form", name_of(*split_name("Ludwig van Beethoven")) == "van Beethoven, L."
               and name_of("Bárány", "Balázs") == "Bárány, B." and name_of("Serre", "Jean-Pierre") == "Serre, J.-P.")
        # kept copies, online: a fetch by the card's identifiers, the restore of an emptied store
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for name, body in (("main.tex", "\\documentclass{article}\\begin{document}Slices of the gasket.\n"
                                            "\\section{Rational slopes}\\input{defs}\n\\end{document}"),
                               ("defs.tex", "A slice through a corner. % not for print\n")):
                info, raw = tarfile.TarInfo(name), body.encode()
                info.size = len(raw)
                tar.addfile(info, io.BytesIO(raw))
        src, pdf = buf.getvalue(), b"%PDF\nreversibility\fundecidable in two dimensions\f"
        net[:0] = [("export.arxiv.org/api/query?id_list=1301.7077", (200, b"<feed><entry><id>http://arxiv.org/abs/1301.7077v3</id></entry></feed>")),
                   ("arxiv.org/e-print/1301.7077v3", (200, src)), ("example.org/kari.pdf", (200, pdf)),
                   ("example.org/landing", (200, b"<!DOCTYPE html><html>a landing page</html>"))]
        p = run(["fetch", "barany2012"])
        cp = p["records"][0]["copy"] if p["records"] else {}
        expect("an arXiv work is fetched as its TeX source at its latest version, with hash, date, version and part count",
               cp.get("from") == "https://arxiv.org/e-print/1301.7077v3" and cp["version"] == "v3" and cp["pages"] == 2
               and cp["sha256"] == hashlib.sha256(src).hexdigest() and cp["fetched"] == today and cp["path"].endswith("barany2012/copy.gz"))
        rc, pl = dispatch(cfg, ["find", "--text", "corner"], today=today, as_json=True, quiet=True)
        rc, no = dispatch(cfg, ["find", "--text", "print"], today=today, as_json=True, quiet=True)
        expect("an input file's text is searched inside its section, a comment is not kept",
               [(h["key"], h["unit"], h["label"]) for h in pl["hits"]] == [("barany2012", 2, "§1 Rational slopes")] and not no["hits"])
        run(["register", "A work known by its address", "--kind", "article", "--key", "addressed"])
        run(["fetch", "addressed"], ok=False)
        p = run(["fetch", "addressed", "--url", "https://example.org/landing"], ok=False)
        expect("planted: an address answering a page → nothing kept",
               any("a page, not a file" in ln for ln in p["lines"]) and parse(cfg.cards / "addressed.md")["copy"] is None)
        p = run(["fetch", "addressed", "--url", "https://example.org/kari.pdf"])
        expect("a given address is fetched and recorded as where the copy came from",
               p["records"] and p["records"][0]["copy"]["from"] == "https://example.org/kari.pdf" and p["records"][0]["copy"]["pages"] == 2)
        for k in ("barany2012", "addressed", s2):
            shutil.rmtree(cfg.store / k)
        p = run(["restore"])
        expect("restore rebuilds an emptied store for the fetchable copies, checks their hashes and names the rest",
               (cfg.store / "barany2012" / "copy.gz").read_bytes() == src and (cfg.store / "addressed" / "copy.pdf").read_bytes() == pdf
               and (cfg.store / "addressed" / "text" / "0002.txt").read_text() == "undecidable in two dimensions"
               and sorted(ln.split(":")[0] for ln in p["lines"] if "NEEDS A BACKUP" in ln) == sorted([s1, s2]))
        shutil.rmtree(cfg.store / "addressed")
        net.insert(0, ("example.org/kari.pdf", (200, b"%PDF\nanother printing\f")))
        p = run(["restore", "addressed"], ok=False)
        expect("planted: an address that now answers other bytes → nothing written",
               not (cfg.store / "addressed" / "copy.pdf").exists() and any("other bytes" in ln for ln in p["lines"]))

        # the watch: what is new since it last looked, with no clock kept
        oa = lambda *works: json.dumps({"meta": {"count": len(works)}, "results": [
            {"id": f"https://openalex.org/{i}", "doi": d and f"https://doi.org/{d}", "title": t, "publication_date": on,
             "authorships": [{"author": {"display_name": who}}]} for i, d, t, on, who in works]}).encode()
        fresh, old, carded = (("W222", "10.9/new", "A new slice of the gasket", "2026-05-01", "Ada Newcomer"),
                              ("W223", "10.9/old", "An old slice", "2019-01-01", "Otto Elder"),
                              ("W224", "10.25088/ComplexSystems.21.2.85", "Boundary growth", "2026-02-02", "Charles Brummitt"))
        net[:0] = [("works/doi:10.1088", (200, b'{"id": "https://openalex.org/W111"}')),
                   ("filter=cites%3AW111", (200, oa(fresh, old, carded))),
                   ("works/W111?", (200, b'{"related_works": ["https://openalex.org/W222", "https://openalex.org/W333"]}')),
                   ("filter=openalex%3AW222%7CW333", (200, oa(fresh, ("W333", "10.9/rel", "A related classic", "2001-01-01", "Rhea Lated")))),
                   ("opencitations.net/index/v2/citations/doi:10.25088", (200, json.dumps([
                       {"citing": "omid:br/1 doi:10.9/oc", "creation": "2026-06"}, {"citing": "omid:br/2", "creation": "2026"}]).encode())),
                   ("doi.org/10.9/oc", (200, csl(type="journal-article", title="Growth, cited", author=[{"given": "Cy", "family": "Ting"}],
                                                 issued={"date-parts": [[2026, 6]]}))),
                   ("search_query=", (200, b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2601.00001v1</id>'
                                           b'<title>Automata in a prover</title><published>2026-01-05T00:00:00Z</published>'
                                           b'<author><name>Pat Prover</name></author></entry><entry><id>http://arxiv.org/abs/1108.1791v3</id>'
                                           b'<title>Why philosophers</title><published>2011-08-08T00:00:00Z</published></entry></feed>')),
                   ("api.github.com/search/repositories", (200, json.dumps({"items": [
                       {"full_name": "Someone/ca-lean", "description": "Cellular automata in Lean", "created_at": "2026-03-01T10:00:00Z"},
                       {"full_name": "old/repo", "description": None, "created_at": "2020-01-01T00:00:00Z"}]}).encode()))]
        run(["watch", "--add", "citing-barany", "--citing", "barany2012", "--since", "2026-01-01", "--why", "the slices"])
        run(["watch", "--add", "citing-barany", "--citing", "barany2012"], ok=False)
        run(["watch", "--add", "nameless", "--citing", "addressed"], ok=False)
        run(["watch", "--add", "two-kinds", "--citing", "barany2012", "--arxiv", "all:x"], ok=False)
        p = run(["watch"])
        _, cands = load_watch(cfg)
        expect("planted: an unseen identifier is proposed once; a work dated before the watch and a work that is a card are not",
               [c["ids"] for c in cands] == [["doi:10.9/new", "openalex:W222"]] and cands[0]["authors"] == "Newcomer"
               and sum(ln.startswith("new: ") for ln in p["lines"]) == 1 and any("1 dated before 2026-01-01" in ln and "1 already a card" in ln for ln in p["lines"]))
        held = (cfg.watch_file.read_bytes(), cfg.cand_file.read_bytes(), cfg.watch_file.stat().st_mtime_ns)
        p = run(["watch"])
        expect("a second run right after the first reports nothing new and writes no file",
               not any(ln.startswith("new: ") for ln in p["lines"]) and any("0 new" in ln for ln in p["lines"])
               and held == (cfg.watch_file.read_bytes(), cfg.cand_file.read_bytes(), cfg.watch_file.stat().st_mtime_ns)
               and "since" in load_watch(cfg)[0][0] and not set(load_watch(cfg)[0][0]) & {"checked", "last", "every", "due"})
        run(["candidates", "--exclude", "doi:10.9/new"], ok=False)
        run(["candidates", "--exclude", "doi:10.9/new", "--reason", "about another gasket"])
        run(["watch", "--add", "related-barany", "--related", "barany2012"])
        p = run(["watch", "related-barany"])
        _, cands = load_watch(cfg)
        expect("planted: a candidate set aside is proposed by no other watch, and keeps its reason",
               [(c["ids"][0], c["state"]) for c in cands] == [("doi:10.9/new", "excluded"), ("doi:10.9/rel", "proposed")]
               and "about another gasket" in cands[0]["reason"] and any("1 already a card or a candidate" in ln for ln in p["lines"]))
        run(["watch", "--add", "citing-brummitt", "--citing", "brummitt2012", "--since", "2026-01-01"])
        p = run(["watch", "citing-brummitt"])
        got = [c for c in load_watch(cfg)[1] if c["watch"] == "citing-brummitt"]
        expect("where OpenAlex does not answer the OpenCitations index is asked, and a work it names by identifier alone gets its title where the identifier lives",
               [(c["ids"], c["title"], c["authors"]) for c in got] == [(["doi:10.9/oc"], "Growth, cited", "Ting")]
               and "OpenCitations" in got[0]["why"])
        run(["watch", "--add", "provers", "--arxiv", "all:automata AND all:prover", "--since", "2026-01-01"])
        run(["watch", "--add", "lean-ca", "--github", "cellular automata language:Lean", "--since", "2026-01-01"])
        p = run(["watch", "provers", "lean-ca"])
        got = [c["ids"][0] for c in load_watch(cfg)[1] if c["watch"] in ("provers", "lean-ca")]
        expect("a saved query proposes the new arXiv entry and the new repository, not the carded work nor the old repository",
               got == ["arxiv:2601.00001", "github:someone/ca-lean"])
        run(["register", "ca-lean", "--kind", "repository", "--url", "https://github.com/Someone/ca-lean", "--key", "someone-ca-lean"])
        expect("a candidate registered as a card leaves the list",
               "github:someone/ca-lean" not in [c["ids"][0] for c in load_watch(cfg)[1]])
        run(["watch", "--add", "silent", "--citing", "aaronson2011"])
        before_seen = [w.get("seen") for w in load_watch(cfg)[0]]
        p = run(["watch", "silent"], ok=False)
        expect("an interface that does not answer is said so, and nothing is recorded as seen",
               any("silent: no look" in ln for ln in p["lines"]) and [w.get("seen") for w in load_watch(cfg)[0]] == before_seen)
        rc, pl = dispatch(cfg, ["watch", "--list"], today=today, as_json=True, quiet=True)
        expect("the watches are listed with what each has seen, a watch never run said so",
               any("silent" in ln and "never run" in ln for ln in pl["lines"]) and any("citing-barany" in ln and "6 seen" in ln for ln in pl["lines"]))
        run(["watch", "--drop", "silent"])
        cards, broken = load_all(cfg)
        problems, cov = validate(cfg, cards, broken, today)
        expect("the check counts the watches and the candidates and asks no interface",
               not [pr for pr in problems if pr["code"] == "L14"] and cov["watches"] == 5 and cov["candidates"] == 3 and cov["candidates_excluded"] == 1)
        kept_files = (cfg.watch_file.read_text(), cfg.cand_file.read_text())
        cfg.watch_file.write_text(kept_files[0].replace('card = "brummitt2012"', 'card = "nobody1900"'))
        expect("planted: a watch on a card that is not there → L14", any(pr["code"] == "L14" for pr in validate(cfg, cards, broken, today)[0]))
        cfg.watch_file.write_text(kept_files[0])
        cfg.cand_file.write_text(re.sub(r'reason = .*\n', "", kept_files[1]))
        expect("planted: a candidate set aside with no reason → L14", any(pr["code"] == "L14" for pr in validate(cfg, cards, broken, today)[0]))
        cfg.cand_file.write_text(kept_files[1])
        FETCH = lambda url, headers: (0, b"no route to the host")
        rc, _ = dispatch(cfg, ["resolve", "Nobody, N. (1900). Nothing.", "--arxiv", "1706.03762"], today=today, as_json=True, quiet=True)
        expect("an online command nothing answered exits 2, could not run", rc == 2)
        FETCH = real

        # the tie between a document's reference entries and the cards, offline
        (root / "library.toml").write_text(SELFTEST_TOML + '[entries]\ndocuments = ["papers/*.md"]\n')
        cfg = Config(root)
        (root / "papers").mkdir()
        doc = root / "papers" / "alpha.md"
        head = "# Alpha\n\nBody citing Kneser (1953).\n\n## References\n\nA line that is no entry.\n\n"
        good = ("Kneser, M. (1953). Abschätzung der asymptotischen Dichte von Summenmengen. *Math. Z.* 58, 459–484. (Read at the primary.)\n\n"
                "- Brummitt, C.D. & Rowland, E. (2012). Boundary growth in one-dimensional cellular automata. *Complex Systems* 21. — Read in full.\n\n"
                "van Aaronson, S. (2011). Not an entry of this library.\n")
        doc.write_text(head + good.replace("van Aaronson, S. (2011). Not an entry of this library.\n", "") + "\n## Appendix\n\nJen, E. (1990). Outside the section.\n")
        rc, pl = dispatch(cfg, ["entries"], today=today, as_json=True, quiet=True)
        expect("the entries of a document are read under its heading alone, a list marker and an annotation set aside, each tied to its card",
               [(e["keys"], e["annotation"][:4]) for e in pl["entries"]] == [(["kneser1953"], "(Rea"), (["brummitt2012"], "Read")])
        rc, pl = dispatch(cfg, ["cited", "kneser1953"], today=today, as_json=True, quiet=True)
        expect("cited names the entry tied to the card", [s["path"] for s in pl["sites"]] == ["papers/alpha.md"])
        claimed = head.replace("Body citing Kneser (1953).", "Body citing Kneser (1953).\nWe prove the density bound of Kneser (1953) on the line.\n"
                               "This resolves a question of Brummitt & Rowland (2012).\nKneser (1953) is named here and nothing is claimed.")
        doc.write_text(claimed + good.replace("van Aaronson, S. (2011). Not an entry of this library.\n", "") + "\n## Appendix\n\nJen, E. (1990). Outside the section.\n")
        run(["read", "kneser1953", "--grade", "full"])
        run(["extract", "kneser1953", "density", "--at", "Satz 1", "--says", "It bounds the density of a sum set from below."])
        rc, pl = dispatch(cfg, ["claims"], today=today, as_json=True, quiet=True)
        expect("planted: a claim-shaped sentence naming a work whose card carries no extract is reported as uncovered, a covered one with its extract, a bare mention not at all",
               [(c["key"], c["extracts"], c["line"]) for c in pl["claims"]] == [("kneser1953", ["density"], 4), ("brummitt2012", [], 5)]
               and pl["uncovered"] == 1)
        doc.write_text(head + good.replace("van Aaronson, S. (2011). Not an entry of this library.\n", "") + "\n## Appendix\n\nJen, E. (1990). Outside the section.\n")
        run(["read", "kneser1953", "--grade", "parts", "--what", "the statement", "--undated"], ok=False)  # not seeded
        run(["read", "aaronson2011", "--grade", "full", "--undated"])
        run(["read", "kneser1953", "--grade", "full"])
        run(["read", "brummitt2012", "--grade", "full"])
        p = run(["check"])
        expect("check green with every entry tied; the coverage counts the entries and the tied cards by grade",
               not p["problems"] and p["coverage"]["entries"] == 2 and p["coverage"]["tied_cards"] == 2
               and p["coverage"]["tied_grades"] == {"full": 2} and p["coverage"]["untied_cards"] >= 1)

        def doc_plant(name, code, text, also=None):
            keep = doc.read_text()
            doc.write_text(text)
            plant(name, code, also or (lambda: None))
            doc.write_text(keep)

        # internal documents: a card naming a tracked file, read by section, cited by no bound document
        (root / "library.toml").write_text(SELFTEST_TOML + '[entries]\ndocuments = ["papers/*.md"]\n[internal]\ndirectories = ["reports"]\n')
        cfg = Config(root)
        (root / "reports").mkdir()
        rpt = root / "reports" / "A Survey 2026.md"
        rpt.write_text("# A survey of slices\n\nIt opens here.\n\n## Findings\n\nNobody prices the decoder, the survey finds.\n\n## Sources\n\nMany.\n")
        expect("planted: a document of the project with no card → L17",
               any(pr["code"] == "L17" and pr["path"] == "reports/A Survey 2026.md" for pr in validate(cfg, *load_all(cfg), today)[0]))
        run(["register", "A survey of slices", "--kind", "article", "--file", "reports/A Survey 2026.md"], ok=False)
        run(["register", "A survey with no file", "--kind", "report"], ok=False)
        run(["register", "A survey of slices", "--kind", "report", "--file", "reports/A Survey 2026.md", "--author", "Surveyor, A.",
             "--year", "2026", "--key", "report-survey", "--read", "full"])
        run(["register", "The same survey again", "--kind", "report", "--file", "reports/A Survey 2026.md", "--key", "report-twice"], ok=False)
        rc, pl = dispatch(cfg, ["page", "report-survey"], today=today, as_json=True, quiet=True)
        expect("an internal document is read from its tracked file, by section",
               [u["label"] for u in pl["units"]] == ["A survey of slices", "Findings", "Sources"])
        rc, pl = dispatch(cfg, ["find", "--text", "decoder", "prices"], today=today, as_json=True, quiet=True)
        expect("its text is searched with the kept copies", [(h["key"], h["label"]) for h in pl["hits"]] == [("report-survey", "Findings")])
        run(["extract", "report-survey", "decoder", "--at", "Findings", "--quote", "Nobody prices the decoder", "--rule", "A lead, never a source."])
        run(["extract", "report-survey", "absent", "--at", "Findings", "--quote", "Everybody prices the decoder"])
        problems, cov = validate(cfg, *load_all(cfg), today)
        expect("an extract on an internal document is anchored in its file, and a quotation the file lacks → L15",
               [pr["code"] for pr in problems] == ["L15"] and cov["internal"] == 1)
        run(["extract", "report-survey", "absent", "--at", "Findings", "--says", "It finds nobody does.", "--replace"])
        run(["fetch", "report-survey"], ok=False)
        run(["keep", "report-survey", str(rpt)], ok=False)
        doc_plant("a reference entry naming an internal document", "L12",
                  head + good + "\nSurveyor, A. (2026). A survey of slices. An internal report.\n")
        saved_rpt = rpt.read_text()
        rpt.unlink()
        expect("planted: a card whose file is gone → L17", any(pr["code"] == "L17" and "not in the tree" in pr["msg"] for pr in validate(cfg, *load_all(cfg), today)[0]))
        rpt.write_text(saved_rpt)
        doc_plant("a reference entry with no card", "L12", head + good)
        keep_doc = doc.read_text()
        doc.write_text(keep_doc.replace("Kneser, M. (1953).", "Kneser, M. (1953a).", 1))
        expect("a year with a letter suffix (1953a) ties to the card of 1953",
               not [pr for pr in validate(cfg, *load_all(cfg), today)[0] if pr["code"] == "L12"])
        doc.write_text(keep_doc.replace("Kneser, M. (1953).", "Kneser, M. (ed.) (1953).", 1))
        expect("an editor's mark before the year still reads as an entry, and ties",
               [e["entry"] for e in reference_entries(cfg) if "(ed.)" in e["entry"]]
               and not [pr for pr in validate(cfg, *load_all(cfg), today)[0] if pr["code"] == "L12"])
        doc.write_text(keep_doc.replace("Kneser, M. (1953).", "**Kneser, M.** (1953, June 2).", 1))
        expect("bold authors and a year with a day read as an entry, and tie",
               [e["authors"] for e in reference_entries(cfg) if "June" in e["entry"]] == ["Kneser, M."]
               and not [pr for pr in validate(cfg, *load_all(cfg), today)[0] if pr["code"] == "L12"])
        doc.write_text(keep_doc.replace("Kneser, M. (1953).", "1. Kneser, M. (1953).", 1))
        expect("a line under the heading written like an entry and not read as one → L12",
               [(pr["code"], "not read as an entry" in pr["msg"]) for pr in validate(cfg, *load_all(cfg), today)[0]] == [("L12", True)])
        doc.write_text(keep_doc.replace("Kneser, M. (1953).", "Kneser, M. (n.d.).", 1))
        expect("an entry with no year (n.d.) is read, and ties no card that carries one",
               [e["year"] for e in reference_entries(cfg) if "n.d." in e["entry"]] == [None]
               and [pr["code"] for pr in validate(cfg, *load_all(cfg), today)[0]] == ["L12"])
        doc.write_text(keep_doc)
        bad_card = cfg.cards / "zz-bytes.md"
        bad_card.write_bytes(b"---\nkey: zz-bytes\ntitle: \xff\n---\n")
        expect("planted: a card that is not UTF-8 → L0", any(pr["code"] == "L0" and pr["key"] == "zz-bytes" for pr in validate(cfg, *load_all(cfg), today)[0]))
        bad_card.unlink()
        doc_plant("a reference entry whose year no card carries", "L12", head + good.split("\n\n")[0].replace("1953", "1955") + "\n")
        doc_plant("a reference entry two cards agree with", "L12", doc.read_text(),
                  lambda: (cfg.cards / "kneser1953b.md").write_text((cfg.cards / "kneser1953.md").read_text().replace(
                      "key: kneser1953", "key: kneser1953b").replace('doi: "10.9/kneser"', "doi: null")))
        run(["read", "brummitt2012", "--grade", "unread"])
        p = run(["check"], ok=False)
        expect("planted: a work a document cites, graded unread and known through no card → L13",
               any(pr["code"] == "L13" for pr in p["problems"]))
        run(["read", "brummitt2012", "--grade", "unread", "--via", "kneser1953"])
        run(["check"])

    # the kept directory: a copy with no address is tracked there, a copy with an address stays in the store
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "library.toml").write_text(SELFTEST_TOML.replace('store = "library/.store"\n', 'store = "library/.store"\nkept = "library/kept"\n'))
        (root / "records").mkdir()
        cfg = Config(root)
        today = "2026-10-13"

        def run(argv, ok=True):
            rc, payload = dispatch(cfg, argv, today=today, as_json=True, quiet=True)
            expect(" ".join(argv[:2]) + (" refused" if not ok else ""), (rc == 0) == ok)
            return payload

        p = run(["register", "A scanned book", "--kind", "book", "--author", "Hand, B.", "--year", "1980"])
        k1 = p["created"][0]
        p = run(["register", "An addressed paper", "--kind", "article", "--author", "Net, A.", "--year", "2001"])
        k2 = p["created"][0]
        scan = root / "scan.pdf"
        scan.write_bytes(b"%PDF\nthe first page states the lemma on columns\fthe second page proves aperiodicity\f")
        run(["keep", k1, str(scan)], ok=False)
        expect("without --redistributable nothing is written into the tracked directory", not (cfg.kept / k1).exists())
        p = run(["keep", k1, str(scan), "--redistributable"])
        cp = p["records"][0]["copy"] if p["records"] else {}
        expect("a copy with no address is kept under the tracked kept directory",
               cp.get("path") == f"library/kept/{k1}/copy.pdf" and (root / cp["path"]).is_file() and cp["from"] is None)
        expect("its text is derived under the store, not beside it",
               (cfg.store / k1 / "text" / "0002.txt").read_text() == "the second page proves aperiodicity"
               and not (cfg.kept / k1 / "text").exists())
        p = run(["keep", k2, str(scan), "--from", "https://example.org/paper.pdf"])
        cp = p["records"][0]["copy"] if p["records"] else {}
        expect("a copy with an address is kept in the store", cp.get("path") == f"library/.store/{k2}/copy.pdf")
        rc, pl = dispatch(cfg, ["page", k1, "2"], today=today, as_json=True, quiet=True)
        expect("a kept copy's page is read from the derived text", rc == 0 and pl["text"].strip() == "the second page proves aperiodicity")
        run(["index"])
        cards, broken = load_all(cfg)
        problems, cov = validate(cfg, cards, broken, today)
        expect("the check passes and names the kept directory", not problems and cov["kept"] == "library/kept" and cov["copies_by_hand"] == [k1])
        moved = cfg.store / k1 / "copy.pdf"
        shutil.move(cfg.kept / k1 / "copy.pdf", moved)
        c1 = parse(cfg.cards / f"{k1}.md")
        c1.fm["copy"]["path"] = f"library/.store/{k1}/copy.pdf"
        write_card(cfg, c1)
        problems, _ = validate(cfg, *load_all(cfg), today)
        expect("planted: a copy with no address kept in the store while the project names a kept directory → L6",
               any(pr["code"] == "L6" and pr["key"] == k1 for pr in problems))
        shutil.move(moved, cfg.kept / k1 / "copy.pdf")
        c1.fm["copy"]["path"] = f"library/kept/{k1}/copy.pdf"
        write_card(cfg, c1)
        (cfg.kept / k1 / "copy.pdf").unlink()
        p = run(["restore", k1])
        expect("restore names a lost hand copy as tracked under the kept directory",
               any("restore it from version control" in ln for ln in p["lines"]))
    # the web and repository resolver, answered by a stub
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "library.toml").write_text(SELFTEST_TOML)
        (root / "records").mkdir()
        cfg = Config(root)
        today = "2026-10-23"
        answers = {
            "https://api.github.com/repos/acme/tool": (200, json.dumps({"full_name": "acme/tool", "owner": {"login": "acme"}, "created_at": "2021-03-04T00:00:00Z",
                                                                        "html_url": "https://github.com/acme/tool", "description": "A tool.", "license": {"spdx_id": "MIT"},
                                                                        "pushed_at": "2026-01-02T00:00:00Z"}).encode()),
            "https://example.org/paper": (200, b'<html><head><title>Fallback</title><meta name="citation_title" content="A Page About Columns">'
                                               b'<meta content="Jen, Erica" name="citation_author"><meta name="citation_author" content="Ada Lovelace">'
                                               b'<meta name="citation_publication_date" content="1990/05/01"><meta name="citation_journal_title" content="J. Things">'
                                               b'<meta name="citation_doi" content="10.1000/xyz"></head></html>'),
            "https://example.org/plain": (200, b'<html><head><title>Just a Title &amp; More</title><meta property="og:site_name" content="Example"></head></html>'),
        }
        real = FETCH
        FETCH = lambda url, headers: answers.get(url.split("?")[0], (404, b""))
        rc, pl = dispatch(cfg, ["resolve", "--url", "https://github.com/acme/tool", "--register"], today=today, as_json=True, quiet=True)
        expect("a repository resolves through its forge's API and registers with its address and a note",
               rc == 0 and pl["created"] == ["acme2021"] and pl["records"][0]["kind"] == "repository" and pl["records"][0]["url"] == "https://github.com/acme/tool"
               and "A tool." in parse(cfg.cards / "acme2021.md").body and "MIT" in parse(cfg.cards / "acme2021.md").body)
        rc, pl = dispatch(cfg, ["resolve", "https://example.org/paper", "--register"], today=today, as_json=True, quiet=True)
        expect("a page resolves through its citation metadata: title, authors in either attribute order, year, venue, DOI",
               rc == 0 and pl["records"][0]["title"] == "A Page About Columns" and pl["records"][0]["authors"] == ["Jen, Erica", "Lovelace, A."]
               and pl["records"][0]["year"] == 1990 and pl["records"][0]["doi"] == "10.1000/xyz" and pl["records"][0]["kind"] == "article")
        rc, pl = dispatch(cfg, ["resolve", "--url", "https://example.org/plain"], today=today, as_json=True, quiet=True)
        expect("a page with a title element alone is a web candidate that passes", rc == 0 and any("PASS" in ln and "web" in ln for ln in pl["lines"]))
        rc, pl = dispatch(cfg, ["resolve", "--url", "https://example.org/nowhere"], today=today, as_json=True, quiet=True)
        expect("an address that does not answer writes nothing", rc == 1 and not pl["created"] and any("no answer" in ln for ln in pl["lines"]))
        FETCH = real
        rc, pl = dispatch(cfg, ["pages"], today=today, as_json=True, quiet=True)
        expect("the page manifest names a mount, a record route and the cite pattern",
               rc == 0 and pl["pages"]["mount"] == "/library" and any(r["view"] == "record" for r in pl["pages"]["routes"])
               and re.search(pl["pages"]["links"][0]["pattern"], "see lib:acme2021#x"))
        rc, pl = dispatch(cfg, ["show", "acme2021"], today=today, as_json=True, quiet=True)
        expect("show answers the citing sites as a list", rc == 0 and pl["sites"] == [])

    # init: a fresh project, checked green at once
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        a = argparse.Namespace(dir="library", kept=True, scan=["docs"], documents=None, internal=["reports"], force=False)
        written = do_init(root, a)
        cfg = Config(root)
        cards, broken = load_all(cfg)
        problems, cov = validate(cfg, cards, broken, "2026-10-23")
        expect("init: a tree that checks green, with the store ignored and the kept directory tracked",
               not problems and "library.toml" in written and (root / "library" / ".gitignore").read_text() == ".store/\n"
               and cfg.kept_name == "library/kept" and (root / "library" / "kept").is_dir() and cfg.internal_dirs == ("reports",))
        rc, pl = dispatch(cfg, ["register", "A first work", "--kind", "book", "--author", "Hand, B.", "--year", "1980"], today="2026-10-23", as_json=True, quiet=True)
        expect("init: the first register lands", rc == 0 and pl["created"] == ["hand1980"])
        try:
            do_init(root, a)
            expect("init refuses over an existing library.toml", False)
        except Refused:
            expect("init refuses over an existing library.toml", True)
        expect("the front matter reads a single-quoted string and writes a double-quoted one",
               unscalar("'it''s'", "t") == "it's" and scalar("it's") == '"it\'s"' and unscalar('"a b"', "t") == "a b")
        r = subprocess.run([sys.executable, __file__, "--help"], capture_output=True, text=True, cwd=tempfile.gettempdir())
        expect("--help works with no bindings file", r.returncode == 0 and "register" in r.stdout and "init" in r.stdout)

    reportable = set(re.findall(r'bad\("(L\d+)"', SOURCE)) | set(re.findall(r'"code": "(L\d+)"', SOURCE))
    expect(f"every code the check can report is planted ({', '.join(sorted(reportable - planted)) or 'none missing'})",
           reportable <= planted)
    print(f"library selftest: {'OK' if not failures else str(len(failures)) + ' FAILED: ' + '; '.join(failures)}")
    return 0 if not failures else 1


# --- dispatch ---------------------------------------------------------------------

def build_parser():
    ap = argparse.ArgumentParser(prog="library", description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root")
    ap.add_argument("--today")
    ap.add_argument("--selftest", action="store_true")
    sp = ap.add_subparsers(dest="cmd")
    p = sp.add_parser("register"); p.add_argument("title"); p.add_argument("--kind", required=True)
    p.add_argument("--author", action="append", help="repeatable"); p.add_argument("--year", type=int); p.add_argument("--venue")
    for f in IDENTS + ("url", "key", "read", "via", "notes", "file"):
        p.add_argument("--" + f)
    p.add_argument("--read-on", dest="read_on"); p.add_argument("--read-what", dest="read_what")
    p.add_argument("--tag", action="append", help="repeatable"); p.add_argument("--note", action="append", help="repeatable"); p.add_argument("--seed", action="store_true")
    p = sp.add_parser("read"); p.add_argument("ref"); p.add_argument("--grade", required=True); p.add_argument("--what")
    p.add_argument("--on"); p.add_argument("--via"); p.add_argument("--note"); p.add_argument("--undated", action="store_true")
    p = sp.add_parser("note"); p.add_argument("ref"); p.add_argument("--note", action="append", help="repeatable"); p.add_argument("--notes")
    p.add_argument("--tag", action="append", help="repeatable")
    p = sp.add_parser("extract"); p.add_argument("ref"); p.add_argument("id"); p.add_argument("--at", required=True)
    p.add_argument("--quote", action="append", help="repeatable"); p.add_argument("--says"); p.add_argument("--caveat"); p.add_argument("--rule")
    p.add_argument("--on"); p.add_argument("--edition"); p.add_argument("--unanchored"); p.add_argument("--replace", action="store_true")
    p = sp.add_parser("type"); p.add_argument("ref"); p.add_argument("--title"); p.add_argument("--author", action="append", help="repeatable")
    p.add_argument("--year", type=int); p.add_argument("--venue")
    p = sp.add_parser("relate"); p.add_argument("a"); p.add_argument("b"); p.add_argument("--drop", action="store_true")
    p = sp.add_parser("exclude"); p.add_argument("ref"); p.add_argument("--reason"); p.add_argument("--undo", action="store_true")
    p = sp.add_parser("resolve"); p.add_argument("entry", nargs="?", default=""); p.add_argument("--doi"); p.add_argument("--arxiv")
    p.add_argument("--openalex"); p.add_argument("--url")
    p.add_argument("--title"); p.add_argument("--at"); p.add_argument("--register", action="store_true")
    p.add_argument("--pick", type=int); p.add_argument("--override"); p.add_argument("--key"); p.add_argument("--kind")
    p.add_argument("--author", action="append", help="repeatable"); p.add_argument("--year", type=int)
    p.add_argument("--venue"); p.add_argument("--tag", action="append", help="repeatable"); p.add_argument("--note", action="append", help="repeatable")
    p.add_argument("--seed", action="store_true")
    p = sp.add_parser("verify"); p.add_argument("refs", nargs="+"); p.add_argument("--take", action="append", help="repeatable")
    p = sp.add_parser("keep"); p.add_argument("ref"); p.add_argument("file"); p.add_argument("--from", dest="source")
    p.add_argument("--redistributable", action="store_true")
    p.add_argument("--version"); p.add_argument("--on"); p.add_argument("--replace", action="store_true")
    p.add_argument("--move", action="store_true")
    p = sp.add_parser("fetch"); p.add_argument("ref"); p.add_argument("--url"); p.add_argument("--version")
    p.add_argument("--pdf", action="store_true"); p.add_argument("--replace", action="store_true")
    p = sp.add_parser("restore"); p.add_argument("refs", nargs="*")
    p = sp.add_parser("page"); p.add_argument("ref"); p.add_argument("n", nargs="?", type=int)
    p = sp.add_parser("watch"); p.add_argument("names", nargs="*"); p.add_argument("--add"); p.add_argument("--drop")
    p.add_argument("--list", action="store_true")
    for f in ("citing", "related", "arxiv", "github", "since", "why"):
        p.add_argument("--" + f)
    p = sp.add_parser("candidates"); p.add_argument("--excluded", action="store_true"); p.add_argument("--exclude", nargs="+")
    p.add_argument("--reason")
    p = sp.add_parser("show"); p.add_argument("ref")
    p = sp.add_parser("find"); p.add_argument("words", nargs="*"); p.add_argument("--text", action="store_true")
    for f in ("tag", "grade", "state", "kind", "id"):
        p.add_argument("--" + f)
    p.add_argument("--limit", type=int); p.add_argument("--from", dest="frm", type=int, default=0)
    p = sp.add_parser("related"); p.add_argument("ref")
    p = sp.add_parser("cited"); p.add_argument("ref")
    p = sp.add_parser("entries"); p.add_argument("--untied", action="store_true")
    p = sp.add_parser("claims"); p.add_argument("docs", nargs="*"); p.add_argument("--uncovered", action="store_true")
    sp.add_parser("keys")
    p = sp.add_parser("index"); p.add_argument("--check", action="store_true")
    sp.add_parser("check")
    sp.add_parser("pages")
    p = sp.add_parser("init"); p.add_argument("--dir", default="library"); p.add_argument("--kept", action="store_true")
    p.add_argument("--scan", action="append", help="repeatable"); p.add_argument("--documents", action="append", help="repeatable"); p.add_argument("--internal", action="append", help="repeatable")
    p.add_argument("--force", action="store_true")
    return ap


def line_of(c, extra=""):
    return f"{c.key} | {label(c.fm)} | {c.grade}" + (f" | {extra}" if extra else "")


def summary_of(cfg, c):
    return dict(c.fm, path=rel(cfg, c.path), label=label(c.fm))


def dispatch(cfg, argv, today=None, as_json=False, quiet=False):
    a = build_parser().parse_args(argv)
    writes = a.cmd in WRITERS or a.cmd in ONLINE or (a.cmd == "index" and not a.check)
    with project_lock(cfg, cfg.dir, "library") if writes else contextlib.nullcontext():
        return _dispatch(cfg, a, today, as_json, quiet)


def _dispatch(cfg, a, today, as_json, quiet):
    offline = False
    today = today or a.today or dt.date.today().isoformat()
    as_json = as_json or a.json or a.cmd == "keys"
    out = {"ok": True, "command": a.cmd, "created": [], "changed": [], "records": [], "problems": []}

    def emit(text=""):
        if not quiet and not as_json and text:
            print(text)

    try:
        cards, broken = load_all(cfg)
        if broken and a.cmd != "check" and not quiet:
            for b in broken:
                print(f"library: skipped {b['path']}: {b['msg']}", file=sys.stderr)
        if a.cmd in WRITERS:
            created, changed = WRITERS[a.cmd](cfg, cards, a, today)
            out["created"] = [c.key for c in created]
            out["changed"] = [c.key for c in changed]
            out["records"] = [summary_of(cfg, c) for c in created + changed]
            for c in created:
                emit(f"created {line_of(c)}  ({rel(cfg, c.path)})")
            for c in changed:
                emit(f"changed {line_of(c)}  ({rel(cfg, c.path)})")
            cards, _ = load_all(cfg)
            cfg.dir.mkdir(parents=True, exist_ok=True)
            write_whole(cfg.index, render_index(cfg, cards))
            emit(f"index refreshed: {rel(cfg, cfg.index)}")
            sync_candidates(cfg, cards)
        elif a.cmd in ONLINE:
            _CALLS[:] = [0, 0]
            touched, lines, ok = ONLINE[a.cmd](cfg, cards, a, today)
            out["lines"], out["ok"] = lines, ok
            offline = not ok and _CALLS[0] > 0 and not _CALLS[1]  # nothing answered: could not run
            if a.cmd == "candidates" and not a.exclude:
                out["candidates"] = [dict(c, ids=", ".join(c.get("ids") or [])) for c in load_watch(cfg)[1]
                                     if c.get("state") == ("excluded" if a.excluded else "proposed")]
            if a.cmd == "watch" and a.list:
                out["watches"] = [dict(w, seen=len(w.get("seen") or []), looks_at=watch_why(w)) for w in load_watch(cfg)[0]]
            out["created" if a.cmd == "resolve" else "changed"] = [c.key for c in touched]
            out["records"] = [summary_of(cfg, c) for c in touched]
            for line in lines:
                emit(line)
            if touched:
                cards, _ = load_all(cfg)
                write_whole(cfg.index, render_index(cfg, cards))
                emit(f"index refreshed: {rel(cfg, cfg.index)}")
                sync_candidates(cfg, cards)
        elif a.cmd == "show":
            c = by_ref(cards, a.ref)
            sites = citing_sites(cfg, cards).get(c.key, [])
            out["records"], out["body"], out["cited"] = [summary_of(cfg, c)], c.body, len(sites)
            out["sites"] = [{"path": p_, "line": n_, "text": t_} for p_, n_, t_ in sites]
            emit(rel(cfg, c.path))
            emit(render(c.fm, c.body).rstrip("\n"))
            emit("")
            emit(f"label: {label(c.fm)}")
            for f, ks in (("via", [c["via"]] if c["via"] else []), ("related", c["related"] or [])):
                for k in ks:
                    emit(f"{f}: {k} — {label(cards[k].fm) if k in cards else 'MISSING'}")
            emit(f"cited at {len(sites)} site(s) in {len({s[0] for s in sites})} file(s)" + (f" — `library cited {c.key}`" if sites else ""))
        elif a.cmd == "find" and a.text:
            ranker, hits = find_text(cfg, cards, a.words)
            limit = a.limit or cfg.limit
            page = hits[a.frm:a.frm + limit]
            nxt = a.frm + limit if a.frm + limit < len(hits) else None
            out.update({"rankers": [ranker], "total": len(hits), "next": nxt,
                        "hits": [{"key": k, "unit": u, "label": lab, "snippet": sn} for k, u, lab, sn in page]})
            emit("rankers: " + ranker)
            for k, u, lab, sn in page:
                emit(f"{k} {u} | {lab} | {sn}")
            emit(f"{len(page)} of {len(hits)} page(s) of kept text" + (f"; more: --from {nxt}" if nxt is not None else "")
                 + "; `library page KEY N` prints one")
        elif a.cmd == "page":
            c = by_ref(cards, a.ref)
            units = read_units(cfg, c)
            cp = c["copy"] if not c["file"] else {"path": c["file"], "text": "yes"}
            if a.n is None:
                out["units"] = [{"unit": i, "label": lab, "chars": len(t)} for i, (lab, t) in enumerate(units, 1)]
                emit(f"{c.key}: {cp['path']} — {len(units)} unit(s)" + ("" if cp.get("text") != "none" else "; NO TEXT in it"))
                for i, (lab, t) in enumerate(units, 1):
                    emit(f"{i} | {lab} | {len(t)} characters")
            else:
                if not 1 <= a.n <= len(units):
                    raise Refused(f"{c.key} has {len(units)} unit(s); there is no {a.n}")
                lab, t = units[a.n - 1]
                out.update({"key": c.key, "unit": a.n, "label": lab, "text": t})
                emit(f"{c.key} {a.n} | {lab}")
                emit(t.rstrip("\n") if t.strip() else
                     f"(no text on this page; read it as an image, for one: pdftoppm -r 110 -f {a.n} -l {a.n} -png {cp['path']} OUT)")
        elif a.cmd == "find":
            rankers, hits = find(cfg, cards, a)
            limit = a.limit or cfg.limit
            page = hits[a.frm:a.frm + limit]
            nxt = a.frm + limit if a.frm + limit < len(hits) else None
            out.update({"rankers": rankers, "total": len(hits), "next": nxt,
                        "records": [dict(summary_of(cfg, c), matched=m) for c, m in page]})
            emit("rankers: " + "; ".join(rankers))
            for c, m in page:
                emit(line_of(c, ", ".join(m)))
            emit(f"{len(page)} of {len(hits)} card(s)" + (f"; more: --from {nxt}" if nxt is not None else ""))
        elif a.cmd == "claims":
            found = claims(cfg, cards, a.docs)
            bare = [c for c in found if not c["extracts"]]
            out.update({"claims": found, "uncovered": len(bare)})
            for c in (bare if a.uncovered else found):
                emit(f"{c['doc']}:{c['line']} | {c['key']} | "
                     + ("UNCOVERED: the card carries no extract" if not c["extracts"] else "extracts: " + ", ".join(c["extracts"]))
                     + f" | {c['sentence'][:200]}")
            emit(f"claims: {len(found)} claim-shaped sentence(s) naming a carded work in {len({c['doc'] for c in found})} document(s); "
                 f"{len(bare)} at a card with no extract, so unverifiable from the library; a sentence naming no carded work is not listed")
        elif a.cmd == "related":
            c = by_ref(cards, a.ref)
            rows = related_cards(cfg, cards, c)
            out["records"] = [dict(summary_of(cfg, o), why=why) for _, o, why in rows]
            for _, o, why in rows:
                emit(line_of(o, "; ".join(why)))
            emit(f"{len(rows)} related card(s)")
        elif a.cmd == "cited":
            c = by_ref(cards, a.ref)
            sites = citing_sites(cfg, cards).get(c.key, [])
            out["records"] = [summary_of(cfg, c)]
            out["sites"] = [{"path": p, "line": n, "text": t} for p, n, t in sites]
            for p, n, t in sites:
                emit(f"{p}:{n}: {t[:160]}")
            emit(f"{cfg.cite_prefix}{c.key} cited at {len(sites)} site(s); read: {', '.join(cfg.scan) or 'no path configured'}")
        elif a.cmd == "entries":
            ents = tied_entries(cfg, cards)
            if a.untied:
                ents = [e for e in ents if len(e["keys"]) != 1]
            out["entries"] = ents
            for e in ents:
                emit(f"{e['doc']}:{e['line']}: {' + '.join(e['keys']) or 'NO CARD'} | {e['entry'][:180]}")
            emit(f"{len(ents)} reference entr{'y' if len(ents) == 1 else 'ies'} under `## {cfg.entry_heading}` in: "
                 + (", ".join(cfg.entry_docs) or "NO DOCUMENT CONFIGURED"))
        elif a.cmd == "pages":
            out["pages"] = pages_manifest(cfg)
            if not as_json:
                print(json.dumps(out["pages"], ensure_ascii=False, indent=1))
        elif a.cmd == "keys":
            out = {"ok": not broken, "cite_prefix": cfg.cite_prefix,
                   "cards": {k: {"state": c["state"], "grade": c.grade,
                                 "extracts": [e["id"] for e in parse_extracts(sections(c.body).get("Extracts", ""))[0]]}
                             for k, c in sorted(cards.items())},
                   "problems": broken}
        elif a.cmd == "index":
            text = render_index(cfg, cards)
            if a.check:
                stale = not cfg.index.is_file() or cfg.index.read_text(encoding="utf-8") != text
                out["stale"] = stale
                emit(f"index {'STALE' if stale else 'fresh'}: {rel(cfg, cfg.index)}")
                if stale:
                    out["ok"] = False
            else:
                cfg.dir.mkdir(parents=True, exist_ok=True)
                write_whole(cfg.index, text)
                emit(f"wrote {rel(cfg, cfg.index)}")
        elif a.cmd == "check":
            problems, cov = validate(cfg, cards, broken, today)
            out["problems"], out["coverage"] = problems, cov
            for p in problems:
                emit(f"{p['path'] or p['key'] or '-'}: {p['code']} {p['msg']}")
            emit(f"library check: {cov['cards']} card(s); {len(problems)} problem(s); registered: "
                 + (", ".join(f"{n} {g}" for g, n in cov["registered"].items()) or "none")
                 + f"; excluded {cov['excluded']}; copies {cov['copies_present']} verified, "
                 f"{cov['copies_absent']} recorded and not on disk, {cov['copies_no_text']} with no text in them, "
                 f"{len(cov['copies_by_hand'])} obtained by hand"
                 + (f" and tracked under {cov['kept']}" if cov["kept"] else " and needing a backup outside the store")
                 + (f" ({', '.join(cov['copies_by_hand'])})" if cov["copies_by_hand"] else "")
                 + f"; store {cov['store'] or 'NOT CONFIGURED'}; kept {cov['kept'] or 'not named: a copy obtained by hand goes to the store'}; "
                 f"reflow via {cov['reflow']}; citing sites are computed from: {', '.join(cov['scan']) or 'NO PATH CONFIGURED'}")
            emit(f"fields: {cov['from_resolver']} card(s) written by a resolver, {cov['from_hand']} typed by hand; "
                 + (f"{cov['verified']} verified against a resolver, the oldest on {cov['verified_oldest']}" if cov["verified"]
                    else "none verified against a resolver")
                 + "; no resolver is asked here (`library verify` is online and on demand)")
            emit(f"internal documents: {cov['internal']} card(s) naming a file of the project; every file under "
                 f"{', '.join(cov['internal_dirs']) or 'NO DIRECTORY CONFIGURED'} has one; no bound document's reference entry may be tied to one")
            emit(f"extracts: {cov['extracts']} extract(s), {cov['extracts_anchored']} borne out by a kept copy"
                 + "".join(f", {n} unanchored — {k}" for k, n in cov["extracts_unanchored"].items())
                 + "; a quotation and a numbered locator are looked for in the kept text, a restatement is not judged")
            emit(f"watch: {cov['watches']} watch(es), {cov['watch_never_run']} never run, {cov['watch_seen']} identifier(s) seen; "
                 f"{cov['candidates']} candidate(s) proposed, {cov['candidates_excluded']} set aside; "
                 "no interface is asked here and no run is due: `library watch` looks when it is run")
            emit(f"entries: {cov['entries']} reference entr{'y' if cov['entries'] == 1 else 'ies'} in {cov['entry_docs']} document(s) of "
                 f"{', '.join(cov['entry_globs']) or 'NO DOCUMENT CONFIGURED'}, tied to {cov['tied_cards']} card(s)"
                 + (" — by read grade: " + ", ".join(f"{n} {g}" for g, n in cov["tied_grades"].items()) if cov["tied_grades"] else "")
                 + f"; {cov['untied_cards']} registered card(s) no entry cites; a work a document names outside its entries is not read")
            if problems:
                out["ok"] = False
        else:
            raise Refused("no command (see --help)")
    except Refused as e:
        out["ok"] = False
        out["problems"].append({"code": "REFUSED", "key": None, "path": None, "msg": str(e)})
        if not quiet and not as_json:
            print(f"library: refused — {e}", file=sys.stderr)
    if as_json and not quiet:
        print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return (0 if out["ok"] else 2 if offline else 1), out


def refused(command, msg, as_json):
    """A refusal before any command ran, in the answer's own shape under --json."""
    if as_json:
        print(json.dumps({"ok": False, "command": command, "problems": [{"code": "REFUSED", "key": None, "path": None, "msg": msg}]},
                         ensure_ascii=False, indent=1))
    else:
        print(f"library: {msg}", file=sys.stderr)


def main():
    """The command line; a crash exits 2, could not run, never 1, which says problems were found."""
    try:
        return _main()
    except Exception:
        traceback.print_exc()
        print("library: could not run (the error above)", file=sys.stderr)
        return 2


def _main():
    if "--selftest" in sys.argv:
        return selftest()
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--root")
    pre.add_argument("--json", action="store_true")
    pre.add_argument("--today")
    known, rest = pre.parse_known_args()
    # the global flags are read wherever they stand (`library check --json` as well as `library --json check`)
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
            print(INSTRUCTIONS.format(dir=a.dir))
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
