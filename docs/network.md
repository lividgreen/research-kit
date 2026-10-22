# What goes online, and what runs

Every check is offline: `flow check`, `library check`, `formal check` and the dashboard read the project and nothing else; `formal handback` reads git.
The library's online commands — `resolve`, `verify`, `fetch`, `restore`, `watch` — run on demand and never from a check.

## The hosts

They call arXiv, DOI content negotiation at doi.org, Crossref, OpenAlex, the OpenCitations index, GitHub's API for a repository's address and the page itself for any other address; `resolve --at` adds zbMATH or Semantic Scholar, and `fetch` asks Unpaywall for an open-access copy of a DOI when a contact address is set.
`fetch --url` and `resolve --url` fetch the address given, whatever host it names.
Only an http or https address is fetched, a redirect to any other scheme is not followed, and an answer past 256 MiB, or a source that unpacks past it, is not kept.

## The environment variables

Three optional environment variables are read when set and from no file: `LIBRARY_MAILTO`, `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`.
The address is sent in the User-Agent of every request the library makes, so every host called sees it; the keys go only to their interfaces; the first line of an online command says which variables were set and prints no value.

## What runs

Besides the scripts themselves and the Python that runs them, the kit runs these, and nothing else:

- `markdownlint`, where it is on PATH, over a record `flow` just wrote, reverting the write if it added a violation;
- the command `library.toml` binds for a kept PDF's text (`pdftotext` by default), over the kept file;
- the library, asked for its keys by `flow check`: the `[library] command` of `flow.toml`, else the library skill installed beside the flow skill, else `library` on PATH (as in the hooks' environment), the last two only where a `library.toml` stands at the root;
- the `reflow_module` a bindings file names, imported and run over the text a command writes;
- `git`, from `formal handback`, for the manifests and the diff at the base revision;
- each component the dashboard mounts: the scripts of the skills installed beside it, `flow` and `library` on PATH, and what `dashboard.toml` or `--component` names.

So a bindings file is code the checks run, as a pre-commit hook is, and `formal.toml`'s `[manifest] generate` is a command the prover session runs in the workspace: read the bindings before running a check or a prover session in a repository you did not write.
