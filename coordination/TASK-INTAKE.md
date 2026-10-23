# Paired task + routing intake

Use the existing **single** task queue and router. This helper prevents a recurring drift observed while Amar and other sessions work concurrently: a task enters `coordination/tasks.json` without a matching `coordination/work-routing.json` rule, so the next session cannot route it and CI rightfully fails.

`tools/task_routing_pair.py` is an offline Python-stdlib preparation tool. It does not open GitHub, send data, claim a task on its own, execute a worker, call a model, or connect to anyone's Mac. It will not automatically select a lane or infer a local application from a task's name.

## Procedure for local Git checkouts

1. Fetch main, check `git status`, and read `WORK.md`. Do not overwrite another session's changes or take over claimed scopes.
2. Prepare the new task as a local JSON **object** with `id`, `title`, `priority`, `status` (`ready` with null owner, or `active` with an exact stable owner, timezone-aware `updated_at`, and `next_update`), `branch`, `scopes`, `depends_on`, `next_action`, and `acceptance`.
3. Validate without changing files:

```sh
python3 tools/task_routing_pair.py --check
python3 tools/task_routing_pair.py --task-json /path/to/new-task.json --lane coordination --require hosted-ci
```

4. After reviewing the exact task ID, lane, capability assumptions, dependencies and claims, apply **only to a clean local checkout**:

```sh
python3 tools/task_routing_pair.py --task-json /path/to/new-task.json --lane coordination --require hosted-ci --apply
git diff -- coordination/tasks.json coordination/work-routing.json
python3 tools/project_loop.py check
python3 tools/task_routing_pair.py --check
git add coordination/tasks.json coordination/work-routing.json
git commit -m "coordination: add one task and its explicit route"
```

5. Push through the existing PR/merge process and **re-read latest main**, resolving any newly concurrent edits instead of force-pushing.

Use the smallest truthful required capability set. Adding `local-exec`, `moho-runtime`, `blender-runtime`, or `final-cut-runtime` does **not** grant that ability to ChatGPT. For a genuine host smoke test, require `local-exec` plus the relevant app runtime.

## Guarantees and limitations

- Existing queue and route must both pass validation and contain matching task IDs.
- Rejects duplicate IDs, unknown dependencies, overlapping reserved scopes when claiming `active`, invalid lane/capability values, and missing/redirected state paths.
- `--apply` refuses uncommitted changes to the two tracked files and checks their bytes again before writing. A clean checkout and exact owner remain the caller's responsibility.
- Writes the paired local files, but **does not make two filesystem renames a single atomic transaction**. If a machine stops mid-write, inspect/reconcile both files before committing.
- **Only one Git commit and a non-force push / normal PR merge provide a versioned paired change.** Concurrent GitHub API callers that edit main one file at a time still require the existing fail-closed coverage test; no shared distributed lock or GitHub branch-protection rule has been installed by this helper.
- Do not put credentials, private customer data, source media or personal computer paths in public task records.

## Tests

```sh
python3 -m unittest discover -s tests -p test_task_routing_pair.py -v
python3 tools/project_loop.py check
```

The isolated GitHub-hosted workflow runs both under Python 3.9 and 3.11. These tests do not demonstrate Mac access or ghost employees running unattended.
