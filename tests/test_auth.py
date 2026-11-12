import os
import pytest
import models

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
import jwt
import security
from datetime import datetime, timedelta, timezone
from database import Base, get_db
from main import app

load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is not configured")

if make_url(TEST_DATABASE_URL).database != "relationship_journal_test_db":
    raise RuntimeError("Tests must use the test database!")

test_engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    try:
        yield
    finally:
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(clean_database):
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)

    try:
        yield test_client
    finally:
        try:
            test_client.close()
        finally:
            if previous_override is None:
                app.dependency_overrides.pop(get_db, None)
            else:
                app.dependency_overrides[get_db] = previous_override


# ==================== HELPERS ====================

def create_authenticated_user(client, username):
    gmail = f"{username}@gmail.com"
    password = "testpassword123"

    signup = client.post("/signup", json={
        "username": username,
        "gmail": gmail,
        "password": password
    })
    assert signup.status_code == 200, signup.text

    login = client.post("/login", data={
        "username": gmail,
        "password": password
    })
    assert login.status_code == 200, login.text

    token = login.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def create_relationship(client, headers, his_name="test", status="active"):
    response = client.post("/relationships", json={
        "his_name": his_name,
        "years_together": 2,
        "problem": "communication",
        "status": status
    }, headers=headers)

    assert response.status_code == 201, response.text

    return response.json()["id"]


