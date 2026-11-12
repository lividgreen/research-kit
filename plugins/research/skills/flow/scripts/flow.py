#!/usr/bin/env python3
"""flow — the CLI, validator and index for a typed flow of work.

Records live as one Markdown file each, front matter plus a prose body, under the
directory `flow.toml` names.  Six kinds:

  idea       a thought not yet a question; open | consumed | removed  (drawn into a hand like a task)
  task       a unit of work, across the main axis; ready | active | done | aborted | removed  (closed tasks move
             to the archive); its tags say what it is, it may carry a due date and a post-done instruction
  question   what we have to answer to move the research; open | answered | wrong | impossible | removed;
             its body says what counts as an answer, and it may serve goals and directions
  finding    a CHECKABLE claim: each evidence item is form:target, the form one of [evidence] forms (the kit
             ships formal, statistical, peer-reviewed, stated, reference), resolved by its shape; the forms it
             carries are its trust; standing | removed (a finding found false is removed)
  goal       a destination the owner forms, its body saying what reached means; open | reached | given_up
  direction  the owner's dated statement of where the research moves; open | closed

Five links: `references` on every kind, the general one with no rule; a question's `answered_by` (the finding
that settles it), `blocked_by` on a question or a task (a map of date, on and reason: blocked while an item of
`on` holds) and `serves` (goals and directions); an idea's `consumed_by` (the cards it was folded into).
A ready task or an open question may be parked (by decision) and blocked (by what it waits on), both at once;
it keeps its rank, and the lists mark the wait.

Transitions (the only writers of state and links).  Every mint takes --ref ID (repeatable), --tag T
(repeatable), --source S and --body FILE:

  flow idea SUMMARY                                            an open idea
  flow question SUMMARY [--consume IDEA]... [--serves ID]... [--size s]   an open question, the ideas consumed
  flow task SUMMARY [--size s] [--due YYYY-MM-DD] [--after A]  a ready task
  flow finding SUMMARY --evidence FORM:TARGET... [--answers Q] a standing finding; --answers Q closes Q answered by it
  flow goal SUMMARY  |  flow direction SUMMARY                 the owner's, minted and closed on the owner's word
  flow draw ID --owner O         a ready task -> active, or an open idea into the hand (hand limit from flow.toml)
  flow return ID [--note N]      active -> ready, or an idea out of the hand
  flow make T --resolution FILE                                active -> done, archived; its `after` printed
  flow abort T --reason R [--resolution FILE]                  active -> aborted, archived
  flow answer Q --by F           question(open) -> answered by F
  flow impossible Q --by F       question(open) -> impossible, F the finding that shows it
  flow wrong Q --reason R        question(open) -> wrong
  flow reopen Q --reason R       a closed question -> open, a dated note keeping what it was
  flow remove ID --reason R      idea(open) | question(open) | task(ready) | finding(standing) -> removed
  flow consume IDEA              an open idea -> consumed into every card that names it in references
  flow reach G --reason R  |  flow giveup G --reason R  |  flow drop D --reason R
  flow evidence F FORM:TARGET... evidence added to a standing finding: its trust raised
  flow evidence F --replace OLD NEW  |  flow evidence F --retire OLD --reason R    an item whose file is gone, swapped
                                 or retired, the dated note in the body keeping what it was
  flow park ID --reason R [--revival V]  |  flow unpark ID [--note N]     an open question or a ready task
  flow block ID --on X... --reason R     |  flow unblock ID [--on X] [--note N]
                                 X a task's or a question's id, a date alone (YYYY-MM-DD) or words
  flow rank ID N [--insert]  |  rank --set ID...  |  rank ID --clear
  flow checked ID...             refresh an open question's last-checked date
  flow set ID FIELD VALUE        summary (every kind, the old one kept in the body), size (question, task),
                                 due | after (task)
  flow ref ID +X -Y...           a record's references: +X adds one, -Y removes one
  flow serves Q +G -D...         an open question's goals and directions
  flow tag ID +T -U...           a record's tags after its mint: +T adds one, -U removes one, the rest kept
  flow note ID --body FILE       FILE's text appended to the record's body under today's date; no field changes

A transition that changes a record's state, or parks, unparks, blocks or unblocks it, names the records that refer
to it, which may need a follow-up; it refuses nothing for them.

Views: find, show, graph, state (the cold-start bundle), directions, tags, artifacts, index [--check | --print],
check; `pages` (the dashboard's page manifest); `--json` on every command.

  flow state --check             what a machine sees of a freeze: the log's top entry today's where the tree
                                 changed since the newest committed entry, every record changed since then named;
                                 the hands' active tasks and drawn ideas printed
  flow doctor [--fix] [--all]    every record and binding written in an older model's words, and what it reads
                                 now; --fix writes every edit whose line states it, the rest left to the hand
  flow log add FILE              one entry at the top of the log, reflowed and linted as a record is
  flow log archive --before DATE the older entries moved verbatim, one file per month, into `[paths] log_archive`
  flow reflow --check PATH...    the lines of the project's other prose that are not one sentence per line
  flow reflow --as DEST DRAFT    a draft checked as if appended to DEST (a file or a record's id): the reflow,
                                 then markdownlint
`flow init [--records DIR] [--log FILE] [--owner O]... [--force]` writes a project's `flow.toml`, its
directories and its inbox, and prints the paragraph the project's instructions should carry.
A goal and a direction are minted and closed on the owner's word alone; a question names them by id in
`serves`, which their closing leaves as it is.
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
import html
import importlib.util
import io
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
    "finding": ("standing", "removed"),
    "goal": ("open", "reached", "given_up"),
    "direction": ("open", "closed"),
}
CLOSED_TASK = ("done", "aborted", "removed")
SETTLED = (*CLOSED_TASK, "answered", "wrong", "impossible")  # a record a block waits on no longer holds it
SCHEMA = {
    "idea": ("id", "type", "state", "summary", "source", "references", "owner", "drawn", "consumed_by",
             "closed", "origin", "created", "tags"),
    "question": ("id", "type", "state", "summary", "references", "size", "checked", "parked", "blocked_by", "rank",
                 "serves", "answered_by", "closed", "origin", "source", "created", "tags"),
    "task": ("id", "type", "state", "summary", "references", "size", "owner", "drawn", "due", "after", "rank",
             "parked", "blocked_by", "closed", "origin", "source", "created", "tags"),
    "finding": ("id", "type", "state", "summary", "evidence", "references", "closed", "origin", "source", "created", "tags"),
    "goal": ("id", "type", "state", "summary", "references", "closed", "origin", "source", "created", "tags"),
    "direction": ("id", "type", "state", "summary", "references", "closed", "origin", "source", "created", "tags"),
}
LIST_FIELDS = ("references", "serves", "evidence", "consumed_by", "tags")
# The five links between records: `references` the general one, with no rule; the others each with its own.
LINKS = ("references", "answered_by", "blocked_by", "serves", "consumed_by")
# The five evidence forms the kit ships, the words a finding's trust is read from; a project picks the ones it
# accepts in [evidence] forms and adds its own.
SHIPPED_FORMS = ("formal", "statistical", "peer-reviewed", "stated", "reference")
# The forms the flow resolves itself; any other may be bound to a resolver in [evidence.resolvers], and `formal` is
# asked of the formal plugin's resolver when the project has a formal.toml.
OWN_FORMS = ("statistical", "peer-reviewed", "stated", "reference")
# The version of the protocol the flow speaks with a resolver, `formal resolve --protocol` the one the kit ships;
# tests/run.py holds it equal to formal.py's own.
RESOLVER_PROTOCOL = 1
# The words of the models before this one, which `flow doctor` names and the check refuses: states and fields
# renamed, and fields dropped, each with what it reads now.
OLD_STATES = {"abandoned", "decomposed"}
OLD_FIELDS = {"abandoned": "closed", "derived_from": "references", "blocked": "blocked_by"}
MOVED_FIELDS = {
    "abandoned": "`closed`", "derived_from": "`references`", "blocked": "`blocked_by`",
    "parent": "an entry of `references`", "requires": "entries of `references`", "depends_on": "entries of `references`",
    "question": "an entry of `references`", "direction": "an entry of `serves`",
    "kill": "words in the body", "criterion": "words in the body", "dod": "words in the body", "horizon": "words in the body",
    "why_now": "words in the body", "first_move": "words in the body",
    "kind": "a tag", "rider": "the tag `rider`", "status": "the forms of the evidence, and the tag `refuted`",
    "paper": "a reference like any other",
}
DROPPED_FIELDS = {"idea": (), "question": ("parent", "kill", "criterion", "why_now", "first_move", "direction", "kind"),
                  "task": ("question", "kind", "requires", "dod", "why_now", "first_move", "rider"),
                  "finding": ("question", "status", "paper", "depends_on"), "goal": ("criterion", "horizon"), "direction": ()}
# the fields whose words move to the body, in the order the doctor writes them (`kill` the criterion's older name)
BODY_FIELDS = ("kill", "criterion", "dod", "horizon", "why_now", "first_move")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FENCE = "---"


class Refused(Exception):
    pass


class NotRun(Refused):
    """A check that could not run — a file it was given is missing, an owner not named — exits 2, never 1."""


# --- the release the setup last brought the project to ([kit] release) -------

RELEASE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
# how an older plugin, or an older hooks' pin, is moved to the release a project was brought to elsewhere
KIT_MOVE = ("`claude plugin marketplace update research-kit`, then `claude plugin update research@research-kit --scope project` "
            "and a restart of the session; for remote hooks, `prek autoupdate` (or `pre-commit autoupdate`)")


def release_key(tag):
    """A release tag as a tuple to order by (`v0.7.0` -> (0, 7, 0)); None for anything else."""
    m = RELEASE_TAG.match(str(tag or ""))
    return tuple(int(g) for g in m.groups()) if m else None


def script_version():
    """This script's release: `v` + the `metadata.version` of the flow skill's SKILL.md beside it, or of the
    research-kit package the remote hooks install it in; None for a copy of the script alone, which then refuses
    nothing on the project's `[kit] release`."""
    try:
        fm = (Path(__file__).resolve().parent.parent / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
        m = re.search(r'^\s+version: "([^"]+)"', fm, re.M)
        if m:
            return "v" + m.group(1)
    except (OSError, IndexError):
        pass
    if __package__ == "research_kit":
        try:
            from importlib import metadata
            return "v" + metadata.version("research-kit")
        except Exception:  # an install with no metadata: no version to hold the project to
            return None
    return None


def kit_ahead(cfg):
    """Where flow.toml's `[kit] release` is newer than this script, the refusal's words: the project was brought to
    that release on another machine or checkout, this plugin (or this hook's pin) is behind it, and an older script
    over newer records and bindings misreads them.  None otherwise, and where either version is unknown."""
    mine, theirs = release_key(cfg.script_version), release_key(cfg.kit_release)
    if not mine or not theirs or theirs <= mine:
        return None
    return (f"flow.toml's [kit] release is {cfg.kit_release} and this flow script is {cfg.script_version}: the project was brought to "
            f"{cfg.kit_release} on another machine or checkout, and an older script misreads newer records and bindings; "
            f"move this plugin to {cfg.kit_release}: {KIT_MOVE}")


def kit_behind(cfg):
    """Where flow.toml's `[kit] release` is older than this script, the line `flow state` prints first; None otherwise."""
    mine, theirs = release_key(cfg.script_version), release_key(cfg.kit_release)
    if not mine or not theirs or theirs >= mine:
        return None
    return f"the setup was last brought to {cfg.kit_release}; this is {cfg.script_version}: run `/research:research-init`"


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


def find_resolver(root, here=None):
    """The command that resolves `formal` evidence when flow.toml binds none: the formal plugin's `formal resolve
    --protocol` beside the research plugin, else `formal` on PATH (the hooks' environment, where the package installs
    it beside `flow`), either only where a formal.toml stands at the root.  The plugin is in one of three places, the
    first that is a file, P being the directory four above this script (the plugin's directory in a checkout, the
    version's in Claude Code's cache): beside P, beside P's parent under P's own version, or the `land` skill in the
    directory this one sits in, where the skills were installed flat.  Returns the command and the words the
    coverage line says (`here`, this script's path, is the selftest's to move)."""
    if not (root / "formal.toml").is_file():
        return [], "no formal.toml at the root"
    here = Path(here or __file__).resolve()
    places = []
    if len(here.parents) > 3:  # a path shallower than that has no plugin directory to look beside
        plugin = here.parents[3]
        places += [(plugin.parent / "formal" / "skills" / "land" / "scripts" / "formal.py", "the formal plugin beside the research plugin"),
                   (plugin.parent.parent / "formal" / plugin.name / "skills" / "land" / "scripts" / "formal.py", "the formal plugin beside the research plugin")]
    places.append((here.parent.parent.parent / "land" / "scripts" / "formal.py", "the land skill beside the flow skill"))
    for cand, words in places:
        if cand.is_file():
            return [sys.executable, str(cand), "resolve", "--protocol"], words
    on_path = shutil.which("formal")
    if on_path:
        return [on_path, "resolve", "--protocol"], "the formal command on PATH"
    return [], "formal.toml at the root but no formal plugin beside the research plugin or command on PATH"


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
        # the research-kit release the setup last brought the project to, and this script's own
        kit = raw.get("kit", {})
        self.kit_release = kit.get("release") if isinstance(kit, dict) else None
        if self.kit_release is not None and not (isinstance(self.kit_release, str) and release_key(self.kit_release)):
            raise Refused(f"flow.toml: [kit] release {self.kit_release!r} is no release tag (vN.N.N): it names the release "
                          "the setup last brought the project to, which the setup's verify step writes")
        self.script_version = script_version()
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
        # Evidence ([evidence]): the forms, the probes register, the anchors a document's items take, and the
        # resolvers a form whose targets another tool owns is asked of.
        ev = raw.get("evidence", {})
        resolvers = ev.get("resolvers", {})
        if not isinstance(resolvers, dict):
            raise Refused("flow.toml: [evidence.resolvers] is a table of a form and the command that resolves it, `formal = [\"formal\", \"resolve\", \"--protocol\"]`")
        self.resolvers = {}
        for f, c in resolvers.items():
            if f in OWN_FORMS or not FORM_WORD.match(f):
                raise Refused(f"flow.toml: [evidence.resolvers] binds {f!r}: a form is one lowercase word, and the flow resolves {', '.join(OWN_FORMS)} itself; "
                              "any other form may be bound")
            words = [c] if isinstance(c, str) else c
            if not isinstance(words, list) or not all(isinstance(w, str) and w for w in words):
                raise Refused(f"flow.toml: [evidence.resolvers] {f} is {c!r}: the whole command, a list of strings (one string is one word); [] turns it off")
            self.resolvers[f] = (words, "flow.toml's [evidence.resolvers]" if words else "disabled in flow.toml's [evidence.resolvers]")
        if "formal" not in self.resolvers:
            self.resolvers["formal"] = find_resolver(self.root)
        # the forms whose targets are a resolver's: the flow reads no path out of them, and holds an item to `form:target`
        # and [evidence] forms alone.  `formal` always; another form once a command is bound to it.
        self.resolved = ("formal", *(f for f, (c, _) in self.resolvers.items() if c and f != "formal"))
        # the forms whose targets are no repository path of the tree (`flow artifacts`, `find --refers`): those, and the library's keys
        self.opaque_forms = ("peer-reviewed", *self.resolved)
        # An item of a declaration's shape, `Path.ext#name` or `Path.ext`: what `flow doctor` reads an item written
        # before the forms as, for any extension but a document's or a probe's.
        ext_rx = r"(?!(?:md|py)(?:#|$))[A-Za-z0-9]+"
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
        # What a document's anchor names, beside a heading: a numbered statement, a word of `statement_words`
        # then its number, and a table row, whose first cell matches `row_id`.  Unbound, the kit's words and ids.
        words = ev.get("statement_words", STMT_WORDS)
        self.stmt_words = tuple(str(w) for w in ([words] if isinstance(words, str) else words))
        for w in self.stmt_words:
            if not w.strip() or w != w.strip() or re.search(r"[#\s\d]", w):
                raise Refused(f"flow.toml: [evidence] statement_words names {w!r}: a statement word is one word with no digit, "
                              "space or `#` (Theorem, Law, §)")
        self.row_id = str(ev.get("row_id", ROW_ID))
        try:
            row_rx = re.compile(self.row_id)
        except re.error as e:
            raise Refused(f"flow.toml: [evidence] row_id {self.row_id!r} is no regular expression: {e}")
        if row_rx.fullmatch("") or row_rx.fullmatch(" "):
            raise Refused(f"flow.toml: [evidence] row_id {self.row_id!r} matches an empty or a blank anchor")
        self.ev_row = re.compile(r"^([^#\s]+\.md)#(%s)$" % self.row_id)
        self.ev_stmt = re.compile(r"^([^#\s]+\.md)#(%s)( ?)(\d+(?:\.\d+)*)$" % "|".join(map(re.escape, self.stmt_words))) \
            if self.stmt_words else re.compile(r"(?!)")
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
        # how far ahead `flow state` lists the due dates, in days; the index lists them all, since it never reads the day
        self.due_within = idx.get("due_within")
        if self.due_within is not None and (isinstance(self.due_within, bool) or not isinstance(self.due_within, int) or self.due_within < 0):
            raise Refused(f"flow.toml: [index] due_within {self.due_within!r} is not a number of days (0 or more)")
        # any run of digits: the records written before `id_width` was widened keep their narrower ids
        self.id_re = re.compile(r"^(%s)-(\d+)(?:-[a-z0-9-]+)?\.md$" % "|".join(re.escape(self.prefix[t]) for t in TYPES))
        self.type_of_prefix = {self.prefix[t]: t for t in TYPES}
        self._reflow = None

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


_SENT = re.compile(r"([.?!])([\"”’')\]*`]*)[ \t]+(?=[A-Z0-9*`(\[“\"§_])")
FENCE_RUN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
# The abbreviations the built-in reflow does not split after: the lowercase Latin ones are compared in any case, the capitalised
# ones as spelled, and `et al.` by the `et ` before it.  A project with others (journal names such as `Amer.` and `Math.`) binds
# its own reflow module, which is the escape that exists.
BUILTIN_ABBREVIATIONS = frozenset((
    "cf", "e.g", "i.e", "vs", "resp", "approx", "ibid",
    "Prop", "Thm", "Lem", "Def", "Eq", "Fig", "Sec", "Ch", "No", "Vol", "Eqs", "Figs", "Secs", "Thms", "Props"))


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
            word = re.search(r"(?:[A-Za-z]\.)*[A-Za-z]+$", body[:b.start()])
            if b.group(1) == "." and word and (word.group() in BUILTIN_ABBREVIATIONS or word.group().lower() in BUILTIN_ABBREVIATIONS
                                               or re.search(r"\bet al$", body[:b.start()])):  # `cf.`, `Thm.`, `et al.`, but `A.` is a sentence
                continue
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
            out += [f"{k}:"] if v else [f"{k}: {{}}"]
            for sk, sv in v.items():  # a map's value is a scalar, or a list of scalars (a block on several things)
                out += ([f"  {sk}:"] + [f"    - {scalar(x)}" for x in sv] if sv else [f"  {sk}: []"]) if isinstance(sv, list) else [f"  {sk}: {scalar(sv)}"]
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
                j, nested = i + 1, []
                while not sm.group(2) and j < len(lines) and lines[j].startswith("    - "):  # a list under the map's key
                    more, j2 = _continued(lines, j + 1, 5)
                    nested.append(unscalar(_fold(lines[j][6:], more), f"{name}: {k}.{sm.group(1)}"))
                    j = j2
                if nested:
                    sub[sm.group(1)] = nested
                else:
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
    return parse_text(path, text)


def parse_text(path, text):
    """A record from its text, `path` naming it in a refusal."""
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
    for b in broken or []:  # a file named for a record that reads elsewhere: a stray beside it, most often a guessed name
        m = cfg.id_re.match(Path(b["path"]).name) if b["code"] == "V0" else None
        twin = recs.get(f"{m.group(1)}-{m.group(2)}") if m else None
        if twin is not None and rel(cfg, twin.path) != b["path"]:
            b["msg"] += (f"; {twin.id} is {rel(cfg, twin.path)}, so this file is a stray beside it: its text belongs in that record "
                         f"(`flow note {twin.id} --body FILE` appends a body), and this file goes")
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
    fm["state"] = {"task": "ready", "finding": "standing"}.get(type_, "open")
    if type_ == "question":
        fm["checked"] = today
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


BODY_HELP = "a file whose text is the body; `-` reads it from the standard input"
RESOLUTION_HELP = "a file whose text is appended under the date as the resolution; `-` reads it from the standard input"


def read_body(path):
    """A body's text from the file named, or from the standard input for `-`, so a one-off body needs no scratch file."""
    if not path:
        return ""
    if path == "-":
        return sys.stdin.read()
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

# A document's anchor, unless the project binds its own ([evidence] row_id, statement_words): a table row's id, two or
# three capitals, a hyphen, then letters and digits; a numbered statement, one of these words then its number.
ROW_ID = r"[A-Z]{2,3}-[A-Za-z0-9]+"
STMT_WORDS = ("Theorem", "Proposition", "Lemma", "Corollary", "Definition", "Remark", "Fact", "Conjecture", "Example")
EV_ANCHORED = re.compile(r"^([^#\s]+\.md)#(.+)$")  # a document and an anchor: a row, a statement or a heading
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


def outside_tree(target):
    """True for a path that leaves the tree: absolute, or climbing above the root by `..`; a repository path is
    written from the project root, `papers/alpha.md`, and `/papers/alpha.md` is the machine's."""
    p = norm_path(target)
    return bool(p) and (p.startswith("/") or p == ".." or p.startswith("../"))


OUTSIDE = "outside the tree: a repository path is written from the project root, with no leading `/` and no `..` above it"


def evidence_path(item, opaque=("formal", "peer-reviewed")):
    """The repository path an evidence item names, before any anchor: a probe, a result, a document; None for an
    item of a form whose targets are no path of the tree (`opaque`: a resolver's, or the library's), a URL or a
    path outside the tree."""
    s = split_evidence(item)
    if s is None or s[0] in opaque or EV_URL.match(s[1]) or outside_tree(s[1]):
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


def tree_links(body):
    """The body's links that are repository paths of the tree: `body_links` less those outside it, which V24 fails."""
    return [p for p in body_links(body) if not outside_tree(p)]


def ask_resolver(cfg, form, targets, cache):
    """What the form's resolver answers for `targets`, asked once for those not answered yet in `cache`: the request
    `{"protocol": 1, "form": FORM, "items": [TARGET, …]}` on its standard input, one JSON object back,
    `{"protocol": 1, "items": {TARGET: {"ok": true} | {"ok": false, "why": …} | {"unchecked": …}}}`.  Returns the
    state kept under the form: `answers` (a target's verdict as `resolve_evidence` words it: None, the reason, or
    "unchecked: …"), `error` (why the resolver did not answer: a nonzero exit, the limit passed, no JSON object, a
    target not answered; every item of the form is then unchecked), `unchecked` (the reason, where it answered in a
    protocol this flow does not read)."""
    st = cache.setdefault(("resolver", form), {"answers": {}, "error": None, "unchecked": None})
    todo = [t for t in dict.fromkeys(targets) if t not in st["answers"]]
    if st["error"] or st["unchecked"] or not todo:
        return st
    cmd = cfg.resolvers[form][0]
    try:
        r = subprocess.run(cmd, input=json.dumps({"protocol": RESOLVER_PROTOCOL, "form": form, "items": todo}),
                           capture_output=True, text=True, cwd=cfg.root, timeout=60)
        if r.returncode != 0:
            lines = lambda out: [ln.strip() for ln in out.splitlines() if ln.strip()]
            said = (lines(r.stderr) or lines(r.stdout) or [""])[-1]  # the last line: a traceback ends in its message
            raise ValueError(f"exit {r.returncode}" + (f" ({said[:200]})" if said else ""))
        ans = json.loads(r.stdout)
        if not isinstance(ans, dict) or isinstance(ans.get("protocol"), bool) or not isinstance(ans.get("protocol"), int):
            raise ValueError("no JSON object with a `protocol` number")
        if ans["protocol"] != RESOLVER_PROTOCOL:
            st["unchecked"] = f"the resolver for {form} answered in protocol {ans['protocol']}, which this flow does not read (it reads {RESOLVER_PROTOCOL})"
            return st
        if not isinstance(ans.get("items"), dict):
            raise ValueError("no `items` object")
        for t in todo:
            a = ans["items"].get(t)
            if not isinstance(a, dict):
                raise ValueError(f"no answer for {t}")
            if a.get("ok") is True:
                st["answers"][t] = None
            elif a.get("ok") is False:
                st["answers"][t] = str(a.get("why") or "the resolver refuses it")
            elif isinstance(a.get("unchecked"), str):
                st["answers"][t] = f"unchecked: {a['unchecked']}"
            else:
                raise ValueError(f"the answer for {t} is neither ok nor unchecked")
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        st["error"] = f"timed out after 60 seconds" if isinstance(e, subprocess.TimeoutExpired) else str(e)
    return st


def ask_resolvers(cfg, items, cache):
    """Every item of a form a resolver answers for, asked of it in one run for each form."""
    by = defaultdict(list)
    for e in items:
        s = split_evidence(e)
        if s and s[0] in cfg.forms and s[0] in cfg.resolved and cfg.resolvers[s[0]][0]:
            by[s[0]].append(s[1])
    for form, targets in by.items():
        ask_resolver(cfg, form, targets, cache)


def _resolve_by_resolver(cfg, form, target, cache):
    """An item of a form whose targets a resolver owns: its verdict, None where it resolves."""
    cmd, route = cfg.resolvers[form]
    if not cmd:
        return f"unchecked: no resolver for {form} ({route})"
    st = ask_resolver(cfg, form, [target], cache)
    if st["error"]:
        return f"unchecked: the resolver for {form} did not answer: {st['error']}"
    if st["unchecked"]:
        return f"unchecked: {st['unchecked']}"
    return st["answers"][target]


HTML_TAG = re.compile(r"<!--.*?-->|</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>")
# emphasis by `_`, a run opening before a word and closing after one; an underscore inside a word, `snake_case`, is text
UNDERSCORE_EMPHASIS = re.compile(r"(?<![^\W_])(_+)(?=[^\s_])(.*?[^\s_])\1(?![^\W_])")


def heading_anchor(text):
    """A heading's anchor as GitHub writes it, from the text the heading renders: inline code as written, and
    outside it a link's target, an HTML tag and emphasis dropped (`*`, and `_` around words, not inside one), an
    entity read as its character; then lowercased, every character but a letter, a digit, a hyphen, an underscore
    or a space dropped, each space a hyphen."""
    parts = re.split(r"(`+)(.+?)(?<!`)\1(?!`)", text.strip())  # prose, then (ticks, code) pairs
    out = []
    for k in range(0, len(parts), 3):
        t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", parts[k])
        t = HTML_TAG.sub("", t).replace("\\_", "\0")  # an escaped underscore is text, kept from the emphasis
        while (u := UNDERSCORE_EMPHASIS.sub(r"\2", t)) != t:
            t = u
        out.append(html.unescape(t.replace("*", "").replace("\0", "_")))
        if k + 2 < len(parts):
            out.append(parts[k + 2])
    return re.sub(r"[^\w\- ]", "", "".join(out).lower()).replace(" ", "-")


# a line that opens a block of its own, ending a paragraph: a quote, a list item, a table row, a thematic break;
# a paragraph's lines before a `===` or `---` underline are a setext heading
NOT_PARAGRAPH = re.compile(r"^ {0,3}(?:>|[-*+](?:[ \t]|$)|\d{1,9}[.)](?:[ \t]|$)|\||([-*_])(?:[ \t]*\1){2,}[ \t]*$)")


def heading_anchors(text):
    """The anchors of a document's headings, ATX (`## Title`) and setext (`Title` over `===` or `---`), outside
    code fences and a leading front matter block; a repeated one gains `-1`, `-2`, as GitHub numbers them."""
    out, seen, fence, para = [], Counter(), None, []

    def add(title):
        a = heading_anchor(title)
        out.append(a if not seen[a] else f"{a}-{seen[a]}")
        seen[a] += 1

    lines = text.split("\n")
    for line in lines[front_end(lines):]:
        was, fence = fence, fence_after(fence, line)
        if was is not None or fence is not None:
            para = []
            continue
        m = re.match(r"^ {0,3}#{1,6}[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$", line)
        if m:
            add(m.group(1))
            para = []
        elif para and re.match(r"^ {0,3}(?:=+|-+)[ \t]*$", line):
            add(" ".join(para))
            para = []
        elif not line.strip() or NOT_PARAGRAPH.match(line) or (not para and line.startswith("    ")):
            para = []  # a blank line, a block that interrupts the paragraph, or an indented code block
        else:
            para.append(line.strip())
    return out


def _cached(cache, key, make):
    """The cache's value under `key`, made once: `setdefault` would read or scan on every call."""
    if key not in cache:
        cache[key] = make()
    return cache[key]


def _resolve_document(cfg, target, cache, form="stated"):
    """A row, a numbered statement or a heading of a document of the project: the file, then the anchor in it."""
    m = EV_ANCHORED.match(target)
    if not m:
        return (f"{form} takes a document and an anchor: a statement (doc.md#{cfg.stmt_words[0] if cfg.stmt_words else 'Theorem'} N[.M]), "
                "a row (doc.md#ROW) or a heading (doc.md#its-anchor)")
    doc, anchor = m.groups()
    f = cfg.root / doc
    if not f.is_file():
        return f"{doc} is not a file"
    text = _cached(cache, f, lambda: f.read_text(encoding="utf-8"))
    if cfg.ev_row.match(target):
        return None if re.search(r"^\| *%s *\|" % re.escape(anchor), text, re.M) else f"row {anchor} is not in {doc}"
    s = cfg.ev_stmt.match(target)
    if s:
        said = s.group(2) + s.group(3) + s.group(4)
        if not re.search(r"(^|\*\*|#+ )%s\b" % re.escape(said), text, re.M):
            return f"{said} is not in {doc}"
        return None
    anchors = _cached(cache, (f, "#"), lambda: heading_anchors(text))
    if anchor in anchors:
        return None
    near = difflib.get_close_matches(anchor.lower(), anchors, n=1, cutoff=0.6)
    return (f"#{anchor} is no row ({cfg.row_id}), statement ({', '.join(cfg.stmt_words) or 'none bound'} then a number) "
            f"or heading of {doc}" + (f"; the nearest heading's anchor is #{near[0]}" if near else ""))


def _resolve_probe(cfg, target, cache):
    if not (cfg.root / target).is_file():
        return f"{target} is not a file"
    if not cfg.probes or not (cfg.root / cfg.probes).is_file():
        return "unchecked: no probes register bound ([evidence] probes)"
    text = _cached(cache, cfg.root / cfg.probes, lambda: (cfg.root / cfg.probes).read_text(encoding="utf-8"))
    name = Path(target).name
    listed = {mm.group(1) for line in text.splitlines() if line.startswith("|")
              for mm in [re.fullmatch(r"`([^`]+\.py)`", line.split("|")[1].strip())] if mm}
    return None if name in listed else f"{name} is not listed in the probes register"


def resolve_evidence(cfg, item, cache, lib=None):
    """None when the item resolves; 'unchecked: …' where no resolver is bound for it; else the reason.  The form is
    held to [evidence] forms, the target to the shape its form takes: `formal`, and any form the project binds to a
    resolver, whatever the resolver answers for it (`cache` keeps its answers), `statistical` a probe of the
    register or a committed result by its path, `peer-reviewed` a card of the library
    (`lib` its `keys` answer, asked where None), `stated` a row, a numbered statement or a heading of a document of
    the project, `reference` a URL for its form alone or a path for its existence; a document's anchor, under
    `statistical` and `reference` as well, checked as a stated item's is; a form of the project's own, a path for its
    existence and anything else unchecked."""
    s = split_evidence(item)
    if s is None:
        return (f"no form: an item is form:target, the form one of {', '.join(cfg.forms)} "
                "(`flow doctor` names the prefix an older item takes)")
    form, target = s
    if form not in cfg.forms:
        return f"form {form!r} is not one [evidence] forms lists ({', '.join(cfg.forms)})"
    if form in cfg.resolved:  # the resolver's targets: the flow reads no path out of them
        return _resolve_by_resolver(cfg, form, target, cache)
    if form != "peer-reviewed" and not EV_URL.match(target) and outside_tree(target):
        return f"{norm_path(target)} is {OUTSIDE}"
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
        if EV_ANCHORED.match(target):  # a document's row, statement or heading: checked as a stated item's is
            return _resolve_document(cfg, target, cache, form)
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
    ask_resolvers(cfg, items, cache)
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


def blocked_on(b):
    """What a block waits on, as a list: `on` is a list, read as one where an older model wrote one value."""
    on = b.get("on") if isinstance(b, dict) else None
    return [str(x) for x in on] if isinstance(on, list) else [str(on)] if on else []


def blocker_kind(cfg, recs, item):
    """What a block's item is, told apart exactly: `record` where it has the shape of an id (the project's prefixes) or
    is one, `date` where it is `YYYY-MM-DD` and a day of the calendar, `words` for anything else (a date inside words
    is words)."""
    if item in recs or cfg.id_re.match(f"{item}.md"):
        return "record"
    return "date" if is_date(item) else "words"


def settled_item(cfg, recs, item):
    """Whether an item is a record that is settled (done, aborted, removed, answered, wrong or impossible): the one
    kind of item the index, which never reads the day, can tell no longer holds."""
    return blocker_kind(cfg, recs, item) == "record" and item in recs and recs[item]["state"] in SETTLED


def block_holds(cfg, recs, ons, today):
    """The items of a block that hold today: a record not settled, a date not reached, words until removed by hand.
    A record is blocked while one of them does: the state is calculated, never marked."""
    return [o for o in ons if not settled_item(cfg, recs, o) and not (blocker_kind(cfg, recs, o) == "date" and o <= today)]


def blocked_now(cfg, recs, r, today):
    """The items of r's block that hold today; empty where it carries none, or none holds."""
    b = r["blocked_by"] if r.type in ("question", "task") else None
    return block_holds(cfg, recs, blocked_on(b), today) if isinstance(b, dict) else []


def index_waits_on(cfg, recs, r):
    """The items of r's block the index lists: every one but a record that is settled, a date and words as written."""
    b = r["blocked_by"] if r.type in ("question", "task") else None
    return [o for o in blocked_on(b) if not settled_item(cfg, recs, o)] if isinstance(b, dict) else []


def waits(cfg, recs, r):
    """The waits a record carries, as words for the index: parked by decision, blocked by what it names that is left."""
    out = []
    p = r["parked"] if "parked" in r.fm else None
    if isinstance(p, dict):
        out.append(f"parked {p.get('date')} — {str(p.get('reason', '')).split('. ')[0]}")
    left = index_waits_on(cfg, recs, r)
    if left:
        b = r["blocked_by"]
        out.append(f"blocked on {', '.join(left)} {b.get('date')} — {str(b.get('reason', '')).split('. ')[0]}")
    return out


def in_references(r, id_):
    """Whether record r names id_ in its references."""
    return isinstance(r["references"], list) and id_ in r["references"]


LIVE = {"idea": ("open",), "question": ("open",), "task": ("ready", "active"), "goal": ("open",), "direction": ("open",),
        "finding": ("standing",)}


def live(r):
    """Whether a record is at the front of work: open, ready or active; a finding while it stands."""
    return r["state"] in LIVE.get(r.type, ())


def link_ids(r):
    """The records r names by a link, as (field, id): `references`, `answered_by`, `serves`, `consumed_by`, and the
    items of `blocked_by.on`, a date or words among them (a caller keeps the ids of records)."""
    out = []
    for f in LINKS:
        if f not in r.fm or r.fm[f] is None:
            continue
        v = r.fm[f]
        if f == "blocked_by":
            out += [(f, o) for o in blocked_on(v)]
        else:
            out += [(f, str(x)) for x in (v if isinstance(v, list) else [v])]
    return out


def validate(cfg, recs, today):
    problems, warnings = [], []
    cache = {}
    coverage = {"records": len(recs), "kinds": list(cfg.kinds), "forms": list(cfg.forms),
                "probes": bool(cfg.probes and (cfg.root / cfg.probes).is_file()),
                "reflow": cfg.reflow_source, "markdownlint": bool(shutil.which("markdownlint"))}

    def bad(code, r, msg):
        problems.append({"code": code, "id": r.id if r else None,
                         "path": rel(cfg, r.path) if r else None, "msg": msg})

    by_owner = Counter()
    tasks_of = defaultdict(list)
    named_by = defaultdict(set)
    for r in recs.values():
        for x in r["references"] if isinstance(r["references"], list) else []:
            named_by[x].add(r.id)
            if r.type == "task":
                tasks_of[x].append(r)
    ranks = defaultdict(list)
    lib = library_keys(cfg)
    cited, citers = Counter(), set()
    if lib is not None and lib.get("error"):
        problems.append({"code": "V23", "id": None, "path": None, "msg": f"the library did not answer: {lib['error']}"})
    # every item of a form a resolver answers for, asked of it once; one that does not answer is one problem, no record's
    ask_resolvers(cfg, [str(e) for r in recs.values() if r.type == "finding" and r["state"] != "removed"
                        for e in (r["evidence"] if isinstance(r["evidence"], list) else [])], cache)
    for form in cfg.resolved:
        st = cache.get(("resolver", form))
        if st and st["error"]:
            problems.append({"code": "V6", "id": None, "path": None, "msg": f"the resolver for {form} did not answer: {st['error']}"})

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
        older = any(k in r.fm for k in MOVED_FIELDS)
        for k in SCHEMA[t]:
            if k not in r.fm:
                bad("V3", r, f"missing field {k}" + (" (`flow doctor` names the records of an older model)" if older else ""))
        for k in r.fm:
            if k not in SCHEMA[t]:
                bad("V3", r, f"unknown field {k}" + (f", of an older model: it reads {MOVED_FIELDS[k]} now (`flow doctor`)" if k in MOVED_FIELDS else ""))
        if r["state"] not in STATES[t]:
            bad("V3", r, f"state {r['state']!r} not in {STATES[t]}" + (" (`flow doctor`)" if r["state"] in OLD_STATES else ""))
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
        for f in ("parked", "blocked_by", "closed"):
            block = r[f] if f in SCHEMA[t] else None
            d = block.get("date") if isinstance(block, dict) else None
            if d is not None and not ISO.match(str(d)):
                bad("V20", r, f"{f}.date is not an ISO date")
            elif d is not None and str(d) > today:
                bad("V20", r, f"{f}.date is in the future")
        # the links: each names a record that exists, the three with a kind of their own that kind
        for f, want in (("references", None), ("consumed_by", None), ("answered_by", ("finding",)), ("serves", ("goal", "direction"))):
            if f not in SCHEMA[t]:
                continue
            if f == "serves" and r[f] is not None and not isinstance(r[f], list):
                bad("V2", r, "serves is one value: it is a list of goals and directions (`flow doctor --fix`)")
                continue
            vals = r[f] if isinstance(r[f], list) else ([r[f]] if r[f] else [])
            for v in vals:
                if v not in recs:
                    bad("V2", r, f"{f} names {v}, which does not exist")
                elif want and recs[v].type not in want:
                    bad("V2", r, f"{f} names {v}, a {recs[v].type}, not a {' or a '.join(want)}")
        # the closing: a dated reason where the closing has one, and none on an open record
        closing = {"idea": ("removed",), "question": ("wrong", "removed"), "task": ("aborted", "removed"),
                   "finding": ("removed",), "goal": ("reached", "given_up"), "direction": ("closed",)}.get(t, ())
        c = r["closed"] if "closed" in SCHEMA[t] else None
        if r["state"] in closing and not (isinstance(c, dict) and c.get("date") and c.get("reason")):
            bad("V17", r, f"{r['state']} without a dated reason (`closed`: date, reason)")
        elif c is not None and r["state"] not in closing:
            bad("V17", r, f"a dated closing reason on a record that is {r['state']}")
        # the positions: parked and blocked_by on an open question or a ready task, either or both
        if t in ("question", "task"):
            where = "an open question" if t == "question" else "a ready task"
            ok_state = r["state"] == ("open" if t == "question" else "ready")
            p, b = r["parked"], r["blocked_by"]
            if p is not None and (not ok_state or not isinstance(p, dict) or not p.get("date") or not p.get("reason")):
                bad("V15", r, f"parked needs {where} with a date and a reason")
            if b is not None and (not ok_state or not isinstance(b, dict) or not b.get("date") or not b.get("on") or not b.get("reason")):
                bad("V15", r, f"blocked_by needs {where} with a date, what it waits on and a reason")
            elif isinstance(b, dict) and not isinstance(b.get("on"), list):
                bad("V15", r, "blocked_by.on is one value: it is a list, one item for each thing waited on (`flow doctor --fix`)")
        if t == "task":
            if r["state"] in ("ready", "active") and r["due"] is not None and ISO.match(str(r["due"])) and str(r["due"]) <= today:
                warnings.append(f"{r.id}: due {r['due']} has passed")
            if r["state"] == "active":
                if r["owner"]:
                    by_owner[r["owner"]] += 1
                else:
                    bad("V9", r, "active without an owner")
            elif r["state"] in CLOSED_TASK and r["owner"]:
                bad("V20", r, f"a {r['state']} task carries an owner")  # its drawn date stays, the day its work began
            elif r["state"] == "ready" and (r["owner"] or r["drawn"]):
                bad("V9", r, "a ready task carries an owner or a drawn date: it is in no hand")
        if t == "finding" and r["state"] != "removed":  # a removed finding's evidence is history, no longer resolved
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
            by = r["answered_by"]
            if isinstance(by, list):
                bad("V18", r, "answered_by is one finding, not a list (`flow doctor`)")
            elif r["state"] in ("answered", "impossible"):
                if by is None and r["origin"] != "legacy":
                    bad("V18", r, f"{r['state']} needs the one finding that settles it in answered_by")
                elif by in recs and recs[by].type == "task":
                    bad("V18", r, f"{r['state']} by {by}, a task: a finding settles a question "
                                  f"(`flow finding … --ref TASK`, then `flow answer`), or the question reads as removed")
            elif by is not None:
                bad("V18", r, f"answered_by on a question that is {r['state']}")
            if r["state"] == "open":
                ts = tasks_of.get(r.id, [])
                if ts and all(x["state"] in CLOSED_TASK for x in ts):
                    warnings.append(f"{r.id}: needs refine or answer (every task closed)")
        if t == "idea":
            if r["state"] == "consumed":
                into = r["consumed_by"] if isinstance(r["consumed_by"], list) else [r["consumed_by"]] if r["consumed_by"] else []
                if not isinstance(r["consumed_by"], list) and r["consumed_by"]:
                    bad("V17", r, "consumed_by lists the cards it was folded into, not one id (`flow doctor`)")
                elif not into or any(x not in named_by.get(r.id, set()) for x in into):
                    bad("V17", r, "consumed without the cards it was folded into, each naming it in references")
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
            if isinstance(r["rank"], int) and not isinstance(r["rank"], bool):
                ranks[r["rank"]].append(r.id)
            else:
                bad("V3", r, f"rank {r['rank']!r} is not a whole number")
        if cfg.reflow_source and r.body and cfg.reflow(r.body) != r.body:
            bad("V19", r, "body is not one sentence per line (reflow changes it)")
        # the artifacts a body links: a path that is gone fails a live record and is warned of on a closed one
        for p in sorted(set(body_links(r.body))):
            where = OUTSIDE if outside_tree(p) else None if (cfg.root / p).exists() else "not in the tree"
            if where:
                if live(r):
                    bad("V24", r, f"the body links {p}, which is {where}")
                else:
                    warnings.append(f"{r.id}: the body links {p}, which is {where}")
    for n, ids in ranks.items():
        if len(ids) > 1:
            problems.append({"code": "V14", "id": None, "path": None, "msg": f"rank {n} on {', '.join(ids)}"})
    if ranks and sorted(ranks) != list(range(1, len(ranks) + 1)):
        problems.append({"code": "V14", "id": None, "path": None, "msg": f"ranks are not 1..n: {sorted(ranks)}"})
    coverage["resolvers"] = {}
    for form in (f for f in cfg.forms if f in cfg.resolvers):  # each form asked of a resolver: the route that answered, or why none did
        cmd, route = cfg.resolvers[form]
        st = cache.get(("resolver", form)) or {}
        coverage["resolvers"][form] = (f"unchecked ({route})" if not cmd else f"unchecked (did not answer: {st['error']}; {route})" if st.get("error")
                                       else f"unchecked ({st['unchecked']}; {route})" if st.get("unchecked") else f"via {route}")
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
        bits = [f"serves: {', '.join(map(str, r['serves']))}"] if r.type == "question" and r["serves"] else []
        bits += [f"waits: {w}" for w in waits(cfg, recs, r)]
        rows.append(f"{r['rank']}. `{r.id}` — {r['summary']}")
        rows += [f"   {b}" for b in bits]
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
            return ", ".join([*(str(t) for t in r["tags"] or []), f"drawn {r['drawn']}"] + list(r["references"] or []))
        rows += ([f"{len(held)} of {lim}", ""] if lim and held else []) + ([_line(r, what(r)) for r in held] or ["none"])
        rows.append("")
    section("Hand", rows[:-1])

    # the goals and the directions, the pulls on the ranking: each open goal by its summary, each open direction with
    # its date, and under each the open questions serving it
    def served(x):
        qs = sorted((q for q in R if q.type == "question" and q["state"] == "open" and x.id in (q["serves"] or [])), key=lambda q: q.id)
        return [f"  - `{q.id}` — {q['summary']}" for q in qs] or ["  - no open question serves it"]
    goals = sorted((r for r in R if r.type == "goal" and r["state"] == "open"), key=lambda r: r.id)
    if goals:
        section("Goals", [row for g in goals for row in [_line(g)] + served(g)])
    dirs = sorted((r for r in R if r.type == "direction" and r["state"] == "open"), key=lambda r: r.id)
    if dirs:
        section("Directions", [row for d in dirs for row in [_line(d, str(d["created"]))] + served(d)])

    order = {s: i for i, s in enumerate(cfg.sizes)}
    ready = [r for r in R if r.type == "task" and r["state"] == "ready"]
    ready.sort(key=lambda r: (order.get(r["size"], len(order)), r.id))
    section("Ready", [_line(r, "; ".join([", ".join(x for x in (*(str(t) for t in r["tags"] or []), r["size"], *(r["references"] or [])) if x)] + waits(cfg, recs, r))) for r in ready])

    if cfg.has("question"):
        waiting = lambda r: r["parked"] is not None or bool(index_waits_on(cfg, recs, r))
        opn = [r for r in R if r.type == "question" and r["state"] == "open" and not waiting(r)]
        opn.sort(key=lambda r: (str(r["checked"]), r.id))
        section("Open questions", [_line(r, ", ".join(x for x in (r["size"], f"checked {r['checked']}", *map(str, r["serves"] or [])) if x)) for r in opn])

        wait = [r for r in R if r.type == "question" and r["state"] == "open" and waiting(r)]
        wait.sort(key=lambda r: r.id)
        section("Parked or blocked questions", [_line(r, "; ".join(waits(cfg, recs, r))) for r in wait])

        tasks_of = defaultdict(list)
        for r in R:
            for x in (r["references"] or []) if r.type == "task" else []:
                tasks_of[x].append(r)
        need = [r for r in R if r.type == "question" and r["state"] == "open" and tasks_of[r.id]
                and all(x["state"] in CLOSED_TASK for x in tasks_of[r.id])]
        section("Needs refine or answer", [_line(r, f"{len(tasks_of[r.id])} tasks, all closed") for r in sorted(need, key=lambda r: r.id)])

    if cfg.has("finding"):
        fnd = sorted((r for r in R if r.type == "finding" and r["state"] != "removed"), key=lambda r: r.id, reverse=True)[:cfg.recent_findings]
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
        raise Refused(f"{id_} is {r['state']}, not {' or '.join(states)}"
                      + (f": draw it first (`flow draw {id_} --owner O`)" if r.type == "task" and r["state"] == "ready" and "active" in states else ""))
    return r


# The ranks a transition renumbered without being asked, (id, from, to): reported as re-ranks, not as changes.
_RERANKED = []
# What `flow rank --set` did to each record it touched, ("ranked", id, rank) or ("unranked", id, was): said as such.
_SET_RANKS = []


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


def mint_refs(recs, ids, own=None):
    """The references a record is minted with, or given by `flow ref`: each an id that exists, in any state, a removed
    record's included; never the record's own and never twice.  No other rule: a reference obliges nothing."""
    out = []
    for i in ids or []:
        get(recs, i)
        if i == own:
            raise Refused(f"{i} is the record itself: a record does not reference itself")
        if i in out:
            raise Refused(f"{i} is named twice")
        out.append(i)
    return out


def mint_common(cfg, recs, a):
    """The fields every mint takes: --ref, --tag and --source."""
    return {"references": mint_refs(recs, a.ref), "source": mint_source(cfg, a.source), "tags": a.tag or []}


def check_serves(recs, ids):
    """What a question is given to serve: each an open goal or direction, named once."""
    out = []
    for i in ids or []:
        r = get(recs, i)
        if r.type not in ("goal", "direction"):
            raise Refused(f"{i} is a {r.type}: a question serves a goal or a direction")
        if r["state"] != "open":
            raise Refused(f"{i} is {r['state']}: a question is given an open {r.type} to serve")
        if i in out:
            raise Refused(f"{i} is named twice")
        out.append(i)
    return out


def check_due(due):
    if due is not None and not ISO.match(str(due)):
        raise Refused("--due takes a date, YYYY-MM-DD")
    if due is not None and not is_date(str(due)):
        raise Refused(f"--due {due} is no day of the calendar: it takes a date, YYYY-MM-DD")
    return due


def consume(recs, rec, also=()):
    """The idea consumed into every card that names it in references, `also` the ones a transition is minting."""
    into = sorted({r.id for r in recs.values() if in_references(r, rec.id)} | set(also))
    if not into:
        raise Refused(f"no card names {rec.id} in references: an idea is consumed into the cards it was folded into; "
                      f"name it with `--ref {rec.id}` as each is minted (`flow ref ID +{rec.id}` after), or remove the idea")
    rec.fm.update({"state": "consumed", "consumed_by": into, "owner": None, "drawn": None})


def path_source(src):
    """The repository path a source names, root-relative, where it reads as one: a word with no space that is no
    URL, leaves no tree and carries a `/` or an extension; else None, the source being words."""
    if not isinstance(src, str) or not src or re.search(r"\s", src) or EV_URL.match(src) or not re.search(r"/|\.\w+$", src):
        return None
    return None if outside_tree(src) else norm_path(src)


def source_path(r):
    """The repository path a record's `source` names (`path_source`), listed whether or not it is still in the tree."""
    return path_source(r["source"] if "source" in r.fm else None)


def mint_source(cfg, src):
    """The source a record is minted with: words as given; one that reads as a repository path, root-relative, held
    to the tree, so a source in words with the shape of a path (`arXiv:2301.12345`, `v1.2`) is refused for its words
    rather than listed by `flow artifacts` as a missing path."""
    p = path_source(src)
    if p is None:
        return src
    if not (cfg.root / p).exists():
        raise Refused(f"--source {src} reads as a repository path (no space, a `/` or an extension) and {p} is not in "
                      "the tree: name a path of the tree, or write the source in words with a space (`arXiv 2301.12345`) "
                      "or as a URL")
    return p


# --- the mints: one per kind, each the kind's name ---------------------------------

def cmd_idea(cfg, recs, a, today):
    r = new_record(cfg, "idea", {"summary": a.summary, **mint_common(cfg, recs, a)}, read_body(a.body), today)
    return [r], []


def cmd_question(cfg, recs, a, today):
    """A question, standing alone or not: --consume IDEA consumes an open idea into it (and every other card naming
    it), named in its references; what else it comes from is a --ref, a document its --source."""
    common = mint_common(cfg, recs, a)
    ideas = []
    for i in a.consume or []:
        x = get(recs, i, "idea", ("open",))
        if x in ideas:
            raise Refused(f"{i} is named twice")
        ideas.append(x)
        if i not in common["references"]:
            common["references"].append(i)
    q = new_record(cfg, "question", {"summary": a.summary, "size": a.size, "serves": check_serves(recs, a.serves), **common},
                   read_body(a.body), today)
    for x in ideas:
        consume(recs, x, [q.id])
        save(cfg, x)
    return [q], ideas


def cmd_task(cfg, recs, a, today):
    r = new_record(cfg, "task", {"summary": a.summary, "size": a.size, "due": check_due(a.due), "after": a.after, **mint_common(cfg, recs, a)},
                   read_body(a.body), today)
    return [r], []


def answerable(recs, qid):
    """An open question, which a finding may settle; a closed one is reopened first."""
    q = get(recs, qid, "question")
    if q["state"] != "open":
        by = q["answered_by"]
        if isinstance(by, list) or (by in recs and recs[by].type == "task"):
            raise Refused(f"{q.id} is {q['state']} in an older model's words (answered_by {by}): mint the finding "
                          f"without --answers and write it into answered_by by hand, as `flow doctor` says")
        raise Refused(f"{q.id} is {q['state']}" + (f" by {by}" if by else "")
                      + f": `flow reopen {q.id} --reason R` first, where it is to be settled again")
    return q


def standing(recs, fid):
    """A finding that stands, which may settle a question; a removed one settles nothing."""
    f = get(recs, fid, "finding")
    if f["state"] != "standing":
        raise Refused(f"{f.id} is {f['state']}: a removed finding settles nothing")
    return f


def cmd_finding(cfg, recs, a, today):
    """The one mint of a finding, whatever produced it; --answers names the question it settles, which closes answered."""
    common = mint_common(cfg, recs, a)
    q = answerable(recs, a.answers) if a.answers else None
    items = list(a.evidence or [])
    if not items:
        raise Refused("a finding takes --evidence FORM:TARGET, one item or more")
    resolve_items(cfg, items)
    f = new_record(cfg, "finding", {"summary": a.summary, "evidence": items, **common}, read_body(a.body), today)
    if q is None:
        return [f], []
    close_question(cfg, recs, q, "answered", today, by=f.id)
    return [f], [q]


def cmd_evidence(cfg, recs, a, today):
    """Evidence added to a finding: the way its trust is raised, a proof formalized, a probe run, a work cited;
    each item resolved as at the mint.  An item whose file a later change deleted is swapped (`--replace OLD NEW`,
    NEW resolved as an added item is) or retired (`--retire OLD --reason R`, refused where it leaves the finding
    none, which V6 fails), the dated note in the body keeping what the evidence was."""
    f = get(recs, a.finding, "finding")
    if f["state"] != "standing":
        raise Refused(f"{f.id} is {f['state']}: its evidence is history, kept as it was")
    held = list(f["evidence"] or [])
    if (bool(a.evidence) + (a.replace is not None) + (a.retire is not None)) != 1:
        raise Refused("flow evidence takes one of the items to add, --replace OLD NEW or --retire OLD --reason R")
    if a.reason is not None and a.retire is None:
        raise Refused("--reason goes with --retire")
    if a.evidence:
        resolve_items(cfg, a.evidence, have=held)
        f.fm["evidence"] = held + list(a.evidence)
    else:
        old, new = a.replace if a.replace is not None else (a.retire, None)
        if old not in held:
            raise Refused(f"evidence {old} is not among {f.id}'s items, which are {', '.join(held) or 'none'}")
        if new is not None:
            resolve_items(cfg, [new], have=held)
            at = held.index(old)  # a hand-edited finding may hold an item twice: one occurrence is acted on
            f.fm["evidence"] = held[:at] + [new] + held[at + 1:]
            append_note(f, today, f"evidence `{old}` replaced by `{new}`")
        else:
            if not (a.reason or "").strip():
                raise Refused("--retire needs --reason: the words kept in the note")
            at = held.index(old)  # one occurrence only, as with --replace
            left = held[:at] + held[at + 1:]
            if not left:
                raise Refused(f"evidence {old} is {f.id}'s only item, and a finding with none fails V6: --replace it")
            f.fm["evidence"] = left
            append_note(f, today, f"evidence `{old}` retired: {a.reason.strip()}")
    save(cfg, f)
    return [], [f]


def cmd_goal(cfg, recs, a, today):
    """A goal the owner forms: the summary names the outcome, the body what reached means and how far out it lies."""
    r = new_record(cfg, "goal", {"summary": a.summary, **mint_common(cfg, recs, a)}, read_body(a.body), today)
    return [r], []


def cmd_direction(cfg, recs, a, today):
    """A direction the owner opens: its name the summary, the owner's words its body, dated by `created`."""
    r = new_record(cfg, "direction", {"summary": a.summary, **mint_common(cfg, recs, a)}, read_body(a.body), today)
    return [r], []


# --- the hands, and the closings -----------------------------------------------------

def held_by(recs, owner):
    """What an owner's hand holds: the active tasks drawn into it and the ideas drawn."""
    return [r for r in recs.values() if r["owner"] == owner and
            ((r.type == "task" and r["state"] == "active") or (r.type == "idea" and r["state"] == "open"))]


def cmd_draw(cfg, recs, a, today):
    r = get(recs, a.id)
    if r.type == "task":
        if r["state"] != "ready":
            raise Refused(f"{r.id} is {r['state']}, not ready")
        holds = blocked_now(cfg, recs, r, today)
        why = (["parked (`flow unpark` it first)"] if r["parked"] is not None else []) + \
              ([f"blocked on {', '.join(holds)}, which still holds (`flow unblock {r.id} --on X` for words or a mistake)"] if holds else [])
        if why:
            raise Refused(f"{r.id} is {' and '.join(why)}")
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
        r.fm.update({"state": "active", "blocked_by": None})  # a block none of whose items holds goes with the draw
    save(cfg, r)
    return [], [r]


def cmd_return(cfg, recs, a, today):
    r = get(recs, a.id)
    if r.type == "task" and r["state"] == "active":
        r.fm.update({"state": "ready", "owner": None, "drawn": None})
    elif r.type == "idea" and r["state"] == "open" and r["owner"]:
        r.fm.update({"owner": None, "drawn": None})
    elif r.type == "task" and r["state"] == "ready":
        raise Refused(f"{r.id} is ready, in no hand")
    else:
        raise Refused(f"{r.id} is in no hand")
    made = sorted(x.id for x in recs.values() if in_references(x, r.id)) if r.type == "idea" else []
    if a.note or made:  # an idea put back partly worked lists what it produced so far
        append_note(r, today, "returned" + (f": {a.note}" if a.note else "") + (f"; produced so far: {', '.join(made)}" if made else ""))
    save(cfg, r)
    return [], [r]


def close_task(cfg, recs, t, state, today, reason=None):
    had_rank = t["rank"] is not None
    t.fm.update({"state": state, "owner": None, "rank": None, "parked": None, "blocked_by": None,
                 "closed": {"date": today, "reason": reason} if reason else None})
    save(cfg, t)
    move_to_archive(cfg, t)
    if had_rank:
        close_ranks(cfg, recs)


def cmd_make(cfg, recs, a, today):
    """A task made: its resolution, what was done, appended under the date; it mints nothing, the follow-ups being
    minted after it (`flow task … --ref T`)."""
    t = get(recs, a.task, "task", ("active",))
    text = read_body(a.resolution)
    if not text.strip():
        raise Refused(f"the resolution {'from the standard input' if a.resolution == '-' else a.resolution} is empty: "
                      "a done task says what was done")
    append_note(t, today, "resolution:", text)
    close_task(cfg, recs, t, "done", today)
    return [], [t]


def cmd_abort(cfg, recs, a, today):
    t = get(recs, a.task, "task", ("active",))
    if a.resolution:
        append_note(t, today, "resolution:", read_body(a.resolution))
    close_task(cfg, recs, t, "aborted", today, a.reason)
    return [], [t]


def close_question(cfg, recs, q, state, today, reason=None, by=None):
    """A question closed: no task is asked about, since a question's closing is its own act and tasks stand across it."""
    had_rank = q["rank"] is not None
    q.fm.update({"state": state, "answered_by": by, "rank": None, "parked": None, "blocked_by": None,
                 "closed": {"date": today, "reason": reason} if reason else None})
    save(cfg, q)
    if had_rank:
        close_ranks(cfg, recs)


def cmd_answer(cfg, recs, a, today):
    q = answerable(recs, a.question)
    f = standing(recs, a.by)
    close_question(cfg, recs, q, "answered", today, by=f.id)
    return [], [q]


def cmd_impossible(cfg, recs, a, today):
    q = answerable(recs, a.question)
    f = standing(recs, a.by)
    close_question(cfg, recs, q, "impossible", today, by=f.id)
    return [], [q]


def cmd_wrong(cfg, recs, a, today):
    q = get(recs, a.question, "question", ("open",))
    close_question(cfg, recs, q, "wrong", today, reason=a.reason)
    return [], [q]


def cmd_reopen(cfg, recs, a, today):
    """A closed question back to open, whatever closed it: its answer and its closing cleared, a dated note keeping what
    it was.  The tag do-not-reopen, the person's mark, is refused on; the agent asks the person and never lifts it unasked."""
    q = get(recs, a.question, "question")
    if q["state"] == "open":
        raise Refused(f"{q.id} is open already")
    if "do-not-reopen" in (q["tags"] or []):
        raise Refused(f"{q.id} carries the tag do-not-reopen, the person's mark that it stays settled: ask the person; "
                      f"`flow tag {q.id} -do-not-reopen` lifts it, on their word")
    was, by, c = q["state"], q["answered_by"], q["closed"]
    note = (f"reopened: {a.reason.strip()}; it was {was}" + (f" by {by}" if by else "")
            + (f" ({c.get('date')}: {c.get('reason')})" if isinstance(c, dict) and c.get("reason") else ""))
    q.fm.update({"state": "open", "answered_by": None, "closed": None, "checked": today})
    append_note(q, today, note)
    save(cfg, q)
    return [], [q]


def cmd_reach(cfg, recs, a, today):
    g = get(recs, a.goal, "goal", ("open",))
    g.fm.update({"state": "reached", "closed": {"date": today, "reason": a.reason}})
    save(cfg, g)
    return [], [g]


def cmd_giveup(cfg, recs, a, today):
    """A goal given up; the questions serving it keep it, the notice naming them for the session to decide on."""
    g = get(recs, a.goal, "goal", ("open",))
    g.fm.update({"state": "given_up", "closed": {"date": today, "reason": a.reason}})
    save(cfg, g)
    return [], [g]


def cmd_drop(cfg, recs, a, today):
    """A direction dropped; the questions serving it keep it, the notice naming them for the session to decide on."""
    d = get(recs, a.direction, "direction", ("open",))
    d.fm.update({"state": "closed", "closed": {"date": today, "reason": a.reason}})
    save(cfg, d)
    return [], [d]


def cmd_consume(cfg, recs, a, today):
    """An idea whose whole content is folded into other cards, one or many of any kind, each naming it in references."""
    i = get(recs, a.idea, "idea", ("open",))
    consume(recs, i)
    save(cfg, i)
    return [], [i]


def cmd_remove(cfg, recs, a, today):
    r = get(recs, a.id)
    if r.type == "task":
        if r["state"] != "ready":
            raise Refused(f"{r.id} is {r['state']}: remove takes a ready task; abort an active one" if r["state"] == "active"
                          else f"{r.id} is {r['state']} already")
        close_task(cfg, recs, r, "removed", today, a.reason)
        return [], [r]
    if r.type == "finding":  # a finding found false: removed, its card kept, what refers to it named by the notice
        if r["state"] != "standing":
            raise Refused(f"{r.id} is {r['state']} already")
        r.fm.update({"state": "removed", "closed": {"date": today, "reason": a.reason}})
        save(cfg, r)
        return [], [r]
    if r.type not in ("idea", "question"):
        raise Refused(f"{r.id} is a {r.type}: remove takes an open idea, an open question, a ready task or a standing finding")
    if r["state"] != "open":
        raise Refused(f"{r.id} is {r['state']} already")
    if r.type == "idea":
        r.fm.update({"state": "removed", "owner": None, "drawn": None, "closed": {"date": today, "reason": a.reason}})
        save(cfg, r)
        return [], [r]
    close_question(cfg, recs, r, "removed", today, reason=a.reason)
    return [], [r]


# --- the positions ---------------------------------------------------------------------

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
    if r.type == "question":
        r.fm["checked"] = today
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
    """A block: what the record waits on, each item a task's or a question's id, a date alone or words.  It holds while
    one item does; a block that no longer holds is replaced, and one that never would is refused."""
    r = waitable(recs, a.id)
    if r["blocked_by"] is not None:
        holds = blocked_now(cfg, recs, r, today)
        if holds:
            raise Refused(f"{r.id} is blocked already, on {', '.join(holds)}: unblock it first")
    ons = [o.strip() for o in a.on]
    for on in ons:
        if not on:
            raise Refused("block takes --on: a task or a question by its id, a date (YYYY-MM-DD) or words")
        kind = blocker_kind(cfg, recs, on)
        if kind == "words" and ISO.match(on):
            raise Refused(f"{on} is no day of the calendar: a date waited on is written YYYY-MM-DD, a day that exists")
        if kind == "record":
            w = get(recs, on)
            if w.type not in ("task", "question"):
                raise Refused(f"{on} is a {w.type}: a record waits on a task or a question, a date or words")
            if w.id == r.id:
                raise Refused(f"{r.id} cannot wait on itself")
            if w["state"] in SETTLED:
                raise Refused(f"{on} is {w['state']}: a block on it would never hold")
        elif kind == "date" and on <= today:
            raise Refused(f"{on} is not after today ({today}): a block until it would never hold")
    if len(set(ons)) < len(ons):
        raise Refused("block names one thing twice in --on")
    r.fm["blocked_by"] = {"date": today, "on": ons, "reason": a.reason}
    if r.type == "question":
        r.fm["checked"] = today
    save(cfg, r)
    return [], [r]


def cmd_unblock(cfg, recs, a, today):
    """The block taken off, or with --on one of its items: for words, which hold until removed by hand, and for a
    mistake; a record that settles or a date reached stops holding without it."""
    r = get(recs, a.id)
    if r.type not in ("question", "task") or r["blocked_by"] is None:
        raise Refused(f"{r.id} is not blocked")
    if a.on is not None:
        held = blocked_on(r["blocked_by"])
        if a.on not in held:
            raise Refused(f"{r.id}'s block holds no {a.on!r}; it holds {', '.join(held)}")
        left = [o for o in held if o != a.on]
        r.fm["blocked_by"] = {**r["blocked_by"], "on": left} if left else None
    else:
        r.fm["blocked_by"] = None
    if r.type == "question":
        r.fm["checked"] = today
    if a.note:
        append_note(r, today, "unblocked" + (f" {a.on}" if a.on is not None else "") + ": " + a.note)
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
        for r in sorted(recs.values(), key=lambda r: r.id):
            if r.type in ("question", "task") and r["rank"] is not None and r not in rs:
                _SET_RANKS.append(("unranked", r.id, r["rank"]))
                r.fm["rank"] = None
                save(cfg, r)
                changed.append(r)
        for n, r in enumerate(rs, 1):  # an order only: no question's checked date moves (`flow checked` records a read)
            _SET_RANKS.append(("ranked", r.id, n))
            r.fm["rank"] = n
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
    if r.type == "question":
        r.fm["checked"] = today
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
        q = get(recs, i, "question", ("open",))
        q.fm["checked"] = today
        save(cfg, q)
        out.append(q)
    return [], out


# --- the fields changed after a mint ------------------------------------------------------

# The fields a record's prose owner may change at any time, through the CLI rather than by hand: which record types
# carry each.  State, the links and rank stay with their transitions.
SETTABLE = {"summary": ("idea", "question", "task", "finding", "goal", "direction"), "size": ("question", "task"),
            "due": ("task",), "after": ("task",)}
# the way a field `set` no longer takes goes now
SET_GONE = {**dict.fromkeys(BODY_FIELDS, "its words go in the body: `flow note ID --body FILE`"),
            **dict.fromkeys(("derived_from", "references", "parent", "requires", "depends_on", "question"), "`flow ref ID +X -Y` changes the references"),
            **dict.fromkeys(("serves", "direction"), "`flow serves Q +G -D` changes what an open question serves"),
            "rider": "the tag `rider` marks a hand-off: `flow tag T +rider`", "kind": "the tag `conjecture` marks one: `flow tag Q +conjecture`"}


def cmd_set(cfg, recs, a, today):
    r = get(recs, a.id)
    if a.field not in SETTABLE:
        raise Refused(f"set takes one of {', '.join(SETTABLE)}; {a.field!r} is a transition's or no field"
                      + (f": {SET_GONE[a.field]}" if a.field in SET_GONE else ""))
    if r.type not in SETTABLE[a.field]:
        raise Refused(f"{r.id} is a {r.type}; {a.field} is a field of {', '.join(SETTABLE[a.field])}")
    v = a.value.strip()
    if a.field == "size":
        if v not in (*cfg.sizes, "none"):
            raise Refused(f"size takes one of {', '.join(cfg.sizes)} or none")
        value = None if v == "none" else v
    elif a.field == "due":
        value = None if v == "none" else check_due(v)
    elif a.field == "after":
        value = None if v == "none" else v
        if value == "":
            raise Refused(f"{a.field} takes words, or none")
    else:
        if not v:
            raise Refused(f"{a.field} cannot be empty")
        value = v
    if a.note is not None and not a.note.strip():
        raise Refused("set takes --note in words: an empty one says nothing")
    old = r[a.field]
    if a.field == "summary" and value != old:
        # the summary states the record: what it read before stays in the body, dated, with the words for the change
        append_note(r, today, f"summary set; it read: {old}" + (f". {a.note.strip()}" if a.note else ""))
    elif a.note:
        append_note(r, today, f"{a.field} set: {a.note.strip()}")
    r.fm[a.field] = value
    save(cfg, r)
    return [], [r]


def plus_minus(changes, usage):
    """The +X and -Y of `flow ref` and `flow serves`, as (added, removed): refused with no change, a change that is no
    +X or -Y, and an entry both added and removed."""
    if not changes:
        raise Refused(f"{usage}: +X adds an entry and -Y removes one")
    add, drop = [], []
    for c in changes:
        if c[:1] not in "+-" or not c[1:].strip() or c[1:] != c[1:].strip():
            raise Refused(f"{c!r}: each change is +X to add an entry or -Y to remove one, X and Y ids")
        (add if c[0] == "+" else drop).append(c[1:])
    both = sorted(set(add) & set(drop))
    if both:
        raise Refused(f"{', '.join(both)} both added and removed")
    return list(dict.fromkeys(add)), list(dict.fromkeys(drop))


def cmd_ref(cfg, recs, a, today):
    """A record's references after its mint, any record in any state: an entry added is an id that exists, never the
    record's own and never one it holds; an entry removed is one it holds, never the card a consumed idea was folded into."""
    r = get(recs, a.id)
    add, drop = plus_minus(a.changes, f"ref takes +X and -Y: flow ref {r.id} +X -Y")
    held = list(r["references"] or [])
    lacks = [x for x in drop if x not in held]
    if lacks:
        raise Refused(f"{r.id} references no {', '.join(lacks)}; its references: {', '.join(map(str, held)) or 'none'}")
    for x in drop:
        if x in recs and recs[x].type == "idea" and r.id in (recs[x]["consumed_by"] or []):
            raise Refused(f"{x} is consumed into {r.id}, which names it while it stands so")
    there = [x for x in add if x in held]
    if there:
        raise Refused(f"{r.id} references {', '.join(there)} already")
    mint_refs(recs, add, r.id)
    r.fm["references"] = [x for x in held if x not in drop] + add
    save(cfg, r)
    return [], [r]


def cmd_serves(cfg, recs, a, today):
    """What an open question serves after its mint: an entry added is an open goal or direction; one removed is one held."""
    q = get(recs, a.id, "question", ("open",))
    add, drop = plus_minus(a.changes, f"serves takes +G and -D: flow serves {q.id} +G -D")
    held = list(q["serves"] or [])
    lacks = [x for x in drop if x not in held]
    if lacks:
        raise Refused(f"{q.id} serves no {', '.join(lacks)}; it serves {', '.join(map(str, held)) or 'nothing'}")
    there = [x for x in add if x in held]
    if there:
        raise Refused(f"{q.id} serves {', '.join(there)} already")
    check_serves(recs, add)
    q.fm["serves"] = [x for x in held if x not in drop] + add
    save(cfg, q)
    return [], [q]


def cmd_tag(cfg, recs, a, today):
    """`+T` adds a tag, `-T` removes one, the record's other tags kept in their order; no vocabulary is checked."""
    r = get(recs, a.id)
    if not a.changes:
        raise Refused(f"tag takes +T to add a tag and -T to remove one: flow tag {r.id} +T -U")
    add, drop = [], []
    for c in a.changes:
        if c[:1] not in "+-" or not c[1:].strip() or c[1:] != c[1:].strip():
            raise Refused(f"{c!r}: each change is +T to add a tag or -T to remove one, T a word")
        (add if c[0] == "+" else drop).append(c[1:])
    both = sorted(set(add) & set(drop))
    if both:
        raise Refused(f"{', '.join(both)} both added and removed")
    tags = list(r["tags"] or [])
    lacks = [t for t in drop if t not in tags]
    if lacks:
        raise Refused(f"{r.id} carries no tag {', '.join(lacks)}; its tags: {', '.join(map(str, tags)) or 'none'}")
    new = [t for t in tags if t not in drop] + [t for t in dict.fromkeys(add) if t not in tags]
    if new == tags:
        raise Refused(f"{r.id} carries {', '.join(add)} already")
    r.fm["tags"] = new
    save(cfg, r)
    return [], [r]


def cmd_note(cfg, recs, a, today):
    """A file's text appended to a record's body under today's date, through the record's own write (the reflow,
    markdownlint and the revert on a new violation): a body is edited without its file name guessed."""
    r = get(recs, a.id)
    text = read_body(a.body)
    if not text.strip():
        raise Refused(f"{a.body} is empty: a note needs words")
    append_note(r, today, "note:", text)
    save(cfg, r)
    return [], [r]


# --- the reference library, asked and never read ----------------------------------

def stat(r):
    """What a listing shows after a record's id: its state, or the forms a standing finding's evidence carries, its
    trust; a removed finding is `removed`."""
    return (", ".join(forms_of(r)) or "no evidence") if r.type == "finding" and r["state"] != "removed" else r["state"]


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

def refers_to(r, target, opaque=("formal", "peer-reviewed")):
    """Whether record r names `target`, a record's id or a repository path, by a link (`references`, `answered_by`,
    `serves`, `consumed_by`, an item of `blocked_by.on`), an evidence item, a source that is a path or a body link."""
    if any(v == target for _, v in link_ids(r)):
        return True
    if "evidence" in r.fm and any(evidence_path(e, opaque) == target for e in r["evidence"] or []):
        return True
    if source_path(r) == target:
        return True
    return target in tree_links(r.body)


def referrers(recs, target, deep=False, opaque=("formal", "peer-reviewed")):
    """The ids of the records naming `target`; with `deep`, of those naming them, and so on."""
    found, frontier = set(), [target]
    while frontier:
        x = frontier.pop()
        for r in recs.values():
            if r.id not in found and r.id != target and refers_to(r, x, opaque):
                found.add(r.id)
                if deep:
                    frontier.append(r.id)
    return found


def linked_by(recs, id_):
    """The records that refer to a record by a link, the notice's readers: (record, field) for each."""
    return [(r, f) for r in sorted(recs.values(), key=lambda r: r.id) for f, v in link_ids(r) if v == id_ and r.id != id_]


def cmd_find(cfg, recs, a, today):
    hits = []
    try:
        grep = re.compile(a.grep, re.I) if a.grep else None
    except re.error as e:
        raise Refused(f"--grep {a.grep!r} is not a regular expression: {e}")
    if a.deep and not a.refers:
        raise Refused("--deep follows --refers: flow find --refers ID --deep")
    if a.only and not a.form:
        raise Refused("--only holds the forms of --form: flow find --form stated --only")
    target = a.refers if not a.refers or a.refers in recs else norm_path(a.refers)  # a path is compared as the records carry it
    naming = referrers(recs, target, a.deep, cfg.opaque_forms) if a.refers else None
    for r in recs.values():
        if a.type and r.type != a.type:
            continue
        if a.state and r["state"] != a.state:
            continue
        if not a.state and r["state"] == "removed" and not a.id_:  # a removed record opens by its id, and is listed when asked by its state
            continue
        if a.id_ and r.id not in a.id_:
            continue
        if a.form and (r.type != "finding" or not set(a.form) <= set(forms_of(r)) or (a.only and set(a.form) != set(forms_of(r)))):
            continue
        if a.tag and a.tag not in (r["tags"] or []):
            continue
        if a.owner and r["owner"] != a.owner:
            continue
        if naming is not None and r.id not in naming:
            continue
        if a.parked and (r.type not in ("question", "task") or r["parked"] is None):
            continue
        if a.blocked and not blocked_now(cfg, recs, r, today):  # the records whose block holds today
            continue
        if a.held and not ((r.type == "task" and r["state"] == "active") or (r.type == "idea" and r["owner"])):
            continue
        if a.ranked and r["rank"] is None:
            continue
        if a.grep and not grep.search(render(r.fm, r.body)):
            continue
        hits.append(r)
    return hits


def backlinks(recs, id_):
    """The records naming a record, by the link they name it in: the five fields, `blocked_by` for a block's item."""
    out = defaultdict(list)
    for r, f in linked_by(recs, id_):
        if r.id not in out[f]:
            out[f].append(r.id)
    return dict(out)


def links(r, recs=()):
    """The records r names, by field; `blocked_by` the records among what it waits on, a date and words being none."""
    out = {}
    for f, v in link_ids(r):
        if f == "blocked_by" and v not in recs:
            continue
        out.setdefault(f, [])
        if v not in out[f]:
            out[f].append(v)
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
    """Every repository path a record refers to, by an evidence item, a body link or a source that is a path of the
    tree, with the records naming it and
    whether it is in the tree: the artifacts index, a pure function of the records."""
    paths = defaultdict(list)
    for r in sorted(recs.values(), key=lambda r: r.id):
        if r["state"] == "removed":
            continue
        for e in (r["evidence"] or []) if "evidence" in r.fm else []:
            p = evidence_path(e, cfg.opaque_forms)
            if p:
                paths[p].append({"id": r.id, "via": "evidence"})
        for p in sorted(set(tree_links(r.body))):
            paths[p].append({"id": r.id, "via": "body"})
        p = source_path(r)  # a source in words is no path; one that is a path is listed whether or not it is still in the tree
        if p and r.id not in [x["id"] for x in paths[p]]:
            paths[p].append({"id": r.id, "via": "source"})
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
    for f, vals in links(r, recs).items():
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
    edges = []  # every link but consumed_by, the mirror of a reference
    for r in sorted(recs.values(), key=lambda r: r.id):
        for f, vals in links(r, recs).items():
            edges += [(r.id, v, f) for v in vals if f != "consumed_by"]
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
    """The dates that have passed, as lines: a due date on an open task, a date a block waits on, with what the block
    still waits on where it holds on the rest."""
    out = []
    for r in sorted(recs.values(), key=lambda r: r.id):
        if r.type == "task" and r["state"] in ("ready", "active") and r["due"] is not None and str(r["due"]) <= today:
            out.append(f"{rel(cfg, cfg.index)}: due {r['due']} has passed: {r.id} — {r['summary']}")
        b = r["blocked_by"] if r.type in ("question", "task") and r["state"] in ("open", "ready") else None
        holds = blocked_now(cfg, recs, r, today)
        for o in blocked_on(b):
            if blocker_kind(cfg, recs, o) == "date" and o <= today:
                out.append(f"{rel(cfg, cfg.index)}: the block's date has passed: {r.id} waits on {o} no longer"
                           + (f"; it still waits on {', '.join(holds)}" if holds else ""))
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
            if not sec:
                continue
            rows = range(*sec)
            later = []
            if heading == "Due" and cfg.due_within is not None and today:  # the window: passed dates and those within it
                until = (dt.date.fromisoformat(today) + dt.timedelta(days=cfg.due_within)).isoformat()
                # the records say which tasks fall after it; the index's lines are what is printed, each by its id
                after = {r.id for r in (load_all(cfg) if recs is None else recs).values() if r.type == "task" and r["state"] in ("ready", "active")
                         and r["due"] is not None and str(r["due"]) > until}
                row_id = lambda i: (re.match(r"^- `([^`]+)`", ls[i]) or [None, None])[1]
                later = [i for i in rows if row_id(i) in after]
                rows = [i for i in rows if i not in later]
            lines = [f"{rel(cfg, cfg.index)}:{i + 1}: {ls[i]}" for i in rows]
            if later:  # said before the section's closing blank line
                at = len(lines) - 1 if rows and not ls[rows[-1]].strip() else len(lines)
                lines.insert(at, f"{rel(cfg, cfg.index)}: {len(later)} more due after {until}, beyond [index] due_within = "
                                 f"{cfg.due_within} day(s); the index's `Due` lists them")
            out += lines
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
        r = subprocess.run([exe, *args], capture_output=True, text=True, errors="replace", cwd=cfg.root, timeout=60)
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


def freeze_base(cfg):
    """What the freeze's check reads the log by: (why not, the log's lines, its entries, the entries from the top down
    to the newest committed one, that entry's commit and date); `why` names what is missing where it cannot be read."""
    why = None if cfg.log and cfg.log.is_file() else ("none is bound (`[paths] log`)" if not cfg.log else f"{rel(cfg, cfg.log)} does not exist")
    ls = cfg.log.read_text(encoding="utf-8").split("\n") if why is None else []
    entries = log_entries(ls)
    if why is None and not entries:
        why = f"{rel(cfg, cfg.log)} has no `## ` entry"
    if why is None and git(cfg, "rev-parse", "--is-inside-work-tree") is None:
        why = f"git is absent, or {cfg.root} is not in a work tree"
    if why is None and not (git(cfg, "log", "-n", "1", "--format=%H", "--", rel(cfg, cfg.log)) or "").strip():
        why = f"{rel(cfg, cfg.log)} has never been committed"
    base, base_date, named = None, None, []
    for s, e, d in entries if why is None else []:
        named.append("\n".join(ls[s:e]))
        base = (git(cfg, "log", "-n", "1", "--format=%H", "-S", ls[s], "--", rel(cfg, cfg.log)) or "").strip()
        if base:
            base_date = d
            break
    if why is None and not base:
        why = f"no entry of {rel(cfg, cfg.log)} is committed"
    return why, ls, entries, named, base, base_date


def changed_since(cfg, base):
    """The files changed since a commit, tracked or not, and the records among them by id, each with its path."""
    changed = set((git(cfg, "diff", "--name-only", "--relative", base) or "").split("\n")) \
        | set((git(cfg, "ls-files", "--others", "--exclude-standard") or "").split("\n"))
    changed.discard("")
    ids = {}
    for p in sorted(changed):
        m = cfg.id_re.match(Path(p).name)
        if m and (cfg.root / p).resolve().is_relative_to(cfg.research.resolve()):
            ids.setdefault(f"{m.group(1)}-{m.group(2)}", p)
    return changed, ids


def reranked_only(cfg, base, path):
    """Whether the record at `path`, a file at the commit, differs from it in its `rank` alone: the front matter's
    other fields and their order, and the body, are the same.  One `flow rank … --insert` renumbers every record below
    the one inserted, and a renumbering writes the `rank` field and no other (it does not refresh `checked`, which only
    a rank given to a record sets), so the session did not work on a record it only moved."""
    old = git(cfg, "show", f"{base}:./{path}")
    if old is None:
        return False
    try:
        was, now = parse_text(cfg.root / path, old.lstrip("﻿")), parse(cfg.root / path)
    except (Refused, OSError, ValueError):
        return False
    return was["rank"] != now["rank"] and list(was.fm) == list(now.fm) and was.body == now.body \
        and {k: v for k, v in was.fm.items() if k != "rank"} == {k: v for k, v in now.fm.items() if k != "rank"}


def names_id(text, id_):
    """Whether the log's text names a record: its id written out, or a range `PREFIX-NNNN…MMMM` (an en dash or three
    dots for the ellipsis, written with no spaces around it) of the same digit width with the id's number within it."""
    if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(id_), text):
        return True
    m = re.fullmatch(r"(.+)-(\d+)", id_)
    if not m:
        return False
    prefix, num = m.group(1), m.group(2)
    for a, b in re.findall(r"(?<![\w-])%s-(\d{%d})(?:…|–|\.\.\.)(\d{%d})(?![\w-])" % (re.escape(prefix), len(num), len(num)), text):
        if int(a) <= int(num) <= int(b):
            return True
    return False


