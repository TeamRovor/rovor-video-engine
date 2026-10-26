# Website and landing-page delivery playbook

Version: 1. Decision date: 2026-10-21. Status: reusable internal process; not a client agreement.
Outcome: fewer missing requirements, repeated revisions and uncertain handoffs.
No client, price, deadline, revision allowance or maintenance obligation is established by this document.

## Start here

Read current [WORK.md](../../WORK.md) and claim the appropriate task in the shared queue.
Use [client intake](../templates/client-intake.md) and [delivery review](../templates/delivery-review.md);
keep filled private client records in their authorized system. Record a permitted reference in GitHub,
not credentials or personal submission data. This playbook is not a second ownership queue.

Confirm which tools this session actually has: source access, editing, preview/browser inspection,
form testing and deployment. A missing tool is a named limitation, not a passed check.
Use the relevant available site/code workflow; preserve existing source and hosting unless changing
them is explicitly within scope. Read the relevant tool skill before building.

Roles below describe responsibilities, not installed workers or assumed employee availability:
- Delivery lead: Amar or an explicitly assigned person; settles scope, business promises and escalation.
- Builder: the claimed ChatGPT/human session; produces source, preview, checks and handoff.
- Reviewer: named client/authorized approver; approves the particular artifact version.
One person may fill several roles. If no reviewer is named, record that as missing before sign-off.

## Intake-to-delivery stages

| Stage | Responsible owner | Required output | Exit condition |
| --- | --- | --- | --- |
| 1. Establish goal | Delivery lead; builder prepares intake | Completed known intake fields and missing-input list | Audience, main customer action and decision maker identified; unknowns visibly marked |
| 2. Bound the work | Delivery lead; builder drafts | Scope baseline: pages, features, inputs, exclusions, acceptance and revision policy | Scope accepted or explicitly a proposed internal draft; commercial terms not invented |
| 3. Organize content | Builder; reviewer supplies/approves facts | Page/section outline, asset provenance and draft copy | Each section supports the stated action; unknown claims use clear placeholders |
| 4. Build preview | Builder | Editable source and versioned private preview | Agreed structure and interactions implemented; placeholders and limitations listed |
| 5. Verify | Builder | Check matrix with results/evidence for exact preview version | Required checks pass; failures fixed or clearly held for review; unrun checks remain unrun |
| 6. Review and revise | Reviewer decides; builder implements | Consolidated feedback and updated version/change list | Acceptance criteria met and authorized reviewer approves exact version |
| 7. Publish and verify | Authorized deployment operator; delivery lead coordinates | Release reference, previous version/rollback and live checks | Publication is within authorization; live destination verified; release-specific checks pass |
| 8. Hand off | Delivery lead; builder prepares packet | Delivery record, ownership/access route and support boundaries | Recipient/destination and actual delivery evidence recorded; remaining work assigned |

Prepare whatever is useful when a stage is blocked. Do not turn an internal mockup into an approved
scope, pass an untested integration, or publish because the preview looks finished.

## Scope baseline: fill before implementation

- Business goal and primary action: inquiry, booking, purchase, call or another explicit outcome.
- Exact pages/sections, navigation, language and supplied copy; new writing responsibilities.
- Approved brand files and existing source version; image/font rights and replacement rules.
- Functional requirements: each form field, destination, confirmation/error behavior and integration.
- Target devices/browsers, accessibility checks and any agreed performance constraints.
- Existing domain/hosting; authorized publishing target and person; preservation/rollback requirements.
- Included revisions: number or scope, feedback owner and process; otherwise **not agreed**.
- Price, payment, dates and maintenance: **not agreed** unless sourced to an actual agreement.
- Exclusions: list what this project does not include. Do not assume ecommerce, booking, email setup,
  CRM, analytics, ads, ongoing copy, ongoing hosting or support are bundled with a website.
- Acceptance criteria and approver; reference to the actual agreed version/date.

For a landing page, define one primary conversion action and a focused section sequence.
For a multi-page site, define the navigation/page inventory and shared elements explicitly.
Rovor's service categories are context, not permission to add every service to each project.

## Missing inputs and changes

For every missing item record: item, impact, person/source needed, safe work possible now, and checkpoint.
Examples:
- Missing logo: reuse the verified existing asset if available; otherwise use a labeled placeholder in
  the internal preview. Do not invent a replacement brand or imply it is approved.
- Missing service copy or pricing: draft structure and questions; use marked placeholders. Never
  invent testimonials, client results, certifications, discounts or business contact details.
- Missing form destination: build draft fields and validation; mark delivery testing blocked.
  A success animation without actual confirmed receipt is not a working inquiry system.
- Missing hosting access: deliver source/preview and deployment instructions; publishing stays pending.
- New page/integration request after scope: log the requested change, effect on work/checks and
  delivery lead decision. Do not promise price/date adjustments on the client's behalf.

Collect related questions into one concise request only when needed. Continue independent useful work.
Distinguish correcting a defect against agreed requirements from adding new scope. A revision count
never excuses a broken agreed feature; commercial handling follows the actual agreement.

