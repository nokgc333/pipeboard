"""一覧の検索・絞り込み・ページングのテスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _seed(client: TestClient) -> None:
    for name in ("SHOT010", "SHOT020", "shot_hero", "SEQ_B_030", "Chair"):
        client.post("/shots", json={"name": name})
    ids = {s["name"]: s["id"] for s in client.get("/shots").json()}
    client.patch(f"/shots/{ids['SHOT020']}/status", json={"status": "in_progress"})
    client.patch(f"/shots/{ids['SEQ_B_030']}/status", json={"status": "done"})


def _names(response) -> list[str]:  # type: ignore[no-untyped-def]
    return [item["name"] for item in response.json()]


def test_without_parameters_everything_is_returned_newest_first(client: TestClient) -> None:
    _seed(client)

    response = client.get("/shots")

    assert _names(response) == ["Chair", "SEQ_B_030", "shot_hero", "SHOT020", "SHOT010"]


def test_the_total_count_header_counts_all_matches_not_only_the_page(client: TestClient) -> None:
    _seed(client)

    response = client.get("/shots?limit=2")

    assert len(response.json()) == 2
    assert response.headers["X-Total-Count"] == "5"


def test_offset_skips_items_from_the_start(client: TestClient) -> None:
    _seed(client)

    response = client.get("/shots?limit=2&offset=2")

    assert _names(response) == ["shot_hero", "SHOT020"]


def test_the_last_page_can_be_shorter(client: TestClient) -> None:
    _seed(client)

    assert _names(client.get("/shots?limit=2&offset=4")) == ["SHOT010"]


def test_an_offset_past_the_end_gives_an_empty_list_with_the_real_total(
    client: TestClient,
) -> None:
    _seed(client)

    response = client.get("/shots?offset=50")

    assert response.json() == []
    assert response.headers["X-Total-Count"] == "5"


def test_search_matches_part_of_the_name_ignoring_case(client: TestClient) -> None:
    _seed(client)

    assert _names(client.get("/shots?q=shot")) == ["shot_hero", "SHOT020", "SHOT010"]


def test_search_treats_percent_and_underscore_literally(client: TestClient) -> None:
    _seed(client)

    assert _names(client.get("/shots?q=_B_")) == ["SEQ_B_030"]
    assert _names(client.get("/shots?q=%25")) == []


def test_status_filters_to_one_column(client: TestClient) -> None:
    _seed(client)

    assert _names(client.get("/shots?status=in_progress")) == ["SHOT020"]
    assert _names(client.get("/shots?status=done")) == ["SEQ_B_030"]


def test_search_and_status_combine_with_and(client: TestClient) -> None:
    _seed(client)

    assert _names(client.get("/shots?q=SHOT&status=in_progress")) == ["SHOT020"]
    assert _names(client.get("/shots?q=Chair&status=done")) == []


def test_the_total_count_follows_the_filters(client: TestClient) -> None:
    _seed(client)

    assert client.get("/shots?q=SHOT").headers["X-Total-Count"] == "3"


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=501", "limit=-1", "offset=-1", "status=archived", "limit=abc"]
)
def test_invalid_parameters_are_rejected(client: TestClient, query: str) -> None:
    assert client.get(f"/shots?{query}").status_code == 422


def test_assets_support_the_same_parameters(client: TestClient) -> None:
    for name in ("Hero", "Prop_Chair"):
        client.post("/assets", json={"name": name})

    response = client.get("/assets?q=chair&limit=10")

    assert _names(response) == ["Prop_Chair"]
    assert response.headers["X-Total-Count"] == "1"