def close_check(cfg, recs, today):
    """What a machine can see of a freeze, as (failures, what was checked, what could not be): the log's top entry
    dated today where the tree changed since the commit of the newest committed entry; every record changed since
    that commit named by an entry from the top down to it.  The hands are printed, never failed: each hand
    continues its own work."""
    fails, checked, undecided = [], [], []

    def fail(path, msg):
        fails.append({"code": "STATE", "id": None, "path": path, "msg": msg})

    why, ls, entries, named, base, base_date = freeze_base(cfg)
    if why is not None:
        undecided.append(f"the log's date and the records it names: {why}")
        return fails, checked, undecided
    checked += ["the log's date", "the records the log names"]
    changed, ids = changed_since(cfg, base)
    top, _, top_date = entries[0]
    if top_date != today and changed:
        fail(f"{rel(cfg, cfg.log)}:{top + 1}", f"the top entry is dated {top_date or 'nothing'}, not today ({today}), and {len(changed)} "
             f"file(s) changed since {base[:12]}, the commit of the entry of {base_date}: today's entry is written (`flow log add FILE`)")
    text = "\n".join(named)
    for i, p in sorted(ids.items()):
        if not names_id(text, i) and not reranked_only(cfg, base, p):
            fail(p, f"{i} changed since {base[:12]}, the commit of the log's entry of {base_date}, and no entry since names it"
                 " (`flow touched --unnamed` lists them all)")
    return fails, checked, undecided


