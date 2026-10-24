# OmniRoute actual nine-model fleet inspector

This utility is for the existing Mac OmniRoute AI workforce. It is not a ChatGPT or GitHub-only ghost employee, scheduler, provider account, model, or claim that nine jobs are running.

Run on a reviewed Mac checkout of the existing worker, where ghost_omniroute_job.py is available:

    python3 tools/omniroute_model_fleet.py --expected-models 9

It reads two local CLI catalogs: providers list and combo list. It returns a sanitized report of provider connection entries versus distinct model IDs in ROVOR combos versus current named worker packet/route membership. It does not echo raw provider records, secrets or log payloads. It calls no chat completion, does not edit OmniRoute configuration, and does not alter the existing LaunchAgent, SQLite jobs, STOP or quota.

If there are fewer than nine distinct model IDs in configured ROVOR combos, the difference is explicit. If all nine appear, they are still NOT verified working or free: each provider needs its own documented cost/quota eligibility and accepted live response evidence. A model ending with :free is not sufficient authorization to spend or dispatch automatically. Provider connection count may represent accounts rather than unique model IDs.

Next deployment owner: the existing PR #41 / PR #137 Mac runtime engineer. Use this local inventory to reconcile the actual nine entries against the approved model choices before extending the current SQLite dispatcher. Do not create a second scheduler, replay failed job IDs or run unknown/paid provider routes. Add per-model verified inference receipts to the HUD only after actual host integration. Hosted tests are synthetic and are not evidence that OmniRoute models were called.
