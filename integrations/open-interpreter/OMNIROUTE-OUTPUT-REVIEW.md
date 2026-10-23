# OmniRoute private draft-review gate

**Stage:** Source implemented in PR #51; **not invoked on the user's Mac**. This is a read-only gate for the three existing OmniRoute research workpacks: `runner-blocker`, `supervisor-resilience`, and `provider-efficiency`. It does not create new work, consume provider credits, call Open Interpreter, edit ROVOR source, upload private AI answers to GitHub, operate any application or authorize jobs.

## Why this exists

Three parallel model outputs are only useful if we can distinguish a fresh, attributable private draft from a stale, altered, failed or interrupted one. The input repo and task queue can change while the models work. Even a polished AI paragraph is not proof the Mac or Final Cut did anything. The gate makes that distinction explicit without leaking private draft content to logs.

## How to read results on the actual Mac (only when a trusted local executor exists)

Run from the trusted PR #51 checkout:

```bash
python3 tools/omniroute_draft_review.py --all
```

Or `--packet runner-blocker` to inspect a single existing private receipt. The command scans **only** the fixed `~/Documents/Rovor/OmniRoute-Draft-Receipts` path (or an explicitly specified private `--receipts` folder) and the checked-in packet's permitted public source files. It never initializes the receipt directory, contacts a model, or performs a native UI action. It refuses receipts redirected through symlinks or placed under the Git repository.

### Checks made before a draft can be reviewed

- Exact approved workpack identity, receipt schema/state, model identifier, fixed permission flags and timezone-aware creation time
- The receipt's recorded workpack SHA-256 and every public input-source hash still match the current checked-out inputs
- The draft is complete with bounded response, elapsed time and allowlisted integer usage counters
- Certain high-confidence private-key/token patterns or unsubstantiated first-person claims such as having verified a Mac execution cause extra review blocks
- Failed and reserved receipts remain non-replayable and are **not** upgraded into successful drafts

The status `draft_ready_for_human_review` means the file is well formed and its public inputs have not changed. It does **not** establish factual accuracy, provider cost/eligibility, reproducibility, independent validation, or permission to execute any model-proposed commands.

Output is **only** a small JSON status record with packet ID, fixed reasons and booleans. The AI answer itself, raw provider errors and credential-looking substrings are never printed or sent to GitHub. To read a draft, an authorized person/reviewer must open the private file locally. Some sensitive data may evade fixed patterns; the local review remains necessary. This is not a security boundary against a malicious person with write access to both source files and receipts; there are no signed attestations.

## Coordination

The phone ChatGPT lane owns the private Mac-control bridge/poller integration and has already marked their *source* tasks done, but real Mac execution is still unverified. This receipt tool is an independent review layer in the existing OmniRoute PR #51, not a second task queue, Mac agent or transport. Do not activate insecure public-repo self-hosted runners, auto-merge other agents' work, or replay failed Final Cut library creation/import.

**Verification:** `tests/test_omniroute_draft_review.py` is offline and uses synthetic public sources plus private temporary receipts. GitHub workflow `.github/workflows/omniroute-draft-review.yml` runs that suite on Python 3.9 and 3.11, without any model API requests.
