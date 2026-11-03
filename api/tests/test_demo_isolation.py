import db
import main

PNG = ("skan.png", b"\x89PNG\r\n\x1a\nfake", "image/png")


async def start_demo(client, ip="10.0.0.1"):
    r = await client.post("/auth/demo", headers={"X-Forwarded-For": ip})
    assert r.status_code == 200, r.text
    d = r.json()
    return {
        "key": {"Authorization": f"Bearer {d['api_key']}", "X-Forwarded-For": ip},
        "jwt": {"Authorization": f"Bearer {d['token']}", "X-Forwarded-For": ip},
        "user": d["user"],
    }


async def scan(client, s, **extra):
    return await client.post("/v1/scan", headers={**s["key"], **extra}, files={"file": PNG})


async def test_demo_session_is_separate_account(client):
    a = await start_demo(client)
    b = await start_demo(client)
    assert a["user"]["id"] != b["user"]["id"]
    assert a["user"]["is_demo"] is True
    assert a["user"]["scans_limit"] == main.settings.demo_scans_limit == 10

    me = await client.get("/auth/me", headers=a["jwt"])
    assert me.status_code == 200
    assert me.json()["is_demo"] is True and me.json()["expires_at"]


async def test_two_demo_sessions_do_not_see_each_others_documents(client):
    a = await start_demo(client, "10.0.0.1")
    b = await start_demo(client, "10.0.0.2")

    r = await scan(client, a)
    assert r.status_code == 200, r.text
    scan_id = r.json()["scan_id"]

    docs_a = (await client.get("/v1/documents", headers=a["key"])).json()
    docs_b = (await client.get("/v1/documents", headers=b["key"])).json()
    assert docs_a["total"] == 1 and docs_a["documents"][0]["id"] == scan_id
    assert docs_b["total"] == 0 and docs_b["documents"] == []

    # Bezpośredni dostęp po ID, eksporty i usuwanie — też niedostępne dla B
    for path in (f"/v1/documents/{scan_id}", f"/v1/documents/{scan_id}/export.txt",
                 f"/v1/documents/{scan_id}/export.md", f"/v1/documents/{scan_id}/export.csv"):
        assert (await client.get(path, headers=b["key"])).status_code == 404, path
    assert scan_id not in (await client.get("/v1/documents/export", headers=b["key"])).text
    assert scan_id not in (await client.get("/v1/documents/export.md", headers=b["key"])).text
    assert (await client.delete(f"/v1/documents/{scan_id}", headers=b["key"])).status_code == 404
    assert (await client.get("/v1/stats", headers=b["key"])).json()["total_scans"] == 0

    # Shared demo key from the old setup sees nothing from demo sessions either
    shared = {"Authorization": "Bearer mk_prod_demo123"}
    assert (await client.get("/v1/documents", headers=shared)).json()["total"] == 0
    assert (await client.get(f"/v1/documents/{scan_id}", headers=shared)).status_code == 404


async def test_expired_demo_is_rejected_and_purged(client):
    a = await start_demo(client)
    assert (await scan(client, a)).status_code == 200
    # Regularny klient — jego dane nie mogą zniknąć przy czyszczeniu
    regular = {"Authorization": "Bearer mk_prod_demo123"}
    assert (await client.post("/v1/scan", headers=regular, files={"file": PNG})).status_code == 200

    pool = db.get_pool()
    await pool.execute("UPDATE users SET expires_at = NOW() - interval '1 minute' WHERE is_demo")
    await pool.execute("UPDATE api_keys SET expires_at = NOW() - interval '1 minute' WHERE is_demo")

    # Wygasły klucz nie daje już dostępu, nawet przed czyszczeniem
    assert (await client.get("/v1/documents", headers=a["key"])).status_code == 403

    result = await db.purge_expired_demo()
    assert result == {"users": 1, "api_keys": 1, "scans": 1}
    assert await pool.fetchval("SELECT COUNT(*) FROM users WHERE is_demo") == 0
    assert await pool.fetchval("SELECT COUNT(*) FROM api_keys WHERE is_demo") == 0
    assert await pool.fetchval("SELECT COUNT(*) FROM scans") == 1  # tylko skan klienta
    assert (await client.get("/v1/documents", headers=regular)).json()["total"] == 1


