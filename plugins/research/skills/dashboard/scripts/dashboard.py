#!/usr/bin/env python3
"""dashboard — one read-only dashboard over every component installed beside it and bound in the project.

  python3 dashboard.py [--root DIR] [--host 127.0.0.1] [--port 8765] [--component CMD...]... [--list]

The dashboard is a renderer and nothing else.  A component is any command that answers
`<command> --json pages` with a page manifest — its mount prefix, its navigation entries, the
patterns that turn an id in any text into a link, and its routes, each naming the subcommand
to run for a path and the view its answer is rendered with — and answers every other page
as `<command> --json <subcommand> ...` as the manifest said.  The browser therefore never
reads a record, a card or a file itself: every page is the component's own answer, so the
command line and the dashboard cannot disagree.

Components are found in this order, the first of a name and then the first of a mount winning:

  1. `--component CMD...` on the command line;
  2. `dashboard.toml` at the project root, `[[component]]` tables with a `command` list;
  3. the skill directories beside this one, then the sibling plugins of a checkout and of a
     Claude Code marketplace cache (each at its newest version) — each skill with a
     `component.toml` naming its `command` (relative to that skill directory) and the
     project's `bindings` file — mounted when the bindings file exists at the project root;
  4. the commands `flow` and `library` on PATH, when their bindings file exists.

Views: `markdown` (a field rendered as Markdown), `lines` (a list of lines), `list` (the records of an
answer, laid as cards where the manifest has `card` and as a table of rows where it has none; the query
string is mapped to the command's flags, a `params` entry with `choices` is a select, and the answer's
`next` pages it), `table` (the zones of an answer: hands, the board's goals and directions, decks and piles of cards), `record` (one
answer's card, fields, body and sections), `tables` (several answers, one table each) and `check`
(problems, warnings, coverage).  The manifest's `card` key says how a record is laid on a card's face
and its `home` which page `/` goes to.  Standard library only, no script in a page and nothing fetched
from another host; Markdown bodies use the `markdown` package when it is installed and fall back to
paragraphs otherwise.  Binds to localhost by default and writes nothing.  `--selftest` mounts stub
components and renders every view.
"""

import argparse
import html
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import tomllib
import traceback
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

try:
    import markdown as _markdown
except ImportError:  # pragma: no cover
    _markdown = None

KNOWN = {"flow": "flow.toml", "library": "library.toml"}  # the commands found on PATH, and their bindings
TIMEOUT = 60
_REQ = threading.local()  # the request being answered, for the header to mark its entry


class Refused(Exception):
    pass


def read_toml(path):
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        raise Refused(f"{path} does not parse: {e}")


# --- components --------------------------------------------------------------

class Component:
    def __init__(self, name, command, root):
        self.name, self.command, self.root = name, list(command), root
        self.manifest = None

    def ask(self, *args):
        """One question, answered as JSON; a command that does not answer is an error dict."""
        try:
            r = subprocess.run(self.command + ["--json"] + list(args), capture_output=True, text=True,
                               cwd=self.root, timeout=TIMEOUT)
            ans = json.loads(r.stdout)
            if not isinstance(ans, dict):
                raise ValueError("not an object")
            return ans
        except (OSError, ValueError, subprocess.TimeoutExpired) as e:
            return {"ok": False, "problems": [{"msg": f"{' '.join(self.command)} {' '.join(args)}: {e}"}]}

    def load(self):
        ans = self.ask("pages")
        m = ans.get("pages")
        if not isinstance(m, dict) or not m.get("mount") or not isinstance(m.get("routes"), list):
            raise Refused(f"{self.name}: `pages` did not answer a manifest: {problem_of(ans)}")
        self.manifest = m
        self.mount = m["mount"].rstrip("/") or "/"
        self.routes = []
        for rt in m["routes"]:
            rx = "^" + re.sub(r"\\\{(\w+)\\\}", lambda g: f"(?P<{g.group(1)}>[^/]+)", re.escape(rt["path"])) + "$"
            self.routes.append((re.compile(rx), rt))
        self.routes.sort(key=lambda x: "{" in x[1]["path"])  # fixed paths before templated ones
        self.links = [(re.compile(l["pattern"]), l["path"]) for l in m.get("links") or []]
        return self

    def route(self, path):
        for rx, rt in self.routes:
            m = rx.match(path)  # matched on the raw path, so an encoded `/` adds no segment
            if m:
                params = {k: unquote(v) for k, v in m.groupdict().items()}
                if any(v.startswith("-") for v in params.values()):  # an id or a key, never a flag
                    return None, None
                return rt, params
        return None, None


def problem_of(ans):
    return "; ".join(str(p.get("msg")) for p in ans.get("problems") or []) or "the component did not answer"


def find_root(start):
    p = Path(start).resolve()
    for cand in (p, *p.parents):
        if any((cand / f).is_file() for f in ("dashboard.toml", *KNOWN.values())):
            return cand
    raise Refused(f"no dashboard.toml, flow.toml or library.toml found above {start}")


def _version_key(name):
    return tuple(int(x) if x.isdigit() else -1 for x in re.split(r"[.\-+]", name))


def sibling_components(skills):
    """The `component.toml` files a dashboard at `skills/dashboard` can see, in order: the skill
    directories beside it (one plugin, or every skill flat in an agent's directory); the sibling
    plugins of a checkout (`plugins/<plugin>/skills/<skill>`); the sibling plugins of a Claude
    Code marketplace cache (`<marketplace>/<plugin>/<version>/skills/<skill>`), each plugin at its
    newest version."""
    out = list(sorted(skills.glob("*/component.toml")))
    plugin = skills.parent
    try:
        out += sorted(p for p in plugin.parent.glob("*/skills/*/component.toml") if p.parents[2] != plugin)
    except OSError:
        pass
    # The marketplace walk runs only where the layout is one: the plugin directory is a version
    # (`<marketplace>/<plugin>/<version>/skills`).  A flat `.agents/skills` or a checkout's
    # `plugins/<plugin>/skills` is not, and walking two levels up from it would read the
    # project's parent or the filesystem root.
    if not re.fullmatch(r"v?\d+(?:\.\d+)*(?:[.\-+][\w.]+)?", plugin.name):
        return out
    market = plugin.parent.parent
    try:
        for other in sorted(d for d in market.glob("*") if d.is_dir() and d != plugin.parent):
            versions = sorted((v for v in other.glob("*") if v.is_dir() and (v / "skills").is_dir()), key=lambda v: _version_key(v.name))
            if versions:
                out += sorted(versions[-1].glob("skills/*/component.toml"))
    except OSError:
        pass
    return out


def discover(root, extra=(), skills=None):
    comps, seen = [], set()

    def add(name, command):
        if name in seen:
            return
        seen.add(name)
        comps.append(Component(name, command, root))

    for i, cmd in enumerate(extra):
        add(f"component-{i + 1}", cmd)
    dt = root / "dashboard.toml"
    if dt.is_file():
        for i, c in enumerate(read_toml(dt).get("component", [])):
            cmd = c.get("command")
            if not isinstance(cmd, list) or not cmd:
                raise Refused(f"dashboard.toml: component {i + 1} has no command list")
            cmd = [str(root / x) if (root / x).is_file() else str(x) for x in cmd]
            add(c.get("name") or Path(cmd[-1]).stem, cmd)
    skills = skills or Path(__file__).resolve().parent.parent.parent
    for ct in sibling_components(skills):
        c = read_toml(ct)
        cmd, bindings = c.get("command"), c.get("bindings")
        if not isinstance(cmd, list) or not cmd or not bindings or not (root / bindings).is_file():
            continue
        cmd = [str(ct.parent / x) if (ct.parent / x).is_file() else sys.executable if x == "python3" else str(x) for x in cmd]
        add(c.get("name") or ct.parent.name, cmd)
    for name, bindings in KNOWN.items():
        if (root / bindings).is_file() and shutil.which(name):
            add(name, [shutil.which(name)])
    return comps


def first_per_mount(comps):
    """The loaded components, the first of each mount kept: a command mounted by hand under its own
    name may answer the mount of a component found after it, and two never share one."""
    seen = set()
    return [c for c in comps if not (c.mount in seen or seen.add(c.mount))]


# --- rendering -----------------------------------------------------------------

def esc(x):
    return html.escape("" if x is None else str(x))


class Renderer:
    def __init__(self, comps):
        self.links = [(rx, path) for c in comps for rx, path in c.links]

    def _href(self, path, m):
        groups = [m.group(0)] + [g if g is not None else "" for g in m.groups()]
        href = path
        for i, g in enumerate(groups):
            href = href.replace("{%d}" % i, quote(g, safe=""))
        return re.sub(r"#$", "", href)

    def _link(self, path, m):
        return f'<a class="id" href="{esc(self._href(path, m))}">{esc(m.group(0))}</a>'

    def href(self, text):
        """Where an id leads, by the first link pattern that matches the whole of it; None where none does."""
        for rx, path in self.links:
            m = rx.fullmatch(text)
            if m:
                return self._href(path, m)
        return None

    def autolink(self, h):
        """Link every component's ids in the text nodes of an HTML fragment, never inside a tag or an <a>."""
        out, in_a = [], 0
        for part in re.split(r"(<[^>]+>)", h):
            if part.startswith("<"):
                if re.match(r"<a[\s>]", part):
                    in_a += 1
                elif part.startswith("</a"):
                    in_a = max(0, in_a - 1)
                out.append(part)
            elif in_a:
                out.append(part)
            else:
                for rx, path in self.links:
                    # a link made by an earlier pattern is left alone
                    part = "".join(x if x.startswith("<") else rx.sub(lambda m: self._link(path, m), x)
                                   for x in re.split(r"(<a [^>]*>[^<]*</a>)", part))
                out.append(part)
        h = "".join(out)
        return re.sub(r"<code>(<a class=\"id\"[^>]*>[^<]*</a>)</code>", r"\1", h)

    def inline(self, text):
        h = esc(text)
        h = re.sub(r"`([^`]+)`", r"<code>\1</code>", h)
        h = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", h)
        h = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", h)
        h = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", h)
        return self.autolink(h)

    def block(self, text):
        text = re.sub(r"(?<=\S)\n(?=\*\*[^*\s])", "\n\n", text or "")  # a bold label opens a paragraph
        if _markdown:
            # a record's body is prose: a `<` in it is a character, never a tag the browser runs, and in a
            # code span it is shown as written
            md = _markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
            try:
                md.preprocessors.deregister("html_block")
                md.inlinePatterns.deregister("html")
                h = md.convert(text)
            except (KeyError, ValueError, AttributeError):  # a Markdown without these names: escape before
                h = _markdown.markdown(text.replace("<", "&lt;"), extensions=["tables", "fenced_code", "sane_lists"])
            h = re.sub(r'<a href="([^"]*)"', lambda m: m.group(0) if safe_url(html.unescape(m.group(1))) else "<a", h)
        else:
            h = "".join(f"<p>{esc(p)}</p>" for p in re.split(r"\n\s*\n", text) if p.strip())
        return self.autolink(h)


