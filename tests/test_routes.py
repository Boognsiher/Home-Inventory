def test_dashboard_laedt(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Übersicht".encode() in resp.data


def test_standort_anlegen_und_anzeigen(client):
    resp = client.post("/standorte/neu", data={"name": "Werkstatt Regal 1", "beschreibung": "Test"}, follow_redirects=True)
    assert resp.status_code == 200
    assert "Werkstatt Regal 1".encode() in resp.data


def _standort_id(client):
    from db import load_db
    client.post("/standorte/neu", data={"name": "Regal A"})
    db = load_db()
    return next(iter(db["standorte"]))


def _behaelter_id(client):
    from db import load_db
    sid = _standort_id(client)
    client.post("/behaelter/neu", data={"name": "Kiste 1", "standort_id": sid})
    db = load_db()
    return next(iter(db["behaelter"]))


def test_behaelter_anlegen(client):
    bid = _behaelter_id(client)
    resp = client.get(f"/behaelter/{bid}")
    assert resp.status_code == 200
    assert "Kiste 1".encode() in resp.data


def test_behaelter_qr_code(client):
    bid = _behaelter_id(client)
    resp = client.get(f"/behaelter/{bid}/qr.png")
    assert resp.status_code == 200
    assert resp.content_type == "image/png"


def test_item_anlegen_und_ausbuchen(client):
    bid = _behaelter_id(client)
    resp = client.post(
        "/items/neu",
        data={"name": "M4x20 Schraube", "behaelter_id": bid, "menge": "10", "einheit": "Stk"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "M4x20 Schraube".encode() in resp.data

    from db import load_db
    iid = next(iter(load_db()["items"]))

    resp = client.post(f"/api/items/{iid}/ausbuchen", json={"menge": 3})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["neue_menge"] == 7


def test_inventar_suche(client):
    bid = _behaelter_id(client)
    client.post("/items/neu", data={"name": "Kreuzschlitzschraube", "behaelter_id": bid, "menge": "5"}, follow_redirects=True)
    client.post("/items/neu", data={"name": "USB-Kabel", "behaelter_id": bid, "menge": "2"}, follow_redirects=True)

    resp = client.get("/inventar?q=schraube")
    assert "Kreuzschlitzschraube".encode() in resp.data
    assert "USB-Kabel".encode() not in resp.data


def test_einstellungen_seite(client):
    resp = client.get("/einstellungen")
    assert resp.status_code == 200


def test_export_json(client):
    resp = client.get("/export/json")
    assert resp.status_code == 200
    assert resp.mimetype == "application/json"


def test_export_xlsx(client):
    resp = client.get("/export/xlsx")
    assert resp.status_code == 200
