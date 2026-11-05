from fastapi.testclient import TestClient

from app.main import app


def test_metrics_and_bounded_route_labels(monkeypatch):
    monkeypatch.setenv("FAIL_RATE", "0")
    client = TestClient(app)
    assert client.get("/api/tasks/123456789").status_code == 405
    assert client.get("/api/tasks").status_code == 200
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "trackhub_http_requests_total" in metrics.text
    assert "trackhub_http_request_duration_seconds_bucket" in metrics.text
    assert 'route="/api/tasks"' in metrics.text
    assert 'route="/api/tasks/{task_id}"' in metrics.text
    assert "123456789" not in metrics.text


def test_fail_rate_produces_observable_500_without_breaking_health(monkeypatch, capsys):
    monkeypatch.setenv("FAIL_RATE", "1")
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/api/tasks").status_code == 500
    assert 'route="/api/tasks",status="500"' in client.get("/metrics").text
    assert '"status": 500' in capsys.readouterr().out
