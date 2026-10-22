# Security

## Reporting a vulnerability

Report it privately through GitHub's [private vulnerability reporting](https://github.com/lividgreen/research-kit/security/advisories/new), never in a public issue or pull request.
Say what is affected, how to reproduce it and the tag or commit it was found at.
A fix ships as a new tag with its changelog entry, and the advisory is published with it.

## Supported versions

The latest release tag; a fix is not backported to an older one.

## What the kit runs and reaches

- The checks run offline and read the project.
  The code a project's bindings files name — the reflow module, the library's command, the command for a PDF's text, and the manifest's generate command a prover session runs — runs as the project's pre-commit hooks do.
  So a bindings file is trusted as a hook is, and is read before a check runs in a repository you did not write; [What runs](docs/network.md#what-runs) lists every program the kit runs.
- The library's online commands call only the hosts [What goes online](docs/network.md) lists, run on demand and never from a check, and send a contact address or an API key only where one is set in the environment.
- The dashboard is read-only and binds the loopback by default, where it answers only requests addressed to it.

A way to make the kit run a command or reach a host that this page and those it links do not name, to write outside the project, or to make the dashboard serve a request it should refuse is in scope.
