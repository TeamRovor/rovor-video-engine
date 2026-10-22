# Jane native diagnostic worker

The durable SQLite worker can now dispatch the existing automatic blank Final
Cut import. This connects the previously separate importer and queue; it does
not install a service, export a video, or certify a native timeline.

From the reviewed checkout on Amar's Mac, one command reuses the newest valid
`~/Documents/Rovor/fcp-native-import-*` candidate folder and runs one deduplicated
job. No manual project/library creation or queue construction is required:

```sh
python3 tools/jane_native_worker.py --execute
```

Without `--execute`, it prints the selected candidate and state location, makes
no queue or app changes, and starts no model. The default worker and a worker
with only model use enabled both skip native jobs. Open Interpreter can invoke
this same deterministic launcher as its native action; it is not replaced by
another model. No automatic Interpreter tool registration is claimed.

The launcher creates private state under `~/Documents/Rovor/jane-native-worker-state`.
It uses a key derived from the canonical candidate directory and receipt.
Repeating the command reports the existing terminal result without reimporting.
Native failures and expired 420-second leases go to `needs_review`, never
automatic replay. Each attempt gets its own new output directory inside the
authorized workspace. Existing libraries and original media are not targets.

STOP in the private state directory prevents a claim. During native execution,
the importer checks STOP before each Apple event and while waiting for initial
library creation. A running Apple event can take up to 90 seconds to return;
STOP cannot undo it. Uncertain native effects must be reviewed rather than retried.

A succeeded queue result means both Apple event requests completed and the
library directory was observed. Its `native_timeline_verified` remains false.
It does not mean projects imported correctly, dimensions were checked in the
app, or an edited/exported video exists. macOS may require its first Automation
permission prompt, which this code does not bypass.

Validation in Linux/Python: `python3 -m unittest discover -s tests -p 'test_ghost*.py' -v`
passed 45 tests; py_compile and git diff --check passed. App calls in tests are
simulated. Existing worker/research/loop checks remain green. Native dispatch,
installed Apple DTD, actual Interpreter invocation of this launcher, host
permissions and all-day operation have not been tested in this session.

Importer provenance: reused `tools/fcp_native_auto_import.py` from PR #40,
blob `6659a787deea531ec9c66b909b6656558a8c36c7`, adding only cooperative STOP
checks. This branch stacks on PR #39's existing queue; it copies the required
import action instead of merging unrelated animation workstreams.

Proposed isolated scope: the worker, poller, importer, launcher, this guide and
`tests/test_ghost_native_import_queue.py`. Owner: ChatGPT / Amar native import
queue 2026-10-22. The main task-claim update was rejected by automatic approval
review in the preceding session; this proposed branch does not replace shared
main ownership. Review and native host verification remain the next steps.
