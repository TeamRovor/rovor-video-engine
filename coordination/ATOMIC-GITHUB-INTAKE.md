# ROVOR atomic GitHub task intake

## The proven gap

ChatGPT-connected sessions were publishing a new task to coordination/tasks.json and its capability route to coordination/work-routing.json as separate GitHub writes. A second session could temporarily see an unclassified task. The existing single task queue and routing policy remain authoritative.

## One-commit handoff

The new tools/github_atomic_task_intake.py uses the authenticated GitHub Git Data API against only TeamRovor/rovor-video-engine, main:

1. Read main HEAD SHA and associated Git tree SHA.
2. Read both JSON files at exactly that pinned HEAD.
3. Run the existing task_routing_pair.prepare_pair validator. It rejects duplicate IDs, missing routes, invalid capabilities, unfinished dependencies and conflicting active scopes.
4. Preview by default, without Git writes.
5. With an explicit --apply, construct a Git tree with BOTH files, create one commit parented to the verified HEAD, and update the main ref with force:false.
6. Recheck main before final publication; if the history moved concurrently, the non-fast-forward update is rejected, never forced.

All-or-nothing visibility: unreachable intermediate Git objects may be created, but no separate task-only or route-only revision is visible on main. Do not automatically retry a conflict; refresh main and inspect the concurrent change.

## Usage

Provide a narrowly scoped repository contents read/write token through the process environment variable ROVOR_GITHUB_TOKEN. Never paste or commit it into the repository or issue discussion. The program does not provision credentials. Use a local task JSON object with exact owner, scopes, dependencies, next action, acceptance and timezone-aware timestamp.

Dry-run (no Git writes):

    python3 tools/github_atomic_task_intake.py --task-json /secure/path/new-task.json --lane coordination --require hosted-ci

Approved publication:

    python3 tools/github_atomic_task_intake.py --task-json /secure/path/new-task.json --lane coordination --require hosted-ci --apply

Outputs are limited to task ID, paired counts and commit SHA; API error bodies and secrets are never printed.

## Verification and limits

The GitHub connector independently demonstrated an actual atomic paired change in commit a1b78ca4874665aa016d4bed5fe2b619e57d5287. That live operation used GitHub connector actions, not this newly authored Python program. The Python program is covered by separate hosted, mocked-HTTP regression tests and has NOT executed against a private Mac, local model, or hardware.

GitHub REST ref update force:false uses fast-forward ancestry, not an arbitrary compare-and-swap property. A concurrent independent commit on main makes a candidate with the old parent diverge and fail. Existing branch rules may refuse updates; never bypass them. Branch protections or access credentials are not installed by this command.

For local paired edits without GitHub API access, continue to use tools/task_routing_pair.py and coordination/TASK-INTAKE.md. The tool does not create another queue, execute tasks, synchronize chats automatically, or provide unattended access to Amar's computer.
