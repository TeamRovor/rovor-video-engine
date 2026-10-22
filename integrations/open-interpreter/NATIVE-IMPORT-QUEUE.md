# Native Final Cut diagnostic queue

Proposed isolated scope: tools/ghost_worker.py, tools/ghost_worker_loop.py, tools/fcp_native_auto_import.py and tests/test_ghost_native_import_queue.py. Owner: ChatGPT / Amar native import queue 2026-10-22. Shared main ownership is unchanged: direct claim publication was blocked by automatic approval review in the preceding session.

Goal: connect the existing automatic blank diagnostic importer to the durable SQLite worker. Existing research jobs remain unchanged; native dispatch requires its own opt-in, with no paid model call. Only an existing validated candidate folder inside the explicit workspace is accepted. Preserve crash review, dedupe, stop, and distinguish dispatch from verified timeline import.

Acceptance: default worker skips native jobs; explicit native flag processes at most once; expired native lease goes to needs_review; invalid paths and arbitrary payloads rejected; STOP prevents subsequent import events; receipt is preserved; focused worker/loop/research regressions pass. No Mac runtime or unattended installation is claimed.
