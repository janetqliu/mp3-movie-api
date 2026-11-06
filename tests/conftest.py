from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app, storage
from src.storage import MOVIE_COLUMNS

def clear_storage():
    storage.save(pd.DataFrame(columns=MOVIE_COLUMNS))

@pytest.fixture
def client():
    clear_storage()
    with TestClient(app) as test_client:
        yield test_client
    clear_storage()


@pytest.fixture
def sample_movie_bytes():
    filepath = Path("fixtures") / "sample_movies.csv"
    return filepath.read_bytes()

@pytest.fixture
def sample_txt_bytes():
    filepath = Path("fixtures") / "sample.txt"
    return filepath.read_bytes()

@pytest.fixture
def empty_csv_bytes():
    filepath = Path("fixtures") / "empty.csv"
    return filepath.read_bytes()


@pytest.fixture
def uploaded_movies(client, sample_movie_bytes):
    response = client.post(
        "/upload",
        files={"file": ("sample_movies.csv", sample_movie_bytes, "text/csv")}
    )
    assert response.status_code == 200


@pytest.fixture
def processing_body():
    return {
        "validation": {
            "required_columns": list(MOVIE_COLUMNS),
            "numeric_columns": ["release_year", "rating"]
        },
        "processing": {
            "remove_duplicates": True,
            "missing": {
                "enabled": True,
                "axis": "rows"
            },
            "outliers": {
                "enabled": False,
                "columns": [],
                "method": "iqr",
                "threshold": 1.5
            }
        }
    }
