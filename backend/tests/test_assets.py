"""assets router の統合テスト。shots同様domain.items.create_item_routerを使うため最小限。"""

from fastapi.testclient import TestClient


def test_create_and_list_asset(client: TestClient) -> None:
    create_res = client.post("/assets", json={"name": "Character_Hero"})

    assert create_res.status_code == 201
    assert create_res.json()["status"] == "not_started"

    list_res = client.get("/assets")
    assert [a["name"] for a in list_res.json()] == ["Character_Hero"]


def test_asset_status_update_rejects_invalid_enum(client: TestClient) -> None:
    asset_id = client.post("/assets", json={"name": "Prop_Chair"}).json()["id"]

    response = client.patch(f"/assets/{asset_id}/status", json={"status": "unknown"})

    assert response.status_code == 400


def test_shots_and_assets_are_independent_collections(client: TestClient) -> None:
    """shotsとassetsは別テーブルであり、互いのIDが衝突・混在しないことを確認する。"""
    client.post("/shots", json={"name": "SHOT010"})

    assets_res = client.get("/assets")

    assert assets_res.json() == []
