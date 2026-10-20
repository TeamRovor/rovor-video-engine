# Continuing work on Evan Engine

Use [`START-HERE-V3.md`](START-HERE-V3.md) for the current engine overview and [`evan-engine/README.md`](evan-engine/README.md) for setup and usage on macOS or Windows. Keep machine-specific executables, model files, and `local_tools.json` local to each install.

## Project direction and GitHub sync

- This is Rovor Digital's video engine, not resume work. Keep the current renderer usable on its own; a future Moho Pro adapter should consume the saved scene data without making Moho a current dependency.
- Treat the active GitHub pull request branch as canonical; PR #7 is the current workstream. The extracted workspace copy may be stale.
- Before editing a file, fetch its latest branch content and blob SHA from GitHub. Preserve any newer edits, then update using that exact SHA. If GitHub rejects the SHA, fetch again and reconcile before retrying. Never force-push or replace the branch with an older workspace snapshot.
- Check the current branch again before finishing a related set of edits so changes Amar pushed from his Mac are incorporated.

