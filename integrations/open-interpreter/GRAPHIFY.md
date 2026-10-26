# Graphify — code-only, offline knowledge graph pilot

Source: https://github.com/Graphify-Labs/graphify (default branch `v8`). Official PyPI name **`graphifyy`** with two y's; executable is `graphify`.

This tool indexes code locally using tree-sitter, building a searchable graph of symbols, dependencies and relationships. It can reduce repeated file searches on an existing codebase. It is not a substitute for ROVOR's canonical task queue, GitHub handoff or user memory; it does not automatically share the graph with Evan's computer.

## Safe, no-API Mac setup

Install with the existing `uv` tool manager:
```sh
uv --version
uv tool install graphifyy
graphify --help
```

From the isolated `rovor-interpreter-pilot` checkout, keep Graphify **strictly offline** at first:
```sh
export GRAPHIFY_BACKEND=none
graphify extract --help
graphify extract . --code-only
graphify query "Where is the speech plan validation logic?"
```

Read `graphify extract --help` before running, since CLI arguments may evolve. `GRAPHIFY_BACKEND=none` disables the LLM-based semantic backend; `--code-only` skips docs, PDFs, images and videos that otherwise may incur model calls. For architecture visualization, inspect the locally generated `graphify-out/` artifacts. Do not commit machine-generated graphs or local cache paths until the corpus is confirmed safe and intentionally shared.

Graphify provides `graphify install --project --platform codex` to register its skill in an applicable Codex project, but **do not run this yet**. It may edit local `AGENTS.md` or install hooks that interfere with ROVOR's existing instructions. Start with the standalone CLI and explicit scoped queries from Walter.

Walter's procedure: when graph output already exists, ask a narrow `graphify query`, `path` or `explain` before repeating broad repository scans; check file sources/commits for correctness. If the graph is stale, missing, incomplete or inaccurate, fall back to source files and rerun offline indexing as needed.

Privacy: code-only graphing is local per upstream documentation. Other inputs can trigger LLM use; queries themselves can be logged to `~/.cache/graphify-queries.log` unless logging is disabled via `GRAPHIFY_QUERY_LOG_DISABLE=1`.

**Status in PR #35:** documented opt-in Graphify pilot. No Mac binary or generated graph has been installed or tested by this session.
