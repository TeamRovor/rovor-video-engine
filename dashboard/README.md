# ROVOR Live Operations HUD

A static, public-safe dashboard that reads the Rovor coordination queue directly from GitHub. It can be opened locally or hosted as a static page; it does not need a server, API key, GitHub token, build step, or JavaScript dependency.

## Open it

Open `index.html` in a modern browser, or serve the `dashboard/` folder from any static host. The page requests public data from the GitHub REST API.

## Data integrity and behavior

- Resolves the latest `main` commit, then fetches `coordination/tasks.json` and `coordination/work-routing.json` by that **same immutable commit SHA**. The displayed queue and routing therefore cannot silently mix revisions.
- Polls queue/routing every 60 seconds while the page is open; “Refresh now” also refreshes pull requests.
- Refreshes open pull requests no more than every five minutes, unless manually refreshed.
- Shows network/API rate-limit failures and labels previously displayed data as potentially stale.
- Displays queue ownership separately from host status. GitHub queue entries do not prove a worker claimed work, a laptop is online, a local process is running, or a job executed.
- Contains no token or credential. Requests use GitHub's unauthenticated public API and are subject to its rate limits.

## Limits

This is a read-only viewer. It does not create claims, launch workers, trigger renders, send messages, or change repository state. It is not a replacement for the canonical queue and routing JSON. The page is a new live data view; it does not bundle a missing or private legacy HUD asset.

## Downloadable ZIP

The `Dashboard ZIP` workflow packages this directory and publishes it as a GitHub Actions artifact on pushes affecting the dashboard or when manually dispatched. Download the artifact from the workflow run's **Artifacts** section.
