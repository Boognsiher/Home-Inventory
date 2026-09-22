from config import Config


def test_kein_login_noetig_wenn_kein_passwort_gesetzt(client):
    assert not Config.APP_PASSWORT
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 200


def test_redirect_zu_login_wenn_passwort_gesetzt(client, monkeypatch):
    monkeypatch.setattr(Config, "APP_PASSWORT", "geheim123")
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_mit_falschem_passwort(client, monkeypatch):
    monkeypatch.setattr(Config, "APP_PASSWORT", "geheim123")
    resp = client.post("/login", data={"passwort": "falsch"})
    assert resp.status_code == 200
    assert "Falsches Passwort".encode() in resp.data


def test_login_mit_richtigem_passwort_gewaehrt_zugriff(client, monkeypatch):
    monkeypatch.setattr(Config, "APP_PASSWORT", "geheim123")

    resp = client.post("/login", data={"passwort": "geheim123"}, follow_redirects=True)
    assert resp.status_code == 200
    assert "Übersicht".encode() in resp.data

    resp2 = client.get("/inventar")
    assert resp2.status_code == 200


def test_logout_entfernt_zugriff(client, monkeypatch):
    monkeypatch.setattr(Config, "APP_PASSWORT", "geheim123")

    client.post("/login", data={"passwort": "geheim123"})
    client.post("/logout")

    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
