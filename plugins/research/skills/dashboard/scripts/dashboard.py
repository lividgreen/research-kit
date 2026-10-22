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

Views: `markdown` (a field rendered as Markdown), `lines` (a list of lines), `list` (a filterable
table of `records`, the query string mapped to the command's flags, paged by the answer's `next`),
`record` (one answer's fields, body and sections), `tables` (several answers, one table each) and
`check` (problems, warnings, coverage).  Standard library only; Markdown bodies use the
`markdown` package when it is installed and fall back to paragraphs otherwise.  Binds to
localhost by default and writes nothing.  `--selftest` mounts a stub component and renders
every view.
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
import tomllib
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

try:
    import markdown as _markdown
except ImportError:  # pragma: no cover
    _markdown = None

KNOWN = {"flow": "flow.toml", "library": "library.toml"}  # the commands found on PATH, and their bindings
TIMEOUT = 60


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

    def _link(self, path, m):
        groups = [m.group(0)] + [g if g is not None else "" for g in m.groups()]
        href = path
        for i, g in enumerate(groups):
            href = href.replace("{%d}" % i, quote(g, safe=""))
        href = re.sub(r"#$", "", href)
        return f'<a class="id" href="{esc(href)}">{esc(m.group(0))}</a>'

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
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e3e1db;--card:#fff;--acc:#2f5fb3;--code:#f1efe9;
--g:#2e7d4f;--y:#9a6b00;--r:#b3261e;--b:#2f5fb3;--p:#7a4fb3;--n:#77756f}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#e8e6e1;--mut:#9c9a94;--line:#2e2d2a;--card:#1e1e1c;
--acc:#8fb0ec;--code:#2a2926;--g:#6cc28f;--y:#e0b451;--r:#ef7b72;--b:#8fb0ec;--p:#bb9af0;--n:#9c9a94}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
header{border-bottom:1px solid var(--line);background:var(--card);position:sticky;top:0;z-index:1}
header .in{max-width:1100px;margin:0 auto;padding:10px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header b{font-weight:650;margin-right:6px}
header a{color:var(--fg);text-decoration:none;opacity:.8}header a:hover{opacity:1;color:var(--acc)}
header .sep{color:var(--line)}
input,select,button{font:inherit;padding:4px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
main{max-width:1100px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:1.45em;line-height:1.3;margin:.2em 0 .6em}h2{font-size:1.1em;margin:1.8em 0 .6em}
h3{font-size:1em;margin:1.2em 0 .4em;color:var(--mut)}
a{color:var(--acc)}a.id{font-family:ui-monospace,monospace;font-size:.9em;white-space:nowrap;text-decoration:none}
a.id:hover{text-decoration:underline}
code{font-family:ui-monospace,monospace;font-size:.88em;background:var(--code);padding:1px 4px;border-radius:4px}
pre{background:var(--code);padding:10px;border-radius:6px;overflow-x:auto;white-space:pre-wrap}pre code{padding:0}
.mut{color:var(--mut)}.small{font-size:.87em}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px}
.card h2{margin-top:.2em}
ul.recs{list-style:none;padding:0;margin:0}ul.recs li{padding:6px 0;border-top:1px solid var(--line)}
ul.recs li:first-child{border-top:0}
table{border-collapse:collapse;width:100%}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.82em;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);font-weight:600}
table.kv th{width:10em;text-transform:none;letter-spacing:0;font-size:.9em}
.badge{display:inline-block;font-size:.76em;font-weight:600;padding:1px 7px;border-radius:99px;
border:1px solid currentColor;white-space:nowrap;vertical-align:1px}
.s-open,.s-ready,.s-verified,.s-lean-verified,.s-full,.s-registered{color:var(--g)}
.s-active,.s-decomposed,.s-stated,.s-proven,.s-parts{color:var(--b)}
.s-empirical,.s-parked,.s-skimmed{color:var(--y)}.s-refuted,.s-abandoned,.s-unread,.s-excluded{color:var(--r)}
.s-done,.s-answered,.s-consumed{color:var(--p)}.s-type,.s-ungraded{color:var(--n)}
.body{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:4px 18px}
.body p{margin:.6em 0}.body h2{margin-top:1.2em}
.ok{color:var(--g)}.bad{color:var(--r)}
.filters{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
.table-wrap{overflow-x:auto}
@media (max-width:640px){header .in{gap:10px}}
"""


def badge(v):
    return f'<span class="badge s-{esc(str(v).lower())}">{esc(v)}</span>' if v not in (None, "") else ""


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


STATE_COLS = ("state", "status", "grade", "read.grade")


class Site:
    def __init__(self, comps):
        self.comps = comps
        self.R = Renderer(comps)
        nav = []
        for c in comps:
            if nav:
                nav.append('<span class="sep">|</span>')
            nav += [f'<a href="{esc(n["path"])}">{esc(n["label"])}</a>' for n in c.manifest.get("nav") or []]
        self.nav = "".join(nav)

    def page(self, title, body):
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · dashboard</title>
<style>{CSS}</style></head><body><header><div class="in"><b><a href="/">Dashboard</a></b>{self.nav}
</div></header><main>{body}</main></body></html>"""

    def home(self):
        cards = []
        for c in self.comps:
            m = c.manifest
            items = "".join(f'<li><a href="{esc(n["path"])}">{esc(n["label"])}</a></li>' for n in m.get("nav") or [])
            cards.append(f'<section class="card"><h2><a href="{esc(c.mount)}">{esc(m.get("title") or c.name)}</a></h2>'
                         f'<p class="mut small"><code>{esc(" ".join(Path(x).name if i == 0 else x for i, x in enumerate(c.command)))}</code></p>'
                         f'<ul class="recs">{items}</ul></section>')
        return self.page("Dashboard", f'<h1>Dashboard</h1><p class="mut small">{len(self.comps)} component(s) mounted; '
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
        for p in rt.get("params") or []:
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
        if view == "lines":
            lines = dig(ans, rt.get("field", "lines")) or []
            return 200, self.page(title, f"<h1>{esc(title)}</h1><pre>{self.R.autolink(esc(chr(10).join(map(str, lines))))}</pre>")
        text = dig(ans, rt.get("field", "text")) or ""
        return 200, self.page(title, f'<div class="body">{self.R.block(str(text))}</div>')

    def view_record(self, comp, rt, ans, title):
        R = self.R
        rec = dig(ans, rt.get("fields", "records.0")) or {}
        hide = set(rt.get("hide") or [])
        hrefs = rt.get("hrefs") or {}
        heading = rec.get(rt["heading"]) if rt.get("heading") else None
        rows = []
        for k, v in rec.items():
            if k in hide or k == "summary":
                continue
            if isinstance(v, dict):
                v = {sk: sv for sk, sv in v.items() if f"{k}.{sk}" not in hide}
            h = badge(v) if k in STATE_COLS and isinstance(v, str) else fmt(R, v, hrefs.get(k))
            if h:
                rows.append(f"<tr><th>{esc(k.replace('_', ' '))}</th><td>{h}</td></tr>")
        secs = []
        for sec in rt.get("sections") or []:
            data = dig(ans, sec["field"])
            if not data:
                continue
            kind = sec.get("as", "lines")
            if kind == "refs" and isinstance(data, dict):
                items = "".join(f"<li>{R.inline(x.get('id'))} <span class='small'>{R.inline(x.get('summary') or '')}</span>"
                                f" <span class='mut small'>via {esc(f.replace('_', ' '))}</span></li>"
                                for f, xs in data.items() for x in xs)
            elif kind == "sites":
                items = "".join(f"<li><code>{esc(x.get('path'))}:{esc(x.get('line'))}</code> <span class='small'>{R.inline((x.get('text') or '')[:260])}</span></li>"
                                for x in data)
            else:
                items = "".join(f"<li>{R.inline(x) if isinstance(x, str) else fmt(R, x)}</li>" for x in data)
            secs.append(f'<section class="card"><h2>{esc(sec.get("title") or sec["field"])}</h2><ul class="recs">{items}</ul></section>')
        body_md = dig(ans, rt["body"]) if rt.get("body") else None
        state = rec.get("state") or rec.get("status")
        if rec.get("summary"):
            head = f"<h1>{esc(title)} {badge(state)}<br>{R.inline(rec['summary'])}</h1>"
        else:
            head = f"<h1>{R.inline(heading) if heading else esc(title)}</h1>"
        body = (f'<p class="mut small">{esc(comp.manifest.get("title") or comp.name)} / <code>{esc(title)}</code></p>{head}'
                f'<div class="grid"><section class="card"><table class="kv">{"".join(rows)}</table></section>{"".join(secs)}</div>'
                + (f'<h2>Body</h2><div class="body">{R.block(str(body_md))}</div>' if body_md and str(body_md).strip() else ""))
        return self.page(title, body)

    def view_list(self, comp, rt, ans, title, query):
        R = self.R
        recs = ans.get("records") or []
        cols = rt.get("columns") or (sorted(recs[0].keys()) if recs else [])
        link = rt.get("link") or {}
        path = rt["path"]
        inputs = ""
        if rt.get("words"):
            inputs += f'<input name="{esc(rt["words"])}" size="30" placeholder="words" value="{esc(query.get(rt["words"], ""))}">'
        for p in rt.get("params") or []:
            if p == "from":
                continue
            inputs += f'<input name="{esc(p)}" size="10" placeholder="{esc(p)}" value="{esc(query.get(p, ""))}">'
        for f in rt.get("flags") or []:
            inputs += f'<label><input type="checkbox" name="{esc(f)}" value="1"{" checked" if query.get(f) else ""}> {esc(f)}</label>'
        form = f'<form class="filters" action="{esc(path)}">{inputs}<button>Filter</button></form>' if inputs else ""
        head = "".join(f"<th>{esc(c.split('.')[-1])}</th>" for c in cols)
        rows = []
        for r in recs:
            cells = []
            for c in cols:
                v = dig(r, c)
                if link and c == link["column"] and v is not None:
                    href = link["path"]
                    for k, x in r.items():
                        if isinstance(x, (str, int)) and not isinstance(x, bool):
                            href = href.replace("{%s}" % k, quote(str(x), safe=""))
                    cells.append(f'<td><a class="id" href="{esc(href)}">{esc(v)}</a></td>')
                elif c in STATE_COLS and isinstance(v, str):
                    cells.append(f"<td>{badge(v)}</td>")
                else:
                    cells.append(f"<td>{fmt(R, v)}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        total = ans.get("total", len(recs))
        meta = [f"{len(recs)} of {total}" if total != len(recs) else f"{len(recs)} row(s)"]
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
        body = (f"<h1>{esc(title)}</h1>{form}<p class='mut small'>{' · '.join(meta)}</p>"
                f"<div class='table-wrap'><table><tr>{head}</tr>{''.join(rows)}</table></div>")
        return self.page(title, body)

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
    if u.path == "/":
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
if cmd == "pages":
    out = {"ok": True, "pages": {"component": "stub", "title": "Stub", "mount": "/stub",
        "nav": [{"label": "Stub", "path": "/stub"}, {"label": "Check", "path": "/stub/check"}],
        "links": [{"pattern": r"\bitem-\d{3}\b", "path": "/stub/r/{0}"}, {"pattern": r"lib:([a-z0-9]+)(?:#([a-z0-9]+))?", "path": "/lib/{1}#{2}"}],
        "routes": [
            {"path": "/stub", "view": "markdown", "run": ["index"], "field": "text", "title": "Stub"},
            {"path": "/stub/list", "view": "list", "run": ["find"], "params": ["state"], "flags": ["ranked"], "words": "q",
             "columns": ["id", "state", "summary"], "link": {"column": "id", "path": "/stub/r/{id}"}, "title": "Items"},
            {"path": "/stub/r/{id}", "view": "record", "run": ["show", "{id}"], "title": "{id}", "fields": "records.0", "body": "body",
             "hide": ["id", "secret.path"], "hrefs": {"doi": "https://doi.org/{}", "url": "{}"},
             "sections": [{"field": "backlinks", "title": "Back", "as": "refs"}, {"field": "sites", "title": "Sites", "as": "sites"}]},
            {"path": "/stub/lines", "view": "lines", "run": ["state"], "field": "lines", "title": "Lines"},
            {"path": "/stub/tables", "view": "tables", "title": "Tables", "tables": [{"title": "T", "run": ["cands"], "field": "rows", "columns": ["a", "b"]}]},
            {"path": "/stub/check", "view": "check", "run": ["check"], "title": "Check"}]}}
elif cmd == "index":
    out = {"ok": True, "text": "# Index\n\nSee item-001 and lib:jen1990#lemma here.\n"}
elif cmd == "find":
    recs = [{"id": "item-001", "state": "open", "summary": "the first, citing lib:jen1990"}, {"id": "item-002", "state": "done", "summary": "second"}]
    if "--state" in args:
        recs = [r for r in recs if r["state"] == args[args.index("--state") + 1]]
    if "--ranked" in args:
        recs = recs[:1]
    if "words" in args:
        recs = []
    out = {"ok": True, "records": recs, "total": 2, "next": 2 if len(recs) == 2 else None}
elif cmd == "show":
    if args[1] != "item-001":
        out = {"ok": False, "problems": [{"msg": args[1] + " does not exist"}]}
    else:
        out = {"ok": True, "records": [{"id": "item-001", "state": "open", "summary": "the first", "doi": "10.1/x", "url": " JavaScript:alert(1)", "secret": {"path": "hidden", "n": 3}, "tags": ["t1"]}],
               "body": "A body naming item-002, [a script](java\tscript:alert(2)) and [a page](https://example.org/).\n", "backlinks": {"derived_from": [{"id": "item-002", "summary": "second"}]},
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
        code, h = respond(site, "/")
        expect("one component: the root redirects to its mount", code == 302 and h == "/stub")
        code, h = respond(site, "/stub")
        expect("markdown view: the text rendered, ids and cite keys linked by every pattern",
               code == 200 and 'href="/stub/r/item-001"' in h and 'href="/lib/jen1990#lemma"' in h and "<h1>Index</h1>" in h if _markdown else code == 200 and 'href="/stub/r/item-001"' in h)
        code, h = respond(site, "/stub/list?state=open&ranked=1")
        expect("list view: query mapped to flags, the id column linked, a state badge, paging shown",
               code == 200 and h.count("<tr>") == 2 and 'href="/stub/r/item-001"' in h and "s-open" in h and "item-002" not in h)
        code, h = respond(site, "/stub/list")
        expect("list view: a next link from the answer's next", 'from=2' in h and "2 row(s)" in h)
        code, h = respond(site, "/stub/list?state=--root%3D%2Ftmp")
        expect("a filter value that reads as a flag is refused, never passed", code == 400)
        code, h = respond(site, "/stub/list?q=words")
        expect("list view: words go to the command as positionals", code == 200 and "0 of 2" in h)
        code, h = respond(site, "/stub/r/item-001")
        expect("record view: fields with a hidden nested path, an href, the body linked, sections rendered",
               code == 200 and "hidden" not in h and "<b>n</b>: 3" in h and 'href="https://doi.org/10.1/x"' in h
               and 'href="/stub/r/item-002"' in h and "Back" in h and "a.md" in h and "the first" in h)
        expect("record view: a javascript: address in a field or a body is text, never a link",
               "alert(1)" in h and not re.search(r'href="[^"]*script', h, re.I)
               and ('href="https://example.org/"' in h if _markdown else True))
        code, h = respond(site, "/stub/r/item-999")
        expect("record view: a refused answer is a 404 with the component's words", code == 404 and "does not exist" in h)
        code, h = respond(site, "/stub/lines")
        expect("lines view: the lines in a pre, linked", code == 200 and "<pre>" in h and 'href="/stub/r/item-002"' in h)
        code, h = respond(site, "/stub/tables")
        expect("tables view: one table per run", code == 200 and "<th>a</th>" in h and "<td>x</td>" in h)
        code, h = respond(site, "/stub/check")
        expect("check view: the verdict, problems, warnings and coverage", code == 200 and "1 problem" in h and "V1" in h and "w1" in h and "kinds" in h)
        code, h = respond(site, "/stub/nowhere")
        expect("an unrouted path under a mount is a 404", code == 404)
        code, h = respond(site, "/elsewhere")
        expect("a path under no mount is a 404", code == 404)
        comps2 = [Component("stub", comps[0].command, root).load(), Component("other", comps[0].command, root).load()]
        site2 = Site(comps2)
        code, h = respond(site2, "/")
        expect("two components: a home page listing both", code == 200 and h.count("<section class=\"card\">") == 2)
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
