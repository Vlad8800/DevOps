from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_home_ui_status():
    response = client.get("/")
    assert response.status_code == 200
    assert "TrackHub Engine" in response.text

def test_version_is_visible_in_app_and_health(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.0")
    assert client.get("/version").json() == {"version": "1.2.0"}
    assert client.get("/health").json() == {"status": "ok", "version": "1.2.0"}
    assert "Version: 1.2.0" in client.get("/").text

def test_create_and_get_task():
    create_res = client.post("/api/tasks", json={
        "title": "CI/CD pipeline sanity check",
        "service_tag": "ci-runner",
        "priority": "high"
    })
    assert create_res.status_code == 200
    task_id = create_res.json()["id"]

    list_res = client.get("/api/tasks")
    assert list_res.status_code == 200
    ids = [t["id"] for t in list_res.json()]
    assert task_id in ids
