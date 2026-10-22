# One-pass Mac setup: Walter, Ponytail, Graphify, OmniRoute, selected Agent Skills

**Current state:** Files in draft PR #35, NOT running on Amar's Mac. Commands below are intended for the regular macOS Terminal, not the Open Interpreter prompt. Do not paste Markdown-formatted `[https://...](https://...)` URLs into a shell; copy the raw code block.

## Phase A — authenticate Terminal GitHub and clone ROVOR

1. Exit any active Open Interpreter prompt using `/exit`. Then in Terminal:

```sh
gh --version
gh auth status
```

If `gh` reports `command not found`, use GitHub Desktop's sign-in/clone procedure or install GitHub CLI with `brew install gh` (if Homebrew exists). If not signed into an account authorized for `TeamRovor/rovor-video-engine`:

```sh
gh auth login --web --git-protocol https
gh auth setup-git
gh auth status
```

GitHub password prompts are **not** Open Interpreter prompts. Do not type `/agent` or `/debug-config` there. Do not share credentials.

2. In Terminal, clone **only if the directory does not already exist**:

```sh
mkdir -p "$HOME/Documents/Rovor"
cd "$HOME/Documents/Rovor"
if [ -d rovor-interpreter-pilot/.git ]; then
  cd rovor-interpreter-pilot
  git pull --ff-only
else
  git clone --depth 1 --single-branch --branch feat/open-interpreter-workforce-20261021 https://github.com/TeamRovor/rovor-video-engine.git rovor-interpreter-pilot && cd rovor-interpreter-pilot
fi
```

If clone/pull fails, **STOP**. Check Terminal's error; do not run the agent from the parent directory.

3. Read-only preflight:

```sh
bash integrations/open-interpreter/preflight-mac.sh
```

Expect `AGENTS.md`, the project TOML, Ponytail, context-engineering, debugging, OmniRoute and Graphify runbooks all to show `OK`. Third-party binaries remain optional.

## Phase B — test Walter's project instructions

```sh
interpreter
```

In the Open Interpreter prompt, enter `/debug-config` and then `/agent`. Verify that the loaded config stack includes the ROVOR pilot project and recognizes the named specialist configuration. These commands belong **inside** Interpreter, not the macOS shell.

Try one lightweight, read-only request:

> Walter, confirm the project root, list first-name-only roles Gus, Mike, Jesse, Gale, Jane, Saul and Hank, and report whether Ponytail, context-engineering and debugging skills can be read. Do not spawn extra agents or modify files. Tell me exactly which integrations are unverified.

Don't run 8 subagent checks with a low weekly quota.

## Phase C — Graphify local indexing (opt-in, no provider credits)

Exit Interpreter before returning to Terminal:

```sh
cd "$HOME/Documents/Rovor/rovor-interpreter-pilot"
uv tool install graphifyy
export GRAPHIFY_BACKEND=none
export GRAPHIFY_QUERY_LOG_DISABLE=1
graphify extract --help
graphify extract . --code-only
```

Review the Graphify documentation/installed command help if the CLI signature changed. No docs/media semantic backend is enabled. Then test `graphify query "Where is speech plan validation?"` and inspect the generated graph locally. Keep `graphify-out/` out of Git until reviewed.

## Phase D — OmniRoute provider gateway (opt-in, NOT automatic)

Install only after reviewing the package and deciding which provider account to use:

```sh
node --version
npm view omniroute version
npm install -g omniroute
omniroute
```

The `omniroute` command starts a local gateway/dashboard at port 20128, as documented by the maintainer. In a separate Terminal, `omniroute doctor` can inspect setup. Provider quotas/keys require an account. Use only free/approved plans, and turn off paid fallbacks. See `OMNIROUTE.md`.

**Do not replace the existing Open Interpreter provider yet.** The upstream OmniRoute CLI catalog lists Interpreter as compatible, but the current documented `omniroute run` command does not list an `interpreter` target. The correct Open Interpreter v0.0.56 provider and tool-calling integration must be validated separately. Never paste keys into source files or send private business assets to unvetted providers.

## Phase E — resume ROVOR development

Only after Phase B passes, ask Walter to follow the original `AGENTS.md` / `WORK.md` / canonical task queue. Use Graphify for targeted code lookup, Ponytail for compact changes, the two Addy skills only when their use case applies, and OmniRoute only if the dedicated gateway integration actually passes a read-only test.

No Mac software, backend accounts, API keys or actual 24/7 agent process are activated by this PR. 
