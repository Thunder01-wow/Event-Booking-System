def test_health(client):
    assert client.get("/health").status_code == 200


def test_no_token_is_401(client):
    assert client.get("/bookings").status_code == 401
    assert client.post("/bookings", json={"event_id": "00000000-0000-0000-0000-000000000000"}).status_code == 401


def test_garbage_token_is_401(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_login_wrong_password_is_401(client, alice):
    r = client.post("/auth/login", data={"username": alice.email, "password": "wrong-password"})
    assert r.status_code == 401


def test_me_returns_current_user(client, alice):
    r = client.get("/auth/me", headers=alice.headers)
    assert r.status_code == 200 and r.json()["email"] == alice.email


def test_normal_user_cannot_use_admin_routes(client, alice, event):
    r = client.patch(f"/admin/events/{event['id']}", json={"title": "Hacked"}, headers=alice.headers)
    assert r.status_code == 403


def test_admin_can_update_event_and_set_image(client, admin_user, event):
    r = client.patch(f"/admin/events/{event['id']}", json={"image_url": "https://example.com/x.jpg"}, headers=admin_user.headers)
    assert r.status_code == 200, r.text
    assert client.get(f"/events/{event['id']}").json()["image_url"] == "https://example.com/x.jpg"
