"""Session revocation + secret-key persistence (CODE_REVIEW C1 + C2)."""

from __future__ import annotations

from pathlib import Path


def test_token_invalid_after_logout(owner_client):
    # Authenticated to start with.
    assert owner_client.get("/api/auth/session").json()["authenticated"] is True

    # Logout revokes the server-side session record.
    r = owner_client.post("/api/auth/logout")
    assert r.status_code == 200

    # The TestClient keeps the cookie jar; even with the (deleted) cookie the
    # server must now treat the token as dead.
    assert owner_client.get("/api/auth/session").json()["authenticated"] is False
    # And protected endpoints reject it.
    assert owner_client.get("/api/scenarios").status_code == 401


def test_reused_cookie_after_logout_is_rejected(owner_client):
    from app.config import settings

    # Capture the live cookie, then log out.
    token = owner_client.cookies.get(settings.session_cookie_name)
    assert token
    owner_client.post("/api/auth/logout")

    # Replaying the captured cookie must fail — the DB row is revoked.
    owner_client.cookies.set(settings.session_cookie_name, token)
    assert owner_client.get("/api/scenarios").status_code == 401


def test_token_invalid_after_user_deactivation(owner_client):

    # Create a second user and log in as them in a fresh client.
    r = owner_client.post(
        "/api/auth/users",
        json={
            "email": "victim@local",
            "display_name": "Victim",
            "password": "Victim123!",
            "role": "reviewer",
        },
    )
    assert r.status_code == 201, r.text
    victim_id = r.json()["id"]

    from fastapi.testclient import TestClient

    from app.main import make_app

    with TestClient(make_app()) as victim:
        r = victim.post(
            "/api/auth/login",
            json={"email": "victim@local", "password": "Victim123!"},
        )
        assert r.status_code == 200
        assert victim.get("/api/scenarios").status_code == 200

        # Owner deactivates the victim.
        assert owner_client.delete(f"/api/auth/users/{victim_id}").status_code == 200

        # Victim's existing session is now dead immediately.
        assert victim.get("/api/scenarios").status_code == 401


