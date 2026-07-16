## Context

Currently, after a successful Stripe payment, the user is redirected back to the purchase form (`/admin/ourlives/appsettings/purchase/`) with no confirmation message. The form is empty and there's no indication the payment succeeded. Django's `messages` framework is already rendered by Unfold in the admin base template — any `messages.success()` call in a view will show as a styled notification.

## Goals / Non-Goals

**Goals:**
- Redirect to AppSettings change form after successful payment (shows updated `total_tokens`)
- Show a success message with the number of credits purchased
- Keep cancel flow unchanged (back to purchase page)

**Non-Goals:**
- No real-time confirmation that the webhook has fired (async by nature)
- No Stripe API calls — token count from checkout creation is sufficient
- No model changes or migrations

## Decisions

**Decision 1: Intermediate success view (Option 2)**

Create a lightweight `/stripe/success/` view that receives query params, sets a Django message, and redirects to the admin settings page.

```
                      ┌──────────────────────┐
                      │  create_checkout      │
                      │  (views.py)           │
                      │                       │
                      │  success_url = f(     │
                      │   "/stripe/success/   │
                      │    ?token_count={n}"  │
                      │    "&session_id={     │
                      │     CHECKOUT_SESSION  │
                      │     _ID}"             │
                      │  )                    │
                      └──────────┬────────────┘
                                 │
                      Stripe checkout + payment
                                 │
                      Stripe redirects to success_url
                                 │
                      ┌──────────▼────────────┐
                      │  payment_success       │
                      │  (views.py)            │
                      │                        │
                      │  messages.success(     │
                      │   "50 credits added!") │
                      │                        │
                      │  redirect("admin:      │
                      │   ourlives_appsettings │
                      │   _change")            │
                      └──────────┬─────────────┘
                                 │
                      ┌──────────▼──────────────┐
                      │  Admin settings page     │
                      │  with Unfold notification │
                      │  "50 credits added! ✓"   │
                      └─────────────────────────┘
```

Alternatives considered:
- **Static redirect**: No feedback to user — confusing
- **Stripe API lookup**: Extra latency and API call cost for minimal benefit (token count is already known)
- **Webhook polling**: Model changes, complex, poor UX while waiting
- **Direct redirect to settings with no message**: Simplest but no feedback

Chosen: Intermediate view — minimal code, no API calls, clear UX.

**Decision 2: Use `{CHECKOUT_SESSION_ID}` Stripe template variable**

Stripe replaces `{CHECKOUT_SESSION_ID}` in the success URL with the actual session ID. Including it is forward-compatible — we can use it later for Stripe API lookups if needed, but we don't rely on it now.

**Decision 3: Pass `token_count` in the URL, not `session_id` alone**

Stores the actual token count for the success message without needing an API call. Sent as a query parameter in the success URL (informational only — not security-sensitive).

## Risks / Trade-offs

- **Risk: User modifies `token_count` in URL** → the message would show an incorrect count. Mitigation: this is cosmetic only — the actual credit addition is handled by the webhook server-side. The message is informational.
- **Risk: Unfold message template missing** → fallback: Django's `messages` framework still adds the message to the request; admin base templates typically render it somewhere. Unfold's `admin/base.html` explicitly includes `unfold/helpers/messages.html`.
- **Trade-off**: Intermediate view adds a redirect hop (extra 302) — negligible latency (~5ms).
- **Risk: `session_id` param not present** → view handles gracefully by still showing a success message without the session detail.