def create_journal_entry(
    client,
    headers,
    relationship_id,
    title="rame",
    content="storyteling"
):
    response = client.post(
        f"/relationships/{relationship_id}/entries",
        json={
            "title": title,
            "content": content
        },
        headers=headers
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["title"] == title
    assert data["content"] == content
    assert data["relationship_id"] == relationship_id

    return data["id"]


# ==================== AUTH TESTS ====================

def test_signup(client):
    response = client.post("/signup", json={
        "username": "zura",
        "gmail": "zura@gmail.com",
        "password": "testpassword12345"
    })

    assert response.status_code == 200

    data = response.json()

    assert data["username"] == "zura"
    assert data["gmail"] == "zura@gmail.com"
    assert "hashed_password" not in data


def test_duplicate_signup(client):
    payload = {
        "username": "zura",
        "gmail": "zura@gmail.com",
        "password": "testpassword12345"
    }

    response1 = client.post("/signup", json=payload)
    assert response1.status_code == 200

    response2 = client.post("/signup", json=payload)
    assert response2.status_code == 400


def test_login_success(client):
    signup = client.post("/signup", json={
        "username": "zura",
        "gmail": "zura@gmail.com",
        "password": "testpassword12345"
    })

    assert signup.status_code == 200

    response = client.post("/login", data={
        "username": "zura@gmail.com",
        "password": "testpassword12345"
    })

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    signup = client.post("/signup", json={
        "username": "zura",
        "gmail": "zura@gmail.com",
        "password": "testpassword12345"
    })

    assert signup.status_code == 200

    response = client.post("/login", data={
        "username": "zura@gmail.com",
        "password": "wrongpassword"
    })

    assert response.status_code == 401


def test_me_authenticated(client):
    headers = create_authenticated_user(client, "zura")

    response = client.get("/me", headers=headers)

    assert response.status_code == 200

    data = response.json()

    assert data["gmail"] == "zura@gmail.com"
    assert data["username"] == "zura"
    assert "hashed_password" not in data


def test_signup_integrity_error_rolls_back(client, monkeypatch):
    calls = []
    original_rollback = Session.rollback

    def fake_commit(_self):
        raise IntegrityError(
            "INSERT INTO users",
            {},
            Exception("duplicate key")
        )

    def spy_rollback(self):
        calls.append(1)
        return original_rollback(self)

    monkeypatch.setattr(Session, "commit", fake_commit)
    monkeypatch.setattr(Session, "rollback", spy_rollback)

    response = client.post("/signup", json={
        "username": "test",
        "gmail": "test@gmail.com",
        "password": "testpassword12345"
    })

    assert response.status_code == 400
    assert len(calls) == 1


# ==================== RELATIONSHIP TESTS ====================

def test_user_cannot_get_other_users_relationship(client):
    headers_a = create_authenticated_user(client, "user_a")
    relationship_id = create_relationship(client, headers_a)

    headers_b = create_authenticated_user(client, "user_b")

    response = client.get(
        f"/relationships/{relationship_id}",
        headers=headers_b
    )

    assert response.status_code == 404


def test_relationship_response_contract(client):
    headers = create_authenticated_user(client, "zura_to")

    response = client.post("/relationships", json={
        "his_name": "test",
        "years_together": 2,
        "problem": "communication",
        "status": "active"
    }, headers=headers)

    assert response.status_code == 201

    data = response.json()

    assert data["status"] == "active"
    assert "owner_id" not in data


def test_relationship_filtering(client):
    headers = create_authenticated_user(client, "filter_user")

    first_id = create_relationship(
        client, headers, his_name="First", status="active"
    )

    create_relationship(
        client, headers, his_name="Second", status="ended"
    )

    third_id = create_relationship(
        client, headers, his_name="Third", status="active"
    )

    response = client.get(
        "/relationships",
        params={"status": "active"},
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert [item["id"] for item in data] == [first_id, third_id]
    assert all(item["status"] == "active" for item in data)


# ==================== JOURNAL ENTRY TESTS ====================

def test_journal_entry_crud(client):
    headers = create_authenticated_user(client, "zura")
    relationship_id = create_relationship(client, headers)
    entry_id = create_journal_entry(client, headers, relationship_id)

    entry_url = f"/relationships/{relationship_id}/entries/{entry_id}"

    single_entry = client.get(entry_url, headers=headers)

    assert single_entry.status_code == 200
    assert single_entry.json()["title"] == "rame"

    updated_entry = client.put(entry_url, json={
        "title": "new title",
        "content": "new content"
    }, headers=headers)

    assert updated_entry.status_code == 200
    assert updated_entry.json()["title"] == "new title"
    assert updated_entry.json()["content"] == "new content"

    deleted_entry = client.delete(entry_url, headers=headers)

    assert deleted_entry.status_code == 200

    missing_entry = client.get(entry_url, headers=headers)

    assert missing_entry.status_code == 404


def test_journal_entry_ownership(client):
    headers_a = create_authenticated_user(client, "user_a")
    relationship_id_a = create_relationship(client, headers_a)
    entry_id_a = create_journal_entry(
        client, headers_a, relationship_id_a
    )

    entries_url_a = f"/relationships/{relationship_id_a}/entries"
    entry_url_a = f"{entries_url_a}/{entry_id_a}"

    headers_b = create_authenticated_user(client, "user_b")
    relationship_id_b = create_relationship(client, headers_b)

    create_journal_entry(client, headers_b, relationship_id_b)

    forbidden_list = client.get(entries_url_a, headers=headers_b)
    assert forbidden_list.status_code == 404

    forbidden_create = client.post(entries_url_a, json={
        "title": "hacked",
        "content": "changed"
    }, headers=headers_b)

    assert forbidden_create.status_code == 404

    forbidden_get = client.get(entry_url_a, headers=headers_b)
    assert forbidden_get.status_code == 404

    forbidden_update = client.put(entry_url_a, json={
        "title": "hacked",
        "content": "changed"
    }, headers=headers_b)

    assert forbidden_update.status_code == 404

    forbidden_delete = client.delete(entry_url_a, headers=headers_b)
    assert forbidden_delete.status_code == 404

    original_entry = client.get(entry_url_a, headers=headers_a)

    assert original_entry.status_code == 200
    assert original_entry.json()["title"] == "rame"
    assert original_entry.json()["content"] == "storyteling"


def test_journal_entry_pagination(client):
    headers = create_authenticated_user(client, "pagination_user")
    relationship_id = create_relationship(client, headers)

    create_journal_entry(
        client, headers, relationship_id, title="First"
    )

    entry2 = create_journal_entry(
        client, headers, relationship_id, title="Second"
    )

    entry3 = create_journal_entry(
        client, headers, relationship_id, title="Third"
    )

    response = client.get(
        f"/relationships/{relationship_id}/entries",
        params={"limit": 2, "offset": 1},
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert [entry["id"] for entry in data] == [entry2, entry3]


def test_journal_entry_validation(client):
    headers = create_authenticated_user(client, "validation_user")
    relationship_id = create_relationship(client, headers)

    response = client.post(
        f"/relationships/{relationship_id}/entries",
        json={
            "title": "",
            "content": "content"
        },
        headers=headers
    )

    assert response.status_code == 422


def test_relationship_cascade_delete(client):
    headers = create_authenticated_user(client, "cascade_user")
    relationship_id = create_relationship(client, headers)
    entry_id = create_journal_entry(client, headers, relationship_id)

    response = client.delete(
        f"/relationships/{relationship_id}",
        headers=headers
    )

    assert response.status_code == 200

    with TestingSessionLocal() as db:
        entry = db.query(models.JournalEntry).filter(
            models.JournalEntry.id == entry_id
        ).first()

        assert entry is None


def test_journal_entry_wrong_parent(client):
    headers_a = create_authenticated_user(client, "user_a")
    relationship_id_a = create_relationship(client, headers_a)
    entry_id_a = create_journal_entry(
        client, headers_a, relationship_id_a
    )

    headers_b = create_authenticated_user(client, "user_b")
    relationship_id_b = create_relationship(client, headers_b)

    wrong_url = f"/relationships/{relationship_id_b}/entries/{entry_id_a}"

    response = client.get(wrong_url, headers=headers_b)
    assert response.status_code == 404

    response = client.put(wrong_url, json={
        "title": "hacked",
        "content": "changed"
    }, headers=headers_b)

    assert response.status_code == 404

    response = client.delete(wrong_url, headers=headers_b)
    assert response.status_code == 404

    correct_url = f"/relationships/{relationship_id_a}/entries/{entry_id_a}"

    original = client.get(correct_url, headers=headers_a)

    assert original.status_code == 200
    assert original.json()["title"] == "rame"
    assert original.json()["content"] == "storyteling"


def test_unauthorized_access(client):
    headers = create_authenticated_user(client, "private_user")
    relationship_id = create_relationship(client, headers)
    entry_id = create_journal_entry(client, headers, relationship_id)

    entries_url = f"/relationships/{relationship_id}/entries"
    entry_url = f"{entries_url}/{entry_id}"

    assert client.get("/me").status_code == 401
    assert client.get("/relationships").status_code == 401
    assert client.get(entries_url).status_code == 401
    assert client.get(entry_url).status_code == 401

    response = client.post(entries_url, json={
        "title": "test",
        "content": "test"
    })
    assert response.status_code == 401

    response = client.put(entry_url, json={
        "title": "test",
        "content": "test"
    })
    assert response.status_code == 401

    assert client.delete(entry_url).status_code == 401




# ==================== SECURITY TESTS ====================

@pytest.mark.parametrize("scenario", [
    "expired",
    "missing_exp",
    "wrong_issuer",
    "wrong_audience",
    "invalid_subject",
    "wrong_signature"
])
def test_invalid_jwt_tokens(client, scenario):
    headers = create_authenticated_user(client, "security_user")
    token = headers["Authorization"].split(" ")[1]
    payload = security.decode_access_token(token)

    signing_key = security.JWT_SECRET

    if scenario == "expired":
        payload["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)

    elif scenario == "missing_exp":
        payload.pop("exp")

    elif scenario == "wrong_issuer":
        payload["iss"] = "unknown-issuer"

    elif scenario == "wrong_audience":
        payload["aud"] = "unknown-audience"

    elif scenario == "invalid_subject":
        payload["sub"] = "invalid-user-id"

    elif scenario == "wrong_signature":
        signing_key = "invalid-signing-key-for-testing-only"

    invalid_token = jwt.encode(
        payload,
        signing_key,
        algorithm=security.JWT_ALGORITHM
    )

    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {invalid_token}"}
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_malformed_token(client):
    response = client.get(
        "/me",
        headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401


@pytest.mark.parametrize("field,value", [
    ("password", "x9Q!z7"),
    ("gmail", "invalid-email"),
    ("username", "   ")
])
def test_signup_validation(client, field, value):
    payload = {
        "username": "security_user",
        "gmail": "security@gmail.com",
        "password": "secure-test-password123"
    }
    payload[field] = value
    response = client.post("/signup", json=payload)

    assert response.status_code == 422
    assert payload["password"] not in response.text

    errors = response.json()["detail"]
    assert len(errors) > 0

    for error in errors:
        assert set(error.keys()) == {"loc", "type", "msg"}



def test_login_rate_limit(client):
    for _ in range(10):
        response = client.post("/login", data={
            "username": "unknown@gmail.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    response = client.post("/login", data={
        "username": "unknown@gmail.com",
        "password": "wrongpassword"
    })

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_signup_rate_limit(client):
    for i in range(5):
        response = client.post("/signup", json={
            "username": f"rate_user_{i}",
            "gmail": f"rate_user_{i}@gmail.com",
            "password": "secure-test-password123"
        })
        assert response.status_code == 200

    response = client.post("/signup", json={
        "username": "blocked_user",
        "gmail": "blocked@gmail.com",
        "password": "secure-test-password123"
    })

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_redis_unavailable(client, monkeypatch):
    import rate_limit
    from redis.exceptions import RedisError

    def fail_eval(*args, **kwargs):
        raise RedisError("Connection failed")

    monkeypatch.setattr(
        rate_limit.redis_client,
        "eval",
        fail_eval
    )

    response = client.post("/login", data={
        "username": "user@gmail.com",
        "password": "wrongpassword"
    })

    assert response.status_code == 503


from uuid import uuid4
from redis import Redis
import rate_limit


@pytest.fixture(autouse=True)
def isolate_rate_limits(monkeypatch):
    test_url = os.getenv("REDIS_TEST_URL")

    if not test_url:
        raise RuntimeError("REDIS_TEST_URL is not configured")

    test_redis = Redis.from_url(
        test_url,
        socket_connect_timeout=2,
        socket_timeout=2
    )

    try:
        test_redis.ping()

        monkeypatch.setattr(
            rate_limit,
            "redis_client",
            test_redis
        )

        monkeypatch.setattr(
            rate_limit,
            "RATE_LIMIT_PREFIX",
            f"test:{uuid4().hex}"
        )

        yield

    finally:
        test_redis.close()

# FINAL BACKEND TESTS
def login_session(client, name):
    headers = create_authenticated_user(client, name)
    from web_config import REFRESH_COOKIE
    refresh = client.cookies.get(REFRESH_COOKIE)
    assert refresh
    return headers, refresh

def test_refresh_rotation_and_replay(client):
    from web_config import REFRESH_COOKIE
    old_headers, old_refresh = login_session(client, "rotation_user")
    response = client.post("/refresh")
    assert response.status_code == 200, response.text
    new_refresh = client.cookies.get(REFRESH_COOKIE)
    assert new_refresh != old_refresh
    new_headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    assert client.get("/me", headers=new_headers).status_code == 200
    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE, old_refresh)
    assert client.post("/refresh").status_code == 401
    assert client.get("/me", headers=old_headers).status_code == 401
    assert client.get("/me", headers=new_headers).status_code == 401
    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE, new_refresh)
    assert client.post("/refresh").status_code == 401

def test_concurrent_refresh_replay_revokes_session(client):
    from concurrent.futures import ThreadPoolExecutor
    from web_config import REFRESH_COOKIE
    headers, raw = login_session(client, "race_user")
    def refresh_once():
        with TestClient(app) as isolated_client:
            isolated_client.cookies.set(REFRESH_COOKIE, raw)
            return isolated_client.post("/refresh").status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: refresh_once(), range(2)))
    assert sorted(results) == [200, 401]
    assert client.get("/me", headers=headers).status_code == 401

def test_missing_session_claim(client):
    import jwt
    import security
    headers, _ = login_session(client, "missing_sid")
    payload = security.decode_access_token(headers["Authorization"].split()[1])
    del payload["sid"]
    token = jwt.encode(payload, security.JWT_SECRET, algorithm=security.JWT_ALGORITHM)
    assert client.get("/me", headers={"Authorization": "Bearer " + token}).status_code == 401

def test_logout_revokes_only_current_session(client):
    first, _ = login_session(client, "logout_user")
    login = client.post("/login", data={"username": "logout_user@gmail.com", "password": "testpassword123"})
    assert login.status_code == 200
    second = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.post("/logout").status_code == 200
    assert client.get("/me", headers=second).status_code == 401
    assert client.get("/me", headers=first).status_code == 200
    assert client.post("/refresh").status_code == 401

def test_refresh_hash_and_cookie(client):
    import sessions
    from web_config import REFRESH_COOKIE
    signup = client.post("/signup", json={"username": "cookie_user", "gmail": "cookie@gmail.com", "password": "testpassword123"})
    assert signup.status_code == 200
    login = client.post("/login", data={"username": "cookie@gmail.com", "password": "testpassword123"})
    assert login.status_code == 200
    raw = client.cookies.get(REFRESH_COOKIE)
    assert raw and raw not in login.text
    cookie = login.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    with TestingSessionLocal() as db:
        stored = db.query(models.RefreshToken).one()
        assert stored.token_hash == sessions.hash_refresh_token(raw)
        assert stored.token_hash != raw

def test_expired_session(client):
    from datetime import datetime, timedelta, timezone
    headers, _ = login_session(client, "expired_session")
    with TestingSessionLocal() as db:
        session = db.query(models.AuthSession).one()
        session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert client.get("/me", headers=headers).status_code == 401
    assert client.post("/refresh").status_code == 401

def test_refresh_origin_blocked(client):
    login_session(client, "origin_user")
    assert client.post("/refresh", headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert client.post("/refresh").status_code == 200

def test_delete_account_requires_password_and_cascades(client):
    headers, _ = login_session(client, "delete_user")
    rel_id = create_relationship(client, headers)
    create_journal_entry(client, headers, rel_id)
    wrong = client.request("DELETE", "/me", headers=headers, json={"password": "wrongpassword"})
    assert wrong.status_code == 403
    assert client.get("/me", headers=headers).status_code == 200
    good = client.request("DELETE", "/me", headers=headers, json={"password": "testpassword123"})
    assert good.status_code == 200
    assert client.get("/me", headers=headers).status_code == 401
    with TestingSessionLocal() as db:
        for model in (models.User, models.Relationship, models.JournalEntry, models.AuthSession, models.RefreshToken):
            assert db.query(model).count() == 0

def test_dashboard_export_and_search_ownership(client):
    a = create_authenticated_user(client, "dashboard_a")
    b = create_authenticated_user(client, "dashboard_b")
    rel_a = create_relationship(client, a, his_name="Alpha", status="active")
    rel_b = create_relationship(client, b, his_name="Alpha private", status="closed")
    entry_a = create_journal_entry(client, a, rel_a, title="Shared keyword")
    create_journal_entry(client, b, rel_b, title="Shared keyword")
    dashboard = client.get("/dashboard", headers=a)
    assert dashboard.status_code == 200
    assert dashboard.json() == {"relationships": 1, "journal_entries": 1, "by_status": {"active": 1}}
    export = client.get("/me/export", headers=a)
    assert export.status_code == 200
    data = export.json()
    assert "hashed_password" not in data["user"]
    assert [r["id"] for r in data["relationships"]] == [rel_a]
    assert [e["id"] for e in data["journal_entries"]] == [entry_a]
    assert [r["id"] for r in client.get("/relationships?search=alpha", headers=a).json()] == [rel_a]
    assert [e["id"] for e in client.get(f"/relationships/{rel_a}/entries?search=keyword", headers=a).json()] == [entry_a]
    assert client.get(f"/relationships/{rel_b}/entries?search=keyword", headers=a).status_code == 404
    assert client.get("/dashboard").status_code == 401
    assert client.get("/me/export").status_code == 401

def test_health_and_readiness(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}
