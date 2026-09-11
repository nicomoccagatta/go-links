from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_healthz_is_ok(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_is_echoed_when_provided(client: TestClient) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "abc-123"})

    assert response.headers["x-request-id"] == "abc-123"


@pytest.mark.parametrize("incoming", [None, "not valid!", "a" * 129])
def test_request_id_is_generated_when_missing_or_invalid(
    client: TestClient, incoming: str | None
) -> None:
    headers = {"X-Request-ID": incoming} if incoming is not None else {}

    response = client.get("/healthz", headers=headers)

    assert UUID(response.headers["x-request-id"]).version == 4


def test_metrics_count_redirects_and_label_routes_by_template(client: TestClient) -> None:
    client.post("/api/links", json={"slug": "probe-hit", "target_url": "https://example.com"})
    client.get("/probe-hit")
    client.get("/probe-miss")

    body = client.get("/metrics").text

    assert 'golinks_redirects_total{result="hit"}' in body
    assert 'golinks_redirects_total{result="miss"}' in body
    assert 'http_requests_total{method="GET",route="/{slug}",status="302"}' in body
    assert "probe-hit" not in body
    assert "probe-miss" not in body


def test_unhandled_error_is_500_envelope_without_internals(
    app: FastAPI, client: TestClient
) -> None:
    def explode() -> None:
        raise RuntimeError("postgres://admin:hunter2@db")

    app.add_api_route("/boom/now", explode)

    response = client.get("/boom/now", headers={"X-Request-ID": "req-500"})

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "req-500"
    assert response.json()["error"]["code"] == "internal_error"
    assert response.json()["error"]["request_id"] == "req-500"
    assert "hunter2" not in response.text
