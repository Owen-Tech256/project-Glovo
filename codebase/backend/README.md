# Delivery Marketplace — Backend (Phase 1)

Flask REST API providing the authentication and role-based identity
foundation for the delivery marketplace. Phase 1 implements **only**
identity, authentication, authorization, and account management — no
products, orders, payments, or dispatch logic.

## Stack

- Python 3.11+ / Flask 3
- PostgreSQL + SQLAlchemy + Flask-Migrate (Alembic)
- JWT access tokens (Flask-JWT-Extended) + rotating, DB-hashed refresh tokens
- bcrypt password hashing
- Flask-Limiter (rate limiting) + Flask-CORS
- pytest

## 1. Setup

### Prerequisites
- Python 3.11 or later
- PostgreSQL 14+ running locally (or reachable via `DATABASE_URL`)

### Install

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set at minimum:

```
SECRET_KEY=<random value>
JWT_SECRET_KEY=<random value>
DATABASE_URL=postgresql://<user>:<password>@localhost:5432/delivery_marketplace
```

Generate strong random secrets with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Create the database

```bash
createdb delivery_marketplace   # or via psql / your GUI of choice
```

### Run migrations

```bash
export FLASK_APP=run.py
flask db upgrade
```

This creates `users`, `refresh_tokens`, `password_reset_tokens`, and
`audit_events`. Migration files live in `migrations/versions/` and are
committed to the repo — never regenerate history, only add new revisions:

```bash
flask db migrate -m "describe your change"
flask db upgrade
```

### Create the first Admin account

Admin accounts are **never** created through the public API. Use the
provisioning script:

```bash
python scripts/create_admin.py --email admin@example.com --phone +10000000000 \
  --full-name "Platform Admin" --password "A-Strong-Password1"
```

### Run the API

```bash
python run.py
# or
flask run
```

The API is served at `http://localhost:5000/api/v1`.

## 2. Testing

The test suite runs against an in-memory SQLite database, so it has no
external Postgres dependency and can run anywhere:

```bash
pytest
pytest --cov=app --cov-report=term-missing   # with coverage
```

56 tests cover: registration + duplicate email/phone, login (success,
failure, suspended/disabled accounts), `/auth/me`, logout + refresh-token
revocation, refresh-token rotation, password reset (request, completion,
single-use enforcement, session invalidation), role-based authorization for
all four roles against admin-only endpoints, ownership protection (a user
cannot fetch another user's record by changing the URL id), profile
self-update, password-hashing unit tests, and API error-response shape.

## 3. Environment variables

| Variable | Purpose |
|---|---|
| `APP_CONFIG` | `development` \| `testing` \| `production` |
| `SECRET_KEY` | Flask session/signing secret |
| `JWT_SECRET_KEY` | JWT signing secret (must differ from `SECRET_KEY` in production) |
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_ACCESS_TOKEN_EXPIRES_SECONDS` | Access token lifetime (default 900s / 15 min) |
| `JWT_REFRESH_TOKEN_EXPIRES_SECONDS` | Refresh token lifetime (default 14 days) |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins |
| `RATELIMIT_STORAGE_URI` | `memory://` for local dev; use `redis://...` in production |

Never commit `.env`, database passwords, JWT secrets, or any real credentials.

## 4. API reference (Phase 1 surface)

All responses use a consistent envelope:

```json
// success
{ "success": true, "message": "...", "data": { } }
// error
{ "success": false, "error": { "code": "SOME_CODE", "message": "..." } }
```

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/auth/register` | none | `role` may be `CUSTOMER`, `VENDOR`, or `RIDER` (default `CUSTOMER`). `ADMIN` is rejected. |
| POST | `/api/v1/auth/login` | none | Accepts email or phone in `identifier`. |
| POST | `/api/v1/auth/logout` | access token | Revokes the supplied refresh token. |
| POST | `/api/v1/auth/refresh` | none (refresh token in body) | Rotates: old refresh token is revoked, a new pair is issued. |
| GET | `/api/v1/auth/me` | access token | Returns the caller's own profile. |
| POST | `/api/v1/auth/forgot-password` | none | Always returns a generic message; never discloses whether the email exists. |
| POST | `/api/v1/auth/reset-password` | none (reset token in body) | Single-use token; revokes all of the user's refresh tokens on success. |
| PATCH | `/api/v1/users/me` | access token | Currently supports `full_name` only — email/phone/role/status are not self-service. |
| GET | `/api/v1/users/<public_id>` | access token | Self or `ADMIN` only — the ownership-protection endpoint. |
| GET | `/api/v1/users` | `ADMIN` | Paginated list, optional `?role=` filter. |
| GET | `/api/v1/admin/stats` | `ADMIN` | User counts by role/status, for the admin dashboard overview. |
| GET | `/api/v1/health` | none | Liveness check. |

### Error codes

`VALIDATION_ERROR` (422) · `EMAIL_TAKEN` / `PHONE_TAKEN` (409) ·
`INVALID_CREDENTIALS` (401) · `UNAUTHENTICATED` (401) ·
`ACCOUNT_NOT_ACTIVE` (403) · `FORBIDDEN` (403) · `NOT_FOUND` (404) ·
`INVALID_REFRESH_TOKEN` (401) · `INVALID_RESET_TOKEN` (422) ·
`RATE_LIMITED` (429) · `INTERNAL_ERROR` (500)

## 5. Architecture notes

- **Modular monolith**: `app/{auth,users,api,models,common}` — each domain
  is its own package with its own routes/schemas/service layer. Nothing
  is a single giant file, and each module could be extracted into its own
  service later without rewriting authentication.
- **Token strategy**: access tokens are stateless signed JWTs (fast to
  verify, short-lived). Refresh tokens are opaque random strings whose
  SHA-256 hash is stored server-side — this is what makes revocation
  (logout, password reset) and rotation possible, per the ER model in the
  SRS.
- **Ownership enforcement**: `@require_owner_or_role(...)` is the reusable
  primitive future phases (vendor branches, rider deliveries, customer
  orders) should reuse instead of writing ad-hoc ID checks per endpoint.
- **Known Phase 1 trade-off**: `/auth/forgot-password` returns the raw
  reset token in the response body *only* when `DEBUG`/`TESTING` is
  enabled, since no email/SMS provider is wired up yet. This must be wired
  to a real provider (and the debug branch removed or gated harder) before
  any non-local deployment.