## Website acceptance matrix

Copy these into the delivery review and adjust to the agreed scope. Record pass/fail/blocked/not run
(or not applicable with reason), artifact version, method/device, date and evidence for every row.
These are proposed checks, not a universal certification or a promised score.

| Check | Observable acceptance | Evidence |
| --- | --- | --- |
| Content and brand | Correct supplied logo, names, contact details, offers and spelling; no unexplained placeholders | Compared source references and reviewed page list |
| Responsive layout | No unintended horizontal overflow, hidden controls or unreadable text at agreed widths | Screenshots and viewport/device sizes; emulation labeled |
| Navigation and CTA | Every agreed link/button reaches its intended destination; no broken internal paths | Link list with actual tested destination/result |
| Inquiry form | Required fields and invalid inputs handled; successful authorized test reaches intended destination; failure has honest recovery | Synthetic test ID, receipt confirmation and observed error behavior; no personal data in repo |
| Keyboard and labels | Primary path works with keyboard; visible focus, sensible heading order and labeled fields; meaningful images have appropriate alternatives | Manual walkthrough and any available automated findings |
| Accessibility limits | Known failures fixed or disclosed for review; automated success alone is not full accessibility certification | Check coverage and unresolved limitations |
| Images and loading | Assets load, relevant images sized sensibly, no broken media; agreed performance budget checked if one exists | Actual tool/settings/results; no fabricated score |
| Page metadata | Agreed titles/descriptions, favicon and share image present; preview indexing restriction reviewed before launch | Page metadata inspection; no ranking guarantee |
| Integrations | Only agreed integrations connected; real behavior checked in authorized test mode | Tool/mode/version/result; payments never tested by accidental live charge |
| Preservation | Existing working routes/content/data retained as scoped; no unrelated source edits | Change summary, source revision and rollback reference |
| Release | Exact approved build at authorized URL; HTTPS, navigation and primary action checked after release | Live URL, release ID/time and post-release results |

Synthetic form submissions may contact real inboxes or trigger automation: confirm such testing is
within existing authorization, or use a test destination. Mark an untested live path blocked.
Check data collection/tracking requirements for the actual client and jurisdiction when applicable;
do not copy generic legal promises or add analytics by default.

## Concrete review packet

Use the existing delivery-review template, with these website details:
1. Task ID; exact source commit; preview URL and build/version; proposed vs agreed scope reference.
2. Goal, primary action and page inventory; what is finished and what remains.
3. Screenshots at tested sizes and acceptance matrix; browser/device/method actually used.
4. Remaining placeholders, missing approvals, broken or untested paths and their impact.
5. Feedback request: reference the page/section, desired change and whether it corrects scope or adds it.
6. Reviewer decision and evidence tied to this version. Material changes require review of affected parts.
7. Proposed release target, authorized operator, previous version/backup and rollback steps.
8. Next action, responsible owner and checkpoint; no inferred delivery or publication.

After publication, record release-specific verification separately. If a primary action fails, preserve
evidence and use the authorized rollback procedure; do not keep claiming successful delivery.
Hand over editable source, asset provenance, account ownership/access instructions through secure routes,
and only the maintenance/support terms actually agreed. Never put passwords into a handoff document.

## Workflow walkthroughs (synthetic, not client results)

| Scenario | Correct result | Incorrect result to reject |
| --- | --- | --- |
| Landing page requested, no form inbox or approved price | Build internal layout with marked price placeholder; form receipt check blocked; request inbox/price decision | Invent price and mark form delivered after displaying success text |
| Preview approved, deployment not authorized | Record approved preview version; prepare release/rollback packet; publication pending | Treat design approval as permission to change DNS |
| Client adds a store to an agreed brochure site | Record change and dependencies; delivery lead settles scope; continue unaffected corrections | Promise store, payment setup and same deadline |
| Automated checks pass but mobile CTA is covered | Fail responsive/CTA checks; fix overlap and retest affected path | Report ready based only on build success |
| Another session resumes after preview | Read queue, exact source/preview and check matrix; continue remaining checks | Rebuild from scratch or assume blocked form was tested |
| Live form fails after release | Record live failure and authorized repair/rollback; keep delivery incomplete | Reuse preview pass as evidence live site works |

Walkthrough review on 2026-10-21: all six cases map to the stages and explicit stop/continue decisions
above. This is a document review, not an executed website test or client acceptance.

## Sources and measurement

Derived from repository policy at main commit
`9ace709ba573f970b9bee24941e00f18e5fbf83b`:
[operating system](../OPERATING-SYSTEM.md), [operating plan](../operating-plan.json),
[client intake](../templates/client-intake.md), [delivery review](../templates/delivery-review.md),
and [Rovor AI plan](../../ROVOR-AI-PLAN.md). This playbook adds proposed process details;
it does not establish new client terms or change those source policies.

When used on a real authorized project, record start/review/acceptance dates, revision hours and
missing-input delays in the approved project system. Compare comparable projects before claiming
time saved. No measured efficiency gain or completed client delivery is claimed by this initial version.