CSS = """
:root{color-scheme:light dark;--bg:#e4e8df;--fg:#1d1c1a;--mut:#4f4d47;--line:rgba(0,0,0,.3);--bar:rgba(255,255,255,.5);--acc:#1c4a9a;
--code:rgba(255,255,255,.55);--ok:#1a5231;--bad:#8a1c12;
--paper:#f8f5ee;--wait:#e0ddd3;--ink:#1d1c1a;--lab:#5a564d;--hair:#cfcabd;--plink:#1c4a9a;--pcode:#ebe7dc;
--serif:Georgia,'Iowan Old Style','Times New Roman',serif;--mono:ui-monospace,'SF Mono',Menlo,Consolas,monospace;
--shadow:0 1px 2px rgba(0,0,0,.28),0 6px 14px rgba(0,0,0,.2)}
@media (prefers-color-scheme:dark){:root{--bg:#22332d;--fg:#eef1ea;--mut:#bcc6bd;--line:rgba(255,255,255,.3);--bar:rgba(0,0,0,.22);
--acc:#9fc2ff;--code:rgba(0,0,0,.28);--ok:#8fd9a8;--bad:#ffa59b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--acc)}a:focus-visible{outline:2px solid currentColor;outline-offset:2px}
header{background:var(--bar);border-bottom:1px solid var(--line)}
header .in{max-width:1500px;margin:0 auto;padding:14px 32px;display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 22px}
header a{color:var(--fg)}header a[aria-current=page]{font-weight:700}
header .brand{font:700 18px var(--serif);text-decoration:none}
header .sep{color:var(--mut)}
main{max-width:1500px;margin:0 auto;padding:28px 32px 48px}
h1{font:700 24px/1.25 var(--serif);margin:0 0 12px}
h2{font:700 20px/1.25 var(--serif);margin:1.6em 0 .5em}
h3{font-size:1em;margin:1.2em 0 .4em;color:var(--mut)}
a.id{font-family:var(--mono);font-size:.9em;white-space:nowrap;text-decoration:none}
a.id:hover{text-decoration:underline}
code{font-family:var(--mono);font-size:.88em;background:var(--code);padding:1px 4px;border-radius:4px}
pre{background:var(--code);padding:10px;border-radius:6px;overflow-x:auto;white-space:pre-wrap}pre code{padding:0}
.mut{color:var(--mut)}.small{font-size:.87em}.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.meta{color:var(--mut);font-size:13px;margin:0 0 14px}
table{border-collapse:collapse;width:100%}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.82em;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);font-weight:600}
table.kv th{width:10em;text-transform:none;letter-spacing:0;font-size:.9em}
.table-wrap{overflow-x:auto}
.ok{color:var(--ok)}.bad{color:var(--bad)}
ul.recs{list-style:none;padding:0;margin:0}ul.recs li{padding:6px 0;border-top:1px solid var(--hair)}ul.recs li:first-child{border-top:0}
input,select,button{font:inherit;font-size:14px;min-height:44px;padding:0 10px;border:1px solid #8fa0b3;border-radius:6px;background:var(--paper);color:var(--ink)}
input::placeholder{color:var(--lab)}
button{padding:0 18px;font-weight:700;cursor:pointer}
.filters{display:flex;flex-wrap:wrap;align-items:flex-end;gap:10px 14px;margin:0 0 14px;padding:12px 14px;border:1px solid var(--line);border-radius:10px;background:var(--bar)}
.filters label{display:flex;flex-direction:column;gap:3px;font-size:12px;color:var(--mut)}
.filters label.flag{flex-direction:row;align-items:center;gap:6px;min-height:44px;font-size:14px;color:var(--fg)}
.filters input[type=checkbox]{min-height:0;width:18px;height:18px}
.filters input[type=text]{width:min(220px,100%)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(320px,100%),1fr));gap:16px}
.panel{background:var(--paper);color:var(--ink);border-radius:10px;padding:12px 18px;box-shadow:var(--shadow)}
.panel a{color:var(--plink)}.panel code{background:var(--pcode)}.panel h2{margin-top:.2em;font-size:17px}
.panel th{color:var(--lab)}.panel th,.panel td{border-bottom-color:var(--hair)}
.panel pre{background:var(--pcode)}
.body{padding:4px 0;font-size:15px;line-height:1.55}.panel .body{padding:4px 6px}.body p{margin:.6em 0}.body h2{margin-top:1.2em}
.badge{display:inline-block;padding:1px 7px;border-radius:99px;background:#e2dfd5;color:#44423d;font-size:.8em;font-weight:700;white-space:nowrap;vertical-align:1px}
.s-ready{background:#d6ecdd;color:#1a5231}.s-held{background:#d7e3f6;color:#1f4179}
.s-parked{background:#f4e3b5;color:#5f4200}.s-blocked{background:#f4d5ce;color:#7f2015}
.cards{display:flex;flex-wrap:wrap;gap:16px}
.cd{--p:var(--paper);--band:#5b6068;--plate:transparent;--frame:linear-gradient(#b5b1a6,#b5b1a6);--w:1px;--lines:0 0 0 0 transparent;--glow:0 0 0 0 transparent;
width:240px;max-width:100%;min-height:336px;display:flex;flex-direction:column;overflow:hidden;border-radius:10px;
border:var(--w) solid transparent;background:linear-gradient(var(--p),var(--p)) padding-box,var(--frame) border-box;
box-shadow:var(--lines),var(--glow),var(--shadow);color:var(--ink);text-decoration:none;font-size:11.5px;line-height:1.35}
.cd.wt{--p:var(--wait)}
.cd.f1{--frame:linear-gradient(#8e8a7f,#8e8a7f)}
.cd.fs{--w:4px;--frame:linear-gradient(135deg,#7b848e 0%,#f2f5f7 22%,#9aa3ad 45%,#e6eaee 68%,#6f7882 100%);
--lines:inset 0 0 0 1px #5b636c,0 0 0 1px #5b636c;--glow:0 0 12px rgba(226,232,238,.45);
--plate:linear-gradient(115deg,#d9dee3 0%,#f7f8fa 40%,#cfd5db 75%,#eceff2 100%)}
.cd.fg{--w:6px;--frame:linear-gradient(135deg,#8a6410 0%,#f6dc86 22%,#b98a1c 45%,#fbeeb4 68%,#8a6410 100%);
--lines:inset 0 0 0 1px #6e4f08,0 0 0 1px #6e4f08;--glow:0 0 16px rgba(244,205,96,.6);
--plate:linear-gradient(115deg,#f1d687 0%,#fff6d8 38%,#efd07a 72%,#fbeebb 100%)}
.cd.k-idea{--band:#6a4c9c}.cd.k-question{--band:#2a5599}.cd.k-task{--band:#1d6b5c}.cd.k-finding{--band:#9a3a2e}
.cd.k-goal{--band:#1f2a36}.cd.k-direction{--band:#8a5a1c}.cd.k-work{--band:#4a5560}
.cd .band{display:flex;align-items:center;gap:6px;padding:5px 8px;background:var(--band);color:#fff;min-height:30px}
.cd .pip{min-width:20px;height:20px;padding:0 5px;border-radius:10px;background:#fff;color:#1d1c1a;font-size:12px;font-weight:700;line-height:20px;text-align:center}
.cd .cid{margin-left:auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font:11px var(--mono)}
.cd svg{flex:none}
.cd .plate{display:block;padding:9px 11px 8px;background:var(--plate)}
.cd .ttl{display:block;font:700 14.5px/1.25 var(--serif);overflow-wrap:anywhere}
.cd .tl{display:flex;align-items:center;gap:6px;padding:4px 11px;border-top:1px solid var(--hair);border-bottom:1px solid var(--hair);font-size:11px;color:#4a473f}
.cd .tl b{font-weight:700;white-space:nowrap}.cd .tl i{font-style:normal;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cd .box{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;gap:6px;padding:8px 11px 7px}
.cd .sum{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:6;line-clamp:6;overflow:hidden;font-size:12px;line-height:1.4;color:#2b2925;overflow-wrap:anywhere}
.cd .nos{font-size:12px;font-style:italic;color:var(--lab)}
.cd .lns{margin-top:auto;display:flex;flex-direction:column;gap:3px}
.cd .ln{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cd .ln b{font-size:9.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--lab)}
.cd .ms{display:flex;align-items:center;gap:10px;padding:5px 11px 0;font-size:9.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--lab)}
.cd .m{display:flex;align-items:center;gap:5px}.cd .m+.m{margin-left:auto}
.cd .foot{display:flex;align-items:center;gap:6px;padding:6px 9px 7px;font-size:10.5px}
.cd .foot .badge{font-size:10.5px;vertical-align:baseline}
.cd .pl{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#4a473f}
.zone{display:flex;flex-direction:column;gap:14px;margin:0}
.zone.sep{padding-top:24px;border-top:1px solid var(--line);margin-top:36px}
.hands{display:flex;flex-wrap:wrap;align-items:flex-start;gap:36px 40px}
.hands+.hands{margin-top:36px}
.zh{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px}.zh h2{margin:0}
.zh .note{font-size:13px;color:var(--mut)}
.void{width:240px;max-width:100%;height:336px;display:flex;align-items:center;justify-content:center;padding:16px;border:2px dashed var(--line);border-radius:10px;font-size:13px;text-align:center;color:var(--mut)}
.row{display:flex;flex-wrap:wrap;align-items:flex-start;gap:16px}
.pack{width:150px;display:flex;flex-direction:column;gap:10px}
.pack .note{font-size:12px;color:var(--mut)}.pack a{color:var(--fg);font-size:13px}
.stack{position:relative;width:132px;height:180px}
.back{position:absolute;left:0;top:0;width:120px;height:168px;border-radius:9px;background:#243242;border:1px solid #8fa0b3}
.back.b3{left:12px;top:12px;background:#1a2430}.back.b2{left:6px;top:6px;background:#1f2b39}
.back.b1{display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:inset 0 0 0 5px #243242,inset 0 0 0 6px #8fa0b3;color:#fff}
.back b{font:700 34px/1.1 var(--serif)}.back span{font-size:12px}
.piles{display:flex;flex-wrap:wrap;align-items:flex-start;gap:16px 40px}
.pile{display:flex;align-items:center;gap:14px;color:var(--fg);text-decoration:none}
.pile .pb{width:70px;height:98px;display:flex;align-items:center;justify-content:center;flex:none;border-radius:7px;background:#243242;border:1px solid #8fa0b3;box-shadow:4px 4px 0 #1a2430;color:#fff;font:700 24px var(--serif)}
.pile .pt{display:flex;flex-direction:column}.pile b{text-decoration:underline}.pile span.n{font-size:12px;color:var(--mut)}
.rec{display:flex;flex-wrap:wrap;align-items:flex-start;gap:32px 40px}
.rec .face{width:384px;flex:none}.rec .big{zoom:1.6}
.rec .main{flex:999 1 560px;min-width:0;display:flex;flex-direction:column;gap:24px}
.rec .main h2,.sec h2{margin:0;font-size:17px}
.sec{display:flex;flex-direction:column;gap:10px;margin:0}
.article{padding:20px 24px}.article h1{margin:0 0 12px;font-size:22px}
.article p{margin:0 0 10px;font-size:15px;line-height:1.55}.article .body{padding:0}
.dl{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:8px 16px;margin:14px 0 0;padding-top:14px;border-top:1px solid var(--hair);font-size:12.5px}
.dl dt{font-size:10px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--lab)}.dl dd{margin:0;overflow-wrap:anywhere}
.minis{display:flex;flex-wrap:wrap;gap:12px}
.mini{width:250px;max-width:100%;min-height:76px;display:flex;flex-direction:column;overflow:hidden;border-radius:8px;border:1px solid #b5b1a6;background:var(--paper);color:var(--ink);text-decoration:none}
.mini .mb{display:flex;align-items:baseline;gap:8px;padding:3px 9px;background:var(--band,#5b6068);color:#fff;font-size:11px}
.mini .mb i{font:normal 11px var(--mono)}.mini .mb em{margin-left:auto;font-style:normal}
.mini .mt{padding:7px 9px 8px;font:700 13px/1.25 var(--serif);overflow-wrap:anywhere}
.mini.k-idea .mb{--band:#6a4c9c}.mini.k-question .mb{--band:#2a5599}.mini.k-task .mb{--band:#1d6b5c}.mini.k-finding .mb{--band:#9a3a2e}
.mini.k-goal .mb{--band:#1f2a36}.mini.k-direction .mb{--band:#8a5a1c}.mini.k-work .mb{--band:#4a5560}
@media (max-width:640px){header .in{gap:6px 14px;padding:12px 16px}main{padding:20px 16px 40px}.article{padding:16px}}
@media (max-width:480px){.rec .face{width:312px}.rec .big{zoom:1.3}}
@media (max-width:360px){.rec .face{width:264px}.rec .big{zoom:1.1}}
"""


def param_name(p):
    """A query parameter of a `list` route: a word, or `{"name", "choices"}` for one with a fixed set of values."""
    return p["name"] if isinstance(p, dict) else p


def badge(v):
    """One badge per value: a finding's forms come as `formal, stated`, each its own word and colour."""
    if v in (None, ""):
        return ""
    return " ".join(f'<span class="badge s-{esc(w.lower())}">{esc(w)}</span>' for w in str(v).split(", "))


def dig(obj, path):
    """`records.0.read.grade` into an answer; None where the path leads nowhere."""
    cur = obj
    for part in str(path).split("."):
        if isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)] if int(part) < len(cur) else None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


_SCHEME = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*):")


def safe_url(url):
    """Whether the page may carry `url` as a link: http, https, mailto or a relative path.  Any other scheme
    (`javascript:` above all) is shown as text, since a script on the dashboard's origin reads every page of it."""
    m = _SCHEME.match(re.sub(r"[\x00-\x20]", "", str(url)))  # a browser drops these before it reads the scheme
    return not m or m.group(1).lower() in ("http", "https", "mailto")


def fmt(R, v, href=None):
    if v is None or v == [] or v == {} or v == "":
        return ""
    if href:
        url = href.replace("{}", str(v))
        return f'<a href="{esc(url)}" rel="noreferrer">{esc(v)}</a>' if safe_url(url) else esc(v)
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, dict):
        return "<br>".join(f"<b>{esc(k)}</b>: {fmt(R, x)}" for k, x in v.items() if x not in (None, "", []))
    if isinstance(v, list):
        return "<br>".join(fmt(R, x) for x in v)
    return R.inline(v)


