#!/usr/bin/env python3
"""The research plugin's Claude Code hook: a session's first flow command is refused once where the `flow` skill is not loaded.

`hooks.json` runs this script on three events, told apart by the `hook_event_name` of the JSON on the standard input:

  PostToolUse (matcher Skill) and UserPromptExpansion
      The `flow` skill was loaded, by the model's Skill call (`tool_input.skill`) or by a typed `/research:flow`
      (`command_name`): a marker file is written under ${CLAUDE_PLUGIN_DATA}, named from the session's id and, in a
      subagent, the agent's id as well.
  PreToolUse (matcher Bash)
      A command that runs the flow script, in a project whose `flow.toml` stands at or above the working directory:
      with the marker, nothing; with no marker and no earlier refusal, the call is denied once with the way out and the
      refusal is recorded; after that, nothing.  So one refusal per session at most, and a command taken for a flow
      command by mistake locks nobody out.

Anything unexpected (no data directory, input that is no JSON, an error) passes silently with exit 0, and a pass prints
nothing.  Claude Code only: the other agents run no hook of this plugin.  Standard library only, one file.
"""

import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

SKILL_NAMES = {"flow", "research:flow"}
KEEP_SECONDS = 3 * 24 * 3600  # a marker older than this is removed when a new one is written
REASON = "load the `flow` skill (research:flow), then run this again"
OPERATORS = set("();<>|&")
PREFIXES = {"command", "time", "exec", "nohup", "env", "sudo", "nice", "timeout"}  # words a command may start with before the interpreter
HEREDOC = re.compile(r"(<<-?\s*(['\"]?)(\w+)\2[^\n]*)\n.*?\n[ \t]*\3[ \t]*(?=\n|$)", re.S)


def ident(value):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(value))[:120]


def marker(kind, data):
    """The path of the session's marker of a kind (`loaded`, `refused`): the agent's own where the input names one."""
    name = f"{kind}--{ident(data['session_id'])}" + (f"--{ident(data['agent_id'])}" if data.get("agent_id") else "")
    return Path(os.environ["CLAUDE_PLUGIN_DATA"]) / name


def is_flow_skill(name):
    return isinstance(name, str) and name.strip().lstrip("/") in SKILL_NAMES


def runs_flow(segment):
    """Whether one simple command of a shell line runs the flow script: `python3 PATH/flow.py …` (an env assignment, `uv run`,
    `timeout N` or an option before the interpreter allowed), the script run by its own name, `bash -c 'LINE'` over such a
    line, or the console script `flow …`, which the hooks' package installs."""
    words = list(segment)
    while words and (re.fullmatch(r"\w+=.*", words[0]) or words[0] in PREFIXES):
        if words.pop(0) == "timeout":
            while words and words[0].startswith("-"):
                words.pop(0)
            words = words[1:]  # the duration
    if words[:2] == ["uv", "run"]:
        words = words[2:]
        while words and words[0].startswith("-"):
            words.pop(0)
    if not words:
        return False
    first = words[0].rsplit("/", 1)[-1]
    if first in ("sh", "bash", "zsh", "dash") and "-c" in words[1:-1]:
        return is_flow_command(words[words.index("-c") + 1])
    if re.fullmatch(r"python[\d.]*", first):
        rest = words[1:]
        while rest and rest[0].startswith("-"):
            rest.pop(0)
        return bool(rest) and rest[0].rsplit("/", 1)[-1] == "flow.py"
    return first == "flow.py" or (first == "flow" and len(words) > 1)


def logical_line(text):
    """The text with each newline outside quotes made a `;` and each comment dropped, so that a line of a quoted message
    (a commit message's) is no command of its own."""
    out, quote, i = [], None, 0
    while i < len(text):
        c = text[i]
        if quote is None:
            if c == "\\" and i + 1 < len(text):
                out.append(text[i:i + 2])
                i += 2
                continue
            if c in "'\"":
                quote = c
            elif c == "\n":
                c = ";"
            elif c == "#" and (i == 0 or text[i - 1] in " \t\n;&|("):
                while i < len(text) and text[i] != "\n":
                    i += 1
                continue
        elif c == quote:
            quote = None
        elif c == "\\" and quote == '"' and i + 1 < len(text):
            out.append(text[i:i + 2])
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def is_flow_command(command):
    """Whether any simple command of a shell command line runs the flow script; a quoted word is one word, so a commit
    message that names `flow check`, on one line or several, is no flow command.  An unbalanced quote passes."""
    text = logical_line(HEREDOC.sub(r"\1", command.replace("\\\n", " ")))
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        lex.commenters = ""
        words = list(lex)
    except ValueError:
        return False
    segment = []
    for w in words + [";"]:
        if w and set(w) <= OPERATORS:
            if runs_flow(segment):
                return True
            segment = []
        else:
            segment.append(w)
    return False


def project_has_flow(cwd):
    p = Path(cwd).resolve()
    return any((d / "flow.toml").is_file() for d in (p, *p.parents))


def write_marker(path, exclusive=False):
    """The marker written (False where `exclusive` and it was there), the old ones of the directory removed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    for old in path.parent.iterdir():
        try:
            if old.name.startswith(("loaded--", "refused--")) and now - old.stat().st_mtime > KEEP_SECONDS:
                old.unlink()
        except OSError:
            pass
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else 0))
    except FileExistsError:
        return False
    os.close(fd)
    return True


def handle(data):
    """The answer to print for this input, or None to pass."""
    event = data.get("hook_event_name")
    if not os.environ.get("CLAUDE_PLUGIN_DATA") or not data.get("session_id"):
        return None
    if event == "PostToolUse":
        if data.get("tool_name") == "Skill" and is_flow_skill((data.get("tool_input") or {}).get("skill")):
            write_marker(marker("loaded", data))
        return None
    if event == "UserPromptExpansion":
        if is_flow_skill(data.get("command_name")):
            write_marker(marker("loaded", data))
        return None
    if event != "PreToolUse" or data.get("tool_name") != "Bash":
        return None
    command = (data.get("tool_input") or {}).get("command")
    if not isinstance(command, str) or "flow" not in command or not is_flow_command(command):
        return None
    if not project_has_flow(data.get("cwd") or os.getcwd()) or marker("loaded", data).exists():
        return None
    if not write_marker(marker("refused", data), exclusive=True):  # refused already: this one passes
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": REASON}}


def main():
    try:
        data = json.load(sys.stdin)
        answer = handle(data) if isinstance(data, dict) else None
    except Exception:
        return 0
    if answer:
        print(json.dumps(answer))
    return 0


if __name__ == "__main__":
    sys.exit(main())
