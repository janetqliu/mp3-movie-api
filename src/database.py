import sqlite3
from pathlib import Path


def get_connection(db_path):
    """Return a fresh connection with rows accessible by column name."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database(db_path):
    """Create the movie table if it does not exist."""

    sql_statement = """
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY,
        title TEXT NULL,
        release_year INT NULL,
        rating REAL NULL,
        genre TEXT NULL
    )
    """
    connection = get_connection(db_path)
    connection.execute(sql_statement)
    connection.commit()
    connection.close()