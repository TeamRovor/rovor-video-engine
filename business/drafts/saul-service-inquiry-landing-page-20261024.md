# Saul — ROVOR website-service landing page and lead-intake gate (internal draft)

**Task:** `a-overnight-03-saul-business-draft` · **Prepared:** 2026-10-24 · **Status:** proposed copy/acceptance plan only; **not published, client-approved, or a priced offer**.

## Purpose and evidence boundary

This is a **ROVOR Digital service inquiry page**, not a client website or a replacement for the existing [first scoped client offer](../offers/first-offer-draft.md). Its job is to help a prospective business owner decide whether to request a conversation about a small, useful website project. The [operating system](../OPERATING-SYSTEM.md) describes ROVOR's work as websites, branding, content and inquiry/customer systems, but establishes no client results or revenue baseline. The [proof catalog](../proof-catalog.md) distinguishes source implementation from accepted/delivered client work. Therefore, the copy below **does not** claim delivered client sites, performance improvements, testimonials, or established prices.

### Proposed public-facing page structure — copy is unapproved

| Order | Section | Draft content and interaction | Source/approval gate |
| --- | --- | --- | --- |
| 1 | Hero | **“Make it easier for customers to reach your business.”** Supporting line: “ROVOR Digital can help plan a clear, mobile-friendly website with straightforward ways to call or request a quote.” Primary button: **“Discuss a website project.”** | Copy is a service proposal, not proof of existing results. Button destination **unknown** until an owner approves a working intake route. |
| 2 | Who this is for | “For service businesses that want customers to understand what they offer and how to get in touch.” Prompt: “What should a visitor do first: call, request a quote, or ask about an appointment?” | No assertion that a specific prospect has a broken website or loses leads. |
| 3 | A focused starting scope | “A single responsive page can present your services, service area, business details and one clear contact action.” | Based on the [internal one-page offer](../offers/first-offer-draft.md); actual features, pages and costs require agreement. |
| 4 | Related options, not bundled promises | “Ask about brand/logo work, content planning or a more extensive website.” **Booking, commerce, CRM, email setup, paid ads, social publishing and maintenance are separate discussions, not included features.** | Service categories are described in [business operations](../OPERATING-SYSTEM.md) and the [delivery playbook](../playbooks/website-delivery.md); integrations are **not verified or included by default**. |
| 5 | How a project would work | **Discuss the goal → agree on a written scope → review a versioned preview → test the chosen contact action → authorize launch and handoff.** | Proposed process follows the [website delivery playbook](../playbooks/website-delivery.md). No fixed delivery date or revision allowance is promised. |
| 6 | Contact / inquiry | Button: **“Request a project conversation.”** Form proposal: business name, website (optional), service category, desired visitor action, short project note, preferred reply method, and a consent control **only after actual data handling is reviewed**. | No live form or data processor is selected. Never render a fake success or collect real inquiries before owner approval of destination, retention and applicable notices. |
| 7 | FAQ and footer | “How much does a project cost?” → “Pricing depends on the agreed scope; request a conversation.” “Can you work with an existing domain?” → “We can discuss what access and changes would be required.” Footer: only verified business contact channels and approved legal/privacy text. | **Price, schedule, hosting, support, approved brand kit, live channels and legal wording remain unknown.** Do not invent an address, review count, case study or guarantee. |

**Copy decision:** One primary action on this page is a *project conversation*, not a promise of booked customers. Keep any secondary navigation subordinate. No publication, advertising or outreach is authorized by this draft.

## Lead qualification — private, human-reviewed intake

Use the existing [opportunity brief](../templates/opportunity-brief.md) for a verified prospect and [client intake](../templates/client-intake.md) only after the person has authorized the project discussion. Do not store names, emails, phone numbers, submissions or credentials in this public repository.