STATE_COLS = ("state", "standing", "status", "forms", "grade", "read.grade")


# --- the card's face -----------------------------------------------------------

_SVG = ('<svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#ffffff" stroke-width="1.5" '
        'stroke-linecap="round" stroke-linejoin="round">%s</svg>')
# the seven faces the dashboard knows: the kind's word, its band colour, its sign (an inline stroke SVG, never an emoji)
FACES = {
    "idea": ("Idea", _SVG % '<path d="M8 1.5a4.5 4.5 0 0 0-2.5 8.2V11h5V9.7A4.5 4.5 0 0 0 8 1.5z"/><path d="M6 12.8h4M6.8 14.5h2.4"/>'),
    "question": ("Question", _SVG % '<circle cx="8" cy="8" r="6.3"/><path d="M6.2 6.3a1.9 1.9 0 1 1 2.8 1.7c-.6.3-1 .8-1 1.4M8 11.6v.1"/>'),
    "task": ("Task", _SVG % '<rect x="2.5" y="2.5" width="11" height="11" rx="2"/><path d="M5.2 8.3l2 2 3.6-4.3"/>'),
    "finding": ("Finding", _SVG % '<path d="M8 1.8l5.4 6.2L8 14.2 2.6 8z"/><path d="M5.6 8L8 10.6 10.4 8"/>'),
    "goal": ("Goal", _SVG % '<path d="M4 14.5V2M4 2.5h7.5l-1.8 3 1.8 3H4"/>'),
    "direction": ("Direction", _SVG % '<circle cx="8" cy="8" r="6.3"/><path d="M10.6 5.4L9 9 5.4 10.6 7 7z"/>'),
    "work": ("Work", _SVG % '<path d="M3 2.5h8.5A1.5 1.5 0 0 1 13 4v9.5H4.5A1.5 1.5 0 0 1 3 12z"/><path d="M3 12a1.5 1.5 0 0 1 1.5-1.5H13"/>'),
}
WAITING = ("parked", "blocked")  # the standings whose card lies on greyer paper
GEM = {"f0": "#8b877c", "f1": "#6f6b61", "fs": "#5f6973", "fg": "#a37410"}
DIAMOND = '<path d="M%d 1l5 5-5 5-5-5z" fill="%s" stroke="%s" stroke-width="1.3"/>'
BAR = '<rect x="%d" y="1" width="6" height="10" rx="1.5" fill="%s" stroke="%s" stroke-width="1.3"/>'


def cap(s):
    return s[:1].upper() + s[1:]


def fill_path(path, rec):
    """A route's path with each `{field}` filled from the record's own scalar fields."""
    for k, x in rec.items():
        if isinstance(x, (str, int)) and not isinstance(x, bool):
            path = path.replace("{%s}" % k, quote(str(x), safe=""))
    return path


def level_of(scale, v):
    """1-based place of `v` in a scale given in rising order, 0 where it is not judged or not a level of it."""
    return scale.index(v) + 1 if isinstance(scale, list) and isinstance(v, str) and v in scale else 0


def frame_of(i, n):
    """The frame of level `i` of `n`: none judged, the first level plain, the last gold, those between silver."""
    return "f0" if i <= 0 else "fg" if i >= n else "f1" if i == 1 else "fs"


def filled(i, n, of=3):
    """How many of `of` gems or bars level `i` of `n` fills: one for the first, all for the last, in proportion between."""
    return 0 if i <= 0 else of if i >= n else 1 if i == 1 else max(1, min(of - 1, int(of * i / n + 0.5)))


def meter_html(m, i, n, cls):
    word = str(m["scale"][i - 1]) if i else "not judged"
    k = filled(i, n)
    if m.get("frame"):
        gem = GEM[cls]
        s = "".join(DIAMOND % (6 + 12 * j, gem if j < k else "none", gem) for j in range(3))
        svg = f'<svg role="img" aria-label="{esc(m["label"])}: {esc(word)}" width="36" height="12" viewBox="0 0 36 12">{s}</svg>'
    else:
        bar = "#1d1c1a" if i else GEM["f0"]
        s = "".join(BAR % (1 + 10 * j, bar if j < k else "none", bar) for j in range(3))
        svg = f'<svg role="img" aria-label="{esc(m["label"])}: {esc(word)}" width="28" height="12" viewBox="0 0 28 12">{s}</svg>'
    return f'<span class="m" title="{esc(m["label"])}: {esc(word)}">{esc(m["label"])} {svg}</span>'


def face_parts(spec, rec):
    """What a record prints on a face, by the manifest's `card` paths: a dict, the same for a card and for the record's page."""
    lab = dig(rec, spec["label"]) if spec.get("label") else None
    lab = None if lab in (None, "") else str(lab)
    face = spec.get("face") if spec.get("face") else (spec.get("faces") or {}).get(lab)
    face = face if face in FACES else None
    standing, spath = None, None
    paths = spec.get("standing") or []
    for p in [paths] if isinstance(paths, str) else paths:
        v = dig(rec, p)
        if v not in (None, "", []):
            standing, spath = str(v), p
            break
    lines = [ln for ln in (dig(rec, spec["lines"]) if spec.get("lines") else None) or []
             if isinstance(ln, dict) and ln.get("text") not in (None, "")]
    tags = dig(rec, spec["tags"]) if spec.get("tags") else None
    rank = dig(rec, spec["rank"]) if spec.get("rank") else None
    meters, frame = [], "f0"
    for m in spec.get("meters") or []:
        if not isinstance(m, dict) or not m.get("field") or not isinstance(m.get("scale"), list):
            continue
        if m.get("kinds") is not None and lab not in m["kinds"]:
            continue
        i, n = level_of(m["scale"], dig(rec, m["field"])), len(m["scale"])
        if m.get("frame"):
            frame = frame_of(i, n)
        meters.append((m, i, n))
    carried = [spec.get(k) for k in ("id", "title", "summary", "tags", "rank", "label", "place", "lines")] + [spath] + [m["field"] for m, _, _ in meters]
    return {"carried": carried, "id": dig(rec, spec["id"]) if spec.get("id") else None, "title": dig(rec, spec["title"]) if spec.get("title") else None,
            "has_summary": bool(spec.get("summary")), "summary": dig(rec, spec["summary"]) if spec.get("summary") else None,
            "tags": " · ".join(map(str, tags)) if isinstance(tags, list) else (tags or ""),
            "rank": None if rank in (None, "") else rank, "label": lab, "face": face, "standing": standing,
            "place": dig(rec, spec["place"]) if spec.get("place") else None, "lines": lines, "meters": meters, "frame": frame,
            "word": cap(lab) if lab else FACES[face][0] if face else ""}


def card_html(spec, rec):
    """One card, 240 px wide: the band, the title, the type line, the text box, the parameters and the foot, the whole one link."""
    c = face_parts(spec, rec)
    face = c["face"]
    waiting = any(w in WAITING for w in (c["standing"] or "").split(", "))
    cls = " ".join(["cd", "k-" + face if face else "k-x", c["frame"]] + (["wt"] if waiting else []))
    pip = f'<span class="pip" title="its place on the ranked list">{esc(c["rank"])}</span>' if c["rank"] is not None else ""
    band = f'<span class="band">{pip}{FACES[face][1] if face else ""}<span class="cid">{esc(c["id"])}</span></span>'
    plate = f'<span class="plate"><span class="ttl">{esc(c["title"])}</span></span>'
    typeline = f'<span class="tl"><b>{esc(c["word"])}</b><i>{esc(c["tags"])}</i></span>'
    summary = (f'<span class="sum">{esc(c["summary"])}</span>' if c["summary"] else
               '<span class="nos">no summary yet</span>' if c["has_summary"] else "")
    lns = "".join(f'<span class="ln"><b>{esc(ln.get("label"))}</b> {esc(ln.get("text"))}</span>' for ln in c["lines"][:2])
    box = f'<span class="box">{summary}<span class="lns">{lns}</span></span>'
    ms = "".join(meter_html(m, i, n, c["frame"] if m.get("frame") else "f0") for m, i, n in c["meters"])
    meters = f'<span class="ms">{ms}</span>' if ms else ""
    standing = badge(c["standing"]) if c["standing"] else ""
    foot = f'<span class="foot">{standing}<span class="pl">{esc(c["place"])}</span></span>'
    inner = band + plate + typeline + box + meters + foot
    href = fill_path(spec["link"], rec) if spec.get("link") else ""
    if href and safe_url(href):
        return f'<a class="{cls}" href="{esc(href)}">{inner}</a>'
    return f'<div class="{cls}">{inner}</div>'


