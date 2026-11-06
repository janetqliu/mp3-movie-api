from src.storage import MOVIE_COLUMNS


def upload(client, data, filename="sample_movies.csv"):
    return client.post("/upload", files={"file": (filename, data, "text/csv")})


def get_all_movies(client):
    response = client.get("/movies", params={"limit": 1000})
    assert response.status_code == 200
    return response.json()


# --- /health ---

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# --- POST /upload ---

def test_upload_movies(client, sample_movie_bytes):
    response = upload(client, sample_movie_bytes)
    assert response.status_code == 200
    assert response.json() == {
        "filename": "sample_movies.csv",
        "rows": 20,
        "columns": 4,
        "column_names": MOVIE_COLUMNS,
    }


def test_upload_replaces_collection(client, sample_movie_bytes):
    upload(client, sample_movie_bytes)
    upload(client, sample_movie_bytes)

    body = get_all_movies(client)
    assert body["total_rows"] == 20
    assert body["data"][0]["id"] == 1


def test_upload_unsupported_extension(client, sample_txt_bytes):
    response = client.post(
        "/upload", files={"file": ("sample.txt", sample_txt_bytes, "text/plain")}
    )
    assert response.status_code == 400


def test_upload_empty_file(client, empty_csv_bytes):
    response = upload(client, empty_csv_bytes, "empty.csv")
    assert response.status_code == 400


def test_upload_header_only(client):
    response = upload(client, (",".join(MOVIE_COLUMNS) + "\n").encode(), "header.csv")
    assert response.status_code == 400


def test_upload_wrong_columns(client):
    response = upload(client, b"student_id,score\n1,80\n", "wrong.csv")
    assert response.status_code == 400
    assert get_all_movies(client)["total_rows"] == 0


# --- GET /movies ---

def test_get_movies_with_limit(client, uploaded_movies):
    response = client.get("/movies", params={"limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 20
    assert [row["id"] for row in body["data"]] == [1, 2]
    assert set(body["data"][0]) == {"id", *MOVIE_COLUMNS}


def test_get_movies_empty(client):
    response = client.get("/movies")
    assert response.status_code == 200
    assert response.json() == {"data": [], "total_rows": 0}


def test_get_movies_invalid_limit(client):
    response = client.get("/movies", params={"limit": 0})
    assert response.status_code == 422


# --- GET /movies/search ---

def test_search_default_columns(client, uploaded_movies):
    response = client.get("/movies/search", params={"min_rating": 8.5, "limit": 2})
    assert response.status_code == 200
    rows = response.json()
    assert 0 < len(rows) <= 2
    assert all(set(row) == {"id", "title"} for row in rows)


def test_search_selected_columns(client, uploaded_movies):
    response = client.get(
        "/movies/search",
        params={"columns": ["title", "rating"], "min_rating": 8.5, "limit": 2},
    )
    assert response.status_code == 200
    rows = response.json()
    assert 0 < len(rows) <= 2
    assert all(set(row) == {"id", "title", "rating"} for row in rows)

    ratings = [row["rating"] for row in rows]
    assert all(rating >= 8.5 for rating in ratings)
    assert ratings == sorted(ratings, reverse=True)


def test_search_no_matches(client):
    response = client.get("/movies/search")
    assert response.status_code == 200
    assert response.json() == []


def test_search_unsupported_column(client, uploaded_movies):
    response = client.get("/movies/search", params={"columns": ["budget"]})
    assert response.status_code == 400


def test_search_invalid_min_rating(client):
    response = client.get("/movies/search", params={"min_rating": 11})
    assert response.status_code == 422


# --- POST /movies/process ---

def test_process_movies(client, uploaded_movies, processing_body):
    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 200
    body = response.json()
    report = body["cleaning_report"]

    assert report["rows_before"] == 20 - body["validation_rows_removed"]
    assert get_all_movies(client)["total_rows"] == report["rows_after"]


def test_process_empty_collection(client, processing_body):
    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 400


def test_process_missing_required_column(client, uploaded_movies, processing_body):
    before = get_all_movies(client)
    processing_body["validation"]["required_columns"].append("budget")

    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 400
    assert get_all_movies(client) == before


def test_process_unsupported_outlier_method(client, uploaded_movies, processing_body):
    before = get_all_movies(client)
    processing_body["processing"]["outliers"] = {
        "enabled": True,
        "columns": ["rating"],
        "method": "median",
        "threshold": 1.5,
    }

    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 400
    assert get_all_movies(client) == before


def test_process_malformed_body(client):
    response = client.post(
        "/movies/process",
        content="{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


# --- Middleware ---

def test_request_ids(client, uploaded_movies, processing_body):
    processing_body["validation"]["required_columns"].append("budget")

    responses = {
        200: client.get("/health"),
        400: client.post("/movies/process", json=processing_body),
        404: client.get("/does-not-exist"),
        422: client.get("/movies", params={"limit": 0}),
    }

    for expected_status, response in responses.items():
        assert response.status_code == expected_status
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 8

    first = client.get("/health").headers["X-Request-ID"]
    second = client.get("/health").headers["X-Request-ID"]
    assert first != second