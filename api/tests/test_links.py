from typing import Any

import pytest
from fastapi.testclient import TestClient

VALID_LINK = {"slug": "oncall", "target_url": "https://oncall.example.com/schedule"}


def test_create_returns_201_with_location(client: TestClient) -> None:
    response = client.post(
        "/api/links", json={**VALID_LINK, "slug": "  OnCall ", "description": "Who's on call"}
    )

    assert response.status_code == 201
    assert response.headers["location"] == "/api/links/oncall"
    body = response.json()
    assert body["slug"] == "oncall"
    assert body["target_url"] == VALID_LINK["target_url"]
    assert body["description"] == "Who's on call"
    assert body["visit_count"] == 0
    assert body["last_visited_at"] is None
    assert body["created_at"].endswith(("Z", "+00:00"))


def test_duplicate_slug_differing_only_by_case_is_409(client: TestClient) -> None:
    client.post("/api/links", json=VALID_LINK)

    response = client.post("/api/links", json={**VALID_LINK, "slug": "ONCALL"})

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "slug_taken"
    assert error["details"] == [{"field": "slug", "message": "go/oncall is already taken."}]


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"slug": "-oncall"}, "slug"),
        ({"slug": "on call"}, "slug"),
        ({"slug": "a" * 65}, "slug"),
        ({"slug": "Docs"}, "slug"),  # reserved, case-insensitively
        ({"target_url": "javascript:alert(1)"}, "target_url"),
        ({"target_url": "/relative/path"}, "target_url"),
        ({"target_url": "http://localhost:8000/oncall"}, "target_url"),  # loops back into go/
        ({"description": "x" * 281}, "description"),
    ],
)
def test_invalid_input_is_422_with_field_detail(
    client: TestClient, overrides: dict[str, Any], field: str
) -> None:
    response = client.post("/api/links", json={**VALID_LINK, **overrides})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert [detail["field"] for detail in error["details"]] == [field]


def test_list_is_sorted_by_slug(client: TestClient) -> None:
    for slug in ["payroll", "design-system", "oncall"]:
        client.post("/api/links", json={**VALID_LINK, "slug": slug})

    response = client.get("/api/links")

    assert response.status_code == 200
    assert [link["slug"] for link in response.json()["items"]] == [
        "design-system",
        "oncall",
        "payroll",
    ]


def test_unknown_link_is_404_with_envelope(client: TestClient) -> None:
    response = client.get("/api/links/nope", headers={"X-Request-ID": "req-404"})

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "link_not_found",
            "message": "go/nope doesn't exist.",
            "request_id": "req-404",
        }
    }
