#!/usr/bin/env python3
"""release — cut a release of research-kit on a clean `main`, locally, pushing nothing.

    python3 tools/release.py X.Y.Z [--date YYYY-MM-DD] [--dry-run]

It writes X.Y.Z into every version field (both manifests of each plugin, every skill's
`metadata.version`, `pyproject.toml`), turns the changelog's `## Unreleased` heading into
`## vX.Y.Z — DATE` (today by default), runs `tests/run.py`, commits and tags `vX.Y.Z` (annotated),
then opens a fresh `## Unreleased` in a second commit, so the tag's changelog, which the website
publishes, carries no empty heading.  A failed test restores the files and commits nothing.
It refuses unless the tree is clean, the branch is `main`, the tag is new, the version is above
the changelog's last release, and `## Unreleased` has something under it.
The push is printed, not run: `git push --atomic origin main vX.Y.Z` sends both commits and the
tag or neither, and the tag starts `.github/workflows/release.yml`.  `--dry-run` prints what
would change and writes nothing.
"""

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
RELEASED = re.compile(r"^## v(\d+\.\d+\.\d+) — (\d{4}-\d{2}-\d{2})$", re.M)
UNRELEASED = "## Unreleased\n"


class Refused(Exception):
    pass


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode:
        raise Refused(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def version_fields():
    """Every file that carries the version, with the pattern whose one match is it."""
    out = [(ROOT / "pyproject.toml", re.compile(r'^(version = ")([^"]+)(")', re.M))]
    for pl in sorted((ROOT / "plugins").iterdir()):
        for manifest in (pl / ".claude-plugin/plugin.json", pl / "plugin.json"):
            out.append((manifest, re.compile(r'^(  "version": ")([^"]+)(")', re.M)))
        for skill in sorted(pl.glob("skills/*/SKILL.md")):
            out.append((skill, re.compile(r'^(  version: ")([^"]+)(")', re.M)))
    return out


def bumped(version):
    """Each version file's new text, refusing a file whose version is not found exactly once."""
    out = {}
    for path, rx in version_fields():
        text = path.read_text(encoding="utf-8")
        new, n = rx.subn(lambda m: m.group(1) + version + m.group(3), text)
        if n != 1:
            raise Refused(f"{path.relative_to(ROOT)}: {n} version fields where one was expected")
        out[path] = new
    return out


def released_changelog(version, date):
    text = CHANGELOG.read_text(encoding="utf-8")
    head, sep, rest = text.partition(UNRELEASED)
    if not sep:
        raise Refused("CHANGELOG.md has no `## Unreleased` heading to release")
    body = rest.split("\n## ", 1)[0]
    if not body.strip():
        raise Refused("`## Unreleased` is empty: a release needs its notes")
    last = RELEASED.search(text)
    if last and tuple(map(int, last.group(1).split("."))) >= tuple(map(int, version.split("."))):
        raise Refused(f"v{version} is not above the last release, v{last.group(1)}")
    return head + f"## v{version} — {date}\n" + rest


def main():
    ap = argparse.ArgumentParser(prog="release", description=__doc__.splitlines()[0])
    ap.add_argument("version", help="X.Y.Z, without the v")
    ap.add_argument("--date", default=datetime.date.today().isoformat(), help="the release date (default: today)")
    ap.add_argument("--dry-run", action="store_true", help="print what would change and write nothing")
    a = ap.parse_args()
    tag = f"v{a.version}"
    try:
        if not SEMVER.match(a.version):
            raise Refused(f"{a.version!r} is not X.Y.Z")
        datetime.date.fromisoformat(a.date)
        if git("rev-parse", "--abbrev-ref", "HEAD") != "main":
            raise Refused("not on main")
        if git("status", "--porcelain"):
            raise Refused("the working tree is not clean; commit or stash first")
        if git("rev-parse", "-q", "--verify", f"refs/tags/{tag}", check=False):
            raise Refused(f"tag {tag} exists")
        files = bumped(a.version)
        files[CHANGELOG] = released_changelog(a.version, a.date)
    except (Refused, ValueError) as e:
        print(f"release: refused — {e}", file=sys.stderr)
        return 1
    changed = [p for p, t in files.items() if t != p.read_text(encoding="utf-8")]
    print(f"release: {tag} — {a.date}; {len(changed)} file(s) change:")
    for p in changed:
        print(f"  {p.relative_to(ROOT)}")
    if a.dry_run:
        return 0
    for p, t in files.items():
        p.write_text(t, encoding="utf-8")
    print("release: running tests/run.py")
    r = subprocess.run([sys.executable, str(ROOT / "tests/run.py")], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        git("checkout", "--", *[str(p.relative_to(ROOT)) for p in changed])
        print("\n".join(ln for ln in r.stdout.splitlines() if "BAD" in ln) or r.stdout[-2000:] + r.stderr[-2000:])
        print("release: the tests failed; the files are restored and nothing is committed", file=sys.stderr)
        return 1
    git("commit", "-q", "-am", f"release: {tag}")
    git("tag", "-a", tag, "-m", tag)
    text = CHANGELOG.read_text(encoding="utf-8")
    CHANGELOG.write_text(text.replace(f"## {tag} — ", UNRELEASED + "\n" + f"## {tag} — ", 1), encoding="utf-8")
    git("commit", "-q", "-am", "chore: open the changelog's Unreleased section")
    print(f"release: committed and tagged {tag}, then opened `## Unreleased`; to publish:\n"
          f"  git push --atomic origin main {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
