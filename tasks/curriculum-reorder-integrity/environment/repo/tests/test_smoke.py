"""The suite the team ships with the repo. It covers the happy path only."""
import pytest

from curriculum import db, ordering, seed


@pytest.fixture()
def conn():
    c = db.connect()
    seed.seed(c)
    yield c
    c.close()


def section_id(conn, title):
    return db.one(conn, "SELECT id FROM sections WHERE title = %s", (title,))["id"]


def test_seed_orders_each_section_from_one(conn):
    first = section_id(conn, "Foundations")
    assert [l["position"] for l in ordering.lessons_in(conn, first)] == [1, 2, 3]


def test_append_lands_at_the_end_of_the_only_touched_section(conn):
    first = section_id(conn, "Foundations")
    with conn.cursor() as cur:
        cur.execute("DELETE FROM lessons WHERE section_id <> %s", (first,))
    conn.commit()
    ordering.append_lesson(conn, first, "Position sizing")
    assert [l["title"] for l in ordering.lessons_in(conn, first)][-1] == "Position sizing"


def test_normalize_is_idempotent(conn):
    first = section_id(conn, "Foundations")
    ordering.normalize_positions(conn, first)
    before = [l["id"] for l in ordering.lessons_in(conn, first)]
    ordering.normalize_positions(conn, first)
    assert [l["id"] for l in ordering.lessons_in(conn, first)] == before
