# Relationship Journal API

A privacy-conscious personal journal backend built with Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Redis and pytest. An educational portfolio project; not an audited production service. AI assisted portions of implementation and review.

## Features

- Account registration, Argon2 password hashing, short-lived JWT access tokens
- Database-backed sessions, hashed refresh tokens, rotation and replay revocation
- Redis-backed authentication rate limits
- Owner-scoped relationships and journal entries, pagination and literal case-insensitive search
- Dashboard, private JSON export, password-confirmed account deletion
- Health/readiness endpoints and automated integration tests

## Local development (existing PostgreSQL and Redis)

1. Create a virtual environment and install `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env`, configure the database URLs and Redis URLs, and set a random JWT secret (at least 32 bytes). Never commit `.env`.
3. Start your PostgreSQL and Redis containers and create the separate `relationship_journal_test_db` database.
4. Run `alembic upgrade head` and `uvicorn main:app --reload --port 8001 --no-access-log`.
5. Open `http://127.0.0.1:8001/docs`. Run `python -m pytest -q` to test.

## Alternative: local Docker Compose

With a local `.env` containing a valid JWT_SECRET, run `docker compose up --build -d`. The API is published on loopback only; the database and Redis use a new isolated Compose network and data volume. This configuration is for development, not production. Stop any existing server on port 8001 first. Run tests with `docker compose run --rm api python -m pytest -q`. `docker compose down` stops services without deleting data. Do not use `down -v` on data you want to retain.

## API authentication

`POST /signup` accepts JSON. `POST /login` accepts OAuth2-style form fields `username` (email) and `password`; this is first-party application authentication, not a general OAuth provider. It returns a bearer access token and sets an HttpOnly, SameSite=Strict refresh cookie. Send the access token in the Authorization header. `POST /refresh` rotates the cookie and returns a new access token; `POST /logout` revokes the current cookie session. `DELETE /me` requires JSON containing the current password. Older access tokens without a session ID are no longer accepted.

A browser client should keep access tokens in memory, send credentialed requests for authentication, serialize refresh attempts, and use the same site as the API. For local development use the same hostname for frontend and API. For HTTPS deployment set COOKIE_SECURE=true and configure exact trusted CORS origins and proxy settings. Do not store refresh tokens in localStorage. Use synthetic journal data in demos.

## Operations and limitations

`GET /health` reports liveness; `GET /ready` checks PostgreSQL and Redis. Application logging avoids request bodies and query strings; keep proxy/access logging configured to avoid sensitive URLs. `/me/export` is a bounded JSON export. Redis limits currently use client IP, not a complete distributed abuse prevention system. Production work still includes HTTPS, secret rotation, request size limits, account-level abuse controls, session cleanup, backup/restore, dependency scanning and independent security review. Docker/CI configuration must be validated on the target environment.
