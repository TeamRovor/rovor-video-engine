# Addy Osmani Agent Skills — targeted, on-demand subset

Upstream: https://github.com/addyosmani/agent-skills (MIT, Copyright 2025 Addy Osmani).
Original work contains 25 independent developer workflow skills plus adapters and reference documents. ROVOR's initial pilot deliberately copies **only two** relevant standalone skills:

- `.agents/skills/context-engineering/SKILL.md` (upstream blob `fb8bb5f85128302b231d301c1201da1e223f6869`) — choose appropriate scope and context at session start and during task switches.
- `.agents/skills/debugging-and-error-recovery/SKILL.md` (upstream blob `356da20365a7cd6825b4ffad14be39280c92cdfc`) — reproduce, localize, reduce, fix and verify failures.
- `.agents/skills/addy-agent-skills-LICENSE` — upstream MIT terms and attribution.

Why not install every skill? The existing ROVOR AGENTS.md, WORK.md, queue protocol, Ponytail and QA process cover much of the same ground. Loading or applying a large overlapping pack for every prompt can cost more tokens or produce incompatible instructions. Expand selectively when an actual task needs a new capability, after checking for duplicate guidance.

Recommended activation (Open Interpreter from project root):
- Walter/Gus: read `context-engineering` **only** for session/task handoff or when context is being wasted.
- Mike/Jesse/Gale/Jane/Hank: read `debugging-and-error-recovery` **only** for concrete failure investigation.
- Keep Ponytail as the default concise coding guidance; ROVOR safety, build checks, animation quality and repository ownership always win.
- Do not claim native skill discovery or upstream slash commands until verified in Open Interpreter v0.0.56. Explicitly read a relevant SKILL.md file if auto-discovery is absent.

No external setup, extra packages, hooks, personas or background services are installed by these Markdown skills.