| Check | Evidence to request or verify | If unknown |
| --- | --- | --- |
| Genuine business and authority | Public business/site reference where appropriate; the person confirms they can decide or introduce the decision maker. | Mark **unverified**, not qualified. |
| Concrete goal | They choose one primary action: call, quote request, booking inquiry or another defined action. | Ask one clarifying goal question; do not sell an unspecified automation. |
| Existing journey | Inspect the exact public website, with date and URL, **before** asserting a defect. A new business may have no site. | Record “not inspected” or “new site”; never invent lost leads. |
| Smallest useful scope | Proposed page count, CTA, content, form destination and excluded features. | Offer a scope conversation, not a quote. |
| Assets and authority | Client-approved brand/text/images, source rights, domain/hosting access and publishing authority. | Preview-only; no domain changes or reused unlicensed assets. |
| Commercial and delivery decisions | Owner-approved price, payment, schedule, revisions, support and reviewer. | **Not agreed**; no commitment or due date. |
| Safe inquiry handling | Approved destination, minimal fields, notice/consent requirements and permission to test. | Form stays non-operational; no live collection. |

**Triage rule:** “Ready for an owner-scoped proposal” requires a real decision maker, a stated customer action, a plausible smallest deliverable and a list of missing inputs. “Needs discovery” is not a rejection; “unverified” is not a qualified lead. No automatic scoring, outreach or CRM export is implemented.

## Acceptance tests — proposed, not executed

| ID | Test and expected result | Current result |
| --- | --- | --- |
| LP-01 | At agreed phone/tablet/desktop widths, heading, CTA and service description remain readable with no horizontal overflow. | **NOT RUN** — no page built. |
| LP-02 | Hero and footer contain no unsourced client count, testimonial, ranking, price, deadline or guaranteed result. | **DRAFT CONTENT REVIEW ONLY**; final page untested. |
| LP-03 | Every CTA has an owner-approved destination; absent one, no misleading live button or fake confirmation appears. | **BLOCKED** — destination unknown. |
| LP-04 | Form rejects missing/invalid required fields, prevents double-submit and reports actual failure honestly. | **BLOCKED** — no implementation. |
| LP-05 | An explicitly authorized synthetic inquiry reaches the verified intended recipient with a traceable receipt, with no personal submission data committed to GitHub. | **BLOCKED** — destination and test authorization unknown. |
| LP-06 | Keyboard navigation, focus visibility, form labels, heading order and meaningful image alternatives are checked on the exact preview. | **NOT RUN**. |
| LP-07 | Every displayed logo, service statement, business contact channel and rights-sensitive asset is compared with owner-approved source. | **BLOCKED** — approved brand/contact inventory not supplied. |
| LP-08 | The authorized reviewer approves the exact preview revision; only an authorized operator publishes; HTTPS/CTA/form are retested at the live URL and a rollback reference is retained. | **BLOCKED** — no approval or deployment. |

These checks complement, rather than replace, the [existing delivery acceptance matrix](../playbooks/website-delivery.md). A green GitHub check would not prove the page is deployed, that an inbox receives inquiries, or that a customer accepted it.

## Owner handoff / next executable action

1. **Amar / authorized ROVOR owner:** confirm whether this service inquiry page is wanted; approve the exact hero/offer wording, verified brand/logo/contact channels and desired intake route. Decide whether the proposed one-page client offer is the default starting scope; **do not infer a standard price from an individual deal**.
2. **Authorized builder, after a separate claim:** create a private versioned preview only from approved assets; record actual device/browser tests and the missing form/legal decisions. Do not alter the existing live ROVOR entrance or homepage without separate explicit approval.
3. **Authorized reviewer/operator:** approve the exact preview, form destination and any publishing target before any release. Use the [delivery review process](../playbooks/website-delivery.md); record live checks and handoff separately.

**Not done:** no prospect verified, form connected, client record created, email/social message sent, ad purchased, site published, paid API called, or business outcome measured. This is a reusable, source-grounded **proposal and test plan**, not a completed sales or website delivery.
