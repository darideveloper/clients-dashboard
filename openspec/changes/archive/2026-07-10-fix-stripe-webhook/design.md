## Context

The Stripe webhook handler at `ourlives/views.py:webhook()` receives a `stripe.Event` object from `verify_webhook_signature()`. In stripe-python v15, `StripeObject` no longer has a `.get()` method — callers must use dict-style access (`event["type"]`) or attribute access (`event.type`). The existing code uses `.get()` on both `stripe.Event` and nested `StripeObject` instances throughout `views.py` and `models.py`, causing `AttributeError: get` on every webhook call.

Production logs show the error at `views.py:92` — payment completes on Stripe's side but the webhook crashes before credits are issued.

## Goals / Non-Goals

**Goals:**
- Fix the `AttributeError` so webhooks process successfully
- Preserve all existing fallback/default behavior (`.get("field", default)` semantics)
- Zero behavior change — same fields read, same defaults applied, same event dedup logic

**Non-Goals:**
- No new capabilities or features
- No spec changes (existing `credit-purchase` spec behavior unaffected)
- No changes to test infrastructure
- No Stripe library version change

## Decisions

**Decision 1: Convert StripeObject to dict at the earliest point (Option A)**

Convert the `event` object via `event.to_dict()` immediately after signature verification in `views.py:webhook()`. In stripe-python v15, `to_dict()` recursively converts the entire object tree to native Python types — `to_dict_recursive()` was removed. The resulting plain dict is passed downstream to `process_ourlives_checkout_completion`.

| Aspect | Option A: Early dict conversion | Option B: Replace `.get()` with `[]`/`in` |
|--------|-------------------------------|-------------------------------------------|
| Touch points | 1 line in `views.py` | 10+ lines across `views.py` + `models.py` |
| Risk of missed spots | Low — central conversion catches all | Higher — easy to miss a `.get()` |
| Fallback handling | Works naturally (dict.get has defaults) | Need explicit `in` checks for each fallback |
| Future-proofing | Decouples from StripeObject API | Tightly coupled to Stripe dict structure |

Chosen: **Option A** — lower risk, fewer changes, and the existing `.get()` logic in `models.py` continues working verbatim.

## Risks / Trade-offs

- **Risk: Stripe adds large/dynamic fields** → `to_dict()` may include extra fields not present in the StripeObject property API. Mitigation: no field iteration happens — we access specific known keys, so extra fields are harmless.
- **Risk: Future Stripe API sends unexpected types** → plain dicts are the most portable format. No issue.
- **Trade-off**: The convenience of attribute-style access (`event.type`) is lost — but the codebase already uses `.get()` style, so dict is consistent.