def entries_since(cfg, base):
    """The log's entries from the top down to the newest one the log held at a commit, that one included, as the
    text an entry since the commit names a record in; every entry where the log was not there, none where there
    is no log."""
    if not (cfg.log and cfg.log.is_file()):
        return []
    ls = cfg.log.read_text(encoding="utf-8").split("\n")
    held = set((git(cfg, "show", f"{base}:./{rel(cfg, cfg.log)}") or "").split("\n"))
    named = []
    for s, e, d in log_entries(ls):
        named.append("\n".join(ls[s:e]))
        if ls[s] in held:
            break
    return named


def cmd_touched(cfg, recs, a, today):
    """The records changed since a commit, for the log's entry to name: by default since the commit of the log's
    newest committed entry, the base `flow state --check` reads, named by an entry from the top down to that one;
    `--since REV` since another commit, named by an entry from the top down to the newest the log held at REV;
    `--unnamed`, those no such entry names.  A record whose only change is its rank (a renumbering moved it) is left
    out of the list and returned apart, as the third value: the log's entry need not name it."""
    if a.since:
        if git(cfg, "rev-parse", "--is-inside-work-tree") is None:
            raise NotRun(f"git is absent, or {cfg.root} is not in a work tree")
        base = (git(cfg, "rev-parse", "--verify", "--quiet", a.since + "^{commit}") or "").strip()
        if not base:
            raise Refused(f"--since {a.since}: no such commit")
        named, base_date = entries_since(cfg, base), None
    else:
        why, ls, entries, named, base, base_date = freeze_base(cfg)
        if why is not None:
            raise NotRun(f"the base is the commit of the log's newest committed entry, and {why}; `--since REV` names another")
    _, ids = changed_since(cfg, base)
    text = "\n".join(named)
    out, moved = [], []
    for i, p in sorted(ids.items(), key=lambda x: (x[0].rsplit("-", 1)[0], x[0])):
        if reranked_only(cfg, base, p):
            moved.append(i)
            continue
        if a.unnamed and names_id(text, i):
            continue
        r = recs.get(i)
        out.append({"id": i, "path": p, "type": r.type if r else None, "state": stat(r) if r else "gone",
                    "summary": r["summary"] if r else None, "named": names_id(text, i)})
    said = f"since {base[:12]}" + (f", the commit of the log's entry of {base_date}" if base_date else "")
    return out, said, moved


# --- the log: an entry written at its top, the old ones archived by month ------------
#
# Dated entries, newest first, each a `## YYYY-MM-DD — headline` opening with a `**State.**`
# paragraph.  `flow log add` writes one at the top, reflowed and linted as a record is;
# `flow log archive` moves the old ones verbatim into one file per month beside the log.

# What a freeze holds that no machine sees: `flow state --check` prints them as the checklist the freeze's report answers.
SESSION_STEPS = (
    "the conversation's inventory, item by item: what it held, and the record, document or log entry each went to",
    "the sweep by meaning over the documents the session's records touch: every site a change reaches says the same",
    "the agent's memory checked: a note the session made stale is corrected or removed",
    "the gates by exit code: `flow check` and the project's hooks (`prek run --all-files` or `pre-commit run --all-files`)",
)
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
    recs = load_all(cfg, []) if not dest.is_file() else {}
    if a.as_[0] in recs:  # a record named by its id: its file, whatever its name
        dest = recs[a.as_[0]].path
    m = cfg.id_re.match(dest.name) if not dest.is_file() else None
    if m:
        twin = recs.get(f"{m.group(1)}-{m.group(2)}")
        if twin is not None:
            raise Refused(f"{dest} does not exist; {twin.id} is {rel(cfg, twin.path)}: name the record by its id, `--as {twin.id}`")
    text = read_body(draft).strip("\n")
    problems += [{"code": "REFLOW", "id": None, "path": f"{draft}:{n}", "msg": line} for n, line in reflow_misses(cfg, text)]
    # a record not minted yet: its body will stand under front matter whose summary is the title, as for any record
    had = dest.read_text(encoding="utf-8").rstrip("\n") if dest.is_file() else f"{FENCE}\nsummary: the record's\n{FENCE}" if m else ""
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
    params = ["type", "state", "tag", "owner", "grep"] + (["form"] if cfg.has("finding") else []) + ["refers"]
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
# The doctor names what an older model wrote and what it reads now, in two classes: the mechanical
# ones, whose line states the exact edit and which `--fix` applies in place (a field the record lacks,
# a word renamed, a kind to a tag, an evidence prefix read off its shape, a move out of a shard), and
# the judgment ones, which the agent settles by hand from the lines (a task in answered_by, a decision
# task, the directions file's bullets, a third hand, the bindings).  No migration logic for what needs
# judgment; after a fix, `flow index` is written and `flow check` says what is left.

def _item(path, was, now, cls=None, fix=None, rec=None, remark=None):
    """`remark`: words the doctor always prints beside the item, a remark and no thing for the hand."""
    return {"path": path, "was": was, "now": now, "cls": cls, "fix": fix, "rec": rec, "remark": remark}


# the mechanical classes, each the phrase its summary line carries
DOCTOR_CLASSES = {
    "field": "a field of this model the record lacks, written null or []",
    "derived-from": "`derived_from` renamed `references`",
    "parent": "a question's `parent` deleted, its question named in `references`",
    "requires": "a task's `requires` deleted, its findings named in `references`",
    "depends-on": "a finding's `depends_on` deleted, its findings named in `references`",
    "blocked": "`blocked` renamed `blocked_by`",
    "body": "a field whose words are the body's now (`criterion`, `dod`, `horizon`, `why_now`, `first_move`, `kill`) deleted, "
            "its words appended to the body as a dated line",
    "kind": "a `kind` made a tag (a task's, a question's `conjecture`) and deleted",
    "rider": "a task's `rider` deleted, the tag `rider` added where it was true",
    "serves-list": "a question's `serves` as one value made a list",
    "direction-serves": "a question's `direction` deleted, the direction named in `serves`",
    "finding-state": "a finding given `state: standing`",
    "abandoned": "`abandoned` renamed `closed`",
    "state-abandoned": "the state `abandoned` read as `aborted` (a task that was drawn) or `removed`",
    "state-decomposed": "the state `decomposed` read as `open`",
    "question": "a task's or a finding's `question` deleted, the question named in `references` where it was not",
    "status": "a finding's `status` deleted, the tag `refuted` added where it was that",
    "paper": "a finding's `paper` deleted",
    "evidence": "an evidence item given its form as a prefix, read off its shape",
    "shard": "a finding moved out of its shard into findings/",
    "answered-by": "`answered_by` as a list of one or none made one value",
    "consumed-by": "`consumed_by` as one id made a list",
    "blocked-on": "a block's `on` as one value made a list",
    "direction": "a question's `direction` by name deleted, the direction record's id named in `serves`",
    "ready-hand": "an owner or a drawn date on a ready task cleared",
    "closed-owner": "an owner on a closed record cleared",
    "archive": "a closed task moved into the archive",
    "inbox": "the inbox created, a `# Inbox` title and nothing else",
}


