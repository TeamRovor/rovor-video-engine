# Mac-independent ROVOR cloud dispatcher: GitHub-hosted shift

This is an external trigger of the existing owner-private Site POST /api/ghost/service
operation shift. It is not a replacement cloud employee, never invokes the local
Mac, and does not select or pay for models.

## Required for actual unattended execution

1. The existing private Site must be deployed with the cloud service route,
   checking its dedicated 32+ character GHOST_SERVICE_TOKEN and processing
   only the approved-packet replenisher and claim-gated tick.
2. Provision the SAME existing dedicated service credential as the GitHub
   Actions secret ROVOR_GHOST_SERVICE_TOKEN for TeamRovor/rovor-video-engine.
   This is a separate admin step. The connected GitHub integration cannot
   create repository secrets. Never put tokens or provider API keys in Git,
   chat, or shell command arguments.
3. Merge the hosted scheduler workflow to default branch main. Scheduled jobs
   only execute from the default branch. GitHub's nominal five-minute cron is
   best effort, not a 24/7 SLA.
4. Use Actions > ROVOR cloud workforce (hosted shift) > Run workflow once.
   A green run with state not_armed means no repository secret and NO WORK.
   State executed with dispatched 0 means admission/claims blocked dispatch.
5. Match real job attempts and actual models in the existing private HUD.
   Do not infer quota/online status from API-key presence or model catalog.

## Safety

- Pinned HTTPS owner-private Site, no redirects, one authenticated POST.
- Pull request CI performs offline tests only, receives no service credential,
  and cannot call model endpoints.
- Secrets, prompts, jobs and model responses are never logged. Actions output
  contains only aggregate dispatched and denied counts.
- Site enforces STOP, reviewed immutable job eligibility, exact verified
  zero-cost account/model, pacing, quotas, circuit, and durable claims.
- A job already attempted is never automatically replayed.
- GitHub concurrency prohibits overlapping hosted jobs; the Site also
  coordinates concurrent native or ChatGPT-triggered shifts.
- GitHub Actions may delay or drop scheduled invocations. Green no-op runs
  never count as proof of cloud model execution.
- Cron cannot invent new eligible tasks. The approved queue must actually
  contain valid unattempted jobs.
- This hosted path does not change private Site native_clock_verified; native
  cron deployment is a separate acceptance requirement.