async def test_purge_keeps_active_demo_sessions(client):
    a = await start_demo(client, "10.0.0.1")
    b = await start_demo(client, "10.0.0.2")
    await scan(client, a)
    await scan(client, b)
    await db.get_pool().execute(
        "UPDATE users SET expires_at = NOW() - interval '1 minute' WHERE id = $1::uuid", a["user"]["id"]
    )
    assert (await db.purge_expired_demo())["scans"] == 1
    assert (await client.get("/v1/documents", headers=b["key"])).json()["total"] == 1


async def test_end_demo_deletes_data_immediately(client):
    a = await start_demo(client)
    await scan(client, a)
    r = await client.post("/auth/demo/end", headers=a["jwt"])
    assert r.status_code == 200 and r.json()["scans"] == 1
    assert (await client.get("/v1/documents", headers=a["key"])).status_code == 403
    assert await db.get_pool().fetchval("SELECT COUNT(*) FROM scans") == 0


async def test_demo_scan_quota(client, monkeypatch):
    a = await start_demo(client)
    await db.get_pool().execute("UPDATE api_keys SET scans_limit = 2 WHERE is_demo")
    assert (await scan(client, a)).status_code == 200
    assert (await scan(client, a)).status_code == 200
    assert (await scan(client, a)).status_code == 429


async def test_demo_blocks_email_ikz_mobile_webhook_and_keys(client):
    a = await start_demo(client)
    scan_id = (await scan(client, a)).json()["scan_id"]

    r = await client.post("/v1/documents/send-email", headers=a["key"], json={"scan_id": scan_id, "to": "x@example.com"})
    assert r.status_code == 403
    assert (await scan(client, a, **{"X-IKZ-Silos-Id": "123"})).status_code == 403
    key_id = (await client.get("/v1/api-keys", headers=a["key"])).json()["keys"][0]["key_id"]
    r = await client.patch(f"/v1/api-keys/{key_id}/webhook", headers=a["key"], json={"webhook_url": "https://evil.example"})
    assert r.status_code == 403
    r = await client.post("/v1/api-keys", headers=a["key"], json={"name": "x", "facility_name": "y"})
    assert r.status_code == 403


async def test_api_key_listing_isolation(client):
    a = await start_demo(client, "10.0.0.1")
    b = await start_demo(client, "10.0.0.2")
    keys_a = (await client.get("/v1/api-keys", headers=a["key"])).json()["keys"]
    assert len(keys_a) == 1 and keys_a[0]["plan"] == "demo_guest"
    # Lista dla zwykłego klucza nie pokazuje gości demo
    regular = (await client.get("/v1/api-keys", headers={"Authorization": "Bearer mk_prod_demo123"})).json()["keys"]
    assert all(k["plan"] != "demo_guest" for k in regular)
    assert b["user"]["id"]


async def test_demo_session_rate_limit_per_ip(client):
    for _ in range(main.settings.demo_sessions_per_ip_per_hour):
        await start_demo(client, "10.9.9.9")
    r = await client.post("/auth/demo", headers={"X-Forwarded-For": "10.9.9.9"})
    assert r.status_code == 429
    # Inny adres nadal może zacząć demo
    await start_demo(client, "10.9.9.10")
    # Sfałszowany pierwszy wpis X-Forwarded-For nie omija limitu (liczy się ostatni)
    r = await client.post("/auth/demo", headers={"X-Forwarded-For": "1.2.3.4, 10.9.9.9"})
    assert r.status_code == 429


async def test_demo_scans_rate_limited_per_ip_across_sessions(client):
    main.demo_scan_limiter.max_hits = 3
    try:
        sessions = [await start_demo(client, "10.7.7.7") for _ in range(2)]
        codes = [(await scan(client, sessions[i % 2])).status_code for i in range(4)]
        assert codes == [200, 200, 200, 429]
    finally:
        main.demo_scan_limiter.max_hits = main.settings.demo_scans_per_ip_per_hour


async def test_shared_demo_login_is_blocked(client):
    r = await client.post("/auth/login", json={"email": "demo@ikzocr.pl", "password": "cokolwiek"})
    assert r.status_code == 403


async def test_demo_account_cannot_log_in_with_password(client):
    a = await start_demo(client)
    r = await client.post("/auth/login", json={"email": a["user"]["email"], "password": ""})
    assert r.status_code == 401
