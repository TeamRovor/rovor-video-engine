# Ponytail — lightweight ROVOR coding-efficiency integration

Ponytail is **not an LLM, provider, or free-token gateway**. It is an instruction-based coding skill: read relevant code, reuse existing implementation, make the smallest complete change, maintain validation, and report unverified work. It may reduce avoidable output tokens and coding time, but **no reduction has been benchmarked for Open Interpreter v0.0.56 or ROVOR**. The upstream benchmark was run using Claude Code and should not be applied directly to Codex subscription limits.

## Implemented in this pilot branch

- Copy of the upstream MIT-licensed `skills/ponytail/SKILL.md` is stored at `.agents/skills/ponytail/SKILL.md`.
- Its upstream copyright and MIT license are retained in `.agents/skills/ponytail/LICENSE`.
- `AGENTS.md` directs Walter and any appropriate coding specialist to consult the skill for coding tasks; ROVOR's existing work queue, task claims, creative QA, security and approvals take precedence.
- No external hooks, network service, added dependency, account credentials, local model or API keys were installed.

**Provenance:** [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail), upstream skill blob SHA `d64edd32265ba21cbf5270158f04e97d96925f27` at the time copied; [upstream MIT license](https://github.com/DietrichGebert/ponytail/blob/main/LICENSE). See [upstream install instructions](https://github.com/DietrichGebert/ponytail/blob/main/INSTALL.md) for other supported agent clients. This is an instruction-only integration, not the upstream plugin with lifecycle hooks, modes, status bands or slash commands.

## Local usage after the private ROVOR repo is cloned

Start Open Interpreter from the `rovor-interpreter-pilot` repository root. Confirm `AGENTS.md` and `.agents/skills/ponytail/SKILL.md` exist, then ask:

> Walter, on code tasks consult `.agents/skills/ponytail/SKILL.md` and apply the smallest complete, tested solution. First identify existing tools and relevant callers. Do not shorten work by omitting validation, animation fidelity, safety or a deliverable. Handle minor tasks yourself and delegate only when parallel expertise is necessary. Check project setup in read-only mode now.

Even if this specific Open Interpreter build does **not** automatically discover Codex project skills, the instruction in AGENTS.md and explicit request above can activate the relevant behavior. Confirm by checking what instructions the running session actually sees; do not claim native skill activation without that check.

## Usage-budget approach

- Reuse code/commands already documented in the repository; avoid asking multiple agents to rediscover the Mac environment.
- For initial verification, one read-only query is enough. Do not issue a giant eight-agent setup task.
- Prefer the lowest-capability-cost model that can reliably perform the task, as available under your provider. Verify selected provider and account's actual rate limits in `/model` and `/status`; don't assume switching prompts adds credits.
- For routine media inspection, use FFmpeg/ffprobe, shell tests and deterministic scripts where appropriate. Save AI model reasoning for planning, debugging and exceptions.
- Use a local model only if separately installed and tested for both instruction quality and permissions; Ponytail cannot run on hardware by itself.

## Compatibility and rollback

If ROVOR's current Open Interpreter executable does not support `.agents/skills` automatic discovery, continue using the direct `AGENTS.md` instructions. No additional install is necessary for the core efficiency policy.

Remove the optional `AGENTS.md` policy paragraph and the `.agents/skills/ponytail/` directory from this pilot branch to revert; existing animation sources remain untouched.

No runtime test has been performed on Amar's Mac from this GitHub-only session.
