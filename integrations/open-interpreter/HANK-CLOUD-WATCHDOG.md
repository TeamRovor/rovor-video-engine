# Hank hosted QA

Hank is a recurring read-only check for the public ROVOR GitHub project. The scheduled workflow runs at minutes 17 and 47 each hour on a GitHub-hosted Ubuntu runner. It reviews queue-routing coverage, claim evidence, employee roster and spending safeguards, then leaves a short summary attached to that Actions run.

This initial employee does not use an AI model, operate desktop software, or change the task queue. It is a deterministic guard that works when the Mac is offline. No changes to the existing Mac scheduler are required.

A successful push run is evidence of hosted execution. A successful scheduled run is separate evidence of recurrence, and GitHub cron delivery is best effort. The other AI employees still require a verified provider connection, approved work packets and private Mac control for local applications.

Workflow: `.github/workflows/hank-cloud-watchdog.yml`.

Source: `tools/hank_cloud_watchdog.py`.

Unit tests: `tests/test_hank_cloud_watchdog.py`.
