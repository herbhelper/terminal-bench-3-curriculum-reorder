"""Database access for the curriculum service.

One process, one connection, autocommit off. Every public entry point in this
package is expected to own its transaction boundary.
"""
import os
import pathlib

import psycopg2
import psycopg2.extras

SCHEMA = pathlib.Path(__file__).with_name("schema.sql")

DSN = os.environ.get("CURRICULUM_DSN", "dbname=curriculum user=curriculum password=curriculum host=127.0.0.1")


def connect():
    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    return conn


def reset(conn):
    """Drop and rebuild the schema. Used by the test fixtures and the seeder."""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS lesson_moves, lessons, sections CASCADE")
        cur.execute("DROP FUNCTION IF EXISTS log_lesson_move() CASCADE")
        cur.execute(SCHEMA.read_text())
    conn.commit()


def rows(conn, sql, params=()):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def one(conn, sql, params=()):
    result = rows(conn, sql, params)
    return result[0] if result else None
