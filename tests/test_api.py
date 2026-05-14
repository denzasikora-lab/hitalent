from fastapi.testclient import TestClient


def test_create_tree_and_get_depth(client: TestClient) -> None:
    r = client.post("/departments/", json={"name": "Root"})
    assert r.status_code == 201
    root_id = r.json()["id"]

    r = client.post("/departments/", json={"name": "Eng", "parent_id": root_id})
    assert r.status_code == 201
    eng_id = r.json()["id"]

    r = client.post("/departments/", json={"name": "Backend", "parent_id": eng_id})
    assert r.status_code == 201

    r = client.get(f"/departments/{root_id}", params={"depth": 1})
    assert r.status_code == 200
    body = r.json()
    assert len(body["children"]) == 1
    assert body["children"][0]["department"]["name"] == "Eng"
    assert body["children"][0]["children"] == []

    r = client.get(f"/departments/{root_id}", params={"depth": 2})
    assert r.status_code == 200
    body = r.json()
    assert len(body["children"][0]["children"]) == 1
    assert body["children"][0]["children"][0]["department"]["name"] == "Backend"


def test_duplicate_department_name_same_parent_409(client: TestClient) -> None:
    r = client.post("/departments/", json={"name": "DupRoot"})
    assert r.status_code == 201
    root_id = r.json()["id"]
    assert client.post("/departments/", json={"name": "A", "parent_id": root_id}).status_code == 201
    r2 = client.post("/departments/", json={"name": "A", "parent_id": root_id})
    assert r2.status_code == 409


def test_patch_cycle_409(client: TestClient) -> None:
    a = client.post("/departments/", json={"name": "A"}).json()["id"]
    b = client.post("/departments/", json={"name": "B", "parent_id": a}).json()["id"]
    c = client.post("/departments/", json={"name": "C", "parent_id": b}).json()["id"]
    r = client.patch(f"/departments/{a}", json={"parent_id": c})
    assert r.status_code == 409


def test_patch_move_to_root(client: TestClient) -> None:
    a = client.post("/departments/", json={"name": "A"}).json()["id"]
    b = client.post("/departments/", json={"name": "B", "parent_id": a}).json()["id"]
    r = client.patch(f"/departments/{b}", json={"parent_id": None})
    assert r.status_code == 200
    assert r.json()["parent_id"] is None


def test_delete_reassign_leaf_moves_employees(client: TestClient) -> None:
    a = client.post("/departments/", json={"name": "A"}).json()["id"]
    b = client.post("/departments/", json={"name": "B", "parent_id": a}).json()["id"]
    e = client.post(
        f"/departments/{b}/employees/",
        json={"full_name": "Jane", "position": "Dev"},
    ).json()
    assert e["department_id"] == b

    r = client.delete(f"/departments/{b}", params={"mode": "reassign", "reassign_to_department_id": a})
    assert r.status_code == 204

    tree = client.get(f"/departments/{a}", params={"depth": 1}).json()
    assert any(x["full_name"] == "Jane" and x["department_id"] == a for x in tree["employees"])


def test_delete_reassign_with_children_409(client: TestClient) -> None:
    a = client.post("/departments/", json={"name": "A"}).json()["id"]
    b = client.post("/departments/", json={"name": "B", "parent_id": a}).json()["id"]
    client.post("/departments/", json={"name": "C", "parent_id": b})
    r = client.delete(f"/departments/{b}", params={"mode": "reassign", "reassign_to_department_id": a})
    assert r.status_code == 409
    assert "child departments" in r.json()["detail"].lower()


def test_delete_cascade_removes_subtree(client: TestClient) -> None:
    a = client.post("/departments/", json={"name": "A"}).json()["id"]
    b = client.post("/departments/", json={"name": "B", "parent_id": a}).json()["id"]
    client.post(f"/departments/{b}/employees/", json={"full_name": "X", "position": "Y"})
    r = client.delete(f"/departments/{a}", params={"mode": "cascade"})
    assert r.status_code == 204
    assert client.get(f"/departments/{a}").status_code == 404


def test_employee_sort_order(client: TestClient) -> None:
    d = client.post("/departments/", json={"name": "D"}).json()["id"]
    client.post(f"/departments/{d}/employees/", json={"full_name": "Zeta", "position": "p"})
    client.post(f"/departments/{d}/employees/", json={"full_name": "Alpha", "position": "p"})
    tree = client.get(f"/departments/{d}").json()
    names = [e["full_name"] for e in tree["employees"]]
    # Primary: created_at ascending; Zeta created before Alpha
    assert names == ["Zeta", "Alpha"]


def test_duplicate_root_department_name_409(client: TestClient) -> None:
    assert client.post("/departments/", json={"name": "OnlyOne"}).status_code == 201
    r2 = client.post("/departments/", json={"name": "OnlyOne"})
    assert r2.status_code == 409


def test_reassign_cannot_use_self_as_target_409(client: TestClient) -> None:
    b = client.post("/departments/", json={"name": "Leaf"}).json()["id"]
    client.post(f"/departments/{b}/employees/", json={"full_name": "E", "position": "P"})
    r = client.delete(f"/departments/{b}", params={"mode": "reassign", "reassign_to_department_id": b})
    assert r.status_code == 409
