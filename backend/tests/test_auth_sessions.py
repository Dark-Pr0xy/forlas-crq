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
    from app.config import settings

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
