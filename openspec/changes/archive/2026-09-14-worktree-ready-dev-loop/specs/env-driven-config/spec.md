## MODIFIED Requirements

### Requirement: CORS and CSRF origins
`CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` SHALL be derived from comma-split env vars, with each value stripped and trailing slashes removed. The dev `.env.dev` SHALL include `https://clients.localhost` and `http://localhost:8000`; prod SHALL include the production hostname. In dev, `.localhost` subdomain requests from the checkout's own portless domain SHALL also be accepted so copied env files work in any sibling.

#### Scenario: Localhost trusted
- **WHEN** `.env.dev` has `CORS_ALLOWED_ORIGINS=https://clients.localhost,http://localhost:8000`
- **THEN** `settings.CORS_ALLOWED_ORIGINS == ["https://clients.localhost", "http://localhost:8000"]`

#### Scenario: Sibling domain accepted
- **WHEN** a sibling serves `https://clients-feature-x.localhost` with a copied `.env.dev`
- **THEN** requests from that origin pass host, CORS, and CSRF checks

## ADDED Requirements

### Requirement: Portless URL resolution chain
Settings SHALL resolve the public dev URL as `PORTLESS_URL` (injected by portless) first, then `HOST` from env, then the production fallback, so a copied `.env.dev` yields the correct per-checkout domain without edits.

#### Scenario: Injected URL wins
- **WHEN** `PORTLESS_URL=https://clients-feature-x.localhost` is present
- **THEN** the app generates absolute URLs (e.g. redirects, callbacks) against that domain regardless of the copied `HOST` value