class Site:
    def __init__(self, comps):
        self.comps = comps
        self.R = Renderer(comps)
        self.entries = [(ci, n["label"], n["path"]) for ci, c in enumerate(comps) for n in c.manifest.get("nav") or []]

    def nav_html(self):
        """The header's entries, each component's group after a separator; the entry of the page being read is marked."""
        where = getattr(_REQ, "where", None)
        best, most = None, -1
        for idx, (_, _, path) in enumerate(self.entries):
            u = urlparse(path)
            q = parse_qs(u.query)
            if where and u.path == where[0] and all(where[1].get(k) == v for k, v in q.items()) and len(q) > most:
                best, most = idx, len(q)
        out, last = [], None
        for idx, (ci, label, path) in enumerate(self.entries):
            if last is not None and ci != last:
                out.append('<span class="sep">|</span>')
            last = ci
            cur = ' aria-current="page"' if idx == best else ""
            out.append(f'<a href="{esc(path)}"{cur}>{esc(label)}</a>')
        return "".join(out)

    def page(self, title, body):
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · dashboard</title>
<style>{CSS}</style></head><body><header><nav class="in" aria-label="Dashboard"><a class="brand" href="/">Dashboard</a>{self.nav_html()}
</nav></header><main>{body}</main></body></html>"""

    def home(self):
        cards = []
        for c in self.comps:
            m = c.manifest
            items = "".join(f'<li><a href="{esc(n["path"])}">{esc(n["label"])}</a></li>' for n in m.get("nav") or [])
            cards.append(f'<section class="panel"><h2><a href="{esc(c.mount)}">{esc(m.get("title") or c.name)}</a></h2>'
                         f'<p class="mut small"><code>{esc(" ".join(Path(x).name if i == 0 else x for i, x in enumerate(c.command)))}</code></p>'
                         f'<ul class="recs">{items}</ul></section>')
        return self.page("Dashboard", f'<h1>Dashboard</h1><p class="meta">{len(self.comps)} component(s) mounted; '
                         f'every page is the component\'s own answer, through its command with <code>--json</code>.</p>'
                         f'<div class="grid">{"".join(cards)}</div>')

    def error(self, title, msg, code=500):
        return code, self.page(title, f"<h1>{esc(title)}</h1><pre>{esc(msg)}</pre>")

    # --- views ---------------------------------------------------------------

    def render(self, comp, rt, params, qs):
        args = [p.format(**params) if "{" in p else p for p in rt.get("run") or []]
        query = {k: v[0] for k, v in qs.items() if v and v[0] != ""}
        if rt.get("words") and query.get(rt["words"]):
            args += [w for w in query[rt["words"]].split() if not w.startswith("-")]  # a flag is not a word
        title = (rt.get("title") or comp.name).format(**params)
        for p in map(param_name, rt.get("params") or []):
            if query.get(p):
                if query[p].startswith("-"):  # a value, never a flag: `--root=…` would point the command elsewhere
                    return self.error(title, f"the filter {p} takes a value, and {query[p]!r} reads as a flag", 400)
                args += ["--" + p, query[p]]
        for f in rt.get("flags") or []:
            if query.get(f):
                args.append("--" + f)
        view = rt.get("view", "markdown")
        if view == "tables":
            return self.view_tables(comp, rt, title)
        ans = comp.ask(*args)
        if view == "check":
            return self.view_check(ans, title)
        if not ans.get("ok", True):
            why = problem_of(ans)
            return self.error(title, why, 404 if re.search(r"does not exist|no card|not found", why, re.I) else 500)
        if view == "record":
            return 200, self.view_record(comp, rt, ans, title)
        if view == "list":
            return 200, self.view_list(comp, rt, ans, title, query)
        if view == "table":
            return 200, self.view_table(comp, rt, ans, title)
        if view == "lines":
            lines = dig(ans, rt.get("field", "lines")) or []
            return 200, self.page(title, f"<h1>{esc(title)}</h1><pre>{self.R.autolink(esc(chr(10).join(map(str, lines))))}</pre>")
        text = dig(ans, rt.get("field", "text")) or ""
        return 200, self.page(title, f'<div class="body">{self.R.block(str(text))}</div>')

    def fields(self, rec, skip, hrefs):
        """The (name, html) pairs of a record's fields that hold something, `a.b` skipping a key inside a map."""
        out = []
        for k, v in rec.items():
            if k in skip:
                continue
            if isinstance(v, dict):
                v = {sk: sv for sk, sv in v.items() if f"{k}.{sk}" not in skip}
            h = badge(v) if k in STATE_COLS and isinstance(v, str) else fmt(self.R, v, hrefs.get(k))
            if h:
                out.append((k, h))
        return out

    def mini(self, comp, item, via):
        """A link of a `refs` section as a small card: the band with the id and the link's field, the title under it."""
        faces = (comp.manifest.get("card") or {}).get("faces") or {}
        pre = re.match(r"([a-z]+)-", str(item.get("id")))  # an id that opens with a label of `faces` takes that face's band
        face = faces.get(pre.group(1)) if pre else None
        cls = "mini" + (f" k-{face}" if face in FACES else "")
        href = self.R.href(str(item.get("id")))
        inner = (f'<span class="mb"><i>{esc(item.get("id"))}</i><em>{esc(via.replace("_", " "))}</em></span>'
                 f'<span class="mt">{esc(item.get("title"))}</span>')
        return f'<a class="{cls}" href="{esc(href)}">{inner}</a>' if href else f'<div class="{cls}">{inner}</div>'

    def section(self, comp, ans, sec):
        data = dig(ans, sec["field"])
        if not data:
            return ""
        R = self.R
        kind = sec.get("as", "lines")
        head = f'<h2>{esc(sec.get("title") or sec["field"])}</h2>'
        if kind == "refs" and isinstance(data, (dict, list)):
            groups = data.items() if isinstance(data, dict) else [("", data)]
            minis = "".join(self.mini(comp, x, f) for f, xs in groups for x in xs if isinstance(x, dict))
            return f'<section class="sec">{head}<div class="minis">{minis}</div></section>'
        if kind == "sites":
            items = "".join(f"<li><code>{esc(x.get('path'))}:{esc(x.get('line'))}</code> <span class='small'>{R.inline((x.get('text') or '')[:260])}</span></li>"
                            for x in data)
        else:
            items = "".join(f"<li>{R.inline(x) if isinstance(x, str) else fmt(R, x)}</li>" for x in data)
        return f'<section class="sec">{head}<div class="panel"><ul class="recs">{items}</ul></div></section>'

    def view_record(self, comp, rt, ans, title):
        R = self.R
        spec = comp.manifest.get("card")
        rec = dig(ans, rt.get("fields", "records.0")) or {}
        hide = set(rt.get("hide") or [])
        hrefs = rt.get("hrefs") or {}
        secs = "".join(self.section(comp, ans, sec) for sec in rt.get("sections") or [])
        body_md = dig(ans, rt["body"]) if rt.get("body") else None
        body = f'<div class="body">{R.block(str(body_md))}</div>' if body_md and str(body_md).strip() else ""
        crumb = f'<p class="meta">{esc(comp.manifest.get("title") or comp.name)} / <code>{esc(title)}</code></p>'
        heading = rec.get(rt["heading"]) if rt.get("heading") else None
        if spec:
            c = face_parts(spec, rec)
            skip = hide | {p for p in (c["carried"]) if p}
            heading = heading or c["title"] or title
            summary = f"<p>{R.inline(c['summary'])}</p>" if c["summary"] else ""
            dl = "".join(f"<div><dt>{esc(k.replace('_', ' '))}</dt><dd>{h}</dd></div>" for k, h in self.fields(rec, skip, hrefs))
            dl = f'<dl class="dl">{dl}</dl>' if dl else ""
            article = f'<article class="panel article"><h1>{R.inline(heading)}</h1>{summary}{body}{dl}</article>'
            return self.page(title, f'{crumb}<div class="rec"><div class="face"><div class="big">{card_html(spec, rec)}</div></div>'
                                    f'<div class="main">{article}{secs}</div></div>')
        named = rec.get("title") if not heading else None  # a record's `title` heads its page where the route names no heading field
        rows = "".join(f"<tr><th>{esc(k.replace('_', ' '))}</th><td>{h}</td></tr>"
                       for k, h in self.fields(rec, hide | ({"title"} if named else set()), hrefs))
        state = rec.get("state") or rec.get("status") or rec.get("forms")
        if named:
            head = f"<h1>{esc(title)} {badge(state)}<br>{R.inline(named)}</h1>"
        else:
            head = f"<h1>{R.inline(heading) if heading else esc(title)}</h1>"
        return self.page(title, f'{crumb}{head}<div class="grid"><section class="panel"><table class="kv">{rows}</table></section>{secs}</div>'
                         + (f'<h2>Body</h2><div class="panel">{body}</div>' if body else ""))

    def view_list(self, comp, rt, ans, title, query):
        R = self.R
        spec = comp.manifest.get("card")
        recs = ans.get("records") or []
        path = rt["path"]
        inputs = ""
        if rt.get("words"):
            inputs += f'<label>Words<input type="text" name="{esc(rt["words"])}" value="{esc(query.get(rt["words"], ""))}"></label>'
        for p in rt.get("params") or []:
            name = param_name(p)
            if name == "from":
                continue
            cur = query.get(name, "")
            if isinstance(p, dict) and isinstance(p.get("choices"), list):
                choices = [str(x) for x in p["choices"]]
                opts = '<option value="">any</option>' + "".join(
                    f'<option value="{esc(x)}"{" selected" if x == cur else ""}>{esc(x)}</option>'
                    for x in choices + ([cur] if cur and cur not in choices else []))
                inputs += f'<label>{esc(cap(name.replace("_", " ")))}<select name="{esc(name)}">{opts}</select></label>'
            else:
                inputs += f'<label>{esc(cap(name.replace("_", " ")))}<input type="text" name="{esc(name)}" value="{esc(cur)}"></label>'
        for f in rt.get("flags") or []:
            inputs += f'<label class="flag"><input type="checkbox" name="{esc(f)}" value="1"{" checked" if query.get(f) else ""}> {esc(f)}</label>'
        form = f'<form class="filters" action="{esc(path)}">{inputs}<button>Filter</button></form>' if inputs else ""
        total = ans.get("total", len(recs))
        unit = "card" if spec else "row"
        meta = [f"{len(recs)} of {total}" if total != len(recs) else f"{len(recs)} {unit}(s)"]
        if ans.get("rankers"):
            meta.append("ranked by " + "; ".join(ans["rankers"]))
        if rt.get("note"):
            meta.append(esc(rt["note"]))
        if ans.get("next") is not None:
            q = dict(query, **{"from": str(ans["next"])})
            meta.append(f'<a href="{esc(path + "?" + urlencode(q))}">next</a>')
        if query.get("from"):
            q = dict(query)
            q.pop("from")
            meta.append(f'<a href="{esc(path + ("?" + urlencode(q) if q else ""))}">first page</a>')
        head = f"<h1>{esc(title)}</h1>{form}<p class='meta'>{' · '.join(meta)}</p>"
        if spec:  # the component lays its records on a face
            return self.page(title, head + (f'<div class="cards">{"".join(card_html(spec, r) for r in recs)}</div>' if recs else "<p class='mut'>none</p>"))
        cols = rt.get("columns") or (sorted(recs[0].keys()) if recs else [])
        link = rt.get("link") or {}
        th = "".join(f"<th>{esc(c.split('.')[-1])}</th>" for c in cols)
        rows = []
        for r in recs:
            cells = []
            for c in cols:
                v = dig(r, c)
                if link and c == link["column"] and v is not None:
                    cells.append(f'<td><a class="id" href="{esc(fill_path(link["path"], r))}">{esc(v)}</a></td>')
                elif c in STATE_COLS and isinstance(v, str):
                    cells.append(f"<td>{badge(v)}</td>")
                else:
                    cells.append(f"<td>{fmt(R, v)}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        return self.page(title, head + f"<div class='table-wrap'><table><tr>{th}</tr>{''.join(rows)}</table></div>")

    def view_table(self, comp, rt, ans, title):
        """The table: each zone of the answer, its heading and its cards (a hand's with a dashed place for each free one,
        a board zone's, the goals or the directions, face up with no place and no stack, the two in a row of their own
        after the hands, a deck's behind a stack of backs carrying its count), the piles in one row at the end."""
        spec = comp.manifest.get("card") or {"id": "id", "title": "title"}
        lst = rt.get("list")

        def href(z):
            q = urlencode({k: "1" if v is True else v for k, v in (z.get("find") or {}).items() if v is not False and v is not None})
            return lst + ("?" + q if q else "") if lst else None

        def cards(z):
            return "".join(card_html(spec, r) for r in z.get("cards") or [] if isinstance(r, dict))

        def heading(z, note=""):
            word = f'<span class="note">{esc(note)}</span>' if note else ""
            return f'<div class="zh"><h2>{esc(cap(str(z.get("title") or "")))}</h2>{word}</div>'

        def stack(count):
            layers = "".join(f'<span class="back b{k}"></span>' for k in range(min(3, count), 1, -1))
            unit = "card" if count == 1 else "cards"
            return f'<span class="stack">{layers}<span class="back b1"><b>{esc(count)}</b><span>{unit}</span></span></span>'

        out, hands, board = [f'<h1 class="vh">{esc(title)}</h1>'], [], []

        def flush():
            for row, rows in (('hands', hands), ('hands board', board)):
                if rows:
                    out.append(f'<div class="{row}">' + "".join(rows) + "</div>")
                    rows.clear()

        piles = []
        for z in [z for z in dig(ans, rt.get("field", "zones")) or [] if isinstance(z, dict)]:
            kind, count = z.get("kind"), z.get("count") or 0
            if kind == "pile":
                piles.append(z)
            elif kind == "deck":
                flush()
                if not count:
                    body = heading(z, "no cards")
                else:
                    h = href(z)
                    more = f'<a href="{esc(h)}">The whole deck</a>' if h else ""
                    pack = f'<div class="pack">{stack(count)}<span class="note">{esc(z.get("note"))}</span>{more}</div>'
                    body = f'{heading(z)}<div class="row">{pack}{cards(z)}</div>'
                out.append(f'<section class="zone sep">{body}</section>')
            elif kind == "board":
                body = heading(z, z.get("note") or "no cards") + (f'<div class="cards">{cards(z)}</div>' if z.get("cards") else "")
                board.append(f'<section class="zone">{body}</section>')
            else:
                if board:
                    flush()
                room = z.get("room") if isinstance(z.get("room"), int) and not isinstance(z.get("room"), bool) else 0
                row = cards(z) + '<div class="void">room for one more</div>' * max(0, room)
                body = heading(z, z.get("note")) + (f'<div class="cards">{row}</div>' if row else '<p class="mut">no cards</p>')
                hands.append(f'<section class="zone">{body}</section>')
        flush()
        if piles:
            items = ""
            for z in piles:
                h = href(z)
                inner = (f'<span class="pb">{esc(z.get("count") or 0)}</span><span class="pt"><b>{esc(cap(str(z.get("title") or "")))}</b>'
                         f'<span class="n">{esc(z.get("note"))}</span></span>')
                items += f'<a class="pile" href="{esc(h)}">{inner}</a>' if h else f'<div class="pile">{inner}</div>'
            out.append(f'<section class="zone sep"><h2>Piles</h2><div class="piles">{items}</div></section>')
        return self.page(title, "".join(out))

    def view_tables(self, comp, rt, title):
        R = self.R
        parts = [f"<h1>{esc(title)}</h1>"]
        if rt.get("note"):
            parts.append(f"<p class='mut small'>{esc(rt['note'])}</p>")
        for t in rt.get("tables") or []:
            ans = comp.ask(*t["run"])
            rows = dig(ans, t.get("field", "records")) or []
            parts.append(f"<h2>{esc(t.get('title') or t['field'])}</h2>")
            if not ans.get("ok", True) and not rows:
                parts.append(f"<p class='bad'>{esc(problem_of(ans))}</p>")
                continue
            if not rows:
                parts.append("<p class='mut'>none</p>")
                continue
            cols = t.get("columns") or sorted(rows[0].keys())
            parts.append("<div class='table-wrap'><table><tr>" + "".join(f"<th>{esc(c)}</th>" for c in cols) + "</tr>"
                         + "".join("<tr>" + "".join(f"<td>{fmt(R, dig(r, c))}</td>" for c in cols) + "</tr>" for r in rows) + "</table></div>")
        return 200, self.page(title, "".join(parts))

    def view_check(self, ans, title):
        R = self.R
        problems = ans.get("problems") or []
        warnings = ans.get("warnings") or []
        cov = ans.get("coverage") or {}
        verdict = '<span class="ok">✓ clean</span>' if not problems else f'<span class="bad">✗ {len(problems)} problem(s)</span>'

        def table(items):
            if not items:
                return "<p class='ok'>none</p>"
            items = [x if isinstance(x, dict) else {"msg": x} for x in items]
            cols = [c for c in ("code", "id", "key", "path", "msg") if any(c in x for x in items)]
            return ("<div class='table-wrap'><table><tr>" + "".join(f"<th>{esc(c)}</th>" for c in cols) + "</tr>"
                    + "".join("<tr>" + "".join(f"<td>{R.inline(x.get(c)) if x.get(c) is not None else ''}</td>" for c in cols) + "</tr>" for x in items)
                    + "</table></div>")
        covs = "".join(f"<tr><th>{esc(k)}</th><td>{fmt(R, v) if v not in (None, '') else '<span class=mut>—</span>'}</td></tr>" for k, v in cov.items())
        body = (f"<h1>{esc(title)}</h1><p>{verdict}</p><h2>Problems ({len(problems)})</h2>{table(problems)}"
                + (f"<h2>Warnings ({len(warnings)})</h2>{table(warnings)}" if warnings else "")
                + f"<h2>Coverage</h2><table class='kv'>{covs}</table>")
        return 200, self.page(title, body)


def respond(site, path):
    """(status, html) for a request path with its query: what the server sends, usable without one."""
    u = urlparse(path)
    _REQ.where = (u.path, parse_qs(u.query))
    if u.path == "/":
        for c in site.comps:  # the first component that names a home page is where `/` goes
            home = c.manifest.get("home")
            if isinstance(home, str) and re.fullmatch(r"/(?![/\\])[^\\]*", home):  # one `/` first, and no backslash: `/\x` reads as `//x`
                return 302, home
        if len(site.comps) == 1:
            return 302, site.comps[0].mount
        return 200, site.home()
    comp = max((c for c in site.comps if u.path == c.mount or u.path.startswith(c.mount + "/")),
               key=lambda c: len(c.mount), default=None)
    if comp is None:
        return 404, site.page("Not found", "<h1>Not found</h1>")
    rt, params = comp.route(u.path)
    if rt is None:
        return 404, site.page("Not found", f"<h1>No page at <code>{esc(u.path)}</code></h1>")
    return site.render(comp, rt, params, parse_qs(u.query))


# --- server --------------------------------------------------------------------

def make_handler(site, host="127.0.0.1", allow_hosts=()):
    loopback = host in ("127.0.0.1", "localhost", "::1")
    allowed = {host.lower(), "localhost", "127.0.0.1", "[::1]", "::1"} | {h.lower() for h in allow_hosts}
    if not loopback:  # reached from another device: by this machine's names, or by any address
        allowed |= {socket.gethostname().lower(), socket.gethostname().lower() + ".local", socket.getfqdn().lower()}

    def host_ok(name):
        if name in allowed:
            return True
        try:  # a rebinding page reaches the server under a name it controls, never under an address
            ipaddress.ip_address(name.strip("[]"))
            return not loopback
        except ValueError:
            return False

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            # bound to the loopback, the server answers only a request addressed to it: a page from
            # elsewhere that resolves its name to this address is not answered
            name = (self.headers.get("Host") or "").rsplit(":", 1)[0] if not (self.headers.get("Host") or "").startswith("[") \
                else (self.headers.get("Host") or "").split("]")[0] + "]"
            fetch_site, mode = self.headers.get("Sec-Fetch-Site"), self.headers.get("Sec-Fetch-Mode")
            origin = self.headers.get("Origin")
            if not host_ok(name.lower()):
                code, text = site.error("Forbidden", "the request names another host", 403)
            elif (fetch_site in ("cross-site", "same-site") and mode != "navigate") or \
                    (origin and urlparse(origin).netloc.lower() != (self.headers.get("Host") or "").lower()):
                # another site's page may link here, but never load a page of it in the background
                code, text = site.error("Forbidden", "a page of another site asked for this one", 403)
            else:
                code, text = respond(site, self.path)
            location = text if code == 302 else None
            data = ("" if location else text).encode("utf-8")
            self.send_response(code)
            if location:
                self.send_header("Location", location)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):
            pass

    return H


