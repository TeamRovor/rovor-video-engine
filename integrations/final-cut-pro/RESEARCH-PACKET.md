# Jane's first ROVOR editing research packet

**Job type:** evidence-backed study and connection planning. **Executor today:** an explicitly invoked GitHub-connected ChatGPT session or a verified local Codex/Open Interpreter session. **Not** an unattended research process, continuous monitoring, browsing daemon or authority to install software. Consult live coordination queue before a new task claim. Keep research output under a separately claimed scope in later work; do not invent task ownership outside coordination/tasks.json.

## The assignment Jane receives

> Jane, research Final Cut Pro until you can reliably explain how to assemble ROVOR's existing source-faithful Evan animation, voiceover, SFX, music and captions into professional YouTube videos and 9:16 reels. Use official current Apple user/developer guides first, then inspect candidate MCP/automation projects. For every claim give source/version/date and separate source-verified from Mac-tested. Create a concise, actionable step-by-step post-production playbook and the safest minimal Mac connection test. Do not install packages, modify an existing Final Cut library, consume paid services or request broad accessibility permissions without explicit approval. Record next questions and evidence in the existing shared GitHub workflow; do not claim you are running unattended.

## Five bounded research missions (prioritized)

| Mission | Research questions and authoritative starting point | Tangible output and falsification test |
| --- | --- | --- |
| A. Editing fundamentals | Libraries/events/projects; importing media; magnetic timeline/connected clips; clip organization/roles; audio mixing; transitions; frame rates and color. [Apple FCP user guide](https://support.apple.com/guide/final-cut-pro/welcome/mac) | Human-readable reproducible 30+ second editing recipe with media manifest, source preservation and expected intermediate outputs; reject undocumented UI commands |
| B. ROVOR long-form YouTube | Storyboarding chapters for 4–9 min spoken narration; scene and shot cadence; audio ducking, continuity and sound design; markers, subtitles, export master. [Apple Final Cut Pro guide](https://support.apple.com/guide/final-cut-pro/welcome/mac) | Reusable edit decision blueprint that maps each original narration interval to shot/artifact/source and review checklist; no scene fabricated from silence |
| C. Reels/shorts repurposing | 9:16 output, separate framing, Smart Conform limitations, caption safe areas, hooks, platform-specific export and normal-speed review. [Apple vertical/square projects](https://support.apple.com/en-ph/guide/final-cut-pro/ver8bad7adc6/mac) | Portrait edit recipe with explicit subject/prop visibility checks, source aspect/crop choices, 1080×1920 60fps target and captions overlay review |
| D. App connection | FCPXML versions and preservation limits; Apple events; workflow extension SDK; external FCPXML MCP v0.27.2 source/dependencies; CommandPost permissions; read-only handshake. [Apple FCPXML](https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference); [Apple Apple-event guide](https://developer.apple.com/documentation/professional-video-applications/sending-data-programmatically-to-final-cut-pro); [upstream MCP](https://github.com/DareDev256/fcp-mcp-server) | Decision table covering methods, support/version, read/write, real-time control, export, installation, security, budget, open questions. Recommend one bounded option only after evidence |
| E. Integration proof | Is FCP installed and version compatible? Can local Codex enumerate tools? Can it inspect a synthetic XML within root? Does outside-root path fail? Does a permitted disposable import preserve originals? | Actual host transcript/receipt with command, versions, input/output SHA, tool response and any native FCP observation. Not completed by static documentation |

## Known and unknown as of 2026-10-22

**Official source-backed**
- Apple documents XML interchange and an Apple event for importing FCPXML; Workflow Extensions are a different documented extension mechanism.
- Apple documents creating vertical versions and Smart Conform; automatic crop/reframing needs review.
- Apple documents exporting to social-ready formats and caption modes. Uploading is a separate activity.

**Third-party source inspected (not independently host-verified)**
- DareDev256/fcp-mcp-server on inspected HEAD: pyproject version 0.27.2, 15 grouped tool families claimed, basic packages mcp>=1.21.1 and defusedxml>=0.7.1. README/source mention optional FCP import.
- Its single FCP_PROJECTS_DIR variable is a listing setting, while FCP_PROJECTS_DIRS controls read allowlists; set both narrowly in the disabled default config.
- CommandPost claims Lua/CLI automation; target Final Cut version, security behavior and costs are not confirmed for ROVOR.

**Unknown / blocking host evidence**
- Is Final Cut Pro installed on Amar's Intel Mac, and which exact version?
- Can the local Codex trusted project activate an MCP successfully, with a pinned Python runtime?
- Are the original audio, source artwork, existing project/library and selected audio rights available through an authorized host session?
- Can the chosen workflow emit real source-faithful 1080p60 edits without performance issues or visual defects?
- Can a persistent local worker/researcher actually execute, persist receipts and recover while the Mac is awake? The existing ghost-worker PRs #32–#34 are scoped read-only infrastructure, not Jane's editing capability; no adapter is authorized here.

## Evidence format for future research passes

Record results in the existing task/PR artifact, not a duplicate owner table:

| Field | Example |
| --- | --- |
| Mission / question | D: Can the external MCP read a disposable project? |
| Exact source | Canonical Apple URL or pinned GitHub commit/blob link |
| Checked date / versions | ISO 8601, FCP version, Python and MCP server version |
| Claim classification | Official documentation / upstream implementation / hypothesis / locally executed |
| Smallest proof | Tool discovery + one exact read command and resulting safe output |
| Required approval | Install package / grant Automation rights / import demo / none |
| Finding and unknown | Evidence with scope, errors and next targeted research |
| Next task | Separate existing-queue claim, scope, acceptance, blocked dependencies |

Success is a vetted learning system, not a huge undifferentiated encyclopedia. Jane should write down the top 5 repeated operations that save ROVOR editing time and automate one safely, measure fidelity and cost, then expand.

## Research/review guardrails

No invented official FCP API, no remote Mac claim, no GUI click automation unless real host and approval, no original library edits, no sideloaded binary patches, no social posting or paid provider fallback, no extra personas for routine tasks. Research can be done in a cloud ChatGPT/GitHub session; testing the actual editor needs a Mac-local executor. Roles do not continuously search without a configured scheduler, budget, credentials and verified loop.
