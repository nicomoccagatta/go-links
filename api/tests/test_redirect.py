from fastapi.testclient import TestClient


def test_redirect_is_302_and_counts_the_visit(client: TestClient) -> None:
    client.post("/api/links", json={"slug": "oncall", "target_url": "https://oncall.example.com"})

    response = client.get("/OnCall")

    assert response.status_code == 302
    assert response.headers["location"] == "https://oncall.example.com"
    link = client.get("/api/links/oncall").json()
    assert link["visit_count"] == 1
    assert link["last_visited_at"] is not None


def test_unknown_slug_redirects_to_create_page(client: TestClient) -> None:
    response = client.get("/new-thing")

    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:5173/?new=new-thing"


def test_unknown_slug_is_url_encoded_in_create_page(client: TestClient) -> None:
    response = client.get("/Team%20Wiki")

    assert response.headers["location"] == "http://localhost:5173/?new=team+wiki"