# --- selftest ------------------------------------------------------------------

STUB = r'''
import json, sys
args = [a for a in sys.argv[1:] if a != "--json"]
cmd = args[0] if args else ""
SCALE = ["low", "medium", "high"]
SIZES = ["small", "medium", "large"]


def card(i, type_, state, title, summary=None, standing=None, value=None, size=None, rank=None, tags=(), place=None, lines=()):
    return {"id": "item-%03d" % i, "type": type_, "state": state, "standing": standing, "title": title, "summary": summary,
            "tags": list(tags), "rank": rank, "value": value, "size": size, "place": place,
            "lines": [{"label": a, "text": b} for a, b in lines]}


CARDS = [
    card(1, "idea", "open", "A <b> & the first", "if a < b & c > d", "held", "high", None, 1, ("t1", "t2"), "ann, 3 days",
         (("serves", "Goal one"), ("due", "2026-01-01"), ("third", "never shown"))),
    card(2, "question", "done", "second", None, None, "medium", "large", None, (), "discard pile"),
    card(3, "task", "open", "third", "a parked one", "parked", "low", "small", 4, (), "ann's deck", (("parked", "until the calibration"),)),
    card(4, "task", "open", "fourth", "a blocked one", "blocked", None, "medium", None, (), "common deck", (("waits", "item-003"),)),
    card(5, "finding", "standing", "fifth", "a finding", None),
    card(6, "goal", "open", "sixth", "a goal"),
    card(7, "direction", "open", "seventh", "a direction"),
    card(8, "paper", "open", "eighth", "a work", None, None, None, None, ("w",)),
    card(9, "gizmo", "open", "ninth", "a kind nobody knows", "odd"),
]
FACES = {"idea": "idea", "question": "question", "task": "task", "finding": "finding", "goal": "goal", "direction": "direction",
         "paper": "work", "item": "task"}
if cmd == "pages":
    out = {"ok": True, "pages": {"component": "stub", "title": "Stub", "mount": "/stub", "home": "/stub/table",
        "nav": [{"label": "Table", "path": "/stub/table"}, {"label": "Open", "path": "/stub/list?state=open"}, {"label": "Stub", "path": "/stub"},
                {"label": "Check", "path": "/stub/check"}],
        "card": {"id": "id", "title": "title", "summary": "summary", "tags": "tags", "rank": "rank", "label": "type", "faces": FACES,
                 "standing": ["standing", "state"], "place": "place", "lines": "lines", "link": "/stub/r/{id}",
                 "meters": [{"label": "value", "field": "value", "scale": SCALE, "kinds": ["idea", "question", "task"], "frame": True},
                            {"label": "effort", "field": "size", "scale": SIZES, "kinds": ["question", "task"]}]},
        "links": [{"pattern": r"\bitem-\d{3}\b", "path": "/stub/r/{0}"}, {"pattern": r"lib:([a-z0-9]+)(?:#([a-z0-9]+))?", "path": "/lib/{1}#{2}"}],
        "routes": [
            {"path": "/stub", "view": "markdown", "run": ["index"], "field": "text", "title": "Stub"},
            {"path": "/stub/table", "view": "table", "run": ["table"], "field": "zones", "params": ["top"], "list": "/stub/list", "title": "Table"},
            {"path": "/stub/list", "view": "list", "run": ["find"], "params": [{"name": "state", "choices": ["open", "done"]}, "tag"], "flags": ["ranked", "held"],
             "words": "q", "columns": ["id", "state", "title"], "link": {"column": "id", "path": "/stub/r/{id}"}, "title": "Items"},
            {"path": "/stub/r/{id}", "view": "record", "run": ["show", "{id}"], "title": "{id}", "fields": "records.0", "body": "body",
             "hide": ["id", "secret.path"], "hrefs": {"doi": "https://doi.org/{}", "url": "{}"},
             "sections": [{"field": "links", "title": "Links", "as": "refs"}, {"field": "backlinks", "title": "Back", "as": "refs"},
                          {"field": "sites", "title": "Sites", "as": "sites"}]},
            {"path": "/stub/h/{id}", "view": "record", "run": ["show", "{id}"], "title": "{id}", "fields": "records.0", "heading": "label", "hide": ["label"]},
            {"path": "/stub/lines", "view": "lines", "run": ["state"], "field": "lines", "title": "Lines"},
            {"path": "/stub/tables", "view": "tables", "title": "Tables", "tables": [{"title": "T", "run": ["cands"], "field": "rows", "columns": ["a", "b"]}]},
            {"path": "/stub/check", "view": "check", "run": ["check"], "title": "Check"}]}}
elif cmd == "index":
    out = {"ok": True, "text": "# Index\n\nSee item-001 and lib:jen1990#lemma here.\n"}
elif cmd == "find":
    recs = list(CARDS)
    if "--state" in args:
        recs = [r for r in recs if r["state"] == args[args.index("--state") + 1]]
    if "--ranked" in args:
        recs = recs[:1]
    if "words" in args:
        recs = []
    out = {"ok": True, "records": recs, "total": len(CARDS), "next": 5 if len(recs) == len(CARDS) else None}
elif cmd == "table":
    out = {"ok": True, "zones": [
        {"kind": "hand", "owner": "ann", "title": "ann's hand", "count": 2, "note": "2 of 3", "room": 1, "find": {"held": True, "owner": "ann"},
         "cards": [CARDS[0], CARDS[2]]},
        {"kind": "hand", "owner": "bot", "title": "bot's hand", "count": 1, "note": "1 held, no limit", "room": None, "find": {"held": True, "owner": "bot"},
         "cards": [CARDS[3]]},
        {"kind": "board", "owner": None, "title": "the goals", "count": 1, "note": "1 open", "room": None, "find": {"type": "goal", "state": "open"},
         "cards": [CARDS[5]]},
        {"kind": "board", "owner": None, "title": "the directions", "count": 0, "note": "none set", "room": None, "find": {"type": "direction", "state": "open"},
         "cards": []},
        {"kind": "deck", "owner": "ann", "title": "ann's deck", "count": 0, "note": "", "room": None, "find": {"deck": "ann"}, "cards": []},
        {"kind": "deck", "owner": "bot", "title": "bot's deck", "count": 2, "note": "2 ready", "room": None, "find": {"held": True, "owner": "bot"},
         "cards": [CARDS[7]]},
        {"kind": "deck", "owner": None, "title": "the common deck", "count": 7, "note": "3 ready", "room": None, "find": {"deck": "common"},
         "cards": [CARDS[4], CARDS[8]]},
        {"kind": "pile", "owner": None, "title": "the discard pile", "count": 3, "note": "2 done, 1 answered", "room": None, "find": {"pile": "discard"}, "cards": []},
        {"kind": "pile", "owner": None, "title": "the graveyard", "count": 1, "note": "1 aborted", "room": None, "find": {"pile": "graveyard"}, "cards": []}]}
elif cmd == "show":
    hit = [c for c in CARDS if c["id"] == args[1]]
    if not hit:
        out = {"ok": False, "problems": [{"msg": args[1] + " does not exist"}]}
    else:
        rec = dict(hit[0], label="Label of one", doi="10.1/x", url=" JavaScript:alert(1)", secret={"path": "hidden", "n": 3})
        out = {"ok": True, "records": [rec],
               "body": "A body naming item-002, [a script](java\tscript:alert(2)) and [a page](https://example.org/).\n",
               "links": {"serves": [{"id": "goal-0001", "title": "Goal & more"}]},
               "backlinks": {"references": [{"id": "item-002", "title": "second <i>"}]},
               "sites": [{"path": "a.md", "line": 3, "text": "cites item-001"}]}
elif cmd == "state":
    out = {"ok": True, "lines": ["a.md:1: one", "a.md:2: item-002 here"]}
elif cmd == "cands":
    out = {"ok": True, "rows": [{"a": 1, "b": "x"}]}
elif cmd == "check":
    out = {"ok": False, "problems": [{"code": "V1", "id": "item-002", "msg": "bad"}], "warnings": ["w1"], "coverage": {"records": 2, "kinds": ["a", "b"]}}
else:
    out = {"ok": False, "problems": [{"msg": "no such command"}]}
print(json.dumps(out))
'''
# the same component with no `card` and no `home`, mounted elsewhere: it renders rows, and `/` stays as it was
PLAIN = STUB.replace('"/stub', '"/plain').replace('"card":', '"nocard":').replace('"home":', '"nohome":')


def css_rules(css, media=""):
    """The stylesheet as [(media, selector, {property: value})] in its order, a block under `@media` read with its condition."""
    out, pos = [], 0
    while True:
        m = re.compile(r"\s*([^{}]+)\{").match(css, pos)
        if not m:
            return out
        depth, j = 1, m.end()
        while depth and j < len(css):
            depth += {"{": 1, "}": -1}.get(css[j], 0)
            j += 1
        body, sel, pos = css[m.end():j - 1], m.group(1).strip(), j
        if sel.startswith("@media"):
            out += css_rules(body, sel)
        else:
            decls = [d.split(":", 1) for d in body.split(";") if ":" in d]
            out.append((media, sel, {k.strip(): v.strip() for k, v in decls}))


