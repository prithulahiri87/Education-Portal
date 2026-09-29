import secrets
from datetime import date, timedelta

from app.seed_data import seed


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["service"] == "harbor-crm"
    assert body["database"] == "sqlite"
    assert body["auth_required"] is False


def test_lead_crud_and_search(client):
    created = client.post(
        "/api/leads",
        json={
            "first_name": "Jonah",
            "last_name": "Hale",
            "company": "Bright Parcel Co",
            "email": "jonah.hale@example.com",
            "status": "New",
            "source": "Web",
        },
    )
    assert created.status_code == 201
    lead_id = created.json()["id"]
    assert client.get("/api/leads", params={"q": "Jonah"}).json()["total"] == 1
    assert client.get("/api/leads", params={"q": "%"}).json()["total"] == 0
    patched = client.patch("/api/leads/" + lead_id, json={"status": "Working"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "Working"
    assert client.delete("/api/leads/" + lead_id).status_code == 204
    assert client.get("/api/leads/" + lead_id).status_code == 404


def test_convert_lead_is_one_way(client):
    created = client.post(
        "/api/leads",
        json={"first_name": "Ada", "last_name": "Brooks", "company": "Northwind Goods"},
    )
    lead_id = created.json()["id"]
    converted = client.post(
        "/api/leads/" + lead_id + "/convert",
        json={"create_opportunity": True, "opportunity_name": "Warehouse refresh"},
    )
    assert converted.status_code == 200
    body = converted.json()
    assert body["lead"]["status"] == "Converted"
    assert body["account"]["name"] == "Northwind Goods"
    assert body["contact"]["email"] is None
    assert body["opportunity"]["stage"] == "Prospecting"
    assert body["opportunity"]["account_id"] == body["account"]["id"]
    again = client.post("/api/leads/" + lead_id + "/convert", json={})
    assert again.status_code == 409
    readonly = client.patch("/api/leads/" + lead_id, json={"status": "Working"})
    assert readonly.status_code == 409


def test_quote_math_and_rejected_client_total(client):
    account = client.post("/api/accounts", json={"name": "Northwind Goods"}).json()
    contact = client.post(
        "/api/contacts",
        json={"account_id": account["id"], "first_name": "Ada", "last_name": "Brooks"},
    ).json()
    close_date = (date.today() + timedelta(days=30)).isoformat()
    opportunity = client.post(
        "/api/opportunities",
        json={"account_id": account["id"], "name": "Racking", "close_date": close_date},
    ).json()
    quote = client.post(
        "/api/quotes",
        json={"opportunity_id": opportunity["id"], "contact_id": contact["id"], "name": "Q-1042"},
    ).json()
    rejected = client.post(
        "/api/quotes",
        json={
            "opportunity_id": opportunity["id"],
            "name": "Q-hack",
            "grand_total": "1.00",
        },
    )
    assert rejected.status_code == 422
    client.post(
        "/api/quotes/" + quote["id"] + "/line-items",
        json={"product_name": "Racking", "quantity": "2", "unit_price": "100.00", "discount_percent": "10"},
    )
    client.post(
        "/api/quotes/" + quote["id"] + "/line-items",
        json={"product_name": "Install", "quantity": "1", "unit_price": "50.00", "discount_percent": "0"},
    )
    updated = client.patch(
        "/api/quotes/" + quote["id"],
        json={"discount_percent": "10", "tax_percent": "8", "status": "Accepted"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["subtotal"] == 230.0
    assert body["discount_amount"] == 23.0
    assert body["tax_amount"] == 16.56
    assert body["grand_total"] == 223.56
    opportunity = client.get("/api/opportunities/" + opportunity["id"]).json()
    assert opportunity["amount"] == 223.56
    mismatch = client.post(
        "/api/contacts",
        json={
            "account_id": "00000000-0000-4000-8000-000000000099",
            "first_name": "No",
            "last_name": "Account",
        },
    )
    assert mismatch.status_code == 422


def test_account_delete_is_blocked_while_contacts_exist(client):
    account = client.post("/api/accounts", json={"name": "Lumen Field Clinics"}).json()
    contact = client.post(
        "/api/contacts",
        json={"account_id": account["id"], "first_name": "Mina", "last_name": "Ortiz"},
    ).json()
    blocked = client.delete("/api/accounts/" + account["id"])
    assert blocked.status_code == 409
    assert client.delete("/api/contacts/" + contact["id"]).status_code == 204
    assert client.delete("/api/accounts/" + account["id"]).status_code == 204


def test_token_is_required_when_configured(client, monkeypatch):
    token = secrets.token_urlsafe(16)
    monkeypatch.setenv("CRM_API_TOKEN", token)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/leads").status_code == 401
    assert client.get("/api/leads").json()["detail"] == "Authentication required"
    allowed = client.get("/api/leads", headers={"Authorization": "Bearer " + token})
    assert allowed.status_code == 200


def test_seed_is_idempotent(client):
    assert seed() is True
    assert seed() is False
    assert client.get("/api/accounts").json()["total"] == 2
    assert client.get("/api/contacts").json()["total"] == 3
    assert client.get("/api/opportunities").json()["total"] == 3
    assert client.get("/api/quotes").json()["total"] == 2
    assert client.get("/api/leads").json()["total"] == 3
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["counts"]["quote_line_items"] == 4
    assert len(dashboard["pipeline"]) == 7
    lines = client.get("/api/quotes/99999999-9999-4999-8999-999999999999/line-items").json()
    assert lines["total"] == 2
