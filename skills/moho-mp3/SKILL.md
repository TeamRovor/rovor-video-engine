---
name: rovor-moho-mp3
description: Use when a user attaches one MP3 and asks to submit, monitor, or retrieve a local Moho Pro render job.
---

# Local Moho render jobs

Use the ChatGPT attachment directly with `render_from_mp3`; never ask for a local file path or copy the audio into a public service. First use `check_setup` when readiness is unclear. The bridge blocks before transfer when media verification (ffprobe or the bundled macOS AVFoundation probe), the Moho Pro 14 command-line renderer, or a private administrator-owned adapter configuration is missing.

`render_from_mp3` accepts one `.mp3` file up to 25 MiB and 60 seconds. If it returns a job ID, poll `get_render_status` with that ID. Report `blocked`, `failed`, or `review_required` exactly; never describe an unverified job as a finished animation. A missing or unverified adapter must remain blocked.

When status is `review_required`, call `get_render_artifact` to obtain the hash-bound `video/mp4` resource link. The current local MCP server does not certify that the host surfaces this resource as an attached video in the chat. The `review_required` status means only that the current machine checks passed; it does not certify that Evan's art, acting, pronunciation, or full production quality passed.

The renderer must be Moho Pro 14 through the trusted adapter. Do not use or represent the Evan sprite engine as Moho. Do not alter the source project, infer phones from spelling, skip the acoustic gate, run GUI interactions, or claim the whole upload-to-render loop is verified until a real MP3 has completed the local headless path and its artifact has been returned.