def css_of(rules, selector, media=""):
    """What the stylesheet says of one selector (under one `@media` condition), the later rule winning."""
    out = {}
    for md, sel, d in rules:
        if md == media and sel == selector:
            out.update(d)
    return out


def style_of(rules, card):
    """What the stylesheet gives a rendered card: the `.cd` rule and each `.cd.x.y` rule whose classes the card has."""
    have = set(re.match(r'<(?:a|div) class="([^"]*)"', card).group(1).split())
    out = {}
    for md, sel, d in rules:
        m = re.fullmatch(r"\.cd((?:\.[\w-]+)*)", sel)
        if not md and m and set(m.group(1).split(".")[1:]) <= have:
            out.update(d)
    return out


def contrast(a, b):
    def lum(h):
        c = [int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)



def selftest():
    failures = []

    def expect(name, cond):
        print(f"  {'ok ' if cond else 'BAD'} {name}")
        if not cond:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        skills = root / "skills"
        (skills / "stub").mkdir(parents=True)
        (skills / "stub" / "stub.py").write_text(STUB)
        (skills / "stub" / "component.toml").write_text('command = ["python3", "stub.py"]\nbindings = "stub.toml"\n')
        (skills / "unbound").mkdir()
        (skills / "unbound" / "component.toml").write_text('command = ["python3", "x.py"]\nbindings = "nowhere.toml"\n')
        comps = discover(root, skills=skills)
        expect("a sibling component with no bindings file is not mounted", [c.name for c in comps] == [])
        (root / "stub.toml").write_text("")
        comps = discover(root, skills=skills)
        expect("a sibling component is mounted when its bindings file exists, with this interpreter",
               [c.name for c in comps] == ["stub"] and comps[0].command[0] == sys.executable and comps[0].command[1].endswith("stub.py"))
        (root / "dashboard.toml").write_text('[[component]]\nname = "stub"\ncommand = ["python3", "skills/stub/stub.py"]\n')
        comps = discover(root, skills=skills)
        expect("dashboard.toml wins over the sibling of the same name", len(comps) == 1 and comps[0].command[1].endswith("skills/stub/stub.py"))
        (root / "dashboard.toml").unlink()
        market = root / "cache" / "market"
        for plugin, versions in (("dash", ("0.1.0",)), ("other", ("0.9.0", "0.10.0"))):
            for v in versions:
                sk = market / plugin / v / "skills" / (plugin if plugin != "dash" else "dashboard")
                sk.mkdir(parents=True)
                if plugin != "dash":
                    (sk / "stub.py").write_text(STUB.replace("stub", "other-" + v))
                    (sk / "component.toml").write_text('command = ["python3", "stub.py"]\nbindings = "stub.toml"\n')
        comps = discover(root, skills=market / "dash" / "0.1.0" / "skills")
        expect("a sibling plugin of the marketplace cache is mounted at its newest version",
               [c.name for c in comps] == ["other"] and "/0.10.0/" in comps[0].command[1])
        checkout = root / "plugins"
        for plugin in ("dash", "lib"):
            sk = checkout / plugin / "skills" / plugin
            sk.mkdir(parents=True)
            if plugin == "lib":
                (sk / "stub.py").write_text(STUB)
                (sk / "component.toml").write_text('command = ["python3", "stub.py"]\nbindings = "stub.toml"\n')
        comps = discover(root, skills=checkout / "dash" / "skills")
        expect("a sibling plugin of a checkout is mounted", [c.name for c in comps] == ["lib"])
        decoy = root / "flat" / "decoy" / "1.0.0" / "skills" / "decoy"
        decoy.mkdir(parents=True)
        (decoy / "stub.py").write_text(STUB.replace("stub", "decoy"))
        (decoy / "component.toml").write_text('command = ["python3", "stub.py"]\nbindings = "stub.toml"\n')
        (root / "flat" / "proj" / "skills" / "dashboard").mkdir(parents=True)
        comps = discover(root / "flat" / "proj", skills=root / "flat" / "proj" / "skills")
        expect("a flat skills directory walks no marketplace: nothing two levels up is mounted", [c.name for c in comps] == [])
        (root / "dashboard.toml").write_text('[[component]]\nname = "stub"\ncommand = ["python3", "skills/stub/stub.py"]\n')
        comps = discover(root, skills=skills)
        for c in comps:
            c.load()
        site = Site(comps)
        pages = []

        def get(path, s=None):
            code, h = respond(s or site, path)
            pages.append(h)
            return code, h

        def chunk(h, ident):
            """The one card of a page that carries `ident`."""
            return next((x for x in re.split(r'(?=<(?:a|div) class="cd )', h) if f'>{ident}</span>' in x), "")

        # --- the home and the table
        code, h = respond(site, "/")
        expect("`/` goes to the home page the manifest names", code == 302 and h == "/stub/table")
        (skills / "plain").mkdir()
        (skills / "plain" / "plain.py").write_text(PLAIN)
        (skills / "plain" / "component.toml").write_text('command = ["python3", "plain.py"]\nbindings = "stub.toml"\n')
        (skills / "plain2").mkdir()
        (skills / "plain2" / "plain2.py").write_text(PLAIN.replace("/plain", "/plain2"))
        (skills / "plain2" / "component.toml").write_text('command = ["python3", "plain2.py"]\nbindings = "stub.toml"\n')
        by = {c.name: c for c in discover(root, skills=skills)}
        plain, plain2 = by["plain"].load(), by["plain2"].load()
        expect("`/` goes to the first mounted component that names a home, not to the first mounted",
               respond(Site([plain, comps[0]]), "/") == (302, "/stub/table"))
        def lone(home):
            return respond(types.SimpleNamespace(comps=[types.SimpleNamespace(manifest={"home": home}, mount="/lone")], home=lambda: ""), "/")
        expect("`/` goes only to a home that begins with one slash and holds no backslash: `//x`, `/\\x` and `x` are refused, the component's mount instead",
               lone("/lone/table") == (302, "/lone/table") and lone("/") == (302, "/")
               and all(lone(bad) == (302, "/lone") for bad in ("//evil.example", "/\\evil.example", "/a\\b", "evil.example", "https://evil.example/", "", 7)))
        expect("with no home named, `/` stays as it was: a lone component's mount, a home page for several",
               respond(Site([plain]), "/") == (302, "/plain") and respond(Site([plain, plain2]), "/")[1].count('<section class="panel">') == 2)
        code, h = get("/stub/table")
        names = [esc(n) for n in ("Ann's hand", "Bot's hand", "The goals", "The directions", "Ann's deck", "Bot's deck", "The common deck", "Piles")]
        expect("table view: the zones in the answer's order, each heading in the serif face with its first letter raised",
               code == 200 and all(n in h for n in names) and [h.index(n) for n in names] == sorted(h.index(n) for n in names)
               and h.count("<h2>") == 8 and '<h1 class="vh">Table</h1>' in h)
        expect("table view: a hand's cards, then a dashed empty place for each free one, and its note beside the heading",
               h.count('class="void"') == 1 and h.index('class="void"') > h.index("item-003") and '<span class="note">2 of 3</span>' in h
               and names[0] in h[h.index('<div class="hands">'):h.index(names[4])] and names[1] in h[h.index('<div class="hands">'):h.index(names[4])])
        hrow = h[h.index('<div class="hands">'):h.index('<div class="hands board">')]
        brow = h[h.index('<div class="hands board">'):h.index('<section class="zone sep">')]
        goals = h[h.index(names[2]):h.index(names[3])]
        expect("table view: the board's zones are a row of their own after the hands' and before the decks, the two sharing it, each a row of cards on their own faces with no dashed place and no stack, its note beside the heading",
               hrow.count("<section") == 2 and brow.count("<section") == 2 and brow.count("</section>") == 2 and h.count('<div class="hands">') == 1 and h.count('<div class="hands board">') == 1
               and names[2] in brow and names[3] in brow and names[0] not in brow and '<span class="note">1 open</span>' in goals
               and goals.count('<a class="cd ') == 1 and 'class="cd k-goal ' in goals and "item-006" in goals and 'class="void"' not in goals and 'class="stack"' not in goals
               and h.index(names[1]) < h.index('<div class="hands board">') < h.index(names[2]) < h.index(names[3]) < h.index(names[4]))
        expect("table view: an empty board zone is its heading with its note and no cards, no stack and no dashed place",
               names[3] + '</h2><span class="note">none set</span></div></section>' in h and 'class="void"' not in h[h.index(names[3]):h.index(names[4])])
        _site = Site([])
        _zones = [{"kind": "hand", "title": "a hand", "count": 1, "note": "1 held", "room": 1, "find": {}, "cards": [{"id": "item-001", "type": "idea", "state": "open", "title": "one"}]},
                  {"kind": "shelf", "title": "a shelf", "count": 1, "note": "1 shelved", "room": 1, "find": {}, "cards": [{"id": "item-002", "type": "goal", "state": "open", "title": "two"}]}]
        shelf = _site.view_table(types.SimpleNamespace(manifest={"card": {"id": "id", "title": "title", "label": "type", "faces": FACES}}), {"field": "zones"}, {"zones": _zones}, "T")
        expect("table view: a zone of a kind the dashboard does not know is laid as a hand is, its free places included, in the hands' row",
               shelf.count('<div class="hands">') == 1 and 'hands board' not in shelf and shelf.count('class="void"') == 2 and "A shelf" in shelf and '<span class="note">1 shelved</span>' in shelf)
        expect("table view: a deck is a stack of backs carrying the count, the note under it and The whole deck, then its cards face up",
               h.count('class="stack"') == 2 and "<b>7</b><span>cards</span>" in h and '<span class="note">3 ready</span>' in h
               and 'href="/stub/list?deck=common">The whole deck</a>' in h and h.index('class="stack"') < h.index("item-005"))
        expect("table view: an empty deck is its heading and `no cards`, with no stack", names[4] + "</h2><span class=\"note\">no cards</span>" in h)
        expect("table view: a zone's link is the route's list path with the zone's find as its query, a flag as `1`",
               'href="/stub/list?held=1&amp;owner=bot">The whole deck</a>' in h)
        expect("table view: the piles are one row under a heading Piles, each a small stack with its count and its note and a link to its list",
               h.count('class="pile"') == 2 and 'href="/stub/list?pile=discard"' in h and '<span class="pb">3</span>' in h
               and "2 done, 1 answered" in h and h.index("Piles") > h.index("The common deck") and h.count('class="piles"') == 1)
        # --- the card's face

        def empties(c):
            """The gems and bars of a card drawn as outlines only, the sign of its band not among them."""
            return len(re.findall(r'fill="none" stroke="#(?!ffffff)', c))
        code, h = get("/stub/list")
        expect("list view: cards are laid where the manifest has `card`, each the whole card one link to its record",
               code == 200 and h.count('<a class="cd ') == 9 and 'href="/stub/r/item-001"' in h and "<table" not in h)
        expect("list view: paging is as it was, a next link from the answer's next", "from=5" in h and "9 card(s)" in h)
        expect("the face: one for each of the seven kinds, each with its sign, and a neutral grey one with no sign for a kind the dashboard does not know",
               all(f"k-{k}" in h for k in FACES) and h.count('<svg aria-hidden="true" width="16"') == 8 and h.count("k-x ") == 1
               and "k-x" in chunk(h, "item-009") and "<svg aria-hidden" not in chunk(h, "item-009"))
        expect("the face: the kind's word in bold with the tags after it, the rank in a white pip where there is one",
               "<b>Idea</b><i>t1 · t2</i>" in chunk(h, "item-001") and '<span class="pip" title="its place on the ranked list">1</span>' in chunk(h, "item-001")
               and "pip" not in chunk(h, "item-002") and "<b>Gizmo</b>" in chunk(h, "item-009"))
        expect("the face: the frame follows the value, none judged flat, the lowest plain, a middle silver, the highest gold",
               'class="cd k-idea fg"' in chunk(h, "item-001") and 'class="cd k-question fs"' in chunk(h, "item-002")
               and 'class="cd k-task f1 wt"' in chunk(h, "item-003") and 'class="cd k-task f0 wt"' in chunk(h, "item-004")
               and 'class="cd k-finding f0"' in chunk(h, "item-005"))
        expect("the face: value as three gems and effort as three bars filled to their levels, the ones not judged empty outlines, an idea showing value alone",
               'aria-label="value: high"' in chunk(h, "item-001") and "effort" not in chunk(h, "item-001") and empties(chunk(h, "item-001")) == 0
               and 'aria-label="effort: large"' in chunk(h, "item-002") and empties(chunk(h, "item-002")) == 1
               and empties(chunk(h, "item-003")) == 4 and empties(chunk(h, "item-004")) == 3 + 1
               and 'aria-label="value: not judged"' in chunk(h, "item-004") and "aria-label" not in chunk(h, "item-005"))
        expect("the face: a parked or a blocked card lies on greyer paper, a held one does not, and the standing is a badge",
               'wt"' in chunk(h, "item-003") and 'wt"' in chunk(h, "item-004") and 'wt"' not in chunk(h, "item-001")
               and '<span class="badge s-held">held</span>' in chunk(h, "item-001") and '<span class="badge s-done">done</span>' in chunk(h, "item-002")
               and "--wait:#e0ddd3" in CSS and ".cd.wt{--p:var(--wait)}" in CSS and "opacity" not in CSS)
        expect("the face: `no summary yet` where the card has a summary path and the record's is empty, the summary otherwise",
               "no summary yet" in chunk(h, "item-002") and "no summary yet" not in chunk(h, "item-001") and "a parked one" in chunk(h, "item-003"))
        expect("the face: no `no summary yet` where the component's card has no summary path",
               "no summary yet" not in card_html({"id": "id", "title": "title"}, {"id": "k", "title": "t"}))
        expect("the face: the first two lines at the box's foot and no third; the place after the badge",
               "<b>serves</b> Goal one" in chunk(h, "item-001") and "<b>due</b> 2026-01-01" in chunk(h, "item-001")
               and "never shown" not in chunk(h, "item-001") and '<span class="pl">ann, 3 days</span>' in chunk(h, "item-001"))
        expect("the face: a title and a summary with `<` and `&` are escaped, in the card as on the record's page",
               "A &lt;b&gt; &amp; the first" in chunk(h, "item-001") and "if a &lt; b &amp; c &gt; d" in chunk(h, "item-001") and "A <b>" not in h)
        expect("the face: a card's text holds no link of its own, since the whole card is one", chunk(h, "item-004").count("<a ") == 1)
        expect("the face: the title is whole and the summary folds to six lines in the stylesheet, nothing unfolds or moves",
               "-webkit-line-clamp:6" in CSS and "overflow-wrap:anywhere" in CSS and "animation" not in CSS and "transition" not in CSS and "hover" not in CSS.replace("a.id:hover", ""))
        c5 = {"id": "id", "title": "title", "label": "type", "face": "task", "meters": [{"label": "value", "field": "v", "scale": list("abcde"), "frame": True}]}
        sets = [(card_html(c5, {"id": "x", "title": "t", "type": "k", "v": w}), w) for w in ("a", "b", "c", "d", "e", None)]
        expect("the value's look for a scale of another length: the first level plain, the last gold, those between silver, the gems in proportion",
               [re.search(r'class="cd [\w-]+ (f\w)', s).group(1) for s, _ in sets] == ["f1", "fs", "fs", "fs", "fg", "f0"]
               and [empties(s) for s, _ in sets] == [2, 2, 1, 1, 0, 3]
               and [frame_of(i, 2) for i in (0, 1, 2)] == ["f0", "f1", "fg"] and [filled(i, 2) for i in (0, 1, 2)] == [0, 1, 3])
        cm = {"id": "id", "title": "title", "label": "type", "faces": {"a": "mystery", "b": "work"}}
        expect("the face: a face the dashboard does not know is neutral, `face` gives one face to every record, no label gives no word",
               "k-x" in card_html(cm, {"id": "1", "title": "t", "type": "a"}) and "k-work" in card_html(dict(cm, face="work"), {"id": "1", "title": "t", "type": "a"})
               and "<b>Work</b>" in card_html({"id": "id", "title": "title", "face": "work"}, {"id": "1", "title": "t"}))
        expect("the look: the ground follows prefers-color-scheme, the paper is the same in both, and the frames' gradients are as given",
               "prefers-color-scheme:dark" in CSS and "--bg:#22332d" in CSS and "--bg:#e4e8df" in CSS and "--paper:#f8f5ee" in CSS
               and "linear-gradient(135deg,#7b848e 0%,#f2f5f7 22%,#9aa3ad 45%,#e6eaee 68%,#6f7882 100%)" in CSS
               and "linear-gradient(135deg,#8a6410 0%,#f6dc86 22%,#b98a1c 45%,#fbeeb4 68%,#8a6410 100%)" in CSS
               and "padding-box,var(--frame) border-box" in CSS and "border-radius:10px" in CSS and "max-width:1500px" in CSS and "#243242" in CSS)
        ground = {"#eef1ea": "#22332d", "#bcc6bd": "#22332d", "#1d1c1a": "#e4e8df", "#4f4d47": "#e4e8df"}
        paper = [("#1d1c1a", "#f8f5ee"), ("#5a564d", "#f8f5ee"), ("#1d1c1a", "#e0ddd3"), ("#5a564d", "#e0ddd3"), ("#4a473f", "#e0ddd3"),
                 ("#1a5231", "#d6ecdd"), ("#1f4179", "#d7e3f6"), ("#5f4200", "#f4e3b5"), ("#7f2015", "#f4d5ce"), ("#44423d", "#e2dfd5"),
                 ("#ffffff", "#243242"), ("#1d1c1a", "#d9dee3"), ("#1d1c1a", "#cfd5db"), ("#1d1c1a", "#f1d687"), ("#1d1c1a", "#efd07a")]
        bands = [(k, "#ffffff") for k in ("#6a4c9c", "#2a5599", "#1d6b5c", "#9a3a2e", "#1f2a36", "#8a5a1c", "#4a5560", "#5b6068")]
        links = [("#9fc2ff", "#22332d"), ("#1c4a9a", "#e4e8df"), ("#1c4a9a", "#f8f5ee"), ("#8fd9a8", "#22332d"), ("#1a5231", "#e4e8df"),
                 ("#ffa59b", "#22332d"), ("#8a1c12", "#e4e8df")]
        everything = list(ground.items()) + paper + bands + links
        expect("the look: text is 4.5:1 or better on its ground in every pair of the palette, white on every band included, each colour in the stylesheet",
               all(contrast(a, b) >= 4.5 for a, b in everything) and all(x in CSS for pair in everything for x in pair if x != "#ffffff")
               and all(k in CSS for k, _ in bands))
        # --- the look, each value held where it is used: the rule the card or the page takes, not the string anywhere in the stylesheet
        rules = css_rules(CSS)
        lt, dark = css_of(rules, ":root"), css_of(rules, ":root", "@media (prefers-color-scheme:dark)")
        sheet = {k: css_of(rules, k) for k in (".cd", ".cd .band", ".cd .pip", ".cd .plate", ".cd .ttl", ".cd .tl", ".cd .sum", ".cd .nos", ".cd .ln b", ".cd .ms",
                                               ".cd .cid", ".back", ".back.b1", ".back b", ".pile .pb", ".mini", ".badge", "main", "header .in", "body", "a.id", "h1", "h2",
                                               ".s-ready", ".s-held", ".s-parked", ".s-blocked", ".void", ".stack", ".cd.wt")}
        expect("the look, the ground: dark `#22332d` with text `#eef1ea` and muted `#bcc6bd` under prefers-color-scheme, light `#e4e8df`, `#1d1c1a`, `#4f4d47` otherwise, the body on it",
               (dark.get("--bg"), dark.get("--fg"), dark.get("--mut")) == ("#22332d", "#eef1ea", "#bcc6bd")
               and (lt.get("--bg"), lt.get("--fg"), lt.get("--mut")) == ("#e4e8df", "#1d1c1a", "#4f4d47")
               and sheet["body"].get("background") == "var(--bg)" and sheet["body"].get("color") == "var(--fg)" and "system-ui" in sheet["body"].get("font", ""))
        expect("the look, the page: up to 1500px wide, the header's row and the main alike",
               sheet["main"].get("max-width") == "1500px" and sheet["header .in"].get("max-width") == "1500px")
        expect("the look, the paper: `#f8f5ee`, a waiting card's `#e0ddd3`, hairlines `#cfcabd`, text `#1d1c1a`, labels `#5a564d`, the same in both settings",
               (lt.get("--paper"), lt.get("--wait"), lt.get("--hair"), lt.get("--ink"), lt.get("--lab"))
               == ("#f8f5ee", "#e0ddd3", "#cfcabd", "#1d1c1a", "#5a564d") and not {"--paper", "--wait", "--hair", "--ink", "--lab"} & set(dark)
               and style_of(rules, chunk(h, "item-001")).get("--p") == "var(--paper)" and style_of(rules, chunk(h, "item-003")).get("--p") == "var(--wait)"
               and sheet[".cd"].get("color") == "var(--ink)" and sheet[".cd"].get("--p") == "var(--paper)"
               and sheet[".cd .tl"].get("border-top") == "1px solid var(--hair)" and sheet[".cd .tl"].get("border-bottom") == "1px solid var(--hair)"
               and all(sheet[k].get("color") == "var(--lab)" for k in (".cd .nos", ".cd .ln b", ".cd .ms"))
               and sheet[".mini"].get("background") == "var(--paper)" and sheet[".mini"].get("border") == "1px solid #b5b1a6")
        expect("the look, the type: the serif `Georgia, 'Iowan Old Style', 'Times New Roman', serif` for a card's title, the headings and the counts, the monospace for ids",
               lt.get("--serif") == "Georgia,'Iowan Old Style','Times New Roman',serif" and "var(--serif)" in sheet[".cd .ttl"].get("font", "")
               and "var(--serif)" in sheet["h1"].get("font", "") and "var(--serif)" in sheet["h2"].get("font", "") and "var(--serif)" in sheet[".back b"].get("font", "")
               and "var(--serif)" in sheet[".pile .pb"].get("font", "") and "monospace" in lt.get("--mono", "")
               and "var(--mono)" in sheet[".cd .cid"].get("font", "") and sheet["a.id"].get("font-family") == "var(--mono)"
               and '<span class="plate"><span class="ttl">' in chunk(h, "item-001") and 'class="cid"' in chunk(h, "item-001"))
        expect("the look, the card: 240px wide and at least 336px high, a transparent border of the frame's width over its gradient, the lines, the glow and the shadow, corners round",
               sheet[".cd"].get("width") == "240px" and sheet[".cd"].get("min-height") == "336px" and sheet[".cd"].get("border-radius") == "10px"
               and sheet[".cd"].get("border") == "var(--w) solid transparent"
               and sheet[".cd"].get("background") == "linear-gradient(var(--p),var(--p)) padding-box,var(--frame) border-box"
               and sheet[".cd"].get("box-shadow") == "var(--lines),var(--glow),var(--shadow)" and sheet[".cd"].get("overflow") == "hidden"
               and sheet[".cd .plate"].get("background") == "var(--plate)" and sheet[".void"].get("width") == "240px" and sheet[".void"].get("height") == "336px")
        gold, silver = style_of(rules, chunk(h, "item-001")), style_of(rules, chunk(h, "item-002"))
        flat0, flat1 = style_of(rules, chunk(h, "item-005")), style_of(rules, chunk(h, "item-003"))
        expect("the look, a gold card (the highest level): a 6px frame of the gold gradient, its dark lines inside and outside it, the gold glow at 16px, the gold plate",
               gold.get("--w") == "6px"
               and gold.get("--frame") == "linear-gradient(135deg,#8a6410 0%,#f6dc86 22%,#b98a1c 45%,#fbeeb4 68%,#8a6410 100%)"
               and gold.get("--lines") == "inset 0 0 0 1px #6e4f08,0 0 0 1px #6e4f08" and gold.get("--glow") == "0 0 16px rgba(244,205,96,.6)"
               and gold.get("--plate") == "linear-gradient(115deg,#f1d687 0%,#fff6d8 38%,#efd07a 72%,#fbeebb 100%)")
        expect("the look, a silver card (a middle level): a 4px frame of the silver gradient, its lines, the silver glow at 12px, the silver plate",
               silver.get("--w") == "4px"
               and silver.get("--frame") == "linear-gradient(135deg,#7b848e 0%,#f2f5f7 22%,#9aa3ad 45%,#e6eaee 68%,#6f7882 100%)"
               and silver.get("--lines") == "inset 0 0 0 1px #5b636c,0 0 0 1px #5b636c" and silver.get("--glow") == "0 0 12px rgba(226,232,238,.45)"
               and silver.get("--plate") == "linear-gradient(115deg,#d9dee3 0%,#f7f8fa 40%,#cfd5db 75%,#eceff2 100%)")
        expect("the look, a card not judged and one of the lowest level: a 1px flat frame (`#b5b1a6`, `#8e8a7f`), no lines, no glow, no plate",
               all(x.get("--w") == "1px" and x.get("--lines") == "0 0 0 0 transparent" and x.get("--glow") == "0 0 0 0 transparent" and x.get("--plate") == "transparent"
                   for x in (flat0, flat1))
               and flat0.get("--frame") == "linear-gradient(#b5b1a6,#b5b1a6)" and flat1.get("--frame") == "linear-gradient(#8e8a7f,#8e8a7f)")
        gems = lambda c: re.findall(r'<path d="M\d+ 1l5 5-5 5-5-5z" fill="([^"]*)" stroke="([^"]*)"', c)
        expect("the look, the gems: gold `#a37410` all three, silver `#5f6973` two of three, the lowest `#6f6b61` one, a value not judged three grey outlines",
               gems(chunk(h, "item-001")) == [("#a37410", "#a37410")] * 3
               and gems(chunk(h, "item-002")) == [("#5f6973", "#5f6973")] * 2 + [("none", "#5f6973")]
               and gems(chunk(h, "item-003")) == [("#6f6b61", "#6f6b61")] + [("none", "#6f6b61")] * 2
               and gems(chunk(h, "item-004")) == [("none", "#8b877c")] * 3)
        expect("the look, the band: white on the kind's colour, the rank in a white pip with dark text, the id in monospace; the neutral band `#5b6068`",
               sheet[".cd .band"].get("color") == "#fff" and sheet[".cd .band"].get("background") == "var(--band)"
               and sheet[".cd .pip"].get("background") == "#fff" and sheet[".cd .pip"].get("color") == "#1d1c1a"
               and sheet[".cd"].get("--band") == "#5b6068" and style_of(rules, card_html({"id": "id", "title": "title"}, {"id": "k", "title": "t"})).get("--band") == "#5b6068"
               and '<span class="pip"' in chunk(h, "item-001"))
        kinds = {"idea": "#6a4c9c", "question": "#2a5599", "task": "#1d6b5c", "finding": "#9a3a2e", "goal": "#1f2a36", "direction": "#8a5a1c", "work": "#4a5560"}
        expect("the look, the seven faces: each kind's band colour on its card and on its small card",
               all(style_of(rules, card_html({"id": "id", "title": "title", "face": k}, {"id": "k", "title": "t"})).get("--band") == v
                   and css_of(rules, f".mini.k-{k} .mb").get("--band") == v for k, v in kinds.items()) and list(kinds) == list(FACES))
        expect("the look, the summary's fold: six lines, then an ellipsis, in the box; the title whole",
               sheet[".cd .sum"].get("display") == "-webkit-box" and sheet[".cd .sum"].get("-webkit-box-orient") == "vertical"
               and sheet[".cd .sum"].get("-webkit-line-clamp") == "6" and sheet[".cd .sum"].get("line-clamp") == "6" and sheet[".cd .sum"].get("overflow") == "hidden"
               and '<span class="sum">' in chunk(h, "item-001") and "line-clamp" not in sheet[".cd .ttl"] and "overflow" not in sheet[".cd .ttl"]
               and sheet[".cd .ttl"].get("overflow-wrap") == "anywhere")
        pairs = {"ready": ("#d6ecdd", "#1a5231"), "held": ("#d7e3f6", "#1f4179"), "parked": ("#f4e3b5", "#5f4200"), "blocked": ("#f4d5ce", "#7f2015"), "done": ("#e2dfd5", "#44423d")}
        got = {}
        for w in pairs:
            c = card_html({"id": "id", "title": "title", "standing": ["standing"]}, {"id": "k", "title": "t", "standing": w})
            d = dict(sheet[".badge"], **css_of(rules, f".s-{w}"))
            got[w] = (d.get("background"), d.get("color")) if f'<span class="badge s-{w}">{w}</span>' in c else None
        expect("the look, the five badge pairs: ready, held, parked, blocked, and any other word, each on its card", got == pairs)
        _, tbl = get("/stub/table")
        back = css_of(rules, ".back")
        expect("the look, a card's back: `#243242` with an inset keyline `#8fa0b3`, the count in the serif at its centre; the piles' small stack the same",
               'class="back b1"><b>7</b>' in tbl and back.get("background") == "#243242" and back.get("border") == "1px solid #8fa0b3"
               and "inset 0 0 0 5px #243242,inset 0 0 0 6px #8fa0b3" == sheet[".back.b1"].get("box-shadow") and sheet[".back.b1"].get("color") == "#fff"
               and sheet[".back.b1"].get("justify-content") == "center" and sheet[".back.b1"].get("align-items") == "center"
               and sheet[".pile .pb"].get("background") == "#243242" and sheet[".pile .pb"].get("border") == "1px solid #8fa0b3" and 'class="pb"' in tbl)
        # --- filters, record, the other views
        code, h = get("/stub/list?state=open&ranked=1&held=1")
        expect("list view: query mapped to flags, the card of the first record only, the filter form keeping what was asked",
               code == 200 and h.count('<a class="cd ') == 1 and "item-002" not in h and '<input type="checkbox" name="ranked" value="1" checked>' in h
               and '<input type="checkbox" name="held" value="1" checked>' in h)
        expect("list view: a `params` entry with `choices` is a select with any, the one asked for selected, the others a text input",
               '<select name="state"><option value="">any</option><option value="open" selected>open</option><option value="done">done</option></select>' in h
               and '<input type="text" name="tag" value="">' in h and '<input type="text" name="q" value="">' in h)
        code, h = get("/stub/list?state=--root%3D%2Ftmp")
        expect("a filter value that reads as a flag is refused, never passed", code == 400)
        code, h = get("/stub/list?q=words")
        expect("list view: words go to the command as positionals", code == 200 and "0 of 9" in h and "none" in h)
        code, h = get("/stub/r/item-001")
        expect("record view: the card at the left enlarged, beside it a paper panel with the title as its heading, the summary whole, the body and the fields",
               code == 200 and '<div class="big"><a class="cd k-idea fg"' in h and '<article class="panel article"><h1>A &lt;b&gt; &amp; the first</h1>' in h
               and "<p>if a &lt; b &amp; c &gt; d</p>" in h and 'href="/stub/r/item-002"' in h and h.index("<p>if a") < h.index("A body naming") < h.index('<dl class="dl">')
               and ".rec .big{zoom:1.6}" in CSS)
        dts = re.findall(r"<dt>([^<]*)</dt>", h)
        expect("record view: only the fields the face does not carry are under the body: not the title, the rank, the value, the place, the standing, the tags or a hidden one",
               dts == ["state", "label", "doi", "url", "secret"] and "</b>: hidden" not in h and "<b>n</b>: 3" in h and 'href="https://doi.org/10.1/x"' in h)
        expect("record view: a `refs` section is a row of small cards, each the band with the id and the link's field and the title under it, a link where the id leads somewhere",
               '<div class="mini k-goal"><span class="mb"><i>goal-0001</i><em>serves</em></span><span class="mt">Goal &amp; more</span></div>' in h
               and '<a class="mini k-task" href="/stub/r/item-002"><span class="mb"><i>item-002</i><em>references</em></span><span class="mt">second &lt;i&gt;</span></a>' in h)
        expect("record view: a `sites` section stays lines, and a javascript: address in a field or a body is text, never a link",
               "a.md:3" in h and "alert(1)" in h and not re.search(r'href="[^"]*script', h, re.I) and ('href="https://example.org/"' in h if _markdown else True))
        code, h = get("/stub/h/item-001")
        expect("record view: a heading field the route names heads the panel over the title, and `hide` still hides", "<h1>Label of one</h1>" in h and "<dt>label</dt>" not in h)
        code, h = get("/stub/r/item-999")
        expect("record view: a refused answer is a 404 with the component's words", code == 404 and "does not exist" in h)
        code, h = get("/stub")
        expect("markdown view: the text rendered, ids and cite keys linked by every pattern",
               code == 200 and 'href="/stub/r/item-001"' in h and 'href="/lib/jen1990#lemma"' in h and "<h1>Index</h1>" in h if _markdown else code == 200 and 'href="/stub/r/item-001"' in h)
        code, h = get("/stub/lines")
        expect("lines view: the lines in a pre, linked", code == 200 and "<pre>" in h and 'href="/stub/r/item-002"' in h)
        code, h = get("/stub/tables")
        expect("tables view: one table per run", code == 200 and "<th>a</th>" in h and "<td>x</td>" in h)
        code, h = get("/stub/check")
        expect("check view: the verdict, problems, warnings and coverage", code == 200 and "1 problem" in h and "V1" in h and "w1" in h and "kinds" in h)
        expect("the header marks the entry of the page being read", 'aria-current="page">Check</a>' in h and h.count('aria-current="page"') == 1
               and 'aria-current="page">Open</a>' in get("/stub/list?state=open")[1])
        code, h = respond(site, "/stub/nowhere")
        expect("an unrouted path under a mount is a 404", code == 404)
        code, h = respond(site, "/elsewhere")
        expect("a path under no mount is a 404", code == 404)
        # --- a component with no `card` renders as it did
        site3 = Site([plain])
        code, h = get("/plain/list?state=done", site3)
        expect("a component with no `card`: the list is the table of rows it had, the id column linked, a state badge",
               code == 200 and h.count("<tr>") == 2 and "<th>id</th>" in h and 'href="/plain/r/item-002"' in h and "s-done" in h and "class=\"cd" not in h)
        code, h = get("/plain/list", site3)
        expect("a component with no `card`: paging as it was, and its `choices` still a select", "from=5" in h and "9 row(s)" in h and '<select name="state">' in h)
        code, h = get("/plain/r/item-001", site3)
        expect("a component with no `card`: the record is a key-value table under the title and its state, the summary one more field of it, refs small cards",
               code == 200 and "<br>A &lt;b&gt; &amp; the first</h1>" in h and "<th>summary</th><td>if a &lt; b &amp; c &gt; d</td>" in h
               and "<th>title</th>" not in h and '<table class="kv">' in h and 'class="rec"' not in h and 'class="mini' in h and "</b>: hidden" not in h)
        code, h = get("/plain/table", site3)
        expect("a component with no `card` but a `table` route lays its zones on a neutral face from `id` and `title`", code == 200 and "k-x" in h and "The whole deck" in h)
        expect("no page holds a script, a stylesheet or an image fetched from another host",
               all(not re.search(r"<script|<link|<img|@import|url\(|src=|<iframe", p) for p in pages) and len(pages) > 15)
        comps2 = [Component("stub", comps[0].command, root).load(), Component("other", comps[0].command, root).load()]
        expect("two components answering one mount: the first is kept", [c.name for c in first_per_mount(comps2)] == ["stub"])
    print(f"dashboard selftest: {'OK' if not failures else str(len(failures)) + ' FAILED: ' + '; '.join(failures)}")
    return 0 if not failures else 1


