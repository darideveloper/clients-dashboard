## 1. Fix webhook entry point

- [x] 1.1 Add `stripe_event_dict = event.to_dict()` in `views.py:webhook()` after signature verification
- [x] 1.2 Pass `stripe_event_dict` to `process_ourlives_checkout_completion` instead of the raw event
- [x] 1.3 Change `event.get("type")` to `stripe_event_dict["type"]` and `event.get("id")` to `stripe_event_dict["id"]`

## 2. Verify and run tests

- [x] 2.1 Run existing test suite to confirm no regressions
- [x] 2.2 Verify webhook endpoint responds successfully
