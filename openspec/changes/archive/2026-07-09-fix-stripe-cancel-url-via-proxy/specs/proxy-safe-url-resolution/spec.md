No spec-level changes. This is a pure implementation fix.

The requirement remains: Stripe `success_url` and `cancel_url` SHALL resolve to the correct external URL that the user's browser can reach. Implementation was incorrect (`request.build_absolute_uri()` uses proxy-rewritten Host header); the fix changes the implementation approach without altering requirements.