def doctor(cfg, today):
    """Every record and binding in an older model's words, each as an item: its path, what is written, what it
    reads now, and for a mechanical class the function that writes the edit."""
    out = []
    raw, task, fnd, ev = cfg.raw, cfg.raw.get("task", {}), cfg.raw.get("finding", {}), cfg.raw.get("evidence", {})
    for k in ("decision_kinds", "decision_owners"):
        if k in task:
            out.append(_item("flow.toml", f"[task] {k}", "goes: a decision is no card and no owner's work; delete the line"))
    if "question_optional_kinds" in task:
        out.append(_item("flow.toml", "[task] question_optional_kinds", "goes: any task may stand alone; delete the line"))
    for k in ("kinds", "default_kind"):
        if k in task:
            out.append(_item("flow.toml", f"[task] {k}", "goes: a task's kind is a tag now, written with --tag; delete the line, and the section once "
                             "empty, with the comments init wrote beside it"))
    if fnd:
        out.append(_item("flow.toml", "[finding]", "goes: a finding's status is read from the forms of its evidence, which [evidence] forms lists; "
                         "delete the section, with the comments init wrote beside it"))
    for k, now in (("manifest", "the declaration manifests are `formal.toml`'s alone ([manifest] files), and the flow asks `formal resolve` for formal evidence"),
                   ("manifest_roots", "a declaration's path is read under the package directories `formal.toml`'s [packages] binds"),
                   ("manifest_extension", "a declaration's path carries `.lean`, which the formal plugin owns")):
        if k in ev:
            out.append(_item("flow.toml", f"[evidence] {k}", f"goes: {now}; delete the line"))
    if "forms" not in ev:
        out.append(_item("flow.toml", "no [evidence] forms", f"forms = [{', '.join(json.dumps(f) for f in SHIPPED_FORMS)}]: "
                         "the forms the project accepts, of the five the kit ships and its own"))
    if cfg.kit_release is None:  # never mechanical: the machine does not know which release the project stood at
        now = cfg.script_version or "the release installed"
        out.append(_item("flow.toml", "no [kit] release", f"add `[kit] release = \"{cfg.script_version or 'vX.Y.Z'}\"` once the setup's steps up to "
                         f"{now} are taken: the release the setup last brought the project to; the setup's verify step "
                         "(`/research:research-init`) writes it"))
    if len(cfg.hand) > 2:
        out.append(_item("flow.toml", f"[hand] names {len(cfg.hand)} owners ({', '.join(cfg.hand)})",
                         "two hands, the agent's and the person's: a prover's task stays active in the agent's hand, the handoff's log entry "
                         "saying where it went, so its owner goes and its limit folds into the agent's (4 by default)"))
    legacy = list(fnd.get("statuses", ()))
    refuted = str(fnd.get("refuted", legacy[3] if len(legacy) > 3 else "refuted"))
    if "directions" in raw.get("paths", {}) or cfg.directions_file.is_file():
        dfile = cfg.directions_file.is_file()
        dpath = rel(cfg, cfg.directions_file)
        bullets = []
        if dfile:
            ls = cfg.directions_file.read_text(encoding="utf-8").split("\n")
            bullets = re.findall(r"^- \*\*(.+?)\*\*", re.sub(r"<!--.*?-->", "", "\n".join(ls), flags=re.S), re.M)
        out.append(_item(dpath if dfile else "flow.toml", "the directions file" if dfile else "[paths] directions",
                         ("directions are records now: `flow direction NAME --body FILE` for each bullet, its words in FILE; a question's "
                          "`direction` becomes the record's id in `serves` (--fix writes it once the record exists); then delete the file and the binding")
                         if bullets else "directions are records now, and the file holds none to carry: delete the file and the binding"))
        if dfile:
            sec = _section(ls, "Inbox")
            if sec:
                out.append(_item(f"{dpath}:{sec[0] + 1}", "an `## Inbox` section",
                                 f"the inbox is a file of its own: move its items to {rel(cfg, cfg.inbox)} and delete the section"))
            for name in bullets:
                out.append(_item(dpath, f"- **{name}**", f"`flow direction {json.dumps(name)} --body FILE`, the bullet's words in FILE"))
    if not cfg.inbox.is_file():
        def mk_inbox(cfg=cfg):
            cfg.inbox.parent.mkdir(parents=True, exist_ok=True)
            cfg.inbox.write_text("# Inbox\n", encoding="utf-8")
        out.append(_item(rel(cfg, cfg.inbox), "absent", "the person's inbox: create it, a `# Inbox` title and nothing else", "inbox", mk_inbox))
    recs = load_all(cfg, broken := [])
    for b in broken:
        out.append(_item(b["path"], "a record that does not read", b["msg"]))
    by_name = defaultdict(list)  # an open direction's name to its ids: one, or several where the hand must pick
    for d in recs.values():
        if d.type == "direction" and d["state"] == "open":
            by_name[str(d["summary"])].append(d.id)

    def setter(fm, **kv):
        return lambda: fm.update(kv)

    def renamer(fm, old, new):
        def go():
            v = fm.pop(old)
            if isinstance(v, list) and isinstance(fm.get(new), list):  # a list another fix wrote first: the renamed entries lead
                v = v + [x for x in fm[new] if x not in v]
            fm[new] = v
        return go

    def deleter(fm, k):
        return lambda: fm.pop(k, None)

    def add_refs(fm, k, vals):
        """The field k dropped and its values added to `references` where they are not there yet."""
        def go():
            fm.pop(k, None)
            refs = list(fm.get("references") or [])
            fm["references"] = refs + [x for x in dict.fromkeys(vals) if x not in refs and x not in (fm.get("derived_from") or [])]
        return go

    def to_body(r, k, label, words):
        """The field k dropped and its words, where it has some, appended to the body under the date."""
        def go():
            r.fm.pop(k, None)
            if words:
                append_note(r, today, f"{label} (moved from the field): {words}")
        return go

    def to_serves(fm, v):
        """A question's direction dropped and added to `serves`, a list, where it is not there yet."""
        def go():
            fm.pop("direction", None)
            held = fm.get("serves")
            held = list(held) if isinstance(held, list) else [held] if held else []
            fm["serves"] = held + ([v] if v and v not in held else [])
        return go

    def tag_with(fm, k, tag):
        """The field k dropped and `tag` added to the tags where it is not there yet; no tag where `tag` is None."""
        def go():
            fm.pop(k, None)
            if tag is not None and str(tag) not in [str(x) for x in fm.get("tags") or []]:
                fm["tags"] = list(fm.get("tags") or []) + [str(tag)]
        return go

    docs = {}  # the documents read while anchors are resolved

    for r in sorted(recs.values(), key=lambda r: r.id or ""):
        t, path, fm = r.type, rel(cfg, r.path), r.fm
        if t not in SCHEMA:
            continue
        st = r["state"]
        writes = set()  # the fields a fix below writes, which the last class does not add again
        add = lambda was, now, cls=None, fix=None, remark=None: out.append(_item(path, was, now, cls, fix, r, remark))
        if "abandoned" in fm:
            add("abandoned", "closed: rename the field, its date and reason unchanged" + ("" if st == "abandoned" else "; null where the record is not closed"),
                "abandoned", renamer(fm, "abandoned", "closed"))
        final = st
        if st == "abandoned":
            final = "aborted" if t == "task" and r["drawn"] else "removed"
            add("state: abandoned", f"state: {final}" + (" (it was drawn, then given up)" if final == "aborted" else " (dropped while ready)" if t == "task" else ""),
                "state-abandoned", setter(fm, state=final))
        if st == "decomposed":
            final = "open"
            add("state: decomposed", "state: open (that it was refined is read from its tasks)", "state-decomposed", setter(fm, state="open"))
        if t == "task" and (r["kind"] == "decision" or "decision" in (r["tags"] or [])) and st in ("ready", "active") and r["parked"] is None:
            add("kind: decision", "a task waiting on a decision is parked with a reason naming it (`flow park T --reason …`, returned first if active); or removed")
        by = r["answered_by"] if t == "question" and isinstance(r["answered_by"], list) else None
        if by is not None:
            tasks = [x for x in by if x in recs and recs[x].type == "task"]
            finds = [x for x in by if x in recs and recs[x].type == "finding"]
            settled = final in ("answered", "impossible")
            if tasks:
                add(f"answered_by: {', '.join(tasks)}", "a finding settles a question: mint it with "
                    f"`flow finding SUMMARY --evidence FORM:TARGET… --ref {tasks[0]}` and write its id in answered_by in place of the task, the migration's "
                    "one hand-write of that field; or, where no finding is to be had, read the question as removed (state, closed with the reason)")
            elif len(finds) > 1:
                add(f"answered_by: {', '.join(finds)}", "one finding answers a question: keep the one that settles it, as one value; each other names "
                    "the question in its references")
            elif len(by) > len(finds):
                add(f"answered_by: {', '.join(map(str, by))}", "one value, a finding, or null: an id here is no record")
            elif finds and not settled:
                add(f"answered_by: {finds[0]} on a question that is {final}", "clear it, or close the question answered by it, its state and "
                    "answered_by written together")
            elif not finds and settled and r["origin"] != "legacy":
                add(f"answered_by: [] on a question that is {final}", "the one finding that settles it, minted first (`flow finding … --ref T`) and "
                    "written here by hand; or the question read as removed (state, closed with the reason)")
            else:
                add("answered_by as a list", f"answered_by: {finds[0] if finds else 'null'} (one value, not a list)", "answered-by",
                    setter(fm, answered_by=finds[0] if finds else None))
        if t == "idea" and r["consumed_by"] and not isinstance(r["consumed_by"], list):
            add(f"consumed_by: {r['consumed_by']}", f"consumed_by as a list, `- {r['consumed_by']}` (every card it was folded into)", "consumed-by",
                setter(fm, consumed_by=[r["consumed_by"]]))
        # the links of v0.7.0: derived_from renamed, parent, requires and depends_on folded into references
        if "derived_from" in fm:
            add("derived_from", "references: rename the field, its entries unchanged", "derived-from", renamer(fm, "derived_from", "references"))
            writes.add("references")
        b = (fm.get("blocked") if "blocked" in fm else fm.get("blocked_by")) if t in ("question", "task") else None
        if "blocked" in fm and t in ("question", "task"):
            dated = [o for o in blocked_on(b) if blocker_kind(cfg, recs, o) == "words" and re.search(r"\d{4}-\d{2}-\d{2}", o)]
            add("blocked", "blocked_by: rename the field, its date, items and reason unchanged", "blocked", renamer(fm, "blocked", "blocked_by"),
                f"{', '.join(dated)} is words, which hold until removed by hand: a date waited on is an item written alone, "
                "YYYY-MM-DD (`flow unblock ID --on X`, then `flow block`)" if dated else None)
            writes.add("blocked_by")
        if isinstance(b, dict) and b.get("on") and not isinstance(b["on"], list):

            def fix_block(b=b):
                b["on"] = [b["on"]]
            add(f"blocked.on: {b['on']}", f"blocked_by.on as a list, `- {b['on']}` (every thing it waits on)", "blocked-on", fix_block)
        for k, cls in (("parent", "parent"), ("requires", "requires"), ("depends_on", "depends-on")):
            if k in fm and k in DROPPED_FIELDS.get(t, ()):
                vals = [str(x) for x in (fm[k] if isinstance(fm[k], list) else [fm[k]] if fm[k] else [])]
                add(f"{k}: {', '.join(vals) or 'none'}", "goes: delete the field" + (f", and name {', '.join(vals)} in references, where not yet" if vals else ""),
                    cls, add_refs(fm, k, vals))
                writes.add("references")
        for k in DROPPED_FIELDS.get(t, ()):
            if k not in fm:
                continue
            if k == "question":
                q = r[k]
                answers = q in recs and r.id in (recs[q]["answered_by"] if isinstance(recs[q]["answered_by"], list) else [recs[q]["answered_by"]])
                name_it = bool(q) and not answers
                add(f"{k}: {q or 'null'}", "goes: a task or a finding no longer belongs to a question; delete the field"
                    + (f", and name {q} in references, where it is not yet" if name_it else ""), "question", add_refs(fm, "question", [q] if name_it else []))
                writes.add("references")
            elif k == "kind":
                v = r[k]
                tag = (str(v) if v is not None else None) if t == "task" else "conjecture" if v == "conjecture" else None
                add(f"kind: {v}", "goes: a kind is a tag now; " + (f"add {json.dumps(tag)} to tags, and delete the field" if tag else "delete the field"),
                    "kind", tag_with(fm, "kind", tag))
            elif k == "rider":
                add(f"rider: {str(r[k]).lower()}", "goes: a hand-off is the tag `rider`; " + ("add it to tags, and delete the field" if r[k] is True else "delete the field"),
                    "rider", tag_with(fm, "rider", "rider" if r[k] is True else None))
            elif k == "status":
                def fix_status(fm=fm, is_refuted=str(r[k]) == refuted):
                    fm.pop("status", None)
                    if is_refuted and "refuted" not in (fm.get("tags") or []):
                        fm["tags"] = list(fm.get("tags") or []) + ["refuted"]
                add(f"status: {r[k]}", "goes: the forms of the evidence stand for it; delete the field" + (", and add the tag `refuted`" if str(r[k]) == refuted else ""),
                    "status", fix_status)
            elif k == "paper":
                add(f"paper: {r[k] or 'null'}", "goes: delete the field; the document is a reference `flow find --refers PATH` groups by", "paper", deleter(fm, "paper"))
        for k in BODY_FIELDS:
            if k in fm and k in DROPPED_FIELDS.get(t, ()):
                words = " ".join(str(fm[k]).split()) if fm[k] not in (None, "", []) else ""
                label = "criterion" if k == "kill" else k
                add(f"{k}: {words or 'null'}", "goes: delete the field" + (f", its words appended to the body as `{today} — {label} (moved from the field): …`" if words else ""),
                    "body", to_body(r, k, label, words))
        if t == "question" and "serves" in fm and not isinstance(fm["serves"], list):
            v = fm["serves"]
            add(f"serves: {v if v is not None else 'null'}", "serves as a list" + (f", `- {v}`" if v else ", `[]`") + " (every goal and direction it serves)",
                "serves-list", setter(fm, serves=[v] if v else []))
        if t == "question" and "direction" in fm:
            v = fm["direction"]
            if not v or v in recs or cfg.id_re.match(f"{v}.md"):
                add(f"direction: {v or 'null'}", "goes: delete the field" + (f", and name {v} in serves, where it is not yet" if v else ""),
                    "direction-serves", to_serves(fm, v))
                writes.add("serves")
            else:
                hits = by_name.get(str(v), [])
                if len(hits) == 1:
                    add(f"direction: {v}", f"{hits[0]}, the record minted from that bullet, named in serves; the field deleted", "direction", to_serves(fm, hits[0]))
                    writes.add("serves")
                elif hits:
                    add(f"direction: {v}", f"the id of one of the open directions of that name, {', '.join(hits)}, named in serves: yours to pick")
                else:
                    add(f"direction: {v}", "the id of the direction record minted from that bullet (`direction-0001`), named in serves, once it is")
        if t == "finding" and "state" not in fm:
            add("no state", "state: standing (a finding stands until it is removed)", "finding-state", setter(fm, state="standing"))
            writes.add("state")
        if t == "finding":
            for n, e in enumerate(r["evidence"] or []):
                e = str(e)
                s_e = split_evidence(e)
                if s_e and s_e[0] in ("statistical", "reference") and EV_ANCHORED.match(s_e[1]) \
                        and (cfg.root / EV_ANCHORED.match(s_e[1]).group(1)).is_file():
                    why = _resolve_document(cfg, s_e[1], docs, s_e[0])
                    if why:  # an anchor the check held to the file's existence alone before v0.5.0
                        add(f"evidence {e}", f"{why}: a document's anchor under {s_e[0]} is checked as a stated item's is now; "
                            f"cite the row, the numbered statement or the heading's anchor, or the path alone")
                if s_e is None:
                    prefix = ("formal" if cfg.ev_decl.match(e) or cfg.ev_declfile.match(e) else "statistical" if EV_PROBE.match(e)
                              else "stated" if cfg.ev_row.match(e) or cfg.ev_stmt.match(e) else None)

                    def fix_evidence(fm=fm, n=n, p=prefix):
                        fm["evidence"][n] = f"{p}:{fm['evidence'][n]}"
                    add(f"evidence {e}", f"{prefix}:{e} (its form as a prefix)" if prefix else "form:TARGET, the form one of [evidence] forms",
                        "evidence" if prefix else None, fix_evidence if prefix else None)
            if r.path.parent.resolve() != cfg.dir_of("finding").resolve():
                add(f"under {rel(cfg, r.path.parent)}/", f"move to {rel(cfg, cfg.dir_of('finding'))}/: findings no longer shard by document", "shard",
                    ("move", cfg.dir_of("finding")))
        owner = r["owner"] if t in ("task", "idea") else None
        held = (t == "task" and final == "active") or (t == "idea" and final == "open")
        if t == "task" and final == "ready" and (owner or r["drawn"]):
            add(f"owner: {owner or 'null'}, drawn: {r['drawn'] or 'null'} on a ready task", "owner: null and drawn: null (a ready task is in no hand; "
                "a decision owner's task was minted into that hand)", "ready-hand", setter(fm, owner=None, drawn=None))
        elif t == "task" and final in CLOSED_TASK and owner:
            add(f"owner: {owner} on a task that is {final}", "owner: null (a closed task is in no hand; its drawn date stays, the day its work began)",
                "closed-owner", setter(fm, owner=None))
        elif t == "idea" and final != "open" and (owner or r["drawn"]):
            add(f"owner: {owner or 'null'}, drawn: {r['drawn'] or 'null'} on an idea that is {final}", "owner: null and drawn: null (a closed idea is in no hand)",
                "closed-owner", setter(fm, owner=None, drawn=None))
        elif held and owner and owner not in cfg.owners:
            add(f"owner: {owner}", f"an owner [hand] does not list ({', '.join(cfg.owners)}): `flow return {r.id}`, then draw it into a listed hand "
                "where it is still worked")
        if t == "task" and final in CLOSED_TASK and r.path.parent.resolve() != cfg.archive.resolve():
            add(f"a {final} task under {rel(cfg, r.path.parent)}/", f"move to {rel(cfg, cfg.archive)}/: a closed task lives in the archive", "archive",
                ("move", cfg.archive))
        renamed = {OLD_FIELDS.get(k, k) for k in fm} | writes  # a dropped field is named above, a missing one below
        for k in SCHEMA[t]:
            if k not in renamed:
                # written only where still absent at its turn: an earlier fix may have put the tag or the folded question there
                add(f"no {k}", f"{k}: {'[]' if k in LIST_FIELDS else 'null'} (a field of this model)", "field",
                    lambda fm=fm, k=k: fm.setdefault(k, [] if k in LIST_FIELDS else None))
    return out


# What reads each binding `flow init` writes, for `flow doctor`'s notes on a key a flow.toml written earlier lacks.
BINDING_READERS = {
    "paths.records": "every command: the records' directory", "paths.index": "`flow index` and `flow check`: the generated index",
    "paths.archive": "the closing transitions: where a closed task moves", "paths.inbox": "`flow state` and the `whatsnext` skill: the person's inbox",
    "paths.log": "`flow log add`, `flow state` and `flow state --check`: the dated log",
    "paths.log_archive": "`flow log archive`: where the log's old entries move, beside the log unless bound",
    "paths.reflow_module": "every write and `flow reflow`: the project's own sentence splitter",
    "paths.markdownlint_config": "every write: the markdownlint configuration a new violation is read by",
    "question.sizes": "`flow question`, `flow task` and `flow set … size`: the sizes a question or a task takes",
    "evidence.statement_words": "`flow check` and the evidence mints: the words a numbered statement's anchor takes",
    "evidence.row_id": "`flow check` and the evidence mints: the pattern a table row's id matches",
    "evidence.probes": "`flow check`: the probes register statistical evidence resolves against",
    "library.command": "`flow check`: the command that answers the library's keys",
    "index.recent_findings": "`flow index`: how many recent findings the index lists",
    "index.oldest_ideas": "`flow index`: how many of the oldest ideas the index lists",
    "index.due_within": "`flow state`: how far ahead the due list reaches",
}


def doctor_notes(cfg):
    """The keys `flow init` writes now, set or commented, that the project's flow.toml has neither set nor commented
    (a file written by an earlier init): each with the default the template carries and what reads it.  Never a
    failure; `[kit] release` is a thing for the hand instead, `[evidence] forms` too, and `[hand]`'s keys are owners."""
    try:
        text = (cfg.root / "flow.toml").read_text(encoding="utf-8")
    except OSError:
        return []
    def toml_value(v):
        try:
            tomllib.loads(f"k = {v}")
            return True
        except tomllib.TOMLDecodeError:
            return False
    key_line = re.compile(r"^\s*#?\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*(?:#\s.*)?$")

    def keys(src):
        out, section = {}, None
        for line in src.split("\n"):
            m = re.match(r"^\s*#?\s*\[([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\]\s*$", line)
            if m:
                section = m.group(1)
                continue
            m = key_line.match(line)
            # a commented line is a key only when its value reads as TOML: a prose comment is not
            if m and section and (not line.lstrip().startswith("#") or toml_value(m.group(2))):
                out.setdefault(f"{section}.{m.group(1)}", m.group(2))
        return out
    have = keys(text)
    notes = []
    log = cfg.raw.get("paths", {}).get("log") if isinstance(cfg.raw.get("paths"), dict) else None
    for k, default in keys(init_text(cfg.records_name, log, release=cfg.script_version)).items():
        section, key = k.rsplit(".", 1)
        if k in have or section in ("hand", "kit", "evidence.resolvers") or k == "evidence.forms":
            continue
        notes.append({"key": f"[{section}] {key}", "default": default,
                      "reads": BINDING_READERS.get(k, "the record ids of that type" if section == "prefixes" else "the flow's commands")})
    return notes


def doctor_fix(cfg, items):
    """Apply every mechanical item: each record's edits together, its front matter re-ordered to the schema, written
    without the lint, and the reflow only where a field's words were appended to the body, then moved where an item
    says; the index refreshed.
    Returns (the counts by class, the items left to the hand), an item whose move finds its destination taken among them."""
    fixed, left = Counter(), [it for it in items if it["fix"] is None]
    moves = defaultdict(list)
    for it in items:
        if it["fix"] is None:
            continue
        if isinstance(it["fix"], tuple):
            moves[it["rec"].id].append(it)
        elif it["rec"] is None:
            it["fix"]()
            fixed[it["cls"]] += 1
    by_rec = defaultdict(list)
    for it in items:
        if it["fix"] is not None and not isinstance(it["fix"], tuple) and it["rec"] is not None:
            by_rec[it["rec"].id].append(it)
    for rid, its in by_rec.items():
        r = its[0]["rec"]
        body = r.body
        for it in its:
            it["fix"]()
            fixed[it["cls"]] += 1
        if r.body != body:  # words a field held, appended to the body: reflowed as any write of a body is
            r.body = cfg.reflow(r.body)
        fm = {k: r.fm[k] for k in SCHEMA[r.type] if k in r.fm}
        fm.update({k: v for k, v in r.fm.items() if k not in SCHEMA[r.type]})
        r.fm = fm
        write_whole(r.path, render(r.fm, r.body))
    for rid, its in moves.items():
        for it in its:
            dest_dir = it["fix"][1]
            dest = dest_dir / it["rec"].path.name
            if dest.exists():
                left.append(_item(it["path"], it["was"], f"{it['now']}; a file of that name is there already, so the move is yours"))
                continue
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(it["rec"].path), str(dest))
            it["rec"].path = dest
            fixed[it["cls"]] += 1
    if fixed:
        cfg.index.parent.mkdir(parents=True, exist_ok=True)
        write_whole(cfg.index, render_index(cfg, load_all(cfg, [])))
    return fixed, left


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
# due_within = 14   # `flow state` lists the tasks due within this many days, and every passed date; unset, all

[kit]
# The research-kit release the setup last brought this project to: written by `flow init`, moved by the
# setup's verify step (`/research:research-init`) once every step up to the installed release is taken.  A flow
# script older than it refuses to write, the project having been brought further on another machine.
{kit}
"""

INIT_RESEARCH = """[question]
sizes = ["small", "medium", "large"]

[evidence]
# The forms a finding's evidence takes, each item `form:target`, the finding's trust the forms it carries.
# The kit ships five: formal (a declaration of the prover's library, machine-checked), statistical (a probe of the
# register, or a committed result by its path), peer-reviewed (a card of the library), stated (a row, a
# statement or a heading of a document of the project: its own word, the trust to raise) and reference (any
# other source, a link).  Keep the ones the project accepts and add its own words; the instructions say what
# each means here.
forms = ["formal", "statistical", "peer-reviewed", "stated", "reference"]
# What a document's anchor names beside a heading (`doc.md#its-anchor`): a numbered statement, one of these
# words then its number (`doc.md#Theorem 2.1`, `doc.md#§4.2`), and a table row, whose first cell matches
# row_id (`doc.md#FV-1`).  Unset, the words and the id shown.
# statement_words = ["Theorem", "Proposition", "Lemma", "Corollary", "Definition", "Remark", "Fact", "Conjecture", "Example"]
# row_id = "[A-Z]{2,3}-[A-Za-z0-9]+"
# A probes register: a Markdown table whose first column names each self-asserting script.
# probes = "probes/README.md"
# A form whose targets another tool owns is asked of that tool: one request on its standard input holds every item
# of the form, one answer on its standard output says each resolves or why not (the flow's page names the
# protocol).  Unset, `formal` is asked of the formal plugin installed beside the research one, else `formal` on PATH,
# either only where a formal.toml stands at the root; `formal = []` asks none.  Another prover's, or a form of the
# project's own, binds the whole command here, run at the project root.
# [evidence.resolvers]
# formal = ["formal", "resolve", "--protocol"]

[library]
# The reference library, when the project has one: the command that answers `keys`.  Unset, the
# flow asks the library skill installed beside the flow skill, else `library` on PATH, either only
# where a library.toml stands at the root; `command = []` asks none.
# command = ["library"]

"""

INSTRUCTIONS = """What the project's instructions (CLAUDE.md, AGENTS.md) should now carry, in their words:

- `flow …` here is the flow skill's script run by its installed path from the project root, no command
  on PATH: under Claude Code `python3 ~/.claude/plugins/cache/research-kit/research/<version>/skills/flow/scripts/flow.py …`.
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
  When the person says "whatsnext" or "freeze", they mean these skills: each is called every time, even if it
  ran earlier in the session, and every step is taken; a request ending "… and freeze" is two requests, the work
  and then the `freeze` skill.
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


def init_text(records="records", log=None, owners=("agent", "owner"), release=None):
    """The flow.toml `flow init` writes, `release` this script's (a commented line where it is unknown)."""
    return INIT_TOML.format(
        dir=records,
        log=(f'log = "{log}"                 # the dated log whose top entry `flow state` prints\n'
             f'log_archive = "{Path(log).with_name(Path(log).stem + "-archive").as_posix()}"   '
             '# `flow log archive` moves the old entries here verbatim, one file per month\n') if log else
            '# log = "WORKLOG.md"             # the dated log whose top entry `flow state` prints\n'
            '# log_archive = "WORKLOG-archive"   # `flow log archive` moves the old entries here verbatim, one file per month\n',
        owners="\n".join(f"{o} = {0 if o == owners[-1] and len(owners) > 1 else 4}" for o in owners),
        research=INIT_RESEARCH,
        kit=f'release = "{release}"' if release else '# release = "vX.Y.Z"   # unknown: written by the setup\'s verify step')


def init_instructions(root):
    """The paragraphs `flow init` prints, for the bindings as they stand: the records directory and the log read from
    the project's flow.toml where one stands and reads, the defaults otherwise.  It writes nothing and refuses nothing."""
    try:
        paths = tomllib.loads((root / "flow.toml").read_text(encoding="utf-8")).get("paths", {})
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        paths = {}
    paths = paths if isinstance(paths, dict) else {}
    records, log = str(paths.get("records") or "records"), paths.get("log")
    return INSTRUCTIONS.format(records=records, log_line=LOG_BOUND.format(log=log) if log else LOG_UNBOUND)


def do_init(root, a):
    """Write flow.toml, the record directories and the index; refuse over an existing flow.toml, and with --force
    over one whose `[kit] release` is newer than this script."""
    toml = root / "flow.toml"
    if toml.is_file() and not a.force:
        raise Refused(f"{toml} exists (use --force to overwrite the bindings file alone)")
    mine, theirs, release = script_version(), None, script_version()
    if toml.is_file():
        try:
            theirs = tomllib.loads(toml.read_text(encoding="utf-8")).get("kit", {}).get("release")
        except (tomllib.TOMLDecodeError, UnicodeDecodeError, AttributeError):
            theirs = None
        # a rewrite keeps the release the setup last brought the project to: only the setup's verify step moves it,
        # and a file with none gets the commented line, which `flow doctor` names until the setup writes it
        release = theirs if release_key(theirs) else None
        if release_key(mine) and release_key(theirs) and release_key(theirs) > release_key(mine):
            raise Refused(f"{toml}'s [kit] release is {theirs} and this flow script is {mine}: the project was brought to {theirs} "
                          f"on another machine or checkout; move this plugin to {theirs} first: {KIT_MOVE}")
    kinds = list(TYPES)
    owners = a.owner or ["agent", "owner"]
    for o in owners:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", o):
            raise Refused(f"--owner {o!r}: an owner is one word of letters, digits, `_` and `-` (it is a key of flow.toml)")
    text = init_text(a.records, a.log, owners, release)
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
probes = "probes/README.md"
[evidence.resolvers]
formal = ["{python}", "resolver.py"]
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

# A resolver the selftest binds in place of `formal resolve --protocol`: it reads the manifest `decls.txt` and answers in the
# protocol, `resolver.mode` making it misbehave (`exit1`, `raise`, `say`, `nojson`, `v2`, `skip`) and `resolver.log` counting what it was asked.
SELFTEST_RESOLVER = """import json, sys
from pathlib import Path
mode = Path("resolver.mode").read_text().strip() if Path("resolver.mode").exists() else ""
if mode == "exit1":
    sys.exit(1)
if mode == "raise":
    raise ValueError("boom")
if mode == "say":
    print("first line")
    print("COULD NOT CHECK: no lake")
    sys.exit(1)
if mode == "nojson":
    print("hello")
    sys.exit(0)
req = json.load(sys.stdin)
with open("resolver.log", "a") as log:
    log.write(json.dumps(req["items"]) + "\\n")
rows = [l.split() for l in Path("decls.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
mods = {r[1] for r in rows if r[0] == "module"}
decls = {(r[0], r[1]) for r in rows if len(r) == 2 and r[0] != "module"} | {(r[1], r[2]) for r in rows if len(r) == 3 and r[0] in ("private", "field")}
items = {}
for t in req["items"]:
    path, _, name = t.partition("#")
    module = path[:-5].replace("/", ".")
    if not path.endswith(".lean"):
        items[t] = {"ok": False, "why": "formal takes a declaration (Path.lean#name) or a whole module (Path.lean)"}
    elif not name:
        items[t] = {"ok": True} if module in mods else {"ok": False, "why": "module " + module + " is not in the manifest"}
    elif any(m == module and (n == name or n.endswith("." + name)) for m, n in decls):
        items[t] = {"ok": True}
    else:
        items[t] = {"ok": False, "why": "`" + name + "` is not in the manifest"}
if mode == "skip":
    items.popitem()
print(json.dumps({"protocol": 2 if mode == "v2" else 1, "items": items}))
"""

SOURCE = Path(__file__).read_text(encoding="utf-8")


