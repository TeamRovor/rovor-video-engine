# Owner review ledger

The trusted `hud-cloud-reviews` issue-event workflow writes immutable
`issue-NUMBER.json` decisions here after an owner submits a HUD review through
GitHub's signed-in confirmation. Employees must never create, edit or approve
these records, or submit issues impersonating owner reviews.

The latest issue number for an exact receipt ID and commit is authoritative.
To change a decision, submit a new review. Editing or closing the old issue
does not rewrite its original recorded decision. PASS accepts that output;
FAIL requests rework as a new bounded task, never a replay of an old job.
Reviewing does not itself execute or deploy the output. This is runtime review
state, not a second development task ownership queue.
