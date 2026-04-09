from fastapi.testclient import TestClient

from server.app import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_metadata_theme() -> None:
    response = client.get("/metadata")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "autonomous_traffic_control_env"
    assert (
        payload["description"]
        == "Multi-agent environment where AI systems manage a 4-way intersection with emergency vehicle prioritization."
    )


def test_reset_and_step_flow() -> None:
    reset_resp = client.post("/reset", json={"task_id": "easy-four-way-rush-hour"})
    assert reset_resp.status_code == 200
    reset_payload = reset_resp.json()

    assert "observation" in reset_payload
    assert reset_payload["done"] is False
    assert reset_payload["observation"]["task_id"] == "easy-four-way-rush-hour"
    assert len(reset_payload["observation"]["queue"]) == 2

    first_alert_id = reset_payload["observation"]["queue"][0]["alert_id"]
    step_resp = client.post(
        "/step",
        json={
            "action": {
                "action_type": "inspect_alert",
                "alert_id": first_alert_id,
            }
        },
    )
    assert step_resp.status_code == 200
    step_payload = step_resp.json()
    assert "observation" in step_payload
    assert step_payload["observation"]["step_count"] == 1
