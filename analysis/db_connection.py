import os
from contextlib import contextmanager

import psycopg2


def get_db_config() -> dict:
    return {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
    }


@contextmanager
def get_db_connection():
    conn = psycopg2.connect(**get_db_config())
    try:
        yield conn
    finally:
        conn.close()
