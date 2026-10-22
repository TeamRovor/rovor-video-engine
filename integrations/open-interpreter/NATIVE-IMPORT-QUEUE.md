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

To inspect a pending request without launching or retrying it:

```sh
python3 tools/jane_native_worker.py --status
```

Status uses a read-only SQLite connection and also reads checkpoints from the
existing `fcp-jane-auto-*` manual attempts. It works before queue initialization.
The import action now prints and persists progress before each blocking Apple
event, while waiting for the library, and at completion/failure. A checkpoint
shows the latest recorded stage; it does not prove the process is still alive.
If a manual attempt already exists and no matching queued job is recorded,
execution stops for inspection instead of starting another uncertain import.

The launcher creates private state under `~/Documents/Rovor/jane-native-worker-state`.
It uses a key derived from the validated source XML hashes, independent of the
candidate directory name, timestamp or formatting of its receipt.
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
passed 49 tests; 16 additional current importer/candidate tests passed in an
isolated source harness. py_compile and git diff --check passed. App calls in
tests are simulated. The two generated library-targeted XML files also passed
real lxml/libxml2 DTD validation against FCPXML 1.13 with SHA256
`5afbc7ca1001bbc2190fb3b21d4d440ce061d94f5a5f583074e982b4745cd04d`, matching
the user's installed Mac DTD receipt. This is Linux schema validation, not an
xmllint or app run on this Mac. Existing worker/research/loop checks remain green.
Native dispatch, actual Interpreter invocation of this launcher, host
permissions and all-day operation have not been tested in this session.

Importer provenance: preserves the current pilot's live checkpoint and atomic
receipt changes through commit `9863ebc`, combines PR #40's exclusive reservation,
stale-receipt and prepared-XML checks, and adds cooperative STOP checks.
This branch stacks on PR #39's existing queue; it copies the required
import action instead of merging unrelated animation workstreams.

Proposed isolated scope: the worker, poller, importer, launcher, this guide and
`tests/test_ghost_native_import_queue.py`. Owner: ChatGPT / Amar native import
queue 2026-10-22. The main task-claim update was rejected by automatic approval
review in the preceding session; this proposed branch does not replace shared
main ownership. Review and native host verification remain the next steps.
