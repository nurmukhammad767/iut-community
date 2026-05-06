import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

def get_db_connection():
    url = urlparse(os.getenv("DATABASE_URL"))
    conn = psycopg2.connect(
        host=url.hostname,
        port=url.port,
        database=url.path[1:],   # remove leading slash
        user=url.username,
        password=url.password,
        cursor_factory=RealDictCursor,
    )
    return conn