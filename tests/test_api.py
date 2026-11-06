def test_upload_csv(client, sample_csv_bytes):
    response = client.post("/upload", files={"file": ("sample.csv", sample_csv_bytes, "text/csv")})
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 6
    assert body["columns"] == 2
    assert isinstance(body["id"], int)
    assert body["id"] > 0


def test_process_and_retrieve(
    client, uploaded_dataset_id, processing_body
):
    response = client.post(f"/datasets/{uploaded_dataset_id}/process", json=processing_body)

    assert response.status_code == 200
    body = response.json()
    assert body["validation_rows_removed"] == 1
    assert body["cleaning_report"]["rows_before"] == 5
    assert body["cleaning_report"]["rows_after"] == 3

    response2 = client.get(f"/datasets/{uploaded_dataset_id}")
    assert response2.status_code == 200
    body2 = response2.json()
    assert body2["total_rows"] == 3

    scores = {record["student_id"]: record["score"] for record in body2["data"]}
    assert scores == {1: 80, 2: 90, 5: 85}


def test_retrieve_missing_dataset(client):
    response = client.get("/datasets/100")
    assert response.status_code == 404

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"

def test_unsupported_file(client, sample_txt_bytes):
    response = client.post("/upload", files={"file": ("sample.txt", sample_txt_bytes, "text/plain")})
    assert response.status_code == 400

def test_empty_file(client, empty_csv_bytes):
    response = client.post("/upload", files={"file": ("empty.csv", empty_csv_bytes, "text/csv")})
    assert response.status_code == 400


def get_stored(client, dataset_id):
    response = client.get(f"/datasets/{dataset_id}")
    assert response.status_code == 200
    return response.json()


def test_retrieve_with_limit(client, uploaded_dataset_id):
    response = client.get(f"/datasets/{uploaded_dataset_id}", params={"limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert body["total_rows"] == 6


def test_invalid_limit(client, uploaded_dataset_id):
    response = client.get(f"/datasets/{uploaded_dataset_id}", params={"limit": 0})
    assert response.status_code == 422


def test_process_missing_dataset(client, processing_body):
    response = client.post("/datasets/999/process", json=processing_body)
    assert response.status_code == 404


def test_missing_required_column(client, uploaded_dataset_id, processing_body):
    before = get_stored(client, uploaded_dataset_id)

    processing_body["validation"]["required_columns"].append("age")

    response = client.post(f"/datasets/{uploaded_dataset_id}/process", json=processing_body)
    assert response.status_code == 400
    assert get_stored(client, uploaded_dataset_id) == before


def test_unsupported_outlier_method(client, uploaded_dataset_id, processing_body):
    before = get_stored(client, uploaded_dataset_id)

    processing_body["processing"]["outliers"] = {
        "enabled": True,
        "columns": ["score"],
        "method": "median",
        "threshold": 1.5,
    }

    response = client.post(f"/datasets/{uploaded_dataset_id}/process", json=processing_body)
    assert response.status_code == 400
    assert get_stored(client, uploaded_dataset_id) == before


def test_malformed_request_body(client, uploaded_dataset_id):
    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process",
        content="{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_request_ids(client, uploaded_dataset_id, processing_body):
    processing_body["validation"]["required_columns"].append("age")

    responses = {
        200: client.get("/health"),
        400: client.post(f"/datasets/{uploaded_dataset_id}/process", json=processing_body),
        404: client.get("/datasets/999"),
        422: client.get(f"/datasets/{uploaded_dataset_id}", params={"limit": 0}),
    }

    for expected_status, response in responses.items():
        assert response.status_code == expected_status
        request_id = response.headers["X-Request-ID"]
        assert request_id
        assert len(request_id) == 8

    first = client.get("/health").headers["X-Request-ID"]
    second = client.get("/health").headers["X-Request-ID"]
    assert first != second