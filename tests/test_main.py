from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_home_ui_status():
    response = client.get("/")
    assert response.status_code == 200
    assert "TrackHub Engine" in response.text

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