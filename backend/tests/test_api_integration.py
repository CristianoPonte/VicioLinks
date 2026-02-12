import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app import main
from backend.app.models import UserInDB


class FakeResponse:
    def __init__(self, data=None, count=None):
        self.data = data if data is not None else []
        self.count = count


class FakeRpcCall:
    def __init__(self, response):
        self._response = response

    def execute(self):
        return self._response


class FakeQuery:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self._op = "select"
        self._filters = []
        self._payload = None
        self._count = None
        self._order_field = None
        self._order_desc = False
        self._limit = None

    def select(self, _columns="*", count=None):
        self._op = "select"
        self._count = count
        return self

    def eq(self, key, value):
        self._filters.append((key, value))
        return self

    def order(self, field, desc=False):
        self._order_field = field
        self._order_desc = desc
        return self

    def limit(self, value):
        self._limit = value
        return self

    def upsert(self, payload):
        self._op = "upsert"
        self._payload = payload
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    def execute(self):
        rows = self.db.tables.setdefault(self.table_name, [])
        primary_key = self.db.primary_keys.get(self.table_name)

        def matches(row):
            return all(row.get(k) == v for k, v in self._filters)

        if self._op == "select":
            result = [r.copy() for r in rows if matches(r)]
            total_count = len(result)
            if self._order_field:
                result.sort(key=lambda x: x.get(self._order_field), reverse=self._order_desc)
            if self._limit is not None:
                result = result[: self._limit]
            return FakeResponse(data=result, count=total_count if self._count == "exact" else None)

        if self._op in {"insert", "upsert"}:
            payload = self._payload.copy()
            if primary_key and payload.get(primary_key) is not None:
                idx = next((i for i, r in enumerate(rows) if r.get(primary_key) == payload[primary_key]), None)
                if idx is not None:
                    rows[idx] = {**rows[idx], **payload}
                else:
                    rows.append(payload)
            else:
                rows.append(payload)
            return FakeResponse(data=[payload])

        if self._op == "update":
            updated = []
            for i, row in enumerate(rows):
                if matches(row):
                    rows[i] = {**row, **self._payload}
                    updated.append(rows[i].copy())
            return FakeResponse(data=updated)

        if self._op == "delete":
            kept = []
            deleted = []
            for row in rows:
                if matches(row):
                    deleted.append(row)
                else:
                    kept.append(row)
            self.db.tables[self.table_name] = kept
            return FakeResponse(data=deleted)

        return FakeResponse(data=[])


class FakeDB:
    def __init__(self):
        self.primary_keys = {
            "users": "username",
            "launches": "slug",
            "source_configs": "slug",
            "products": "slug",
            "turmas": "slug",
            "launch_types": "slug",
            "links": "id",
            "settings": "id",
            "audits": "event_id",
        }
        self.tables = {
            "users": [],
            "launches": [],
            "source_configs": [],
            "products": [],
            "turmas": [],
            "launch_types": [],
            "links": [],
            "settings": [{"id": "link_counter", "count": 0}],
            "audits": [],
        }

    def table(self, table_name):
        return FakeQuery(self, table_name)

    def rpc(self, function_name, args):
        if function_name != "increment_link_counter":
            return FakeRpcCall(FakeResponse(data=None))
        row_id = args["row_id"]
        settings = self.tables["settings"]
        row = next((r for r in settings if r["id"] == row_id), None)
        if row is None:
            row = {"id": row_id, "count": 0}
            settings.append(row)
        row["count"] += 1
        return FakeRpcCall(FakeResponse(data=row["count"]))


class ApiIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        admin_user = UserInDB(
            username="admin",
            role="admin",
            disabled=False,
            hashed_password=main.get_password_hash("admin123"),
        ).model_dump()
        self.db.tables["users"].append(admin_user)

        self.get_db_patch = patch("backend.app.main.get_db", return_value=self.db)
        self.get_db_patch.start()

        main.app.dependency_overrides[main.get_current_active_user] = lambda: {"username": "admin", "role": "admin"}
        main.app.dependency_overrides[main.require_admin] = lambda: {"username": "admin", "role": "admin"}
        main.app.dependency_overrides[main.require_editor] = lambda: {"username": "admin", "role": "admin"}

        self.client = TestClient(main.app)

    def tearDown(self):
        main.app.dependency_overrides = {}
        self.get_db_patch.stop()

    def test_token_endpoint_success_and_failure(self):
        with patch("backend.app.main.authenticate_user") as auth_mock, patch("backend.app.main.create_access_token") as token_mock:
            auth_mock.return_value = type("U", (), {"username": "admin", "role": "admin"})()
            token_mock.return_value = "fake-jwt"
            ok = self.client.post("/token", data={"username": "admin", "password": "admin123"})
            self.assertEqual(ok.status_code, 200)
            self.assertEqual(ok.json()["access_token"], "fake-jwt")

            auth_mock.return_value = None
            bad = self.client.post("/token", data={"username": "admin", "password": "wrong"})
            self.assertEqual(bad.status_code, 401)

    def test_users_endpoints(self):
        me = self.client.get("/users/me")
        self.assertEqual(me.status_code, 200)

        listing = self.client.get("/users")
        self.assertEqual(listing.status_code, 200)
        self.assertGreaterEqual(len(listing.json()), 1)

        created = self.client.post("/users", json={"username": "editor1", "password": "abc123", "role": "user"})
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["username"], "editor1")

        updated = self.client.put("/users/editor1", json={"username": "editor1", "password": "newpass", "role": "viewer"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["role"], "viewer")

        deleted = self.client.delete("/users/editor1")
        self.assertEqual(deleted.status_code, 200)

    def test_launches_endpoints(self):
        created = self.client.post("/launches", json={"slug": "vde1f_90d_evento_0124", "nome": "Campanha 1", "owner": "admin", "status": "active"})
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["slug"], "vde1f_90d_evento_01-24")

        listing = self.client.get("/launches")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()[0]["slug"], "vde1f_90d_evento_01-24")

        deleted = self.client.delete("/launches/vde1f_90d_evento_01-24")
        self.assertEqual(deleted.status_code, 200)

    def test_source_configs_endpoints(self):
        payload = {
            "slug": "instagram",
            "name": "Instagram",
            "config": {
                "mediums": [{"slug": "feed", "name": "Feed"}],
                "contents": [{"slug": "bio", "name": "Bio"}],
                "term_config": "standard",
                "required_fields": ["date"],
            },
        }
        created = self.client.post("/source-configs", json=payload)
        self.assertEqual(created.status_code, 200)

        listing = self.client.get("/source-configs")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()[0]["slug"], "instagram")

        deleted = self.client.delete("/source-configs/instagram")
        self.assertEqual(deleted.status_code, 200)

    def test_catalog_endpoints(self):
        product = self.client.post("/products", json={"slug": "vde1f", "nome": "VDE1F"})
        turma = self.client.post("/turmas", json={"slug": "120d", "nome": "Turma 120d"})
        ltype = self.client.post("/launch-types", json={"slug": "evento", "nome": "Evento"})
        self.assertEqual(product.status_code, 200)
        self.assertEqual(turma.status_code, 200)
        self.assertEqual(ltype.status_code, 200)

        self.assertEqual(self.client.get("/products").status_code, 200)
        self.assertEqual(self.client.get("/turmas").status_code, 200)
        self.assertEqual(self.client.get("/launch-types").status_code, 200)

    def test_links_generate_and_list_captacao(self):
        resp = self.client.post(
            "/links/generate",
            json={
                "link_type": "captacao",
                "base_url": "https://lp.exemplo.com",
                "path": "/oferta",
                "utm_source": "Instagram",
                "utm_medium": "Feed",
                "utm_campaign": "Camp_1",
                "utm_content": "Bio",
                "utm_term": "cta",
                "custom_params": {"foo": "bar"},
                "dynamic_fields": {},
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("utm_id=", data["full_url"])
        self.assertIn("utm_source=instagram", data["full_url"])
        self.assertEqual(data["src"], None)
        self.assertEqual(data["sck"], None)
        self.assertEqual(data["xcode"], None)

        listing = self.client.get("/links")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.json()), 1)

    def test_links_generate_and_list_vendas(self):
        resp = self.client.post(
            "/links/generate",
            json={
                "link_type": "vendas",
                "base_url": "https://metodovde.com.br",
                "path": "/concursos/carreirasjuridicas",
                "utm_source": "WhatsApp",
                "utm_medium": "api_disparos",
                "utm_campaign": "vde1f_90d_evento_0124",
                "utm_content": "grupos_antigos",
                "utm_term": "aaa_12022026",
                "custom_params": {"coupon": "ABC", "utm_id": "should_not_win"},
                "dynamic_fields": {},
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("utm_source=whatsapp", data["full_url"])
        self.assertIn("utm_medium=api_disparos", data["full_url"])
        self.assertIn("utm_campaign=vde1f_90d_evento_01-24", data["full_url"])
        self.assertIn("utm_content=grupos_antigos", data["full_url"])
        self.assertIn("utm_term=aaa_12-02-2026", data["full_url"])
        self.assertIn("xcode=", data["full_url"])
        self.assertIn("src=whatsapp_grupos_antigos", data["full_url"])
        self.assertIn("sck=api_disparos", data["full_url"])
        self.assertIn("coupon=ABC", data["full_url"])
        self.assertNotIn("utm_id=", data["full_url"])

        self.assertEqual(data["utm_campaign"], "vde1f_90d_evento_01-24")
        self.assertEqual(data["utm_term"], "aaa_12-02-2026")
        self.assertEqual(data["src"], "whatsapp_grupos_antigos")
        self.assertEqual(data["sck"], "api_disparos")
        self.assertTrue(data["xcode"].startswith("lnk_"))

    def test_delete_link_endpoint(self):
        created = self.client.post(
            "/links/generate",
            json={
                "link_type": "captacao",
                "base_url": "https://lp.exemplo.com",
                "path": "/oferta",
                "utm_source": "instagram",
                "utm_medium": "feed",
                "utm_campaign": "camp_delete",
                "utm_content": "bio",
                "utm_term": "cta",
                "custom_params": {},
                "dynamic_fields": {},
            },
        )
        self.assertEqual(created.status_code, 200)
        link_id = created.json()["id"]

        deleted = self.client.delete(f"/links/{link_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["status"], "deleted")

        listing = self.client.get("/links")
        self.assertEqual(listing.status_code, 200)
        ids = [item["id"] for item in listing.json()]
        self.assertNotIn(link_id, ids)

    def test_links_list_filters(self):
        payloads = [
            {
                "link_type": "captacao",
                "base_url": "https://lp.exemplo.com",
                "utm_source": "instagram",
                "utm_medium": "feed",
                "utm_campaign": "camp_a",
            },
            {
                "link_type": "captacao",
                "base_url": "https://lp.exemplo.com",
                "utm_source": "email",
                "utm_medium": "newsletter",
                "utm_campaign": "camp_b",
            },
            {
                "link_type": "vendas",
                "base_url": "https://checkout.exemplo.com",
                "utm_source": "whatsapp",
                "utm_medium": "api_disparos",
                "utm_campaign": "camp_c",
            },
        ]
        for p in payloads:
            req = {
                "path": "",
                "utm_content": "bio",
                "utm_term": "cta",
                "custom_params": {},
                "dynamic_fields": {},
                **p,
            }
            result = self.client.post("/links/generate", json=req)
            self.assertEqual(result.status_code, 200)

        filtered = self.client.get("/links", params={"utm_source": "email"})
        self.assertEqual(filtered.status_code, 200)
        items = filtered.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["utm_source"], "email")

        by_type = self.client.get("/links", params={"link_type": "captacao"})
        self.assertEqual(by_type.status_code, 200)
        self.assertEqual(len(by_type.json()), 2)

        by_type_vendas = self.client.get("/links", params={"link_type": "vendas"})
        self.assertEqual(by_type_vendas.status_code, 200)
        self.assertEqual(len(by_type_vendas.json()), 1)


if __name__ == "__main__":
    unittest.main()
