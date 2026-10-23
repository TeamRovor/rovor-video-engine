# ROVOR Live Operations HUD

A static, public-safe dashboard that reads the Rovor coordination queue directly from GitHub. It can be opened locally or hosted as a static page; it needs no server, API key, GitHub token, build step, or JavaScript dependency.

## Open it

Open `index.html` in a modern browser, or serve the `dashboard/` folder from any static host. The page requests public data from the GitHub REST API.

## Data integrity and behavior

- Resolves the latest `main` commit, then fetches `coordination/tasks.json` and `coordination/work-routing.json` by that **same immutable commit SHA**. Queue and routing therefore cannot silently mix revisions.
- Polls queue/routing every 60 seconds while the page is open; “Refresh now” also refreshes pull requests.
- Refreshes open pull requests no more than every five minutes, unless manually refreshed.
- Shows network/API rate-limit failures and labels previously displayed data as potentially stale.
- Displays queue ownership separately from host status. GitHub queue entries do not prove a worker claimed work, a laptop is online, a local process is running, or a job executed.
- Contains no token or credential. Requests use GitHub's unauthenticated public API and are subject to rate limits.

## Limits and packaging

This is a read-only viewer. It does not create claims, launch workers, trigger renders, send messages, or change repository state. It is not a replacement for the canonical queue and routing JSON.

The legacy Iron Man HUD source was not present on `main` or in the active task branch when this task resumed, so this branch supplies a standalone live-data view rather than claiming to preserve unseen legacy artwork. The GitHub Actions ZIP workflow could not be added through the available write path in this session; no downloadable workflow artifact is claimed yet. To package locally, run `zip -r rovor-live-operations-hud.zip dashboard` from the repository root.