def selftest():
    failures = []

    def expect(name, cond):
        print(f"  {'ok ' if cond else 'BAD'} {name}")
        if not cond:
            failures.append(name)

    def text_of(c, argv):
        """What a command prints to a person (not the JSON page), as a string."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            dispatch(c, argv, today=today, as_json=False, quiet=False)
        return buf.getvalue()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "flow.toml").write_text(SELFTEST_TOML.replace("{python}", json.dumps(sys.executable)[1:-1]))
        (root / "resolver.py").write_text(SELFTEST_RESOLVER)
        (root / "decls.txt").write_text("module Lib.Foo 1\nmodule Lib.Bar 1\nLib.Foo lemma_L\nLib.Bar lemma_B\nprivate Lib.Foo helper\nuses Lib.Bar lemma_B lemma_L\n")
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
        (root / "res.md").write_text("It is done.\n")
        res = str(root / "res.md")
        cfg = Config(root)
        today = "2026-09-25"
        expect("formal evidence is resolved by the resolver flow.toml binds, and the flow reads no manifest: the answer is the resolver's",
               cfg.resolvers["formal"] == ([sys.executable, "resolver.py"], "flow.toml's [evidence.resolvers]") and cfg.resolved == ("formal",)
               and resolve_evidence(cfg, "formal:Lib/Bar.lean#lemma_B", {}) is None
               and resolve_evidence(cfg, "formal:Lib/Bar.lean#lemma_L", {}) == "`lemma_L` is not in the manifest")

        def run(argv, ok=True):
            rc, payload = dispatch(cfg, argv, today=today, as_json=True, quiet=True)
            expect(" ".join(argv[:2]) + (" refused" if not ok else ""), (rc == 0) == ok)
            if (rc == 0) != ok:
                for pr in payload["problems"]:
                    print("      ", pr["code"], pr.get("path") or pr.get("id"), pr["msg"])
            return payload

        new = lambda argv: run(argv)["created"][0]
        ids = lambda argv: [r["id"] for r in run(argv)["records"]]
        noticed = lambda p, id_: [x["id"] for n in p["notices"] if n["id"] == id_ for x in n["refers"]]
        (root / "bridge.md").write_text("The bridge between A and B.\n")
        d = new(["direction", "Bridge", "--body", str(root / "bridge.md")])
        expect("a direction is a record, open, the owner's words its body",
               load_all(cfg)[d]["state"] == "open" and load_all(cfg)[d].body == "The bridge between A and B.\n")
        idea = new(["idea", "an idea", "--source", "test"])
        (root / "answer.md").write_text("A finite counterexample answers it.\n")
        p = run(["question", "Does A imply B?", "--consume", idea, "--serves", d, "--body", str(root / "answer.md")])
        q = p["created"][0]
        recs = load_all(cfg)
        expect("a question minted --consume IDEA consumes the idea into it and names it in its references; it serves what --serves names, "
               "is open, checked today, and its body says what counts as an answer",
               recs[q]["references"] == [idea] and recs[idea]["state"] == "consumed" and recs[idea]["consumed_by"] == [q]
               and recs[q]["serves"] == [d] and recs[q]["state"] == "open" and recs[q]["checked"] == today and p["changed"] == [idea]
               and "counterexample" in recs[q].body and not p["notices"])
        run(["question", "again", "--consume", idea], ok=False)  # consumed already
        run(["question", "S", "--serves", "direction-0099"], ok=False)  # no such record
        run(["question", "S", "--serves", idea], ok=False)  # an idea is no goal or direction
        run(["question", "S", "--ref", "idea-0099"], ok=False)  # no such record
        run(["question", "S", "--ref", idea, "--ref", idea], ok=False)  # named twice
        t1 = new(["task", "prove L", "--ref", q, "--tag", "research"])
        t2 = new(["task", "design the route", "--ref", q, "--tag", "research"])
        sq = new(["question", "sub question", "--ref", q])
        recs = load_all(cfg)
        expect("a task and a sub-question minted from a question name it in their references, and the question is left as it was",
               recs[t1]["references"] == [q] and recs[sq]["references"] == [q] and recs[t1]["tags"] == ["research"]
               and recs[q]["state"] == "open" and recs[t1]["state"] == "ready" and not {"kind", "rider", "dod"} & set(recs[t1].fm))
        run(["draw", t1, "--owner", "root"])
        run(["draw", t2, "--owner", "root"])
        t3 = new(["task", "third", "--ref", sq])
        run(["draw", t3, "--owner", "root"], ok=False)  # hand full
        run(["return", t2, "--note", "later"])
        p = run(["return", t3], ok=False)
        expect("return on a ready task says it is ready and in no hand, as an idea in no hand is answered",
               "is ready, in no hand" in p["problems"][0]["msg"] and "draw it first" not in p["problems"][0]["msg"])
        tree = lambda: {x: x.read_text(encoding="utf-8") for x in sorted((root / "research").rglob("*.md"))}
        before = tree()
        run(["make", t1, "--resolution", "missing.md"], ok=False)
        (root / "empty.md").write_text("\n")
        p = run(["make", t1, "--resolution", str(root / "empty.md")], ok=False)
        expect("make refuses an empty resolution, and a refused make leaves the tree as it was",
               "is empty" in p["problems"][0]["msg"] and tree() == before)
        p = run(["make", t1, "--resolution", res])
        recs = load_all(cfg)
        expect("a made task is archived, its owner cleared, its drawn date kept, its resolution in the body, and nothing minted",
               "research/archive/" in p["records"][-1]["path"] and recs[t1]["owner"] is None and recs[t1]["drawn"] == today
               and recs[t1].body.rstrip().endswith(f"{today} — resolution:\n\nIt is done.") and p["created"] == [])
        run(["make", t1, "--resolution", res], ok=False)  # done already
        p = run(["finding", "L holds", "--evidence", "formal:Lib/Foo.lean#lemma_L", "stated:papers/alpha.md#FV-1", "--ref", t1])
        f = p["created"][0]
        expect("a finding stands, lives under findings/, references the task it came from, and its trust is the forms it carries",
               "research/findings/" in p["records"][0]["path"] and load_all(cfg)[f]["references"] == [t1] and load_all(cfg)[f]["state"] == "standing"
               and not {"question", "status", "paper", "depends_on"} & set(load_all(cfg)[f].fm) and p["records"][0]["forms"] == "formal, stated")
        run(["draw", t2, "--owner", "root"])
        (root / "wall.md").write_text("The route hits a wall.\n")
        p = run(["abort", t2, "--reason", "wall", "--resolution", str(root / "wall.md")])
        body = Path(root / p["records"][-1]["path"]).read_text(encoding="utf-8")
        expect("a resolution is appended under its date, and the task's notes stay",
               "returned: later" in body and body.rstrip().endswith(f"{today} — resolution:\n\nThe route hits a wall."))
        recs = load_all(cfg)
        expect("an aborted task carries its state and its dated reason in closed",
               recs[t2]["state"] == "aborted" and recs[t2]["closed"] == {"date": today, "reason": "wall"})
        fr = new(["finding", "the route fails", "--evidence", "statistical:probes/p.py", "--ref", t2, "--tag", "refuted"])
        for had in ("", "A note.\n"):  # a resolution opening with a heading, on an empty body and after a note
            r = type("R", (), {"body": had})()
            append_note(r, today, "resolution:", "\n## Result\n\nIt is done.\n\n")
            expect("a resolution file's text is set apart from its dated line by one blank line" + (", after a note" if had else ", on an empty body"),
                   render({"id": "task-0001"}, r.body).endswith(f"---\n\n{had and had + chr(10)}{today} — resolution:\n\n## Result\n\nIt is done.\n"))
        # a question's closing is its own act: a ready task that names it holds nothing back, and the notice names who refers to it
        p = run(["finding", "B follows from L", "--evidence", "stated:papers/alpha.md#Theorem 2.1", "--ref", t1, "--answers", q])
        fa = p["created"][0]
        recs = load_all(cfg)
        expect("a finding minted --answers Q closes Q answered by it, an open sub-question and its task notwithstanding",
               recs[q]["state"] == "answered" and recs[q]["answered_by"] == fa and p["changed"] == [q] and recs[sq]["state"] == "open")
        expect("the notice names every record referring to the closed question, each with its state, a closed one among them, "
               "and never the finding the same command minted",
               set(noticed(p, q)) == {idea, t1, t2, sq} and {"id": t2, "state": "aborted"} in p["notices"][0]["refers"] and fa not in noticed(p, q))
        txt = text_of(cfg, ["note", q, "--body", res])
        expect("a note changes no state and prints no notice", "may need a follow-up" not in txt)
        p = run(["finding", "a second answer", "--evidence", "stated:papers/alpha.md#Theorem 2.1", "--answers", q], ok=False)
        expect("a question answered already is reopened first, the refusal says", f"`flow reopen {q} --reason R` first" in p["problems"][0]["msg"])
        p = run(["finding", "a corollary", "--evidence", "stated:papers/alpha.md#Theorem 2.1", "--ref", q])
        fc = p["created"][0]
        expect("a finding the answering produced references the question", load_all(cfg)[fc]["references"] == [q])
        # evidence is added: the trust raised, a proof formalized (an item whose file is gone is swapped or retired, below)
        run(["evidence", fa, "stated:papers/alpha.md#Theorem 2.1"], ok=False)  # there already
        run(["evidence", fa, "formal:Lib/Foo.lean#nope"], ok=False)
        p = run(["evidence", fa, "formal:Lib/Foo.lean#lemma_L"])
        expect("evidence appends an item it resolves, and the finding's forms grow with it",
               load_all(cfg)[fa]["evidence"] == ["stated:papers/alpha.md#Theorem 2.1", "formal:Lib/Foo.lean#lemma_L"] and p["records"][0]["forms"] == "formal, stated")
        expect("find --form lists the findings carrying a form",
               fa in ids(["find", "--form", "formal"]) and fc in ids(["find", "--form", "stated"]) and f not in ids(["find", "--form", "statistical"]))
        expect("find --form F --form G lists the findings carrying both, and --only those carrying no other",
               fa in ids(["find", "--form", "formal", "--form", "stated"]) and fc not in ids(["find", "--form", "formal", "--form", "stated"])
               and fc in ids(["find", "--form", "stated", "--only"]) and fa not in ids(["find", "--form", "stated", "--only"])
               and fa in ids(["find", "--form", "stated", "--form", "formal", "--only"]) and fa not in ids(["find", "--form", "formal", "--only"]))
        run(["find", "--only"], ok=False)  # --only holds the forms of --form
        qk = new(["question", "Is A true?", "--tag", "conjecture"])
        expect("a conjecture is a question tagged conjecture, found by the tag; a question may stand alone",
               ids(["find", "--tag", "conjecture"]) == [qk] and load_all(cfg)[qk]["references"] == [] and "kind" not in load_all(cfg)[qk].fm)
        run(["remove", qk, "--reason", "only for the find"])
        # an item whose file a later change deleted is swapped or retired, the note keeping what it was
        run(["evidence", fc, "formal:Lib/Foo.lean#lemma_L"])
        run(["evidence", fc, "--replace", "formal:Lib/Foo.lean#lemma_L", "statistical:probes/nothing.py"], ok=False)  # the new one resolved
        run(["evidence", fc, "--replace", "formal:Lib/Foo.lean#lemma_Z", "statistical:probes/p.py"], ok=False)  # not among the items
        run(["evidence", fc, "--replace", "formal:Lib/Foo.lean#lemma_L", "stated:papers/alpha.md#Theorem 2.1"], ok=False)  # there already
        run(["evidence", fc, "stated:papers/alpha.md#Theorem 2.1", "--retire", "formal:Lib/Foo.lean#lemma_L", "--reason", "r"], ok=False)  # one way at a time
        p = run(["evidence", fc, "--replace", "formal:Lib/Foo.lean#lemma_L", "statistical:probes/p.py"])
        expect("evidence --replace swaps the item in place and notes it in the body",
               load_all(cfg)[fc]["evidence"] == ["stated:papers/alpha.md#Theorem 2.1", "statistical:probes/p.py"]
               and f"{today} — evidence `formal:Lib/Foo.lean#lemma_L` replaced by `statistical:probes/p.py`" in load_all(cfg)[fc].body
               and not p["notices"])
        run(["evidence", fc, "--retire", "statistical:probes/p.py"], ok=False)  # no reason
        run(["evidence", fc, "--reason", "gone"], ok=False)  # a reason alone
        run(["evidence", fc, "--retire", "statistical:probes/q.py", "--reason", "gone"], ok=False)  # not among the items
        run(["evidence", fc, "--retire", "statistical:probes/p.py", "--reason", "the probe was deleted"])
        expect("evidence --retire removes the item and notes the reason in the body",
               load_all(cfg)[fc]["evidence"] == ["stated:papers/alpha.md#Theorem 2.1"]
               and f"{today} — evidence `statistical:probes/p.py` retired: the probe was deleted" in load_all(cfg)[fc].body)
        run(["evidence", fc, "--retire", "stated:papers/alpha.md#Theorem 2.1", "--reason", "gone"], ok=False)  # the last item: V6
        # a hand-edited finding may hold an item twice: one occurrence is acted on, and the last one is never retired
        twice = load_all(cfg)[fc]
        twice.fm["evidence"] = ["stated:papers/alpha.md#Theorem 2.1"] * 2
        twice.path.write_text(render(twice.fm, twice.body), encoding="utf-8")
        run(["evidence", fc, "--retire", "stated:papers/alpha.md#Theorem 2.1", "--reason", "r"])
        expect("evidence --retire of an item held twice removes one occurrence and leaves the other",
               load_all(cfg)[fc]["evidence"] == ["stated:papers/alpha.md#Theorem 2.1"])
        run(["evidence", fc, "--retire", "stated:papers/alpha.md#Theorem 2.1", "--reason", "r"], ok=False)  # the one left: V6
        twice = load_all(cfg)[fc]
        twice.fm["evidence"] = ["stated:papers/alpha.md#Theorem 2.1"] * 2
        twice.path.write_text(render(twice.fm, twice.body), encoding="utf-8")
        run(["evidence", fc, "--replace", "stated:papers/alpha.md#Theorem 2.1", "statistical:probes/p.py"])
        expect("evidence --replace of an item held twice swaps one occurrence only",
               load_all(cfg)[fc]["evidence"] == ["statistical:probes/p.py", "stated:papers/alpha.md#Theorem 2.1"])
        run(["evidence", fc, "--retire", "statistical:probes/p.py", "--reason", "back to the one item"])
        run(["remove", t3, "--reason", "not needed"])
        i2 = new(["idea", "a second idea"])
        q3 = new(["question", "Q2", "--consume", i2])
        run(["rank", q3, "1"])
        run(["set", q3, "summary", "Q2, put sharper", "--note", "the owner's words"])
        recs = load_all(cfg)
        expect("a summary set keeps what it read in the body, dated, with the words given for the change",
               recs[q3]["summary"] == "Q2, put sharper" and f"{today} — summary set; it read: Q2. the owner's words" in recs[q3].body)
        for gone in ("criterion", "kill", "rider", "serves", "kind", "depends_on", "horizon", "dod", "why_now"):
            p = run(["set", q3, gone, "x"], ok=False)
            expect(f"set refuses {gone}, a field no longer, and says the way it goes now", "`flow " in p["problems"][0]["msg"])
        run(["set", q3, "size", "huge"], ok=False)  # not a size
        run(["set", q3, "state", "answered"], ok=False)  # a transition's field
        q4 = new(["question", "Q to park", "--consume", new(["idea", "an idea to park"])])
        run(["rank", q4, "2"])
        was = load_all(cfg)[q4]["checked"]
        rc, _ = dispatch(cfg, ["park", q4, "--reason", "waiting"], today="2026-09-26", as_json=True, quiet=True)
        expect("park on a question refreshes its checked date, a judgment about one record", rc == 0 and load_all(cfg)[q4]["checked"] == "2026-09-26" != was)
        raw = load_all(cfg)[q4]
        raw.fm.update({"checked": today, "parked": {**raw["parked"], "date": today}})
        raw.path.write_text(render(raw.fm, raw.body), encoding="utf-8")
        run(["park", q4, "--reason", "again"], ok=False)  # parked already
        run(["block", q4, "--on", q3, "--reason", "needs its answer"])
        run(["block", q4, "--on", "the release", "--reason", "again"], ok=False)  # blocked already, q3 open
        run(["block", q3, "--on", f, "--reason", "r"], ok=False)  # a finding is waited on by nothing
        run(["block", q3, "--on", q3, "--reason", "r"], ok=False)  # itself
        p = run(["block", q3, "--on", q, "--reason", "r"], ok=False)  # answered: it would never hold
        expect("a block on a record already settled is refused: it would never hold", "would never hold" in p["problems"][0]["msg"])
        run(["block", q3, "--on", today, "--reason", "r"], ok=False)  # a date not after today
        p = run(["block", q3, "--on", "2026-02-30", "--reason", "r"], ok=False)  # of the shape of a date, and no day of the calendar
        expect("a block on an item of the shape YYYY-MM-DD that is no day of the calendar is refused, not read as words",
               "is no day of the calendar" in p["problems"][0]["msg"] and load_all(cfg)[q3]["blocked_by"] is None)
        run(["block", q3, "--on", "the release of 2026-02-30", "--reason", "r"])  # words that merely contain a date stay words
        run(["unblock", q3])
        tz = new(["task", "a task to tag and note"])
        for verb in (["park", q3], ["block", q3, "--on", "the release"], ["remove", tz], ["abort", t1], ["reopen", q]):
            run(verb + ["--reason", "  "], ok=False)  # a reason is words, refused here and not left to V15
        p = run(["make", tz, "--resolution", res], ok=False)
        expect("a refusal of a task not drawn names the draw", f"`flow draw {tz} --owner O`" in p["problems"][0]["msg"])
        # a record's tags changed after its mint, and a body appended to without its file name
        run(["tag", tz, "+upkeep"])
        run(["tag", tz, "+chore", "-upkeep", "+chore"])
        expect("tag adds and removes, the other tags kept in their order", load_all(cfg)[tz]["tags"] == ["chore"])
        for bad in ([], ["-upkeep"], ["+a", "-a"], ["chore"], ["+"], ["+chore"]):
            run(["tag", tz] + bad, ok=False)  # nothing, a tag it lacks, both ways, no sign, no word, there already
        (root / "note.md").write_text("A remark on it.\nIt has two sentences.\n")
        run(["note", tz, "--body", str(root / "note.md")])
        expect("note appends a file's text to the body under the date", load_all(cfg)[tz].body.endswith(f"{today} — note:\n\nA remark on it.\nIt has two sentences.\n"))
        (root / "note.md").write_text("\n")
        run(["note", tz, "--body", str(root / "note.md")], ok=False)  # an empty note
        # `-` reads a body from the standard input, so a one-off body needs no scratch file
        with contextlib.redirect_stdout(io.StringIO()):
            saved_in, sys.stdin = sys.stdin, io.StringIO("Read from the standard input.\n")
            try:
                run(["note", tz, "--body", "-"])
                sys.stdin = io.StringIO("An idea's body from a pipe.\n")
                piped = new(["idea", "an idea with a piped body", "--body", "-"])
            finally:
                sys.stdin = saved_in
        expect("--body - reads the body from the standard input, a note's and a mint's",
               load_all(cfg)[tz].body.endswith("note:\n\nRead from the standard input.\n")
               and "An idea's body from a pipe." in load_all(cfg)[piped].body)
        run(["idea", "an idea whose body is words", "--body", "words, not a file"], ok=False)
        expect("every --body that reads a file says FILE in its help, and `-`",
               all(act.metavar == "FILE" and "-" in (act.help or "") for sub in build_parser()._subparsers._group_actions[0].choices.values()
                   for act in sub._actions if "--body" in act.option_strings or "--resolution" in act.option_strings))
        # the references after a mint: added and removed, any record in any state, with tag's refusals
        run(["ref", tz, "+" + q])
        for bad in ([], ["+" + q], ["-" + q3], ["+" + tz], ["+idea-0999"], ["+" + q3, "-" + q3], [q3]):
            run(["ref", tz] + bad, ok=False)  # nothing, held, not held, itself, no such record, both ways, no sign
        run(["ref", tz, "+" + q3, "-" + q])
        p = run(["ref", q3, "-" + i2], ok=False)
        expect("ref adds and removes references and refuses to remove the card a consumed idea names",
               load_all(cfg)[tz]["references"] == [q3] and f"{i2} is consumed into {q3}" in p["problems"][0]["msg"])
        run(["ref", tz, "-" + q3])
        # a block on several things, a record, a date written alone and words holding a date, each told apart exactly
        run(["block", tz, "--on", q3, "--on", q3, "--reason", "r"], ok=False)  # one thing twice
        run(["block", tz, "--on", q3, "--on", f, "--reason", "r"], ok=False)  # a finding among them
        run(["block", tz, "--on", q3, "--on", "2026-10-01", "--on", "the release of 2026-10-01", "--reason", "needs all three"])
        recs = load_all(cfg)
        p = run(["show", q3])
        expect("a block keeps a list, each record among them a back-reference, found by --refers, the index's wait naming all",
               recs[tz]["blocked_by"]["on"] == [q3, "2026-10-01", "the release of 2026-10-01"]
               and tz in [x["id"] for x in p["backlinks"].get("blocked_by", [])] and tz in ids(["find", "--refers", q3])
               and f"blocked on {q3}, 2026-10-01, the release of 2026-10-01" in cfg.index.read_text(encoding="utf-8"))
        expect("an item is a record by an id's shape, a date written alone and a day of the calendar, else words",
               [blocker_kind(cfg, recs, x) for x in (q3, "task-0999", "2026-10-01", "2026-02-30", "the release of 2026-10-01")]
               == ["record", "record", "date", "words", "words"])
        p = run(["unblock", tz, "--on", "the release"], ok=False)
        expect("unblock --on takes an item as written, and names the items the block holds", "2026-10-01" in p["problems"][0]["msg"])
        run(["unblock", tz, "--on", "the release of 2026-10-01", "--note", "it is out"])
        recs = load_all(cfg)
        expect("unblock --on removes the one item, the note dated", recs[tz]["blocked_by"]["on"] == [q3, "2026-10-01"]
               and f"{today} — unblocked the release of 2026-10-01: it is out" in recs[tz].body)
        later = "2026-10-02"
        rc, pl = dispatch(cfg, ["draw", tz, "--owner", "root"], today=later, as_json=True, quiet=True)
        expect("blocked is calculated: a date reached holds no more, an open question still does",
               rc == 1 and f"blocked on {q3}" in pl["problems"][0]["msg"] and "2026-10-01" not in pl["problems"][0]["msg"]
               and tz in ids(["find", "--blocked"]) and blocked_now(cfg, recs, recs[tz], later) == [q3])
        run(["unblock", tz])
        run(["tag", tz, "-chore", "+decision"])
        decision = lambda: [x for x in dispatch(cfg, ["doctor"], today=today, as_json=True, quiet=True)[1]["problems"] if "kind: decision" in x["msg"]]
        had = decision()
        run(["park", tz, "--reason", "the owner's choice of route"])
        expect("the doctor's decision line fires on a ready task tagged decision, and settles once it is parked", had and not decision())
        run(["unpark", tz])
        run(["tag", tz, "-decision"])
        stray = load_all(cfg)[tz].path.with_name(tz + "-a-guess.md")
        stray.write_text("A body written beside the record.\n")
        p = run(["check"], ok=False)
        expect("planted: a file named for a record that reads elsewhere → V0 naming the record's path",
               any(x["code"] == "V0" and f"{tz} is {rel(cfg, load_all(cfg, [])[tz].path)}" in x["msg"] and "stray" in x["msg"] for x in p["problems"]))
        stray.unlink()
        run(["remove", tz, "--reason", "it stood here to test tag and note"])
        recs = load_all(cfg)
        expect("a parked and blocked question keeps its rank and both waits", recs[q4]["rank"] == 2
               and recs[q4]["parked"]["reason"] == "waiting" and recs[q4]["blocked_by"] == {"date": today, "on": [q3], "reason": "needs its answer"})
        run(["index"])
        idx = cfg.index.read_text(encoding="utf-8")
        expect("the index marks the waits on the ranked list and lists the waiting question apart, with no why-now, first move or rider",
               f"   waits: parked {today} — waiting" in idx and f"   waits: blocked on {q3} {today} — needs its answer" in idx
               and "## Parked or blocked questions" in idx and "why now" not in idx and "first move" not in idx and "Rider" not in idx)
        p = run(["check"])
        expect("check green on the happy path", not p["problems"])
        q5 = new(["question", "Q4"])
        t4 = new(["task", "t", "--ref", q5])
        run(["draw", t4, "--owner", "root"])
        run(["make", t4, "--resolution", res])
        for bad in ("formal:Lib/Foo.lean#nope", "formal:Lib/Bar.lean#lemma_L", "stated:Lib/Foo.lean#lemma_L", "formal:papers/alpha.md#Theorem 2.1",
                    "nonsense:papers/alpha.md#Theorem 2.1", "papers/alpha.md#Theorem 2.1", "statistical:results/nope.md",
                    "statistical:results/bench.md#BR-9", "benchmark:results/none.csv"):
            run(["finding", "bad", "--evidence", bad, "--ref", t4], ok=False)  # not in the manifest, another module, no document, no form, …
        run(["finding", "bad", "--evidence", "stated:papers/alpha.md#Theorem 2.1", "stated:papers/alpha.md#Theorem 2.1", "--ref", t4], ok=False)  # twice
        p = run(["finding", "fine", "--evidence", "stated:papers/alpha.md#Theorem 2.1", "statistical:results/bench.md#BR-1", "--evidence",
                 "benchmark:results/bench.md", "benchmark:the run of 2026-09", "reference:https://example.org/x", "--ref", t4, "--answers", q5])
        fb = p["created"][0]
        expect("a finding carries a result's row, a form of the project's and a link, its forms the words it carries; --evidence repeats",
               p["records"][0]["forms"] == "benchmark, reference, stated, statistical" and len(load_all(cfg)[fb]["evidence"]) == 5)
        (root / "results" / "rates.md").write_text("# Rates\n\n## Measured rates (2026)\n\n```text\n## not a heading\n```\n\n"
                                                   "## Measured rates (2026)\n\n### `R4` and *friends* ##\n")
        run(["evidence", fb, "statistical:results/rates.md#measured-rates-2026", "statistical:results/rates.md#measured-rates-2026-1",
             "reference:results/rates.md#r4-and-friends"])
        expect("a heading's anchor resolves under statistical and reference, a repeated heading numbered as GitHub numbers it",
               "reference:results/rates.md#r4-and-friends" in load_all(cfg)[fb]["evidence"])
        p = run(["evidence", fb, "statistical:results/rates.md#not-a-heading"], ok=False)  # inside a code fence
        expect("an anchor that is no row, statement or heading is refused, the nearest heading named",
               "no row" in p["problems"][0]["msg"] and "#measured-rates-2026" not in p["problems"][0]["msg"])
        p = run(["evidence", fb, "stated:results/rates.md#measured-rate-2026"], ok=False)
        expect("a misspelt heading anchor names the nearest", "the nearest heading's anchor is #measured-rates-2026" in p["problems"][0]["msg"])
        run(["evidence", fb, "reference:results/rates.md#BR-1"], ok=False)  # a row's id, and no such row
        (root / "results" / "gh.md").write_text("---\ntitle: front matter\n---\nRates by\nround\n=====\n\n## _Friends_ and **foes**\n\n"
                                                "## Rates <small>(2026)</small> &amp; `snake_case` __init__\n\n- an item\n---\n")
        expect("a heading's anchor is GitHub's: `_` emphasis and an HTML tag dropped, an entity read, code and an "
               "intraword underscore kept, a setext heading seen, a front matter block and a list item none",
               heading_anchors((root / "results" / "gh.md").read_text()) == ["rates-by-round", "friends-and-foes", "rates-2026--snake_case-init"])
        run(["evidence", fb, "stated:results/gh.md#friends-and-foes", "stated:results/gh.md#rates-by-round"])
        for outside in (str(root / "results" / "rates.md"), "../rates.md", "results/../../rates.md"):
            p = run(["evidence", fb, f"reference:{outside}"], ok=False)
            expect(f"an evidence path outside the tree is refused, though the file is there: {outside}",
                   "outside the tree" in p["problems"][0]["msg"])
        own = root / "own"
        own.mkdir()
        (own / "doc.md").write_text("# Doc\n\n**Law 3.** It holds.\n\nConfirmation 2 holds as well.\n\n§4.2 Rates\n\n| A2 | the round |\n")
        bindings = lambda ev: (own / "flow.toml").write_text("[evidence]\n" + ev)
        bindings('statement_words = ["Law", "Confirmation", "§"]\nrow_id = "[A-Z][0-9]+"\n')
        oc = Config(own)
        rv = lambda item: resolve_evidence(oc, item, {})
        expect("the statement words and the row id a project binds are read, a symbol's number written with no space",
               rv("stated:doc.md#Law 3") is None and rv("stated:doc.md#Confirmation 2") is None and rv("stated:doc.md#§4.2") is None
               and rv("stated:doc.md#A2") is None and "row A9 is not in" in rv("stated:doc.md#A9") and rv("stated:doc.md#Law 4") is not None)
        expect("a statement word the project does not bind is read as a heading's anchor, and fails",
               "no row" in rv("stated:doc.md#Theorem 1") and rv("stated:doc.md#doc") is None)
        for ev, why in (('statement_words = ["Main theorem"]\n', "statement word"), ('row_id = "[A-Z]*"\n', "empty"), ('row_id = "[A-Z"\n', "no regular")):
            bindings(ev)
            try:
                Config(own)
                said = ""
            except Refused as e:
                said = str(e)
            expect(f"flow.toml's {ev.split(' =')[0]} refused: {why}", why in said)
        (own / "flow.toml").write_text("[index]\ndue_within = -1\n")
        try:
            Config(own)
            said = ""
        except Refused as e:
            said = str(e)
        expect("flow.toml's due_within refused: not a number of days", "not a number of days" in said)
        p = run(["question", "Does the paper's bound hold?", "--source", "./papers/alpha.md"])
        qs = p["created"][0]
        recs = load_all(cfg)
        expect("a question minted from a document, no idea first, names it as its source, listed by artifacts and --refers",
               recs[qs]["source"] == "papers/alpha.md" and recs[qs]["references"] == [] and qs in ids(["find", "--refers", "papers/alpha.md"])
               and {"id": qs, "via": "source"} in next(x for x in run(["artifacts"])["artifacts"] if x["path"] == "papers/alpha.md")["records"])
        (cfg.root / "papers" / "draft.md").write_text("# Draft\n", encoding="utf-8")
        qd = run(["question", "Is the draft's claim right?", "--source", "papers/draft.md"])["created"][0]
        (cfg.root / "papers" / "draft.md").unlink()
        gone = next((x for x in run(["artifacts"])["artifacts"] if x["path"] == "papers/draft.md"), None)
        expect("a source that is a path, gone from the tree, stays in the artifacts index as MISSING, as a body link does",
               gone is not None and not gone["exists"] and {"id": qd, "via": "source"} in gone["records"])
        run(["remove", qd, "--reason", "minted for the test"])
        for words in ("arXiv:2301.12345", "v1.2", "notes/none.md"):
            p = run(["idea", "an idea", "--source", words], ok=False)
            expect(f"a source with a path's shape that is not in the tree is refused at mint, words asked for: {words}",
                   "reads as a repository path" in p["problems"][0]["msg"] and "in words" in p["problems"][0]["msg"])
        ia = new(["idea", "an idea from the paper", "--source", "./papers//alpha.md"])
        ib = new(["idea", "an idea from a machine's file", "--source", str(cfg.root / "papers" / "alpha.md")])
        recs = load_all(cfg)
        expect("a source that is a path of the tree is minted root-relative; one outside it is words, never an artifact",
               recs[ia]["source"] == "papers/alpha.md" and ia in ids(["find", "--refers", "papers/alpha.md"])
               and source_path(recs[ib]) is None and not any(x["path"].startswith("/") for x in run(["artifacts"])["artifacts"]))
        run(["remove", ia, "--reason", "minted for the test"])
        run(["remove", ib, "--reason", "minted for the test"])
        run(["remove", qs, "--reason", "minted for the test"])
        run(["index"])
        p = run(["check"])
        expect("a form of the project's with no path is reported unchecked, never failed",
               not p["problems"] and any(f"{fb}: benchmark:the run of 2026-09: unchecked" in w for w in p["warnings"]))
        rt = new(["task", "an upkeep chore", "--tag", "upkeep", "--due", "2026-10-01", "--after", "mint the same chore for the next month"])
        run(["task", "a chore due soon", "--due", "soon"], ok=False)
        p = run(["task", "a chore due in month 13", "--due", "2026-13-01"], ok=False)
        expect("a due date that is no day of the calendar is refused", "is no day of the calendar" in p["problems"][0]["msg"])
        run(["set", rt, "due", "2026-02-30"], ok=False)
        run(["set", rt, "due", "never"], ok=False)
        run(["set", rt, "due", "2026-10-02"])
        run(["set", rt, "after", ""], ok=False)
        run(["set", rt, "size", "small", "--note", "a chore"])
        recs = load_all(cfg)
        expect("set wrote the due date and the size, its note dated as `FIELD set: N`",
               recs[rt]["due"] == "2026-10-02" and recs[rt]["size"] == "small" and f"{today} — size set: a chore" in recs[rt].body)
        lt = new(["task", "a task with no question"])  # any task may stand alone
        tq0 = new(["task", "a task naming an answered question", "--ref", q])  # a reference obliges nothing
        run(["remove", lt, "--reason", "it stood alone to test it"])
        run(["remove", tq0, "--reason", "it stood here to test a reference"])
        # a ready task waits too: parked and blocked at once, and drawn only once neither holds
        run(["park", rt, "--reason", "after the release"])
        run(["block", rt, "--on", "the next release", "--reason", "it needs the tag"])
        run(["draw", rt, "--owner", "root"], ok=False)
        run(["unpark", rt, "--note", "the release is out"])
        run(["draw", rt, "--owner", "root"], ok=False)  # still blocked: words hold until removed by hand
        run(["unblock", rt])
        tw = new(["task", "a task it waits on"])
        run(["block", rt, "--on", tw, "--on", "2026-09-30", "--reason", "the task and the day"])
        run(["draw", rt, "--owner", "root"], ok=False)
        run(["remove", tw, "--reason", "settled, so the block holds on the date alone"])
        expect("a record waited on that settles holds the block no more; the date still does", rt in ids(["find", "--blocked"]))
        rc, _ = dispatch(cfg, ["draw", rt, "--owner", "root"], today="2026-09-30", as_json=True, quiet=True)
        expect("on the day, nothing holds: the draw goes through and clears the block", rc == 0 and load_all(cfg)[rt]["blocked_by"] is None)
        dispatch(cfg, ["return", rt], today="2026-09-30", as_json=True, quiet=True)
        run(["park", rt, "--reason", "r"])
        run(["unpark", rt])
        p = run(["set", rt, "question", q3], ok=False)
        expect("set names `flow ref` for a field of references", "flow ref" in p["problems"][0]["msg"])
        shallow, deep = set(ids(["find", "--refers", q])), set(ids(["find", "--refers", q, "--deep"]))
        expect("find --refers lists who names a record by any link, the idea consumed into it included, and --deep who names those",
               {idea, t1, t2, sq, fc} <= shallow and {f, fa, fr} <= deep and f not in shallow)
        expect("find --refers PATH lists the records whose evidence names a repository path", {f, fa, fc, fb} <= set(ids(["find", "--refers", "papers/alpha.md"])))
        run(["find", "--deep"], ok=False)  # --deep follows --refers
        # an idea drawn like a task, worked into other cards, consumed into one of them
        wi = new(["idea", "an idea to work"])
        run(["draw", wi, "--owner", "root"])
        run(["draw", wi, "--owner", "root"], ok=False)  # in hand already
        run(["consume", wi], ok=False)  # nothing references it yet
        sub = new(["idea", "a narrower idea", "--ref", wi])
        p = run(["return", wi, "--note", "half worked"])
        expect("an idea put back partly worked lists what it produced so far",
               load_all(cfg)[wi].body.rstrip().endswith(f"returned: half worked; produced so far: {sub}"))
        run(["draw", wi, "--owner", "root"])
        wt = new(["task", "a chore it shows", "--tag", "upkeep", "--ref", wi])
        run(["consume", wi])
        recs = load_all(cfg)
        expect("an idea consumed is folded into every card that references it, and leaves the hand",
               recs[wi]["state"] == "consumed" and recs[wi]["consumed_by"] == sorted([sub, wt]) and recs[wi]["owner"] is None)
        run(["draw", wi, "--owner", "root"], ok=False)  # consumed
        run(["remove", sub, "--reason", "folded into the chore"])
        sub2 = new(["idea", "an idea referring to a removed one", "--ref", sub])
        expect("a removed record may be referenced: nothing is deleted, and nothing is refused for it", load_all(cfg)[sub2]["references"] == [sub])
        run(["remove", sub2, "--reason", "it stood here to test a reference"])
        run(["remove", sub, "--reason", "again"], ok=False)
        expect("find leaves a removed record out unless asked by its state or its id",
               sub not in ids(["find", "--type", "idea"]) and sub in ids(["find", "--state", "removed"]) and ids(["find", "--id", sub]) == [sub])
        # wrong and impossible, each a settled closing listed as such
        qw = new(["question", "Is the empty sum odd?"])
        run(["wrong", qw, "--reason", "parity is not defined for it"])
        qi = new(["question", "Does it halt?"])
        run(["impossible", qi, "--by", q], ok=False)  # not a finding
        fs = sorted(r.id for r in load_all(cfg).values() if r.type == "finding")
        run(["impossible", qi, "--by", fs[0]])
        run(["index"])
        idx = cfg.index.read_text(encoding="utf-8")
        expect("wrong and impossible are listed as settled, a removed record nowhere",
               f"`{qw}` — Is the empty sum odd? [wrong]" in idx and f"`{qi}` — Does it halt? [impossible]" in idx and sub not in idx)
        heap = new(["idea", "an idea for the heap"])
        # the reference library, asked through its `keys` answer (a stub stands for it here)
        stub = root / "lib_stub.py"
        stub.write_text('import json\nprint(json.dumps({"ok": True, "cite_prefix": "lib:", "cards": '
                        '{"jen1990": {"state": "registered", "grade": "parts", "extracts": ["lemma"]}, '
                        '"aside": {"state": "excluded", "grade": "unread"}}, "problems": []}))\n')
        cfg.library_cmd = [sys.executable, str(stub)]
        run(["idea", "an idea citing lib:jen1990 twice over, lib:jen1990, and lib:aside"])
        for bad in ("peer-reviewed:nobody2000", "peer-reviewed:jen1990#theorem9", "peer-reviewed:Jen 1990"):
            run(["finding", "bad", "--evidence", bad, "--ref", t4], ok=False)  # no such card, no such extract, a key not words
        fp = new(["finding", "as Jen shows", "--evidence", "peer-reviewed:jen1990#lemma", "--ref", t4])
        run(["index"])
        p = run(["check"])
        expect("check green with a cited key the library holds and a peer-reviewed item it holds", not p["problems"])
        expect("the coverage counts the cited keys by grade and the excluded ones",
               p["coverage"]["library"] == {"cited": 2, "records": 1, "grades": {"parts": 1, "unread": 1}, "excluded": 1})
        txt = text_of(cfg, ["check"])
        expect("check says in words how many keys the records cite, and which route answered for formal and what the register bounds",
               "library: 2 key(s) cited from the records" in txt and "resolver formal via flow.toml's [evidence.resolvers]" in txt
               and f"probe evidence via {cfg.probes}" in txt and p["coverage"]["resolvers"] == {"formal": "via flow.toml's [evidence.resolvers]"}
               and "manifest" not in p["coverage"])
        keep = cfg.probes
        cfg.probes = "probes/gone.md"
        txt = text_of(cfg, ["check"])
        cfg.probes = keep
        expect("check says a bound register that is absent is not found, not that none is bound",
               "probe evidence unchecked (register probes/gone.md not found)" in txt and "no register bound" not in txt)
        # the resolver: asked once for every item of its form, and one that does not answer is one problem, no record's
        log = root / "resolver.log"
        log.unlink(missing_ok=True)
        p = run(["check"])
        asked = [json.loads(ln) for ln in log.read_text().splitlines()]
        expect("check asks the formal resolver once, with every formal item of the records on its standard input",
               len(asked) == 1 and set(asked[0]) >= {"Lib/Foo.lean#lemma_L"} and len(asked[0]) == len(set(asked[0])) and not p["problems"])
        log.unlink()
        run(["evidence", fa, "formal:Lib/Bar.lean#lemma_B"])
        expect("a mint asks the resolver once, for the items it mints", [json.loads(ln) for ln in log.read_text().splitlines()] == [["Lib/Bar.lean#lemma_B"]])
        run(["evidence", fa, "--retire", "formal:Lib/Bar.lean#lemma_B", "--reason", "it was a test of the resolver"])
        for mode, said in (("exit1", "exit 1"), ("raise", "(ValueError: boom)"), ("say", "(COULD NOT CHECK: no lake)"),
                           ("nojson", "Expecting value"), ("skip", "no answer for")):
            (root / "resolver.mode").write_text(mode)
            p = run(["check"], ok=False)
            ours = [x for x in p["problems"] if x["code"] == "V6"]
            expect(f"a resolver that does not answer ({mode}) is one V6 problem with no record, the formal items unchecked",
                   len(ours) == 1 and ours[0]["id"] is None and ours[0]["msg"].startswith("the resolver for formal did not answer: ") and said in ours[0]["msg"]
                   and "Traceback" not in ours[0]["msg"] and "first line" not in ours[0]["msg"]
                   and any("formal:Lib/Foo.lean#lemma_L: unchecked: the resolver for formal did not answer" in w for w in p["warnings"]))
            expect(f"a mint passes a formal item as unchecked while the resolver does not answer ({mode})",
                   resolve_evidence(cfg, "formal:Lib/Foo.lean#nope", {}).startswith("unchecked: the resolver for formal did not answer: "))
            txt = text_of(cfg, ["check"])
            expect(f"the coverage line says the route did not answer ({mode})", "formal unchecked (did not answer: " in txt)
        (root / "resolver.mode").write_text("v2")
        p = run(["check"])
        expect("an answer in a protocol this flow does not read leaves the items unchecked with that reason, and no problem",
               not p["problems"] and any("answered in protocol 2, which this flow does not read (it reads 1)" in w for w in p["warnings"])
               and p["coverage"]["resolvers"]["formal"].startswith("unchecked (the resolver for formal answered in protocol 2"))
        run(["finding", "unchecked", "--evidence", "formal:Lib/Foo.lean#nope", "--ref", t4])  # the mint passes it unchecked
        (root / "resolver.mode").unlink()
        fu = [r.id for r in load_all(cfg).values() if r.type == "finding" and "formal:Lib/Foo.lean#nope" in (r["evidence"] or [])][0]
        p = run(["check"], ok=False)
        expect("an item that passed unchecked is refused once the resolver answers", any(x["id"] == fu and x["code"] == "V6" and "`nope` is not in the manifest" in x["msg"] for x in p["problems"]))
        run(["remove", fu, "--reason", "a test of the unchecked mint"])
        cfg.resolvers["formal"] = ([], "disabled in flow.toml's [evidence.resolvers]")
        expect("a resolver turned off leaves formal evidence unchecked, said in the coverage",
               resolve_evidence(cfg, "formal:Lib/Foo.lean#lemma_L", {}).startswith("unchecked: no resolver for formal (disabled")
               and "formal unchecked (disabled in flow.toml's [evidence.resolvers])" in text_of(cfg, ["check"]))
        cfg.resolvers["formal"] = ([sys.executable, "resolver.py"], "flow.toml's [evidence.resolvers]")

        # goals: formed by the owner, served by questions, reached or given up
        (root / "reach.md").write_text("Reached means B is proved, before the talk.\n")
        g = new(["goal", "Reach B", "--ref", d, "--body", str(root / "reach.md")])
        recs = load_all(cfg)
        expect("a goal references the direction it was produced along, which stays open, and its body says what reached means",
               recs[g]["references"] == [d] and recs[d]["state"] == "open" and "Reached means" in recs[g].body)
        qg = new(["question", "Qg", "--consume", new(["idea", "an idea for the goal"]), "--serves", g])
        run(["question", "Qx", "--serves", "goal-0099"], ok=False)
        run(["rank", qg, "3"])
        run(["serves", q4, "+" + g])
        for bad in ([], ["+" + g], ["-" + d], ["+" + q], ["+" + g, "-" + g]):
            run(["serves", q4] + bad, ok=False)  # nothing, held, not held, a question, both ways
        run(["serves", q, "+" + g], ok=False)  # an answered question: what it served stays as history
        run(["serves", rt, "+" + g], ok=False)  # a task serves through the question it references
        run(["index"])
        idx = cfg.index.read_text(encoding="utf-8")
        expect("the index lists the due task first, each goal and direction by its summary with the questions serving it, "
               "and what a ranked question serves",
               idx.index("## Due") < idx.index("## Next (ranked)") and f"`{rt}` — an upkeep chore [due 2026-10-02]" in idx
               and f"## Goals\n\n- `{g}` — Reach B\n  - `{q4}` — Q to park\n  - `{qg}` — Qg\n" in idx
               and f"## Directions\n\n- `{d}` — Bridge [{today}]\n  - no open question serves it\n" in idx and f"   serves: {g}" in idx)
        expect("flow directions renders the open directions as the owner's list",
               f"- **Bridge** ({today}, `{d}`) — The bridge between A and B." in run(["directions"])["text"])
        p = run(["giveup", g, "--reason", "B is out of reach this year"])
        recs = load_all(cfg)
        expect("a goal given up clears nothing on its questions, which keep it and their ranks, and the notice names them",
               recs[g]["state"] == "given_up" and recs[g]["closed"] == {"date": today, "reason": "B is out of reach this year"}
               and recs[qg]["serves"] == [g] and recs[q4]["serves"] == [g] and recs[qg]["rank"] == 3
               and set(noticed(p, g)) == {q4, qg} and "released" not in p)
        txt = text_of(cfg, ["unpark", q4])
        expect("unpark prints the notice under the changed line, in the owner's words, a referring record that is not removed",
               f"changed {q4}" in txt and "  refers to it, may need a follow-up: " in txt.split(f"changed {q4}", 1)[1])
        raw = load_all(cfg)[q4]
        raw.fm["parked"] = {"date": today, "reason": "waiting", "revival": None}
        raw.path.write_text(render(raw.fm, raw.body), encoding="utf-8")
        run(["reach", g, "--reason", "r"], ok=False)  # given up already
        run(["serves", qg, "-" + g])
        run(["serves", qg, "+" + g], ok=False)  # not open
        run(["serves", q4, "-" + g])
        g2 = new(["goal", "Reach C"])
        run(["serves", qg, "+" + g2])
        run(["set", g2, "summary", "Reach C, formalized", "--note", "the owner: \"a proof on paper is not enough\""])
        body = load_all(cfg)[g2].body
        expect("a goal's summary set leaves what it read in the body, dated, with the owner's words",
               f"{today} — summary set; it read: Reach C. the owner: \"a proof on paper is not enough\"" in body)
        run(["reach", g2, "--reason", f"C is proved, {fa}"])
        recs = load_all(cfg)
        expect("a goal reached carries its date and what shows it", recs[g2]["state"] == "reached" and recs[g2]["closed"]["reason"] == f"C is proved, {fa}")
        run(["serves", qg, "-" + g2])
        # a direction dropped by the owner; a question keeps what it served
        qd = new(["question", "Qd", "--consume", new(["idea", "an idea for the bridge"]), "--serves", d])
        p = run(["drop", d, "--reason", "the bridge is crossed"])
        recs = load_all(cfg)
        expect("a direction dropped clears nothing on its questions, and the notice names who refers to it, a closed one among them",
               recs[d]["state"] == "closed" and recs[qd]["serves"] == [d] and recs[q]["serves"] == [d] and {qd, q, g} <= set(noticed(p, d)))
        run(["question", "Qz", "--serves", d], ok=False)
        run(["serves", qd, "-" + d])
        d2 = new(["direction", "Second"])
        text = run(["directions"])["text"]
        expect("flow directions lists the open directions alone", d not in text and d2 in text)
        # the tag report and the artifacts index
        p = run(["tags"])
        expect("tags lists each tag with its records, then the untagged, a removed record in neither",
               p["tags"]["research"] == [t1, t2] and p["tags"]["refuted"] == [fr] and q in p["untagged"] and sub not in p["untagged"]
               and q not in run(["tags", "--type", "task"])["untagged"])
        (root / "linked.md").write_text("See [the paper](<./papers//alpha.md#Theorem 2.1>) and [the probe](probes/p.py), "
                                        "not <https://example.org/x> nor `papers/prose.md`.\n")
        li = new(["idea", "a linked idea", "--body", str(root / "linked.md")])
        p = run(["artifacts"])
        by = {x["path"]: x for x in p["artifacts"]}
        expect("artifacts lists every path the records refer to, with who names it and how, a `./` and a doubled slash folded; "
               "a URL, a backticked path and a declaration are not paths",
               by["papers/alpha.md"]["exists"] and {"id": li, "via": "body"} in by["papers/alpha.md"]["records"]
               and {"id": f, "via": "evidence"} in by["papers/alpha.md"]["records"] and by["probes/p.py"]["exists"] and "results/bench.md" in by
               and "Lib/Foo.lean" not in by and not any("example.org" in k or "prose" in k or k.startswith(".") for k in by))
        expect("find --refers PATH lists the records naming a path in a body link too, the path given in any spelling",
               li in ids(["find", "--refers", "papers/alpha.md"]) and li in ids(["find", "--refers", "./papers/alpha.md"]))
        p = run(["show", q])
        g_edges = run(["graph"])["graph"].splitlines()
        expect("show keys the links by field, and graph draws each link labelled by its field, consumed_by left out",
               p["links"]["references"] == [{"id": idea, "summary": "an idea"}] and p["links"]["answered_by"][0]["id"] == fa
               and p["links"]["serves"][0]["id"] == d and {x["id"] for x in p["backlinks"]["references"]} >= {t1, t2, sq}
               and f"{q} --answered_by--> {fa}" in g_edges and f"{t1} --references--> {q}" in g_edges and f"{q4} --blocked_by--> {q3}" in g_edges
               and not any("consumed_by" in e for e in g_edges))

        # a closing transition closes the ranks up and reports the moves as re-ranks (q3 holds rank 1, q4 rank 2)
        run(["rank", qg, "--clear"])
        q6 = new(["question", "Q to close"])
        run(["rank", q6, "3"])
        run(["rank", q3, "--clear"])
        expect("clearing a rank closes the ranks up", [load_all(cfg)[i]["rank"] for i in (q4, q6)] == [1, 2])
        run(["rank", q3, "3"])
        p = run(["remove", q6, "--reason", "closed to test the ranks"])
        expect("removing a ranked question renumbers the rest and reports them as re-ranked, not changed",
               p["changed"] == [q6] and p["reranked"] == [{"id": q3, "from": 3, "to": 2}]
               and load_all(cfg)[q3]["rank"] == 2 and not validate(cfg, load_all(cfg), today)[0])
        run(["rank", qw, "1"], ok=False)  # wrong is closed
        run(["rank", q5, "1"], ok=False)  # answered
        q7 = new(["question", "Q late"])
        p = run(["rank", q7, "1"], ok=False)  # rank 1 is held
        expect("a rank refused as held names --insert and --set", "--insert" in p["problems"][0]["msg"] and "rank --set" in p["problems"][0]["msg"])
        p = run(["rank", q7, "1", "--insert"])
        expect("rank --insert puts a new record at N in one step and moves the rest down, reporting them as re-ranked",
               [load_all(cfg)[i]["rank"] for i in (q7, q4, q3)] == [1, 2, 3] and {x["id"] for x in p["reranked"]} == {q4, q3})
        run(["rank", q3, "1", "--insert"])
        expect("rank --insert moves a ranked record up, the rest closing round it",
               [load_all(cfg)[i]["rank"] for i in (q3, q7, q4)] == [1, 2, 3] and not validate(cfg, load_all(cfg), today)[0])
        run(["rank", q7, "4", "--insert"], ok=False)  # past the end of the ranks
        # --set writes an order and asserts no read: no question's checked date moves; a rank given to one record refreshes it
        later = "2026-09-20"  # another day than the one the questions were checked on (a later one would be in the future)
        was = {i: load_all(cfg)[i]["checked"] for i in (q3, q7, q4)}
        rc, _ = dispatch(cfg, ["rank", "--set", q4, q3, q7], today=later, as_json=True, quiet=True)
        expect("rank --set orders the list and leaves every question's checked date as it was",
               rc == 0 and [load_all(cfg)[i]["rank"] for i in (q4, q3, q7)] == [1, 2, 3]
               and {i: load_all(cfg)[i]["checked"] for i in was} == was and later not in was.values())
        rc, _ = dispatch(cfg, ["rank", q3, "1", "--insert"], today=later, as_json=True, quiet=True)
        expect("rank ID N on a question still refreshes its checked date, the records it moved keeping theirs",
               rc == 0 and load_all(cfg)[q3]["checked"] == later and load_all(cfg)[q4]["checked"] == was[q4])
        txt = text_of(cfg, ["rank", "--set", q3, q7])
        p = run(["rank", "--set", q3, q7, q4])
        expect("rank --set says each record it placed as `ranked ID N`, one it cleared as `unranked ID (was N)`, never as plain changed",
               f"ranked {q3} 1" in txt and f"ranked {q7} 2" in txt and f"unranked {q4} (was 2)" in txt and "changed" not in txt
               and p["ranked"] == [{"id": q3, "rank": 1}, {"id": q7, "rank": 2}, {"id": q4, "rank": 3}] and p["unranked"] == []
               and set(p["changed"]) == {q3, q7, q4})
        run(["rank", q7, "--clear", "--insert"], ok=False)  # --insert takes a rank
        run(["rank", q7, "--clear"])
        run(["rank", idea, "1"], ok=False)  # an idea is never ranked
        run(["rank", idea, "--clear"], ok=False)
        run(["checked", qw], ok=False)  # a closed question: its read is history
        # a question closed, reopened, answered: none of it asks about the tasks naming it, and the notice names them
        q8 = new(["question", "Q with two tasks"])
        ta, tb = new(["task", "first", "--ref", q8]), new(["task", "second", "--ref", q8])
        p = run(["wrong", q8, "--reason", "badly put"])
        expect("a question with ready tasks naming it closes, and the notice names them",
               load_all(cfg)[q8]["state"] == "wrong" and noticed(p, q8) == [ta, tb] and p["notices"][0]["refers"][0] == {"id": ta, "state": "ready"})
        run(["reopen", q8, "--reason", "put better now"])
        recs = load_all(cfg)
        expect("reopen brings a wrong question back to open, its closing cleared, checked today, a note keeping what it was",
               recs[q8]["state"] == "open" and recs[q8]["closed"] is None and recs[q8]["checked"] == today
               and f"{today} — reopened: put better now; it was wrong ({today}: badly put)" in recs[q8].body)
        run(["reopen", q8, "--reason", "x"], ok=False)  # open already
        run(["reopen", ta, "--reason", "x"], ok=False)  # only a question is reopened
        run(["impossible", q8, "--by", fr])
        run(["reopen", q8, "--reason", "the proof has a gap"])
        expect("reopen of an impossible question names the finding that showed it", f"reopened: the proof has a gap; it was impossible by {fr}" in load_all(cfg)[q8].body)
        run(["tag", q8, "+do-not-reopen"])
        run(["remove", q8, "--reason", "set aside"])
        p = run(["reopen", q8, "--reason", "x"], ok=False)
        expect("reopen refuses a question tagged do-not-reopen, saying it is the person's mark and how it is lifted",
               "do-not-reopen" in p["problems"][0]["msg"] and "the person's mark" in p["problems"][0]["msg"]
               and f"`flow tag {q8} -do-not-reopen`" in p["problems"][0]["msg"])
        run(["tag", q8, "-do-not-reopen"])
        run(["reopen", q8, "--reason", "back on the table"])
        expect("a removed question reopens too", load_all(cfg)[q8]["state"] == "open"
               and f"reopened: back on the table; it was removed ({today}: set aside)" in load_all(cfg)[q8].body)
        run(["answer", q8, "--by", ta], ok=False)  # a task settles nothing
        txt = text_of(cfg, ["answer", q8, "--by", fa])
        expect("answer closes an open question answered by a finding, and says so",
               load_all(cfg)[q8]["state"] == "answered" and load_all(cfg)[q8]["answered_by"] == fa and f"{q8} closed answered by {fa}" in txt)
        run(["answer", q8, "--by", fa], ok=False)  # answered already
        # a finding found false: removed, its card kept, the notice naming what rests on it; the check says nothing afterwards
        ff = new(["finding", "a claim found false", "--evidence", "stated:papers/alpha.md#Theorem 2.1"])
        run(["reopen", q8, "--reason", "a second look"])
        run(["answer", q8, "--by", ff])
        f2 = new(["finding", "the corrected claim", "--evidence", "stated:papers/alpha.md#FV-1", "--ref", ff])
        p = run(["remove", ff, "--reason", "a counterexample"])
        recs = load_all(cfg)
        expect("a finding found false is removed, with its dated reason, and the notice names the question it answered and the finding that replaces it",
               recs[ff]["state"] == "removed" and recs[ff]["closed"] == {"date": today, "reason": "a counterexample"}
               and set(noticed(p, ff)) == {q8, f2} and p["records"][0]["forms"] == "removed")
        run(["remove", ff, "--reason", "again"], ok=False)
        run(["evidence", ff, "stated:papers/alpha.md#FV-1"], ok=False)  # its evidence is history
        run(["answer", qd, "--by", ff], ok=False)  # a removed finding settles nothing
        run(["finding", "x", "--evidence", "stated:papers/alpha.md#FV-1", "--ref", ff])  # a removed one is referenced still
        expect("a removed finding is found by its state and in no list of findings",
               ff in ids(["find", "--state", "removed"]) and ff not in ids(["find", "--type", "finding"]))
        run(["index"])
        idx = cfg.index.read_text(encoding="utf-8")
        p = run(["check"])
        expect("a removed finding is in no list and no count of the index, and the check says nothing of the question it answered",
               f"`{ff}`" not in idx and not p["problems"] and load_all(cfg)[q8]["answered_by"] == ff)
        run(["reopen", q8, "--reason", "its answer was removed"])
        run(["remove", ta, "--reason", "done with"])
        run(["remove", tb, "--reason", "done with"])
        run(["index"])
        p = run(["check"])
        expect("check green after the rank, reopen and removal round", not p["problems"])
        # the post-done instruction, printed at the close for the agent to follow; the resolution read from a pipe
        run(["draw", rt, "--owner", "root"])
        with contextlib.redirect_stdout(io.StringIO()):
            saved_in, sys.stdin = sys.stdin, io.StringIO("The chore is done.\n")
            try:
                p = run(["make", rt, "--resolution", "-"])
            finally:
                sys.stdin = saved_in
        expect("make prints the task's post-done instruction, its resolution read from the standard input",
               p["after"] == "mint the same chore for the next month" and "The chore is done." in load_all(cfg)[rt].body)
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
        plant("a finding's state that is not standing or removed", "V3", lambda R: raw_edit(R, f, lambda fm: fm.update(state="refuted")))
        plant("a state of the older model", "V3", lambda R: raw_edit(R, q3, lambda fm: fm.update(state="decomposed")))
        plant("a field of v0.7.0's model", "V3", lambda R: raw_edit(R, q3, lambda fm: fm.update(derived_from=fm.pop("references"))))
        plant("a field whose words are the body's now", "V3", lambda R: raw_edit(R, q3, lambda fm: fm.update(criterion="k")))
        plant("a task's kind, an older model's field", "V3", lambda R: raw_edit(R, wt, lambda fm: fm.update(kind="upkeep")))
        plant("a finding's status, an older model's field", "V3", lambda R: raw_edit(R, f, lambda fm: fm.update(status="verified")))
        plant("a record with no id", "V1", lambda R: raw_edit(R, q, lambda fm: fm.update(id=None)))
        plant("a record whose id names another prefix", "V1", lambda R: raw_edit(R, q, lambda fm: fm.update(id="task-9998")))
        plant("a record that does not read", "V0", lambda R: R[q].path.write_text("---\nid: 'unterminated\n---\n"))
        plant("a record that is not UTF-8", "V0", lambda R: R[q].path.write_bytes(b"---\nid: " + q.encode() + b"\nsummary: \xff\n---\n"))
        plant("a parking block that is not a map", "V15", lambda R: raw_edit(R, q4, lambda fm: fm.update(parked="later")))
        plant("a parking block with no reason", "V15", lambda R: raw_edit(R, q4, lambda fm: fm.update(parked={"date": today})))
        plant("a block that names nothing it waits on", "V15", lambda R: raw_edit(R, q4, lambda fm: fm.update(blocked_by={"date": today, "reason": "r"})))
        plant("a block naming what it waits on as one value, not a list", "V15", lambda R: raw_edit(R, q4, lambda fm: fm.update(blocked_by={"date": today, "on": q3, "reason": "r"})))
        plant("a done task parked", "V15", lambda R: raw_edit(R, t4, lambda fm: fm.update(parked={"date": today, "reason": "r"})))
        plant("a parking date that is not a date", "V20", lambda R: raw_edit(R, q4, lambda fm: fm.update(parked={"date": "soon", "reason": "r"})))
        plant("a due date that is not a date", "V20", lambda R: raw_edit(R, wt, lambda fm: fm.update(due="soon")))
        plant("a removed record with no reason", "V17", lambda R: raw_edit(R, t3, lambda fm: fm.update(closed={"date": today})))
        plant("a removed finding with no reason", "V17", lambda R: raw_edit(R, ff, lambda fm: fm.update(closed=None)))
        plant("a standing finding with a closing reason", "V17", lambda R: raw_edit(R, f, lambda fm: fm.update(closed={"date": today, "reason": "r"})))
        plant("a goal given up with no reason", "V17", lambda R: raw_edit(R, g, lambda fm: fm.update(closed=None)))
        plant("a closing dated in the future", "V20", lambda R: raw_edit(R, t3, lambda fm: fm.update(closed={"date": "2999-01-01", "reason": "r"})))
        plant("a closing reason on an open question", "V17", lambda R: raw_edit(R, q3, lambda fm: fm.update(closed={"date": today, "reason": "r"})))
        plant("a consumed idea naming a card that does not reference it", "V17", lambda R: raw_edit(R, i2, lambda fm: fm.update(consumed_by=[q5])))
        plant("a consumed idea naming its card as one id", "V17", lambda R: raw_edit(R, i2, lambda fm: fm.update(consumed_by=q3)))
        plant("a question answered by nothing", "V18", lambda R: raw_edit(R, q, lambda fm: fm.update(answered_by=None)))
        plant("a question answered by a task", "V18", lambda R: raw_edit(R, q, lambda fm: fm.update(answered_by=t1)))
        plant("a question answered by a list of findings", "V18", lambda R: raw_edit(R, q, lambda fm: fm.update(answered_by=[fa, f])))
        plant("an open question naming an answer", "V18", lambda R: raw_edit(R, q3, lambda fm: fm.update(answered_by=f)))
        plant("a task that names a question in an older model's field", "V3", lambda R: raw_edit(R, wt, lambda fm: fm.update(question=q3)))
        plant("a created date that is not a date", "V20", lambda R: raw_edit(R, q, lambda fm: fm.update(created="yesterday")))
        plant("a dangling reference", "V2", lambda R: raw_edit(R, t4, lambda fm: fm.update(references=["question-9999"])))
        plant("a question serving an idea", "V2", lambda R: raw_edit(R, q3, lambda fm: fm.update(serves=[i2])))
        plant("a question's serves as one value", "V2", lambda R: raw_edit(R, q3, lambda fm: fm.update(serves=g2)))
        plant("a question answered by a goal", "V2", lambda R: raw_edit(R, q, lambda fm: fm.update(answered_by=g)))
        plant("duplicate rank", "V14", lambda R: raw_edit(R, q8, lambda fm: fm.update(rank=1)))
        plant("rank on a closed question", "V14", lambda R: raw_edit(R, q5, lambda fm: fm.update(rank=4)))
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
        plant("closed task outside the archive", "V21", lambda R: shutil.move(str(R[t1].path), str(cfg.research / "tasks" / R[t1].path.name)))
        plant("a finding under a shard of the older model", "V21",
              lambda R: ((cfg.research / "findings" / "alpha").mkdir(), shutil.move(str(R[f].path), str(cfg.research / "findings" / "alpha" / R[f].path.name))))
        shutil.rmtree(cfg.research / "findings" / "alpha", ignore_errors=True)
        plant("finding without evidence", "V6", lambda R: raw_edit(R, f, lambda fm: fm.update(evidence=[])))
        plant("an evidence item with no form", "V6", lambda R: raw_edit(R, f, lambda fm: fm.update(evidence=["Lib/Foo.lean#lemma_L"])))
        plant("an evidence item of a form the project does not list", "V6", lambda R: raw_edit(R, f, lambda fm: fm.update(evidence=["folklore:Lib/Foo.lean#lemma_L"])))
        plant("an evidence item twice", "V6", lambda R: raw_edit(R, f, lambda fm: fm.update(evidence=["formal:Lib/Foo.lean#lemma_L"] * 2)))
        plant("finding whose declaration left the manifest", "V6", lambda R: (root / "decls.txt").write_text("module Lib.Foo 0\n"))
        (root / "decls.txt").write_text("module Lib.Foo 1\nLib.Foo lemma_L\n")
        recs = load_all(cfg)
        raw_edit(recs, ff, lambda fm: fm.update(evidence=["stated:papers/gone.md#x"]))
        expect("a removed finding's evidence is history: not resolved, never failed",
               not any(p["code"] == "V6" and p["id"] == ff for p in validate(cfg, load_all(cfg), today)[0]))
        raw_edit(load_all(cfg), ff, lambda fm: fm.update(evidence=["stated:papers/alpha.md#Theorem 2.1"]))
        plant("a body link to a path that is gone, on a live record", "V24",
              lambda R: R[li].path.write_text(render(R[li].fm, "See [gone](papers/gone.md).\n")))
        recs = load_all(cfg)
        recs[t1].path.write_text(render(recs[t1].fm, recs[t1].body + "\nSee [gone](papers/gone.md).\n"))
        recs[ff].path.write_text(render(recs[ff].fm, recs[ff].body + "\nSee [gone](papers/gone.md).\n"))
        problems, warnings, _ = validate(cfg, load_all(cfg), today)
        expect("a body link to a path that is gone, on an archived task or a removed finding, is warned of, never failed",
               not any(p["code"] == "V24" for p in problems) and any(f"{t1}: the body links papers/gone.md" in w for w in warnings)
               and any(f"{ff}: the body links papers/gone.md" in w for w in warnings))
        recs[t1].path.write_text(render(recs[t1].fm, recs[t1].body))
        recs[ff].path.write_text(render(recs[ff].fm, recs[ff].body))
        plant("a body link outside the tree, the file there, on a live record", "V24",
              lambda R: R[li].path.write_text(render(R[li].fm, f"See [it]({R[li].path}) and [up](../x.md).\n")))
        plant("a hand over its limit, a drawn idea counted", "V9", lambda R: (
            raw_edit(R, wt, lambda fm: fm.update(state="active", owner="root", drawn=today)),
            raw_edit(R, t3, lambda fm: fm.update(state="active", owner="root", drawn=today)),
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
        raw_edit(recs, q4, lambda fm: fm.update(blocked_by={"date": today, "on": [q5], "reason": "its answer"}))
        recs = load_all(cfg)
        run(["index"])
        idx = cfg.index.read_text(encoding="utf-8")
        expect("a block whose records have all settled warns of nothing; the index lists no wait for it, and draw and find read it so",
               not any(q4 in w for w in validate(cfg, recs, today)[1]) and not blocked_now(cfg, recs, recs[q4], today)
               and "waits: blocked" not in idx and q4 not in ids(["find", "--blocked"]))
        raw_edit(load_all(cfg), q4, lambda fm: fm.update(blocked_by={"date": today, "on": ["2026-09-01"], "reason": "its tag"}))
        raw_edit(load_all(cfg), wt, lambda fm: fm.update(due="2026-09-01"))
        _, warnings, _ = validate(cfg, load_all(cfg), today)
        expect("a due date that has passed is warned of, a block's date that has passed is not",
               any(f"{wt}: due 2026-09-01 has passed" in w for w in warnings) and not any(q4 in w for w in warnings))
        raw_edit(load_all(cfg), q4, lambda fm: fm.update(blocked_by={"date": today, "on": ["2026-09-01", q3], "reason": "both"}))
        recs = load_all(cfg)
        said = [l for l in passed_dates(cfg, recs, today) if q4 in l]
        expect("a block on a passed date and an open record holds: state's line names what it still waits on",
               recs[q3]["state"] == "open" and said == [f"{rel(cfg, cfg.index)}: the block's date has passed: {q4} waits on 2026-09-01 no longer; it still waits on {q3}"])
        raw_edit(load_all(cfg), q4, lambda fm: fm.update(blocked_by={"date": today, "on": ["2026-09-01", q5], "reason": "both"}))
        recs = load_all(cfg)
        said = [l for l in passed_dates(cfg, recs, today) if q4 in l]
        expect("once the rest of a block has settled, state's line names no wait left", len(said) == 1 and "still waits" not in said[0])
        raw_edit(load_all(cfg), q4, lambda fm: fm.update(blocked_by={"date": today, "on": [q3], "reason": "needs its answer"}))
        run(["index"])
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
                rc, _ = dispatch(c2, ["idea", "A long sentence", "--source", "t", "--body", str(r2 / "body.md")], today=today, as_json=True, quiet=True)
                expect("a body sentence longer than 80 characters is written under the built-in configuration", rc == 0)
                dispatch(c2, ["task", "An upkeep", "--tag", "upkeep", "--due", "2026-12-01"], today=today, as_json=True, quiet=True)
                dispatch(c2, ["goal", "A goal"], today=today, as_json=True, quiet=True)
                dispatch(c2, ["direction", "A direction"], today=today, as_json=True, quiet=True)
                (r2 / "body.md").write_text("A line.\n## A heading with no blank line above it\n", encoding="utf-8")
                rc, _ = dispatch(c2, ["idea", "A violation", "--source", "t", "--body", str(r2 / "body.md")], today=today, as_json=True, quiet=True)
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
        far = dispatch(cfg, ["task", "a chore due in December", "--due", "2026-12-01"], today=today, as_json=True, quiet=True)[1]["created"][0]
        cfg.due_within = 7
        lines, _ = state_lines(cfg, recs=load_all(cfg), today=today)
        expect("[index] due_within narrows state's due list to the window and the passed dates, and says how many more the index lists",
               any(wt in l and "due 2026-09-01" in l for l in lines) and not any(far in l for l in lines)
               and any("1 more due after 2026-10-02, beyond [index] due_within = 7 day(s)" in l for l in lines)
               and far in cfg.index.read_text(encoding="utf-8"))
        idx = cfg.index.read_text(encoding="utf-8")
        cfg.index.write_text(idx.replace("[due 2026-12-01]", "[due: 1 December]"), encoding="utf-8")
        lines, _ = state_lines(cfg, recs=load_all(cfg), today=today)
        cfg.index.write_text(idx, encoding="utf-8")
        cfg.due_within = None
        expect("the window is the records' due dates, the index's lines named by id, however a line writes its date",
               not any(far in l for l in lines) and any("1 more due after 2026-10-02" in l for l in lines))
        dispatch(cfg, ["remove", far, "--reason", "it stood here to test the window"], today=today, as_json=True, quiet=True)
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
            rc, payload = dispatch(cfg, ["idea", "the first idea"], today="2026-10-23", as_json=True, quiet=True)
            expect("init: the first idea lands", rc == 0 and payload["created"] == ["idea-0001"])
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
               and cfg.ev_decl.match("src/Foo.agda#bar") and not cfg.ev_decl.match("papers/a.md#x"))
        expect("formal evidence with no formal.toml at the root is unchecked, not failed, and the coverage says why",
               cfg.resolvers["formal"] == ([], "no formal.toml at the root")
               and resolve_evidence(cfg, "formal:src/Foo.agda#bar", {}).startswith("unchecked: no resolver for formal (no formal.toml at the root)"))
        (root / "flow.toml").write_text("[evidence]\nmanifest = \"decls.txt\"\nmanifest_roots = \"lean\"\n")
        old = Config(root)
        expect("a flow.toml with the manifest bindings of the models before is read, and nothing refuses on them", old.resolvers["formal"][0] == [])
        for ev, why in (('[evidence.resolvers]\nstated = ["x"]\n', "resolves"), ('[evidence.resolvers]\nBench = ["x"]\n', "one lowercase word"),
                        ('[evidence.resolvers]\nformal = [1]\n', "list of strings"), ('[evidence]\nresolvers = "x"\n', "is a table")):
            (root / "flow.toml").write_text(ev)
            try:
                Config(root)
                said = ""
            except Refused as e:
                said = str(e)
            expect(f"flow.toml's resolvers refused: {why}", why in said)
        (root / "flow.toml").write_text('[evidence]\nforms = ["formal", "benchmark"]\n[evidence.resolvers]\nformal = "frm"\nbenchmark = ["bench", "run"]\nother = []\n')
        c4 = Config(root)
        expect("a bound command is the whole command: a string is one word, [] turns a form's resolver off, and a bound form is the resolver's",
               c4.resolvers == {"formal": (["frm"], "flow.toml's [evidence.resolvers]"), "benchmark": (["bench", "run"], "flow.toml's [evidence.resolvers]"),
                                "other": ([], "disabled in flow.toml's [evidence.resolvers]")}
               and c4.resolved == ("formal", "benchmark") and c4.opaque_forms == ("peer-reviewed", "formal", "benchmark"))
        # the formal resolver found as the library is: formal.toml at the root, then the plugin beside the research one in one of
        # three places, then PATH
        with tempfile.TemporaryDirectory() as t5:
            base = Path(t5)
            proj = base / "proj"
            proj.mkdir()
            words = lambda here: find_resolver(proj, here)
            expect("with no formal.toml at the root no resolver is looked for", words(base / "x" / "a" / "b" / "c" / "flow.py") == ([], "no formal.toml at the root"))
            (proj / "formal.toml").write_text("", encoding="utf-8")
            land = lambda d: (d / "skills" / "land" / "scripts").mkdir(parents=True) or (d / "skills" / "land" / "scripts" / "formal.py").write_text("")
            flow_at = lambda d: d / "skills" / "flow" / "scripts" / "flow.py"
            land(base / "checkout" / "formal")
            cmd, route = words(flow_at(base / "checkout" / "research"))
            expect("a checkout: the formal plugin beside the research plugin, asked `resolve --protocol`",
                   cmd == [sys.executable, str(base / "checkout" / "formal" / "skills" / "land" / "scripts" / "formal.py"), "resolve", "--protocol"]
                   and route == "the formal plugin beside the research plugin")
            land(base / "cache" / "formal" / "0.8.0")
            land(base / "cache" / "formal" / "0.7.0")
            cmd, route = words(flow_at(base / "cache" / "research" / "0.8.0"))
            expect("Claude Code's cache: the formal plugin of the same version, and no other",
                   cmd[1:2] == [str(base / "cache" / "formal" / "0.8.0" / "skills" / "land" / "scripts" / "formal.py")]
                   and route == "the formal plugin beside the research plugin")
            expect("the cache holds another version of formal only: not that one",
                   words(flow_at(base / "cache" / "research" / "0.9.0"))[1] != "the formal plugin beside the research plugin")
            land(base / "flat")
            cmd, route = words(base / "flat" / "skills" / "flow" / "scripts" / "flow.py")
            expect("skills installed flat: the land skill beside the flow skill", cmd[1:2] == [str(base / "flat" / "skills" / "land" / "scripts" / "formal.py")]
                   and route == "the land skill beside the flow skill")
            cmd, route = words(flow_at(base / "alone" / "research"))
            cmd, route = words(Path("/a/flow.py"))
            expect("a script shallower than four directories raises nothing: the places beside it are skipped, then PATH or none",
                   (cmd, route) == (([shutil.which("formal"), "resolve", "--protocol"], "the formal command on PATH") if shutil.which("formal")
                                    else ([], "formal.toml at the root but no formal plugin beside the research plugin or command on PATH")))
            expect("with none beside it: `formal` on PATH where there is one, else none and why",
                   (cmd, route) == (([shutil.which("formal"), "resolve", "--protocol"], "the formal command on PATH") if shutil.which("formal")
                                    else ([], "formal.toml at the root but no formal plugin beside the research plugin or command on PATH")))
        # a form of the project's own bound to a resolver: its targets are the resolver's, read as no path
        with tempfile.TemporaryDirectory() as t6:
            r6 = Path(t6)
            (r6 / "bres.py").write_text('import json, sys\nreq = json.load(sys.stdin)\nprint(json.dumps({"protocol": 1, "items": {t: {"ok": True} if t == "run-1" '
                                        'else {"unchecked": "not run yet"} if t == "run-2" else {"ok": False, "why": "no such run"} for t in req["items"]}}))\n')
            (r6 / "flow.toml").write_text('[evidence]\nforms = ["benchmark", "reference"]\n[evidence.resolvers]\n'
                                          f'benchmark = [{json.dumps(sys.executable)}, "bres.py"]\n')
            (r6 / "results").mkdir()
            (r6 / "results" / "run-1").write_text("x\n")
            c6 = Config(r6)
            rc6 = lambda argv: dispatch(c6, argv, today="2026-09-25", as_json=True, quiet=True)
            expect("a bound form is held to form:target, the resolver's word taken: ok, unchecked, or refused with its why",
                   resolve_evidence(c6, "benchmark:run-1", {}) is None and resolve_evidence(c6, "benchmark:run-2", {}) == "unchecked: not run yet"
                   and resolve_evidence(c6, "benchmark:run-3", {}) == "no such run" and resolve_evidence(c6, "benchmark:../outside", {}) == "no such run")
            rc, pl = rc6(["finding", "ran", "--evidence", "benchmark:run-1", "benchmark:run-2", "reference:results/run-1"])
            rc_bad, _ = rc6(["finding", "ran", "--evidence", "benchmark:run-3"])
            expect("a mint takes the unchecked item and refuses the one the resolver refuses", rc == 0 and rc_bad == 1)
            rc, pl = rc6(["artifacts"])
            expect("the flow reads no path out of a bound form's target: only the reference is a path", [a["path"] for a in pl["artifacts"]] == ["results/run-1"])
            rc, pl = rc6(["find", "--refers", "run-1"])
            expect("find --refers names no record for a bound form's target taken as a path", rc == 0 and pl["records"] == [])
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
        (root / "research").mkdir(exist_ok=True)
        txt = text_of(cfg, ["check"])
        expect("check says in words that no resolver is found for formal, and no register and no library is bound",
               "resolver formal unchecked (no formal.toml at the root)" in txt and "probe evidence unchecked (no register bound)" in txt
               and "library: none bound" in txt and "NOT CONFIGURED" not in txt)
        r = subprocess.run([sys.executable, __file__, "--help"], capture_output=True, text=True, cwd=tempfile.gettempdir())
        expect("--help works with no bindings file", r.returncode == 0 and "reopen" in r.stdout and "init" in r.stdout)
        with tempfile.TemporaryDirectory() as bare:
            (Path(bare) / "a.md").write_text("# A\n\nOne. Two on a line.\n", encoding="utf-8")
            r = subprocess.run([sys.executable, __file__, "reflow", "--check", "a.md"], capture_output=True, text=True, cwd=bare)
            expect("reflow --check runs where no flow.toml stands, with the built-in reflow", r.returncode == 1 and "a.md:3" in r.stdout)
            r = subprocess.run([sys.executable, __file__, "done", "task-0001"], capture_output=True, text=True, cwd=bare)
            expect("a guessed verb is answered with its way, not the list of every command",
                   r.returncode == 2 and "no command 'done'" in r.stderr and "`make T --resolution FILE`" in r.stderr and "idea, question" not in r.stderr)
            words = {w: subprocess.run([sys.executable, __file__, w, "x"], capture_output=True, text=True, cwd=bare) for w in ("capture", "frame", "refine")}
            expect("a command that went is answered with the new way: capture, frame and refine",
                   all(r.returncode == 2 for r in words.values()) and "`idea SUMMARY`" in words["capture"].stderr
                   and "`question SUMMARY`" in words["frame"].stderr and "`task SUMMARY --ref Q`" in words["refine"].stderr)
            r = subprocess.run([sys.executable, __file__, "chekced"], capture_output=True, text=True, cwd=bare)
            expect("a misspelt verb is answered with the nearest names", r.returncode == 2 and "the nearest: checked" in r.stderr)

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
            expect("state --check lists the steps that are the session's own, the checklist the freeze's report answers",
                   p["session_steps"] == list(SESSION_STEPS) and len(SESSION_STEPS) == 4
                   and all(f"  [ ] {s}" in text_of(cfg, ["state", "--check"]) for s in SESSION_STEPS))
            idea = go(["idea", "an idea"])["records"][0]["path"]
            p = go(["state", "--check"], ok=False)
            expect("planted: a record changed since the top entry's commit that no entry names fails the freeze",
                   [x["path"] for x in p["problems"]] == [idea])
            p = go(["touched", "--unnamed"])
            expect("touched --unnamed lists the record the freeze would fail on, with what the log's entry names it by",
                   [x["path"] for x in p["touched"]] == [idea] and p["touched"][0]["id"] == "idea-0001" and not p["touched"][0]["named"]
                   and "the commit of the log's entry of" in p["base"])
            go(["touched", "--since", "no-such-rev"], ok=False)
            p = go(["state", "--check"], ok=False, day="2026-10-30")
            expect("planted: a top entry not dated today, the tree changed since its commit, fails the freeze",
                   any("not today (2026-10-30)" in x["msg"] for x in p["problems"]))
            entry.write_text("## 2026-10-27 — an idea\n\n**State.** The idea idea-0001 is captured.\n", encoding="utf-8")
            go(["log", "add", str(entry)])
            p = go(["state", "--check"])
            expect("an entry above the committed one naming the changed record passes the freeze", not p["problems"])
            expect("touched lists a record an entry names as named, and --unnamed leaves it out",
                   go(["touched"])["touched"][0]["named"] and go(["touched", "--unnamed"])["touched"] == []
                   and [x["id"] for x in go(["touched", "--since", "HEAD"])["touched"]] == ["idea-0001"])
            # --since REV: named by an entry from the top down to the newest the log held at REV, not only down to the newest committed one
            head0, log0 = (git(cfg, "rev-parse", "HEAD") or "").strip(), cfg.log.read_text(encoding="utf-8")
            for argv in (["add", "-A"], ["commit", "-q", "--no-verify", "-m", "the idea and the entry naming it"]):
                subprocess.run(gitc + argv, cwd=root, capture_output=True, text=True)
            entry.write_text("## 2026-10-27 — nothing new\n\n**State.** No record changed.\n", encoding="utf-8")
            go(["log", "add", str(entry)])
            for argv in (["add", "-A"], ["commit", "-q", "--no-verify", "-m", "an entry naming nothing"]):
                subprocess.run(gitc + argv, cwd=root, capture_output=True, text=True)
            t0 = go(["touched", "--since", head0])["touched"]
            expect("touched --since REV names a record by the entries since REV, an entry below the newest committed one among them",
                   [x["id"] for x in t0] == ["idea-0001"] and t0[0]["named"] and go(["touched", "--since", head0, "--unnamed"])["touched"] == []
                   and go(["touched", "--since", "HEAD"])["touched"] == [] and "the commit of the log's entry" not in go(["touched", "--since", head0])["base"])
            subprocess.run(gitc + ["reset", "-q", head0], cwd=root, capture_output=True, text=True)
            cfg.log.write_text(log0, encoding="utf-8")
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
            # a renumbering moves the records below the one inserted: a record whose only change is its rank is no change the log must name
            t1 = go(["task", "a ranked chore"])["created"][0]
            t2 = go(["task", "a second ranked chore"])["created"][0]
            go(["rank", t1, "1"])
            go(["rank", t2, "2"])
            entry.write_text("## 2026-10-27 — two ranked chores\n\n**State.** Two chores are ranked.\n", encoding="utf-8")
            go(["log", "add", str(entry)])
            for argv in (["add", "-A"], ["commit", "-q", "--no-verify", "-m", "two ranked chores"]):
                subprocess.run(gitc + argv, cwd=root, capture_output=True, text=True)
            t3 = go(["task", "a chore ranked first"])["created"][0]
            go(["rank", t3, "1", "--insert"])
            entry.write_text(f"## 2026-10-27 — a chore ranked first\n\n**State.** The chore {t3} is ranked first.\n", encoding="utf-8")
            go(["log", "add", str(entry)])
            p = go(["state", "--check"])
            expect("a record whose only change since the base is its rank passes the freeze with no entry naming it", not p["problems"])
            p = go(["touched"])
            expect("touched leaves the records only re-ranked out of its list and reports them apart",
                   [x["id"] for x in p["touched"]] == [t3] and p["reranked_only"] == sorted([t1, t2]))
            expect("touched says in its text which records were only re-ranked, and --ids lists the new task alone",
                   f"re-ranked only: {', '.join(sorted([t1, t2]))}" in text_of(cfg, ["touched"]) and text_of(cfg, ["touched", "--ids"]).split() == [t3])
            p2 = next(cfg.research.rglob(f"{t2}*.md"))
            p2.write_text(p2.read_text(encoding="utf-8").replace("a second ranked chore", "a second ranked chore, reworded"), encoding="utf-8")
            p = go(["state", "--check"], ok=False)
            expect("planted: a record whose summary changed with its rank is held by the freeze until an entry names it",
                   [x["path"] for x in p["problems"]] == [rel(cfg, p2)] and go(["touched"])["reranked_only"] == [t1])
            p2.write_text(p2.read_text(encoding="utf-8").replace(", reworded", ""), encoding="utf-8")
            # a record re-saved with only its quoting changed has the same rank: it is no record only moved, and stays an unnamed change
            moved2 = p2.read_text(encoding="utf-8")
            p2.write_text(moved2.replace(f"id: {t2}", f"id: '{t2}'").replace("rank: 3", "rank: 2"), encoding="utf-8")
            expect("planted: a record whose rank did not change is not labelled re-ranked only",
                   go(["touched"])["reranked_only"] == [t1] and t2 in [x["id"] for x in go(["touched"])["touched"]])
            p2.write_text(moved2, encoding="utf-8")
            # a question `rank --set` only moved is re-ranked only: an order asserts no read, so its checked date stands
            qx = go(["question", "a ranked question", "--consume", go(["idea", "an idea behind a ranked question"])["created"][0]],
                    day="2026-10-26")["created"][0]
            go(["rank", qx, "4"], day="2026-10-26")
            entry.write_text(f"## 2026-10-27 — a ranked question\n\n**State.** The question {qx} and the chore {t3} are ranked.\n", encoding="utf-8")
            go(["log", "add", str(entry)])
            for argv in (["add", "-A"], ["commit", "-q", "--no-verify", "-m", "a ranked question"]):
                subprocess.run(gitc + argv, cwd=root, capture_output=True, text=True)
            go(["rank", "--set", qx, t3, t1, t2])
            p = go(["touched"])
            expect("a question `rank --set` only moved keeps its checked date and reads as re-ranked only in touched",
                   load_all(cfg)[qx]["checked"] == "2026-10-26" and qx in p["reranked_only"] and qx not in [x["id"] for x in p["touched"]])
            # a range in the log's entry names every id of its prefix within it
            expect("an entry's range of ids (an ellipsis, an en dash or three dots, written with no spaces) names the ids within it and not outside",
                   all(names_id(f"The findings finding-0015{sep}0035 are in.", f"finding-{n:04d}") for sep in ("…", "–", "...")
                       for n in (15, 20, 35))
                   and not any(names_id(f"The findings finding-0015{sep}0035 are in.", i) for sep in ("…", "–", "...")
                               for i in ("finding-0014", "finding-0036", "task-0020", "finding-00200", "finding-020"))
                   and not any(names_id(f"The findings finding-0015{sep}0035 are in.", f"finding-{n:04d}") for sep in (" … ", " – ", " ... ")
                               for n in (20, 35))
                   and names_id("finding-0007 – 2024 runs", "finding-0007") and not names_id("finding-0007 – 2024 runs", "finding-0100")
                   and not names_id("finding-0035…0015", "finding-0020") and names_id("finding-0035…0015", "finding-0035")
                   and not names_id("finding-0015…0035x", "finding-0020"))
        elif os.environ.get("CI"):
            expect("git is on PATH in CI, where the freeze's log part is tested", False)
        else:
            print("  --  the freeze's log part not tested: no git on PATH")

        # the release the setup last brought the project to: init writes it; an older script refuses to write over a newer one
        with tempfile.TemporaryDirectory() as t3:
            r3 = Path(t3)
            do_init(r3, build_parser().parse_args(["init", "--log", "LOG.md"]))
            toml3 = (r3 / "flow.toml").read_text(encoding="utf-8")
            mine = script_version()
            expect("init writes [kit] release at this script's release, or a commented line where it is unknown",
                   (f'\nrelease = "{mine}"\n' in toml3) if mine else '\n# release = "vX.Y.Z"' in toml3)

            def at(release, version="v1.2.0"):
                (r3 / "flow.toml").write_text(re.sub(r"(?m)^#? ?release = .*$", release, toml3), encoding="utf-8")
                c = Config(r3)
                c.script_version = version
                return c

            def answer(c, argv):
                return dispatch(c, argv, today=today, as_json=True, quiet=True)
            c3 = at('release = "v1.3.0"')
            (r3 / "entry.md").write_text(f"## {today} — x\n\n**State.** X.\n", encoding="utf-8")
            refusals = {" ".join(argv): answer(c3, argv) for argv in (["idea", "an idea"], ["doctor", "--fix"], ["log", "add", str(r3 / "entry.md")], ["index"])}
            expect("a newer [kit] release refuses every write, naming both releases and the commands that move the plugin",
                   all(rc == 1 and "v1.3.0" in pl["problems"][0]["msg"] and "this flow script is v1.2.0" in pl["problems"][0]["msg"]
                       and "claude plugin update research@research-kit --scope project" in pl["problems"][0]["msg"]
                       and "prek autoupdate" in pl["problems"][0]["msg"] for rc, pl in refusals.values())
                   and not list((r3 / "records" / "ideas").glob("idea-*.md")))
            rc, pl = answer(c3, ["check"])
            expect("a newer [kit] release makes `flow check` report the mismatch as a problem, exit 1, with the same words", rc == 1 and "v1.3.0" in pl["problems"][0]["msg"])
            reads = [answer(c3, argv) for argv in (["state"], ["find", "--type", "idea"], ["index", "--check"], ["doctor"])]
            expect("a newer [kit] release lets the reads answer, each with the warning",
                   all(rc == 0 and "v1.3.0" in pl.get("kit_ahead", "") for rc, pl in reads))
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf), contextlib.redirect_stdout(io.StringIO()):
                dispatch(c3, ["state"], today=today)
            expect("the warning is printed first, on the standard error, so a read's output stays as it is", buf.getvalue().startswith("flow: warning — "))
            expect("a script of unknown release refuses nothing on the marker", answer(at('release = "v1.3.0"', None), ["idea", "an idea"])[0] == 0)
            c3 = at('release = "v1.1.0"')
            rc, pl = answer(c3, ["state"])
            expect("an older [kit] release has `flow state` say so first, and `flow check` say nothing",
                   rc == 0 and pl["lines"][0] == "the setup was last brought to v1.1.0; this is v1.2.0: run `/research:research-init`"
                   and answer(c3, ["check"])[0] == 0 and "v1.1.0" not in text_of(c3, ["check"]))
            expect("the same release asks nothing", answer(at('release = "v1.2.0"'), ["state"])[1]["kit_behind"] is None)
            c3 = at("")
            rc, pl = answer(c3, ["doctor"])
            expect("a flow.toml without [kit] release is a thing for the hand, never a mechanical edit",
                   rc == 1 and any("no [kit] release" in x["msg"] and 'add `[kit] release = "v1.2.0"`' in x["msg"] for x in pl["problems"])
                   and not pl["mechanical"])
            for bad in ('release = "0.7.0"', 'release = "latest"', "release = 7"):
                (r3 / "flow.toml").write_text(re.sub(r"(?m)^#? ?release = .*$", bad, toml3), encoding="utf-8")
                try:
                    Config(r3)
                    expect(f"planted: [kit] {bad} is refused when flow.toml is read", False)
                except Refused as e:
                    expect(f"planted: [kit] {bad} is refused when flow.toml is read", "no release tag" in str(e))
            if mine:
                (r3 / "flow.toml").write_text(re.sub(r"(?m)^release = .*$", 'release = "v99.0.0"', toml3), encoding="utf-8")
                try:
                    do_init(r3, build_parser().parse_args(["init", "--force"]))
                    expect("init --force over a newer [kit] release is refused", False)
                except Refused as e:
                    expect("init --force over a newer [kit] release is refused", "v99.0.0" in str(e) and "flow.toml" in (r3 / "flow.toml").read_text())
            (r3 / "flow.toml").write_text(re.sub(r"(?m)^#? ?release = .*$", 'release = "v0.0.1"', toml3), encoding="utf-8")
            do_init(r3, build_parser().parse_args(["init", "--force"]))
            expect("init --force keeps an older [kit] release: only the setup's verify step moves it",
                   '\nrelease = "v0.0.1"\n' in (r3 / "flow.toml").read_text(encoding="utf-8"))
            (r3 / "flow.toml").write_text(re.sub(r"(?m)^#? ?release = .*\n", "", toml3), encoding="utf-8")
            do_init(r3, build_parser().parse_args(["init", "--force"]))
            expect("init --force over a flow.toml with no [kit] release writes the line commented, for the setup to write",
                   '\n# release = "vX.Y.Z"' in (r3 / "flow.toml").read_text(encoding="utf-8"))
            (r3 / "flow.toml").write_text(toml3, encoding="utf-8")
            # the paragraphs init prints, for the bindings as they stand, with nothing written
            (r3 / "flow.toml").write_text(toml3.replace('records = "records"', 'records = "notes/records"'), encoding="utf-8")
            snap = lambda d: {q: q.read_bytes() for q in sorted(Path(d).rglob("*")) if q.is_file()}
            before = snap(r3)
            r = subprocess.run([sys.executable, __file__, "init", "--print-instructions"], cwd=r3 / "records", capture_output=True, text=True)
            expect("init --print-instructions prints the paragraphs for the bindings as they stand, found from a subdirectory, and writes nothing",
                   r.returncode == 0 and "The records are `notes/records/`" in r.stdout and "The log is `LOG.md`" in r.stdout and snap(r3) == before)
            with tempfile.TemporaryDirectory() as t4:
                r = subprocess.run([sys.executable, __file__, "init", "--print-instructions"], cwd=t4, capture_output=True, text=True)
                expect("init --print-instructions with no flow.toml prints the defaults and writes nothing",
                       r.returncode == 0 and "The records are `records/`" in r.stdout and "The log is not bound yet" in r.stdout and not any(Path(t4).iterdir()))
            expect("the paragraphs say the person's bare words mean the session skills, called every time, and a request ending in a freeze is two",
                   "they mean these skills" in INSTRUCTIONS and "is two requests" in INSTRUCTIONS)
            # a flow.toml of the v0.5.0 shape: the keys a later init writes are noted, never failed
            older = re.sub(r"(?m)^(log_archive|# statement_words|# row_id) = .*\n", "", toml3)
            # a prose comment that reads like `key = words` is no commented key, so the key it resembles is still noted
            older = older.replace("[evidence]\n", "[evidence]\n# row_id = whatever the project likes, in words\n", 1)
            (r3 / "flow.toml").write_text(older, encoding="utf-8")
            c3 = Config(r3)
            rc, pl = answer(c3, ["doctor"])
            noted = {n["key"]: n for n in pl["notes"]}
            expect("the doctor notes each key the current init writes that a flow.toml written earlier lacks, with its default and its reader, failing nothing",
                   rc == 0 and set(noted) == {"[paths] log_archive", "[evidence] statement_words", "[evidence] row_id"}
                   and noted["[paths] log_archive"]["default"].startswith('"LOG-archive"') and "flow log archive" in noted["[paths] log_archive"]["reads"]
                   and not pl["problems"])
            expect("the doctor's text counts the notes", "3 optional key(s) the current init writes, noted" in text_of(c3, ["doctor"]))
            (r3 / "flow.toml").write_text(toml3, encoding="utf-8")
            expect("a key the project keeps commented, as init writes it, is no note", not answer(Config(r3), ["doctor"])[1]["notes"])
            expect("init writes no manifest binding, and the resolvers commented",
                   not re.search(r"manifest", toml3) and "# [evidence.resolvers]\n# formal = " in toml3)
            # a flow.toml of the models before the resolver: the three manifest bindings are read, refused by nothing, and named for the hand
            (r3 / "flow.toml").write_text(toml3.replace("[evidence]\n", '[evidence]\nmanifest = ["decls.txt"]\nmanifest_roots = ["lean"]\nmanifest_extension = "lean"\n', 1), encoding="utf-8")
            rc, pl = answer(Config(r3), ["doctor"])
            named = [x for x in pl["problems"] if x["path"] == "flow.toml" and "[evidence] manifest" in x["msg"]]
            expect("the doctor names the three manifest bindings for the hand, each as one line to delete, and --fix writes none of them",
                   len(named) == 3 and all("goes:" in x["msg"] and "delete the line" in x["msg"] for x in named)
                   and not any("manifest" in x["msg"] for x in pl["mechanical"]))
            (r3 / "flow.toml").write_text(toml3, encoding="utf-8")

        # the doctor: the words of the model before 0.3, named with what each reads now
        with tempfile.TemporaryDirectory() as t2:
            r2 = Path(t2)
            do_init(r2, build_parser().parse_args(["init", "--log", "LOG.md"]))
            c2 = Config(r2)
            rc, pl = dispatch(c2, ["doctor"], today=today, as_json=True, quiet=True)
            expect("the doctor finds nothing in a tree init wrote", rc == 0 and not pl["problems"])
            (r2 / "res.md").write_text("Done.\n", encoding="utf-8")
            res2 = str(r2 / "res.md")
            for argv in (["idea", "i"], ["question", "Q", "--consume", "idea-0001"],
                         ["task", "t", "--ref", "question-0001"], ["draw", "task-0001", "--owner", "agent"], ["make", "task-0001", "--resolution", res2],
                         ["task", "a chore", "--tag", "upkeep"], ["task", "a chore given up", "--tag", "upkeep"],
                         ["finding", "F", "--evidence", "reference:https://example.org/f", "--ref", "task-0001"]):
                dispatch(c2, argv, today=today, as_json=True, quiet=True)
            recs = load_all(c2)

            def old(id_, fn):
                fm = dict(recs[id_].fm)
                fn(fm)
                recs[id_].path.write_text(render(fm, recs[id_].body))
            old("question-0001", lambda fm: (fm.update(state="decomposed", kill="k", answered_by=[], direction="Bridge"), fm.pop("blocked_by")))
            old("task-0001", lambda fm: fm.update(abandoned={"date": today, "reason": "a wall"}, state="abandoned", drawn=today, owner="prover") or fm.pop("closed"))
            old("task-0002", lambda fm: fm.update(abandoned=None, drawn=today, question="question-0001", kind="work") or fm.pop("closed"))
            old("task-0003", lambda fm: fm.update(abandoned={"date": today, "reason": "given up while ready"}, state="abandoned") or fm.pop("closed"))
            # a record of the first model, with no tags and no references, a kind to carry over and a listed owner on a done task;
            # a consumed idea still in a hand; a question answered by a list of one finding, and an open one naming one
            for argv in (["idea", "j"], ["task", "an old chore"], ["question", "Q2", "--consume", "idea-0002"],
                         ["draw", "task-0004", "--owner", "agent"], ["make", "task-0004", "--resolution", res2],
                         ["finding", "G", "--evidence", "reference:https://example.org/g", "--ref", "task-0004", "--answers", "question-0002"],
                         ["idea", "k"], ["question", "Q3", "--consume", "idea-0003"]):
                dispatch(c2, argv, today=today, as_json=True, quiet=True)
            recs = load_all(c2)
            old("task-0004", lambda fm: (fm.update(kind="survey", owner="agent"), fm.pop("tags"), fm.pop("references"), fm.pop("after")))
            old("idea-0002", lambda fm: fm.update(owner="agent", drawn=today))
            old("question-0002", lambda fm: fm.update(answered_by=[fm["answered_by"]]))
            old("question-0003", lambda fm: (fm.update(answered_by=["finding-0002"], blocked={"date": today, "on": "the release", "reason": "r"}), fm.pop("blocked_by")))
            old("idea-0001", lambda fm: fm.update(consumed_by="question-0001"))
            old("finding-0001", lambda fm: fm.update(status="refuted", paper="alpha",
                                                     evidence=["papers/alpha.md#Theorem 2.1", "probes/p.py", "Lib/Foo.lean#lemma_L",
                                                               "reference:papers/alpha.md#Section 2"]))  # an anchor held to the file's existence before v0.5.0
            (r2 / "papers").mkdir()
            (r2 / "papers" / "alpha.md").write_text("# Alpha\n\n**Theorem 2.1.** It holds.\n\n## Section 2\n", encoding="utf-8")
            toml0 = (r2 / "flow.toml").read_text(encoding="utf-8")
            (r2 / "flow.toml").write_text(toml0 + '\n[task]\ndefault_kind = "work"\ndecision_owners = ["owner"]\n[finding]\nstated = "proven"\n', encoding="utf-8")
            (r2 / "records" / "directions.md").write_text("# Directions\n\n## Inbox\n\n- an item\n\n## Directions\n\n- **Bridge** (2026-01-01) — the words.\n", encoding="utf-8")
            c2 = Config(r2)
            rc, pl = dispatch(c2, ["doctor"], today=today, as_json=True, quiet=True)
            said = [x["path"] + ": " + x["msg"] for x in pl["problems"]] + [x["path"] + ": " + x["was"] + " — " + x["now"] for x in pl["mechanical"]]
            want = ("decision_owners", "[task] default_kind — goes: a task's kind is a tag now", "[finding] — goes", "an `## Inbox` section",
                    "the directions file — directions are records now", '- **Bridge** — `flow direction "Bridge" --body FILE`',
                    "direction: Bridge — the id of the direction record",
                    "state: decomposed — state: open", "kill: k — goes: delete the field, its words appended to the body", "no blocked_by — blocked_by: null",
                    "state: abandoned — state: aborted", "abandoned — closed", f"drawn: {today} on a ready task",
                    "owner: prover on a task that is aborted — owner: null", "owner: agent on a task that is done — owner: null",
                    "kind: survey — goes: a kind is a tag now", "no tags — tags: []", "no references — references: []",
                    "on an idea that is consumed — owner: null and drawn: null", "answered_by as a list — answered_by: finding-0002",
                    "question: question-0001 — goes", "name question-0001 in references",
                    "kind: work — goes: a kind is a tag now", "status: refuted — goes: the forms of the evidence stand for it; delete the field, and add the tag `refuted`",
                    "paper: alpha — goes", "evidence papers/alpha.md#Theorem 2.1 — stated:papers/alpha.md#Theorem 2.1",
                    "evidence probes/p.py — statistical:probes/p.py", "evidence Lib/Foo.lean#lemma_L — formal:Lib/Foo.lean#lemma_L",
                    "evidence reference:papers/alpha.md#Section 2 — #Section 2 is no row", "the nearest heading's anchor is #section-2: a document's anchor under reference is checked",
                    "consumed_by: question-0001 — consumed_by as a list", "answered_by as a list — answered_by: null", "blocked — blocked_by: rename the field")
            expect("the doctor names each old word and field with what it reads now, and exits 1",
                   rc == 1 and all(any(w in x for x in said) for w in want))
            if rc != 1 or not all(any(w in x for x in said) for w in want):
                print("      ", "\n       ".join(said))
            ok = (pl["summary"].get("field") == 4 and pl["summary"].get("evidence") == 3 and pl["summary"].get("kind") == 2 and pl["summary"].get("archive") == 1
                  and pl["summary"].get("closed-owner") == 3 and pl["summary"].get("answered-by") == 2
                  and any("answered_by: finding-0002 on a question that is open" in x["msg"] for x in pl["problems"])
                  and not any("kill" in x["msg"] or "no blocked" in x["msg"] for x in pl["problems"]) and any("decision_owners" in x["msg"] for x in pl["problems"]))
            expect("the doctor summarizes the mechanical classes with a count each and keeps the judgment lines apart", ok)
            if not ok:
                print("      ", pl["summary"], "\n       ", "\n        ".join(x["msg"] for x in pl["problems"]))
            # the fix: the mechanical classes written in place, the judgment ones left to the hand, then a green check;
            # the hand's part first: the anchor of the old shape rewritten to the heading's
            recs = load_all(c2)
            old("finding-0001", lambda fm: fm["evidence"].__setitem__(3, "reference:papers/alpha.md#section-2"))
            (r2 / "probes").mkdir()
            (r2 / "probes" / "p.py").write_text("print('ok')\n", encoding="utf-8")
            rc, pl = dispatch(c2, ["doctor", "--fix"], today=today, as_json=True, quiet=True)
            fixed, left = pl["fixed"], [x["msg"] for x in pl["problems"]]
            expect("doctor --fix writes the mechanical classes, counts them by class, and leaves the judgment ones",
                   rc == 1 and fixed.get("body") == 1 and fixed.get("abandoned") == 3 and fixed.get("state-abandoned") == 2 and fixed.get("state-decomposed") == 1
                   and fixed.get("kind") == 2 and fixed.get("question") == 1 and fixed.get("status") == 1 and fixed.get("paper") == 1 and fixed.get("evidence") == 3
                   and fixed.get("answered-by") == 2 and fixed.get("consumed-by") == 1 and fixed.get("blocked-on") == 1 and fixed.get("blocked") == 1
                   and fixed.get("ready-hand") == 1 and fixed.get("closed-owner") == 3 and fixed.get("archive") == 1 and fixed.get("field") == 4
                   and any("decision_owners" in m for m in left) and any("- **Bridge**" in m for m in left) and any("direction: Bridge" in m for m in left)
                   and not any("kill" in m or "paper:" in m or "no blocked" in m for m in left))
            if rc != 1 or not left or fixed.get("archive") != 1:
                print("      ", fixed, "\n       ", "\n        ".join(left))
            recs = load_all(c2)
            expect("after the fix: the words renamed, the states read, the tag, the prefixes, the moves, the fields added",
                   recs["question-0001"]["state"] == "open" and f"{today} — criterion (moved from the field): k" in recs["question-0001"].body
                   and "kill" not in recs["question-0001"].fm
                   and recs["question-0001"]["answered_by"] is None and recs["question-0001"]["blocked_by"] is None and recs["question-0001"]["serves"] == []
                   and recs["task-0001"]["state"] == "aborted" and recs["task-0001"]["closed"] == {"date": today, "reason": "a wall"}
                   and recs["task-0001"]["owner"] is None and recs["task-0001"]["drawn"] == today and recs["task-0001"].path.parent.resolve() == c2.archive.resolve()
                   and recs["task-0002"]["tags"] == ["upkeep", "work"] and recs["task-0002"]["references"] == ["question-0001"] and "question" not in recs["task-0002"].fm
                   and recs["task-0002"]["drawn"] is None and recs["task-0002"]["closed"] is None and recs["task-0002"]["due"] is None
                   and recs["idea-0001"]["consumed_by"] == ["question-0001"]
                   and recs["task-0003"]["state"] == "removed" and recs["task-0003"].path.parent.resolve() == c2.archive.resolve()
                   and recs["task-0004"]["tags"] == ["survey"] and recs["task-0004"]["references"] == [] and recs["task-0004"]["after"] is None
                   and recs["task-0004"]["owner"] is None and recs["task-0004"]["drawn"] == today
                   and recs["idea-0002"]["owner"] is None and recs["idea-0002"]["drawn"] is None
                   and recs["question-0002"]["answered_by"] == "finding-0002" and recs["question-0003"]["answered_by"] == ["finding-0002"]
                   and recs["question-0003"]["blocked_by"]["on"] == ["the release"]
                   and recs["finding-0001"]["evidence"] == ["stated:papers/alpha.md#Theorem 2.1", "statistical:probes/p.py", "formal:Lib/Foo.lean#lemma_L",
                                                            "reference:papers/alpha.md#section-2"]
                   and recs["finding-0001"]["tags"] == ["refuted"] and not {"status", "paper"} & set(recs["finding-0001"].fm)
                   and list(recs["finding-0001"].fm) == list(SCHEMA["finding"]))
            # the hand's part: the bindings and the file, the open question's answer cleared, and the direction minted; two of that name
            # leave the choice to the hand, one lets a second --fix name its id in serves
            (r2 / "flow.toml").write_text(toml0, encoding="utf-8")
            (r2 / "records" / "directions.md").unlink()
            c2 = Config(r2)
            recs = load_all(c2)
            old("question-0003", lambda fm: fm.update(answered_by=None))
            dispatch(c2, ["direction", "Bridge"], today=today, as_json=True, quiet=True)
            dispatch(c2, ["direction", "Bridge"], today=today, as_json=True, quiet=True)
            stamp = c2.index.stat().st_mtime_ns
            rc, pl = dispatch(c2, ["doctor", "--fix"], today=today, as_json=True, quiet=True)
            expect("two open directions of the bullet's name leave the question's direction to the hand, and a fix that wrote nothing leaves the index alone",
                   rc == 1 and not pl["fixed"] and any("yours to pick" in x["msg"] for x in pl["problems"]) and c2.index.stat().st_mtime_ns == stamp)
            dispatch(c2, ["drop", "direction-0002", "--reason", "minted twice"], today=today, as_json=True, quiet=True)
            rc, pl = dispatch(c2, ["doctor", "--fix"], today=today, as_json=True, quiet=True)
            expect("a second --fix, one direction record of the name left open, names its id in serves and exits 0",
                   rc == 0 and pl["fixed"] == {"direction": 1} and not pl["problems"] and load_all(c2)["question-0001"]["serves"] == ["direction-0001"]
                   and "direction" not in load_all(c2)["question-0001"].fm)
            rc, pl = dispatch(c2, ["check"], today=today, as_json=True, quiet=True)
            expect("the migrated tree checks green", rc == 0 and not pl["problems"])
            for x in pl["problems"]:
                print("      ", x["code"], x["path"], x["msg"])
            rc, pl = dispatch(c2, ["doctor"], today=today, as_json=True, quiet=True)
            expect("the doctor finds nothing left", rc == 0 and not pl["problems"] and not pl["mechanical"])

        # a tree as the v0.7.0 script wrote it, every field this release removes in use: `flow doctor --fix` brings it to
        # this model, and the fixed tree passes `flow check`
        with tempfile.TemporaryDirectory() as t2:
            r2 = Path(t2)
            do_init(r2, build_parser().parse_args(["init", "--log", "LOG.md"]))
            c2 = Config(r2)
            day = "2026-10-01"
            base = lambda id_, type_, state, summary, **kv: {"id": id_, "type": type_, **({"state": state} if state else {}), "summary": summary, **kv}
            tail = {"origin": "current", "source": None, "created": day, "tags": []}
            v07 = {
                "directions/direction-0001-bridge.md": base("direction-0001", "direction", "open", "Bridge", derived_from=[], closed=None, **tail),
                "goals/goal-0001-reach-b.md": base("goal-0001", "goal", "open", "Reach B", criterion="B is proved. On paper first.",
                                                   horizon="this year", derived_from=["direction-0001"], closed=None, **tail),
                "ideas/idea-0001-an-idea.md": {"id": "idea-0001", "type": "idea", "state": "consumed", "summary": "an idea", "source": "a talk",
                                               "derived_from": [], "owner": None, "drawn": None, "consumed_by": ["question-0001"], "closed": None,
                                               "origin": "current", "created": day, "tags": []},
                "questions/question-0001-does-a-imply-b.md": {
                    "id": "question-0001", "type": "question", "kind": "conjecture", "state": "open", "summary": "Does A imply B?",
                    "derived_from": ["idea-0001"], "parent": None, "size": "medium",
                    "criterion": "A finite counterexample answers it. A proof settles it too.", "checked": day, "parked": None,
                    "blocked": {"date": day, "on": ["task-0001", "the release of 2026-12-01"], "reason": "needs the lemma"},
                    "rank": 1, "why_now": "the talk is soon", "first_move": "read the lemma", "direction": "direction-0001", "serves": "goal-0001",
                    "answered_by": None, "closed": None, **tail},
                "questions/question-0002-a-sub-question.md": {
                    "id": "question-0002", "type": "question", "kind": "question", "state": "answered", "summary": "a sub-question",
                    "derived_from": ["question-0001"], "parent": "question-0001", "size": None, "criterion": "k", "checked": day, "parked": None,
                    "blocked": None, "rank": None, "why_now": None, "first_move": None, "direction": None, "serves": None,
                    "answered_by": "finding-0002", "closed": None, **tail},
                "tasks/task-0001-prove-the-lemma.md": {
                    "id": "task-0001", "type": "task", "state": "ready", "summary": "prove the lemma", "derived_from": ["question-0001"],
                    "requires": ["finding-0001"], "size": "small", "owner": None, "drawn": None, "dod": "the lemma is proved", "due": None,
                    "after": "mint the next", "rank": 2, "why_now": "w", "first_move": "m", "rider": True, "parked": None, "blocked": None,
                    "closed": None, **{**tail, "tags": ["research"]}},
                "archive/task-0002-read-the-paper.md": {
                    "id": "task-0002", "type": "task", "state": "done", "summary": "read the paper", "derived_from": ["question-0001"],
                    "requires": [], "size": None, "owner": None, "drawn": day, "dod": None, "due": None, "after": None, "rank": None,
                    "why_now": None, "first_move": None, "rider": False, "parked": None, "blocked": None, "closed": None, **tail},
                "findings/finding-0001-the-paper-s-lemma.md": base("finding-0001", "finding", None, "the paper's lemma",
                                                                   evidence=["reference:https://example.org/a"], derived_from=["task-0002"], depends_on=[], **tail),
                "findings/finding-0002-it-follows.md": base("finding-0002", "finding", None, "it follows", evidence=["reference:https://example.org/b"],
                                                            derived_from=["question-0002"], depends_on=["finding-0001"], **tail),
            }
            for rel_path, fm in v07.items():
                (c2.research / rel_path).parent.mkdir(parents=True, exist_ok=True)
                (c2.research / rel_path).write_text(render(fm, "Its body.\n"), encoding="utf-8")
            rc, pl = dispatch(c2, ["check"], today=today, as_json=True, quiet=True)
            expect("a v0.7.0 tree fails V3 on each field this release removes, with what it reads now and `flow doctor`",
                   rc == 1 and any(x["code"] == "V3" and "unknown field derived_from, of an older model: it reads `references` now" in x["msg"] for x in pl["problems"])
                   and any(x["code"] == "V3" and "unknown field why_now" in x["msg"] and "words in the body" in x["msg"] for x in pl["problems"]))
            rc, pl = dispatch(c2, ["doctor"], today=today, as_json=True, quiet=True)
            said = [x["was"] + " — " + x["now"] for x in pl["mechanical"]]
            expect("the doctor says a block's words holding a date are words, a date being an item written alone",
                   len(pl["remarks"]) == 1 and pl["remarks"][0]["path"].endswith("question-0001-does-a-imply-b.md")
                   and "the release of 2026-12-01 is words" in pl["remarks"][0]["text"] and "written alone" in pl["remarks"][0]["text"]
                   and not any("written alone" in x for x in said) and not pl["problems"])
            plain = text_of(c2, ["doctor"])
            expect("plain `flow doctor`, without --all, prints a line with the record's path and the remark, which is no thing for the hand",
                   "question-0001-does-a-imply-b.md: the release of 2026-12-01 is words" in plain and "written alone" in plain
                   and "flow doctor: 0 thing(s) for the hand and" in plain)
            expect("`flow doctor --all` prints the remark once", text_of(c2, ["doctor", "--all"]).count("written alone") == 1)
            with tempfile.TemporaryDirectory() as t2b:  # a copy, fixed with the text a person reads; the tree itself is fixed below with the JSON
                shutil.copytree(r2, Path(t2b) / "p", dirs_exist_ok=True)
                fixed_text = text_of(Config(Path(t2b) / "p"), ["doctor", "--fix"])
            expect("`flow doctor --fix` prints the remark too, naming the record it fixed",
                   "question-0001-does-a-imply-b.md: the release of 2026-12-01 is words" in fixed_text and "written alone" in fixed_text
                   and "flow doctor: 0 thing(s) for the hand" in fixed_text)
            rc, pl = dispatch(c2, ["doctor", "--fix"], today=today, as_json=True, quiet=True)
            expect("`flow doctor --fix --json` carries the remark", len(pl["remarks"]) == 1 and "written alone" in pl["remarks"][0]["text"])
            recs = load_all(c2)
            q1, t1_, g1 = recs["question-0001"], recs["task-0001"], recs["goal-0001"]
            expect("doctor --fix moves every v0.7.0 field: the links to references and serves, the block renamed, the words to the body "
                   "as dated lines, reflowed, the kinds and the rider to tags, a finding standing",
                   rc == 0 and q1["references"] == ["idea-0001"] and q1["serves"] == ["goal-0001", "direction-0001"]
                   and q1["blocked_by"] == {"date": day, "on": ["task-0001", "the release of 2026-12-01"], "reason": "needs the lemma"}
                   and q1["tags"] == ["conjecture"] and list(q1.fm) == list(SCHEMA["question"])
                   and f"{today} — criterion (moved from the field): A finite counterexample answers it.\nA proof settles it too.\n" in q1.body
                   and f"{today} — why_now (moved from the field): the talk is soon" in q1.body
                   and q1.body.index("criterion (moved") < q1.body.index("why_now (moved") < q1.body.index("first_move (moved")
                   and recs["question-0002"]["references"] == ["question-0001"] and recs["question-0002"]["serves"] == []
                   and t1_["references"] == ["question-0001", "finding-0001"] and t1_["tags"] == ["research", "rider"]
                   and f"{today} — dod (moved from the field): the lemma is proved" in t1_.body and t1_["after"] == "mint the next"
                   and recs["task-0002"]["tags"] == [] and recs["task-0002"]["references"] == ["question-0001"]
                   and recs["finding-0002"]["references"] == ["question-0002", "finding-0001"]
                   and recs["finding-0002"]["state"] == "standing" and recs["finding-0002"]["closed"] is None
                   and g1["references"] == ["direction-0001"] and f"{today} — criterion (moved from the field): B is proved.\nOn paper first." in g1.body
                   and f"{today} — horizon (moved from the field): this year" in g1.body and not set(MOVED_FIELDS) & {k for r in recs.values() for k in r.fm})
            rc, pl = dispatch(c2, ["check"], today=today, as_json=True, quiet=True)
            expect("the v0.7.0 tree passes `flow check` after `flow doctor --fix`", rc == 0 and not pl["problems"])
            for x in pl["problems"]:
                print("      ", x["code"], x["path"], x["msg"])
            rc, pl = dispatch(c2, ["doctor"], today=today, as_json=True, quiet=True)
            expect("and the doctor finds nothing left in it, and no remark: words holding a date are legitimate words once fixed",
                   rc == 0 and not pl["problems"] and not pl["mechanical"] and pl["remarks"] == [])

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
        expect("the built-in reflow leaves the scholarly abbreviations unsplit: Prop., Thm., Cf., i.e., e.g.",
               _builtin_reflow("By Prop. 3.4 and Thm. 2 it holds.") == "By Prop. 3.4 and Thm. 2 it holds."
               and _builtin_reflow("Cf. Smith (1990), i.e. the lemma, e.g. here.") == "Cf. Smith (1990), i.e. the lemma, e.g. here."
               and _builtin_reflow("See Smith et al. 1990 for it.") == "See Smith et al. 1990 for it.")
        expect("the built-in reflow still splits after a journal's abbreviations, which a project's bound module lists (the escape for others)",
               _builtin_reflow("See Amer. J. Math. 60 for it.").startswith("See Amer.\n"))
        expect("the built-in reflow splits after a single capital, Theorem A. and the matrix A., and after Fig. 2. only at the 2",
               _builtin_reflow("Theorem A. Then it holds.") == "Theorem A.\nThen it holds."
               and _builtin_reflow("Take the matrix A. The rest follows.") == "Take the matrix A.\nThe rest follows."
               and _builtin_reflow("See Fig. 2. Then it holds.") == "See Fig. 2.\nThen it holds.")
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
        tr = go(["task", "a task to append to"])["created"][0]
        p = go(["reflow", "--as", tr, str(draft)])
        expect("reflow --as takes a record's id for DEST", p["coverage"].endswith(f"markdownlint as at {load_all(cfg)[tr].path}, the draft appended to it"))
        p = go(["reflow", "--as", str(cfg.research / "tasks" / f"{tr}-a-guess.md"), str(draft)], ok=False)
        expect("reflow --as refuses a missing DEST named for a record that is elsewhere, naming its path",
               f"{tr} is {rel(cfg, load_all(cfg)[tr].path)}" in p["problems"][0]["msg"])
        p = go(["reflow", "--as", str(cfg.research / "tasks" / "task-0099-not-yet.md"), str(draft)])
        expect("reflow --as on a record not minted yet lints the draft as a body under front matter, no MD041",
               not p["problems"] and not (cfg.research / "tasks" / "task-0099-not-yet.md").exists())
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

    def mint(kind, help_):
        p = sp.add_parser(kind, help=help_)
        p.add_argument("summary", help="the one line that states it" if kind != "direction" else "its name")
        p.add_argument("--ref", action="append", metavar="ID", help="a record it references, in any state; repeatable")
        p.add_argument("--tag", action="append", help="repeatable")
        p.add_argument("--source", help="where it came from, in words, a URL or a repository path of the tree")
        p.add_argument("--body", metavar="FILE", help=BODY_HELP)
        return p
    mint("idea", "an open idea")
    p = mint("question", "an open question; its body says what counts as an answer")
    p.add_argument("--consume", action="append", metavar="IDEA", help="an open idea consumed into it, named in its references; repeatable")
    p.add_argument("--serves", action="append", metavar="ID", help="an open goal or direction it serves; repeatable"); p.add_argument("--size")
    p = mint("task", "a ready task; its body says what done means")
    p.add_argument("--size"); p.add_argument("--due", metavar="YYYY-MM-DD", help="its due date: surfaced as it nears, never a rank")
    p.add_argument("--after", help="what follows its completion, in words; printed at the close")
    p = mint("finding", "a standing finding, with its evidence")
    p.add_argument("--evidence", action="extend", nargs="+", required=True, metavar="FORM:TARGET", help="one item or more; repeatable")
    p.add_argument("--answers", metavar="Q", help="the open question it settles, which closes answered")
    mint("goal", "the owner's goal: the summary names the outcome, the body what reached means and how far out it lies")
    mint("direction", "the owner's direction, its words the body")
    p = sp.add_parser("draw"); p.add_argument("id"); p.add_argument("--owner", required=True)
    p = sp.add_parser("return"); p.add_argument("id"); p.add_argument("--note")
    p = sp.add_parser("make"); p.add_argument("task"); p.add_argument("--resolution", required=True, metavar="FILE", help=RESOLUTION_HELP + "; required")
    p = sp.add_parser("abort"); p.add_argument("task"); p.add_argument("--reason", required=True); p.add_argument("--resolution", metavar="FILE", help=RESOLUTION_HELP)
    p = sp.add_parser("answer"); p.add_argument("question"); p.add_argument("--by", required=True, help="the standing finding that settles it")
    p = sp.add_parser("evidence"); p.add_argument("finding"); p.add_argument("evidence", nargs="*", metavar="FORM:TARGET", help="added: how a finding's trust is raised")
    p.add_argument("--replace", nargs=2, metavar=("OLD", "NEW"), help="the item OLD, as written, swapped for NEW, resolved as an added item is; a dated note in the body")
    p.add_argument("--retire", metavar="OLD", help="the item OLD removed, with --reason; a dated note in the body")
    p.add_argument("--reason", help="with --retire: why the item goes, kept in the note")
    p = sp.add_parser("reach"); p.add_argument("goal"); p.add_argument("--reason", required=True, help="what shows it reached")
    p = sp.add_parser("giveup"); p.add_argument("goal"); p.add_argument("--reason", required=True)
    p = sp.add_parser("drop"); p.add_argument("direction"); p.add_argument("--reason", required=True)
    p = sp.add_parser("consume"); p.add_argument("idea")
    p = sp.add_parser("remove"); p.add_argument("id"); p.add_argument("--reason", required=True)
    p = sp.add_parser("wrong"); p.add_argument("question"); p.add_argument("--reason", required=True)
    p = sp.add_parser("impossible"); p.add_argument("question"); p.add_argument("--by", required=True, help="the standing finding that shows it")
    p = sp.add_parser("reopen"); p.add_argument("question"); p.add_argument("--reason", required=True, help="why it is to be settled again")
    p = sp.add_parser("park"); p.add_argument("id"); p.add_argument("--reason", required=True); p.add_argument("--revival")
    p = sp.add_parser("unpark"); p.add_argument("id"); p.add_argument("--note")
    p = sp.add_parser("block"); p.add_argument("id")
    p.add_argument("--on", required=True, action="append", help="a task's or a question's id, a date alone (YYYY-MM-DD) or words; repeatable")
    p.add_argument("--reason", required=True)
    p = sp.add_parser("unblock"); p.add_argument("id"); p.add_argument("--on", metavar="X", help="one item removed, as written; none, the block taken off")
    p.add_argument("--note")
    p = sp.add_parser("rank"); p.add_argument("id", nargs="?"); p.add_argument("n", nargs="?", type=int); p.add_argument("--set", nargs="+")
    p.add_argument("--clear", action="store_true"); p.add_argument("--insert", action="store_true")
    p = sp.add_parser("checked"); p.add_argument("ids", nargs="+")
    p = sp.add_parser("set"); p.add_argument("id"); p.add_argument("field"); p.add_argument("value")
    p.add_argument("--note", help="words appended to the body under the date: why, the owner's own for a goal's summary")
    p = sp.add_parser("ref", help="+X adds a reference, -Y removes one"); p.add_argument("id")
    p.add_argument("changes", nargs=argparse.REMAINDER, metavar="+X|-Y", help="each +X adds a reference and -Y removes one, the others kept")
    p = sp.add_parser("serves", help="+G adds a goal or a direction an open question serves, -D removes one"); p.add_argument("id")
    p.add_argument("changes", nargs=argparse.REMAINDER, metavar="+G|-D", help="each +G adds an open goal or direction and -D removes one")
    p = sp.add_parser("tag", help="+T adds a tag, -T removes one"); p.add_argument("id")
    p.add_argument("changes", nargs=argparse.REMAINDER, metavar="+T|-T", help="each +T adds a tag and -T removes one, the others kept")
    p = sp.add_parser("note", help="a file's text appended to a record's body under today's date"); p.add_argument("id")
    p.add_argument("--body", required=True, metavar="FILE", help="a file, or `-` for the standard input, whose text is appended, set apart under the date")
    p = sp.add_parser("find")
    for f in ("type", "state", "tag", "owner", "grep"):
        p.add_argument("--" + f)
    p.add_argument("--form", action="append", help="a finding's evidence form; repeatable, a finding listed when it carries every one given")
    p.add_argument("--only", action="store_true", help="with --form: the findings whose evidence carries those forms and no other")
    p.add_argument("--refers", metavar="ID|PATH", help="the records naming ID or PATH by a link, an evidence item, a source that is a path or a body link")
    p.add_argument("--deep", action="store_true", help="with --refers: the records naming those, and so on")
    p.add_argument("--parked", action="store_true"); p.add_argument("--ranked", action="store_true")
    p.add_argument("--blocked", action="store_true", help="the records whose block holds today")
    p.add_argument("--held", action="store_true", help="the active tasks and the ideas in a hand")
    p.add_argument("--id", action="append", dest="id_", metavar="ID", help="these records, a removed one among them; repeatable")
    p = sp.add_parser("show"); p.add_argument("id")
    p = sp.add_parser("graph"); p.add_argument("--from", dest="frm"); p.add_argument("--dot", action="store_true")
    p = sp.add_parser("index"); p.add_argument("--check", action="store_true"); p.add_argument("--print", action="store_true", dest="print_")
    sp.add_parser("check")
    p = sp.add_parser("state"); p.add_argument("--from", dest="frm", type=int, default=0); p.add_argument("--budget", type=int, default=14000)
    p.add_argument("--check", action="store_true", help="what a machine can see of a freeze; exit 1 on a failure, "
                                                         "2 where a part could not be decided")
    p = sp.add_parser("log"); lp = p.add_subparsers(dest="log_cmd", required=True, metavar="{add,archive}")
    lp.add_parser("add", help="FILE: one entry, written at the top of the log; `-` reads it from the standard input").add_argument("file")
    lp.add_parser("archive", help="--before DATE: the older entries moved, one file per month").add_argument("--before", required=True)
    p = sp.add_parser("reflow"); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", nargs="+", metavar="PATH", help="exit 1 on a line the reflow changes, each printed")
    g.add_argument("--as", nargs=2, metavar=("DEST", "DRAFT"), dest="as_", help="the draft checked as if appended to DEST, a file or a record's id: the reflow and markdownlint")
    p = sp.add_parser("doctor", help="the records and bindings an older model wrote, and what each reads now")
    p.add_argument("--fix", action="store_true", help="write every edit whose line states it, in place; what needs judgment stays for the hand")
    p.add_argument("--all", action="store_true", help="list each mechanical edit, not only the count per class")
    sp.add_parser("directions", help="the open directions as the owner's list")
    p = sp.add_parser("tags", help="every tag in use with its records, then the untagged"); p.add_argument("--type")
    p = sp.add_parser("touched", help="the records changed since the log's newest committed entry, for today's entry to name")
    p.add_argument("--since", metavar="REV", help="since this commit instead")
    p.add_argument("--unnamed", action="store_true", help="only those no entry since the base names")
    p.add_argument("--ids", action="store_true", help="the ids alone, on one line")
    sp.add_parser("artifacts", help="every repository path a record refers to, with the records naming it")
    sp.add_parser("pages")
    p = sp.add_parser("init"); p.add_argument("--records", default="records")
    p.add_argument("--log"); p.add_argument("--owner", action="append", help="repeatable"); p.add_argument("--force", action="store_true")
    p.add_argument("--print-instructions", action="store_true", dest="print_instructions",
                   help="print the paragraphs for the instructions file, for the bindings as they stand, and write nothing")
    return ap


TRANSITIONS = {"idea": cmd_idea, "question": cmd_question, "task": cmd_task, "finding": cmd_finding, "goal": cmd_goal,
               "direction": cmd_direction, "draw": cmd_draw, "return": cmd_return, "make": cmd_make, "abort": cmd_abort,
               "answer": cmd_answer, "impossible": cmd_impossible, "wrong": cmd_wrong, "reopen": cmd_reopen,
               "consume": cmd_consume, "remove": cmd_remove, "reach": cmd_reach, "giveup": cmd_giveup, "drop": cmd_drop,
               "park": cmd_park, "unpark": cmd_unpark, "block": cmd_block, "unblock": cmd_unblock,
               "rank": cmd_rank, "checked": cmd_checked, "set": cmd_set, "ref": cmd_ref, "serves": cmd_serves,
               "tag": cmd_tag, "note": cmd_note, "evidence": cmd_evidence}
# What a transition's notice reads of a record: a change of any of it is a change the records referring to it may follow.
NOTICED = ("state", "parked", "blocked_by")


def notices(recs, before, created, changed):
    """For each record a transition changed in its state, or parked, unparked, blocked or unblocked, the records that refer to
    it by a link, each with its state: who may need a follow-up.  A removed record is left out, and so is one the same
    command minted or changed; nothing is refused or failed for them."""
    touched = {r.id for r in created + changed}
    out = []
    for r in changed:
        now = json.dumps([r.fm.get(k) for k in NOTICED], sort_keys=True, default=str)
        if before.get(r.id) in (None, now):
            continue
        refs = []
        for x, _ in linked_by(recs, r.id):
            if x["state"] != "removed" and x.id not in touched and x.id not in [y["id"] for y in refs]:
                refs.append({"id": x.id, "state": x["state"]})
        if refs:
            out.append({"id": r.id, "refers": refs})
    return out


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
        ahead = kit_ahead(cfg)  # the project was brought to a newer release elsewhere: no write, a check that reports it, a warning on a read
        if ahead and (a.cmd in TRANSITIONS or a.cmd == "log" or a.cmd == "check" or a.cmd == "index" and not (a.print_ or a.check) or a.cmd == "doctor" and a.fix):
            raise Refused(ahead)  # `check` too: the mismatch is a problem found, exit 1, never "could not run"
        if ahead:
            out["kit_ahead"] = ahead
            if not quiet and not as_json:
                print(f"flow: warning — {ahead}", file=sys.stderr)
        broken = []
        recs = load_all(cfg, broken) if a.cmd == "check" else {} if a.cmd in ("log", "reflow", "doctor") else load_all(cfg)
        if a.cmd in TRANSITIONS:
            if a.cmd == "rank" and not a.set and not a.id:
                raise Refused("rank takes ID N, --set ID..., or ID --clear")
            if getattr(a, "reason", None) is not None and not a.reason.strip():  # what V15 and the closings need, refused here
                raise Refused(f"{a.cmd} takes --reason in words: an empty one says nothing")
            _JOURNAL.clear()
            _RERANKED.clear()
            _SET_RANKS.clear()
            before = {i: json.dumps([r.fm.get(k) for k in NOTICED], sort_keys=True, default=str) for i, r in recs.items()}
            try:
                created, changed = TRANSITIONS[a.cmd](cfg, recs, a, today)
            except BaseException:
                rollback()  # a transition happens whole or not at all
                raise
            _JOURNAL.clear()
            out["created"] = [r.id for r in created]
            out["changed"] = [r.id for r in changed]
            out["records"] = [summary_of(cfg, r) for r in created + changed]
            out["notices"] = notices(recs, before, created, changed)
            said = {n["id"]: n["refers"] for n in out["notices"]}
            for r in created:
                emit(f"created {r.id} — {r['summary']}  ({rel(cfg, r.path)})")
            if a.cmd == "rank" and a.set:  # an order written: each record said as placed or cleared, never as plain `changed`
                out["ranked"] = [{"id": i, "rank": n} for w, i, n in _SET_RANKS if w == "ranked"]
                out["unranked"] = [{"id": i, "was": n} for w, i, n in _SET_RANKS if w == "unranked"]
                for w, i, n in _SET_RANKS:
                    emit(f"ranked {i} {n}" if w == "ranked" else f"unranked {i} (was {n})")
            else:
                for r in changed:
                    emit(f"changed {r.id} — {stat(r) or ''} ({rel(cfg, r.path)})")
                    if r.id in said:  # who refers to it, for the session to decide on: never a refusal
                        emit("  refers to it, may need a follow-up: " + ", ".join(f"{x['id']} ({x['state']})" for x in said[r.id]))
            out["reranked"] = [{"id": i, "from": f, "to": n} for i, f, n in _RERANKED]
            for i, f, n in _RERANKED:
                emit(f"re-ranked {i} {f} → {n}")
            if a.cmd in ("finding", "answer", "impossible") and changed:
                emit(f"{changed[0].id} closed {changed[0]['state']} by {changed[0]['answered_by']}")
            if a.cmd in ("make", "abort") and changed and changed[0]["after"]:  # the post-done instruction, for the agent to follow
                out["after"] = changed[0]["after"]
                emit(f"after {changed[0].id}: {changed[0]['after']}")
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
            out["links"] = {f: refs(recs, ids) for f, ids in links(r, recs).items()}
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
            out["session_steps"] = list(SESSION_STEPS)
            emit("the session's own, which this command cannot see; the freeze's report answers each:")
            for s in SESSION_STEPS:
                emit(f"  [ ] {s}")
            emit(f"flow state --check: {len(problems)} failure(s); checked {', '.join(checked)}"
                 + (f"; {len(undecided)} not decided" if undecided else "")
                 + f"; {len(SESSION_STEPS)} step(s) above are the session's own")
            if problems or undecided:  # a failure exits 1; else a part not decided exits 2, never read as clean
                out["ok"], not_run = False, not problems
        elif a.cmd == "doctor":
            items = doctor(cfg, today)
            mech = [it for it in items if it["fix"] is not None]
            hand = [it for it in items if it["fix"] is None]
            remarks = [{"path": it["path"], "text": it["remark"]} for it in items if it["remark"]]  # always printed, never a thing for the hand
            out["remarks"] = remarks
            if a.fix:
                fixed, hand = doctor_fix(cfg, items)
                out["fixed"] = dict(fixed)
                if a.all:
                    for it in mech:
                        emit(f"{it['path']}: {it['was']} — {it['now']}")
                for cls, n in sorted(fixed.items(), key=lambda x: (-x[1], x[0])):
                    emit(f"fixed {n}: {DOCTOR_CLASSES[cls]}")
                if fixed:
                    emit(f"index refreshed: {rel(cfg, cfg.index)}")
            else:
                summary = Counter(it["cls"] for it in mech)
                out["summary"] = dict(summary)
                out["mechanical"] = [{"path": it["path"], "was": it["was"], "now": it["now"], "class": it["cls"]} for it in mech]
                if a.all:
                    for it in mech:
                        emit(f"{it['path']}: {it['was']} — {it['now']}")
                for cls, n in sorted(summary.items(), key=lambda x: (-x[1], x[0])):
                    emit(f"{n} × {DOCTOR_CLASSES[cls]}")
                if mech:
                    emit(f"`flow doctor --fix` writes these {len(mech)} edit(s) in place" + ("" if a.all else "; `--all` lists each"))
            for rm in remarks:
                emit(f"{rm['path']}: {rm['text']}")
            out["problems"] = [{"code": "DOCTOR", "id": None, "path": it["path"], "msg": f"{it['was']} — {it['now']}"} for it in hand]
            for it in hand:
                emit(f"{it['path']}: {it['was']} — {it['now']}")
            out["notes"] = doctor_notes(cfg)  # never a failure: a key an earlier init did not write, and its default
            for n in out["notes"]:
                emit(f"note: flow.toml has no {n['key']}, which `flow init` writes now ({n['default']}); read by {n['reads']}")
            emit(f"flow doctor: {len(hand)} thing(s) for the hand" + (f" and {len(mech)} mechanical edit(s)" if mech and not a.fix else "")
                 + (f"; {len(out['notes'])} optional key(s) the current init writes, noted" if out["notes"] else "")
                 + ("; settle each by hand from its line, then `flow index` and `flow check`" if hand else
                    "; then `flow check`" if a.fix else ""))
            if hand or (mech and not a.fix):
                out["ok"] = False
        elif a.cmd == "state":
            lines, more = state_lines(cfg, a.frm, a.budget, recs, today)
            behind = kit_behind(cfg) if not a.frm else None
            out["kit_behind"] = behind
            lines = ([behind] if behind else []) + lines
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
        elif a.cmd == "touched":
            rows, said, moved = cmd_touched(cfg, recs, a, today)
            out["touched"], out["base"], out["reranked_only"] = rows, said, moved
            if a.ids:
                emit(" ".join(x["id"] for x in rows))
            else:
                for x in rows:
                    emit(f"{x['id']} — {x['summary']} ({x['type']}, {x['state']})" if x["type"] else f"{x['id']} — gone ({x['path']})")
                emit(f"{len(rows)} record(s) changed {said}" + (", not named by an entry since" if a.unnamed else ""))
                if moved:
                    emit(f"re-ranked only: {', '.join(moved)}")
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
                 + (f"evidence forms {', '.join(cov['forms'])}; resolver{'s' if len(cov['resolvers']) > 1 else ''} {', '.join(f'{f} {w}' for f, w in cov['resolvers'].items()) or 'none asked'}; "
                    f"probe evidence {f'via {cfg.probes}' if cov['probes'] else f'unchecked (register {cfg.probes} not found)' if cfg.probes else 'unchecked (no register bound)'}; " if cfg.has("finding") else "")
                 + f"reflow via {cov['reflow']}; markdownlint {'present' if cov['markdownlint'] else 'ABSENT'}")
            lc = cov["library"]
            emit("library: " + (f"none bound ({cfg.library_route}) — a cited key is not checked" if not cfg.library_cmd else
                                f"DID NOT ANSWER ({cfg.library_route})" if lc is None else
                                f"{lc['cited']} key(s) cited from the records, {lc['records']} record(s) citing"
                                + (", by read grade: " + ", ".join(f"{n} {g}" for g, n in sorted(lc["grades"].items())) if lc["grades"] else "")
                                + f"; {lc['excluded']} of them excluded cards; the papers' reference entries and the documents the library's scan binds are not read here; asked through {cfg.library_route}"))
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


# The words a session reaches for that are no command here, each with the way it goes (`unknown_command`).
USUAL_WORDS = {
    **dict.fromkeys(("done", "close", "finish", "complete"), "a task closes with `make T --resolution FILE` (or `abort T --reason R`), "
                    "a question with the finding that settles it, `answer Q --by F` or `finding SUMMARY --evidence FORM:TARGET… --answers Q`"),
    "capture": "an idea is minted by `idea SUMMARY`",
    "frame": "a question is minted by `question SUMMARY`, `--consume IDEA` for an idea it is framed from, `--ref ID` for a finding or a question",
    "refine": "a question's tasks are minted by `task SUMMARY --ref Q`, a sub-question by `question SUMMARY --ref Q`",
    "kill": "`remove ID --reason R` for an idea, an open question or a ready task; `abort T --reason R` for an active task",
    **dict.fromkeys(("out", "release", "putback"), "`return ID --note N` puts a drawn record back"),
    **dict.fromkeys(("start", "take", "claim"), "`draw ID --owner O`"),
    **dict.fromkeys(("list", "ls", "search"), "`find` lists records, `state` prints the cold-start bundle"),
    "status": "`state` prints the cold-start bundle, `show ID` one record",
    **dict.fromkeys(("edit", "update"), "`set ID FIELD VALUE` changes a field, `note ID --body FILE` appends to a body"),
    **dict.fromkeys(("comment", "append"), "`note ID --body FILE` appends to a record's body"),
    "untag": "`tag ID -T` removes a tag, `tag ID +T` adds one",
}


def unknown_command(parser, word, usual):
    """The refusal for a subcommand that does not exist, or None where `word` is one (or a flag): the way the
    usual word for it goes, and the nearest names, in place of argparse's list of every choice."""
    names = [n for act in parser._actions if isinstance(act, argparse._SubParsersAction) for n in act.choices]
    if not word or word.startswith("-") or word in names:
        return None
    near = difflib.get_close_matches(word, names, n=3, cutoff=0.6)
    return (f"no command {word!r}" + (f": {usual[word]}" if word in usual else "")
            + (f"; the nearest: {', '.join(near)}" if near else "") + f"; `{parser.prog} --help` lists every command")


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
    msg = unknown_command(build_parser(), rest[0], USUAL_WORDS)
    if msg:  # a guessed verb: its way and the nearest names, not the whole list
        refused(rest[0], msg, known.json)
        return 2
    if "-h" in rest or "--help" in rest:  # a subcommand's flags need none either
        build_parser().parse_args(rest)
        return 0
    if rest and rest[0] == "init":
        a = build_parser().parse_args(["init"] + rest[1:])
        if a.print_instructions:  # the paragraphs to compare an instructions file with: nothing written, nothing refused
            try:  # the project's root, found upward as every command finds it; the working directory where none stands
                where = Path(known.root).resolve() if known.root else find_root(os.getcwd())
            except Refused:
                where = Path(os.getcwd()).resolve()
            text = init_instructions(where)
            print(json.dumps({"ok": True, "command": "init", "instructions": text}, indent=1) if known.json else text, end="" if not known.json else "\n")
            return 0
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