def main():
    """The command line; a crash exits 2, could not run, never 1, which says problems were found."""
    try:
        return _main()
    except Exception:
        traceback.print_exc()
        print("dashboard: could not run (the error above)", file=sys.stderr)
        return 2


def _main():
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(prog="dashboard", description=__doc__.splitlines()[0])
    ap.add_argument("--root", help="the project root (default: found above the cwd by its bindings files)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--allow-host", action="append", default=[], metavar="NAME",
                    help="another name the server answers to, as a proxy or a tunnel calls it (repeatable)")
    ap.add_argument("--component", action="append", nargs="+", metavar="CMD", help="mount a command by hand (repeatable)")
    ap.add_argument("--list", action="store_true", help="print what would be mounted and exit")
    a = ap.parse_args()
    try:
        root = Path(a.root).resolve() if a.root else find_root(os.getcwd())
        comps = discover(root, a.component or ())
        if not comps:
            raise Refused(f"nothing to mount at {root}: no dashboard.toml, no component beside this skill with its bindings file, no flow or library on PATH")
        comps = first_per_mount([c.load() for c in comps])
    except Refused as e:
        print(f"dashboard: {e}", file=sys.stderr)
        return 2
    for c in comps:
        print(f"dashboard: {c.name} at {c.mount}  ({' '.join(c.command)})")
    if a.list:
        return 0
    site = Site(comps)
    host = a.host.strip("[]")  # `[::1]` and `::1` alike, so the loopback's Host check holds for both
    server = ThreadingHTTPServer
    if ":" in host:
        class server(ThreadingHTTPServer):
            address_family = socket.AF_INET6
    try:
        srv = server((host, a.port), make_handler(site, host, a.allow_host))
    except OSError as e:  # the port taken, the address not this machine's
        print(f"dashboard: cannot serve on {a.host} port {a.port}: {e}", file=sys.stderr)
        return 2
    print(f"dashboard: {root} at http://{f'[{host}]' if ':' in host else host}:{a.port}/  (Ctrl-C stops)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
