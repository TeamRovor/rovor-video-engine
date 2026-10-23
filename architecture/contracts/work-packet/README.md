# Portable work packet contract v1

This is a small, versioned data contract, not a second task queue, scheduler, runtime or permission system. Queue ownership remains in `coordination/tasks.json`; capability routing remains in `coordination/work-routing.json`; workers continue using existing handoff and render transports.

## Files

- `work-packet.schema.json`: JSON Schema 2020-12 shape.
- `examples.json`: three synthetic packet projections based on evaluation-pack case IDs for client intake, sourced sales observation and GitHub Actions triage.
- `invalid-examples.json`: intentionally invalid candidates for the negative acceptance check.
- `validate.py`: dependency-free structural and cross-field checks.
- `tests/test_work_packet_contract.py`: regression suite.

## Contract invariants

- Source references have stable IDs, a URI, explicit verification status and a SHA-256 field. A source marked verified must have a valid hash; unverified or unavailable evidence is never silently promoted.
- Acceptance checks preserve `not_run`, `running`, `pass`, `fail`, `unknown` and `blocked`.
- Technical status is separate from human approval, publication and delivery. A green technical result never implies approval.
- Artifact receipts distinguish not-created, reserved, produced, verified, failed and unknown. Verified artifacts need a content hash.
- External effects require explicit authorization references and cannot exceed the effects declared allowed by the constraints.
- Executor fields describe capability requirements and bounded mode; opaque executable payload fields are rejected.
- The validator checks structure and references. It cannot prove that a person is genuine, a URI is reachable, a source is truthful, or that a client granted consent. Ground truth and authorization still require independent review.

## Run

From the repository root (Python standard library only):

```sh
python -m unittest discover -s tests -p test_work_packet_contract.py -v
python architecture/contracts/work-packet/validate.py --expect pass
python architecture/contracts/work-packet/validate.py --examples architecture/contracts/work-packet/invalid-examples.json --expect fail
```

These examples are synthetic projections of the evaluation pack, not real client jobs. No model calls, network access, customer contact, spending, deployment or local application control occurs.