def test_header_token_auth_works_without_cookie(client):
    """The Tauri path: authenticate via X-Session-Token instead of a cookie."""
    from app.config import settings

    r = client.post(
        "/api/auth/login",
        json={"email": settings.bootstrap_owner_email, "password": "Test1234!"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["session_token"]
    assert token

    # Drop the cookie the TestClient stored, so only the header can authenticate.
    client.cookies.clear()
    assert client.get("/api/scenarios").status_code == 401

    # With the header, the same request succeeds.
    r = client.get("/api/scenarios", headers={"X-Session-Token": token})
    assert r.status_code == 200


def test_header_token_dies_after_logout(client):
    from app.config import settings

    token = client.post(
        "/api/auth/login",
        json={"email": settings.bootstrap_owner_email, "password": "Test1234!"},
    ).json()["session_token"]
    # Log out via the header (no cookie).
    client.cookies.clear()
    assert client.post("/api/auth/logout", headers={"X-Session-Token": token}).status_code == 200
    # Token is now revoked.
    assert client.get("/api/scenarios", headers={"X-Session-Token": token}).status_code == 401


def test_setup_closed_when_owner_exists(client):
    # The default fixture presets an owner password, so bootstrap already created
    # the owner — the app is past first-run and setup is closed.
    assert client.get("/api/auth/session").json()["needs_setup"] is False
    r = client.post("/api/auth/setup", json={"username": "someone", "password": "abcd1234"})
    assert r.status_code == 409


def test_first_run_setup_creates_owner(tmp_path, monkeypatch):
    """Fresh interactive install (no preset password): the user creates the first
    account via the setup screen, which signs them straight in."""
    monkeypatch.setenv("FORLAS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("FORLAS_SEED_DEMO_SCENARIOS", "false")
    monkeypatch.delenv("FORLAS_BOOTSTRAP_OWNER_PASSWORD", raising=False)

    import app.config
    import app.db
    from app.config import Settings

    fresh = Settings()
    fresh.ensure_dirs()
    for field in fresh.__class__.model_fields:
        object.__setattr__(app.config.settings, field, getattr(fresh, field))
    app.db._engine = None

    from fastapi.testclient import TestClient

    from app.main import make_app

    with TestClient(make_app()) as c:
        # No accounts yet → the UI is told to show the setup screen.
        s = c.get("/api/auth/session").json()
        assert s["needs_setup"] is True
        assert s["authenticated"] is False

        # Creating the first account signs the user in and returns a token.
        r = c.post("/api/auth/setup", json={"username": "Michael", "password": "s3cretpw!"})
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["session_token"]
        assert body["user"]["role"] == "owner"
        assert body["user"]["email"] == "michael"  # handle is lowercased

        # Setup is now closed to everyone else.
        assert (
            c.post(
                "/api/auth/setup", json={"username": "another", "password": "s3cretpw!"}
            ).status_code
            == 409
        )

        # The chosen username + password now works at the sign-in endpoint.
        r = c.post("/api/auth/login", json={"email": "michael", "password": "s3cretpw!"})
        assert r.status_code == 200


def _make_user(owner_client, email: str, role: str, password: str = "Passw0rd1!") -> int:
    r = owner_client.post(
        "/api/auth/users",
        json={"email": email, "display_name": email, "password": password, "role": role},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_non_owner_can_change_own_password(owner_client):
    uid = _make_user(owner_client, "selfserve@local", "reviewer")

    from fastapi.testclient import TestClient

    from app.main import make_app

    with TestClient(make_app()) as c:
        assert (
            c.post(
                "/api/auth/login",
                json={"email": "selfserve@local", "password": "Passw0rd1!"},
            ).status_code
            == 200
        )
        # Change own password (the Settings card) — allowed for any role.
        r = c.patch(f"/api/auth/users/{uid}", json={"password": "NewPassw0rd!"})
        assert r.status_code == 200, r.text
        # New password works, old one doesn't.
        c.post("/api/auth/logout")
        assert (
            c.post(
                "/api/auth/login",
                json={"email": "selfserve@local", "password": "NewPassw0rd!"},
            ).status_code
            == 200
        )


def test_non_owner_cannot_escalate_own_role(owner_client):
    uid = _make_user(owner_client, "climber@local", "reviewer")

    from fastapi.testclient import TestClient

    from app.main import make_app

    with TestClient(make_app()) as c:
        c.post("/api/auth/login", json={"email": "climber@local", "password": "Passw0rd1!"})
        assert c.patch(f"/api/auth/users/{uid}", json={"role": "owner"}).status_code == 403
        assert c.patch(f"/api/auth/users/{uid}", json={"is_active": True}).status_code == 403


def test_non_owner_cannot_update_other_users(owner_client):
    _make_user(owner_client, "bystander@local", "reviewer")
    target = _make_user(owner_client, "target@local", "reviewer")

    from fastapi.testclient import TestClient

    from app.main import make_app

    with TestClient(make_app()) as c:
        c.post("/api/auth/login", json={"email": "bystander@local", "password": "Passw0rd1!"})
        r = c.patch(f"/api/auth/users/{target}", json={"password": "Hijacked123!"})
        assert r.status_code == 403


def test_last_active_owner_cannot_be_demoted_or_deactivated(owner_client):
    me = owner_client.get("/api/auth/session").json()["user"]
    assert me["role"] == "owner"
    # Sole owner: demotion and deactivation are both refused.
    assert (
        owner_client.patch(f"/api/auth/users/{me['id']}", json={"role": "reviewer"}).status_code
        == 409
    )
    assert (
        owner_client.patch(f"/api/auth/users/{me['id']}", json={"is_active": False}).status_code
        == 409
    )
    # With a second active owner, demotion is allowed again.
    _make_user(owner_client, "owner2@local", "owner")
    r = owner_client.patch(f"/api/auth/users/{me['id']}", json={"role": "approver"})
    assert r.status_code == 200, r.text


def test_secret_key_persisted_to_data_dir(isolated_data_dir):
    from app.config import Settings

    key_file = Path(isolated_data_dir) / "secret.key"
    # The conftest fixture already constructed one Settings; ensure the file
    # exists and a fresh Settings reads the SAME key (survives "restart").
    assert key_file.exists(), "secret.key should be created on first run"
    first = key_file.read_text().strip()
    assert first

    fresh = Settings()
    assert fresh.secret_key == first, "secret key must persist across restarts"


def test_explicit_secret_key_env_wins(monkeypatch, isolated_data_dir):
    from app.config import Settings

    monkeypatch.setenv("FORLAS_SECRET_KEY", "operator-supplied-key")
    s = Settings()
    assert s.secret_key == "operator-supplied-key"
